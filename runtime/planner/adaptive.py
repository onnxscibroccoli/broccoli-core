from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from runtime.eventbus.service import bus as default_bus
from runtime.memory.knowledge_graph import KnowledgeGraph

try:
    from runtime.event_bus.publisher import publish as write_event
except Exception:  # pragma: no cover
    def write_event(source, event, detail="", severity="INFO", metadata=None):
        return {
            "timestamp": int(time.time()),
            "source": source,
            "event": event,
            "severity": severity,
            "detail": detail,
            "metadata": metadata or {},
        }


ADAPTIVE_TOPICS = {
    "ADAPTIVE_PLAN_CREATED",
    "ADAPTIVE_FEEDBACK",
    "ADAPTIVE_LEARNED",
    "ADAPTIVE_ADJUSTED",
    "ADAPTIVE_OK",
    "ADAPTIVE_WARNING",
    "ADAPTIVE_CRITICAL",
    "ADAPTIVE_RECOVERED",
    "ADAPTIVE_DEGRADED",
    "ADAPTIVE_HEARTBEAT",
    "KNOWLEDGE_OK",
    "KNOWLEDGE_WARNING",
    "KNOWLEDGE_CRITICAL",
    "KNOWLEDGE_RECOVERED",
    "KNOWLEDGE_HEARTBEAT",
}


@dataclass
class PlanStep:
    step_id: str
    description: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    status: str = "pending"
    result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdaptiveSnapshot:
    timestamp: int
    status: str
    plan_count: int
    feedback_count: int
    knowledge_status: str
    last_goal: Optional[str] = None
    last_activity_age_seconds: Optional[float] = None
    note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "plan_count": self.plan_count,
            "feedback_count": self.feedback_count,
            "knowledge_status": self.knowledge_status,
            "last_goal": self.last_goal,
            "last_activity_age_seconds": self.last_activity_age_seconds,
            "note": self.note,
            "metadata": dict(self.metadata),
        }


class AdaptivePlanner:
    """
    Adaptive planner integration backed by the persistent knowledge graph.

    The planner produces structured plans, records execution feedback, and uses
    the knowledge graph as the persistent memory layer for future decisions.
    """

    def __init__(
        self,
        bus=None,
        root: Optional[Path] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        event_writer: Optional[Callable[..., Dict[str, Any]]] = None,
        warning_seconds: int = 120,
        critical_seconds: int = 300,
        heartbeat_interval_seconds: int = 60,
    ):
        self.bus = bus or default_bus
        self.root = Path(root or Path.cwd())
        self.event_writer = event_writer or write_event
        self.warning_seconds = warning_seconds
        self.critical_seconds = critical_seconds
        self.heartbeat_interval_seconds = heartbeat_interval_seconds

        self.processed_dir = self.root / "runtime" / "event_bus" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.knowledge_graph = knowledge_graph or KnowledgeGraph(
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )

        self.started_at = time.time()
        self.last_plan_at: Optional[float] = None
        self.last_feedback_at: Optional[float] = None
        self.last_snapshot: Optional[AdaptiveSnapshot] = None
        self.last_emit_at: float = 0.0
        self.running = False
        self.plan_count = 0
        self.feedback_count = 0
        self.last_goal: Optional[str] = None

        for topic in ADAPTIVE_TOPICS:
            try:
                self.bus.subscribe(topic, self._on_event)
            except Exception:
                pass


    def start(self):
        self.running = True
        return self

    def stop(self):
        self.running = False
        return self

    def health(self):
        snapshot = self.collect_health()
        return {
            "running": self.running,
            "plan_count": self.plan_count,
            "feedback_count": self.feedback_count,
            "last_goal": self.last_goal,
            "snapshot": snapshot.to_dict(),
        }

    def _payload_of(self, event: Any) -> Dict[str, Any]:
        if event is None:
            return {}
        if isinstance(event, dict):
            return event
        payload = getattr(event, "payload", None)
        if isinstance(payload, dict):
            return payload
        try:
            return dict(event)
        except Exception:
            return {}

    def _topic_of(self, event: Any, payload: Dict[str, Any]) -> str:
        topic = getattr(event, "topic", None) or payload.get("topic") or payload.get("event")
        return str(topic or "UNKNOWN")

    def _on_event(self, event: Any) -> None:
        payload = self._payload_of(event)
        topic = self._topic_of(event, payload)
        if topic.startswith("KNOWLEDGE_"):
            # KnowledgeGraph already tracks its own health; we only keep planner
            # state aligned when knowledge activity is visible.
            self.last_feedback_at = self.last_feedback_at or time.time()

    def _publish(
        self,
        topic: str,
        event: str,
        severity: str = "INFO",
        detail: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "timestamp": int(time.time()),
            "source": "adaptive_planner",
            "event": event,
            "severity": severity,
            "detail": detail,
            "metadata": metadata or {},
        }

        self.event_writer(
            source="adaptive_planner",
            event=event,
            detail=detail,
            severity=severity,
            metadata=metadata or {},
        )

        try:
            self.bus.publish(topic, payload, source="AdaptivePlanner")
        except Exception:
            pass

        out = self.processed_dir / f"adaptive_{int(time.time())}.json"
        try:
            out.write_text(json.dumps(payload, indent=2))
        except Exception:
            pass

        self.last_emit_at = time.time()
        return payload

    def _tokenize(self, text: str) -> List[str]:
        tokens = []
        for raw in text.replace("/", " ").replace("-", " ").split():
            token = raw.strip(".,;:!?()[]{}<>\"'").lower()
            if len(token) >= 3:
                tokens.append(token)
        return tokens

    def _related_nodes(self, goal: str) -> List[str]:
        goal_tokens = set(self._tokenize(goal))
        if not goal_tokens:
            return []

        related: List[str] = []
        for node_id, node in self.knowledge_graph.nodes.items():
            haystack = " ".join([
                node_id,
                json.dumps(node.content, sort_keys=True),
                " ".join(node.tags),
                json.dumps(node.metadata, sort_keys=True),
            ]).lower()
            if any(token in haystack for token in goal_tokens):
                related.append(node_id)

        return related[:5]

    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = dict(context or {})
        related = self._related_nodes(goal)
        plan_id = f"plan_{int(time.time())}"

        steps: List[PlanStep] = []
        if related:
            for idx, node_id in enumerate(related, start=1):
                steps.append(
                    PlanStep(
                        step_id=f"{plan_id}_reuse_{idx}",
                        description=f"Reuse prior pattern from knowledge node {node_id}",
                        inputs={"knowledge_node": node_id},
                        expected_outcome="Incorporate prior successful pattern.",
                    )
                )

        steps.extend(
            [
                PlanStep(
                    step_id=f"{plan_id}_decompose",
                    description=f"Decompose goal: {goal}",
                    inputs={"goal": goal, "context": context},
                    expected_outcome="Break the goal into executable actions.",
                ),
                PlanStep(
                    step_id=f"{plan_id}_execute",
                    description="Execute the next best action from the plan.",
                    inputs={"goal": goal},
                    expected_outcome="Advance the goal without blocking.",
                ),
                PlanStep(
                    step_id=f"{plan_id}_verify",
                    description="Verify the result of the action.",
                    inputs={"goal": goal},
                    expected_outcome="Confirm the outcome is correct.",
                ),
                PlanStep(
                    step_id=f"{plan_id}_learn",
                    description="Record the execution result and learning signal.",
                    inputs={"goal": goal},
                    expected_outcome="Persist the lesson into the knowledge graph.",
                ),
            ]
        )

        goal_node = self.knowledge_graph.upsert_node(
            node_id=f"goal_{plan_id}",
            content={"goal": goal, "context": context, "plan_id": plan_id},
            tags=["adaptive", "goal"],
            metadata={"goal": goal, "plan_id": plan_id},
        )
        plan_node = self.knowledge_graph.upsert_node(
            node_id=plan_id,
            content={
                "goal": goal,
                "steps": [step.to_dict() for step in steps],
                "related_nodes": related,
                "context": context,
            },
            tags=["adaptive", "plan"],
            metadata={"goal": goal, "plan_id": plan_id},
        )
        self.knowledge_graph.add_edge(goal_node.node_id, plan_node.node_id, relation="drives")

        self.last_plan_at = time.time()
        self.plan_count += 1
        self.last_goal = goal

        self._publish(
            "ADAPTIVE_PLAN_CREATED",
            "ADAPTIVE_PLAN_CREATED",
            severity="INFO",
            detail=f"Created plan for goal: {goal}",
            metadata={
                "plan_id": plan_id,
                "goal": goal,
                "steps": [step.to_dict() for step in steps],
                "related_nodes": related,
                "context": context,
            },
        )

        return {
            "plan_id": plan_id,
            "goal": goal,
            "steps": [step.to_dict() for step in steps],
            "related_nodes": related,
            "goal_node": goal_node.to_dict(),
            "plan_node": plan_node.to_dict(),
        }

    def record_feedback(
        self,
        plan_id: str,
        step_id: str,
        success: bool,
        feedback: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = dict(context or {})
        feedback_id = f"feedback_{int(time.time())}"
        payload = {
            "plan_id": plan_id,
            "step_id": step_id,
            "success": bool(success),
            "feedback": feedback,
            "context": context,
        }

        self.knowledge_graph.upsert_node(
            node_id=feedback_id,
            content=payload,
            tags=["adaptive", "feedback", "success" if success else "failure"],
            metadata={"plan_id": plan_id, "step_id": step_id, "success": bool(success)},
        )
        self.knowledge_graph.add_edge(plan_id, feedback_id, relation="evaluated_by", metadata={"step_id": step_id, "success": bool(success)})

        self.last_feedback_at = time.time()
        self.feedback_count += 1

        self._publish(
            "ADAPTIVE_FEEDBACK",
            "ADAPTIVE_FEEDBACK",
            severity="INFO" if success else "WARNING",
            detail=feedback or ("Execution succeeded." if success else "Execution failed."),
            metadata=payload,
        )
        self._publish(
            "ADAPTIVE_LEARNED" if success else "ADAPTIVE_ADJUSTED",
            "ADAPTIVE_LEARNED" if success else "ADAPTIVE_ADJUSTED",
            severity="INFO" if success else "WARNING",
            detail=feedback or ("Learning recorded." if success else "Plan adjusted."),
            metadata=payload,
        )

        return payload

    def _knowledge_status(self) -> Tuple[str, str, Optional[float]]:
        snapshot = self.knowledge_graph.collect_health()
        return snapshot.status, snapshot.note, snapshot.last_activity_age_seconds

    def collect_health(self) -> AdaptiveSnapshot:
        knowledge_status, knowledge_note, knowledge_age = self._knowledge_status()

        status = "ADAPTIVE_OK"
        note = "Adaptive planner is operating."

        ages: List[float] = []
        if self.last_plan_at is not None:
            ages.append(max(0.0, time.time() - self.last_plan_at))
        if self.last_feedback_at is not None:
            ages.append(max(0.0, time.time() - self.last_feedback_at))
        if knowledge_age is not None:
            ages.append(knowledge_age)

        last_activity_age = round(max(ages), 2) if ages else None

        if knowledge_status == "KNOWLEDGE_CRITICAL":
            status = "ADAPTIVE_CRITICAL"
            note = "Knowledge graph is critical."
        elif self.last_plan_at is None:
            status = "ADAPTIVE_WARNING"
            note = "No adaptive plans created yet."
        elif last_activity_age is not None and last_activity_age > self.critical_seconds:
            status = "ADAPTIVE_CRITICAL"
            note = "Adaptive planner activity is stale."
        elif last_activity_age is not None and last_activity_age > self.warning_seconds:
            status = "ADAPTIVE_WARNING"
            note = "Adaptive planner activity is aging."

        return AdaptiveSnapshot(
            timestamp=int(time.time()),
            status=status,
            plan_count=self.plan_count,
            feedback_count=self.feedback_count,
            knowledge_status=knowledge_status,
            last_goal=self.last_goal,
            last_activity_age_seconds=last_activity_age,
            note=note if status != "ADAPTIVE_OK" else knowledge_note or note,
            metadata={
                "started_at": int(self.started_at),
                "warning_seconds": self.warning_seconds,
                "critical_seconds": self.critical_seconds,
                "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
                "knowledge_status": knowledge_status,
                "knowledge_note": knowledge_note,
            },
        )

    def _transition_events(self, previous: Optional[AdaptiveSnapshot], current: AdaptiveSnapshot):
        if previous is None:
            return [(current.status, current.status, current.note)]

        events = []
        if previous.status != current.status:
            events.append((current.status, current.status, current.note))
            if previous.status == "ADAPTIVE_OK" and current.status in {"ADAPTIVE_WARNING", "ADAPTIVE_CRITICAL"}:
                events.append(("ADAPTIVE_DEGRADED", "ADAPTIVE_DEGRADED", current.note))
            if previous.status in {"ADAPTIVE_WARNING", "ADAPTIVE_CRITICAL"} and current.status == "ADAPTIVE_OK":
                events.append(("ADAPTIVE_RECOVERED", "ADAPTIVE_RECOVERED", current.note))
        elif current.status == "ADAPTIVE_OK" and (time.time() - self.last_emit_at) >= self.heartbeat_interval_seconds:
            events.append(("ADAPTIVE_HEARTBEAT", "ADAPTIVE_HEARTBEAT", current.note))

        return events

    def run_once(self) -> AdaptiveSnapshot:
        snapshot = self.collect_health()
        for topic, event, detail in self._transition_events(self.last_snapshot, snapshot):
            self._publish(
                topic,
                event,
                severity="INFO" if topic in {"ADAPTIVE_OK", "ADAPTIVE_RECOVERED", "ADAPTIVE_HEARTBEAT"} else "WARNING",
                detail=detail,
                metadata=snapshot.to_dict(),
            )
        self.last_snapshot = snapshot
        return snapshot

    def verify_integration(self) -> Dict[str, Any]:
        knowledge_ok = self.knowledge_graph.verify_roundtrip()
        plan = self.plan(
            "verify adaptive planner integration",
            {"mode": "verify", "source": "runtime/planner/adaptive.py"},
        )
        self.record_feedback(
            plan_id=plan["plan_id"],
            step_id=plan["steps"][0]["step_id"],
            success=True,
            feedback="Adaptive planner verification passed.",
            context={"verification": True},
        )
        snapshot = self.run_once()
        return {
            "knowledge_roundtrip": knowledge_ok,
            "plan_id": plan["plan_id"],
            "status": snapshot.status,
            "snapshot": snapshot.to_dict(),
        }

    def run_forever(self, interval_seconds: int = 60) -> None:
        self.start()
        while self.running:
            self.run_once()
            time.sleep(interval_seconds)

    def stop(self) -> None:
        self.running = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Broccoli Core Adaptive Planner")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    parser.add_argument("--verify", action="store_true", help="Run a knowledge/planning roundtrip verification")
    args = parser.parse_args()

    planner = AdaptivePlanner()
    if args.verify:
        print(json.dumps(planner.verify_integration(), indent=2))
        return

    if args.loop:
        planner.run_forever(interval_seconds=args.interval)
    else:
        print(json.dumps(planner.run_once().to_dict(), indent=2))


if __name__ == "__main__":
    main()
