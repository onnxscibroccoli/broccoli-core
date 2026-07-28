import xml.etree.ElementTree as ET
from typing import Optional
from models.semantic import UIElement, Screen, Window

class UINormalizer:
    def __init__(self, event_bus):
        self.bus = event_bus
        self.bus.subscribe("UI_UPDATED", self._on_ui_updated)

    def _on_ui_updated(self, raw_xml: str):
        print("[Normalizer] Parsing raw UI dump...")
        try:
            screen = self.parse_xml(raw_xml)
            # Publish normalized model to the bus for the Planner
            self.bus.publish("SEMANTIC_UPDATE", screen)
        except Exception as e:
            print(f"[Normalizer] Parsing failed: {e}")

    def parse_xml(self, xml_string: str) -> Screen:
        root = ET.fromstring(xml_string)
        screen = Screen()
        
        # Basic mapping logic: iterate over nodes and build UIElement objects
        # This is a simplified traversal; we focus on nodes with resource-id
        for node in root.iter('node'):
            node_id = node.attrib.get('resource-id', 'unknown')
            bounds = node.attrib.get('bounds', '[0,0][0,0]')
            role = node.attrib.get('class', 'element')
            
            element = UIElement(node_id, role, bounds)
            # Add attributes
            element.attributes = {k: v for k, v in node.attrib.items() if k not in ['resource-id', 'bounds', 'class']}
            
            # This is a flat list for now; we'll add nesting/window logic as the model matures
            screen.windows.append(Window(id=node_id))
            
        return screen
