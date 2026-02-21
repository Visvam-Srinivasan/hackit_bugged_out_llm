"""
Basic chatbot using Ollama with Mistral and Toggle-Driven Security.
"""

import streamlit as st
import asyncio

# Import the orchestrator pipeline (which handles the LLM and security modules)
from core.orchestrator import process_request

MODEL = "mistral"
MAX_HISTORY = 6

def main():
    st.set_page_config(page_title="Secure Mistral Chatbot", page_icon="🛡️", layout="centered")
    st.title("🛡️ Secure Mistral Chatbot")
    st.caption(f"Powered by Ollama · Model: {MODEL} · Modular Security Pipeline")

    # --- SIDEBAR: SECURITY TOGGLES ---
    with st.sidebar:
        st.header("⚙️ Security Modules")
        st.markdown("Turn modules on/off to bypass them seamlessly.")
        
        # Build the config dynamically based on UI toggles
        security_config = {
            "sanitization": {
                "enabled": st.toggle("Input Sanitization", value=True)
            },
            "embedding_check": {
                "enabled": st.toggle("Embedding Similarity", value=True),
                "threshold": st.slider("Embedding Threshold", 0.0, 1.0, 0.85)
            },
            "llama_guard_pre": {
                "enabled": st.toggle("Llama Guard (Pre-check)", value=True)
            },
            "llama_guard_post": {
                "enabled": st.toggle("Llama Guard (Post-check)", value=True)
            }
        }
        
        st.divider()
        if st.button("Clear chat history"):
            st.session_state.messages = []
            st.rerun()

    # --- CHAT INTERFACE ---
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
            with st.spinner("Analyzing and Processing..."):
                # Grab chat history for context
                history_slice = st.session_state.messages[-MAX_HISTORY:]
                messages_for_api = [
                    {"role": m["role"], "content": m["content"]}
                    for m in history_slice
                ]
                
                # Execute the modular pipeline asynchronously
                result = asyncio.run(process_request(prompt, messages_for_api, security_config, MODEL))
                
            # Handle the standardized pipeline result
            if result["decision"] == "BLOCK":
                # Render a block warning
                response_text = f"🚨 **BLOCKED**: Flagged by {result.get('triggered_by', 'Unknown module')}."
                st.error(response_text)
                if "risk_score" in result:
                    st.caption(f"Risk Score: {result['risk_score']:.2f}")
            else:
                # Render the safe output
                response_text = result["output"]
                st.markdown(response_text)
                if result.get("pre_risk_score", 0) > 0:
                    st.caption(f"✓ Passed security checks (Risk: {result['pre_risk_score']:.2f})")

        # Save assistant response to history
        st.session_state.messages.append({"role": "assistant", "content": response_text})

if __name__ == "__main__":
    main()