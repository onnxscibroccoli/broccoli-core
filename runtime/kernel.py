"""The atom.

Sense intent → match a schema → act (or dry-run) → confirm → remember.
One phrase fires one schema. Never classify-and-toggle after a schema on.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from runtime.automation.engine import AutomationEngine
from runtime.embed.pipeline import EmbedPipeline
from runtime.intent_schema import IntentSchemaEngine, Step
from runtime.memory.search import HybridSearch
from runtime.memory.vectors import VectorStore
from runtime.memory_vector import EncryptedMemory
from runtime.onnx_runtime import OnnxIntentClassifier

try:
    from runtime.eventbus.bus import EventBus
except Exception:  # pragma: no cover
    from runtime.event_bus import EventBus  # type: ignore


def default_vector_root() -> Path:
    override = os.environ.get("BROCCOLI_VECTOR_ROOT", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".broccoli" / "vectors"


def default_memory_path() -> Path:
    override = os.environ.get("BROCCOLI_MEMORY_PATH", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".broccoli" / "kernel_memory.json"


class Kernel:
    def __init__(
        self,
        bus: Optional[EventBus] = None,
        store_root: Optional[Path] = None,
        memory_path: Optional[Path] = None,
    ) -> None:
        self.bus = bus or EventBus()
        self.intents = IntentSchemaEngine()
        self.classifier = OnnxIntentClassifier()
        self.store_root = Path(store_root) if store_root else default_vector_root()
        self.memory_path = Path(memory_path) if memory_path else default_memory_path()
        self.store = VectorStore(self.store_root)
        self.pipeline = EmbedPipeline(self.store)
        self.recall_engine = HybridSearch(self.store)
        self.memory = EncryptedMemory(self.memory_path)
        self.actions = AutomationEngine(recall=self.recall)
        self._last_memory: Dict[str, Any] = {}
        self._wire_executors()

    def recall(self, query: str):
        return self.recall_engine.recall(query, top_k=5)

    def _wire_executors(self) -> None:
        def bind(name: str):
            def _fn(step: Step) -> bool:
                ctx = dict(step.params or {})
                ctx.setdefault("text", (step.params or {}).get("text", ""))
                result = self.actions.run(name, ctx)
                if name == "search_memory":
                    self._last_memory = result
                return bool(result.get("ok"))
            return _fn

        for action in (
            "bluetooth.on",
            "bluetooth.off",
            "bluetooth.toggle",
            "notification",
            "reminder.set",
            "calendar.open",
            "search_memory",
        ):
            self.intents.register_executor(action, bind(action))

    def _emit(self, topic: str, payload: Dict[str, Any]) -> None:
        if hasattr(self.bus, "emit"):
            self.bus.emit(topic, payload)
        elif hasattr(self.bus, "publish"):
            self.bus.publish(topic, payload)

    def _remember(self, text: str, schema_key: str, dry_run: bool) -> Dict[str, Any]:
        raw = (text or "").strip()
        remembered = {"encrypted": False, "embedded": False}
        if not raw:
            return remembered
        try:
            self.memory.remember(
                raw,
                kind="intent",
                source="kernel",
                schema=schema_key,
                dry_run=dry_run,
            )
            remembered["encrypted"] = True
        except Exception:
            remembered["encrypted"] = False
        try:
            result = self.pipeline.ingest(
                raw,
                source="kernel",
                kind="intent",
                meta={"schema": schema_key, "dry_run": dry_run},
            )
            remembered["embedded"] = bool(result.get("ok"))
            remembered["added"] = int(result.get("added") or 0)
        except Exception:
            remembered["embedded"] = False
        return remembered

    def tick(self, text: str, dry_run: bool = True) -> Dict[str, Any]:
        self._last_memory = {}
        classified = self.classifier.classify(text)
        schema = self.intents.resolve(text)
        self._emit(
            "IntentSeen",
            {"text": text, "classified": classified["intent"], "schema": schema.key},
        )
        # Schema is the only actuator. A second engine.run() on the
        # classified label turned Bluetooth back off after schema on.
        ran = self.intents.run(text, dry_run=dry_run)
        if schema.key == "search_memory" and dry_run:
            # Dry-run still surfaces recall so the phone can confirm
            # before any other actuator fires.
            self._last_memory = self.actions.run("search_memory", {"text": text, "query": text})
        ok = ran.get("status") in ("done", "dry")
        remembered = self._remember(text, schema.key, dry_run)
        out = {
            "ok": ok,
            "text": text,
            "intent": classified["intent"],
            "schema": schema.key,
            "confidence": schema.confidence,
            "schema_run": ran,
            "remembered": remembered,
        }
        if self._last_memory:
            out["memory"] = {
                "query": self._last_memory.get("query", text),
                "hits": self._last_memory.get("hits") or [],
                "stub": bool(self._last_memory.get("stub")),
            }
        self._emit("IntentDone", out)
        return out
