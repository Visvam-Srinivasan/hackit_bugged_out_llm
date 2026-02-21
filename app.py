"""
Basic chatbot using Ollama with Mistral.
Requires Ollama running locally with: ollama pull mistral
"""

import streamlit as st
import requests
import json

OLLAMA_URL = "http://localhost:11434"
MODEL = "mistral"


def get_ollama_response(messages: list[dict], stream: bool = False) -> str:
    """Call Ollama chat API and return the assistant reply."""
    url = f"{OLLAMA_URL}/api/chat"
    payload = {"model": MODEL, "messages": messages, "stream": stream}
    try:
        # Shorter timeout so the UI doesn't "think" forever
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("message", {}).get("content", "").strip()
    except requests.exceptions.ConnectionError:
        return "Error: Cannot reach Ollama. Is it running? Start with `ollama serve` and ensure the mistral model is pulled (`ollama pull mistral`)."
    except requests.exceptions.Timeout:
        return "Error: Request timed out."
    except Exception as e:
        return f"Error: {e}"


def main():
    st.set_page_config(page_title="Mistral Chatbot", page_icon="💬", layout="centered")
    st.title("💬 Mistral Chatbot")
    st.caption(f"Powered by Ollama · Model: {MODEL}")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Type a message..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                messages_for_api = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
                response = get_ollama_response(messages_for_api)
            st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})

    with st.sidebar:
        st.header("Settings")
        if st.button("Clear chat history"):
            st.session_state.messages = []
            st.rerun()


if __name__ == "__main__":
    main()
