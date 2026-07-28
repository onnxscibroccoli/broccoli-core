from abc import ABC, abstractmethod
from typing import List

class Capability(ABC):
    @property
    @abstractmethod
    def id(self) -> str: pass

    @property
    @abstractmethod
    def version(self) -> str: pass

    @property
    @abstractmethod
    def available(self) -> bool: pass

    @property
    @abstractmethod
    def health(self) -> str: pass  # e.g., "OK", "DEGRADED", "OFFLINE"

    @property
    @abstractmethod
    def permissions(self) -> List[str]: pass

    @property
    @abstractmethod
    def latency(self) -> float: pass  # Expected response time in ms

    @property
    @abstractmethod
    def reliability(self) -> float: pass  # 0.0 to 1.0 confidence score

    @property
    @abstractmethod
    def features(self) -> List[str]: pass

    @abstractmethod
    def initialize(self) -> bool:
        """Startup sequence for the specific capability."""
        pass
