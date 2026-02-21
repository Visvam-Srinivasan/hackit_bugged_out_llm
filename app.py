# app.py
import streamlit as st
import asyncio
import pandas as pd
import json
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import the orchestrator pipeline
from core.orchestrator import process_request
# Import Vector Store
from modules.vector_store import VectorStore

MODEL = "mistral"
MAX_HISTORY = 6
LOG_FILE = "logs/pipeline_audit.jsonl"

# Initialize Vector Store
db = VectorStore()

def display_audit_logs():
    """Reads and displays the pipeline audit trail in a table."""
    st.subheader("🕵️ Historical Pipeline Audit")
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()
                logs = [json.loads(line) for line in lines[-20:]]
            
            logs.reverse() # Newest first
            df = pd.DataFrame(logs)
            
            st.dataframe(
                df, 
                use_container_width=True,
                column_order=("timestamp", "stage", "module", "decision", "status", "score", "reason")
            )
            
            # MOVED: The clear button is now below the table in the main view
            if st.button("🗑️ Clear Audit Logs"):
                os.remove(LOG_FILE)
                st.rerun()
        except Exception as e:
            st.error(f"Error loading logs: {e}")
    else:
        st.info("No logs found. Interact with the bot to see security traces.")

def main():
    st.set_page_config(page_title="Secure RAG Chatbot", page_icon="🛡️", layout="wide")
    
    # --- SIDEBAR: KNOWLEDGE BASE & SECURITY TOGGLES ONLY ---
    with st.sidebar:
        st.title("🛡️ Secure RAG Controls")
        
        st.header("📄 Knowledge Base")
        uploaded_file = st.file_uploader("Upload a Text Document", type=["txt", "md"])
        
        if uploaded_file and st.button("Index Document"):
            with st.spinner("Processing and chunking document..."):
                raw_text = uploaded_file.read().decode("utf-8")
                splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
                chunks = splitter.split_text(raw_text)
                
                ids = [f"{uploaded_file.name}_chunk_{i}" for i in range(len(chunks))]
                db.add_documents(chunks, ids)
                st.success(f"Successfully indexed {len(chunks)} chunks!")

        st.divider()
        st.header("⚙️ Security Modules")
        
        do_sanit = st.toggle("Input Sanitization", value=True)
        do_embed = st.toggle("Embedding Similarity", value=True)
        do_embed_thresh = st.slider("Threshold", 0.0, 1.0, 0.60) 
        do_lg_pre = st.toggle("Llama Guard (Pre-check)", value=True)
        do_lg_post = st.toggle("Llama Guard (Post-check)", value=True)

        security_config = {
            "sanitization": {"enabled": do_sanit},
            "embedding_check": {"enabled": do_embed, "threshold": do_embed_thresh},
            "llama_guard_pre": {"enabled": do_lg_pre},
            "llama_guard_post": {"enabled": do_lg_post}
        }

        st.divider()
        if st.button("Clear chat history"):
            st.session_state.messages = []
            st.rerun()

    # --- MAIN UI LAYOUT ---
    st.title("🛡️ Secure RAG Chatbot")
    st.caption(f"Powered by Ollama · Model: {MODEL} · Modular Security Pipeline")

    tab_chat, tab_audit = st.tabs(["💬 Secure Chat", "🛠️ Security Diagnostics"])

    with tab_chat:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Create a dedicated container for messages to anchor input box
        chat_container = st.container()

        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    # Display RAG context if the assistant used it
                    if msg["role"] == "assistant" and msg.get("context"):
                        with st.expander("View Retrieved Context"):
                            st.info(msg["context"])

        if prompt := st.chat_input("Ask a question about your documents..."):
            st.session_state.messages.append({"role": "user", "content": prompt})

            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Analyzing Security, Retrieving & Generating..."):
                        history_slice = st.session_state.messages[-MAX_HISTORY:]
                        # Only send role/content to the API, filter out the context key
                        messages_for_api = [{"role": m["role"], "content": m["content"]} for m in history_slice]
                        
                        result = asyncio.run(process_request(prompt, messages_for_api, security_config, MODEL))
                        
                    if result["decision"] == "BLOCK":
                        response_text = f"🚨 **BLOCKED**: {result.get('triggered_by', 'Security violation detected')}."
                        st.error(response_text)
                        retrieved_context = ""
                    else:
                        response_text = result["output"]
                        retrieved_context = result.get("context", "")
                        st.markdown(response_text)
                        
                        if retrieved_context:
                            with st.expander("View Retrieved Context"):
                                st.info(retrieved_context)

            # Save the message, state, and RAG context
            st.session_state.messages.append({
                "role": "assistant", 
                "content": response_text, 
                "context": retrieved_context
            })
            st.session_state.last_result = result
            st.rerun()

    with tab_audit:
        # --- MOVED: Module Data Stream is now in the Diagnostics Tab ---
        st.header("🔍 Latest Request Data Stream")
        
        if "last_result" in st.session_state:
            res = st.session_state.last_result
            
            # Using columns to lay out the data beautifully
            col1, col2 = st.columns(2)
            
            with col1:
                if do_sanit:
                    with st.expander("📝 Sanitization Data", expanded=True):
                        st.caption("Input:")
                        st.text(res.get("clean_prompt", "N/A"))
                        st.caption("Output (Status):")
                        st.code(res.get("sanitization_status", "PASS"))

                if do_lg_pre:
                    with st.expander("🛡️ Llama Guard Pre", expanded=True):
                        st.caption("Verdict:")
                        st.code(res.get("lg_pre_verdict", "SAFE"))

            with col2:
                if do_embed:
                    with st.expander("🧠 Embedding Data", expanded=True):
                        st.caption("Similarity Score:")
                        st.metric("Score", round(res.get("embedding_score", 0.0), 4))

                if do_lg_post:
                    with st.expander("📤 Llama Guard Post", expanded=True):
                        st.caption("Verdict:")
                        st.code(res.get("lg_post_verdict", "SAFE"))
        else:
            st.info("Start a chat to see real-time data movement through the pipeline.")
            
        st.divider()
        
        # Call the historical audit logs below the live data stream
        display_audit_logs()

if __name__ == "__main__":
    main()