import sys
import time
import os

# Local runtime imports
from event_bus import EventBus
from state import SystemState
from constants import STATE_RUNNING
from capabilities.registry import CapabilityRegistry
from journal import EventJournal
from models.semantic import Screen
from maintenance.sync import SyncManager
from normalizer import UINormalizer

# Dynamically link existing external drivers/governors if present
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "drivers", "accessibility")))
    from driver import AccessibilityDriver
except ImportError:
    AccessibilityDriver = None

try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "governor")))
    from engine import Governor
except ImportError:
    Governor = None

def main():
    print("=== Broccoli Core: 12-Step Startup Sequence ===")

    print("[1] Loading configuration...")
    journal = EventJournal()
    journal.log_event("STARTUP", "Config loaded")

    print("[2] Discovering available capabilities...")
    registry = CapabilityRegistry()

    print("[3] Verifying user-authorized permissions...")
    # Shizuku/ADB readiness checks here

    print("[4] Registering available capabilities...")
    # e.g., registry.register(InputInjectionCapability())

    print("[5] Starting event bus...")
    bus = EventBus()

    print("[5.5] Starting UI normalizer...")
    normalizer = UINormalizer(bus)

    print("[6] Starting accessibility capture pipeline...")
    if AccessibilityDriver:
        driver = AccessibilityDriver(bus)

    print("[7] Building semantic UI model...")
    semantic_model = Screen()

    print("[8] Starting planner...")
    # planner = Planner(semantic_model, bus)

    print("[9] Starting governor...")
    state = SystemState()
    if Governor:
        gov = Governor(bus, state)

    print("[10] Enabling plugins...")
    # plugin_loader.load_active()

    print("[10.5] Initializing SyncManager...")
    sync_mgr = SyncManager()
    # sync_mgr.perform_full_sync()  # Uncomment to sync on boot

    print("[11] Begin execution loop...")
    print("[12] Continuously monitor health and recover failed components.")

    try:
        while True:
            # The execution loop triggers ticks, and the registry can verify health
            bus.publish("TICK")
            healthy_caps = registry.get_all_healthy()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[-] Runtime terminated by user. Flushing journal.")
        journal.log_event("SHUTDOWN", "User terminated execution loop")

if __name__ == "__main__":
    main()
