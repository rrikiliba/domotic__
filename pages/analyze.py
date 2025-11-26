import streamlit as st
from utils import model_name_format, pdf_request, Cache
import json

cache = Cache()

def upload_bill():
    if 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        cache['pdf_model'] = cache['selected_model']
        try:
            res = pdf_request(cache['pdf_model'], st.session_state['pdf_file'].getvalue())
            cache['pdf_content'] = json.dumps(res)
        except KeyError:
            st.error('Our chatbot couldn\'t analyze your pdf.')
        except Exception as e:
            st.error(e)
        print(cache['pdf_content'])

with st.container(border=True):
    st.file_uploader('Upload your bill for more personalized results', accept_multiple_files=False, key='pdf_file', on_change=upload_bill, type='pdf')
    if 'pdf_model' in cache and cache['pdf_model'] is not None and 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.write(f':gray[*this file has been analyzed by {model_name_format(cache["pdf_model"]).split(", from")[0]}*]')