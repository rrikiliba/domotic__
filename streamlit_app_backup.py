# streamlit_app.py - VERSIONE FINALE CON COLONNE CSV ARERA REALI
import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from openai import OpenAI
import plotly.express as px
import plotly.graph_objects as go

# Import enhanced parser
from bill_parser import EnhancedBillParser

# ============================================
# CONFIGURAZIONE
# ============================================

st.set_page_config(
    page_title="Energy Comparator",
    page_icon="⚡",
    layout="wide"
)

# OpenRouter client (compatibile con OpenAI SDK)
try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=st.secrets.get("OPENROUTER_API_KEY", "")
    )
    AI_AVAILABLE = True
except:
    AI_AVAILABLE = False
    st.warning("⚠️ OpenRouter API key non configurata. Chatbot non disponibile.")

# ============================================
# FUNZIONI HELPER
# ============================================

@st.cache_data(ttl=3600)
def load_arera_offers():
    """Carica offerte ARERA con cache"""
    try:
        #FIXME per diverse versioni del file CSV
        df = pd.read_csv('PO_Offerte_E_PLACET_20251113.csv')
        
        # Pulizia dati
        df = df.dropna(subset=['denominazione', 'nome_offerta'])
        
        # Converti prezzi in float
        # FIXME ATTENZIONE: se ci sono più colonne attive per fasce (tri, bi, mono), significa che l'offerta le supporta tutte separatamente
        price_columns = ['p_fix_f', 'p_fix_v', 'p_vol_f1', 'p_vol_f2', 'p_vol_f3', 
                        'p_vol_bf1', 'p_vol_bf23', 'p_vol_mono']
        for col in price_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df, None
    except FileNotFoundError:
        return None, "File CSV offerte non trovato!"
    except Exception as e:
        return None, f"Errore caricamento: {str(e)}"

def extract_pdf_text(uploaded_file):
    """Extract text from PDF using pdfplumber"""
    try:
        pdf_bytes = uploaded_file.read()
        text = ""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text, None
    except Exception as e:
        return "", f"Errore lettura PDF: {str(e)}"

def parse_bill_enhanced(text):
    """
    Parsing AVANZATO della bolletta usando EnhancedBillParser
    Estrae 30+ campi 
    """
    parser = EnhancedBillParser()
    result = parser.parse(text)
    
    # Aggiungi campi per backward compatibility
    if not result.get('importo_mensile'):
        result['importo_mensile'] = result.get('totale_bolletta', 50)
    if not result.get('spesa_annua'):
        result['spesa_annua'] = result.get('importo_mensile', 50) * 12
    
    return result

def extract_price_from_row(row, user_has_fasce=False):
    """
    Estrai prezzo kWh e costo fisso dalla riga CSV ARERA
    
    Colonne prezzi CSV:
    - p_fix_f: quota fissa se prezzo fisso (€/anno)
    - p_fix_v: quota fissa se prezzo variabile (€/anno)
    - p_vol_f1: prezzo energia fascia F1 (€/kWh)
    - p_vol_f2: prezzo energia fascia F2 (€/kWh)
    - p_vol_f3: prezzo energia fascia F3 (€/kWh)
    - p_vol_bf1: prezzo bioraria fascia 1 (€/kWh)
    - p_vol_bf23: prezzo bioraria fasce 2+3 (€/kWh)
    - p_vol_mono: prezzo monorario (€/kWh)
    """
    try:
        # Determina tipo offerta
        tipo_offerta = str(row.get('tipo_offerta', '')).lower()
        is_fixed = 'fisso' in tipo_offerta or 'fiss' in tipo_offerta
        
        # 1. QUOTA FISSA (costo annuale)
        if is_fixed and pd.notna(row.get('p_fix_f')):
            costo_fisso = float(row['p_fix_f'])
        elif pd.notna(row.get('p_fix_v')):
            costo_fisso = float(row['p_fix_v'])
        else:
            costo_fisso = 80.0  # Default se mancante
        
        # 2. PREZZO ENERGIA (€/kWh)
        # Priorità: trioraria > bioraria > monoraria FIXME
        
        # Se utente ha fasce F1/F2/F3, usa prezzo triorario
        if user_has_fasce:
            if pd.notna(row.get('p_vol_f1')) and pd.notna(row.get('p_vol_f2')):
                # Calcola media ponderata fasce (F1:33%, F2:33%, F3:34% tipico)
                p_f1 = float(row['p_vol_f1'])
                p_f2 = float(row.get('p_vol_f2', p_f1))
                p_f3 = float(row.get('p_vol_f3', p_f2))
                prezzo_kwh = (p_f1 * 0.33) + (p_f2 * 0.33) + (p_f3 * 0.34)
            elif pd.notna(row.get('p_vol_bf1')):
                # Bioraria: media ponderata (F1:46%, F2+F3:54%)
                p_bf1 = float(row['p_vol_bf1'])
                p_bf23 = float(row.get('p_vol_bf23', p_bf1))
                prezzo_kwh = (p_bf1 * 0.46) + (p_bf23 * 0.54)
            elif pd.notna(row.get('p_vol_mono')):
                prezzo_kwh = float(row['p_vol_mono'])
            else:
                prezzo_kwh = 0.12  # Default
        else:
            # Senza fasce, usa monoraria o media
            if pd.notna(row.get('p_vol_mono')):
                prezzo_kwh = float(row['p_vol_mono'])
            elif pd.notna(row.get('p_vol_bf1')):
                p_bf1 = float(row['p_vol_bf1'])
                p_bf23 = float(row.get('p_vol_bf23', p_bf1))
                prezzo_kwh = (p_bf1 * 0.46) + (p_bf23 * 0.54)
            elif pd.notna(row.get('p_vol_f1')):
                p_f1 = float(row['p_vol_f1'])
                p_f2 = float(row.get('p_vol_f2', p_f1))
                p_f3 = float(row.get('p_vol_f3', p_f2))
                prezzo_kwh = (p_f1 * 0.33) + (p_f2 * 0.33) + (p_f3 * 0.34)
            else:
                prezzo_kwh = 0.12  # Default
        
        return prezzo_kwh, costo_fisso, is_fixed
    
    except Exception as e:
        return 0.12, 80.0, False  # Fallback

def find_best_offers(df, user_profile, top_n=10):
    """
    Trova migliori offerte dal CSV ARERA
    Usa colonne reali: denominazione, nome_offerta, p_fix_*, p_vol_*
    """
    if df is None or df.empty:
        return []
    
    consumi_annui = user_profile.get('consumo_annuo_kwh', 2700)
    
    # Usa totale bolletta se disponibile, altrimenti stima
    if user_profile.get('totale_bolletta'):
        spesa_mensile = user_profile['totale_bolletta']
        spesa_attuale = spesa_mensile * 12
    else:
        spesa_attuale = user_profile.get('spesa_annua', 600)
    
    # Check se utente ha fasce orarie (per calcolo più preciso)
    user_has_fasce = all([
        user_profile.get('consumo_f1'),
        user_profile.get('consumo_f2'),
        user_profile.get('consumo_f3')
    ])
    
    results = []
    
    # Analizza tutte le offerte
    for idx, row in df.iterrows():
        try:
            # Estrai dati offerta
            fornitore = str(row.get('denominazione', 'N/A'))
            offerta = str(row.get('nome_offerta', 'N/A'))
            tipo_offerta = str(row.get('tipo_offerta', 'N/A'))
            cod_offerta = str(row.get('cod_offerta', ''))
            url_offerta = str(row.get('url_offerta', ''))
            
            # Skip se dati mancanti
            if fornitore == 'nan' or offerta == 'nan':
                continue
            
            # Estrai prezzi usando colonne reali
            prezzo_kwh, costo_fisso, is_fixed = extract_price_from_row(row, user_has_fasce)
            
            # Calcola costo totale
            costo_energia_anno = consumi_annui * prezzo_kwh
            costo_totale_anno = costo_energia_anno + costo_fisso
            
            # Calcola risparmio
            risparmio = spesa_attuale - costo_totale_anno
            risparmio_pct = (risparmio / spesa_attuale * 100) if spesa_attuale > 0 else 0
            
            # Score (0-100) basato su risparmio
            score = 50 + (risparmio / 10)
            score = max(0, min(100, score))
            
            results.append({
                'fornitore': fornitore,
                'offerta': offerta,
                'tipo_offerta': tipo_offerta,
                'tipo_prezzo': 'Fisso' if is_fixed else 'Variabile',
                'prezzo_kwh': round(prezzo_kwh, 4),
                'costo_fisso_anno': round(costo_fisso, 2),
                'costo_energia_anno': round(costo_energia_anno, 2),
                'costo_totale_anno': round(costo_totale_anno, 2),
                'risparmio_euro': round(risparmio, 2),
                'risparmio_pct': round(risparmio_pct, 1),
                'score': round(score, 1),
                'consigliata': risparmio > 100,
                'cod_offerta': cod_offerta,
                'url_offerta': url_offerta
            })
        
        except Exception as e:
            continue
    
    # Ordina per risparmio
    results = sorted(results, key=lambda x: x['risparmio_euro'], reverse=True)
    return results[:top_n]

def chat_with_openrouter(messages, user_context=None):
    """Chatbot con OpenRouter"""
    if not AI_AVAILABLE:
        return "⚠️ Chatbot non disponibile. Configura OPENROUTER_API_KEY."
    
    try:
        # Prepara contesto
        system_msg = """Sei un assistente esperto in bollette energetiche italiane. 
        Rispondi in modo chiaro, conciso e utile. Spiega concetti complessi in modo semplice."""
        
        if user_context:
            system_msg += f"\n\nDati utente:\n"
            
            # Aggiungi solo campi rilevanti
            relevant_fields = [
                ('fornitore', 'Fornitore attuale'),
                ('consumo_annuo_kwh', 'Consumi annui (kWh)'),
                ('totale_bolletta', 'Costo mensile (€)'),
                ('spesa_annua', 'Spesa annua (€)'),
                ('potenza_impegnata_kw', 'Potenza (kW)'),
                ('tipo_prezzo', 'Tipo prezzo')
            ]
            
            for key, label in relevant_fields:
                if user_context.get(key):
                    system_msg += f"- {label}: {user_context[key]}\n"
        
        full_messages = [{"role": "system", "content": system_msg}] + messages
        
        # Try a list of possible models (first from secrets then sensible fallbacks).
        # This avoids a hard crash if the configured model is not available on the OpenRouter instance.
        models_to_try = [
            st.secrets.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
            "gpt-4o-mini",
            "gpt-3.5-turbo"
        ]
        response = None
        last_exc = None
        for m in models_to_try:
            if not m:
                continue
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=full_messages,
                    max_tokens=500
                )
                # success -> stop trying other models
                break
            except Exception as e:
                # remember last exception and try next model
                last_exc = e
                # If model not found (404) or other errors, continue to next candidate
                continue

        if response is None:
            # All attempts failed: return a clear message for the user/operator
            err_msg = f"Errore AI: Impossibile contattare un modello valido. Ultimo errore: {str(last_exc)}"
            err_msg += " Verifica OPENROUTER_API_KEY e/O OPENROUTER_MODEL in .streamlit/secrets.toml."
            return err_msg

        # Extract content robustly (different SDK responses may differ)
        try:
            # Typical chat completions response shape
            return response.choices[0].message.content
        except Exception:
            try:
                # Some clients return .choices[0].text
                return response.choices[0].text
            except Exception:
                # As a last resort, stringify the response
                return str(response)
    
    except Exception as e:
        return f"Errore AI: {str(e)}"

# ============================================
# INTERFACCIA PRINCIPALE
# ============================================

st.title("⚡ Domitic - Energy Comparator")
st.markdown("*Trova le migliori offerte energetiche con l'aiuto dell'AI*")

# Sidebar
with st.sidebar:
    st.header("⚡ Energy Comparator")
    st.caption("Powered by AI & ARERA data")
    
    st.markdown("---")
    
    st.markdown("### 📋 Come funziona")
    st.info("""
    1️⃣ Carica la tua bolletta (PDF)  
    2️⃣ Analizziamo **30+ parametri**  
    3️⃣ Confrontiamo con **offerte ARERA PLACET**  
    4️⃣ Ti mostriamo il **risparmio reale**  
    5️⃣ Chiedi consigli al chatbot AI
    """)
    
    st.markdown("---")
    
    # Info dataset
    df_offerte, error = load_arera_offers()
    if df_offerte is not None:
        st.success(f"✅ **{len(df_offerte)}** offerte PLACET")
        
        # Statistiche dataset
        with st.expander("📊 Info Dataset"):
            n_fornitori = df_offerte['denominazione'].nunique()
            st.metric("Fornitori", n_fornitori)
            
            # Tipo offerte
            if 'tipo_offerta' in df_offerte.columns:
                tipo_counts = df_offerte['tipo_offerta'].value_counts()
                for tipo, count in tipo_counts.head(3).items():
                    st.text(f"{tipo}: {count}")
        
        st.caption("Fonte: Portale Offerte ARERA")
    else:
        st.error(f"❌ {error}")
    
    st.markdown("---")
    st.caption("🔒 **GDPR Compliant**")
    st.caption("Progetto UniTN - Computer Science")

# Check dataset
if df_offerte is None:
    st.error("⚠️ Impossibile caricare le offerte ARERA. Verifica che il file CSV sia presente.")
    st.stop()

# ============================================
# TAB LAYOUT
# ============================================

tab1, tab2, tab3 = st.tabs(["📄 Analisi Bolletta", "💬 Chat Assistente", "📊 Panoramica"])

# ============================================
# TAB 1: ANALISI BOLLETTA
# ============================================

with tab1:
    st.header("📄 Carica e analizza la tua bolletta")
    
    st.markdown("""
    Carica la tua ultima bolletta in formato PDF. Il nostro sistema avanzato estrae automaticamente:
    - ✓ Consumi mensili e annui (anche per fascia F1/F2/F3)
    - ✓ Costi dettagliati (energia, trasporto, oneri, imposte)
    - ✓ Potenza impegnata e tipo contratto
    - ✓ Fornitore attuale e caratteristiche offerta
    """)
    
    uploaded_file = st.file_uploader(
        "Seleziona file PDF della bolletta",
        type=['pdf'],
        help="Carica la tua ultima bolletta in formato PDF (max 10MB)"
    )
    
    if uploaded_file:
        with st.spinner("🔍 Analisi in corso... Questo può richiedere 10-20 secondi"):
            
            # Estrai testo
            text, error = extract_pdf_text(uploaded_file)
            
            if error:
                st.error(error)
                st.stop()
            
            if not text or len(text.strip()) < 50:
                st.error("Impossibile estrarre testo dalla bolletta. Verifica che il PDF non sia protetto o corrotto.")
                st.stop()
            
            # Parse con enhanced parser
            profilo = parse_bill_enhanced(text)
            
            # Salva in session state
            st.session_state['user_profile'] = profilo
            st.session_state['bill_analyzed'] = True
            
            # Mostra confidence
            confidence = profilo.get('confidence_score', 0)
            
            if confidence >= 0.7:
                st.success(f"✅ Bolletta analizzata con successo! (Affidabilità: {confidence*100:.0f}%)")
            elif confidence >= 0.4:
                st.warning(f"⚠️ Bolletta analizzata con affidabilità media ({confidence*100:.0f}%). Alcuni dati potrebbero essere stimati.")
            else:
                st.info(f"ℹ️ Alcuni dati sono stati stimati (Affidabilità: {confidence*100:.0f}%). I risultati sono indicativi.")
            
            # ====== PROFILO UTENTE ======
            st.markdown("### 📊 Il tuo profilo energetico")
            
            # Metriche principali
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Consumi Annui",
                    f"{profilo.get('consumo_annuo_kwh', 0):.0f} kWh",
                    help="Consumo stimato su 12 mesi"
                )
            
            with col2:
                spesa_annua = profilo.get('spesa_annua') or (profilo.get('totale_bolletta', 0) * 12)
                st.metric(
                    "Spesa Annua",
                    f"€{spesa_annua:.2f}",
                    help="Costo totale stimato annuale"
                )
            
            with col3:
                st.metric(
                    "Potenza",
                    f"{profilo.get('potenza_impegnata_kw', 3):.1f} kW",
                    help="Potenza contrattuale"
                )
            
            with col4:
                prezzo_medio = profilo.get('prezzo_medio_kwh')
                if prezzo_medio:
                    st.metric(
                        "Prezzo Medio",
                        f"€{prezzo_medio:.3f}/kWh",
                        help="Costo medio per kWh"
                    )
                else:
                    tipo = profilo.get('tipo_prezzo', 'Non rilevato')
                    st.metric(
                        "Tipo Contratto",
                        tipo.title() if tipo else "N/D"
                    )
            
            # ====== DETTAGLI COMPLETI ======
            with st.expander("📋 Dettagli completi bolletta", expanded=False):
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown("**Identificazione**")
                    if profilo.get('fornitore'):
                        st.text(f"Fornitore: {profilo['fornitore']}")
                    if profilo.get('numero_cliente'):
                        st.text(f"N° Cliente: {profilo['numero_cliente']}")
                    if profilo.get('periodo_fatturazione'):
                        st.text(f"Periodo: {profilo['periodo_fatturazione']}")
                    
                    st.markdown("**Consumi Dettagliati**")
                    if profilo.get('consumo_totale_periodo'):
                        st.text(f"Periodo: {profilo['consumo_totale_periodo']:.0f} kWh")
                    if profilo.get('consumo_mensile_kwh'):
                        st.text(f"Mensile: {profilo['consumo_mensile_kwh']:.0f} kWh")
                    
                    # Fasce orarie
                    if profilo.get('consumo_f1'):
                        st.markdown("**Fasce Orarie**")
                        st.text(f"F1 (picco): {profilo['consumo_f1']:.0f} kWh")
                        if profilo.get('consumo_f2'):
                            st.text(f"F2 (intermedio): {profilo['consumo_f2']:.0f} kWh")
                        if profilo.get('consumo_f3'):
                            st.text(f"F3 (fuori picco): {profilo['consumo_f3']:.0f} kWh")
                
                with col_b:
                    st.markdown("**Costi Dettagliati**")
                    if profilo.get('spesa_energia'):
                        st.text(f"Energia: €{profilo['spesa_energia']:.2f}")
                    if profilo.get('spesa_trasporto_gestione'):
                        st.text(f"Trasporto: €{profilo['spesa_trasporto_gestione']:.2f}")
                    if profilo.get('spesa_oneri_sistema'):
                        st.text(f"Oneri: €{profilo['spesa_oneri_sistema']:.2f}")
                    if profilo.get('accise'):
                        st.text(f"Accise: €{profilo['accise']:.2f}")
                    if profilo.get('iva'):
                        st.text(f"IVA: €{profilo['iva']:.2f}")
                    
                    st.markdown("**Caratteristiche Contratto**")
                    if profilo.get('tipo_prezzo'):
                        st.text(f"Tipo prezzo: {profilo['tipo_prezzo']}")
                    if profilo.get('tipo_mercato'):
                        st.text(f"Mercato: {profilo['tipo_mercato']}")
                    if profilo.get('tipo_tariffa'):
                        st.text(f"Tariffa: {profilo['tipo_tariffa']}")
                
                # Barra confidence
                st.markdown("**Affidabilità Estrazione**")
                st.progress(confidence, text=f"{profilo.get('campi_estratti', 0)}/{profilo.get('campi_totali', 30)} campi estratti ({confidence*100:.0f}%)")
            
            st.markdown("---")
            
            # ====== TROVA OFFERTE ======
            st.markdown("### 🎯 Offerte ARERA PLACET consigliate per te")
            
            with st.spinner("🔍 Confrontando con tutte le offerte ARERA PLACET disponibili..."):
                best_offers = find_best_offers(df_offerte, profilo, top_n=10)
            
            if not best_offers:
                st.warning("Nessuna offerta trovata nel database")
            else:
                # Statistiche rapide
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                
                with col_s1:
                    max_saving = max([o['risparmio_euro'] for o in best_offers])
                    st.metric(
                        "Risparmio Max",
                        f"€{max_saving:.2f}/anno",
                        delta=f"{max_saving/spesa_annua*100:.0f}%" if spesa_annua > 0 else None
                    )
                
                with col_s2:
                    avg_saving = sum([o['risparmio_euro'] for o in best_offers]) / len(best_offers)
                    st.metric("Risparmio Medio", f"€{avg_saving:.2f}/anno")
                
                with col_s3:
                    recommended = sum([1 for o in best_offers if o['consigliata']])
                    st.metric("Consigliate", recommended)
                
                with col_s4:
                    n_fisso = sum([1 for o in best_offers if o['tipo_prezzo'] == 'Fisso'])
                    st.metric("Prezzo Fisso", f"{n_fisso}/{len(best_offers)}")
                
                st.markdown("---")
                
                # ====== GRAFICO COMPARATIVO ======
                st.markdown("### 📊 Confronto visuale")
                
                df_viz = pd.DataFrame(best_offers[:8])  # Top 8 per leggibilità
                
                fig = go.Figure()
                
                # Linea costo attuale
                fig.add_hline(
                    y=spesa_annua,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="Costo attuale",
                    annotation_position="right"
                )
                
                # Barre offerte
                fig.add_trace(go.Bar(
                    x=df_viz['fornitore'],
                    y=df_viz['costo_totale_anno'],
                    marker_color=df_viz['risparmio_euro'].apply(
                        lambda x: '#10b981' if x > 0 else '#ef4444'
                    ),
                    text=df_viz['risparmio_euro'].apply(lambda x: f"€{x:.0f}"),
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>Costo: €%{y:.2f}<br>Risparmio: %{text}<extra></extra>'
                ))
                
                fig.update_layout(
                    title="Confronto costo annuo (Top 8 offerte)",
                    xaxis_title="Fornitore",
                    yaxis_title="Costo annuo (€)",
                    height=450,
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # ====== LISTA OFFERTE ======
                st.markdown("### 📋 Dettaglio offerte")
                
                for i, offer in enumerate(best_offers):
                    is_best = offer['consigliata']
                    
                    with st.container(border=True):
                        # Header
                        col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
                        
                        with col_h1:
                            if is_best and i < 3:
                                st.markdown("⭐ **CONSIGLIATA**")
                            st.markdown(f"### {offer['fornitore']}")
                            st.caption(offer['offerta'])
                            
                            # Badge tipo prezzo
                            tipo_color = "🟢" if offer['tipo_prezzo'] == 'Fisso' else "🟡"
                            st.caption(f"{tipo_color} {offer['tipo_prezzo']}")
                        
                        with col_h2:
                            delta_value = f"-€{offer['risparmio_euro']:.2f}" if offer['risparmio_euro'] > 0 else f"+€{abs(offer['risparmio_euro']):.2f}"
                            st.metric(
                                "Costo Annuo",
                                f"€{offer['costo_totale_anno']:.2f}",
                                delta=delta_value,
                                delta_color="normal" if offer['risparmio_euro'] > 0 else "inverse"
                            )
                        
                        with col_h3:
                            st.metric("Score", f"{offer['score']:.0f}/100")
                        
                        # Dettagli espandibili
                        with st.expander("📊 Dettagli completi offerta"):
                            detail_col1, detail_col2 = st.columns(2)
                            
                            with detail_col1:
                                st.markdown("**Componenti Costo**")
                                st.text(f"Prezzo energia: €{offer['prezzo_kwh']:.4f}/kWh")
                                st.text(f"Quota fissa: €{offer['costo_fisso_anno']:.2f}/anno")
                                st.text(f"Costo energia: €{offer['costo_energia_anno']:.2f}/anno")
                            
                            with detail_col2:
                                st.markdown("**Risparmio**")
                                st.text(f"Risparmio totale: €{offer['risparmio_euro']:.2f}/anno")
                                st.text(f"Percentuale: {offer['risparmio_pct']:.1f}%")
                                mensile = offer['risparmio_euro'] / 12
                                st.text(f"Mensile: €{mensile:.2f}")
                            
                            # Link offerta se disponibile
                            if offer.get('url_offerta') and offer['url_offerta'] != 'nan':
                                st.markdown(f"🔗 [Vai all'offerta sul Portale ARERA]({offer['url_offerta']})")
    
    else:
        # Nessun file caricato
        st.info("👆 Carica una bolletta per iniziare l'analisi")
        
        st.markdown("### 💡 Perché usare Energy Comparator?")
        
        col_why1, col_why2, col_why3 = st.columns(3)
        
        with col_why1:
            st.markdown("#### 🎯 Preciso")
            st.write("Estraiamo **30+ parametri** dalla tua bolletta per un confronto accurato")
        
        with col_why2:
            st.markdown("#### ⚡ Veloce")
            st.write("Analisi completa in **20 secondi** con AI avanzata")
        
        with col_why3:
            st.markdown("#### 💰 Conveniente")
            st.write("Risparmio medio di **€150/anno** cambiando fornitore")
        
        st.markdown("---")
        
        # Esempio risultati
        st.markdown("### 📊 Esempio analisi")
        st.image("https://via.placeholder.com/800x400/667eea/ffffff?text=Esempio+Confronto+Offerte", 
                 caption="Esempio di confronto visuale tra offerte", 
                 use_container_width=True)

# ============================================
# TAB 2: CHAT ASSISTENTE
# ============================================

with tab2:
    st.header("💬 Assistente AI")
    
    if not AI_AVAILABLE:
        st.error("⚠️ Chatbot non disponibile. Configura OPENROUTER_API_KEY in .streamlit/secrets.toml")
        st.stop()
    
    st.markdown("Chiedimi qualsiasi cosa su bollette energetiche, offerte ARERA PLACET, e risparmio!")
    
    # Inizializza chat
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Ciao! Sono il tuo assistente per l'energia. Posso aiutarti a capire la tua bolletta e trovare le migliori offerte ARERA PLACET. Come posso aiutarti oggi?"}
        ]
    
    # Mostra messaggi
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    
    # Suggerimenti
    if len(st.session_state.messages) <= 1:
        st.markdown("### 💡 Domande suggerite")
        
        suggestions = [
            "Quanto potrei risparmiare cambiando fornitore?",
            "Cosa significa prezzo fisso vs variabile?",
            "Come funziona il cambio fornitore in Italia?",
            "Quali sono le fasce orarie F1, F2, F3?",
            "Cos'è un'offerta PLACET?",
            "Conviene un contratto con vincolo di 24 mesi?",
            "Come leggere la mia bolletta?"
        ]
        
        cols = st.columns(2)
        for i, suggestion in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": suggestion})
                    st.rerun()

    # Input utente
    if prompt := st.chat_input("Scrivi la tua domanda..."):
        # Aggiungi messaggio utente
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Genera risposta
        with st.chat_message("assistant"):
            with st.spinner("Sto pensando..."):
                user_context = st.session_state.get('user_profile')
                response = chat_with_openrouter(st.session_state.messages, user_context)
                st.write(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
    

# ============================================
# TAB 3: PANORAMICA
# ============================================

with tab3:
    st.header("📊 Panoramica Mercato Energetico")
    
    # Statistiche database
    st.markdown("### 📈 Database Offerte ARERA PLACET")
    
    col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
    
    with col_stat1:
        n_fornitori = df_offerte['denominazione'].nunique()
        st.metric("Fornitori", n_fornitori)
    
    with col_stat2:
        st.metric("Offerte Totali", len(df_offerte))
    
    with col_stat3:
        if 'tipo_offerta' in df_offerte.columns:
            n_fisso = df_offerte['tipo_offerta'].str.contains('fisso|fiss', case=False, na=False).sum()
            st.metric("Offerte Fisso", n_fisso)
        else:
            st.metric("Offerte Fisso", "N/A")
    
    with col_stat4:
        if 'tipo_offerta' in df_offerte.columns:
            n_variabile = df_offerte['tipo_offerta'].str.contains('variabile|var', case=False, na=False).sum()
            st.metric("Offerte Variabile", n_variabile)
        else:
            st.metric("Offerte Variabile", "N/A")
    
    st.markdown("---")
    
    # Distribuzione fornitori
    st.markdown("### 🏢 Top 10 Fornitori per Numero di Offerte")
    
    top_fornitori = df_offerte['denominazione'].value_counts().head(10)
    
    fig_fornitori = px.bar(
        x=top_fornitori.values,
        y=top_fornitori.index,
        orientation='h',
        labels={'x': 'Numero Offerte', 'y': 'Fornitore'},
        title='Fornitori più attivi nel mercato PLACET'
    )
    fig_fornitori.update_layout(height=400)
    st.plotly_chart(fig_fornitori, use_container_width=True)
    
    st.markdown("---")
    
    # Range prezzi
    st.markdown("### 💰 Range Prezzi Mercato")
    
    # Calcola statistiche prezzi
    price_cols = ['p_vol_mono', 'p_vol_f1', 'p_vol_f2', 'p_vol_f3']
    available_prices = []
    
    for col in price_cols:
        if col in df_offerte.columns:
            prices = df_offerte[col].dropna()
            available_prices.extend(prices.tolist())
    
    if available_prices:
        col_price1, col_price2, col_price3 = st.columns(3)
        
        with col_price1:
            st.metric("Prezzo Min", f"€{min(available_prices):.4f}/kWh")
        
        with col_price2:
            st.metric("Prezzo Medio", f"€{sum(available_prices)/len(available_prices):.4f}/kWh")
        
        with col_price3:
            st.metric("Prezzo Max", f"€{max(available_prices):.4f}/kWh")
        
        # Istogramma prezzi
        fig_prices = px.histogram(
            x=available_prices,
            nbins=30,
            labels={'x': 'Prezzo (€/kWh)', 'y': 'Numero Offerte'},
            title='Distribuzione Prezzi Energia nel Mercato PLACET'
        )
        st.plotly_chart(fig_prices, use_container_width=True)
    
    st.markdown("---")
    
    # Info progetto
    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown("### 🎯 Obiettivo del Progetto")
        st.write("""
        Energy Comparator è nato per semplificare la scelta dell'offerta energia più conveniente. 
        
        **Il problema:** Le bollette energetiche sono complesse e confrontare manualmente 
        centinaia di offerte richiede ore.
        
        **La soluzione:** AI che analizza la tua bolletta in 20 secondi e ti mostra 
        esattamente quanto risparmi con ogni offerta.
        """)
        
        st.markdown("### 📊 Fonte Dati")
        st.write("""
        **Portale Offerte ARERA** - Database ufficiale che raccoglie tutte le offerte 
        PLACET (Prezzo Libero A Condizioni Equiparate di Tutela) del mercato italiano.
        
        Le offerte PLACET sono:
        - ✓ Standardizzate e confrontabili
        - ✓ Con condizioni contrattuali chiare
        - ✓ Pubblicate su portale ufficiale ARERA
        """)
    
    with col_info2:
        st.markdown("### 🛠️ Tecnologie Utilizzate")
        st.write("""
        **Stack Tecnologico:**
        - 🤖 **Enhanced Bill Parser**: AI per estrazione dati da PDF
        - 💬 **OpenRouter LLM**: Chatbot con modelli Llama 3.1
        - 📊 **Pandas**: Elaborazione dataset ARERA (CSV)
        - 📈 **Plotly**: Visualizzazioni interattive
        - 🎨 **Streamlit**: Framework web app Python
        - 📄 **pdfplumber**: Lettura PDF bollette
        """)
        
        st.markdown("### 🔒 Privacy & Sicurezza")
        st.write("""
        **GDPR Compliant:**
        - ✅ Nessun dato salvato su server
        - ✅ Analisi bolletta locale
        - ✅ Nessun tracking o profilazione
        - ✅ API LLM con modelli open source
        - ✅ Codice open source su GitHub
        """)
    
    st.markdown("---")
    
    # Roadmap
    st.markdown("### 🚀 Roadmap Futura")
    
    col_road1, col_road2 = st.columns(2)
    
    with col_road1:
        st.markdown("**✅ Implementato (v1.0)**")
        st.write("""
        - Parser avanzato bollette (30+ campi)
        - Confronto con database ARERA PLACET
        - Calcolo risparmio personalizzato
        - Chatbot AI assistenza
        - Visualizzazioni interattive
        """)
    
    with col_road2:
        st.markdown("**🔮 Prossime Features (v2.0)**")
        st.write("""
        - OCR per bollette scannerizzate
        - Parser specifici per ogni fornitore
        - Alert email nuove offerte
        - Storico consumi e trend
        - App mobile iOS/Android
        - API pubblica per sviluppatori
        """)
    
    st.markdown("---")
    
    # Team & Contatti
    st.markdown("### 👥 Team & Contatti")
    
    st.info("""
    **Progetto Universitario** - Università degli Studi di Trento  
    **Corso:** Innovation and Business ICT  
    **Anno Accademico:** 2024/2025  
    
    **Team:**  
    - [Nome Studente 1] - Backend & Parser AI
    - [Nome Studente 2] - Frontend & UX
    - [Nome tuo collega] - Chatbot & OpenRouter Integration
    
    📧 **Contatti:** energy.comparator@studenti.unitn.it  
    🐙 **GitHub:** [github.com/rrikiliba/domotic__](https://github.com/rrikiliba/domotic__)  
    📊 **Demo Live:** [domotic-chat.streamlit.app](https://domotic-chat.streamlit.app)
    """)
    
    st.markdown("---")
    
    # Disclaimer
    st.caption("""
    **Disclaimer:** Questo tool è sviluppato a scopo educativo nell'ambito del corso 
    Innovation and Business ICT presso UniTN. I calcoli di risparmio sono stime indicative 
    basate sui dati del Portale Offerte ARERA. Per informazioni ufficiali e vincolanti, 
    consultare direttamente il sito del fornitore o il Portale Offerte ARERA.
    """)

# ============================================
# FOOTER
# ============================================

st.markdown("---")

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption("⚡ **Energy Comparator v1.0**")

with footer_col2:
    st.caption("📊 Dati: Portale Offerte ARERA")

with footer_col3:
    st.caption("🎓 UniTN - Computer Science 2024/25")