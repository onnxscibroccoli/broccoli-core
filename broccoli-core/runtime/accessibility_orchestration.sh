#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Full Accessibility Orchestration (Semantic + Focus + Validation) ==="

# Expanded Semantic Model with Focus Graph
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
        def collect_focus(node):
            if node.focusable or node.editable or node.clickable:
                self.focus_graph.append(node)
            for child in node.children:
                collect_focus(child)
        for pane in self.panes:
            collect_focus(pane)

class SemanticAccessibilityModel:
    def __init__(self):
        self.screens: Dict[str, Window] = {}
        self.current_screen: Optional[Window] = None

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

    def get_composer(self):
        return (540, 1274)  # Grok composer fallback
SEM

# Accessibility Driver with Validation
cat > drivers/accessibility/driver.py << 'ACC'
import subprocess
from semantic import SemanticAccessibilityModel

class AccessibilityDriver:
    def __init__(self, bus):
        self.bus = bus
        self.semantic = SemanticAccessibilityModel()
        self.bus.subscribe("TICK", self.capture)

    def capture(self, _):
        try:
            result = subprocess.run(["rish", "-c", "uiautomator dump /sdcard/broccoli_ui.xml && cat /sdcard/broccoli_ui.xml"], 
                                  capture_output=True, text=True, timeout=8)
            if result.stdout and self.semantic.update_from_xml(result.stdout):
                self.bus.publish("AccessibilityCaptureReady", {
                    "primary_action": bool(self.semantic.find_primary_action()),
                    "next_editable": bool(self.semantic.get_next_editable()),
                    "composer_bounds": self.semantic.get_composer()
                })
        except Exception:
            pass

    def tap(self, x=540, y=1274):
        subprocess.run(["rish", "-c", f"input tap {x} {y}"], timeout=5)
