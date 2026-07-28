#!/usr/bin/env python3
"""
Thin bridge between Broccoli Core's existing reactive round loop
and the new Goal / Executor / EventBus autonomy layer.

Usage from brain.py or broccoli_core_round.py:

    from bridge import RoundBridge
    bridge = RoundBridge()

    # at the start of a logical unit of work
    goal_id = bridge.begin("do_something", meta={"round": 42})

    # after each meaningful step
    bridge.checkpoint(goal_id, {"step": "clicked_button", "x": 120, "y": 340})
    bridge.progress(goal_id, 0.4)

    # on success
    bridge.succeed(goal_id)

    # on failure / wire break
    bridge.fail(goal_id, "uiautomator dump timed out")
"""

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from event_bus import EventBus
from executor import Executor, GoalStatus

log = logging.getLogger("broccoli.bridge")

class RoundBridge:
    """
    One long-lived instance is enough.
    It owns an Executor + EventBus and maps simple calls
    onto the Goal lifecycle.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.bus = EventBus()
        self.ex = Executor(event_bus=self.bus, storage_path=storage_path)
        # optional: keep a map of "current" goal per logical name
        self._active: Dict[str, str] = {}   # name -> goal_id

    # ── primary API ───────────────────────────────────────────────────

    def begin(self, name: str, description: str = "",
              meta: Optional[Dict[str, Any]] = None,
              max_retries: int = 3) -> str:
        """
        Start (or resume) a goal for this unit of work.
        Returns goal_id.
        """
        # if we already have an active goal with this name that is still
        # RUNNING or FAILED, resume it instead of creating a duplicate
        for g in self.ex.list_goals():
            if g.name == name and g.status in (GoalStatus.RUNNING, GoalStatus.FAILED):
                if g.status == GoalStatus.FAILED:
                    self.ex.recover_goal(g.id)
                self._active[name] = g.id
                log.info(f"Resumed existing goal {g.id[:8]}… for '{name}'")
                return g.id

        g = self.ex.create_goal(name, description or name,
                                metadata=meta or {}, max_retries=max_retries)
        self.ex.start_goal(g.id)
        self._active[name] = g.id
        log.info(f"Started new goal {g.id[:8]}… for '{name}'")
        return g.id

    def progress(self, goal_id: str, fraction: float,
                 checkpoint: Optional[Dict[str, Any]] = None,
                 confidence: Optional[float] = None):
        """Update progress 0.0–1.0 and optionally drop a checkpoint."""
        self.ex.update_progress(goal_id, fraction,
                                checkpoint_data=checkpoint,
                                confidence=confidence)

    def checkpoint(self, goal_id: str, data: Dict[str, Any]):
        """Convenience: record a checkpoint without changing progress."""
        g = self.ex.get_goal(goal_id)
        if g is None:
            return
        # keep current progress, just add the checkpoint
        self.ex.update_progress(goal_id, g.progress, checkpoint_data=data)

    def succeed(self, goal_id: str):
        """Mark the goal COMPLETED."""
        self.ex.complete_goal(goal_id)
        # clean active map
        for name, gid in list(self._active.items()):
            if gid == goal_id:
                del self._active[name]

    def fail(self, goal_id: str, reason: str):
        """Mark the goal FAILED. Supervisor can recover it later."""
        self.ex.fail_goal(goal_id, reason)

    def recover(self, goal_id: str) -> bool:
        """Manual recover (usually left to the supervisor)."""
        return self.ex.recover_goal(goal_id)

    # ── helpers ───────────────────────────────────────────────────────

    def current(self, name: str) -> Optional[str]:
        """Return the active goal_id for a logical name, if any."""
        return self._active.get(name)

    def list_active(self):
        """Return currently RUNNING goals."""
        return self.ex.list_goals(GoalStatus.RUNNING)


# ── self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    b = RoundBridge()

    gid = b.begin("demo_round", meta={"source": "bridge_selftest"})
    b.checkpoint(gid, {"action": "tap", "x": 100, "y": 200})
    b.progress(gid, 0.5, {"phase": "halfway"})
    b.checkpoint(gid, {"action": "type", "text": "hello"})
    b.progress(gid, 1.0)
    b.succeed(gid)

    print("✅ bridge self-test passed")
    print(f"Active goals now: {len(b.list_active())}")
