from __future__ import annotations

import logging

logger = logging.getLogger("clipboard.consumers")


def register_clipboard_consumers(bus, metrics=None):
    def on_command_received(event):
        payload = getattr(event, "payload", {}) or {}
        logger.info(
            "[CLIPBOARD_COMMAND_RECEIVED] id=%s command=%r",
            payload.get("command_id"),
            payload.get("command"),
        )
        if metrics and hasattr(metrics, "increment"):
            try:
                metrics.increment("clipboard.command_received", 1)
            except TypeError:
                metrics.increment("clipboard.command_received")

    def on_command_result(event):
        payload = getattr(event, "payload", {}) or {}
        logger.info(
            "[CLIPBOARD_COMMAND_RESULT] id=%s output_len=%s",
            payload.get("command_id"),
            len(payload.get("output") or ""),
        )
        if metrics and hasattr(metrics, "increment"):
            try:
                metrics.increment("clipboard.command_result", 1)
            except TypeError:
                metrics.increment("clipboard.command_result")

    bus.subscribe("CLIPBOARD_COMMAND_RECEIVED", on_command_received)
    bus.subscribe("CLIPBOARD_COMMAND_RESULT", on_command_result)

    logger.info("Clipboard consumers registered on EventBus.")
