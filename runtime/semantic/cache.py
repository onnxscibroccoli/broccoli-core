from dataclasses import dataclass, field
from time import time

@dataclass
class SemanticNode:
    semantic_id: str
    class_name: str = ""
    text: str = ""
    resource_id: str = ""
    content_desc: str = ""
    bounds: str = ""
    confidence: float = 1.0
    last_verified: float = field(default_factory=time)

class SemanticCache:

    def __init__(self):
        self.nodes = {}
        self.landmarks = {}
        self.focus_node = None
        self.screen_signature = None
        self.package = None
        self.app_version = None

    def remember(self,node):
        self.nodes[node.semantic_id]=node

    def get(self,semantic_id):
        return self.nodes.get(semantic_id)

    def set_focus(self,semantic_id):
        self.focus_node=semantic_id

    def verify(self,semantic_id):
        node=self.nodes.get(semantic_id)
        if not node:
            return False
        node.last_verified=time()
        return True

    def update_signature(self,sig):
        self.screen_signature=sig
