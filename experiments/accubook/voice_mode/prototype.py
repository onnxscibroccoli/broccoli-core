"""Accubook voice-to-text agentic mode prototype scaffold.

STT input -> keyword match -> slot extraction -> missing-slot detection
-> single clarifying question -> action execution.

Target: Android 15, ≤4 GB RAM. Pure-Python zero-model path.
Reuses keyword-fallback style from runtime/onnx_runtime.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Slot:
    name: str
    value: Optional[str] = None
    required: bool = True


@dataclass
class Intent:
    name: str
    keywords: List[str]
    slots: List[Slot] = field(default_factory=list)
    action: str = ""


# Minimal intent catalog for prototype
INTENTS: List[Intent] = [
    Intent(
        name="log_note",
        keywords=["note", "log", "remember", "write down"],
        slots=[Slot("customer"), Slot("text", required=True)],
        action="create_field_note",
    ),
    Intent(
        name="schedule_job",
        keywords=["schedule", "book", "appointment", "job for"],
        slots=[Slot("customer"), Slot("date"), Slot("time", required=False)],
        action="schedule_job",
    ),
    Intent(
        name="record_payment",
        keywords=["payment", "paid", "cash", "check"],
        slots=[Slot("customer"), Slot("amount"), Slot("method", required=False)],
        action="record_payment_stub",
    ),
]


def keyword_match(transcript: str) -> Optional[Intent]:
    low = (transcript or "").lower()
    for intent in INTENTS:
        if any(k in low for k in intent.keywords):
            return intent
    return None


def extract_slots(transcript: str, intent: Intent) -> Dict[str, Optional[str]]:
    """Very simple prototype extractor. Real version would use patterns + gazetteer."""
    slots: Dict[str, Optional[str]] = {s.name: None for s in intent.slots}
    # Placeholder: in production, parse names, dates, amounts, etc.
    if "for " in transcript.lower():
        # crude customer extraction
        parts = transcript.lower().split("for ", 1)
        if len(parts) > 1:
            slots["customer"] = parts[1].split()[0] if parts[1].split() else None
    return slots


def missing_slots(intent: Intent, filled: Dict[str, Optional[str]]) -> List[str]:
    return [s.name for s in intent.slots if s.required and not filled.get(s.name)]


def clarifying_question(missing: List[str]) -> str:
    if not missing:
        return ""
    if len(missing) == 1:
        return f"What is the {missing[0]}?"
    return f"I need the {missing[0]} and {missing[1]}. Let's start with {missing[0]}."


def process_transcript(transcript: str) -> Dict[str, Any]:
    intent = keyword_match(transcript)
    if not intent:
        return {
            "status": "unknown",
            "question": "I didn't catch that. Try 'log note', 'schedule job', or 'record payment'.",
            "action": None,
        }

    filled = extract_slots(transcript, intent)
    missing = missing_slots(intent, filled)

    if missing:
        return {
            "status": "clarify",
            "intent": intent.name,
            "slots": filled,
            "question": clarifying_question(missing),
            "action": None,
        }

    return {
        "status": "ready",
        "intent": intent.name,
        "slots": filled,
        "question": f"Confirm: {intent.action} with {filled}?",
        "action": intent.action,
    }


if __name__ == "__main__":
    samples = [
        "log a note for smith the roof is leaking",
        "schedule job",
        "record payment of 500",
    ]
    for s in samples:
        print(s, "->", process_transcript(s))
