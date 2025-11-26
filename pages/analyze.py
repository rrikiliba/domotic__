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

with st.container(border=True):
    st.file_uploader('Upload your bill for more personalized results', accept_multiple_files=False, key='pdf_file', on_change=upload_bill, type='pdf')
    if 'pdf_model' in st.session_state and st.session_state['pdf_model'] is not None and 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.write(f':gray[*this file has been analyzed by {model_name_format(st.session_state["selected_model"]).split(", from")[0]}*]')