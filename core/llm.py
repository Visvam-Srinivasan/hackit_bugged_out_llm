# core/llm.py
import requests

OLLAMA_URL = "http://localhost:11434"

def get_ollama_response(messages: list[dict], model: str) -> str:
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"num_predict": 128},
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"Error: {e}"