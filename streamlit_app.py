import streamlit as st
from openai import OpenAI

# Show title and description.
st.title("💬 Welcome to Domotic__")
st.write(
    "You can chat with our chat with us here."
)

openrouter_api_key = st.secrets['OPENROUTER_API_KEY']
if openrouter_api_key is None: 
    st.info("The OpenRouter API key is missing from the app's secrets! Please contact an administrator.", icon="🗝️")
else:
    # Create an OpenAI client.
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_api_key
    )

    # Create a session state variable to store the chat messages. This ensures that the
    # messages persist across reruns.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display the existing chat messages via `st.chat_message`.
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Create a chat input field to allow the user to enter a message. This will display
    # automatically at the bottom of the page.
    if prompt := st.chat_input("What is up?"):

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
            model="kwaipilot/kat-coder-pro:free",
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
