#!/usr/bin/env python3
"""Quick wiring test: Executor + EventBus"""

import logging
import sys
sys.path.insert(0, "/data/data/com.termux/files/home/broccoli-core/autonomy")

from event_bus import EventBus
from executor import Executor

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

bus = EventBus()
seen = []

def capture(event):
    seen.append(event["type"])
    print(f"  bus → {event['type']}")

bus.subscribe("*", capture)

ex = Executor(event_bus=bus)

g = ex.create_goal("integration_test", "Executor ↔ EventBus")
ex.start_goal(g.id)
ex.update_progress(g.id, 0.3, {"phase": "setup"})
ex.fail_goal(g.id, "simulated")
ex.recover_goal(g.id)
ex.update_progress(g.id, 1.0, {"phase": "done"})
ex.complete_goal(g.id)

expected = {
    "GOAL_CREATED", "GOAL_STARTED", "GOAL_PROGRESS",
    "GOAL_FAILED", "GOAL_RECOVERED", "GOAL_PROGRESS", "GOAL_COMPLETED"
}
got = set(seen)
missing = expected - got
print()
if not missing:
    print("✅ Integration test passed – all events reached the bus")
else:
    print(f"❌ Missing events: {missing}")
print(f"Total events captured: {len(seen)}")
print(f"History on bus: {len(bus.get_history())}")
