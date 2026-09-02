"""The atom.

Sense intent → match a schema → act (or dry-run) → confirm → remember.
Stdlib only. Runs on a phone. Runs in CI. Runs nowhere special.
"""
from __future__ import annotations

from typing import Any, Dict

from runtime.automation.engine import AutomationEngine
from runtime.event_bus import EventBus
from runtime.intent_schema import IntentSchemaEngine
from runtime.onnx_runtime import OnnxIntentClassifier


class Kernel:
    def __init__(self, bus: EventBus | None = None) -> None:
        self.bus = bus or EventBus()
        self.intents = IntentSchemaEngine()
        self.classifier = OnnxIntentClassifier()
        self.actions = AutomationEngine()

    def tick(self, text: str, dry_run: bool = True) -> Dict[str, Any]:
        classified = self.classifier.classify(text)
        schema = self.intents.resolve(text)
        self.bus.emit(
            "IntentSeen",
            {"text": text, "classified": classified["intent"], "schema": schema.key},
        )
        ran = self.intents.run(text, dry_run=dry_run)
        if dry_run:
            action = self.actions.run(classified["intent"], {"dry_run": True, "text": text})
        else:
            action = self.actions.run(classified["intent"], {"text": text})
        out = {
            "ok": True,
            "text": text,
            "intent": classified["intent"],
            "schema": schema.key,
            "confidence": schema.confidence,
            "schema_run": ran,
            "action": action,
        }
        self.bus.emit("IntentDone", out)
        return out
