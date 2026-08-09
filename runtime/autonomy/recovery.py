from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

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


HEALTH_TOPICS = {
    "RUNTIME_OK",
    "HEALTH_WARNING",
    "HEALTH_CRITICAL",
    "COMPONENT_DOWN",
    "COMPONENT_RECOVERED",
}


@dataclass
class RecoverySignal:
    topic: str
    payload: Dict[str, Any] = field(default_factory=dict)
    received_at: float = field(default_factory=time.time)


class RecoveryManager:
    """
    Event-driven recovery coordinator.

    It does not hard-restart OS processes directly. Instead, it:
    - watches health signals from the Runtime Health Governor,
    - publishes recovery lifecycle events,
    - invokes optional component handlers when registered,
    - keeps a small in-memory incident ledger,
    - supports periodic scans for the main runtime loop.
    """

    def __init__(
        self,
        bus=None,
        root: Optional[Path] = None,
        event_writer: Optional[Callable[..., Dict[str, Any]]] = None,
        cooldown_seconds: int = 120,
        max_attempts: int = 3,
    ):
        self.bus = bus or default_bus
        self.root = Path(root or Path.cwd())
        self.event_writer = event_writer or write_event
        self.cooldown_seconds = cooldown_seconds
        self.max_attempts = max_attempts

        self.processed_dir = self.root / "runtime" / "event_bus" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.handlers: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self.attempts: Dict[str, int] = {}
        self.last_recovery_at: Dict[str, float] = {}
        self.latest_signal: Optional[RecoverySignal] = None
        self.running = False

        # Subscribe to the health stream for situational awareness.
        for topic in HEALTH_TOPICS:
            try:
                self.bus.subscribe(topic, self._on_health_event)
            except Exception:
                pass

    def register_handler(self, component: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        self.handlers[component] = handler

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

    def _on_health_event(self, event: Any) -> None:
        payload = self._payload_of(event)
        topic = getattr(event, "topic", None) or payload.get("event") or "UNKNOWN"

        self.latest_signal = RecoverySignal(
            topic=topic,
            payload=payload,
            received_at=time.time(),
        )

    def _latest_snapshot_path(self) -> Optional[Path]:
        candidates = []
        for pattern in (
            "runtime_health_*.json",
            "runtime_health_governor_*.json",
        ):
            candidates.extend([p for p in self.processed_dir.glob(pattern) if p.is_file()])

        if not candidates:
            return None

        return max(candidates, key=lambda p: p.stat().st_mtime)

    def _load_latest_snapshot(self) -> Dict[str, Any]:
        if self.latest_signal and self.latest_signal.payload:
            payload = self.latest_signal.payload
            if "metadata" in payload or "overall_status" in payload:
                return payload

        latest = self._latest_snapshot_path()
        if not latest:
            return {}

        try:
            return json.loads(latest.read_text())
        except Exception:
            return {}

    def _required_problem_components(self, snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
        components = snapshot.get("components", [])
        if not isinstance(components, list):
            return []

        problems: List[Dict[str, Any]] = []
        for component in components:
            if not isinstance(component, dict):
                continue
            if not component.get("required", False):
                continue
            if component.get("status") in {"healthy", "ok"}:
                continue
            problems.append(component)
        return problems

    def _within_cooldown(self, component: str) -> bool:
        last = self.last_recovery_at.get(component, 0.0)
        return (time.time() - last) < self.cooldown_seconds

    def _publish(self, topic: str, detail: str, severity: str = "INFO", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {
            "timestamp": int(time.time()),
            "source": "recovery_manager",
            "event": topic,
            "severity": severity,
            "detail": detail,
            "metadata": metadata or {},
        }

        self.event_writer(
            source="recovery_manager",
            event=topic,
            detail=detail,
            severity=severity,
            metadata=metadata or {},
        )

        try:
            self.bus.publish(topic, payload, source="RecoveryManager")
        except Exception:
            pass

        out = self.processed_dir / f"recovery_{topic.lower()}_{payload['timestamp']}.json"
        try:
            out.write_text(json.dumps(payload, indent=2))
        except Exception:
            pass

        return payload

    def _invoke_handler(self, component: str, context: Dict[str, Any]) -> Dict[str, Any]:
        handler = self.handlers.get(component) or self.handlers.get("*")
        if handler is None:
            return {
                "success": True,
                "action": "request_only",
                "detail": "No handler registered; recovery request published only.",
            }

        result = handler(context)
        if isinstance(result, dict):
            result.setdefault("success", True)
            result.setdefault("action", "custom_handler")
            result.setdefault("detail", "Custom handler executed.")
            return result

        return {
            "success": bool(result is None or result is True),
            "action": "custom_handler",
            "detail": "Custom handler executed.",
        }

    def scan_and_recover(self) -> int:
        """
        Scan runtime health snapshot and publish recovery lifecycle events.
        """
        snapshot = self._load_latest_snapshot()

        if not snapshot:
            self._publish(
                "RECOVERY_HEARTBEAT",
                "No recovery snapshot available",
                severity="INFO",
                metadata={
                    "recovered_count": 0,
                    "overall_status": "UNKNOWN",
                    "problems": [],
                    "snapshot": {},
                },
            )
            return 0

        overall = snapshot.get("overall_status", "UNKNOWN")
        problems = self._required_problem_components(snapshot)

        # Trust overall RUNTIME_OK: do not open recovery on residual component noise.
        if overall == "RUNTIME_OK":
            self._publish(
                "RECOVERY_HEARTBEAT",
                "No recovery required",
                severity="INFO",
                metadata={
                    "recovered_count": 0,
                    "overall_status": overall,
                    "problems": [],
                    "snapshot": snapshot,
                },
            )
            return 0

        if not problems:
            self._publish(
                "RECOVERY_HEARTBEAT",
                "No recovery required",
                severity="INFO",
                metadata={
                    "recovered_count": 0,
                    "overall_status": overall,
                    "problems": [],
                    "snapshot": snapshot,
                },
            )
            return 0

        recovered_count = 0

        for component in problems:
            name = component.get("name", "unknown")

            if self._within_cooldown(name):
                continue

            context = {
                "snapshot": snapshot,
                "component": component,
                "overall_status": overall,
            }

            self._publish(
                "RECOVERY_STARTED",
                f"Recovery requested for {name}",
                severity="WARNING",
                metadata=context,
            )

            try:
                result = self._invoke_handler(name, context)
                success = bool(result.get("success", True))
            except Exception as exc:
                result = {
                    "success": False,
                    "error": str(exc),
                }
                success = False

            self.attempts[name] = self.attempts.get(name, 0) + 1
            self.last_recovery_at[name] = time.time()

            self._publish(
                "RECOVERY_FINISHED",
                f"Recovery finished for {name}",
                severity="INFO" if success else "CRITICAL",
                metadata={
                    "component": name,
                    "success": success,
                    "result": result,
                },
            )

            recovered_count += 1

        self._publish(
            "RECOVERY_SCAN_COMPLETE",
            f"Recovery scan complete; actions={recovered_count}",
            severity="INFO",
            metadata={
                "recovered_count": recovered_count,
                "overall_status": overall,
                "problems": [
                    c.get("name", "unknown")
                    for c in problems
                ],
            },
        )

        return recovered_count

    def run_once(self) -> int:
        return self.scan_and_recover()

    def run_forever(self, interval_seconds: int = 60) -> None:
        self.running = True
        while self.running:
            self.scan_and_recover()
            time.sleep(interval_seconds)

    def stop(self) -> None:
        self.running = False


def main() -> None:
    parser = argparse.ArgumentParser(description="Broccoli Core Recovery Manager")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    args = parser.parse_args()

    manager = RecoveryManager()
    if args.loop:
        manager.run_forever(interval_seconds=args.interval)
    else:
        print(manager.scan_and_recover())


if __name__ == "__main__":
    main()
