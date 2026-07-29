from dataclasses import dataclass, field
import time
import uuid

@dataclass
class Event:
    topic: str
    payload: dict
    source: str = "unknown"
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
