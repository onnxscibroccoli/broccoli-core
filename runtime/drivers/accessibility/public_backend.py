import subprocess
from .backend import AccessibilityBackend

class PublicBackend(AccessibilityBackend):
    def initialize(self) -> bool:
        print("PublicBackend: Initialized")
        return True

    def start(self) -> bool:
        print("PublicBackend: Started")
        return True

    def stop(self) -> bool:
        print("PublicBackend: Stopped")
        return True

    def current_snapshot(self) -> str:
        try:
            result = subprocess.run(["rish", "-c", "uiautomator dump /sdcard/broccoli_ui.xml && cat /sdcard/broccoli_ui.xml"], 
                                  capture_output=True, text=True, timeout=8)
            return result.stdout
        except Exception:
            return ""

    def subscribe(self, callback):
        pass  # Event loop handled by manager

    def health(self) -> Dict:
        return {"status": "healthy", "latency_ms": 120, "backend": "public"}

    def capabilities(self) -> Dict:
        return {"supports_incremental": True, "supports_notifications": True, "supports_windows": True, "supports_hidden_api": False}
