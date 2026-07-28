from abc import ABC, abstractmethod
from typing import Dict, Any

class Provider(ABC):
    @abstractmethod
    def initialize(self) -> bool:
        pass
    @abstractmethod
    def send(self, message: str, context: Dict = None) -> bool:
        pass
    @abstractmethod
    def stream(self, message: str):
        pass
    @abstractmethod
    def health(self) -> Dict[str, Any]:
        pass
    @abstractmethod
    def shutdown(self) -> bool:
        pass
    @abstractmethod
    def capabilities(self) -> Dict[str, bool]:
        pass
