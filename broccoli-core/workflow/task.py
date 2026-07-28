from dataclasses import dataclass
from typing import Dict, Optional
import uuid, time

@dataclass
class Task:
    goal: str
    task_id: str = ""
    priority: str = "NORMAL"
    status: str = "queued"
    result: Optional[Dict] = None

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]
