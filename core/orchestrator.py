# core/orchestrator.py
import asyncio
from core.interceptor import wash_text
from core.llm import get_ollama_response
from core.aggregator import aggregate_safety_results
from core.utils import fast_output_filter # Ensure this is imported

async def process_request(prompt: str, history: list, config: dict, model: str) -> dict:
    # 1. Layer 1: Clean the input
    clean_prompt = wash_text(prompt)

    # 2. Initialize modules
    from modules.sanitization import SanitizationModule
    from modules.embedding import EmbeddingCheckModule
    from modules.llamaguard import LlamaGuardModule

    pre_check_modules = [
        SanitizationModule(config.get("sanitization", {})),
        EmbeddingCheckModule(config.get("embedding_check", {})),
        LlamaGuardModule(config.get("llama_guard_pre", {}), check_type="pre")
    ]

    # 3. Layers 2-4: Parallel Pre-Checks
    try:
        tasks = [mod.run(clean_prompt) for mod in pre_check_modules]
        pre_results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=10.0)
    except asyncio.TimeoutError:
        return {"decision": "BLOCK", "triggered_by": "Security Timeout"}

    auth = aggregate_safety_results(pre_results)
    if auth["decision"] == "BLOCK":
        return auth

    # 4. Layer 5: LLM Generation
    loop = asyncio.get_event_loop()
    # We pass the full history to maintain context
    response = await loop.run_in_executor(None, get_ollama_response, history, model, False)

    # 5. Layers 6 & 7: Post-Checks & Self-Correction
    # Fast Filter check
    is_fast_safe = fast_output_filter(response)
    
    # Deep Post-check (Llama Guard)
    lg_post = LlamaGuardModule(config.get("llama_guard_post", {}), check_type="post")
    post_result = await lg_post.run(response)
    is_deep_safe = post_result["status"] != "FAIL"

    if not is_fast_safe or not is_deep_safe:
        # Trigger Self-Correction Retry
        response = await loop.run_in_executor(None, get_ollama_response, history, model, True)
        
        # Final validation of retried response
        if not fast_output_filter(response):
            return {"decision": "BLOCK", "triggered_by": "Post-check (Final Failure)"}

    return {
        "decision": "ALLOW", 
        "output": response, 
        "pre_risk_score": auth.get("risk_score", 0.0)
    }