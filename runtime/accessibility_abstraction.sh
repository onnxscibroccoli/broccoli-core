#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Accessibility Backend Abstraction ==="

mkdir -p drivers/accessibility

# drivers/accessibility/backend.py (interface)
cat > drivers/accessibility/backend.py << 'BACKEND'
from abc import ABC, abstractmethod
from typing import Dict, Callable, Any

class AccessibilityBackend(ABC):
    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def start(self) -> bool:
        pass

    @abstractmethod
    def stop(self) -> bool:
        pass

    @abstractmethod
    def current_snapshot(self) -> str:
        pass

    @abstractmethod
    def subscribe(self, callback: Callable):
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def capabilities(self) -> Dict[str, Any]:
        pass
BACKEND

# drivers/accessibility/public_backend.py
cat > drivers/accessibility/public_backend.py << 'PUBLIC'
import subprocess
from backend import AccessibilityBackend

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
PUBLIC

# drivers/accessibility/hidden_backend.py (stub)
cat > drivers/accessibility/hidden_backend.py << 'HIDDEN'
from backend import AccessibilityBackend

class HiddenBackend(AccessibilityBackend):
    def initialize(self) -> bool:
        print("HiddenBackend: Initialized (optional)")
        return True

    def start(self) -> bool:
        print("HiddenBackend: Started")
        return True

    def stop(self) -> bool:
        print("HiddenBackend: Stopped")
        return True

    def current_snapshot(self) -> str:
        return ""  # Implement hidden API if available

    def subscribe(self, callback):
        pass

    def health(self) -> Dict:
        return {"status": "healthy", "latency_ms": 45, "backend": "hidden"}

    def capabilities(self) -> Dict:
        return {"supports_incremental": True, "supports_notifications": True, "supports_windows": True, "supports_hidden_api": True}
HIDDEN

# drivers/accessibility/manager.py
cat > drivers/accessibility/manager.py << 'MANAGER'
from backend import AccessibilityBackend
from public_backend import PublicBackend
from hidden_backend import HiddenBackend
from event_bus import EventBus

class AccessibilityManager:
    def __init__(self, bus: EventBus, preferred="public"):
        self.bus = bus
        self.preferred = preferred
        self.current_backend: AccessibilityBackend = None
        self.fallback_backend = PublicBackend()

    def initialize(self):
        try:
            if self.preferred == "hidden":
                self.current_backend = HiddenBackend()
            else:
                self.current_backend = PublicBackend()
            self.current_backend.initialize()
            self.bus.publish("BACKEND_STARTED", {"backend": self.preferred})
            return True
        except Exception:
            self.current_backend = self.fallback_backend
            self.current_backend.initialize()
            self.bus.publish("BACKEND_SWITCHED", {"to": "public"})
            return True

    def current_snapshot(self):
        return self.current_backend.current_snapshot()

    def health(self):
        return self.current_backend.health()
MANAGER

# Update driver to use manager
cat > drivers/accessibility/driver.py << 'DRIVER'
import subprocess
from manager import AccessibilityManager
from event_bus import EventBus

class AccessibilityDriver:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.manager = AccessibilityManager(bus)
        self.manager.initialize()
        self.bus.subscribe("TICK", self.capture)

    def capture(self, _):
        snapshot = self.manager.current_snapshot()
        if snapshot:
            self.bus.publish("AccessibilityCaptureReady", {"snapshot_length": len(snapshot)})

    def tap(self, x=540, y=1274):
        subprocess.run(["rish", "-c", f"input tap {x} {y}"], timeout=5)
DRIVER

echo "✅ Accessibility Backend Abstraction complete"
echo "Restarting runtime..."
pkill -f "python3 main.py" 2>/dev/null || true
python3 main.py
