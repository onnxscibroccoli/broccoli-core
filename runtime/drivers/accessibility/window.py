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
