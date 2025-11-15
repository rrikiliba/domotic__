from openai import OpenAI
import streamlit as st
import requests
import base64
import json

def encode_pdf():
    return base64.b64encode(st.session_state['pdf_file'].getvalue()).decode('utf-8')

def openrouter_request(**kwargs):
    return requests.post(
        url='https://openrouter.ai/api/v1/chat/completions', 
        headers={
            "Authorization": f"Bearer {st.secrets['OPENROUTER_API_KEY']}",
            "Content-Type": "application/json"
        }, 
        json=kwargs
    )

def model_name_format_func(item):
    item = item['name'].replace(' (free)', '').split(': ')
    if len(item) > 1:
        return f'{item[1]}, from {item[0]}'
    else: 
        return item[0]

def upload_bill():
    if 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
        st.session_state['pdf_model'] = st.session_state['selected_model']
        res = openrouter_request(
        model=st.session_state['pdf_model']['id'],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Create a summary of the most important information about this electricity bill, in syntactically correct json format."
                    },
                    {
                        "type": "file",
                        "file": {
                            "filename": "document.pdf",
                            "file_data": f"data:application/pdf;base64,{encode_pdf()}"
                        }
                    },
                ]
            }
        ],
        stream=False,
        response_format={"type": "json_object"},
        plugins=[
            {
                "id": "file-parser",
                "pdf": {
                    "engine": "pdf-text",
                },
            },
        ],
        ).json()
        st.session_state['pdf_content'] = json.dumps(res)

if 'OPENROUTER_API_KEY' not in st.secrets or st.secrets['OPENROUTER_API_KEY'] is None: 
    st.error("The OpenRouter API key is missing from the app's secrets! Please contact an administrator.", icon="🗝️")
    st.stop()
elif 'openai_client' not in st.session_state:
    st.session_state.openai_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=st.secrets['OPENROUTER_API_KEY']
            )
    
# Load csv 
if 'csv_content' not in st.session_state:
    st.session_state['csv_content'] = None
    # TODO: obtain and manage latest offers directly from portale offerte
    with open('PO_Offerte_E_PLACET_20251113.csv') as csv_file:
        st.session_state['csv_content'] = csv_file.read()

# Initialize pdf
if 'pdf_content' not in st.session_state:
    st.session_state['pdf_content'] = None

# Show title and description.
st.title("Welcome to Domotic__")

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
    st.title('Help us to help you:')

    # Display model switch
    if 'available_models' not in st.session_state:
        models = requests.get('https://openrouter.ai/api/v1/models/user', headers={'Authorization': f'Bearer {st.secrets["OPENROUTER_API_KEY"]}'}).json()['data']
        models = list(filter(lambda model:model['id'].endswith(':free'), models))
        st.session_state['available_models'] = models
    
    if 'selected_model' not in st.session_state:
        st.session_state['selected_model'] = st.session_state['available_models'][0]

    with st.container(border=True):
        cols = st.columns([0.8, 0.2], vertical_alignment='bottom')
        with cols[0]:
            index = st.session_state['available_models'].index(st.session_state['selected_model'])
            st.selectbox('Which LLM should be used as base?', st.session_state['available_models'], format_func=model_name_format_func, index=index, key='selected_model')
        with cols[1]:
            with st.popover(':material/question_mark:', use_container_width=True, disabled='description' not in st.session_state['selected_model'] or st.session_state['selected_model']['description'] is None or len(st.session_state['selected_model']['description']) == 0):
                if 'description' in st.session_state['selected_model']:
                    st.write(st.session_state['selected_model']['description'])

    with st.container(border=True):
        st.file_uploader('Upload your bill for ore personalized results', accept_multiple_files=False, key='pdf_file', on_change=upload_bill, type='pdf')
        if 'pdf_model' in st.session_state and st.session_state['pdf_model'] is not None and 'pdf_file' in st.session_state and st.session_state['pdf_file'] is not None:
            st.write(f':gray[*this file has been analyzed by {model_name_format_func(st.session_state["selected_model"]).split(", from")[0]}*]')

    with st.container(border=True):
        st.write('Give us your opinion on this chat:')
        rating = st.feedback('faces', width='stretch')
        # not collected for now 

    if rating is not None:
        st.info('Thank you for your feedback, we really value your opinion.')

# Display the existing chat messages via `st.chat_message`.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field to allow the user to enter a message. This will display
# automatically at the bottom of the page.
if prompt := st.chat_input('Ask your questions here:'):

    # Store and display the current prompt.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)


    messages = [{
                "role": m["role"], 
                "content": m["content"]
            } for m in st.session_state.messages]
    
    if st.session_state['csv_content'] is not None:
        csv_messages = [
            {
                'role': 'system',
                'content': 'Use the csv data about available offers from the following csv file to aid in your responses.'
            },
            {
                'role': 'system',
                'content': st.session_state['csv_content']
            }
        ]
        messages = csv_messages + messages

    if st.session_state['pdf_content'] is not None:
        pdf_messages = [
            {
                'role': 'system',
                'content': 'Use the json data about the user\'s electricity bill from the following json file to provide ad hoc suggestions.'
            },
            {
                'role': 'system',
                'content': st.session_state['pdf_content']
            }
        ]
        messages = pdf_messages + messages

    # Generate a response using the OpenAI API.
    stream = st.session_state.openai_client.chat.completions.create(
        model=st.session_state['selected_model']['id'],
        messages=[{
                "role": "system",
                "content": "You are a helpful assistant. You are expert on electricity bills, power consumption etc. The user may ask questions related to this area."
            },
            {
                "role": "system",
                "content": "You must dismiss questions unrelated to electricity bills, power plans, appliances and general home electricity consumption."
            },
            *messages
        ],
        stream=True,
    )

    # Stream the response to the chat using `st.write_stream`, then store it in 
    # session state.
    with st.chat_message("assistant"):
        model_signature = f'''  
:gray[*answered by {model_name_format_func(st.session_state["selected_model"]).split(", from")[0]}*]'''
        response = st.write_stream(stream) + model_signature
    st.session_state.messages.append({"role": "assistant", "content": response})
