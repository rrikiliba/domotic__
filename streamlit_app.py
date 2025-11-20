import streamlit as st
from openrouter import OpenRouter
from utils import model_name_format
import requests

pages = [
    st.Page('./pages/analyze.py', title='Analyze your electricity bill', icon='📑', url_path='analyze', default=True),
    st.Page('./pages/chat.py', title='Chat with Domitico', icon='💬', url_path='chat'),
    st.Page('./pages/overview.py', title='Your bill\'s data', icon='📊', url_path='overview'),
    st.Page('./pages/smart_home.py', title='Your smart home data', icon='🏠', url_path='smart_home'),
]

if 'OPENROUTER_API_KEY' not in st.secrets or st.secrets['OPENROUTER_API_KEY'] is None: 
    st.error("The OpenRouter API key is missing from the app's secrets! Please contact an administrator.", icon="🗝️")
    st.stop()
elif 'openai_client' not in st.session_state:
    st.session_state.client = OpenRouter(api_key=st.secrets['OPENROUTER_API_KEY'])

page = st.navigation(pages)
st.set_page_config(page_title="Domotic__", page_icon="", layout='centered' if page.url_path == 'chat' else 'wide')

# Load csv 
if 'csv_content' not in st.session_state:
    st.session_state['csv_content'] = None
    # TODO: obtain and manage latest offers directly from portale offerte
    with open('PO_Offerte_E_PLACET_20251113.csv') as csv_file:
        st.session_state['csv_content'] = csv_file.read()

# Initialize pdf
if 'pdf_content' not in st.session_state:
    st.session_state['pdf_content'] = None

# Create a session state variable to store the chat messages. This ensures that the
# messages persist across reruns.
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            'role': 'assistant',
            'content': 'Hi there! My name is Domitico and I\'m here to help. Feel free to ask me anything about your electricity bill :smile:'
        }
    ]

with st.sidebar:
    # Display model switch
    if 'available_models' not in st.session_state:
        models = requests.get('https://openrouter.ai/api/v1/models/user', headers={'Authorization': f'Bearer {st.secrets["OPENROUTER_API_KEY"]}'}).json()['data']
        models = list(filter(lambda model:model['id'].endswith(':free'), models))
        st.session_state['available_models'] = models

    with st.container(border=True):
        cols = st.columns([0.8, 0.2], vertical_alignment='bottom')
        with cols[0]:
            if 'selected_model' not in st.session_state:
                for model in st.session_state['available_models']:
                    if 'gpt-oss' in model['name']: 
                        selected_model = model
                        break
                else:
                    selected_model = st.session_state['available_models'][0]
                st.session_state['selected_model'] = selected_model
            else:
                selected_model = st.session_state['selected_model']
            index = st.session_state['available_models'].index(selected_model)
            st.selectbox('Which LLM should be used as base?', st.session_state['available_models'], format_func=model_name_format, index=index, key='selected_model')
        with cols[1]:
            with st.popover('?', type='tertiary', use_container_width=True, disabled='description' not in st.session_state['selected_model'] or st.session_state['selected_model']['description'] is None or len(st.session_state['selected_model']['description']) == 0):
                if 'description' in st.session_state['selected_model']:
                    st.write(st.session_state['selected_model']['description'])

    with st.container(border=True):
        st.write('Tell us how\'s your experience been:')
        rating = st.feedback('faces', width='stretch')
        # not collected for now 

    if rating is not None:
        st.info('Thank you for your feedback, we really value your opinion.')

page.run() 
