import streamlit as st
from openrouter import OpenRouter
import requests
from utils import model_name_format, Cache
from streamlit.components.v1 import html

html('''<script async src="https://www.googletagmanager.com/gtag/js?id=G-GNPF46MXLJ"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());  
          gtag('config', 'G-GNPF46MXLJ');
        </script>''')

pages = [
    st.Page('./pages/homepage.py', title='Visit our homepage', icon='💡', url_path='home', default=True),
    st.Page('./pages/analyze.py', title='Analyze your electricity bill', icon='📑', url_path='analyze'),
    st.Page('./pages/chat.py', title='Chat with Domitico', icon='💬', url_path='chat'),
    st.Page('./pages/overview.py', title='Offers overview', icon='📊', url_path='overview'),
    st.Page('./pages/smart_home.py', title='Your smart home data', icon='🏠', url_path='smart_home'),
]

if 'OPENROUTER_API_KEY' not in st.secrets or st.secrets['OPENROUTER_API_KEY'] is None: 
    st.error("The OpenRouter API key is missing from the app's secrets! Please contact an administrator.", icon="🗝️")
    st.stop()
elif 'openai_client' not in st.session_state:
    st.session_state.client = OpenRouter(api_key=st.secrets['OPENROUTER_API_KEY'])

cache = Cache() 

if 'homepage_visited' in cache and cache['homepage_visited']:
    page = st.navigation(pages[1:])
else:
    page = st.navigation(pages, position='hidden')
    
st.set_page_config(page_title="Domotic__", page_icon="", layout='centered' if page.url_path == 'chat' else 'wide')

# Load csv 
if 'csv_content' not in cache:
    cache['csv_content'] = None
    # TODO: obtain and manage latest offers directly from portale offerte
    with open('assets/offers/PO_Offerte_E_PLACET_20251113.csv') as csv_file:
        cache['csv_content'] = csv_file.read()

# Initialize pdf
if 'pdf_content' not in cache:
    cache['pdf_content'] = None

if 'messages' not in cache:
    cache['messages'] = [
        {
            'role': 'assistant',
            'content': 'Hi there! My name is Domitico and I\'m here to help. Feel free to ask me anything about your electricity bill :smile:'
        }
    ]

if 'homepage_visited' in cache and cache['homepage_visited']:
    with st.sidebar:
        # Display model switch
        if 'available_models' not in cache:
            models = requests.get('https://openrouter.ai/api/v1/models/user', headers={'Authorization': f'Bearer {st.secrets["OPENROUTER_API_KEY"]}'}).json()['data']
            models = list(filter(lambda model:model['id'].endswith(':free'), models))
            cache['available_models'] = models

        with st.container(border=True):
            cols = st.columns([0.8, 0.2], vertical_alignment='bottom')
            with cols[0]:
                if 'selected_model' not in cache:
                    for model in cache['available_models']:
                        if 'gpt-oss' in model['name']: 
                            selected_model = model
                            break
                    else:
                        selected_model = cache['available_models'][0]
                else:
                    selected_model = cache['selected_model']
                index = cache['available_models'].index(selected_model)
                cache['selected_model'] = st.selectbox('Which LLM should be used as base?', cache['available_models'], format_func=model_name_format, index=index)
            with cols[1]:
                with st.popover('?', type='tertiary', use_container_width=True, disabled='description' not in cache['selected_model'] or cache['selected_model']['description'] is None or len(cache['selected_model']['description']) == 0):
                    if 'description' in cache['selected_model']:
                        st.write(cache['selected_model']['description'])

        with st.container(border=True):
            st.write('Tell us how\'s your experience been:')
            rating = st.feedback('faces', width='stretch')
            
        # not collected for now 
        if rating is not None:
            st.info('Thank you for your feedback, we really value your opinion.')

from elements import footer, header


header.load()
page.run() 
footer.load()

