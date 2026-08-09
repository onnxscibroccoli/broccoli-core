from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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


PRODUCTION_TOPICS = {
    "RUNTIME_OK",
    "HEALTH_WARNING",
    "HEALTH_CRITICAL",
    "COMPONENT_DOWN",
    "COMPONENT_RECOVERED",
    "RECOVERY_STARTED",
    "RECOVERY_FINISHED",
    "ACCESSIBILITY_OK",
    "ACCESSIBILITY_WARNING",
    "ACCESSIBILITY_CRITICAL",
    "ACCESSIBILITY_RECOVERED",
    "WORKFLOW_OK",
    "WORKFLOW_WARNING",
    "WORKFLOW_CRITICAL",
    "WORKFLOW_RECOVERED",
    "SCHEDULER_OK",
    "SCHEDULER_WARNING",
    "SCHEDULER_CRITICAL",
    "SCHEDULER_RECOVERED",
    "KNOWLEDGE_OK",
    "KNOWLEDGE_WARNING",
    "KNOWLEDGE_CRITICAL",
    "KNOWLEDGE_RECOVERED",
    "METRICS_OK",
    "METRICS_WARNING",
    "METRICS_CRITICAL",
    "METRICS_RECOVERED",
    "DASHBOARD_OK",
    "DASHBOARD_WARNING",
    "DASHBOARD_CRITICAL",
    "DASHBOARD_RECOVERED",
    "PRODUCTION_OK",
    "PRODUCTION_WARNING",
    "PRODUCTION_CRITICAL",
    "PRODUCTION_RECOVERY_REQUIRED",
    "PRODUCTION_RECOVERED",
    "PRODUCTION_HEARTBEAT",
}

NORMALIZE_STATUS = {
    "ok": "healthy",
    "healthy": "healthy",
    "runtime_ok": "healthy",
    "dashboard_ok": "healthy",
    "accessibility_ok": "healthy",
    "workflow_ok": "healthy",
    "scheduler_ok": "healthy",
    "knowledge_ok": "healthy",
    "metrics_ok": "healthy",
    "production_ok": "healthy",
    "recovered": "healthy",
    "recovery_finished": "healthy",
    "warning": "warning",
    "aging": "warning",
    "degraded": "warning",
    "missing": "missing",
    "critical": "critical",
    "down": "critical",
    "stale": "critical",
    "failed": "critical",
    "failure": "critical",
    "error": "critical",
}


@dataclass
class ProductionComponent:
    name: str
    status: str
    path: Optional[str] = None
    age_seconds: Optional[float] = None
    note: str = ""
    required: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProductionSnapshot:
    timestamp: int
    status: str
    policy_decision: str
    components: List[ProductionComponent] = field(default_factory=list)
    note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "policy_decision": self.policy_decision,
            "components": [c.to_dict() for c in self.components],
            "note": self.note,
            "metadata": dict(self.metadata),
        }


class ProductionGovernor:
    """
    Top-level autonomous supervisor.

    It aggregates the health output of every subsystem governor and converts the
    combined state into a policy decision. This is the layer that reasons over
    the whole runtime rather than a single subsystem.
    """

    COMPONENT_PATTERNS = [
        ("runtime_health", "runtime_health_*.json", True),
        ("recovery", "recovery_*.json", True),
        ("accessibility", "accessibility_*.json", True),
        ("workflow", "workflow_*.json", True),
        ("scheduler", "scheduler_*.json", True),
        ("knowledge", "knowledge_*.json", True),
        ("metrics", "metrics_*.json", True),
        ("dashboard", "dashboard_*.json", False),
    ]

    def __init__(
        self,
        bus=None,
        root: Optional[Path] = None,
        event_writer: Optional[Callable[..., Dict[str, Any]]] = None,
        warning_seconds: int = 120,
        critical_seconds: int = 300,
        heartbeat_interval_seconds: int = 60,
        critical_threshold: int = 1,
        warning_threshold: int = 1,
    ):
        self.bus = bus or default_bus
        self.root = Path(root or Path.cwd())
        self.event_writer = event_writer or write_event
        self.warning_seconds = warning_seconds
        self.critical_seconds = critical_seconds
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.critical_threshold = critical_threshold
        self.warning_threshold = warning_threshold

        self.processed_dir = self.root / "runtime" / "event_bus" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.started_at = time.time()
        self.last_event_at: Optional[float] = None
        self.last_event_topic: Optional[str] = None
        self.last_snapshot: Optional[ProductionSnapshot] = None
        self.last_emit_at: float = 0.0
        self.running = False
        self.event_counts = defaultdict(int)

        for topic in PRODUCTION_TOPICS:
            try:
                self.bus.subscribe(topic, self._on_production_event)
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

    def _on_production_event(self, event: Any) -> None:
        payload = self._payload_of(event)
        topic = self._topic_of(event, payload)
        self.last_event_at = time.time()
        self.last_event_topic = topic
        self.event_counts[topic] += 1

    def _latest_match(self, pattern: str) -> Optional[Path]:
        matches = [p for p in self.processed_dir.glob(pattern) if p.is_file()]
        if not matches:
            return None
        return max(matches, key=lambda p: p.stat().st_mtime)

    def _normalize(self, raw: Any) -> str:
        if raw is None:
            return "missing"
        s = str(raw).strip().lower()
        if s in NORMALIZE_STATUS:
            return NORMALIZE_STATUS[s]
        if s.endswith("_ok"):
            return "healthy"
        if s.endswith("_warning"):
            return "warning"
        if s.endswith("_critical"):
            return "critical"
        if s.endswith("_degraded"):
            return "warning"
        if s.endswith("_recovered"):
            return "healthy"
        return "warning"

    def _status_from_artifact(self, data: Dict[str, Any], required: bool, age_seconds: Optional[float]) -> Tuple[str, str]:
        status_keys = (
            "policy_decision",
            "status",
            "overall_status",
            "event",
            "severity",
        )
        raw = None
        for key in status_keys:
            if key in data and data[key] is not None:
                raw = data[key]
                break

        # Event-heavy artifacts such as recovery or dashboard snapshots often
        # encode useful state in the event field rather than a pure status field.
        if raw is None and "metadata" in data and isinstance(data["metadata"], dict):
            raw = data["metadata"].get("status")

        status = self._normalize(raw)

        if age_seconds is not None:
            if age_seconds > self.critical_seconds:
                status = "critical"
            elif age_seconds > self.warning_seconds and status == "healthy":
                status = "warning"

        if not required and status == "missing":
            return "missing", "optional artifact missing"

        if status == "healthy":
            return "healthy", "fresh artifact"
        if status == "warning":
            return "warning", "aging artifact"
        if status == "critical":
            return "critical", "stale/failed artifact"
        return "missing", "required artifact missing" if required else "optional artifact missing"

    def _load_artifact(self, path: Path) -> Dict[str, Any]:
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}

    def collect(self) -> ProductionSnapshot:
        components: List[ProductionComponent] = []
        required = []
        warnings = 0
        critical = 0
        missing = 0

        for name, pattern, is_required in self.COMPONENT_PATTERNS:
            latest = self._latest_match(pattern)
            if latest is None:
                status, note = self._status_from_artifact({}, is_required, None)
                components.append(
                    ProductionComponent(
                        name=name,
                        status=status,
                        path=None,
                        age_seconds=None,
                        note=note,
                        required=is_required,
                        details={"pattern": pattern, "required": is_required, "source": "missing"},
                    )
                )
                if is_required:
                    required.append(name)
                if status == "warning":
                    warnings += 1
                elif status == "critical":
                    critical += 1
                elif status == "missing":
                    missing += 1
                continue

            age = round(max(0.0, time.time() - latest.stat().st_mtime), 2)
            data = self._load_artifact(latest)
            status, note = self._status_from_artifact(data, is_required, age)

            components.append(
                ProductionComponent(
                    name=name,
                    status=status,
                    path=str(latest),
                    age_seconds=age,
                    note=note,
                    required=is_required,
                    details={"pattern": pattern, "required": is_required, "source": latest.name},
                )
            )

            if is_required:
                required.append(name)
            if status == "warning":
                warnings += 1
            elif status == "critical":
                critical += 1
            elif status == "missing":
                missing += 1

        if critical >= self.critical_threshold or missing > 0:
            status = "PRODUCTION_CRITICAL"
            policy_decision = "escalate_and_recover"
        elif warnings >= self.warning_threshold:
            status = "PRODUCTION_WARNING"
            policy_decision = "monitor_and_prepare_recovery"
        else:
            status = "PRODUCTION_OK"
            policy_decision = "steady_state"

        note = (
            f"{status} | required={len(required)} "
            f"warnings={warnings} critical={critical} missing={missing}"
        )

        return ProductionSnapshot(
            timestamp=int(time.time()),
            status=status,
            policy_decision=policy_decision,
            components=components,
            note=note,
            metadata={
                "started_at": int(self.started_at),
                "warning_seconds": self.warning_seconds,
                "critical_seconds": self.critical_seconds,
                "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold,
                "required_components": required,
                "warnings": warnings,
                "critical": critical,
                "missing": missing,
            },
        )

    def _severity_for(self, status: str) -> str:
        return {
            "PRODUCTION_OK": "INFO",
            "PRODUCTION_WARNING": "WARNING",
            "PRODUCTION_CRITICAL": "CRITICAL",
            "PRODUCTION_RECOVERY_REQUIRED": "CRITICAL",
        }.get(status, "INFO")

    def _event_for_status(self, status: str) -> Tuple[str, str]:
        if status == "PRODUCTION_OK":
            return "PRODUCTION_OK", "INFO"
        if status == "PRODUCTION_WARNING":
            return "PRODUCTION_WARNING", "WARNING"
        if status == "PRODUCTION_CRITICAL":
            return "PRODUCTION_CRITICAL", "CRITICAL"
        return "PRODUCTION_WARNING", "WARNING"

    def _emit(self, topic: str, snapshot: ProductionSnapshot, severity: str = "INFO", detail: str = "") -> None:
        payload = {
            "timestamp": snapshot.timestamp,
            "source": "production_governor",
            "event": topic,
            "severity": severity,
            "detail": detail or snapshot.note,
            "metadata": snapshot.to_dict(),
        }

        self.event_writer(
            source="production_governor",
            event=topic,
            detail=detail or snapshot.note,
            severity=severity,
            metadata=snapshot.to_dict(),
        )

        try:
            self.bus.publish(topic, payload, source="ProductionGovernor")
        except Exception:
            pass

        outfile = self.processed_dir / f"production_{snapshot.timestamp}.json"
        try:
            outfile.write_text(json.dumps(snapshot.to_dict(), indent=2))
        except Exception:
            pass

        self.last_emit_at = time.time()

    def run_once(self) -> ProductionSnapshot:
        snapshot = self.collect()
        current_topic, current_severity = self._event_for_status(snapshot.status)

        if self.last_snapshot is None:
            self._emit(current_topic, snapshot, severity=current_severity, detail=snapshot.note)
        elif self.last_snapshot.status != snapshot.status:
            self._emit(current_topic, snapshot, severity=current_severity, detail=snapshot.note)

            if self.last_snapshot.status == "PRODUCTION_OK" and snapshot.status in {"PRODUCTION_WARNING", "PRODUCTION_CRITICAL"}:
                self._emit("PRODUCTION_DEGRADED", snapshot, severity=current_severity, detail=snapshot.note)

            if self.last_snapshot.status in {"PRODUCTION_WARNING", "PRODUCTION_CRITICAL"} and snapshot.status == "PRODUCTION_OK":
                self._emit("PRODUCTION_RECOVERED", snapshot, severity="INFO", detail=snapshot.note)

            if snapshot.status == "PRODUCTION_CRITICAL":
                self._emit("PRODUCTION_RECOVERY_REQUIRED", snapshot, severity="CRITICAL", detail=snapshot.note)
        else:
            if snapshot.status == "PRODUCTION_OK" and (time.time() - self.last_emit_at) >= self.heartbeat_interval_seconds:
                self._emit("PRODUCTION_HEARTBEAT", snapshot, severity="INFO", detail=snapshot.note)

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
    parser = argparse.ArgumentParser(description="Broccoli Core Production Governor")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    args = parser.parse_args()

    governor = ProductionGovernor()
    if args.loop:
        governor.run_forever(interval_seconds=args.interval)
    else:
        print(json.dumps(governor.run_once().to_dict(), indent=2))


if __name__ == "__main__":
    main()
