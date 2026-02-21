# core/utils.py
def fast_output_filter(response: str) -> bool:
    forbidden = ["PRIMARY DIRECTIVE", "COMMAND:", "System Prompt", "---"]
    # If the AI starts repeating our secret instructions, block it
    return not any(marker in response for marker in forbidden)