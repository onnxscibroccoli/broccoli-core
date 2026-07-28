#!/usr/bin/env python3
"""
Simple auto-recover supervisor for Broccoli Core.

Two modes:
  1. Event-driven (preferred) – listens on EventBus for GOAL_FAILED
  2. Polling fallback – scans goals.json every N seconds

Usage:
  python3 supervisor.py              # event + light poll hybrid
  python3 supervisor.py --once       # single pass then exit
  python3 supervisor.py --poll 10    # poll every 10 s, no bus required
"""

import sys
import time
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from event_bus import EventBus
from executor import Executor, GoalStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("broccoli.supervisor")

class Supervisor:
    def __init__(self, poll_interval: float = 15.0):
        self.bus = EventBus()
        self.ex = Executor(event_bus=self.bus)
        self.poll_interval = poll_interval
        self._running = False

        # react immediately when something fails
        self.bus.subscribe("GOAL_FAILED", self._on_failed)

    def _on_failed(self, event):
        goal_id = event["payload"].get("goal_id")
        if not goal_id:
            return
        log.info(f"GOAL_FAILED received for {goal_id[:8]}… – attempting recover")
        ok = self.ex.recover_goal(goal_id)
        if ok:
            log.info(f"Recovered {goal_id[:8]}…")
        else:
            log.warning(f"Could not recover {goal_id[:8]}… (max retries or bad state)")

    def scan_once(self) -> int:
        """Look for FAILED goals and try to recover them. Returns count recovered."""
        recovered = 0
        for g in self.ex.list_goals(GoalStatus.FAILED):
            log.info(f"Found FAILED goal {g.id[:8]}… ({g.name}) – retry {g.retry_count}/{g.max_retries}")
            if self.ex.recover_goal(g.id):
                recovered += 1
                log.info(f"  → recovered")
            else:
                log.warning(f"  → gave up")
        return recovered

    def run(self, once: bool = False):
        self._running = True
        log.info("Supervisor started")
        try:
            while self._running:
                self.scan_once()
                if once:
                    break
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            log.info("Supervisor stopped by user")
        finally:
            self._running = False

def main():
    parser = argparse.ArgumentParser(description="Broccoli auto-recover supervisor")
    parser.add_argument("--once", action="store_true", help="Single scan then exit")
    parser.add_argument("--poll", type=float, default=15.0, help="Poll interval seconds")
    args = parser.parse_args()

    sup = Supervisor(poll_interval=args.poll)
    sup.run(once=args.once)

if __name__ == "__main__":
    main()
