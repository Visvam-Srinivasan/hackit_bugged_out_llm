# core/orchestrator.py
import asyncio
from core.llm import get_ollama_response

async def process_request(prompt: str, history: list, config: dict, model: str) -> dict:
    """
    Orchestrates the flow. Currently, it just calls the LLM, 
    but it's ready to accept security modules.
    """
    # 1. (Future) Pre-checks would happen here
    
    # 2. Main LLM Call
    # We use run_in_executor because requests is synchronous
    loop = asyncio.get_event_loop()
    response_text = await loop.run_in_executor(None, get_ollama_response, history, model)

    # 3. Standardized Output for app.py
    return {
        "decision": "ALLOW",
        "output": response_text,
        "triggered_by": None,
        "pre_risk_score": 0.0
    }