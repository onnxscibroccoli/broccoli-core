#!/data/data/com.termux/files/usr/bin/bash
echo "=== Final Import Fix ==="

# Fix state.py (remove relative import)
cat > state.py << 'STATE'
from constants import STATE_INITIALIZING, STATE_RUNNING

class RuntimeState:
    def __init__(self):
        self.current = STATE_INITIALIZING
    def transition(self, new_state):
        print(f"State: {self.current} → {new_state}")
        self.current = new_state
STATE

# Fix governor/engine.py
cat > governor/engine.py << 'GOV'
from constants import STATE_RUNNING, STATE_RECOVERING
from event_bus import EventBus

class Governor:
    def __init__(self, bus: EventBus, state):
        self.bus = bus
        self.state = state
        self.bus.subscribe("TICK", self.on_tick)
        self.bus.subscribe("AccessibilityCaptureReady", self.on_accessibility)

    def on_tick(self, _):
        if self.state.current == STATE_RUNNING:
            self.bus.publish("GOVERNOR_HEARTBEAT")

    def on_accessibility(self, payload):
        if payload and payload.get("primary_action"):
            print("Governor: Primary action (send) ready")
        if payload and payload.get("next_editable"):
            print("Governor: Input field ready")

    def recover(self):
        print("Governor: Recovery started")
        self.state.transition(STATE_RECOVERING)
        self.bus.publish("GovernorRecoveryStarted")
GOV

# Fix driver import
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
                    "next_editable": bool(self.semantic.get_next_editable())
                })
        except Exception:
            pass

    def tap(self, x=540, y=1274):
        subprocess.run(["rish", "-c", f"input tap {x} {y}"], timeout=5)
ACC

echo "✅ Imports fixed"
echo "Starting runtime..."
python3 main.py
