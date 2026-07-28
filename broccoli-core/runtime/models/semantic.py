from typing import List, Dict, Any, Optional

class UIElement:
    def __init__(self, id: str, role: str, bounds: tuple):
        self.id = id
        self.role = role  # e.g., "button", "text_input", "collection"
        self.bounds = bounds
        self.attributes: Dict[str, Any] = {}
        self.children: List['UIElement'] = []

class Pane:
    def __init__(self, id: str):
        self.id = id
        self.landmarks: List[UIElement] = []
        self.controls: List[UIElement] = []
        self.text_blocks: List[UIElement] = []
        self.collections: List[UIElement] = []
        self.reading_order: List[UIElement] = []

class Window:
    def __init__(self, id: str):
        self.id = id
        self.panes: List[Pane] = []
        self.focus_graph: Dict[str, List[str]] = {}  # Map of node traversal edges

class Screen:
    def __init__(self):
        self.windows: List[Window] = []
        self.interaction_graph: Dict[str, Any] = {}  # Higher-level abstract relations

class PlannerContext:
    def __init__(self, screen: Screen):
        self.current_screen = screen
        self.active_window = screen.windows[0] if screen.windows else None
