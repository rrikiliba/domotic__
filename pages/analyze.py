import streamlit as st
from utils import model_name_format, pdf_request
import json

def json_has_correct_field(json_bill:dict, fields_to_check: list[str]) -> bool:
    try:
        return all([json_bill[field] for field in fields_to_check])
    except:
        return False

def upload_bill():
    if 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.session_state['pdf_model'] = st.session_state['selected_model']
        try:
            with st.spinner(text="Analyzing your bill. Please wait.", show_time=True):
                while True:
                    fields_to_extract = [
                        "Tipologia di cliente",
                        "Consumo annuo",
                        "Comune di fornitura",
                        "Prezzo bolletta",
                        "Importo canone televisione per uso privato",
                        "Potenza impegnata"
                        ]
                    res = pdf_request(st.session_state['pdf_model'], st.session_state['pdf_file'].getvalue(), fields_to_extract)
                    if json_has_correct_field(res, fields_to_extract):
                        st.session_state['pdf_content'] = json.dumps(res)
                        break

            st.toast("Bill succesfully analyzed", duration=1)
        except KeyError:
            st.error('Our chatbot couldn\'t analyze your pdf.')
        except Exception as e:
            st.error(e)
        with open("./parsed_bill.json", "w+") as f:
            f.write(json.dumps(json.loads(st.session_state['pdf_content']), indent=4))

def show_info_about_bill():
    bill_json:dict = json.loads(st.session_state['pdf_content'])
    my_bill_data:dict = {}
    my_bill_data['customer_type'] = bill_json.get("Tipologia di cliente", "Unknown") 
    my_bill_data['annual_consume'] = bill_json.get("Consumo annuo", 100000)
    my_bill_data['city'] = str(bill_json.get("Comune di fornitura", "Unknown")).capitalize()
    my_bill_data['price_no_tv'] = float(bill_json.get("Prezzo bolletta",100000))-float(bill_json.get("Importo canone televisione per uso privato",0))
    my_bill_data['potenza_impegnata'] = bill_json.get("Potenza impegnata", 100000)
        
    other_bill_data = {}
    other_bill_data['avg_price'] = 100.0
    with st.container(border=True):
        # Header
        col_h1, col_h2 = st.columns([2, 1])
        
        with col_h1:
            st.markdown("Ecco i tuoi dati")
            st.markdown("<Dati da mostrare>")


        with col_h2:
            compared_to_avg_price =  my_bill_data['price_no_tv'] - other_bill_data['avg_price']
            delta_value = f"-€{compared_to_avg_price:.2f}" if compared_to_avg_price < 0 else f"+€{abs(compared_to_avg_price):.2f}"
            st.metric(
                "Costo mensile",
                f"€{my_bill_data['price_no_tv']:.2f}",
                delta=delta_value,
                delta_color="normal" if compared_to_avg_price > 0 else "inverse",
                help  = "Costo mensile senza includere TV"
            )

with st.container(border=True):
    st.file_uploader('Upload your bill for more personalized results', accept_multiple_files=False, key='pdf_file', on_change=upload_bill, type='pdf')
    if 'pdf_model' in st.session_state and st.session_state['pdf_model'] is not None and 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.write(f':gray[*this file has been analyzed by {model_name_format(st.session_state["selected_model"]).split(", from")[0]}*]')
        show_info_about_bill()