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
                    "next_editable": bool(self.semantic.get_next_editable())
                })
        except Exception:
            pass
