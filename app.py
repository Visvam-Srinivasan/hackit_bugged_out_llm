# app.py
import streamlit as st
import asyncio
import pandas as pd
import json
import os

# Import the orchestrator pipeline
from core.orchestrator import process_request

MODEL = "mistral"
MAX_HISTORY = 6
LOG_FILE = "logs/pipeline_audit.jsonl"

def display_audit_logs():
    """Reads and displays the pipeline audit trail in a table."""
    st.subheader("🕵️ Real-time Pipeline Audit")
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
                # Parse the last 20 log entries
                logs = [json.loads(line) for line in lines[-20:]]
            
            logs.reverse() # Newest first
            df = pd.DataFrame(logs)
            
            # --- MODIFIED: Added "module" to the visible column order ---
            st.dataframe(
                df, 
                use_container_width=True,
                column_order=("timestamp", "stage", "module", "decision", "status", "score", "reason")
            )
            
            if st.sidebar.button("🗑️ Clear Audit Logs"):
                os.remove(LOG_FILE)
                st.rerun()
        except Exception as e:
            st.error(f"Error loading logs: {e}")
    else:
        st.info("No logs found. Interact with the bot to see security traces.")

def main():
    st.set_page_config(page_title="Secure Mistral Chatbot", page_icon="🛡️", layout="wide")
    
    # --- SIDEBAR: SECURITY TOGGLES ---
    with st.sidebar:
        st.title("🛡️ Security Controls")
        
        # 1. Module Toggles
        st.header("⚙️ Security Modules")
        
        do_sanit = st.toggle("Input Sanitization", value=True)
        do_embed = st.toggle("Embedding Similarity", value=True)
        # Reduced default threshold to 0.60 based on our testing
        do_embed_thresh = st.slider("Threshold", 0.0, 1.0, 0.60) 
        do_lg_pre = st.toggle("Llama Guard (Pre-check)", value=True)
        do_lg_post = st.toggle("Llama Guard (Post-check)", value=True)

        security_config = {
            "sanitization": {"enabled": do_sanit},
            "embedding_check": {"enabled": do_embed, "threshold": do_embed_thresh},
            "llama_guard_pre": {"enabled": do_lg_pre},
            "llama_guard_post": {"enabled": do_lg_post}
        }

        # 2. Dynamic Data Inspection (Visible only when toggled)
        st.divider()
        st.header("🔍 Module Data Stream")
        
        # Check if a result exists in session state to display
        if "last_result" in st.session_state:
            res = st.session_state.last_result
            
            if do_sanit:
                with st.expander("📝 Sanitization Data", expanded=True):
                    st.caption("Input:")
                    st.text(res.get("clean_prompt", "N/A"))
                    st.caption("Output (Status):")
                    st.code(res.get("sanitization_status", "PASS"))

            if do_embed:
                with st.expander("🧠 Embedding Data", expanded=True):
                    st.caption("Target Patterns:")
                    st.text("DAN, Jailbreak, etc.")
                    st.caption("Similarity Score:")
                    st.metric("Score", res.get("embedding_score", 0.0))

            if do_lg_pre:
                with st.expander("🛡️ Llama Guard Pre", expanded=True):
                    st.caption("Verdict:")
                    st.code(res.get("lg_pre_verdict", "SAFE"))

            if do_lg_post:
                with st.expander("📤 Llama Guard Post", expanded=True):
                    st.caption("AI Raw Output:")
                    st.text(str(res.get("raw_response", "N/A"))[:100] + "...")
                    st.caption("Verdict:")
                    st.code(res.get("lg_post_verdict", "SAFE"))
        else:
            st.write("Start a chat to see data movement.")

    # --- MAIN UI LAYOUT ---
    st.title("🛡️ Secure Mistral Chatbot")
    st.caption(f"Powered by Ollama · Model: {MODEL} · Modular Security Pipeline")

    # Use tabs to separate Chat from Diagnostics
    tab_chat, tab_audit = st.tabs(["💬 Secure Chat", "🛠️ Security Diagnostics"])

    with tab_chat:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # --- FIX: Create a dedicated container for messages ---
        chat_container = st.container()

        # 1. Display chat history INSIDE the container
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 2. The input box naturally renders below the container
        if prompt := st.chat_input("Type a message..."):
            
            # Save the user's prompt to state
            st.session_state.messages.append({"role": "user", "content": prompt})

            # 3. Render the NEW messages INSIDE the container (above the input box)
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing Security & Generating..."):
                        history_slice = st.session_state.messages[-MAX_HISTORY:]
                        messages_for_api = [
                            {"role": m["role"], "content": m["content"]}
                            for m in history_slice
                        ]
                        
                        # Run orchestrator
                        result = asyncio.run(process_request(prompt, messages_for_api, security_config, MODEL))
                        
                    # Handle results
                    if result["decision"] == "BLOCK":
                        response_text = f"🚨 **BLOCKED**: {result.get('triggered_by', 'Security violation detected')}."
                        st.error(response_text)
                    else:
                        response_text = result["output"]
                        st.markdown(response_text)
                        
                        # Notify user if a post-check self-correction occurred
                        if "reason" in result and "Self-corrected" in result["reason"]:
                            st.info(f"💡 {result['reason']}")

            # Save the AI message and result state
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.session_state.last_result = result
            
            # Refresh to lock everything in
            st.rerun()

    with tab_audit:
        display_audit_logs()

if __name__ == "__main__":
    main()