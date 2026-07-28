from collections import defaultdict
import json
from pathlib import Path

class KnowledgeGraph:
    def __init__(self):
        self.graph = defaultdict(dict)
        self.memory_file = Path.home() / "broccoli-core/runtime/memory/knowledge.json"
        self.load()

    def add(self, subject, relation, object_, confidence=1.0):
        self.graph[subject][relation] = {"object": object_, "confidence": confidence}
        self.save()
        print(f"KG: {subject} {relation} {object_}")

    def query(self, subject, relation=None):
        if relation:
            return self.graph.get(subject, {}).get(relation)
        return self.graph.get(subject, {})

    def load(self):
        if self.memory_file.exists():
            try:
                self.graph = defaultdict(dict, json.loads(self.memory_file.read_text()))
            except Exception:
                pass

    def save(self):
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.write_text(json.dumps(dict(self.graph), indent=2))
