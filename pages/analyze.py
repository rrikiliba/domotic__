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

def show_info_about_bill() -> dict:
    bill_json:dict = json.loads(cache['pdf_content'])
    my_bill_data:dict = {}
    my_bill_data['customer_type'] = bill_json.get("client_type", "Unknown")
    my_bill_data['annual_consume'] = bill_json.get("annual_consume", 100000)
    my_bill_data['city'] = str(bill_json.get("city", "Unknown")).capitalize()
    my_bill_data['month_cost'] = float(bill_json.get("price_with_tv",100000))
    my_bill_data['extimate_annual_cost'] = bill_data['month_cost']*12
    my_bill_data['price_no_tv'] = float(bill_json.get("price_with_tv",100000))-float(bill_json.get("tv_price",0))
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
                help  = "Prezzo variabile + quota fissa"
            )

            
        with col_h3:
            st.metric(
                "Di cui costo fisso",
                f"€{my_bill_data["fixed_cost"]:.2f}",
                help  = "Costo fisso della bolletta"
            )
    return my_bill_data


def show_compared_to_other_bills(my_bill_data: dict):
    df_offerte, error = ao.load_arera_offers()
    with st.spinner("🔍 Confrontando con tutte le offerte ARERA PLACET disponibili..."):
        best_offers = ao.find_best_offers(df_offerte, my_bill_data, top_n=10)
        
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
                    delta=f"{max_saving/bill_data['extimate_annual_cost']*100:.0f}%" if bill_data['extimate_annual_cost'] > 0 else None
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

with st.container(border=True):
    show_compared_to_other_bills({})
    with streamlit_analytics.track():
        st.file_uploader('Upload your bill for more personalized results', accept_multiple_files=False, key='pdf_file', on_change=upload_bill, type='pdf')
    if 'pdf_model' in cache and cache['pdf_model'] is not None and 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.write(f':gray[*this file has been analyzed by {model_name_format(cache["selected_model"]).split(", from")[0]}*]')
        bill_data = show_info_about_bill()
        show_compared_to_other_bills(bill_data)