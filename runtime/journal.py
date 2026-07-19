import time
from typing import Dict, Any, List

class EventJournal:
    def __init__(self):
        self.entries: List[Dict[str, Any]] = []

    def log_event(self, phase: str, payload: Any):
        """
        Phases match the pipeline: 
        Normalizer -> Semantic Update -> UI Diff -> Planner -> Governor -> Execution
        """
        entry = {
            "timestamp": time.time(),
            "phase": phase,
            "payload": payload
        }
        self.entries.append(entry)
        # Flush to local storage logic would hook in here for recovery

    def dump_history(self) -> List[Dict[str, Any]]:
        return self.entries
