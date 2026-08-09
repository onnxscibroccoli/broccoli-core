from __future__ import annotations

import logging
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from runtime.eventbus.bus import EventBus

from .events import (
    CLIPBOARD_COMMAND_RECEIVED,
    CLIPBOARD_COMMAND_RESULT,
    build_command_payload,
    build_result_payload,
    is_result_envelope,
)

logger = logging.getLogger("clipboard.bridge")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClipboardEventBridge:
    """
    Passive clipboard sensor.

    It reads clipboard content, normalizes it, and publishes structured
    clipboard events onto the shared EventBus. It does not execute commands.
    """

    def __init__(
        self,
        bus: EventBus,
        clipboard_get: Optional[Callable[[], str]] = None,
        poll_interval: float = 2.0,
        logger: Optional[logging.Logger] = None,
    ):
        self.bus = bus
        self._clipboard_get = clipboard_get or self._default_clipboard_get
        self.poll_interval = poll_interval
        self._logger = logger or logging.getLogger("clipboard.bridge")
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_digest: Optional[str] = None
        self._last_observed_at: Optional[str] = None
        self._last_kind: Optional[str] = None

    def _default_clipboard_get(self) -> str:
        if shutil.which("termux-clipboard-get") is None:
            return ""

        try:
            proc = subprocess.run(
                ["termux-clipboard-get"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except Exception as exc:
            self._logger.debug("clipboard read failed: %s", exc)
            return ""

        return (proc.stdout or "").strip("\n")

    def read_clipboard(self) -> str:
        try:
            return (self._clipboard_get() or "").strip("\n")
        except Exception as exc:
            self._logger.debug("clipboard getter failed: %s", exc)
            return ""

    def poll_once(self):
        clip = self.read_clipboard()
        if not clip:
            return None

        digest = _sha256(clip)
        if digest == self._last_digest:
            return None

        self._last_digest = digest
        self._last_observed_at = _utc_now_iso()

        if is_result_envelope(clip):
            self._last_kind = "result"
            payload = build_result_payload(clip, source="clipboard.bridge")
            self.bus.publish(
                CLIPBOARD_COMMAND_RESULT,
                payload,
                source="clipboard.bridge",
            )
            return payload

        self._last_kind = "command"
        payload = build_command_payload(clip, source="clipboard.bridge")
        self.bus.publish(
            CLIPBOARD_COMMAND_RECEIVED,
            payload,
            source="clipboard.bridge",
        )
        return payload

    def start(self):
        if self._thread and self._thread.is_alive():
            return self

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="ClipboardEventBridge",
            daemon=True,
        )
        self._thread.start()
        self._logger.info("ClipboardEventBridge started")
        return self

    def stop(self, timeout: float = 2.0):
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=timeout)
        self._logger.info("ClipboardEventBridge stopped")

    def health(self):
        thread_alive = bool(self._thread and self._thread.is_alive())
        return {
            "running": thread_alive,
            "poll_interval": self.poll_interval,
            "last_digest": self._last_digest,
            "last_observed_at": self._last_observed_at,
            "last_kind": self._last_kind,
        }

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as exc:
                self._logger.exception("clipboard bridge loop failure: %s", exc)
            self._stop_event.wait(self.poll_interval)


def _sha256(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
