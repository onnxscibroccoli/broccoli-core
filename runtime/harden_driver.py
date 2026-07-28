import os

print("[*] Hardening AccessibilityDriver against Android/rish quirks...")

new_code = """import subprocess
from .manager import AccessibilityManager
from .observer import AccessibilityObserver
from .xml_parser import parse_uiautomator_xml
from event_bus import EventBus
import logging

logger = logging.getLogger("accessibility.driver")

class AccessibilityDriver:
    def __init__(self, bus: EventBus, metrics=None, logger=None):
        self.bus = bus
        self.manager = AccessibilityManager(bus)
        self.manager.initialize()

        self.observer = AccessibilityObserver(bus=bus, metrics=metrics, logger=logger)
        self.observer.start()

        self.bus.subscribe("TICK", self.capture)

    def capture(self, _):
        snapshot = self.manager.current_snapshot()
        if snapshot:
            self.bus.publish("AccessibilityCaptureReady", {"snapshot_length": len(snapshot)})
        
        try:
            proc = subprocess.run(
                ["rish", "-c", "uiautomator dump /data/local/tmp/uidump.xml > /dev/null 2>&1 && cat /data/local/tmp/uidump.xml"],
                capture_output=True, text=True, timeout=6
            )
            xml_string = proc.stdout
            
            # Resilient XML extraction (ignores hidden API warnings from Android)
            xml_start = xml_string.find("<?xml")
            nodes = []
            if xml_start != -1:
                clean_xml = xml_string[xml_start:]
                nodes = parse_uiautomator_xml(clean_xml)
            elif xml_string.strip():
                print(f"[!] XML not found in rish output. Raw: {xml_string[:100].strip()}")

            self.observer.observe({
                "package": "unknown",
                "window_id": -1,
                "screen_id": f"snap_{len(snapshot) if snapshot else 0}",
                "nodes": nodes,
            })
        except subprocess.TimeoutExpired:
            print("[-] A11y capture timed out waiting for rish (uiautomator dump).")
        except Exception as e:
            print(f"[-] A11y capture failed: {e}")

    def observe_raw(self, raw_event: dict):
        return self.observer.observe(raw_event)

    def health(self):
        return {"manager": self.manager.health(), "observer": self.observer.health()}

    def tap(self, x=540, y=1274):
        subprocess.run(["rish", "-c", f"input tap {x} {y}"], timeout=5)
"""

with open("drivers/accessibility/driver.py", "w") as f:
    f.write(new_code)
print("[+] driver.py updated with robust XML extraction and error visibility.")
