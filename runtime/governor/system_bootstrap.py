from __future__ import annotations

import argparse
import inspect
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from runtime.eventbus.service import bus as default_bus
from runtime.autonomy.recovery import RecoveryManager
from runtime.governor.accessibility_governor import AccessibilityGovernor
from runtime.governor.workflow_governor import WorkflowGovernor
from runtime.governor.scheduler_governor import SchedulerGovernor
from runtime.governor.runtime_health_governor import RuntimeHealthGovernor
from runtime.governor.metrics_governor import MetricsGovernor
from runtime.governor.metrics_dashboard import UnifiedMetricsDashboard
from runtime.governor.production_governor import ProductionGovernor
from runtime.governor.governor_supervisor import GovernorSupervisor
from runtime.memory.knowledge_graph import KnowledgeGraph
from runtime.planner.adaptive import AdaptivePlanner

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


def _status_rank(status: str) -> int:
    s = str(status).strip().lower()
    if any(tag in s for tag in ("critical", "down", "failed", "failure", "error", "stale")):
        return 3
    if any(tag in s for tag in ("warning", "degraded", "aging", "missing")):
        return 2
    return 1


def _normalize_status(result: Any, default: str = "warning") -> str:
    if result is None:
        return default
    if hasattr(result, "to_dict"):
        data = result.to_dict()
        for key in ("status", "overall_status", "policy_decision", "event"):
            if key in data and data[key]:
                return str(data[key])
        return default
    if isinstance(result, dict):
        for key in ("status", "overall_status", "policy_decision", "event"):
            if key in result and result[key]:
                return str(result[key])
        return default
    if isinstance(result, bool):
        return "healthy" if result else "warning"
    if isinstance(result, int):
        return "healthy" if result >= 0 else "warning"
    return default


@dataclass
class BootstrapComponent:
    name: str
    status: str
    note: str = ""
    result_type: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BootstrapSnapshot:
    timestamp: int
    status: str
    policy_decision: str
    components: List[BootstrapComponent] = field(default_factory=list)
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


class SystemBootstrapOrchestrator:
    """
    Final bootstrap layer for Broccoli Core.

    This wires the already-built governors into a single startup / verification
    sequence so the runtime can check the whole system in one pass.
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
        self.last_snapshot: Optional[BootstrapSnapshot] = None
        self.last_emit_at: float = 0.0
        self.running = False

        self.runtime_health = self._create_component(RuntimeHealthGovernor,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.recovery = self._create_component(RecoveryManager,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
        )
        self.accessibility = self._create_component(AccessibilityGovernor,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.workflow = self._create_component(WorkflowGovernor,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.scheduler = self._create_component(SchedulerGovernor,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.knowledge = self._create_component(KnowledgeGraph,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.adaptive = self._create_component(AdaptivePlanner,
            bus=self.bus,
            root=self.root,
            knowledge_graph=self.knowledge,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.metrics = self._create_component(MetricsGovernor,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.dashboard = self._create_component(UnifiedMetricsDashboard,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.production = self._create_component(ProductionGovernor,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )
        self.supervisor = self._create_component(GovernorSupervisor,
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
            warning_seconds=warning_seconds,
            critical_seconds=critical_seconds,
            heartbeat_interval_seconds=heartbeat_interval_seconds,
        )

    def _create_component(self, factory, **kwargs):
        try:
            sig = inspect.signature(factory)
            filtered = {}
            accepts_var_kw = False
            for p in sig.parameters.values():
                if p.kind == inspect.Parameter.VAR_KEYWORD:
                    accepts_var_kw = True
                    break
            if accepts_var_kw:
                filtered = kwargs
            else:
                for key, value in kwargs.items():
                    if key in sig.parameters:
                        filtered[key] = value
            return factory(**filtered)
        except Exception:
            # Last resort: try progressively smaller kwargs sets.
            for keys in (
                ("bus", "root", "policy", "registry", "event_writer"),
                ("bus", "root", "event_writer"),
                ("bus", "root"),
                ("bus",),
                tuple(),
            ):
                try:
                    filtered = {k: kwargs[k] for k in keys if k in kwargs}
                    return factory(**filtered)
                except Exception:
                    continue
            raise

    def _publish(self, topic: str, snapshot: BootstrapSnapshot, severity: str = "INFO", detail: str = "") -> None:
        payload = {
            "timestamp": snapshot.timestamp,
            "source": "system_bootstrap",
            "event": topic,
            "severity": severity,
            "detail": detail or snapshot.note,
            "metadata": snapshot.to_dict(),
        }

        self.event_writer(
            source="system_bootstrap",
            event=topic,
            detail=detail or snapshot.note,
            severity=severity,
            metadata=snapshot.to_dict(),
        )

        try:
            self.bus.publish(topic, payload, source="SystemBootstrapOrchestrator")
        except Exception:
            pass

        out = self.processed_dir / f"system_bootstrap_{snapshot.timestamp}.json"
        try:
            out.write_text(json.dumps(snapshot.to_dict(), indent=2))
        except Exception:
            pass

        self.last_emit_at = time.time()

    def _run_step(self, name: str, runner: Callable[[], Any]) -> Tuple[BootstrapComponent, Any]:
        try:
            result = runner()
            status = _normalize_status(result, default="healthy" if name in {"recovery"} else "warning")
            note = f"{name} completed"
            result_type = type(result).__name__
            details = {}
            if hasattr(result, "to_dict"):
                details = result.to_dict()
            elif isinstance(result, dict):
                details = dict(result)
            elif isinstance(result, int):
                details = {"count": result}
            return BootstrapComponent(
                name=name,
                status=status,
                note=note,
                result_type=result_type,
                details=details,
            ), result
        except Exception as exc:
            return BootstrapComponent(
                name=name,
                status="critical",
                note=f"{name} failed: {exc}",
                result_type="exception",
                details={"error": str(exc)},
            ), exc

    REQUIRED_COMPONENTS = frozenset({"runtime_health", "recovery"})

    def _overall_status(self, components: List[BootstrapComponent]) -> str:
        required = [c for c in components if c.name in self.REQUIRED_COMPONENTS]
        optional = [c for c in components if c.name not in self.REQUIRED_COMPONENTS]
        req_worst = max((_status_rank(c.status) for c in required), default=1)
        opt_worst = max((_status_rank(c.status) for c in optional), default=1)
        if req_worst >= 3:
            return "BOOTSTRAP_CRITICAL"
        if req_worst == 2:
            return "BOOTSTRAP_WARNING"
        if opt_worst >= 3:
            return "BOOTSTRAP_WARNING"
        return "BOOTSTRAP_OK"

    def collect(self) -> BootstrapSnapshot:
        steps: List[Tuple[str, Callable[[], Any]]] = [
            ("runtime_health", self.runtime_health.run_once),
            ("recovery", self.recovery.run_once),
            ("accessibility", self.accessibility.run_once),
            ("workflow", self.workflow.run_once),
            ("scheduler", self.scheduler.run_once),
            ("knowledge", self.knowledge.run_once),
            ("adaptive", self.adaptive.run_once),
            ("metrics", self.metrics.run_once),
            ("dashboard", self.dashboard.run_once),
            ("production", self.production.run_once),
            ("supervisor", self.supervisor.run_once),
        ]

        components: List[BootstrapComponent] = []
        for name, runner in steps:
            component, _ = self._run_step(name, runner)
            components.append(component)

        overall = self._overall_status(components)
        note = f"{overall} | components={len(components)}"

        return BootstrapSnapshot(
            timestamp=int(time.time()),
            status=overall,
            policy_decision="steady_boot" if overall == "BOOTSTRAP_OK" else "escalate_boot" if overall == "BOOTSTRAP_CRITICAL" else "monitor_boot",
            components=components,
            note=note,
            metadata={
                "started_at": int(self.started_at),
                "warning_seconds": self.warning_seconds,
                "critical_seconds": self.critical_seconds,
                "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            },
        )

    def run_once(self) -> BootstrapSnapshot:
        snapshot = self.collect()

        if self.last_snapshot is None:
            severity = "INFO" if snapshot.status == "BOOTSTRAP_OK" else "WARNING" if snapshot.status == "BOOTSTRAP_WARNING" else "CRITICAL"
            self._publish(snapshot.status, snapshot, severity=severity, detail=snapshot.note)
        elif self.last_snapshot.status != snapshot.status:
            severity = "INFO" if snapshot.status == "BOOTSTRAP_OK" else "WARNING" if snapshot.status == "BOOTSTRAP_WARNING" else "CRITICAL"
            self._publish(snapshot.status, snapshot, severity=severity, detail=snapshot.note)
            if self.last_snapshot.status == "BOOTSTRAP_OK" and snapshot.status in {"BOOTSTRAP_WARNING", "BOOTSTRAP_CRITICAL"}:
                self._publish("BOOTSTRAP_DEGRADED", snapshot, severity=severity, detail=snapshot.note)
            if self.last_snapshot.status in {"BOOTSTRAP_WARNING", "BOOTSTRAP_CRITICAL"} and snapshot.status == "BOOTSTRAP_OK":
                self._publish("BOOTSTRAP_RECOVERED", snapshot, severity="INFO", detail=snapshot.note)
        else:
            if snapshot.status == "BOOTSTRAP_OK" and (time.time() - self.last_emit_at) >= self.heartbeat_interval_seconds:
                self._publish("BOOTSTRAP_HEARTBEAT", snapshot, severity="INFO", detail=snapshot.note)

        self.last_snapshot = snapshot
        return snapshot

    def verify_bootstrap(self) -> Dict[str, Any]:
        knowledge_ok = self.knowledge.verify_roundtrip()
        adaptive_ok = self.adaptive.verify_integration()
        snapshot = self.run_once()
        return {
            "knowledge_roundtrip": knowledge_ok,
            "adaptive_verification": adaptive_ok,
            "snapshot": snapshot.to_dict(),
        }

    def run_forever(self, interval_seconds: int = 60) -> None:
        self.running = True
        while self.running:
            self.run_once()
            time.sleep(interval_seconds)

    def stop(self) -> None:
        self.running = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Broccoli Core System Bootstrap Orchestrator")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    parser.add_argument("--verify", action="store_true", help="Run full bootstrap verification")
    args = parser.parse_args()

    orchestrator = SystemBootstrapOrchestrator()
    if args.verify:
        print(json.dumps(orchestrator.verify_bootstrap(), indent=2))
        return

    if args.loop:
        orchestrator.run_forever(interval_seconds=args.interval)
    else:
        print(json.dumps(orchestrator.run_once().to_dict(), indent=2))


if __name__ == "__main__":
    main()
