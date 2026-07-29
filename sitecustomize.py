from __future__ import annotations

import logging
import os
import sys

_BOOTSTRAPPED = False
_BRIDGE = None


def _should_boot_clipboard_bridge() -> bool:
    argv0 = os.path.basename(sys.argv[0] or "")
    if not argv0:
        return False

    if "pytest" in argv0 or "py.test" in argv0:
        return False

    if os.environ.get("BROCCOLI_DISABLE_CLIPBOARD_BRIDGE") == "1":
        return False

    if os.environ.get("BROCCOLI_ENABLE_CLIPBOARD_BRIDGE") == "1":
        return True

    return sys.argv[0].endswith("runtime/main.py") or argv0 == "main.py"


def _bootstrap():
    global _BOOTSTRAPPED, _BRIDGE
    if _BOOTSTRAPPED or not _should_boot_clipboard_bridge():
        return

    try:
        from runtime.eventbus.service import bus
        from runtime.clipboard.adapter import ClipboardEventBridge
        from runtime.clipboard.consumers import register_clipboard_consumers

        register_clipboard_consumers(bus)
        _BRIDGE = ClipboardEventBridge(bus)
        _BRIDGE.start()
        _BOOTSTRAPPED = True
    except Exception as exc:
        logging.getLogger("clipboard.bootstrap").debug(
            "clipboard bridge bootstrap skipped: %s",
            exc,
        )


_bootstrap()
