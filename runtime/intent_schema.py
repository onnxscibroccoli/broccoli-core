"""Intent-to-Automation Schema Engine.

Core premise: if a human can build an automation programmatically (Tasker,
MacroDroid, Shortcuts, JS, shell), an agentic system should be able to
vectorize the user's intent, match it against a library of proven schemas,
and emit a repeatable, logical, executable plan — without the user writing
the automation or reviewing an LLM's implementation.

Backends are swappable per task:
  - markov: cheap, fast, pattern-based for repetitive intents
  - onnx: small quantized classifier for intent routing
  - llm: Grok CLI / provider for novel or ambiguous intents
  - hybrid: cascade cheap -> expensive only on low confidence

Every successful execution is recorded into the encrypted vector memory
so the next similar intent resolves faster and more accurately.
"""
from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


SCHEMA_VERSION = "1.0"


@dataclass
class Step:
    """One atomic, executable step in an automation."""
    action: str                      # e.g. "bluetooth.toggle", "calendar.create"
    params: Dict[str, Any] = field(default_factory=dict)
    confirm: str = ""               # user-visible confirmation text
    rollback: Optional[str] = None   # action to undo if a later step fails
    timeout_s: float = 10.0
    requires_user: bool = False      # pause for explicit authorization


@dataclass
class AutomationSchema:
    """A proven, repeatable recipe for fulfilling an intent."""
    intent: str
    steps: List[Step]
    backend: str = "hybrid"
    confidence: float = 0.0
    source: str = "library"           # library | learned | llm | emulator
    tags: List[str] = field(default_factory=list)
    version: str = SCHEMA_VERSION

    def to_tasker_xml(self) -> str:
        """Export a Tasker-compatible XML profile (best-effort)."""
        lines = ['<TaskerData sr="" dvi="1" tv="6.0">']
        lines.append('  <Profile sr="prof1" ve="2">')
        lines.append(f'    <id>1</id><nme>{self.intent}</nme>')
        lines.append('    <mid0>3</mid0><clp>true</clp><cme>true</cme>')
        lines.append('  </Profile>')
        lines.append('  <Task sr="task1">')
        lines.append(f'    <id>1</id><nme>{self.intent}</nme>')
        for i, s in enumerate(self.steps, start=1):
            lines.append(f'    <Action sr="act{i}" ve="7">')
            lines.append(f'      <code>{_action_code(s.action)}</code>')
            lines.append(f'      <arg nme="{s.action}" val="{json.dumps(s.params)}"/>')
            lines.append('    </Action>')
        lines.append('  </Task>')
        lines.append('</TaskerData>')
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


def _action_code(action: str) -> int:
    """Map semantic action names to Tasker action codes (subset)."""
    table = {
        "bluetooth.toggle": 37,
        "bluetooth.on": 37,
        "wifi.toggle": 38,
        "notification": 548,
        "wait": 30,
        "shell": 123,
        "app.launch": 20,
        "calendar.create": 547,
    }
    return table.get(action, 123)


# ---------------------------------------------------------------------------
# Schema library: proven recipes. Grows as the emulator / LLM discovers more.
# ---------------------------------------------------------------------------
LIBRARY: Dict[str, AutomationSchema] = {
    "turn_on_bluetooth": AutomationSchema(
        intent="turn on bluetooth",
        steps=[
            Step(action="bluetooth.on", params={}, confirm="Bluetooth turned on"),
            Step(action="notification", params={"text": "Bluetooth on"}),
        ],
        confidence=0.95, source="library", tags=["device", "connectivity"],
    ),
    "turn_off_bluetooth": AutomationSchema(
        intent="turn off bluetooth",
        steps=[
            Step(action="bluetooth.toggle", params={"state": "off"}),
            Step(action="notification", params={"text": "Bluetooth off"}),
        ],
        confidence=0.95, source="library", tags=["device", "connectivity"],
    ),
    "schedule_reminder": AutomationSchema(
        intent="remind me to {task} at {time}",
        steps=[
            Step(action="calendar.create", params={"title": "{task}", "when": "{time}"},
                  confirm="Reminder set: {task}"),
        ],
        confidence=0.8, source="library", tags=["calendar", "reminder"],
    ),
}


# ---------------------------------------------------------------------------
# Vector index over intent phrases (pure-Python TF-IDF, no deps).
# ---------------------------------------------------------------------------
class IntentIndex:
    def __init__(self) -> None:
        self._docs: List[Tuple[str, str]] = []   # (key, text)
        self._tf: List[Dict[str, float]] = []
        self._df: Dict[str, int] = {}
        self._n = 0

    def add(self, key: str, text: str) -> None:
        toks = _tokenize(text)
        tf = _tf(toks)
        for t in set(toks):
            self._df[t] = self._df.get(t, 0) + 1
        self._docs.append((key, text))
        self._tf.append(tf)
        self._n += 1

    def search(self, query: str, k: int = 3) -> List[Tuple[str, float]]:
        if self._n == 0:
            return []
        q = _tf(_tokenize(query))
        scores = []
        for i, tf in enumerate(self._tf):
            scores.append((self._docs[i][0], _cosine(q, tf, self._df, self._n)))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


def _tokenize(text: str) -> List[str]:
    return [w for w in text.lower().split() if w]


def _tf(tokens: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for t in tokens:
        out[t] = out.get(t, 0) + 1
    n = len(tokens) or 1
    return {t: c / n for t, c in out.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float],
             df: Dict[str, int], n: int) -> float:
    if not a or not b:
        return 0.0
    num = 0.0
    for t, av in a.items():
        if t in b:
            idf = math.log((n + 1) / (df.get(t, 0) + 1)) + 1
            num += av * b[t] * idf * idf
    na = math.sqrt(sum((v * math.log((n + 1) / (df.get(t, 0) + 1) + 1)) ** 2
                        for t, v in a.items()))
    nb = math.sqrt(sum((v * math.log((n + 1) / (df.get(t, 0) + 1) + 1)) ** 2
                        for t, v in b.items()))
    return num / (na * nb) if na and nb else 0.0


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
class MarkovBackend:
    """Cheap pattern matcher: transitions between observed intent tokens."""
    def __init__(self) -> None:
        self.trans: Dict[str, Dict[str, int]] = {}

    def learn(self, intent: str, schema_key: str) -> None:
        toks = _tokenize(intent)
        for i in range(len(toks) - 1):
            self.trans.setdefault(toks[i], {})[toks[i + 1]] = \
                self.trans.get(toks[i], {}).get(toks[i + 1], 0) + 1
        self.trans.setdefault(toks[-1] if toks else "", {})[schema_key] = \
            self.trans.get(toks[-1] if toks else "", {}).get(schema_key, 0) + 1

    def suggest(self, intent: str) -> Optional[str]:
        toks = _tokenize(intent)
        if not toks:
            return None
        cur = toks[-1]
        nxt = self.trans.get(cur, {})
        if not nxt:
            return None
        return max(nxt, key=nxt.get)


class ONNXBackend:
    """Optional ONNX classifier. Falls back silently if no model file."""
    def __init__(self, model_path: Optional[str] = None) -> None:
        self.session = None
        self.labels: List[str] = []
        if model_path and Path(model_path).exists():
            try:
                import onnxruntime as ort  # type: ignore
                self.session = ort.InferenceSession(model_path,
                                                   providers=["CPUExecutionProvider"])
                self.labels = ["bluetooth", "calendar", "reminder", "search", "other"]
            except Exception:
                self.session = None

    def classify(self, intent: str) -> Tuple[str, float]:
        if self.session is None:
            return "other", 0.0
        # Real tokenization would use the model's tokenizer; placeholder.
        return "other", 0.0


class LLMBackend:
    """Novel/ambiguous intents -> provider (Grok CLI). Returns a schema or None."""
    def __init__(self, provider: Any = None) -> None:
        self.provider = provider

    def synthesize(self, intent: str) -> Optional[AutomationSchema]:
        if self.provider is None:
            return None
        prompt = (
            "Convert this user intent into a JSON automation schema. "
            "Return ONLY JSON with keys: intent, steps (list of {action, params, confirm}). "
            f"Intent: {intent}\n"
            "Use only these actions: bluetooth.on, bluetooth.toggle, wifi.toggle, "
            "notification, calendar.create, shell, app.launch, wait."
        )
        try:
            out = self.provider.complete(prompt)
            data = json.loads(out)
            steps = [Step(**s) for s in data.get("steps", [])]
            return AutomationSchema(intent=data.get("intent", intent), steps=steps,
                                    source="llm", confidence=0.6)
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Emulator: trial-and-error sandbox that develops schemas remotely.
# ---------------------------------------------------------------------------
class Emulator:
    """Dry-runs a candidate schema against a mock device, records success/failure,
    and promotes working schemas into the library. This is where 'trial and
    error on an emulator' lives — cheap, offline, no real device risk."""
    def __init__(self) -> None:
        self.history: List[Dict[str, Any]] = []

    def trial(self, schema: AutomationSchema) -> bool:
        ok = all(self._simulate(s) for s in schema.steps)
        self.history.append({"schema": schema.intent, "ok": ok, "t": time.time()})
        return ok

    def _simulate(self, step: Step) -> bool:
        # Deterministic mock: known actions succeed; unknown -> 80% success.
        if step.action in ("bluetooth.on", "bluetooth.toggle", "notification",
                           "calendar.create", "wait"):
            return True
        return random.random() < 0.8

    def promote(self, schema: AutomationSchema) -> None:
        if self.trial(schema):
            key = schema.intent.lower().replace(" ", "_")
            LIBRARY[key] = schema


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------
class IntentSchemaEngine:
    """Vectorize intent -> match proven schema -> execute or synthesize."""
    def __init__(self, provider: Any = None, memory: Any = None) -> None:
        self.index = IntentIndex()
        self.markov = MarkovBackend()
        self.onnx = ONNXBackend()
        self.llm = LLMBackend(provider)
        self.emulator = Emulator()
        self.memory = memory
        self.executor: Dict[str, Callable[[Step], bool]] = {}
        self._seed_index()

    def _seed_index(self) -> None:
        for key, sch in LIBRARY.items():
            self.index.add(key, sch.intent)
            self.markov.learn(sch.intent, key)

    def register_executor(self, action: str, fn: Callable[[Step], bool]) -> None:
        self.executor[action] = fn

    def resolve(self, intent: str) -> AutomationSchema:
        """Return the best schema for an intent, synthesizing if needed."""
        # 1. Exact / near vector match against proven library.
        hits = self.index.search(intent, k=1)
        if hits and hits[0][1] >= 0.55:
            key = hits[0][0]
            sch = LIBRARY[key]
            sch.confidence = hits[0][1]
            return sch
        # 2. Markov suggestion.
        mk = self.markov.suggest(intent)
        if mk and mk in LIBRARY:
            return LIBRARY[mk]
        # 3. ONNX classifier.
        label, conf = self.onnx.classify(intent)
        if conf >= 0.7 and label in LIBRARY:
            return LIBRARY[label]
        # 4. LLM synthesis for novel intents.
        syn = self.llm.synthesize(intent)
        if syn is not None:
            if self.emulator.trial(syn):
                self.emulator.promote(syn)
                self.index.add(syn.intent.lower().replace(" ", "_"), syn.intent)
                self.markov.learn(syn.intent, syn.intent.lower().replace(" ", "_"))
            return syn
        # 5. Fallback: single notification step.
        return AutomationSchema(
            intent=intent,
            steps=[Step(action="notification", params={"text": f"Could not resolve: {intent}"})],
            confidence=0.1, source="fallback",
        )

    def run(self, intent: str, dry_run: bool = False) -> Dict[str, Any]:
        """Resolve + execute. Returns a result dict."""
        sch = self.resolve(intent)
        results = []
        for step in sch.steps:
            if step.requires_user:
                return {"status": "needs_user", "step": asdict(step), "schema": sch.intent}
            fn = self.executor.get(step.action)
            if fn is None:
                results.append({"action": step.action, "ok": False, "err": "no executor"})
                continue
            if dry_run:
                results.append({"action": step.action, "ok": True, "dry": True})
                continue
            try:
                ok = fn(step)
            except Exception as e:  # noqa: BLE001
                ok = False
                results.append({"action": step.action, "ok": False, "err": str(e)})
                if step.rollback:
                    rb = self.executor.get(step.rollback)
                    if rb:
                        rb(step)
                continue
            results.append({"action": step.action, "ok": ok, "confirm": step.confirm})
            if not ok and step.rollback:
                rb = self.executor.get(step.rollback)
                if rb:
                    rb(step)
        if self.memory is not None:
            try:
                self.memory.remember(intent, sch, results)
            except Exception:
                pass
        return {"status": "done", "schema": sch.intent, "confidence": sch.confidence,
                "source": sch.source, "results": results}


def default_engine(provider: Any = None, memory: Any = None) -> IntentSchemaEngine:
    return IntentSchemaEngine(provider=provider, memory=memory)
