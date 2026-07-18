#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core

echo "=== Phase 5 Step 13: Codevelopment + Virtual Secondary Display ==="

# Virtual Overlay / Idle Prompt System
cat > drivers/overlay/virtual_display.py <<'OVER'
import time
from runtime.logger import setup_logger

class VirtualSecondaryDisplay:
    def __init__(self):
        self.logger = setup_logger("overlay")
        self.logger.info("🖥️  Virtual Secondary Display initialized")
        self.last_user_activity = time.time()
        self.idle_threshold = 30  # seconds

    def is_idle(self):
        return (time.time() - self.last_user_activity) > self.idle_threshold

    def update_activity(self):
        self.last_user_activity = time.time()

    def show_prompt(self, message: str):
        if self.is_idle():
            self.logger.info(f"📺 Virtual Display Prompt: {message}")
            # In future: show via overlay service, notification, or floating window
            print(f"\n[Virtual Screen] {message}\n")
        else:
            self.logger.info("User active - suppressing overlay")
OVER

# Integrate into Governor
cat >> governor/engine.py <<'GOV'
from drivers.overlay.virtual_display import VirtualSecondaryDisplay

    def __init__(self):
        ...  # previous init
        self.overlay = VirtualSecondaryDisplay()

    def run_cycle(self):
        self.cycle_count += 1
        snapshot = self.accessibility.snapshot()

        if self.overlay.is_idle():
            self.overlay.show_prompt("Codevelopment active - awaiting task or command...")

        decision = self.decision.decide(snapshot, None)
        # ... rest of cycle
GOV

# Auto-prompt example plugin
cat >> plugins/example_plugin.py <<'PLUG'
    def on_cycle(self, governor):
        governor.logger.info("🔌 ExamplePlugin: on_cycle")
        if hasattr(governor, 'overlay') and governor.overlay.is_idle():
            governor.overlay.show_prompt("Plugin suggests: Run accessibility test?")
PLUG

chmod +x *.sh
echo "✅ Codevelopment Virtual Display Ready"
echo "Run: ./run.sh"
