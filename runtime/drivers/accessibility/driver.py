import subprocess
import threading
from .manager import AccessibilityManager
from .observer import AccessibilityObserver
from .xml_parser import parse_uiautomator_xml, is_valid_xml
from runtime.eventbus import EventBus
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

        self._capture_failures = 0
        self._capture_disabled = False
        self._failure_limit = 5

        self.bus.subscribe("TICK", self.on_tick)

    def on_tick(self, _):
        # Accessibility XML capture disabled temporarily.
        # Shizuku/rish is the active execution backend.
        self.bus.publish(
            "CAPABILITY_STATUS",
            {
                "capability": "accessibility_stream",
                "available": False,
                "backend": "shizuku",
                "reason": "awaiting_helper_apk"
            },
            source="AccessibilityDriver"
        )

    def _background_capture(self):
        with self._lock:
            self._capturing = True
        try:
            snapshot = self.manager.current_snapshot()
            if snapshot:
                self.bus.publish("AccessibilityCaptureReady", {"snapshot_length": len(snapshot)})
            
            # Resilient accessibility capture
            nodes = []

            try:
                subprocess.run(
                    [
                        "rish",
                        "-c",
                        "uiautomator dump /data/local/tmp/uidump.xml"
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=8
                )

                proc = subprocess.run(
                    [
                        "rish",
                        "-c",
                        "cat /data/local/tmp/uidump.xml"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                xml_string = proc.stdout or ""

                xml_start = xml_string.find("<?xml")

                if xml_start >= 0:
                    xml_payload = xml_string[xml_start:]

                    if is_valid_xml(xml_payload):
                        try:
                            nodes = parse_uiautomator_xml(xml_payload)
                        except Exception as e:
                            logger.warning(
                                f"XML parse skipped: {e}"
                            )
                    else:
                        logger.warning(
                            "Invalid accessibility XML discarded"
                        )

            except subprocess.TimeoutExpired:
                logger.warning(
                    "Accessibility capture timeout"
                )

            except Exception as e:
                logger.warning(
                    f"Accessibility capture failed: {e}"
                )

            self._capture_failures = 0

            self.observer.observe({
                "package": "unknown",
                "window_id": -1,
                "screen_id": f"snap_{len(snapshot) if snapshot else 0}",
                "nodes": nodes,
            })
        except subprocess.TimeoutExpired:
            self._capture_failures += 1

            logger.warning(
                f"Accessibility capture timeout ({self._capture_failures}/{self._failure_limit})"
            )

            if self._capture_failures >= self._failure_limit:
                self._capture_disabled = True

                self.bus.publish(
                    "CAPABILITY_STATUS",
                    {
                        "capability": "accessibility_stream",
                        "available": False,
                        "fallback": "shizuku",
                        "reason": "circuit_breaker"
                    }
                )

            self.bus.publish(
                "CAPABILITY_STATUS",
                {
                    "capability": "accessibility_stream",
                    "available": False,
                    "fallback": "shizuku"
                }
            )
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
