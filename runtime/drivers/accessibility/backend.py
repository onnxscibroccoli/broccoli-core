from abc import ABC, abstractmethod
from typing import Dict, Callable, Any

class AccessibilityBackend(ABC):
    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def start(self) -> bool:
        pass

    @abstractmethod
    def stop(self) -> bool:
        pass

    @abstractmethod
    def current_snapshot(self) -> str:
        pass

    @abstractmethod
    def subscribe(self, callback: Callable):
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def capabilities(self) -> Dict[str, Any]:
        pass
