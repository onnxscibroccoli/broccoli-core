import os

print("[*] 1. Updating drivers/accessibility/driver.py for live XML parsing...")

driver_code = """import subprocess
from .manager import AccessibilityManager
from .observer import AccessibilityObserver
from .xml_parser import parse_uiautomator_xml
from event_bus import EventBus

class AccessibilityDriver:
    def __init__(self, bus: EventBus, metrics=None, logger=None):
        self.bus = bus
        self.manager = AccessibilityManager(bus)
        self.manager.initialize()

        self.observer = AccessibilityObserver(bus=bus, metrics=metrics, logger=logger)
        self.observer.start()

        self.bus.subscribe("TICK", self.capture)

    def capture(self, _):
        # 1. Existing snapshot path (fallback)
        snapshot = self.manager.current_snapshot()
        if snapshot:
            self.bus.publish("AccessibilityCaptureReady", {
                "snapshot_length": len(snapshot),
            })
        
        # 2. Semantic node extraction (Phase 2 & 3)
        try:
            # Dump XML securely using rish, outputting directly to stdout
            proc = subprocess.run(
                ["rish", "-c", "uiautomator dump /data/local/tmp/uidump.xml > /dev/null 2>&1 && cat /data/local/tmp/uidump.xml"],
                capture_output=True, text=True, timeout=4
            )
            xml_string = proc.stdout.strip()
            
            nodes = []
            if xml_string.startswith("<?xml"):
                nodes = parse_uiautomator_xml(xml_string)
            
            # Feed observer the live nodes
            self.observer.observe({
                "package": "unknown",  # Extracted by parser in future iteration if needed
                "window_id": -1,
                "screen_id": f"snap_{len(snapshot) if snapshot else 0}",
                "nodes": nodes,
            })
        except Exception as e:
            # Fail gracefully on timeout/rish failure so TICK loop continues
            pass

    def observe_raw(self, raw_event: dict):
        return self.observer.observe(raw_event)

    def health(self):
        h = {"manager": self.manager.health()}
        h["observer"] = self.observer.health()
        return h

    def tap(self, x=540, y=1274):
        subprocess.run(["rish", "-c", f"input tap {x} {y}"], timeout=5)
"""

with open("drivers/accessibility/driver.py", "w") as f:
    f.write(driver_code)
print("[+] driver.py successfully updated with uiautomator pipeline.")

print("\n[*] 2. Autonomously patching main.py...")
with open("main.py", "r") as f:
    lines = f.readlines()

out_lines = []
import_added = False
patched = False

for line in lines:
    # Ensure import is added near the top
    if (line.startswith("import") or line.startswith("from")) and not import_added:
        out_lines.append("from drivers.accessibility.consumers import register_accessibility_consumers\n")
        import_added = True
    
    out_lines.append(line)
    
    # Inject registration right after EventBus is instantiated
    if "EventBus(" in line and "import" not in line and not patched:
        indent = line.split(line.strip())[0]
        var_name = line.strip().split("=")[0].strip()  # Extracts 'bus' or 'self.bus'
        out_lines.append(f"{indent}register_accessibility_consumers({var_name})\n")
        patched = True

with open("main.py", "w") as f:
    f.writelines(out_lines)

if patched:
    print("[+] main.py successfully patched with EventBus consumers.")
else:
    print("[-] Could not find EventBus initialization in main.py. Manual check needed.")

print("\n[*] Phase 3 Deployment Complete.")
