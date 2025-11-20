import streamlit as st
from utils import model_name_format, pdf_request
import json

def upload_bill():
    if 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.session_state['pdf_model'] = st.session_state['selected_model']
        try:
            res = pdf_request(st.session_state['pdf_model'], st.session_state['pdf_file'].getvalue())
            st.session_state['pdf_content'] = json.dumps(res)
        except KeyError:
            st.error('Our chatbot couldn\'t analyze your pdf.')
        except Exception as e:
            st.error(e)
        print(st.session_state['pdf_content'])

with st.container(border=True):
    st.file_uploader('Upload your bill for ore personalized results', accept_multiple_files=False, key='pdf_file', on_change=upload_bill, type='pdf')
    if 'pdf_model' in st.session_state and st.session_state['pdf_model'] is not None and 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.write(f':gray[*this file has been analyzed by {model_name_format(st.session_state["selected_model"]).split(", from")[0]}*]')