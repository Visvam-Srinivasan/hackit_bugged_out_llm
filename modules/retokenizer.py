import re
import unicodedata
from typing import Dict, Any

class AdversarialRetokenizer:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

    def _remove_invisible_chars(self, text: str) -> str:
        """Removes zero-width spaces and formatting characters attackers use to hide payloads."""
        return "".join(ch for ch in text if unicodedata.category(ch) not in ('Cf', 'Cc'))

    def _normalize_leetspeak(self, text: str) -> str:
        """Converts basic leetspeak back to standard characters."""
        leet_map = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a', 
            '5': 's', '7': 't', '@': 'a', '$': 's', '!': 'i'
        }
        normalized = ""
        for char in text:
            normalized += leet_map.get(char.lower(), char)
        return normalized

    def _remove_spacer_bypasses(self, text: str) -> str:
        """Detects and collapses spaced-out words (e.g., 'i g n o r e' -> 'ignore')."""
        spaced_word_pattern = re.compile(r'(?:[a-zA-Z]\s){2,}[a-zA-Z]')
        
        def collapse_spaces(match):
            return match.group(0).replace(" ", "")

        return spaced_word_pattern.sub(collapse_spaces, text)

    async def run(self, text: str) -> Dict[str, Any]:
        """Executes the retokenization pipeline."""
        if not self.enabled:
            return {"status": "SKIPPED", "text": text}

        # 1. Strip invisible Unicode
        cleaned_text = self._remove_invisible_chars(text)
        
        # 2. Collapse "s p a c e d" out evasion attempts
        cleaned_text = self._remove_spacer_bypasses(cleaned_text)
        
        # 3. Normalize leetspeak
        cleaned_text = self._normalize_leetspeak(cleaned_text)
        
        # 4. Standard lowercase & strip extra whitespace
        cleaned_text = " ".join(cleaned_text.lower().split())

        return {
            "status": "PASS",
            "original_text": text,
            "cleaned_text": cleaned_text,
            "module": "Adversarial Retokenizer"
        }