import streamlit as st
from utils import model_name_format, stream_generator, Cache

cache = Cache()

# Display the existing chat messages via `st.chat_message`.
for message in cache['messages']:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# These are here for future proofing, in case we figure out how to put chat in a container
latest_message_user = st.empty()
latest_message_assistant = st.empty()

# Create a chat input field to allow the user to enter a message. This will display
# automatically at the bottom of the page.
if prompt := st.chat_input('Ask your questions here:'):

    # Store and display the current prompt.
    cache['messages'].append({"role": "user", "content": prompt})
    with latest_message_user:
        with st.chat_message("user"):
            st.markdown(prompt)


    messages = [{
                "role": m["role"], 
                "content": m["content"]
            } for m in cache['messages']]
    
    if cache['csv_content'] is not None:
        csv_messages = [
            {
                'role': 'system',
                'content': 'Use the csv data about available offers from the following csv file to aid in your responses.'
            },
            {
                'role': 'system',
                'content': cache['csv_content']
            }
        ]
        messages = csv_messages + messages

    if cache['pdf_content'] is not None:
        pdf_messages = [
            {
                'role': 'system',
                'content': 'Use the json data about the user\'s electricity bill from the following json file to provide ad hoc suggestions. This data was analyzed previously by you, directly from the PDF file the user uploaded.'
            },
            {
                'role': 'user',
                'content': cache['pdf_content']
            }
        ]
        messages = pdf_messages + messages

    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant. You are expert on electricity bills, power consumption etc. The user may ask questions related to this area."
        },
        {
            "role": "system",
            "content": "You must dismiss questions unrelated to electricity bills, power plans, appliances and general home electricity consumption."
        },
        *messages
    ]

    # Generate a response using the OpenRouter API.
    try:
        stream = st.session_state.client.chat.send(
            model=cache['selected_model']['id'],
            messages=messages,
            stream=True,
        )
        # Stream the response to the chat using `st.write_stream`, then store it in 
        # session state.
        with latest_message_assistant:
            with st.chat_message("assistant"):
                response = st.write_stream(stream_generator(stream))
        model_signature = f'''  
    :gray[*answered by {model_name_format(cache["selected_model"]).split(", from")[0]}*]'''
        cache['messages'].append({"role": "assistant", "content": response + model_signature})
    except Exception as e:
        with latest_message_assistant:
            st.error(e)

st.markdown("""
<style>
.stBottom {
    bottom: 5em;
}
</style>
""", unsafe_allow_html=True)