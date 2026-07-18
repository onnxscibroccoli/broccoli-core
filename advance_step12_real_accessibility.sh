#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core

echo "=== Phase 4 Step 12: Real UI Dump + Iterative Accessibility ==="

# Enhanced real Accessibility using system dumps
cat > drivers/accessibility/driver.py <<'ACC'
import time
import subprocess
import json
from runtime.logger import setup_logger

class AccessibilityDriver:
    def __init__(self):
        self.logger = setup_logger("accessibility")
        self.logger.info("✅ Real AccessibilityDriver (dumpsys + pointer) loaded")

    def get_pointer_location(self):
        """Read current pointer position from Developer Options overlay"""
        try:
            result = subprocess.run(["dumpsys", "input"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                if "Pointer" in line or "x=" in line and "y=" in line:
                    # Crude parse - improve if needed
                    self.logger.info(f"📍 Pointer: {line.strip()}")
                    return line.strip()
        except:
            pass
        return "unknown"

    def dump_ui(self):
        """Get real UI hierarchy"""
        try:
            # Option 1: dumpsys window
            result = subprocess.run(["dumpsys", "window", "windows"], capture_output=True, text=True, timeout=8)
            nodes = len([l for l in result.stdout.splitlines() if "Window" in l or "mView" in l])
            self.logger.info(f"📱 UI Dump: \~{nodes} visible elements")
            return {"nodes": nodes, "raw": result.stdout[:500], "timestamp": time.time()}
        except Exception as e:
            self.logger.warning(f"UI dump failed: {e}")
            return {"nodes": 0, "error": str(e)}

    def snapshot(self):
        pointer = self.get_pointer_location()
        ui = self.dump_ui()
        return {"pointer": pointer, "ui": ui, "timestamp": time.time()}

    def tap(self, x=None, y=None):
        if x is None or y is None:
            # Fallback to center
            x, y = 540, 1200
        try:
            subprocess.run(["input", "tap", str(x), str(y)], check=True)
            self.logger.info(f"🔨 Tapped at ({x}, {y})")
            return True
        except:
            return False

    def perform_action(self, action: str, params=None):
        if action == "tap":
            return self.tap(params.get("x") if params else None, params.get("y") if params else None)
        # Add swipe, input_text similarly...
        return False
ACC

# Update Governor to use real snapshot
cat >> governor/engine.py <<'GOV'
    def run_cycle(self):
        self.cycle_count += 1
        if not self.health_check():
            return

        snapshot = self.accessibility.snapshot()  # Real dump + pointer
        decision = self.decision.decide(snapshot, None)

        for p in self.plugins:
            p.on_cycle(self)
            p.on_decision(decision)

        task = Task(goal=f"Interact with screen at pointer {snapshot.get('pointer', 'N/A')}", priority="NORMAL")
        self.queue.enqueue(task)
        result = self.executor.execute(task)
        self.queue.complete(task, result)

        self.logger.info(f"Governor cycle {self.cycle_count} | Nodes: {snapshot['ui'].get('nodes', 0)}")
GOV

chmod +x *.sh
echo "✅ Step 12 Ready - Real UI + Pointer Integration"
echo "Run now:"
./run.sh
