import os

print("[*] Updating driver.py with non-blocking asynchronous background capture...")

async_driver_code = """import subprocess
import threading
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

        self._lock = threading.Lock()
        self._capturing = False

        self.bus.subscribe("TICK", self.on_tick)

    def on_tick(self, _):
        # Trigger background capture if not already running to avoid tick starvation
        if not self._capturing:
            threading.Thread(target=self._background_capture, daemon=True).start()

    def _background_capture(self):
        with self._lock:
            self._capturing = True
        try:
            snapshot = self.manager.current_snapshot()
            if snapshot:
                self.bus.publish("AccessibilityCaptureReady", {"snapshot_length": len(snapshot)})
            
            # Non-blocking async rish dump
            proc = subprocess.run(
                ["rish", "-c", "uiautomator dump /data/local/tmp/uidump.xml > /dev/null 2>&1 && cat /data/local/tmp/uidump.xml"],
                capture_output=True, text=True, timeout=10
            )
            xml_string = proc.stdout
            
            xml_start = xml_string.find("<?xml")
            nodes = []
            if xml_start != -1:
                nodes = parse_uiautomator_xml(xml_string[xml_start:])

            self.observer.observe({
                "package": "unknown",
                "window_id": -1,
                "screen_id": f"snap_{len(snapshot) if snapshot else 0}",
                "nodes": nodes,
            })
        except subprocess.TimeoutExpired:
            logger.warning("Background a11y dump timed out.")
        except Exception as e:
            logger.error(f"Background a11y capture error: {e}")
        finally:
            with self._lock:
                self._capturing = False

    def observe_raw(self, raw_event: dict):
        return self.observer.observe(raw_event)

    def health(self):
        return {"manager": self.manager.health(), "observer": self.observer.health()}

    def tap(self, x=540, y=1274):
        subprocess.run(["rish", "-c", f"input tap {x} {y}"], timeout=5)
"""

with open("drivers/accessibility/driver.py", "w") as f:
    f.write(async_driver_code)
print("[+] driver.py successfully updated with async background capture.")
