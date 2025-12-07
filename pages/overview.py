import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
import os
from utils import get_user_cache

cache = get_user_cache()

cache['homepage_visited'] = True

# --- CONFIGURAZIONE PERCORSI ---
# Nota: Usa percorsi relativi o assoluti in base a dove lanci il comando streamlit
# Se questo file è in una sottocartella, potresti dover aggiustare i path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "assets", "offers")
# Se i file sono nella root del progetto, potresti dover usare '..' se questo script è in /pages
PATH_XML = os.path.join(DATA_DIR, "PO_Offerte_E_MLIBERO_20251121.xml")
PATH_CSV = os.path.join(DATA_DIR, "PO_Parametri_Mercato_Libero_E_20251121.csv")
PATH_PUN = os.path.join(DATA_DIR, "pun.csv")

# --- 1. FUNZIONI HELPER & PARSING (Invariate) ---

def _get_text(elem, xpath, default=None):
    if elem is None: return default
    found = elem.find(xpath)
    return found.text if found is not None else default

def _safe_float(val):
    if not val: return 0.0
    if isinstance(val, (float, int)): return float(val)
    try:
        return float(str(val).replace(',', '.').replace(' ', '').strip())
    except (ValueError, TypeError):
        return 0.0

def _map_fascia(code):
    if code == "01": return "F1"
    if code == "02": return "F2"
    if code == "03": return "F3"
    if code == "91": return "F23"
    return "F0"

def carica_pun_da_csv(filepath):
    try:
        df = pd.read_csv(filepath, sep=';', encoding='utf-8')
        df.columns = [c.strip().upper() for c in df.columns]
        col_f1 = next(c for c in df.columns if 'F1' in c)
        col_f2 = next(c for c in df.columns if 'F2' in c)
        col_f3 = next(c for c in df.columns if 'F3' in c)
        pun_medio = {
            'F1': df[col_f1].mean(),
            'F2': df[col_f2].mean(),
            'F3': df[col_f3].mean()
        }
        pun_medio['F23'] = (pun_medio['F2'] + pun_medio['F3']) / 2
        pun_medio['F0'] = (pun_medio['F1'] + pun_medio['F2'] + pun_medio['F3']) / 3
        return pun_medio
    except Exception as e:
        # Fallback silenzioso o loggato
        return {'F1': 0.12, 'F2': 0.11, 'F3': 0.10, 'F23': 0.105, 'F0': 0.11}

def carica_parametri_da_df(df):
    try:
        df.columns = [c.strip().lower() for c in df.columns]
        col_nome = next(c for c in df.columns if 'parametro' in c)
        col_val = next(c for c in df.columns if 'valore' in c)
        diz = {}
        for _, row in df.iterrows():
            diz[row[col_nome]] = _safe_float(row[col_val])
        return diz
    except Exception as e:
        st.error(f"Errore struttura CSV Parametri: {e}")
        return {}

def parsa_offerte_da_stringa(xml_string):
    xml_string = xml_string.strip()
    try:
        tree = ET.ElementTree(ET.fromstring(xml_string))
    except ET.ParseError:
        return []

    root = tree.getroot()
    ns = ""
    if '}' in root.tag:
        ns = root.tag.split('}')[0] + "}"

    iter_offerte = root.findall(f".//{ns}offerta") if root.tag != f"{ns}offerta" else [root]
    lista_offerte = []
    
    for offerta in iter_offerte:
        nome = _get_text(offerta, f".//{ns}NOME_OFFERTA", "Sconosciuto")
        codice = _get_text(offerta, f".//{ns}COD_OFFERTA", "")
        tipo_code = _get_text(offerta, f".//{ns}DettaglioOfferta/{ns}TIPO_CLIENTE", "01")
        tipo_cliente_label = "Domestico" if tipo_code == "01" else "Business"

        idx_node = offerta.find(f".//{ns}RiferimentiPrezzoEnergia/{ns}IDX_PREZZO_ENERGIA")
        is_variable = True if (idx_node is not None and idx_node.text and idx_node.text.strip()) else False
        tipo_prezzo_label = "Variabile" if is_variable else "Fisso"

        dati = {
            'nome': nome, 'codice': codice, 'target': tipo_cliente_label,
            'tipo_prezzo': tipo_prezzo_label,
            'p_fix_comm': 0.0, 'p_vol_comm': {}, 
            'p_fix_fer': 0.0, 'p_vol_fer': {}, 
            'p_vol_qe': {}, 'spread': {}, 'p_pot_qe': 0.0
        }
        
        for comp in offerta.findall(f".//{ns}ComponenteImpresa"):
            macro = _get_text(comp, f".//{ns}MACROAREA")
            if not macro: continue
            
            for intervallo in comp.findall(f".//{ns}IntervalloPrezzi"):
                p_text = _get_text(intervallo, f".//{ns}PREZZO")
                prezzo = _safe_float(p_text)
                u_mis = _get_text(intervallo, f".//{ns}UNITA_MISURA")
                
                if macro == "01": # Comm. Fissa
                     dati['p_fix_comm'] += prezzo if prezzo > 20 else prezzo * 12
                elif macro == "02": # Comm. Variabile
                     if u_mis == "03":
                        fascia = _map_fascia(_get_text(intervallo, f".//{ns}FASCIA_COMPONENTE"))
                        dati['p_vol_comm'][fascia] = prezzo
                elif macro == "04": # Energia
                    if u_mis == "03":
                        fascia = _map_fascia(_get_text(intervallo, f".//{ns}FASCIA_COMPONENTE", "00"))
                        if is_variable: dati['spread'][fascia] = prezzo
                        else: dati['p_vol_qe'][fascia] = prezzo
                    elif u_mis == "02": dati['p_pot_qe'] += prezzo
                elif macro == "06": # FER
                     if u_mis == "01": dati['p_fix_fer'] += prezzo if prezzo > 20 else prezzo * 12
                     elif u_mis == "03":
                        fascia = _map_fascia(_get_text(intervallo, f".//{ns}FASCIA_COMPONENTE", "00"))
                        dati['p_vol_fer'][fascia] = prezzo

        lista_offerte.append(dati)
    return lista_offerte

# --- 2. CLASSE CALCOLO ---

class CalcolatoreSpesa:
    def __init__(self, parametri_csv, pun_medio):
        self.p = parametri_csv
        self.pun = pun_medio
    
    def _get_val(self, key, default=0.0):
        return float(self.p.get(key, default))

    def calcola_dettaglio(self, dati_offerta, profilo):
        consumo_tot = profilo['consumo_annuo']
        potenza = profilo['potenza']
        consumi_fasce = {k: consumo_tot * v for k, v in profilo['ripartizione'].items()}

        c_energia = 0.0
        
        if dati_offerta['tipo_prezzo'] == "Fisso":
            prezzi = dati_offerta['p_vol_qe']
            if len(prezzi) == 1 or 'F0' in prezzi:
                c_energia += list(prezzi.values())[0] * consumo_tot
            else:
                for f, kwh in consumi_fasce.items():
                    p = prezzi.get(f, prezzi.get('F0', prezzi.get('F1', 0.15)))
                    c_energia += p * kwh
        elif dati_offerta['tipo_prezzo'] == 'Variabile':
            spreads = dati_offerta['spread']
            lambda_val = self._get_val('lambda', 0.10)
            for f, kwh in consumi_fasce.items():
                pun_f = self.pun.get(f, self.pun.get('F0', 0.12))
                spread_f = spreads.get(f, spreads.get('F0', spreads.get('F1', 0.0)))
                prezzo_finito = (pun_f * (1 + lambda_val)) + spread_f
                c_energia += prezzo_finito * kwh

        prezzi_fer = dati_offerta['p_vol_fer']
        if prezzi_fer:
            if len(prezzi_fer) == 1 or 'F0' in prezzi_fer:
                 c_energia += list(prezzi_fer.values())[0] * consumo_tot
            else:
                for f, kwh in consumi_fasce.items():
                    p = prezzi_fer.get(f, prezzi_fer.get('F0', 0.0))
                    c_energia += p * kwh

        spesa_materia_energia = (
            dati_offerta['p_fix_fer'] + (dati_offerta['p_pot_qe'] * potenza) + 
            c_energia + (self._get_val('ppe', 0.0) * consumo_tot)
        )

        key_dispbt = 'dispbt_d' if profilo['residente'] and profilo['target'] == 'Domestico' else 'dispbt_nd'
        dispbt = self._get_val(key_dispbt, 0.0)
        
        comm_var_tot = 0.0
        prezzi_comm = dati_offerta['p_vol_comm']
        if prezzi_comm:
             if len(prezzi_comm) == 1 or 'F0' in prezzi_comm:
                 comm_var_tot += list(prezzi_comm.values())[0] * consumo_tot
             else:
                 for f, kwh in consumi_fasce.items():
                     comm_var_tot += prezzi_comm.get(f, 0.0) * kwh

        spesa_comm = dati_offerta['p_fix_comm'] + comm_var_tot + self._get_val('pcv_c', 0.0) + dispbt
        spesa_disp = self._get_val('cdispd', 0.0) * (1 + self._get_val('lambda', 0.1)) * consumo_tot
        
        s_rete = (self._get_val('sigma1', 0.0) + 
                  (self._get_val('sigma2', 0.0) + self._get_val('uc6s_d', 0.0)) * potenza + 
                  (self._get_val('sigma3', 0.0) + self._get_val('uc3', 0.0) + self._get_val('uc6p_d', 0.0)) * consumo_tot)
        
        if profilo['target'] == 'Domestico' and profilo['residente']:
             s_oneri = (self._get_val('asos_dr', 0.0) + self._get_val('arim_dr', 0.0)) * consumo_tot
        else:
             s_oneri = (self._get_val('asos_dnr_f', 0.0) + self._get_val('arim_dnr_f', 0.0) + 
                        (self._get_val('asos_dnr_v', 0.0) + self._get_val('arim_dnr_v', 0.0)) * consumo_tot)

        accise = 0.0
        if profilo['target'] == 'Domestico' and profilo['residente'] and potenza <= 3:
            if consumo_tot > 1800:
                 accise = self._get_val('acc_c_r_l', 0.0227) * (consumo_tot - 1800)
        elif profilo['target'] != 'Domestico':
             accise = self._get_val('acc_a_l_l', 0.0227) * consumo_tot
        else:
             accise = self._get_val('acc_c_nr', 0.0227) * consumo_tot

        imponibile = spesa_materia_energia + spesa_comm + spesa_disp + s_rete + s_oneri + accise
        totale_con_iva = imponibile * 1.10
        
        return {
            "Totale Mensile": round(totale_con_iva / 12, 2),
            "Totale Annuo": round(totale_con_iva, 2),
            "Materia Energia": round(spesa_materia_energia, 2),
            "Fisso Vendita": round(dati_offerta['p_fix_comm'], 2),
            "Imposte": round(accise + (imponibile * 0.10), 2)
        }

# --- 3. UI PAGE FUNCTION ---
with st.container(border=True):
    st.subheader("⚡️ Comparatore Offerte", anchor=False)
    st.markdown("Analizza le offerte del mercato libero basate sul tuo profilo di consumo.")

# --- SEZIONE CONFIGURAZIONE (Espandibile al centro) ---
with st.expander("⚙️ Configurazione Profilo", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("1. Tipologia")
        # Chiave univoca per evitare conflitti con altri widget
        tipo_cliente = st.radio("Sei un cliente:", ["Domestico", "Business"], index=0, key="comp_tipo_cli", horizontal=True)
        target_xml = tipo_cliente
        
        residente = True
        if tipo_cliente == "Domestico":
            residente = st.checkbox("Residente", value=True, key="comp_residente")
        else:
            residente = False
            st.caption("Business = Non Residente")

    with col2:
        st.subheader("2. Consumi")
        potenza = st.slider("Potenza (kW)", 1.5, 15.0, 3.0, step=0.5, key="comp_potenza")
        consumo_annuo = st.number_input("Consumo Annuo (kWh)", value=1900, step=50, key="comp_consumo")

    with col3:
        st.subheader("3. Confronto")
        bolletta_attuale = st.number_input("Bolletta Attuale (€/mese)", value=0.0, step=1.0, key="comp_bolletta")
        st.info("Fasce stimate: F1 33%, F2 33%, F3 34%")

# --- LOGICA DI ESECUZIONE ---

if not os.path.exists(PATH_XML) or not os.path.exists(PATH_CSV):
    st.error(f"⚠️ File dati mancanti nella cartella principale: {PATH_XML}")
else:
    # Caricamento Dati
    try:
        # CSV Parametri
        df_csv = pd.read_csv(PATH_CSV, encoding='utf-8')
        if len(df_csv.columns) < 2: df_csv = pd.read_csv(PATH_CSV, sep=';', encoding='utf-8')
        parametri = carica_parametri_da_df(df_csv)
        
        # PUN (Opzionale)
        pun_data = carica_pun_da_csv(PATH_PUN) if os.path.exists(PATH_PUN) else {'F1':0.12, 'F2':0.11, 'F3':0.10}
        
        # XML Offerte
        with open(PATH_XML, "rb") as f:
            xml_bytes = f.read()
            try: xml_str = xml_bytes.decode('utf-8')
            except: xml_str = xml_bytes.decode('latin-1')
        offerte = parsa_offerte_da_stringa(xml_str)
        
        # Filtro e Calcolo
        offerte_ok = [o for o in offerte if o['target'] == target_xml]
        
        if offerte_ok:
            profilo = {
                "consumo_annuo": consumo_annuo, "potenza": potenza,
                "residente": residente, "target": target_xml,
                "ripartizione": {"F1": 0.33, "F2": 0.33, "F3": 0.34}
            }
            
            calc = CalcolatoreSpesa(parametri, pun_data)
            risultati = []
            
            for off in offerte_ok:
                try:
                    res = calc.calcola_dettaglio(off, profilo)
                    row = {
                        "Offerta": off['nome'],
                        "Tipo": off['tipo_prezzo'],
                        "Totale Mensile": res['Totale Mensile'],
                        "Totale Annuo": res['Totale Annuo'],
                        "Energia": res['Materia Energia'],
                        "Fisso Vendita": res['Fisso Vendita']
                    }
                    if bolletta_attuale > 0:
                        row["Risparmio"] = round(bolletta_attuale - res['Totale Mensile'], 2)
                    risultati.append(row)
                except: continue

            if risultati:
                df_res = pd.DataFrame(risultati).sort_values(by="Totale Annuo")
                
                with st.container(border=True):
                    st.subheader("🏆 Risultati")
                    
                    # Top KPI
                    best = df_res.iloc[0]
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Migliore Offerta", best['Offerta'], best['Tipo'])
                    m2.metric("Spesa Stimata", f"{best['Totale Annuo']} €/anno", f"{best['Totale Mensile']} €/mese")
                    
                    if bolletta_attuale > 0:
                        risp = best['Risparmio']
                        m3.metric("Risparmio", f"{risp} €/mese", delta_color="normal" if risp > 0 else "inverse")
                    
                    # Tabella
                    st.dataframe(
                        df_res.style.format({"Totale Annuo": "{:.2f}", "Totale Mensile": "{:.2f}", "Energia": "{:.2f}"}), 
                        use_container_width=True, 
                        hide_index=True
                    )
            else:
                st.warning("Impossibile calcolare preventivi validi con i dati attuali.")
        else:
            st.warning(f"Nessuna offerta trovata nel file XML per il profilo '{target_xml}'.")

    except Exception as e:
        st.error(f"Si è verificato un errore durante l'elaborazione: {e}")