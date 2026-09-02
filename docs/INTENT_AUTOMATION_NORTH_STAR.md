# Intent-to-Automation: The North Star

## The premise

If a human can create an automation programmatically — Tasker, MacroDroid,
Shortcuts, JavaScript, shell — there is no reason an agentic system cannot
vectorize a user's spoken or typed intent, match it against a library of
proven schemas, and emit a repeatable, logical, executable plan.

The user should never have to:
- write the automation themselves, or
- review an LLM's implementation and say "check my work."

They say what they want. The system finds (or synthesizes) the schema, dry-
runs it on an emulator, and executes it. Confirmation is a notification, not
a code review.

## How it works

```
user intent
    |
    v
[vector index] --match--> proven schema (library)
    | miss
    v
[Markov] --suggest--> pattern-based schema
    | miss
    v
[ONNX classifier] --route--> small model, no LLM cost
    | miss / low confidence
    v
[LLM backend] --synthesize--> novel schema
    |
    v
[Emulator] --trial & error--> promote working schemas to library
    |
    v
[Executor] --real device actions--> confirm via notification
    |
    v
[Encrypted vector memory] --learn--> next time is faster
```

## Backends (pick the cheapest that works)

| Backend | When | Cost |
|---|---|---|
| vector index | known intent | free, instant |
| Markov chain | repetitive patterns | free, instant |
| ONNX (quantized) | intent routing | free, ~ms on device |
| LLM (Grok CLI) | novel / ambiguous | subscription pool |
| hybrid cascade | default | cheap-first |

## Emulator

A dry-run sandbox that develops schemas through trial and error *before*
they ever touch the real device. Working schemas get promoted into the
library. This is where 'remote emulator with trial and error' lives — and it
runs on GitHub Actions for free, no phone required.

## Why this matters

Every telecom, OEM, and ad network already harvests voice, touch, gaze, and
pupil data — and sells it. Broccoli inverts that: the same sensors become
insight *for the user*, triggering automations that serve the user's intent,
not a corporation's profit.

For someone recovering from a brain injury, this is not a convenience. It is
independence: gesture -> action -> confirmation, no thinking required.
