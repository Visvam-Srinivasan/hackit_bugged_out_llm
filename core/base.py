# core/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class SecurityModule(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)

    def skip_result(self, module_name: str) -> Dict[str, Any]:
        """Standardized response when a module is toggled OFF."""
        return {
            "enabled": False,
            "status": "SKIPPED",
            "score": 0.0,
            "reason": f"{module_name} disabled",
            "meta": {}
        }

    @abstractmethod
    async def run(self, text: str) -> Dict[str, Any]:
        """Each module implements its own logic here."""
        pass