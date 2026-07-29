from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from runtime.eventbus.service import bus as default_bus
from runtime.governor.system_bootstrap import SystemBootstrapOrchestrator

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
class SmokeSnapshot:
    timestamp: int
    status: str
    verification_ok: bool
    bootstrap_status: str
    health_status: str
    note: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EndToEndSmoke:
    """
    End-to-end smoke verification for the completed Broccoli Core stack.

    This intentionally checks the whole boot path:
    - bootstrap verification
    - a full bootstrap run
    - a summarized status output suitable for CI or Termux
    """

    def __init__(
        self,
        bus=None,
        root: Optional[Path] = None,
        event_writer: Optional[Callable[..., Dict[str, Any]]] = None,
    ):
        self.bus = bus or default_bus
        self.root = Path(root or Path.cwd())
        self.event_writer = event_writer or write_event
        self.bootstrap = SystemBootstrapOrchestrator(
            bus=self.bus,
            root=self.root,
            event_writer=self.event_writer,
        )
        self.processed_dir = self.root / "runtime" / "event_bus" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def _publish(self, topic: str, snapshot: SmokeSnapshot, severity: str = "INFO") -> None:
        payload = {
            "timestamp": snapshot.timestamp,
            "source": "end_to_end_smoke",
            "event": topic,
            "severity": severity,
            "detail": snapshot.note,
            "metadata": snapshot.to_dict(),
        }

        self.event_writer(
            source="end_to_end_smoke",
            event=topic,
            detail=snapshot.note,
            severity=severity,
            metadata=snapshot.to_dict(),
        )

        try:
            self.bus.publish(topic, payload, source="EndToEndSmoke")
        except Exception:
            pass

        out = self.processed_dir / f"end_to_end_smoke_{snapshot.timestamp}.json"
        try:
            out.write_text(json.dumps(snapshot.to_dict(), indent=2))
        except Exception:
            pass

    def run(self) -> SmokeSnapshot:
        verification = self.bootstrap.verify_bootstrap()
        bootstrap_snapshot = self.bootstrap.run_once()

        adaptive = (
            verification.get("adaptive_verification", {})
            if isinstance(verification, dict)
            else {}
        )

        verification_ok = (
            bool(verification.get("knowledge_roundtrip"))
            and adaptive.get("status") == "ADAPTIVE_OK"
        )

        bootstrap_status = (
            getattr(bootstrap_snapshot, "status", None)
            or "unknown"
        )

        bootstrap_ok = bootstrap_status == "BOOTSTRAP_OK"

        smoke_status = (
            "SMOKE_OK"
            if verification_ok and bootstrap_ok
            else "SMOKE_WARNING"
        )

        snapshot = SmokeSnapshot(
            timestamp=int(time.time()),
            status=smoke_status,
            verification_ok=verification_ok,
            bootstrap_status=str(bootstrap_status),
            health_status=str(bootstrap_status),
            note=(
                f"verification_ok={verification_ok} "
                f"bootstrap_ok={bootstrap_ok}"
            ),
            metadata={
                "verification": verification,
                "bootstrap_ok": bootstrap_ok,
            },
        )

        self._publish(
            smoke_status,
            snapshot,
            severity=(
                "INFO"
                if smoke_status == "SMOKE_OK"
                else "WARNING"
            ),
        )

        return snapshot

    def run_forever(self, interval_seconds: int = 60) -> None:
        while True:
            self.run()
            time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Broccoli Core End-to-End Smoke")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless smoke is fully OK")
    args = parser.parse_args()

    smoke = EndToEndSmoke()
    if args.loop:
        smoke.run_forever(interval_seconds=args.interval)
        return

    snapshot = smoke.run()
    print(json.dumps(snapshot.to_dict(), indent=2))
    if args.strict and snapshot.status != "SMOKE_OK":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
