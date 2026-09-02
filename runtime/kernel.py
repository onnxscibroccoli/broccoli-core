"""The atom.

Sense intent → match a schema → act (or dry-run) → confirm → remember.
Stdlib only. Runs on a phone. Runs in CI. Runs nowhere special.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from runtime.automation.engine import AutomationEngine
from runtime.intent_schema import IntentSchemaEngine, Step
from runtime.onnx_runtime import OnnxIntentClassifier

try:
    from runtime.eventbus.bus import EventBus
except Exception:  # pragma: no cover
    from runtime.event_bus import EventBus  # type: ignore


class Kernel:
    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self.bus = bus or EventBus()
        self.intents = IntentSchemaEngine()
        self.classifier = OnnxIntentClassifier()
        self.actions = AutomationEngine()
        self._wire_executors()

    def _wire_executors(self) -> None:
        def bind(name: str):
            def _fn(step: Step) -> bool:
                ctx = dict(step.params or {})
                ctx.setdefault("text", (step.params or {}).get("text", ""))
                return bool(self.actions.run(name, ctx).get("ok"))
            return _fn

        for action in (
            "bluetooth.on",
            "bluetooth.off",
            "bluetooth.toggle",
            "notification",
            "reminder.set",
            "calendar.open",
        ):
            self.intents.register_executor(action, bind(action))

    def tick(self, text: str, dry_run: bool = True) -> Dict[str, Any]:
        classified = self.classifier.classify(text)
        schema = self.intents.resolve(text)
        payload = {
            "text": text,
            "classified": classified["intent"],
            "schema": schema.key,
        }
        if hasattr(self.bus, "emit"):
            self.bus.emit("IntentSeen", payload)
        elif hasattr(self.bus, "publish"):
            self.bus.publish("IntentSeen", payload)
        ran = self.intents.run(text, dry_run=dry_run)
        action = self.actions.run(
            classified["intent"],
            {"text": text, "dry_run": dry_run},
        )
        ok = bool(action.get("ok")) if classified["intent"] != "unknown" else True
        if not dry_run and ran.get("status") == "partial":
            ok = bool(action.get("ok"))
        out = {
            "ok": ok,
            "text": text,
            "intent": classified["intent"],
            "schema": schema.key,
            "confidence": schema.confidence,
            "schema_run": ran,
            "action": action,
        }
        if hasattr(self.bus, "emit"):
            self.bus.emit("IntentDone", out)
        elif hasattr(self.bus, "publish"):
            self.bus.publish("IntentDone", out)
        return out
