# app.py
import streamlit as st
import asyncio
import pandas as pd
import json
import os
import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Import the orchestrator and vector store
from core.orchestrator import process_request
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
            
            if st.button("🗑️ Clear Audit Logs"):
                os.remove(LOG_FILE)
                st.rerun()
        except Exception as e:
            st.error(f"Error loading logs: {e}")
    else:
        st.info("No logs found. Interact with the bot to see security traces.")

def main():
    st.set_page_config(page_title="Secure RAG Chatbot", page_icon="🛡️", layout="wide")
    
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
        st.header("🧹 Database Management")
        if st.button("🗑️ Wipe Knowledge Base"):
            # PHYSICALLY resets the DB and the internal object reference
            if db.clear_database():
                st.session_state.messages = [] # Clear history to prevent context errors
                st.success("Vector Database and Chat History cleared!")
                st.rerun() # Refresh to update the 'db' reference in the orchestrator

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

    st.title("🛡️ Secure RAG Chatbot")
    tab_chat, tab_audit = st.tabs(["💬 Secure Chat", "🛠️ Security Diagnostics"])

    with tab_chat:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask a question about your documents..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing Security..."):
                    history_slice = st.session_state.messages[-MAX_HISTORY:]
                    messages_for_api = [{"role": m["role"], "content": m["content"]} for m in history_slice]
                    
                    # 1. RUN ORCHESTRATOR FOR PRE-CHECKS & FENCING
                    result = asyncio.run(process_request(prompt, messages_for_api, security_config, MODEL))
                
                if result["decision"] == "BLOCK":
                    st.error(f"🚨 **BLOCKED**: {result.get('triggered_by', 'Security violation')}.")
                else:
                    # 2. STREAMING GENERATOR FOR REAL-TIME OUTPUT
                    def response_generator():
                        stream = ollama.chat(
                            model=MODEL, 
                            messages=result["augmented_history"], # Uses the fenced prompt
                            stream=True
                        )
                        for chunk in stream:
                            yield chunk['message']['content']

                    # Render the stream using Streamlit's typewriter effect
                    full_response = st.write_stream(response_generator())
                    
                    # 3. Save to state and update last result for diagnostics
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    st.session_state.last_result = result
                    st.rerun()

    with tab_audit:
        # (Diagnostics code remains same as previous turns...)
        st.header("🔍 Latest Request Data Stream")
        if "last_result" in st.session_state:
            res = st.session_state.last_result
            col1, col2 = st.columns(2)
            # ... (UI rendering logic) ...
        display_audit_logs()

if __name__ == "__main__":
    main()