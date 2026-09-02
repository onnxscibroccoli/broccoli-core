"""Agentic automation engine (M4) + first live automation: Bluetooth (M5).

Intent -> action -> confirm. The engine takes a classified intent,
executes a registered action, and returns a confirmation the user can
verify. Designed for brain-injury accessibility: the user initiates,
the phone acts, the user gets a clear confirmation.
"""
from __future__ import annotations

import subprocess
from typing import Any, Callable, Dict, Optional


class AutomationEngine:
    """Registry of intent -> action. Each action returns a result dict."""

    def __init__(self) -> None:
        self._actions: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._register_builtins()

    def register(self, intent: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self._actions[intent] = fn

    def run(self, intent: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = context or {}
        fn = self._actions.get(intent)
        if fn is None:
            return {"ok": False, "intent": intent, "error": "no action registered"}
        try:
            result = fn(ctx)
            result.setdefault("intent", intent)
            result.setdefault("ok", True)
            return result
        except Exception as exc:
            return {"ok": False, "intent": intent, "error": str(exc)}

    def _register_builtins(self) -> None:
        self.register("toggle_bluetooth", self._bluetooth)
        self.register("set_reminder", self._reminder_stub)
        self.register("open_calendar", self._calendar_stub)
        self.register("search_memory", self._memory_stub)
        self.register("report_status", self._status)

    # ── actions ─────────────────────────────────────────────────
    def _bluetooth(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Toggle Bluetooth via Termux cmd. Falls back to a dry-run."""
        dry = ctx.get("dry_run", False)
        if dry:
            return {"action": "bluetooth", "state": "toggled", "dry_run": True}
        try:
            # termux-api: cmd bluetooth toggle
            r = subprocess.run(
                ["cmd", "bluetooth", "toggle"],
                capture_output=True, text=True, timeout=10,
            )
            return {
                "action": "bluetooth",
                "state": "toggled",
                "returncode": r.returncode,
                "stdout": (r.stdout or "").strip()[:200],
            }
        except FileNotFoundError:
            # Not on Termux / no termux-api: report what would happen.
            return {
                "action": "bluetooth",
                "state": "toggled",
                "simulated": True,
                "note": "termux-api cmd bluetooth toggle not available; simulated",
            }
        except Exception as exc:
            return {"action": "bluetooth", "error": str(exc)}

    def _reminder_stub(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "reminder", "scheduled": ctx.get("text", ""), "stub": True}

    def _calendar_stub(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "calendar", "opened": True, "stub": True}

    def _memory_stub(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "memory", "query": ctx.get("text", ""), "stub": True}

    def _status(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "status", "ok": True, "message": "Broccoli Core online."}

    def health(self) -> Dict[str, Any]:
        return {"registered_intents": sorted(self._actions.keys())}
