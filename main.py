import random
import time

import streamlit as st

import asklib

# instantiate asklib API class
api = asklib.API()

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


def assistant_talk(message: str):
    with st.chat_message("assistant"):
        response = st.write_stream(message)
        st.session_state.messages.append({"role": "assistant", "content": response})


def user_talk(message: str):
    with st.chat_message("user"):
        st.write(message)
        st.session_state.messages.append({"role": "user", "content": message})

    # Streamed response emulator


def intro_messages():
    response = random.choice(
        [
            "Hello there! How can I assist you today?",
            "Hi, human! Is there anything I can help you with?",
            "Do you need help?",
        ]
    )
    for word in response.split():
        yield word + " "
        time.sleep(0.05)


# setup title and upload widget
st.title("Ask my pdf")
st.write("lista: 5 | Rafael Figueiredo")
uploaded_file = st.file_uploader("Choose a file", type=["pdf"])

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# assistant_talk(intro_messages())

# handle file uploads
if uploaded_file is not None:
    # To read file as bytes:
    api.upload_file(filename=uploaded_file.name, data=uploaded_file.getvalue())

# React to user input
if prompt := st.chat_input("What is up?"):
    # Display user message in chat message container
    user_talk(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        response = st.write_stream(api.ask_file(prompt=prompt))[0]
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
