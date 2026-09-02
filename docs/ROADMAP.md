# Broccoli Core — Master Roadmap

**Vision:** Invert the surveillance stack. Every sensor, every conversation, every behavioral signal that telecoms, OEMs, ad networks, and governments harvest for profit — Broccoli captures for the *user*, encrypted, offline, and agentic.

This is not a chatbot wrapper. This is a personal intelligence layer that:
- remembers everything the user has ever said to any AI, across every provider
- turns that memory into a searchable, vectorized, personalizable model
- acts on intent (Bluetooth, calendar, reminders) without making the user think
- reports back to the user how they're doing — voice stress, friction points, recovery progress
- never sells, never phones home, never trains on the user's data for anyone else

Designed for someone rebuilding life after a brain injury: fewer decisions, more defaults, full auditability, instant revocation.

---

## Milestones

| # | Milestone | Status | Issue |
|---|-----------|--------|-------|
| M1 | Onyx runtime hardening + CI matrix | in progress | #29 |
| M2 | Multi-provider chat history ingest | queued | #30 |
| M3 | Vector store + embedding pipeline | queued | #31 |
| M4 | Account mapping + multi-account iteration | queued | #32 |
| M5 | Agentic automation — Bluetooth toggle from intent | queued | #33 |
| M6 | Sensor pipeline — voice/touch/gaze → user insight | queued | #34 |
| M7 | Calendar + reminder integration | queued | #35 |
| M8 | Encrypted offline-first memory store | queued | #36 |
| M9 | Self-hosted vector training loop (LoRA) | queued | #37 |

---

## Principles (non-negotiable)

1. **Accessibility-first.** If it excludes someone without enterprise access, it's wrong.
2. **Provider-agnostic.** Grok, ChatGPT, Gemini, Claude, web AI — all first-class, none sacred.
3. **Resilient and autonomous.** No manual token rotation. Circuit breakers. Graceful degradation.
4. **Event-driven.** Everything emits to the EventBus. Nothing blocks.
5. **Production-ready.** Structured logs, metrics, error recovery, tests.
6. **User-owned.** Data encrypted at rest, offline by default, exportable, wipeable. The user's property, period.
7. **The inversion.** The same telemetry harvested for profit is used here to help the user function.

---

## Dependency graph

```
M1 (runtime) ──┬──> M2 (ingest) ──> M3 (vectors) ──> M9 (train)
               │                      │
               ├──> M4 (accounts) ───┘
               │
               ├──> M5 (automations) ◄── M7 (calendar)
               │
               ├──> M6 (sensors) ────> M8 (encrypted store) <── all
               │
               └──> M8 (store) <──────────── M2, M3, M5, M6, M7
```

M5 is the first *felt* win: gesture in, Bluetooth on, confirmation. That's the moment Broccoli stops being a project and starts being a life tool.

---

## What "done" looks like

A user with a brain injury opens their phone. They say or gesture "bluetooth." Broccoli turns it on, confirms, logs it, and — because it noticed last week they always forget to turn it off — suggests a 30-minute auto-off. The user nods. Done. No app-switching, no menus, no thinking.

That's the whole fucking point.
