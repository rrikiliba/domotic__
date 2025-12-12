import streamlit as st
import streamlit_analytics as sta
from openrouter import OpenRouter
import requests
from elements import footer, header
from utils import model_name_format, get_user_cache

sta.start_tracking(load_from_json='streamlit_analytics/data.json')

pages = [
    st.Page('./pages/homepage.py', title='Visita la homepage', icon='💡', url_path='home', default=True),
    st.Page('./pages/analyze.py', title='Analizza la tua bolletta', icon='📑', url_path='analyze'),
    st.Page('./pages/chat.py', title='Chatta con Domitico', icon='💬', url_path='chat'),
    st.Page('./pages/overview.py', title='Le offerte', icon='📊', url_path='overview'),
    st.Page('./pages/smart_home.py', title='La tua smart home', icon='🏠', url_path='smart_home'),
    st.Page('./pages/analytics.py', title='Analytics del sito', icon='🔧', url_path='analytics')
]

if 'OPENROUTER_API_KEY' not in st.secrets or st.secrets['OPENROUTER_API_KEY'] is None: 
    st.error("La chiave API di OpenRouter manca dai segreti dell'app! Si prega di contattare un amministratore.", icon="🗝️")
    st.stop()
elif 'openai_client' not in st.session_state:
    st.session_state.client = OpenRouter(api_key=st.secrets['OPENROUTER_API_KEY'])

cache = get_user_cache() 

page = st.navigation(pages, position='sidebar' if 'homepage_visited' in cache and cache['homepage_visited'] else 'hidden')
    
st.set_page_config(page_title="Domotic", page_icon="", layout='centered' if page.url_path == 'chat' else 'wide')

# Load csv 
# if 'csv_content' not in cache:
#     cache['csv_content'] = None
#     with open('assets/offers/PO_Offerte_E_PLACET_20251113.csv') as csv_file:
#         cache['csv_content'] = csv_file.read()

# Initialize pdf
if 'pdf_content' not in cache:
    cache['pdf_content'] = None

if 'available_models' not in cache:

    try: 
        import json
        with open('available_models.json', 'r') as f:   
            cache['available_models'] = json.load(f)
    except:
        models = requests.get('https://openrouter.ai/api/v1/models/user', headers={'Authorization': f'Bearer {st.secrets["OPENROUTER_API_KEY"]}'}).json()['data']
        models = list(filter(lambda model:model['id'].endswith(':free'), models))
        cache['available_models'] = models

if 'homepage_visited' in cache and cache['homepage_visited']:
    with st.sidebar:
        # Display model switch
        with st.container(border=True):
            if 'selected_model' not in cache:
                for model in cache['available_models']:
                    if 'gpt-oss' in model['name']: 
                        cache['selected_model'] = model
                        break
                else:
                    cache['selected_model'] = cache['available_models'][0]

            selected_model = cache['selected_model']
            index = cache['available_models'].index(selected_model)
            help = f"""La seguente descrizione viene fornita direttamente dai proprietari del modello selezionato:  
              
{selected_model['description'] if 'description' in selected_model else 'nessuna descrizione fornita.'}"""
            def change_model():
                cache['selected_model'] = st.session_state['model_selectbox']
            st.selectbox('Quale LLM dovrebbe essere utilizzato come base?', cache['available_models'], format_func=model_name_format, index=index, help=help, key='model_selectbox', on_change=change_model)
            if st.session_state['model_selectbox'] != cache['selected_model']:
                st.rerun()
            # if st.button('data print'):
            #     st.json(cache['selected_model'])

        with st.container(border=True):
            st.write('Dicci com\'è stata la tua esperienza:')
            rating = st.feedback('faces', width='stretch')
            
        if rating is not None:
            st.info('Grazie per il tuo feedback, apprezziamo molto la tua opinione.')


footer.load()
header.load()
page.run() 
sta.stop_tracking(save_to_json='streamlit_analytics/data.json')

