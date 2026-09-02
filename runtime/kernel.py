"""The atom.

Sense intent → match a schema → act (or dry-run) → confirm → remember.
One phrase fires one schema. Never classify-and-toggle after a schema on.
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

    def _emit(self, topic: str, payload: Dict[str, Any]) -> None:
        if hasattr(self.bus, "emit"):
            self.bus.emit(topic, payload)
        elif hasattr(self.bus, "publish"):
            self.bus.publish(topic, payload)

    def tick(self, text: str, dry_run: bool = True) -> Dict[str, Any]:
        classified = self.classifier.classify(text)
        schema = self.intents.resolve(text)
        self._emit(
            "IntentSeen",
            {"text": text, "classified": classified["intent"], "schema": schema.key},
        )
        # Schema is the only actuator. A second engine.run() on the
        # classified label turned Bluetooth back off after schema on.
        ran = self.intents.run(text, dry_run=dry_run)
        ok = ran.get("status") in ("done", "dry")
        out = {
            "ok": ok,
            "text": text,
            "intent": classified["intent"],
            "schema": schema.key,
            "confidence": schema.confidence,
            "schema_run": ran,
        }
        self._emit("IntentDone", out)
        return out
