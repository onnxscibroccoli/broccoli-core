from __future__ import annotations

import argparse
import json
import time
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


@dataclass
class DashboardComponent:
    name: str
    status: str
    path: Optional[str] = None
    age_seconds: Optional[float] = None
    note: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardSnapshot:
    timestamp: int
    status: str
    components: List[DashboardComponent] = field(default_factory=list)
    note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "components": [c.to_dict() for c in self.components],
            "note": self.note,
            "metadata": dict(self.metadata),
        }


class UnifiedMetricsDashboard:
    """
    Aggregate runtime metrics from the governor/supervision artifacts.

    This is intentionally dashboard-like rather than recovery-oriented.
    It scans the existing runtime_event bus artifacts and surfaces a unified
    health view for all the supervisors already in the repo.
    """

    COMPONENT_PATTERNS = [
        ("runtime_health", "runtime_health_*.json", True),
        ("recovery", "recovery_*.json", True),
        ("accessibility", "accessibility_*.json", True),
        ("workflow", "workflow_*.json", True),
        ("scheduler", "scheduler_*.json", True),
        ("knowledge", "knowledge_*.json", True),
        ("metrics", "metrics_*.json", True),
        ("production", "production_*.json", False),
    ]

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
        self.last_snapshot: Optional[DashboardSnapshot] = None
        self.last_emit_at: float = 0.0
        self.running = False

    def _latest_match(self, pattern: str) -> Optional[Path]:
        matches = [p for p in self.processed_dir.glob(pattern) if p.is_file()]
        if not matches:
            return None
        return max(matches, key=lambda p: p.stat().st_mtime)

    def _status_for_age(self, age_seconds: Optional[float], required: bool) -> Tuple[str, str]:
        if age_seconds is None:
            return ("missing", "required artifact missing" if required else "optional artifact missing")
        if age_seconds <= self.warning_seconds:
            return ("healthy", "fresh artifact")
        if age_seconds <= self.critical_seconds:
            return ("warning", "aging artifact")
        return ("critical", "stale artifact")

    def collect(self) -> DashboardSnapshot:
        components: List[DashboardComponent] = []
        worst = "DASHBOARD_OK"

        for name, pattern, required in self.COMPONENT_PATTERNS:
            latest = self._latest_match(pattern)
            if latest is None:
                status, note = self._status_for_age(None, required)
                components.append(
                    DashboardComponent(
                        name=name,
                        status=status,
                        path=None,
                        age_seconds=None,
                        note=note,
                        details={"pattern": pattern, "required": required},
                    )
                )
                if required and worst != "DASHBOARD_CRITICAL":
                    worst = "DASHBOARD_WARNING"
                continue

            age = round(max(0.0, time.time() - latest.stat().st_mtime), 2)
            status, note = self._status_for_age(age, required)
            components.append(
                DashboardComponent(
                    name=name,
                    status=status,
                    path=str(latest),
                    age_seconds=age,
                    note=note,
                    details={"pattern": pattern, "required": required},
                )
            )

            if status == "critical":
                worst = "DASHBOARD_CRITICAL"
            elif status == "warning" and worst == "DASHBOARD_OK":
                worst = "DASHBOARD_WARNING"
            elif status == "missing" and worst == "DASHBOARD_OK":
                worst = "DASHBOARD_WARNING"

        required_components = [c for c in components if c.details.get("required")]
        healthy_count = len([c for c in required_components if c.status == "healthy"])
        warning_count = len([c for c in required_components if c.status == "warning"])
        critical_count = len([c for c in required_components if c.status == "critical"])
        missing_count = len([c for c in required_components if c.status == "missing"])

        note = f"{worst} | healthy={healthy_count} warning={warning_count} critical={critical_count} missing={missing_count}"

        return DashboardSnapshot(
            timestamp=int(time.time()),
            status=worst,
            components=components,
            note=note,
            metadata={
                "started_at": int(self.started_at),
                "warning_seconds": self.warning_seconds,
                "critical_seconds": self.critical_seconds,
                "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
                "healthy_count": healthy_count,
                "warning_count": warning_count,
                "critical_count": critical_count,
                "missing_count": missing_count,
            },
        )

    def _event_for_status(self, status: str) -> Tuple[str, str]:
        if status == "DASHBOARD_OK":
            return "DASHBOARD_OK", "INFO"
        if status == "DASHBOARD_WARNING":
            return "DASHBOARD_WARNING", "WARNING"
        if status == "DASHBOARD_CRITICAL":
            return "DASHBOARD_CRITICAL", "CRITICAL"
        return "DASHBOARD_WARNING", "WARNING"

    def _emit(self, topic: str, snapshot: DashboardSnapshot, severity: str = "INFO", detail: str = "") -> None:
        payload = {
            "timestamp": snapshot.timestamp,
            "source": "metrics_dashboard",
            "event": topic,
            "severity": severity,
            "detail": detail or snapshot.note,
            "metadata": snapshot.to_dict(),
        }

        self.event_writer(
            source="metrics_dashboard",
            event=topic,
            detail=detail or snapshot.note,
            severity=severity,
            metadata=snapshot.to_dict(),
        )

        try:
            self.bus.publish(topic, payload, source="UnifiedMetricsDashboard")
        except Exception:
            pass

        outfile = self.processed_dir / f"dashboard_{snapshot.timestamp}.json"
        try:
            outfile.write_text(json.dumps(snapshot.to_dict(), indent=2))
        except Exception:
            pass

        self.last_emit_at = time.time()

    def run_once(self) -> DashboardSnapshot:
        snapshot = self.collect()

        topic, severity = self._event_for_status(snapshot.status)
        should_heartbeat = (
            self.last_snapshot is not None
            and self.last_snapshot.status == snapshot.status == "DASHBOARD_OK"
            and (time.time() - self.last_emit_at) >= self.heartbeat_interval_seconds
        )

        if self.last_snapshot is None:
            self._emit(topic, snapshot, severity=severity, detail=snapshot.note)
        elif self.last_snapshot.status != snapshot.status:
            self._emit(topic, snapshot, severity=severity, detail=snapshot.note)
            if snapshot.status == "DASHBOARD_OK":
                self._emit("DASHBOARD_RECOVERED", snapshot, severity="INFO", detail=snapshot.note)
            elif self.last_snapshot.status == "DASHBOARD_OK" and snapshot.status in {"DASHBOARD_WARNING", "DASHBOARD_CRITICAL"}:
                self._emit("DASHBOARD_DEGRADED", snapshot, severity=severity, detail=snapshot.note)
        elif should_heartbeat:
            self._emit("DASHBOARD_HEARTBEAT", snapshot, severity="INFO", detail=snapshot.note)

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
    parser = argparse.ArgumentParser(description="Broccoli Core Unified Metrics Dashboard")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    args = parser.parse_args()

    dashboard = UnifiedMetricsDashboard()
    if args.loop:
        dashboard.run_forever(interval_seconds=args.interval)
    else:
        print(json.dumps(dashboard.run_once().to_dict(), indent=2))


if __name__ == "__main__":
    main()
