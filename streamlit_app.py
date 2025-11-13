import streamlit as st
from openai import OpenAI
import requests

def model_name_format_func(item):
    item = item['name'].replace(' (free)', '').split(': ')
    if len(item) > 1:
        return f'{item[1]}, from {item[0]}'
    else: 
        return item[0]
# Show title and description.
st.title("Welcome to Domotic__")

if 'OPENROUTER_API_KEY' not in st.secrets or st.secrets['OPENROUTER_API_KEY'] is None: 
    st.error("The OpenRouter API key is missing from the app's secrets! Please contact an administrator.", icon="🗝️")
else:
    openrouter_api_key = st.secrets['OPENROUTER_API_KEY']
    # Create an OpenAI client.
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_api_key
    )

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                'role': 'assistant',
                'content': 'Hi there! My name is Domitico and I\'m here to help. Feel free to ask me anything about your electricity bill :smile:'
            }
        ]

    # Display model switch
    if 'available_models' not in st.session_state:
        models = requests.get('https://openrouter.ai/api/v1/models/user', headers={'Authorization': f'Bearer {openrouter_api_key}'}).json()['data']
        models = list(filter(lambda model:model['id'].endswith(':free'), models))
        st.session_state['available_models'] = models
    
    if 'selected_model' not in st.session_state:
        st.session_state['selected_model'] = st.session_state['available_models'][0]

    with st.container(border=True):
        cols = st.columns(2)
        with cols[0]:
            st.write('Who would you like to chat with today?')
        with cols[1]:
            index = st.session_state['available_models'].index(st.session_state['selected_model'])
            st.selectbox('model_select', st.session_state['available_models'], format_func=model_name_format_func, index=index, label_visibility='hidden', key='selected_model')
            if 'description' in st.session_state['selected_model']:
                st.info(st.session_state['selected_model']['description'])

    # Display the existing chat messages via `st.chat_message`.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Create a chat input field to allow the user to enter a message. This will display
    # automatically at the bottom of the page.
    if prompt := st.chat_input(f'Now chatting with {st.session_state["selected_model"]["name"].replace("(free)", "").split(": ")[1]}'):

        # Store and display the current prompt.
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)


        messages = [{
                    "role": m["role"], 
                    "content": m["content"]
                } for m in st.session_state.messages]
        # Generate a response using the OpenAI API.
        stream = client.chat.completions.create(
            model=st.session_state['selected_model']['id'],
            messages=[{
                    "role": "system",
                    "content": "You are a helpful assistant. You are expert on electricity bills, power consumption etc. The user may ask questions related to this area."
                },
                {
                    "role": "system",
                    "content": "You must dismiss questions unrelated to electricity bills, power plans, appliances and general home electricity consumption."
                },
                #{
                #    "role": "system",
                #    "content": csv_str
                #},
                *messages
            ],
            stream=True,
        )

        # Stream the response to the chat using `st.write_stream`, then store it in 
        # session state.
        with st.chat_message("assistant"):
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})
