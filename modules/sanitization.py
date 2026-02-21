# modules/sanitization.py
from core.base import SecurityModule
import re


class SanitizationModule(SecurityModule):
    async def run(self, text: str) -> dict:
        if not self.enabled:
            return self.skip_result("Sanitization")

        patterns = {
            "PII": r'\b\d{3}-\d{2}-\d{4}\b|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
            "SQL_INJECTION": r"UNION SELECT|DROP TABLE|OR '1'='1'",
        }

        for name, pattern in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return {"enabled": True, "status": "FAIL", "score": 1.0, "reason": f"Flagged: {name}"}

        return {"enabled": True, "status": "PASS", "score": 0.0, "reason": "No patterns matched"}
