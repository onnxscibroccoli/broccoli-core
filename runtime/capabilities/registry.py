from typing import Dict, List, Optional
from .base import Capability

class CapabilityRegistry:
    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}

    def register(self, cap: Capability) -> bool:
        if cap.initialize() and cap.available:
            self._capabilities[cap.id] = cap
            return True
        return False

    def get(self, cap_id: str) -> Optional[Capability]:
        return self._capabilities.get(cap_id)

    def get_all_healthy(self) -> List[Capability]:
        return [c for c in self._capabilities.values() if c.health == "OK"]
