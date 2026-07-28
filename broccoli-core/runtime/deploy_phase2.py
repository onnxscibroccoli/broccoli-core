import os
import xml.etree.ElementTree as ET
import hashlib

# 1. Create the XML Parser
os.makedirs("drivers/accessibility", exist_ok=True)
with open("drivers/accessibility/xml_parser.py", "w") as f:
    f.write('''import xml.etree.ElementTree as ET
import hashlib
import logging

logger = logging.getLogger(__name__)

def parse_uiautomator_xml(xml_string):
    """Parses Android uiautomator XML dump into generic semantic node dicts."""
    nodes = []
    if not xml_string or not isinstance(xml_string, str):
        return nodes

    try:
        root = ET.fromstring(xml_string)
        for elem in root.iter('node'):
            a = elem.attrib
            bounds = a.get('bounds', '')
            class_name = a.get('class', '')
            text = a.get('text', '')
            res_id = a.get('resource-id', '')
            
            # Generate stable ID matching Phase 1 cache requirements
            raw_id = f"{res_id}::{class_name}::{bounds}::{text}"
            stable_id = hashlib.md5(raw_id.encode('utf-8')).hexdigest()
            
            nodes.append({
                "stable_id": stable_id,
                "resource_id": res_id,
                "class_name": class_name,
                "package": a.get('package', ''),
                "text": text,
                "content_desc": a.get('content-desc', ''),
                "bounds": bounds,
                "is_focused": a.get('focused') == 'true',
                "is_scrollable": a.get('scrollable') == 'true',
                "is_clickable": a.get('clickable') == 'true',
                "is_enabled": a.get('enabled') == 'true'
            })
    except ET.ParseError as e:
        logger.error(f"Failed to parse XML: {e}")
    return nodes
''')

# 2. Create the Event Consumers
with open("drivers/accessibility/consumers.py", "w") as f:
    f.write('''import logging

logger = logging.getLogger("accessibility.consumers")

def register_accessibility_consumers(bus, metrics=None):
    """Wires autonomy layer and metrics to accessibility semantic events."""
    
    def on_ui_changed(event):
        payload = event.get("value", {})
        logger.info(f"[UI_CHANGED] UI state aggregated change: {payload}")
        if metrics and hasattr(metrics, 'increment'):
            try: metrics.increment("accessibility.ui_changed", 1)
            except TypeError: metrics.increment("accessibility.ui_changed")

    def on_focus_changed(event):
        payload = event.get("value", {})
        logger.debug(f"[FOCUS_CHANGED] Focus shifted to: {payload.get('focused_id')}")
        if metrics and hasattr(metrics, 'increment'):
            try: metrics.increment("accessibility.focus_changed", 1)
            except TypeError: metrics.increment("accessibility.focus_changed")

    def on_node_added(event):
        payload = event.get("value", {})
        logger.debug(f"[NODE_ADDED] {payload.get('stable_id')}")

    bus.subscribe("UI_CHANGED", on_ui_changed)
    bus.subscribe("FOCUS_CHANGED", on_focus_changed)
    bus.subscribe("NODE_ADDED", on_node_added)
    
    logger.info("Accessibility consumers registered on EventBus.")
''')

print("[+] Created drivers/accessibility/xml_parser.py")
print("[+] Created drivers/accessibility/consumers.py")

# 3. Validation: End-to-End Smoke Test
print("\n[*] Running Phase 2 Integration Smoke Test...")
try:
    from event_bus import EventBus
    from drivers.accessibility.observer import AccessibilityObserver
    from drivers.accessibility.xml_parser import parse_uiautomator_xml
    from drivers.accessibility.consumers import register_accessibility_consumers

    bus = EventBus()
    events_seen = []
    
    # Intercept publish to track bus activity securely
    original_publish = bus.publish
    def tracking_publish(event_type, payload=None):
        events_seen.append(event_type)
        original_publish(event_type, payload)
    bus.publish = tracking_publish

    # Wire up the new consumers
    register_accessibility_consumers(bus)

    # Boot the observer
    obs = AccessibilityObserver(bus)
    obs.start()

    # Mock uiautomator XML Dump
    mock_xml = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
    <hierarchy rotation="0">
        <node index="0" text="" resource-id="" class="android.widget.FrameLayout" package="com.android.systemui" bounds="[0,0][1080,2400]">
            <node index="0" text="Search" resource-id="com.example:id/search" class="android.widget.EditText" package="com.example.app" focused="true" bounds="[50,100][1030,250]" />
        </node>
    </hierarchy>
    """

    # Parse and extract
    parsed_nodes = parse_uiautomator_xml(mock_xml)
    assert len(parsed_nodes) == 2, "Failed: Should parse exactly 2 nodes."
    
    focused_node = next((n for n in parsed_nodes if n['is_focused']), None)
    assert focused_node is not None, "Failed: Should identify the focused node."

    # Feed the observer
    obs.observe({
        "package": "com.example.app",
        "window_id": 1,
        "focused_id": focused_node["stable_id"],
        "nodes": parsed_nodes
    })

    # Validate output signals
    assert "NODE_ADDED" in events_seen, "Cache diff failed to emit NODE_ADDED."
    assert "UI_CHANGED" in events_seen, "Cache diff failed to emit UI_CHANGED."
    
    print("[+] SUCCESS: XML Parsing -> Observer -> Diff -> EventBus -> Consumers pipeline validated!")
    print(f"[*] Pipeline Health: {obs.health()}")
    
except Exception as e:
    print(f"[-] Integration test failed: {e}")

print("\n" + "="*50)
print("ACTION REQUIRED: MANUAL WIRING (To prevent breaking existing loops)")
print("="*50)
print('''
1. In `main.py`, hook the consumers into your tick loop:
   ```python
   from drivers.accessibility.consumers import register_accessibility_consumers
   # Place this after EventBus initialization:
   register_accessibility_consumers(bus, metrics=your_metrics_instance)

 * In drivers/accessibility/driver.py, replace the empty node pulse:
   from drivers.accessibility.xml_parser import parse_uiautomator_xml

# Wherever you generate the TICK capture/pulse:
nodes = parse_uiautomator_xml(xml_dump_string)
self.observer.observe({
    "nodes": nodes,
    "package": "current_package_here"
    # ... other metadata
})

''')
