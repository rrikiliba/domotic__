import pandas as pd

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


def load_arera_offers():
    """Carica offerte ARERA con cache"""
    try:
        #FIXME per diverse versioni del file CSV
        df = pd.read_csv('./assets/offers/PO_Offerte_E_PLACET_20251113.csv')
        
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


def find_best_offers(df:pd.DataFrame | None, my_bill_data, top_n=10) -> list:
    """
    Trova migliori offerte dal CSV ARERA
    Usa colonne reali: denominazione, nome_offerta, p_fix_*, p_vol_*
    """

    if df is None or df.empty:
        return []
    
    consumi_annui = my_bill_data['annual_consume']
    
    # Usa totale bolletta se disponibile, altrimenti stima
#    if my_bill_data.get('totale_bolletta'):
#        spesa_mensile = my_bill_data['totale_bolletta']
#        spesa_attuale = spesa_mensile * 12
#    else:
#        spesa_attuale = my_bill_data.get('spesa_annua', 600)
#    
    # Check se utente ha fasce orarie (per calcolo più preciso)
#    user_has_fasce = all([ #TODO
#        my_bill_data.get('consumo_f1'),
#        my_bill_data.get('consumo_f2'),
#        my_bill_data.get('consumo_f3')
#    ])

    user_has_fasce = False
    
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
            risparmio = my_bill_data['estimated_annual_cost'] - costo_totale_anno
            risparmio_pct = (risparmio / my_bill_data['estimated_annual_cost'] * 100) if my_bill_data['estimated_annual_cost'] > 0 else 0
            
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
