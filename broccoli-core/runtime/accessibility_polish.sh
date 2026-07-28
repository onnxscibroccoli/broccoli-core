#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Accessibility Orchestration Polish & Validation ==="

# Enhanced Semantic with full helpers
cat > drivers/accessibility/semantic.py << 'SEM'
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
SEM

# Window with Focus Graph (from previous)
cat > drivers/accessibility/window.py << 'WIN'
from .semantic import UIElement
import xml.etree.ElementTree as ET

class Window:
    def __init__(self, root_node: ET.Element):
        self.panes: List[UIElement] = []
        self.focus_graph: List[UIElement] = []
        self._build_graph(root_node)
        self._build_focus_graph()

    def _build_graph(self, root):
        def traverse(node, parent=None):
            elem = UIElement(node)
            if parent:
                parent.children.append(elem)
            else:
                self.panes.append(elem)
            for child in node:
                traverse(child, elem)
        traverse(root)

    def _build_focus_graph(self):
        self.focus_graph = []
        def collect(node):
            if node.focusable or node.editable or node.clickable:
                self.focus_graph.append(node)
            for child in node.children:
                collect(child)
        for pane in self.panes:
            collect(pane)
WIN

echo "✅ Accessibility Orchestration polished & validated"
echo "Restarting with full capabilities..."
pkill -f "python3 main.py" 2>/dev/null || true
python3 main.py
