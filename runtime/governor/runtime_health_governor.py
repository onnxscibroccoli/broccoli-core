from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

from runtime.eventbus.service import bus as default_bus
from runtime.health.component_registry import ComponentSpec, default_component_specs
from runtime.health.health_policy import HealthPolicy
from runtime.health.health_snapshot import ComponentHealth, HealthSnapshot

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


class RuntimeHealthGovernor:
    """
    Central runtime watchdog for Broccoli Core.

    Required components are enforced now. Optional components are tracked and
    will become required as the corresponding subsystems are instrumented.
    """

    def __init__(
        self,
        bus=None,
        root: Optional[Path] = None,
        policy: Optional[HealthPolicy] = None,
        registry: Optional[Iterable[ComponentSpec]] = None,
        event_writer: Optional[Callable[..., Dict[str, object]]] = None,
    ):
        self.bus = bus or default_bus
        self.root = Path(root or Path.cwd())
        self.policy = policy or HealthPolicy()
        self.registry = list(registry or default_component_specs())
        self.event_writer = event_writer or write_event

        self.last_snapshot: Optional[HealthSnapshot] = None
        self.last_emit_at: float = 0.0
        self.running = False

        self.processed_dir = self.root / "runtime" / "event_bus" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def _latest_match(self, pattern: str) -> Optional[Path]:
        matches = [p for p in self.root.glob(pattern) if p.exists() and p.is_file()]
        if not matches:
            return None
        return max(matches, key=lambda p: p.stat().st_mtime)

    def _component_health(self, spec: ComponentSpec) -> ComponentHealth:
        latest = self._latest_match(spec.pattern)

        if latest is None:
            status = "critical" if spec.required else "deferred"
            return ComponentHealth(
                name=spec.name,
                required=spec.required,
                status=status,
                path=None,
                age_seconds=None,
                note=spec.note,
                details={"reason": "missing"},
            )

        age = max(0.0, time.time() - latest.stat().st_mtime)
        status = self.policy.classify_age(age, spec.max_age_seconds)

        return ComponentHealth(
            name=spec.name,
            required=spec.required,
            status=status,
            path=str(latest),
            age_seconds=round(age, 2),
            note=spec.note,
            details={"reason": "freshness_check", "pattern": spec.pattern},
        )

    def collect(self) -> HealthSnapshot:
        components = [self._component_health(spec) for spec in self.registry]

        required = [c for c in components if c.required]
        required_missing = [c for c in required if c.status == "critical" and c.path is None]
        required_critical = [c for c in required if c.status == "critical" and c.path is not None]
        required_warning = [c for c in required if c.status == "warning"]

        optional_warning = [c for c in components if (not c.required) and c.status == "warning"]

        if required_missing:
            overall = "COMPONENT_DOWN"
        elif required_critical:
            overall = "HEALTH_CRITICAL"
        elif required_warning or optional_warning:
            overall = "HEALTH_WARNING"
        else:
            overall = "RUNTIME_OK"

        summary = self._build_summary(overall, components)

        return HealthSnapshot(
            timestamp=int(time.time()),
            overall_status=overall,
            components=components,
            summary=summary,
            metadata={
                "required_total": len(required),
                "required_healthy": len([c for c in required if c.status == "healthy"]),
                "required_warning": len(required_warning),
                "required_missing": len(required_missing),
                "required_critical": len(required_critical),
            },
        )

    def _build_summary(self, overall: str, components: List[ComponentHealth]) -> str:
        parts = [overall]
        for c in components:
            if c.required:
                parts.append(f"{c.name}:{c.status}")
        return " | ".join(parts)

    def _event_for_snapshot(self, snapshot: HealthSnapshot) -> tuple[str, str]:
        if snapshot.overall_status == "RUNTIME_OK":
            return "RUNTIME_OK", "INFO"
        if snapshot.overall_status == "HEALTH_WARNING":
            return "HEALTH_WARNING", "WARNING"
        if snapshot.overall_status == "HEALTH_CRITICAL":
            return "HEALTH_CRITICAL", "CRITICAL"
        return "COMPONENT_DOWN", "CRITICAL"

    def _transition_events(self, previous: Optional[HealthSnapshot], current: HealthSnapshot) -> List[tuple[str, str, Dict[str, object]]]:
        events: List[tuple[str, str, Dict[str, object]]] = []
        current_map = {c.name: c for c in current.components}
        previous_map = {c.name: c for c in previous.components} if previous else {}

        if previous is None:
            event, severity = self._event_for_snapshot(current)
            events.append((event, severity, {"summary": current.summary}))
            return events

        # Component transitions
        recovered = []
        down = []
        for name, c in current_map.items():
            prev = previous_map.get(name)
            if prev is None:
                continue
            if prev.status != "healthy" and c.status == "healthy":
                recovered.append(name)
            if prev.status == "healthy" and c.status in {"warning", "critical"}:
                down.append(name)

        if recovered:
            events.append(("COMPONENT_RECOVERED", "INFO", {"components": recovered}))
        if down:
            events.append(("COMPONENT_DOWN", "CRITICAL", {"components": down}))

        # Overall transitions
        if previous.overall_status != current.overall_status:
            event, severity = self._event_for_snapshot(current)
            events.append((event, severity, {"summary": current.summary}))

        if previous.overall_status in {"HEALTH_WARNING", "HEALTH_CRITICAL", "COMPONENT_DOWN"} and current.overall_status == "RUNTIME_OK":
            events.append(("RECOVERY_FINISHED", "INFO", {"summary": current.summary}))
        elif previous.overall_status == "RUNTIME_OK" and current.overall_status in {"HEALTH_WARNING", "HEALTH_CRITICAL", "COMPONENT_DOWN"}:
            events.append(("RECOVERY_STARTED", "WARNING", {"summary": current.summary}))

        return events

    def _emit(self, event_name: str, severity: str, snapshot: HealthSnapshot, detail: str = "") -> None:
        payload = {
            "timestamp": snapshot.timestamp,
            "source": "runtime_health_governor",
            "event": event_name,
            "severity": severity,
            "detail": detail or snapshot.summary,
            "metadata": snapshot.to_dict(),
        }

        self.event_writer(
            source="runtime_health_governor",
            event=event_name,
            detail=detail or snapshot.summary,
            severity=severity,
            metadata=snapshot.to_dict(),
        )

        try:
            self.bus.publish(event_name, payload, source="RuntimeHealthGovernor")
        except Exception:
            pass

        out = self.processed_dir / f"runtime_health_{snapshot.timestamp}.json"
        out.write_text(json.dumps(snapshot.to_dict(), indent=2))

        self.last_emit_at = time.time()

    def run_once(self) -> HealthSnapshot:
        snapshot = self.collect()

        events = self._transition_events(self.last_snapshot, snapshot)
        should_heartbeat = (
            self.policy.emit_heartbeat_when_stable
            and (time.time() - self.last_emit_at >= self.policy.heartbeat_interval_seconds)
        )

        if not events and should_heartbeat:
            event_name, severity = self._event_for_snapshot(snapshot)
            events = [(event_name, severity, {"heartbeat": True, "summary": snapshot.summary})]

        for event_name, severity, meta in events:
            self._emit(
                event_name=event_name,
                severity=severity,
                snapshot=snapshot,
                detail=meta.get("summary", snapshot.summary),
            )

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
    parser = argparse.ArgumentParser(description="Runtime Health Governor")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    args = parser.parse_args()

    governor = RuntimeHealthGovernor()
    if args.loop:
        governor.run_forever(interval_seconds=args.interval)
    else:
        snapshot = governor.run_once()
        print(json.dumps(snapshot.to_dict(), indent=2))


if __name__ == "__main__":
    main()
