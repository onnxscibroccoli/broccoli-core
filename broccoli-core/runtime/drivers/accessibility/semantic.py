from typing import List, Dict, Optional
import xml.etree.ElementTree as ET

class UIElement:
    def __init__(self, node: ET.Element):
        self.id = node.get("resource-id") or node.get("text") or "unknown"
        self.type = node.tag
        self.text = node.get("text", "")
        self.content_desc = node.get("content-desc", "")
        self.bounds = self._parse_bounds(node.get("bounds"))
        self.clickable = node.get("clickable") == "true"
        self.editable = node.get("editable") == "true"
        self.focusable = node.get("focusable") == "true"
        self.children: List[UIElement] = []
        self.landmark = self._detect_landmark()

    def _parse_bounds(self, bounds_str):
        if not bounds_str: return (0, 0, 0, 0)
        try:
            return tuple(map(int, bounds_str.strip("[]").replace("][", ",").split(",")))
        except:
            return (0, 0, 0, 0)

    def _detect_landmark(self):
        if "button" in self.type.lower() or self.clickable:
            return "action"
        if self.editable or "edittext" in self.type.lower():
            return "input"
        if self.text and len(self.text) > 10:
            return "content"
        return None

class SemanticAccessibilityModel:
    def __init__(self):
        self.screens: Dict[str, 'Window'] = {}
        self.current_screen = None

    def update_from_xml(self, xml_str: str) -> bool:
        try:
            root = ET.fromstring(xml_str)
            self.current_screen = Window(root)
            self.screens["current"] = self.current_screen
            return True
        except Exception:
            return False

    def find_primary_action(self):
        if not self.current_screen: return None
        for pane in self.current_screen.panes:
            for child in pane.children:
                if child.landmark == "action" and child.clickable:
                    return child
        return None

    def get_next_editable(self):
        if not self.current_screen: return None
        for pane in self.current_screen.panes:
            for child in pane.children:
                if child.editable:
                    return child
        return None
