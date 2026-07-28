import subprocess
import time
from typing import Optional, Any

class AccessibilityDriver:
    def __init__(self, event_bus: Any):
        self.bus = event_bus
        self._tick_counter = 0
        print("[AccessibilityDriver] Initialized and binding to EventBus...")
        
        # Subscribe to the heartbeat to trigger polling
        self.bus.subscribe("TICK", self._on_tick)

    def _on_tick(self, payload: Any) -> None:
        self._tick_counter += 1
        # Poll every 5 ticks (5 seconds) to avoid CPU/battery thrashing
        if self._tick_counter % 5 == 0:
            self.capture_tree()

    def capture_tree(self) -> Optional[str]:
        """Dumps the UI hierarchy using Shizuku/Rish."""
        try:
            # Execute uiautomator via rish. 
            # We dump to /data/local/tmp as it has predictable permissions.
            dump_cmd = [
                "rish", "-c", 
                "uiautomator dump /data/local/tmp/ui_dump.xml > /dev/null && cat /data/local/tmp/ui_dump.xml"
            ]
            
            result = subprocess.run(
                dump_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout:
                xml_data = result.stdout.strip()
                print(f"[AccessibilityDriver] Captured UI tree ({len(xml_data)} bytes)")
                
                # Publish the raw XML payload to the bus
                self.bus.publish("UI_UPDATED", xml_data)
                return xml_data
            else:
                print(f"[AccessibilityDriver] Failed to dump UI. Ensure rish is initialized. stderr: {result.stderr.strip()}")
                return None
                
        except FileNotFoundError:
            print("[AccessibilityDriver] Error: 'rish' command not found in PATH.")
            return None
        except Exception as e:
            print(f"[AccessibilityDriver] Exception during capture: {e}")
            return None
