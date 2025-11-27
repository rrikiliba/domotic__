import streamlit as st
import streamlit_analytics
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
    my_bill_data['price_no_tv'] = float(bill_json.get("price_with_tv",100000))-float(bill_json.get("tv_price",0))
    my_bill_data['potenza_impegnata'] = bill_json.get("potenza_impegnata", 100000)
    my_bill_data['fixed_cost'] = bill_json.get("fixed_cost", "Unknown") 
    my_bill_data['offer_code'] = bill_json.get("offer_code", "Unknown") 
    
        
    other_bill_data = {}
    other_bill_data['avg_price'] = 100.0
    with st.container(border=True):
        # Header
        col_h1, col_h2, col_h3 = st.columns([2, 1,1])
        
        with col_h1:
            st.markdown("Ecco i tuoi dati, rispetto ad offerte presenti")
            st.markdown("Codice offerta:"+my_bill_data['offer_code'])


        with col_h2:
            compared_to_avg_price =  my_bill_data['price_no_tv'] - other_bill_data['avg_price']
            delta_value = f"-€{compared_to_avg_price:.2f}" if compared_to_avg_price < 0 else f"+€{abs(compared_to_avg_price):.2f}"
            st.metric(
                "Costo mensile",
                f"€{my_bill_data['price_no_tv']:.2f}",
                delta=delta_value,
                delta_color="inverse" if compared_to_avg_price < 0 else "normal",
                help  = "Costo mensile senza includere TV"
            )

            
        with col_h3:
            st.metric(
                "Costo fisso",
                f"€{my_bill_data["fixed_cost"]}",
                help  = "Costo fisso della bolletta"
            )

with st.container(border=True):
    with streamlit_analytics.track():
        st.file_uploader('Upload your bill for more personalized results', accept_multiple_files=False, key='pdf_file', on_change=upload_bill, type='pdf')
    if 'pdf_model' in cache and cache['pdf_model'] is not None and 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.write(f':gray[*this file has been analyzed by {model_name_format(cache["selected_model"]).split(", from")[0]}*]')
        show_info_about_bill()