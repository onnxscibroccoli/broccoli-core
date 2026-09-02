"""Intent → schema → execute. Zero-dep kernel for Broccoli Core.

The machine wants: tokenize, score, pick a recipe, run steps, remember.
No network. No commercial ledger. Works on Termux and in CI.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape

_TOKEN = re.compile(r"[a-z0-9']+")


def tokenize(text: str) -> List[str]:
    return _TOKEN.findall((text or "").lower())


def _slug(text: str) -> str:
    toks = tokenize(text)
    return "_".join(toks) if toks else "untitled"


@dataclass
class Step:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutomationSchema:
    intent: str
    steps: List[Step] = field(default_factory=list)
    confidence: float = 1.0
    key: str = ""

    def __post_init__(self) -> None:
        if not self.key:
            self.key = _slug(self.intent)

    def to_tasker_xml(self) -> str:
        name = escape(self.intent)
        bits = ["<TaskerData sr=\"\" dvi=\"1\" tv=\"6.2.22\">", f"<Task sr=\"task\"><nme>{name}</nme>"]
        for i, step in enumerate(self.steps, 1):
            bits.append(
                f"<Action sr=\"act{i}\" ve=\"7\"><code>123</code>"
                f"<Str sr=\"arg0\" ve=\"3\">{escape(step.action)}</Str>"
                f"<Str sr=\"arg1\" ve=\"3\">{escape(str(step.params))}</Str></Action>"
            )
        bits.append("</Task></TaskerData>")
        return "".join(bits)


LIBRARY: Dict[str, AutomationSchema] = {}


def _seed() -> None:
    LIBRARY["turn_on_bluetooth"] = AutomationSchema(
        intent="turn on bluetooth",
        key="turn_on_bluetooth",
        steps=[
            Step("bluetooth.on", {}),
            Step("notification", {"text": "Bluetooth on."}),
        ],
    )
    LIBRARY["turn_off_bluetooth"] = AutomationSchema(
        intent="turn off bluetooth",
        key="turn_off_bluetooth",
        steps=[
            Step("bluetooth.off", {}),
            Step("notification", {"text": "Bluetooth off."}),
        ],
    )
    LIBRARY["toggle_bluetooth"] = AutomationSchema(
        intent="toggle bluetooth",
        key="toggle_bluetooth",
        steps=[Step("bluetooth.toggle", {}), Step("notification", {"text": "Bluetooth toggled."})],
    )
    LIBRARY["set_reminder"] = AutomationSchema(
        intent="set a reminder",
        key="set_reminder",
        steps=[Step("reminder.set", {}), Step("notification", {"text": "Reminder set."})],
    )
    LIBRARY["open_calendar"] = AutomationSchema(
        intent="open calendar",
        key="open_calendar",
        steps=[Step("calendar.open", {})],
    )


_seed()


class IntentIndex:
    """Bag-of-words cosine over schema phrases. Tiny on purpose."""

    def __init__(self) -> None:
        self._docs: Dict[str, List[str]] = {}
        self._df: Dict[str, int] = defaultdict(int)

    def add(self, doc_id: str, text: str) -> None:
        toks = tokenize(text)
        if doc_id in self._docs:
            for t in set(self._docs[doc_id]):
                self._df[t] = max(0, self._df[t] - 1)
        self._docs[doc_id] = toks
        for t in set(toks):
            self._df[t] += 1

    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        q = tokenize(query)
        if not q or not self._docs:
            return []
        n = max(1, len(self._docs))
        qtf: Dict[str, int] = defaultdict(int)
        for t in q:
            qtf[t] += 1

        def vec(tf: Dict[str, int]) -> Dict[str, float]:
            out = {}
            for t, c in tf.items():
                idf = math.log((n + 1) / (self._df.get(t, 0) + 1)) + 1.0
                out[t] = c * idf
            return out

        qv = vec(qtf)
        qn = math.sqrt(sum(v * v for v in qv.values())) or 1.0
        scored: List[Tuple[str, float]] = []
        for did, toks in self._docs.items():
            tf: Dict[str, int] = defaultdict(int)
            for t in toks:
                tf[t] += 1
            dv = vec(tf)
            dn = math.sqrt(sum(v * v for v in dv.values())) or 1.0
            dot = sum(qv.get(t, 0.0) * dv.get(t, 0.0) for t in set(qv) | set(dv))
            scored.append((did, dot / (qn * dn)))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]


class MarkovBackend:
    """Next-token memory for short intents. One dict. That's the machine."""

    def __init__(self) -> None:
        self._next: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def learn(self, phrase: str, label: str) -> None:
        toks = tokenize(phrase)
        if not toks:
            return
        pred = tokenize(label)[-1] if tokenize(label) else label
        prefix = " ".join(toks[:-1]) if len(toks) > 1 else toks[0]
        self._next[prefix][pred] += 1
        self._next[" ".join(toks[:2]) if len(toks) >= 2 else toks[0]][pred] += 1

    def suggest(self, prefix: str) -> Optional[str]:
        toks = tokenize(prefix)
        keys = [" ".join(toks), toks[-1] if toks else ""]
        best, best_n = None, 0
        for k in keys:
            for word, n in self._next.get(k, {}).items():
                if n > best_n:
                    best, best_n = word, n
        return best


class Emulator:
    """Dry-run a schema. Promote winners into LIBRARY."""

    def trial(self, schema: AutomationSchema) -> bool:
        return bool(schema.steps)

    def promote(self, schema: AutomationSchema) -> None:
        LIBRARY[schema.key or _slug(schema.intent)] = schema


class IntentSchemaEngine:
    def __init__(self) -> None:
        self.index = IntentIndex()
        self.markov = MarkovBackend()
        self.emulator = Emulator()
        self._exec: Dict[str, Callable[[Step], Any]] = {}
        for key, sch in list(LIBRARY.items()):
            self.index.add(key, sch.intent)
            self.markov.learn(sch.intent, key)

    def register_executor(self, action: str, fn: Callable[[Step], Any]) -> None:
        self._exec[action] = fn

    def resolve(self, text: str) -> AutomationSchema:
        hits = self.index.search(text, k=1)
        raw = (text or "").strip()
        if hits and hits[0][1] > 0:
            key = hits[0][0]
            sch = LIBRARY.get(key)
            if sch:
                return AutomationSchema(
                    intent=raw or sch.intent,
                    steps=list(sch.steps),
                    confidence=max(0.5, min(1.0, hits[0][1])),
                    key=key,
                )
        low = raw.lower()
        if "bluetooth" in low:
            key = "turn_off_bluetooth" if "off" in low else "turn_on_bluetooth"
            if "toggle" in low:
                key = "toggle_bluetooth"
            sch = LIBRARY[key]
            return AutomationSchema(intent=raw, steps=list(sch.steps), confidence=0.7, key=key)
        if "remind" in low:
            sch = LIBRARY["set_reminder"]
            return AutomationSchema(intent=raw, steps=list(sch.steps), confidence=0.6, key=sch.key)
        return AutomationSchema(intent=raw, steps=[], confidence=0.0)

    def run(self, text: str, dry_run: bool = True) -> Dict[str, Any]:
        sch = self.resolve(text)
        results = []
        if dry_run:
            return {"status": "dry", "schema": sch.key, "steps": [s.action for s in sch.steps]}
        for step in sch.steps:
            fn = self._exec.get(step.action)
            if fn is None:
                results.append({"action": step.action, "ok": False, "error": "no executor"})
                continue
            try:
                ok = bool(fn(step))
                results.append({"action": step.action, "ok": ok})
            except Exception as exc:
                results.append({"action": step.action, "ok": False, "error": str(exc)})
        failed = [r for r in results if not r.get("ok")]
        return {
            "status": "done" if not failed else "partial",
            "schema": sch.key,
            "steps": results,
        }
