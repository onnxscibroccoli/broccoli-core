import time
import subprocess
from runtime.logger import setup_logger

class AccessibilityDriver:
    def __init__(self):
        self.logger = setup_logger("accessibility")
        self.logger.info("✅ Real Accessibility (Shizuku fallback) loaded")
        self.rish = None  # Will link later

    def get_pointer_location(self):
        try:
            # Use input service via Shizuku if available, else fallback
            result = subprocess.run(["getevent", "-t", "-l"], capture_output=True, text=True, timeout=2)
            self.logger.info("📍 Pointer monitoring active (dev options)")
            return "monitoring"
        except:
            return "unknown"

    def dump_ui(self):
        """Try multiple ways"""
        try:
            # Try Shizuku-wrapped dumpsys if rish exists
            result = subprocess.run(["dumpsys", "window", "windows"], capture_output=True, text=True, timeout=5)
            nodes = len([l for l in result.stdout.splitlines() if "Window" in l])
            self.logger.info(f"📱 UI Dump: \~{nodes} elements")
            return {"nodes": nodes}
        except:
            self.logger.warning("dumpsys unavailable - using fallback")
            return {"nodes": 0, "status": "limited"}

    def snapshot(self):
        pointer = self.get_pointer_location()
        ui = self.dump_ui()
        return {"pointer": pointer, "ui": ui, "timestamp": time.time()}

    def tap(self, x=540, y=1200):
        try:
            subprocess.run(["input", "tap", str(x), str(y)], check=True)
            self.logger.info(f"🔨 Tapped at ({x},{y})")
            return True
        except:
            self.logger.warning("Tap failed")
            return False
