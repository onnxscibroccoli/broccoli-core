from __future__ import annotations

import logging

from .events import (
    CLIPBOARD_BRIDGE_RECOVERED,
    CLIPBOARD_BRIDGE_RECOVERY_FAILED,
    CLIPBOARD_BRIDGE_RESTART_REQUEST,
)

logger = logging.getLogger("clipboard.supervisor")


def register_clipboard_supervisor(bus, bridge, metrics=None):
    def on_restart_request(event):
        payload = getattr(event, "payload", {}) or {}
        before = bridge.health() if hasattr(bridge, "health") else {}

        try:
            bridge.stop()
        except Exception as exc:
            failure = {
                "reason": payload.get("reason", "restart_request"),
                "error": str(exc),
                "before": before,
            }
            bus.publish(
                CLIPBOARD_BRIDGE_RECOVERY_FAILED,
                failure,
                source="ClipboardSupervisor",
            )
            return

        try:
            bridge.start()
        except Exception as exc:
            failure = {
                "reason": payload.get("reason", "restart_request"),
                "error": str(exc),
                "before": before,
            }
            bus.publish(
                CLIPBOARD_BRIDGE_RECOVERY_FAILED,
                failure,
                source="ClipboardSupervisor",
            )
            return

        after = bridge.health() if hasattr(bridge, "health") else {}
        recovered = {
            "reason": payload.get("reason", "restart_request"),
            "before": before,
            "after": after,
        }
        bus.publish(
            CLIPBOARD_BRIDGE_RECOVERED,
            recovered,
            source="ClipboardSupervisor",
        )

        if metrics and hasattr(metrics, "increment"):
            try:
                metrics.increment("clipboard.bridge.recovered", 1)
            except TypeError:
                metrics.increment("clipboard.bridge.recovered")

    bus.subscribe(CLIPBOARD_BRIDGE_RESTART_REQUEST, on_restart_request)
    logger.info("Clipboard supervisor registered on EventBus.")
