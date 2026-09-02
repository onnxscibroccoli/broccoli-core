"""Agentic automation engine (M4) + first live automation: Bluetooth (M5)."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from runtime.device import bluetooth_set, notify


class AutomationEngine:
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
            result.setdefault("ok", False)
            return result
        except Exception as exc:
            return {"ok": False, "intent": intent, "error": str(exc)}

    def _register_builtins(self) -> None:
        self.register("toggle_bluetooth", self._bluetooth_toggle)
        self.register("bluetooth.on", self._bluetooth_on)
        self.register("bluetooth.off", self._bluetooth_off)
        self.register("bluetooth.toggle", self._bluetooth_toggle)
        self.register("notification", self._notify)
        self.register("set_reminder", self._reminder_stub)
        self.register("reminder.set", self._reminder_stub)
        self.register("open_calendar", self._calendar_stub)
        self.register("calendar.open", self._calendar_stub)
        self.register("search_memory", self._memory_stub)
        self.register("report_status", self._status)

    def _bluetooth_on(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        if ctx.get("dry_run"):
            return {"action": "bluetooth", "state": "on", "dry_run": True, "ok": True}
        return bluetooth_set(want_on=True)

    def _bluetooth_off(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        if ctx.get("dry_run"):
            return {"action": "bluetooth", "state": "off", "dry_run": True, "ok": True}
        return bluetooth_set(want_on=False)

    def _bluetooth_toggle(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        if ctx.get("dry_run"):
            return {"action": "bluetooth", "state": "toggled", "dry_run": True, "ok": True}
        return bluetooth_set(toggle=True)

    def _notify(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        text = str(ctx.get("text") or ctx.get("content") or "Broccoli.")
        if ctx.get("dry_run"):
            return {"action": "notification", "text": text, "dry_run": True, "ok": True}
        return notify(text)

    def _reminder_stub(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "reminder", "scheduled": ctx.get("text", ""), "stub": True, "ok": True}

    def _calendar_stub(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "calendar", "opened": True, "stub": True, "ok": True}

    def _memory_stub(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "memory", "query": ctx.get("text", ""), "stub": True, "ok": True}

    def _status(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "status", "ok": True, "message": "Broccoli Core online."}

    def health(self) -> Dict[str, Any]:
        return {"registered_intents": sorted(self._actions.keys())}
