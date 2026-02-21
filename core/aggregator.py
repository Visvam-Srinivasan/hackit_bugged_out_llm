# core/aggregator.py
def aggregate_safety_results(results: list) -> dict:
    # If any module failed, block the request
    for r in results:
        if r.get("status") == "FAIL":
            return {
                "decision": "BLOCK",
                "triggered_by": r.get("reason"),
                "risk_score": r.get("score", 1.0)
            }
    
    # Otherwise, find the highest risk score among passed/skipped modules
    max_score = max([r.get("score", 0.0) for r in results]) if results else 0.0
    return {
        "decision": "ALLOW",
        "risk_score": max_score,
        "triggered_by": None
    }