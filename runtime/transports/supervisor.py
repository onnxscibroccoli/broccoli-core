from __future__ import annotations

import logging

from .events import (
    TRANSPORT_RECOVERED,
    TRANSPORT_RECOVERY_FAILED,
    TRANSPORT_RESTART_REQUEST,
)

logger = logging.getLogger("transport.supervisor")


def register_transport_supervisor(bus, registry, metrics=None):
    def on_restart_request(event):
        payload = getattr(event, "payload", {}) or {}
        transport_name = payload.get("transport")

        if not transport_name:
            bus.publish(
                TRANSPORT_RECOVERY_FAILED,
                {
                    "reason": payload.get("reason", "restart_request"),
                    "error": "missing transport name",
                    "request": payload,
                },
                source="TransportSupervisor",
            )
            return

        before = registry.health(transport_name)

        try:
            registry.restart(transport_name)
        except Exception as exc:
            bus.publish(
                TRANSPORT_RECOVERY_FAILED,
                {
                    "transport": transport_name,
                    "reason": payload.get("reason", "restart_request"),
                    "error": str(exc),
                    "before": before,
                },
                source="TransportSupervisor",
            )
            return

        after = registry.health(transport_name)

        bus.publish(
            TRANSPORT_RECOVERED,
            {
                "transport": transport_name,
                "reason": payload.get("reason", "restart_request"),
                "before": before,
                "after": after,
            },
            source="TransportSupervisor",
        )

        if metrics and hasattr(metrics, "increment"):
            try:
                metrics.increment(f"transport.{transport_name}.recovered", 1)
            except TypeError:
                metrics.increment(f"transport.{transport_name}.recovered")

    bus.subscribe(TRANSPORT_RESTART_REQUEST, on_restart_request)
    logger.info("Transport supervisor registered on EventBus.")
