#!/usr/bin/env python3
"""
Autonomous Task Executive for Broccoli Core (v2 – concurrency + recovery).

Wraps the existing brain.py queue and rish/uiautomator loop into
formal Goal objects with checkpoints, persistence, event emission,
thread-safe file I/O, and basic automatic recovery.
"""

import logging
import json
import time
import uuid
import threading
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Optional, List, Dict, Any
from pathlib import Path

# Event constants
GOAL_CREATED   = "GOAL_CREATED"
GOAL_STARTED   = "GOAL_STARTED"
GOAL_PROGRESS  = "GOAL_PROGRESS"
GOAL_BLOCKED   = "GOAL_BLOCKED"
GOAL_COMPLETED = "GOAL_COMPLETED"
GOAL_FAILED    = "GOAL_FAILED"
GOAL_RECOVERED = "GOAL_RECOVERED"
GOAL_CANCELLED = "GOAL_CANCELLED"

class GoalStatus(Enum):
    PENDING   = auto()
    RUNNING   = auto()
    BLOCKED   = auto()
    COMPLETED = auto()
    FAILED    = auto()
    CANCELLED = auto()

@dataclass
class Checkpoint:
    step: int
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

@dataclass
class Goal:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    parent_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    status: GoalStatus = GoalStatus.PENDING
    progress: float = 0.0
    confidence: float = 1.0
    checkpoints: List[Checkpoint] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

class Executor:
    def __init__(self,
                 storage_path: Optional[Path] = None,
                 event_bus: Optional[Any] = None,
                 governor: Optional[Any] = None,
                 planner: Optional[Any] = None,
                 workflow_engine: Optional[Any] = None,
                 knowledge_graph: Optional[Any] = None,
                 agent_coordinator: Optional[Any] = None):
        self.logger = logging.getLogger("broccoli.executor")
        self.storage_path = storage_path or Path.home() / ".broccoli" / "goals.json"
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()          # concurrency safety

        self.event_bus = event_bus
        self.governor = governor
        self.planner = planner
        self.workflow_engine = workflow_engine
        self.knowledge_graph = knowledge_graph
        self.agent_coordinator = agent_coordinator

        self.goals: Dict[str, Goal] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self._load_persistent_goals()

    # ── internal helpers ──────────────────────────────────────────────
    def _emit(self, event_type: str, goal_id: str, data: Optional[Dict] = None):
        if self.event_bus:
            payload = {"goal_id": goal_id, "timestamp": time.time()}
            if data:
                payload.update(data)
            self.event_bus.emit(event_type, payload)
        self.logger.info(f"Event: {event_type} for {goal_id}")

    def _load_persistent_goals(self):
        with self._lock:
            if not self.storage_path.exists():
                return
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                for gdata in data.get("goals", []):
                    if isinstance(gdata.get("status"), str):
                        gdata["status"] = GoalStatus[gdata["status"]]
                    cps = [Checkpoint(**cp) for cp in gdata.get("checkpoints", [])]
                    gdata["checkpoints"] = cps
                    goal = Goal(**gdata)
                    self.goals[goal.id] = goal
                self.logger.info(f"Loaded {len(self.goals)} persistent goals")
            except Exception as e:
                self.logger.error(f"Failed to load goals: {e}")

    def _save_persistent_goals(self):
        with self._lock:
            try:
                serializable = []
                for g in self.goals.values():
                    d = asdict(g)
                    d["status"] = g.status.name
                    serializable.append(d)
                data = {"goals": serializable, "last_saved": time.time()}
                with open(self.storage_path, "w") as f:
                    json.dump(data, f, indent=2, default=str)
            except Exception as e:
                self.logger.error(f"Failed to save goals: {e}")

    # ── public API ────────────────────────────────────────────────────
    def create_goal(self, name: str, description: str = "",
                    parent_id: Optional[str] = None,
                    dependencies: Optional[List[str]] = None,
                    metadata: Optional[Dict] = None,
                    max_retries: int = 3) -> Goal:
        with self._lock:
            goal = Goal(
                name=name,
                description=description,
                parent_id=parent_id,
                dependencies=dependencies or [],
                metadata=metadata or {},
                max_retries=max_retries
            )
            self.goals[goal.id] = goal
            self._save_persistent_goals()
            self._emit(GOAL_CREATED, goal.id, {"name": name})
            return goal

    def start_goal(self, goal_id: str) -> bool:
        with self._lock:
            if goal_id not in self.goals:
                return False
            goal = self.goals[goal_id]
            if goal.status not in (GoalStatus.PENDING, GoalStatus.BLOCKED, GoalStatus.FAILED):
                return False

            for dep_id in goal.dependencies:
                if dep_id in self.goals and self.goals[dep_id].status != GoalStatus.COMPLETED:
                    goal.status = GoalStatus.BLOCKED
                    self._emit(GOAL_BLOCKED, goal_id, {"reason": f"waiting for {dep_id}"})
                    self._save_persistent_goals()
                    return False

            goal.status = GoalStatus.RUNNING
            goal.started_at = time.time()
            goal.error = None
            self._save_persistent_goals()
            self._emit(GOAL_STARTED, goal_id)
            return True

    def update_progress(self, goal_id: str, progress: float,
                        checkpoint_data: Optional[Dict] = None,
                        confidence: Optional[float] = None):
        with self._lock:
            if goal_id not in self.goals:
                return
            goal = self.goals[goal_id]
            goal.progress = max(0.0, min(1.0, progress))
            if confidence is not None:
                goal.confidence = max(0.0, min(1.0, confidence))
            if checkpoint_data:
                cp = Checkpoint(step=len(goal.checkpoints), data=checkpoint_data)
                goal.checkpoints.append(cp)
            self._save_persistent_goals()
            self._emit(GOAL_PROGRESS, goal_id, {
                "progress": goal.progress,
                "confidence": goal.confidence,
                "checkpoint_count": len(goal.checkpoints)
            })

    def complete_goal(self, goal_id: str):
        with self._lock:
            if goal_id not in self.goals:
                return
            goal = self.goals[goal_id]
            goal.status = GoalStatus.COMPLETED
            goal.progress = 1.0
            goal.completed_at = time.time()
            self._save_persistent_goals()
            self._emit(GOAL_COMPLETED, goal_id)

            # wake dependents
            for g in self.goals.values():
                if g.status == GoalStatus.BLOCKED and goal_id in g.dependencies:
                    self.start_goal(g.id)

    def fail_goal(self, goal_id: str, error: str):
        with self._lock:
            if goal_id not in self.goals:
                return
            goal = self.goals[goal_id]
            goal.status = GoalStatus.FAILED
            goal.error = error
            goal.completed_at = time.time()
            self._save_persistent_goals()
            self._emit(GOAL_FAILED, goal_id, {"error": error})

    def cancel_goal(self, goal_id: str):
        with self._lock:
            if goal_id not in self.goals:
                return
            goal = self.goals[goal_id]
            goal.status = GoalStatus.CANCELLED
            goal.completed_at = time.time()
            self._save_persistent_goals()
            self._emit(GOAL_CANCELLED, goal_id)

    def recover_goal(self, goal_id: str) -> bool:
        """
        Attempt to resume a FAILED or interrupted goal from its last checkpoint.
        Increments retry_count; gives up after max_retries.
        """
        with self._lock:
            if goal_id not in self.goals:
                return False
            goal = self.goals[goal_id]

            if goal.status not in (GoalStatus.FAILED, GoalStatus.RUNNING):
                return False

            if goal.retry_count >= goal.max_retries:
                self.logger.warning(f"Goal {goal_id} exceeded max_retries ({goal.max_retries})")
                return False

            goal.retry_count += 1
            goal.status = GoalStatus.RUNNING
            goal.error = None
            goal.started_at = time.time()
            self._save_persistent_goals()
            self._emit(GOAL_RECOVERED, goal_id, {
                "retry_count": goal.retry_count,
                "last_checkpoint": goal.checkpoints[-1].data if goal.checkpoints else None
            })
            self.logger.info(f"Recovered goal {goal_id} (attempt {goal.retry_count})")
            return True

    def get_resume_checkpoint(self, goal_id: str) -> Optional[Checkpoint]:
        with self._lock:
            if goal_id not in self.goals:
                return None
            goal = self.goals[goal_id]
            return goal.checkpoints[-1] if goal.checkpoints else None

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        with self._lock:
            return self.goals.get(goal_id)

    def list_goals(self, status: Optional[GoalStatus] = None) -> List[Goal]:
        with self._lock:
            if status is None:
                return list(self.goals.values())
            return [g for g in self.goals.values() if g.status == status]

    def get_execution_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self.execution_history.copy()


# ── self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ex = Executor()

    g = ex.create_goal("test_goal_v2", "concurrency + recovery smoke test")
    print(f"Created: {g.id}")

    assert ex.start_goal(g.id)
    ex.update_progress(g.id, 0.4, {"step": "midway"})
    ex.fail_goal(g.id, "simulated crash")

    assert ex.recover_goal(g.id)
    cp = ex.get_resume_checkpoint(g.id)
    print(f"Resumed from checkpoint: {cp.data if cp else None}")

    ex.update_progress(g.id, 1.0, {"step": "done"})
    ex.complete_goal(g.id)

    print("✅ Self-test passed (v2)")
    print(f"Goals file: {ex.storage_path}")
