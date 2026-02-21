# core/utils.py
def fast_output_filter(response: str) -> bool:
    """Layer 6: Fast Filter (Returns False if bad)"""
    forbidden_markers = ["PRIMARY DIRECTIVE", "UNTRUSTED DATA", "--- END OF DATA ---"]
    for marker in forbidden_markers:
        if marker in response:
            return False # Failed the fast filter
    return True # Passed