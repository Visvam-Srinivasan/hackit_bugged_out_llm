# core/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class SecurityModule(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", False)
        # Automatically grab the name of the child class (e.g., 'EmbeddingCheckModule')
        self.name = self.__class__.__name__

    def skip_result(self, reason: str = None) -> Dict[str, Any]:
        """Standardized response when a module is toggled OFF or skipped due to errors."""
        # Use the provided reason, or default to "[Module Name] disabled"
        skip_reason = reason if reason else f"{self.name} disabled"
        
        return {
            "module": self.name,  # Automatically stamp the module name here
            "enabled": False,
            "status": "SKIPPED",
            "score": 0.0,
            "reason": skip_reason,
            "meta": {}
        }

    @abstractmethod
    async def run(self, text: str) -> Dict[str, Any]:
        """Each module implements its own logic here."""
        pass