# Broccoli Agent OS — North Star

Date locked: 2026-08-10

## Intent

A hybrid agentic platform: phone as the touch surface, remote Linux
as the heavy computer, Android + accessibility for local actuation.
One continuous control plane so tasks feel seamless across both.

Not a Termux replacement. Not a pure cloud IDE.
A personal Agent OS that restores and amplifies function —
for the builder and for people with severe disabilities.

## Architecture (current → target)

| Layer | Role | Status |
|-------|------|--------|
| Phone (Android + a11y + Termux) | Touch, local apps, sensors, UI dump/actuation | active |
| Off-device Durable Object (`@cloudflare/computer`) | Durable workspace, multi-LLM, heavy compute | **spike live** |
| Remote Linux (future) | Full desktop parity: compile, media, torrents, paper trading | planned |
| GitHub | Receipts, code, CI deploy from device | active |

Control principle: **device stays thin; brains and bulk live off-device.**

Live spike:
`https://broccoli-do-spike.onnxscibroccoli.workers.dev`

## Capability domains (backlog)

### 1. Hybrid control
- Phone ↔ remote Linux as one workspace
- Touch-first task UI; voice/a11y as first-class inputs
- Same task queue on-device and off-device

### 2. File / media intelligence
- Inventory large media and torrent-associated files
- Suggest reclaimable space when a torrent remains well-seeded
  (re-downloadable) — human confirms deletes
- Never auto-delete without explicit policy + confirmation

### 3. Build / research agents
- Task packs for Real World Asset protocol work
- Compile / test / document loops off-device; ship artifacts back

### 4. Finance agents (paper first)
- Paper trading integration for purchase confirmation drills
- Portfolio notes and risk checks — no live money until gated

### 5. Telemetry → better self
- Collect operational telemetrics (tasks done, friction points, idle)
- Surface efficiency insights; accessibility metrics included
- Privacy-local by default; export opt-in

### 6. Accessibility core
- Platform usable by able-bodied and by people with severe disabilities
- Restore function: reliable task setting, status, confirmation without
  fine motor or perfect memory assumptions
- TBI-aware UX: short steps, durable state, recoverable context

## Phased delivery

### Phase C0 — done
- Knowledge refs A on main
- Off-device loop decision
- DO VFS spike live + CI deploy from device

### Phase C1 — next
- Result contract: workspace → GitHub receipt
- Thin on-device client (base URL + write/read/ls)
- Task schema: id, goal, domain, status, artifacts

### Phase C2
- Isolate-shell / multi-LLM planner writing plans into workspace
- First domain agent: file inventory + reclaim suggestions

### Phase C3
- Remote Linux bridge (SSH/agent computer) under same task API
- Paper trading agent (sandbox)

### Phase C4
- Telemetry dashboard + accessibility profile
- End-to-end “set task on phone → runs remote → receipt on phone”

## Non-goals (for now)
- Auto-trading real funds
- Unattended destructive file deletes
- Replacing on-device a11y with cloud-only control

## Safety / consent
Destructive actions (delete media, money moves) require explicit
confirmation channels. Agentic power stops at the confirmation gate.
