from typing import Any
import streamlit as st
import streamlit_analytics
from utils import analysis_offerte as ao
from utils import model_name_format, pdf_request, Cache 
import json

cache = Cache()

def upload_bill():
    if 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        cache['pdf_model'] = cache['selected_model']
        try:
            with st.spinner(text="Analyzing your bill. Please wait.", show_time=True):
                res = pdf_request(cache['pdf_model'], st.session_state['pdf_file'].getvalue())
                cache['pdf_content'] = json.dumps(res)
        except KeyError:
            st.error('Our chatbot couldn\'t analyze your pdf.')
        except Exception as e:
            st.error(e)
        with open("./parsed_bill.json", "w+") as f:
            f.write(json.dumps(json.loads(cache['pdf_content']), indent=4))

def show_info_about_bill():
    bill_json:dict = json.loads(cache['pdf_content'])
    my_bill_data:dict = {}
    my_bill_data['customer_type'] = bill_json.get("client_type", "Unknown")
    my_bill_data['annual_consume'] = bill_json.get("annual_consume", 100000)
    my_bill_data['city'] = str(bill_json.get("city", "Unknown")).capitalize()
    my_bill_data['month_cost'] = float(bill_json.get("total_price",100000))
    my_bill_data['estimated_annual_cost'] = my_bill_data['month_cost']*12
    my_bill_data['price_no_tv'] = float(bill_json.get("total_price",100000))-float(bill_json.get("tv_price",0))
    my_bill_data['potenza_impegnata'] = bill_json.get("potenza_impegnata", 100000)
    my_bill_data['offer_code'] = bill_json.get("offer_code", "Unknown") 
    my_bill_data['variable_cost']=bill_json.get('variable_cost', 10000)

    my_bill_data['fixed_cost'] = my_bill_data['price_no_tv']-bill_json.get("taxes", 1000)-my_bill_data['variable_cost']
    

    with st.container(border=True):
        # Header
        col_h1, col_h2, col_h3 = st.columns([2, 1,1])
        
        with col_h1:
            st.markdown("Ecco i tuoi dati")
            st.markdown(f"Codice offerta: :gray[*{my_bill_data['offer_code']}*]")


        with col_h2:
            st.metric(
                "Costo mensile (no TV)",
                f"€{my_bill_data['price_no_tv']:.2f}",
                help  = f"Prezzo variabile(€{my_bill_data['variable_cost']:.2f}) + quota fissa (€{my_bill_data['fixed_cost']:.2f})"
            )

            
        with col_h3:
            st.metric(
                "Costo annuo (stima)",
                "€{:.2f}".format(my_bill_data["estimated_annual_cost"])
            )
    return my_bill_data

def show_offers(best_offers: list):
    st.markdown("### 📋 Dettaglio offerte")
    
    for i, offer in enumerate(best_offers[:10]):
        is_best = offer['consigliata']
        
        with st.container(border=True):
            # Header
            col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
            
            with col_h1:
                if is_best and i < 3:
                    st.markdown("⭐ **CONSIGLIATA**")
                st.markdown(f"### #{i+1} | {offer['fornitore']}")
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



def show_compared_to_other_bills(my_bill_data: dict) -> list:
    df_offerte, error = ao.load_arera_offers()
    best_offers = ao.find_best_offers(df_offerte, my_bill_data, top_n=-1)
    if len(best_offers) == 0:
        st.warning("Nessuna offerta migliore trovata nel database")
    else:
        # Statistiche rapide
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        
        with col_s1:
            max_saving = max([o['risparmio_euro'] for o in best_offers])
            st.metric(
                "Risparmio Max",
                f"€{max_saving:.2f}/anno",
                delta=f"{max_saving/my_bill_data['estimated_annual_cost']*100:.0f}%" if my_bill_data['estimated_annual_cost'] > 0 else None
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
    return best_offers

with st.container(border=True):
    with streamlit_analytics.track():
        st.file_uploader('Upload your bill for more personalized results', accept_multiple_files=False, key='pdf_file', on_change=upload_bill, type='pdf')
    if 'pdf_model' in cache and cache['pdf_model'] is not None and 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.write(f':gray[*this file has been analyzed by {model_name_format(cache["selected_model"]).split(", from")[0]}*]')
        bill_data = show_info_about_bill()
        best_offers = show_compared_to_other_bills(bill_data)
        st.markdown("---")
        show_offers(best_offers)