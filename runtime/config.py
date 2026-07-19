import json
from pathlib import Path
class Config:
    def __init__(self):
        self.tick_seconds = 2.0
        self.max_workers = 4
        self.log_level = "INFO"
        self.state_file = Path.home() / "broccoli-core/runtime/state/runtime.json"
    def load(self):
        return self
    def save(self):
        pass
