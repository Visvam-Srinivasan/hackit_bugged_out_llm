import asyncio
from core.llm import get_ollama_response
from core.interceptor import wash_text
from core.aggregator import aggregate_safety_results

# Import your concrete modules here
# from modules.sanitization import SanitizationModule etc.

async def process_request(prompt: str, history: list, config: dict, model: str) -> dict:
    loop = asyncio.get_event_loop()

    # --- PHASE 1: INTERCEPTION ---
    clean_prompt = wash_text(prompt)

    # --- PHASE 2: PARALLEL PRE-CHECKS ---
    # Here you would initialize modules and gather tasks
    # For now, we simulate an empty result list
    pre_check_results = [] 
    pre_auth = aggregate_safety_results(pre_check_results)
    
    if pre_auth["decision"] == "BLOCK":
        return pre_auth

    # --- PHASE 3: EXECUTION (Initial Attempt) ---
    response = await loop.run_in_executor(None, get_ollama_response, history, model)

    # --- PHASE 4: POST-CHECK & RETRY (Option B) ---
    # Low-latency string check for "system leaks" or bad keywords
    if "PRIMARY DIRECTIVE" in response or "illegal" in response.lower():
        if config["llama_guard_post"]["enabled"]:
            # TRIGGER RETRY
            response = await loop.run_in_executor(None, get_ollama_response, history, model, True)
            
            # If the retry is still bad, we block
            if "illegal" in response.lower():
                return {"decision": "BLOCK", "triggered_by": "Llama Guard (Post-check)"}

    return {
        "decision": "ALLOW",
        "output": response,
        "triggered_by": None,
        "pre_risk_score": pre_auth.get("risk_score", 0.0)
    }