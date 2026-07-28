#!/usr/bin/env python3
import sys
from pathlib import Path

# force the autonomy package onto the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from event_bus import EventBus
from executor import Executor

bus = EventBus()
ex = Executor(event_bus=bus)

g = ex.create_goal("supervisor_demo", "will be failed then recovered")
ex.start_goal(g.id)
ex.update_progress(g.id, 0.2, {"phase": "before_crash"})
ex.fail_goal(g.id, "demo crash")

print(f"✅ Created & failed: {g.id}")
print(f"   name   : {g.name}")
print(f"   status : should be FAILED")
print()
print("Now run the supervisor:")
print("  python3 \~/broccoli-core/autonomy/supervisor.py --once")
