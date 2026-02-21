# core/orchestrator.py
import asyncio
from core.interceptor import wash_text
from core.llm import get_ollama_response
from core.aggregator import aggregate_safety_results
from core.utils import fast_output_filter

async def process_request(prompt: str, history: list, config: dict, model: str) -> dict:
    # 1. Layer 1: Clean the input
    clean_prompt = wash_text(prompt)

    # 2. Initialize and Filter Modules (Strictly respecting toggles)
    from modules.sanitization import SanitizationModule
    from modules.embedding import EmbeddingCheckModule
    from modules.llamaguard import LlamaGuardModule

    # We only instantiate and run modules that are explicitly "enabled" in the UI config
    all_modules = [
        SanitizationModule(config.get("sanitization", {})),
        EmbeddingCheckModule(config.get("embedding_check", {})),
        LlamaGuardModule(config.get("llama_guard_pre", {}), check_type="pre")
    ]
    
    enabled_modules = [m for m in all_modules if m.enabled]

    # 3. Parallel Pre-Checks (only for enabled modules)
    if enabled_modules:
        try:
            tasks = [mod.run(clean_prompt) for mod in enabled_modules]
            pre_results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=15.0)
            auth = aggregate_safety_results(pre_results)
            
            if auth["decision"] == "BLOCK":
                return {
                    "decision": "BLOCK",
                    "triggered_by": auth.get("triggered_by", "Unknown Security Module"),
                    "output": None  # No natural language for pre-check blocks
                }
        except asyncio.TimeoutError:
            return {"decision": "BLOCK", "triggered_by": "Security Timeout"}

    # 4. LLM Generation
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, get_ollama_response, history, model, False)

    # 5. Post-Checks (only if enabled)
    lg_post_config = config.get("llama_guard_post", {})
    if lg_post_config.get("enabled", False):
        lg_post = LlamaGuardModule(lg_post_config, check_type="post")
        post_result = await lg_post.run(response)
        
        if post_result["status"] == "FAIL" or not fast_output_filter(response):
            # Attempt Self-Correction
            retry_response = await loop.run_in_executor(None, get_ollama_response, history, model, True)
            
            # Final validation of retried response
            if fast_output_filter(retry_response):
                return {
                    "decision": "ALLOW",
                    "output": retry_response,
                    "reason": "Self-corrected unsafe output"
                }
            else:
                return {
                    "decision": "BLOCK",
                    "triggered_by": post_result.get("reason", "Llama Guard Post-check"),
                    "output": None
                }

    return {"decision": "ALLOW", "output": response}