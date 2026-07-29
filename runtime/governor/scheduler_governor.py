from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from runtime.eventbus.service import bus as default_bus

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


SCHEDULER_TOPICS = {
    "TICK",
    "TICK_ADVANCED",
    "SCHEDULER_TICK",
    "TASK_ENQUEUED",
    "TASK_STARTED",
    "TASK_FINISHED",
    "TASK_FAILED",
    "TIMER_FIRED",
    "SCHEDULER_HEARTBEAT",
}


@dataclass
class SchedulerSnapshot:
    timestamp: int
    status: str
    last_event_topic: Optional[str] = None
    last_event_age_seconds: Optional[float] = None
    event_counts: Dict[str, int] = field(default_factory=dict)
    note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "last_event_topic": self.last_event_topic,
            "last_event_age_seconds": self.last_event_age_seconds,
            "event_counts": dict(self.event_counts),
            "note": self.note,
            "metadata": dict(self.metadata),
        }


class SchedulerGovernor:
    """
    Supervises scheduler freshness and tick progression.

    The governor listens for scheduler-related events and evaluates whether the
    runtime tick stream is healthy, warning, or stale.
    """

    def __init__(
        self,
        bus=None,
        root: Optional[Path] = None,
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

        self.started_at = time.time()
        self.last_event_at: Optional[float] = None
        self.last_event_topic: Optional[str] = None
        self.last_snapshot: Optional[SchedulerSnapshot] = None
        self.last_emit_at: float = 0.0
        self.running = False
        self.event_counts = defaultdict(int)

        for topic in SCHEDULER_TOPICS:
            try:
                self.bus.subscribe(topic, self._on_scheduler_event)
            except Exception:
                pass

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

    def _on_scheduler_event(self, event: Any) -> None:
        payload = self._payload_of(event)
        topic = self._topic_of(event, payload)
        self.last_event_at = time.time()
        self.last_event_topic = topic
        self.event_counts[topic] += 1

    def _classify(self) -> Tuple[str, str]:
        if self.last_event_at is None:
            return "SCHEDULER_WARNING", "No scheduler events observed yet."

        age = max(0.0, time.time() - self.last_event_at)
        if age <= self.warning_seconds:
            return "SCHEDULER_OK", "Scheduler stream is fresh."
        if age <= self.critical_seconds:
            return "SCHEDULER_WARNING", "Scheduler stream is aging."
        return "SCHEDULER_CRITICAL", "Scheduler stream is stale."

    def collect(self) -> SchedulerSnapshot:
        status, note = self._classify()
        age = None if self.last_event_at is None else round(max(0.0, time.time() - self.last_event_at), 2)

        return SchedulerSnapshot(
            timestamp=int(time.time()),
            status=status,
            last_event_topic=self.last_event_topic,
            last_event_age_seconds=age,
            event_counts=dict(self.event_counts),
            note=note,
            metadata={
                "started_at": int(self.started_at),
                "warning_seconds": self.warning_seconds,
                "critical_seconds": self.critical_seconds,
                "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            },
        )

    def _severity_for(self, status: str) -> str:
        return {
            "SCHEDULER_OK": "INFO",
            "SCHEDULER_WARNING": "WARNING",
            "SCHEDULER_CRITICAL": "CRITICAL",
        }.get(status, "INFO")

    def _emit(self, topic: str, snapshot: SchedulerSnapshot, severity: str = "INFO", detail: str = "") -> None:
        payload = {
            "timestamp": snapshot.timestamp,
            "source": "scheduler_governor",
            "event": topic,
            "severity": severity,
            "detail": detail or snapshot.note,
            "metadata": snapshot.to_dict(),
        }

        self.event_writer(
            source="scheduler_governor",
            event=topic,
            detail=detail or snapshot.note,
            severity=severity,
            metadata=snapshot.to_dict(),
        )

        try:
            self.bus.publish(topic, payload, source="SchedulerGovernor")
        except Exception:
            pass

        outfile = self.processed_dir / f"scheduler_{snapshot.timestamp}.json"
        try:
            outfile.write_text(json.dumps(snapshot.to_dict(), indent=2))
        except Exception:
            pass

        self.last_emit_at = time.time()

    def _transition_events(self, previous: Optional[SchedulerSnapshot], current: SchedulerSnapshot):
        if previous is None:
            return [(current.status, self._severity_for(current.status), current.note)]

        events = []
        if previous.status != current.status:
            events.append((current.status, self._severity_for(current.status), current.note))
            if current.status == "SCHEDULER_OK":
                events.append(("SCHEDULER_RECOVERED", "INFO", current.note))
            elif previous.status == "SCHEDULER_OK" and current.status in {"SCHEDULER_WARNING", "SCHEDULER_CRITICAL"}:
                events.append(("SCHEDULER_DEGRADED", self._severity_for(current.status), current.note))
        elif current.status == "SCHEDULER_OK" and (time.time() - self.last_emit_at) >= self.heartbeat_interval_seconds:
            events.append(("SCHEDULER_HEARTBEAT", "INFO", current.note))

        return events

    def run_once(self) -> SchedulerSnapshot:
        snapshot = self.collect()
        for topic, severity, detail in self._transition_events(self.last_snapshot, snapshot):
            self._emit(topic, snapshot, severity=severity, detail=detail)
        self.last_snapshot = snapshot
        return snapshot

    def run_forever(self, interval_seconds: int = 60) -> None:
        self.running = True
        while self.running:
            self.run_once()
            time.sleep(interval_seconds)

    def stop(self) -> None:
        self.running = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Broccoli Core Scheduler Governor")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    args = parser.parse_args()

    governor = SchedulerGovernor()
    if args.loop:
        governor.run_forever(interval_seconds=args.interval)
    else:
        print(json.dumps(governor.run_once().to_dict(), indent=2))


if __name__ == "__main__":
    main()
