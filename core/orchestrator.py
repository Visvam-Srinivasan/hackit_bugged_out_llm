# core/orchestrator.py
import asyncio
from core.interceptor import wash_text
from core.llm import get_ollama_response
from core.aggregator import aggregate_safety_results
from core.utils import fast_output_filter
from core.pipeline import log_event  

async def process_request(prompt: str, history: list, config: dict, model: str) -> dict:
    # 1. Layer 1: Clean the input
    log_event("INPUT_RAW", {"prompt": prompt})
    clean_prompt = wash_text(prompt)
    log_event("INPUT_CLEANED", {"clean_prompt": clean_prompt})

    # 2. Initialize and Filter Modules
    from modules.sanitization import SanitizationModule
    from modules.embedding import EmbeddingCheckModule
    from modules.llamaguard import LlamaGuardModule

    all_modules = [
        SanitizationModule(config.get("sanitization", {})),
        EmbeddingCheckModule(config.get("embedding_check", {})),
        LlamaGuardModule(config.get("llama_guard_pre", {}), check_type="pre")
    ]
    
    enabled_modules = [m for m in all_modules if m.enabled]
    log_event("PIPELINE_INIT", {"enabled_count": len(enabled_modules)})

    # --- THE FIX: Create default UI details so it never crashes ---
    ui_details = {
        "clean_prompt": clean_prompt,
        "sanitization_status": "SKIPPED",
        "embedding_score": 0.0,
        "lg_pre_verdict": "SKIPPED",
        "lg_post_verdict": "SKIPPED",
        "raw_response": ""
    }

    async def run_and_log_module(mod, text):
        mod_name = getattr(mod, 'name', mod.__class__.__name__)
        if isinstance(mod, LlamaGuardModule):
            mod_name += f"_{mod.check_type.upper()}"
            
        log_event("MODULE_START", {"module": mod_name})
        try:
            res = await mod.run(text)
            res["module"] = mod_name 
            log_event("MODULE_RESULT", res)
            return res
        except Exception as e:
            log_event("MODULE_ERROR", {"module": mod_name, "error": str(e)})
            raise e

    # 3. Parallel Pre-Checks
    if enabled_modules:
        try:
            tasks = [run_and_log_module(mod, clean_prompt) for mod in enabled_modules]
            pre_results = await asyncio.wait_for(asyncio.gather(*tasks), timeout=60.0)
            
            # --- THE FIX: Dynamically map module output by NAME, not by [index] ---
            for r in pre_results:
                m_name = r.get("module", "")
                if "Sanitization" in m_name:
                    ui_details["sanitization_status"] = r.get("status", "PASS")
                elif "Embedding" in m_name:
                    ui_details["embedding_score"] = r.get("score", 0.0)
                elif "LlamaGuard" in m_name and "PRE" in m_name:
                    ui_details["lg_pre_verdict"] = r.get("status", "PASS")

            auth = aggregate_safety_results(pre_results)
            
            if auth["decision"] == "BLOCK":
                log_event("SECURITY_BLOCK", {"stage": "PRE_CHECK", "reason": auth.get("triggered_by")})
                return {
                    "decision": "BLOCK",
                    "triggered_by": auth.get("triggered_by", "Unknown Security Module"),
                    "output": None,
                    **ui_details
                }
        except asyncio.TimeoutError:
            log_event("SECURITY_ERROR", {"reason": "Timeout - Check logs for stuck MODULE_START"})
            return {
                "decision": "BLOCK", 
                "triggered_by": "Security Timeout (Models likely loading)",
                "output": None,
                **ui_details
            }

    # 4. LLM Generation
    log_event("LLM_START", {"model": model})
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, get_ollama_response, history, model, False)
    log_event("LLM_RAW_RESPONSE", {"length": len(response)})
    
    ui_details["raw_response"] = response

    # 5. Post-Checks
    lg_post_config = config.get("llama_guard_post", {})
    if lg_post_config.get("enabled", False):
        lg_post = LlamaGuardModule(lg_post_config, check_type="post")
        post_result = await run_and_log_module(lg_post, response)
        
        ui_details["lg_post_verdict"] = post_result.get("status", "PASS")

        if post_result["status"] == "FAIL" or not fast_output_filter(response):
            log_event("RETRY_TRIGGERED", {"reason": "Post-check flag"})
            retry_response = await loop.run_in_executor(None, get_ollama_response, history, model, True)
            
            if fast_output_filter(retry_response):
                log_event("FINAL_DECISION", {"decision": "ALLOW", "note": "self-corrected"})
                ui_details["raw_response"] = retry_response 
                return {
                    "decision": "ALLOW",
                    "output": retry_response,
                    "reason": "Self-corrected unsafe output",
                    **ui_details
                }
            else:
                log_event("SECURITY_BLOCK", {"stage": "POST_CHECK", "reason": "Retry failed"})
                return {
                    "decision": "BLOCK",
                    "triggered_by": post_result.get("reason", "Llama Guard Post-check"),
                    "output": None,
                    **ui_details
                }

    log_event("FINAL_DECISION", {"decision": "ALLOW"})
    
    # --- THE FIX: Unpack the ui_details instead of hardcoding pre_results[0], etc. ---
    return {
        "decision": "ALLOW",
        "output": response,
        **ui_details 
    }