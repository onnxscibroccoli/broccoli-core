# Broccoli inventory
Generated: 2026-07-07T00:12:39-04:00

## Daemons
- agent_daemon: 27349 bash /data/data/com.termux/files/home/broccoli/tools/agent_daemon.sh
- heal_supervisor: 21460 bash /data/data/com.termux/files/home/broccoli/tools/heal_supervisor.sh

## Runtime
### queue_pending
- bytes: 39
  - ASK|Wire probe: reply one word WIRE_OK
### task_box
- bytes: 196
  - # Mission: recursive wire until DONE in reply
  - Run inventory and deliver device output to Mac co-dev
  - Wire probe: reply one word WIRE_OK
  - Fix INVESTIGATION critical: Grok FG dump only (no Termux FG)
### agent_iteration
- bytes: 163
  - {
  -   "cycle": 3,
  -   "last_prompt": "ITER_OK",
  -   "last_reply": "ITER_OK",
  -   "last_fp": "",
  -   "status": "idle",
### grok_last
- bytes: 23
  - Start new chat
  - ITER_OK
### to_chat
- bytes: 11610
  - ## Co-dev: paste INVESTIGATION_REPORT.md to Mac Grok
  - 
  - # Broccoli system investigation
  - Generated: 2026-07-07T00:06:30-04:00
  - 
  - ## Architecture (expected)
### investigation
- bytes: 3718
  - # Broccoli system investigation
  - Generated: 2026-07-07T00:06:30-04:00
  - 
  - ## Architecture (expected)
  - - **Broccoli** = Termux executor (queue, sandbox, reports).
  - - **Grok app** = accessibility only (dump/tap/paste/read).
### instructions
- bytes: 2013
  - # Broccoli (on-device)
  - 
  - - **Broccoli** = Termux executor: queue, scripts, `sandbox/from_grok`, reports.
  - - **Grok app** = accessibility layer only: UI dump (rish), tap composer/send, read replies. Not "the
  - - **Wire**: `wire_daemon.sh` after **≥3s user idle** → `wire_send_ui.sh` → dump until reply changes 
  - - **No Chrome** for wire. Use `launch_grok_native.sh` + `ui_dump_rish.sh` (must see `package="ai.x.g

## Markdown (37)

### AndroSH/CODE_OF_CONDUCT.md [mixed] todo~0 done~0

### AndroSH/README.md [done] todo~1 done~6

### WiFuX/CHANGELOG.md [open] todo~2 done~0

### WiFuX/README.md [open] todo~2 done~1

### broccoli/HANDOFF.md [done] todo~0 done~1

### broccoli/HANDOFF.md [done] todo~0 done~1

### broccoli/INSTRUCTIONS.md [open] todo~1 done~0

### broccoli/INSTRUCTIONS.md [open] todo~1 done~0

### broccoli/PROJECT.md [mixed] todo~0 done~0

### broccoli/PROJECT.md [mixed] todo~0 done~0

### broccoli/TASK_LIST.md [mixed] todo~0 done~0

### broccoli/TASK_LIST.md [mixed] todo~0 done~0

### broccoli/docs/RUTO_BRIDGE.md [mixed] todo~0 done~0

### broccoli/docs/RUTO_BRIDGE.md [mixed] todo~0 done~0

### broccoli/meta/README.md [mixed] todo~0 done~0

### broccoli/meta/README.md [mixed] todo~0 done~0

### broccoli/meta/current_task.md [done] todo~2 done~7

### broccoli/meta/current_task.md [done] todo~2 done~7

### broccoli/reports/INVENTORY_REPORT.md [done] todo~41 done~54

### broccoli/reports/INVENTORY_REPORT.md [done] todo~41 done~54

### broccoli/reports/INVESTIGATION_REPORT.md [open] todo~14 done~1

### broccoli/reports/INVESTIGATION_REPORT.md [open] todo~14 done~1

### broccoli/research/notes.md [open] todo~1 done~0

### broccoli/research/notes.md [open] todo~1 done~0

### broccoli/spec/BUILD_SPEC.md [mixed] todo~0 done~0

### broccoli/spec/BUILD_SPEC.md [mixed] todo~0 done~0

### broccoli/tasks/current/TASK.md [done] todo~0 done~3

### broccoli/tasks/current/TASK.md [done] todo~0 done~3

### broccoli/thread/conversation.md [mixed] todo~0 done~0

### broccoli/thread/conversation.md [mixed] todo~0 done~0

### broccoli/thread/to_chat.md [open] todo~58 done~49

### broccoli/thread/to_chat.md [open] todo~58 done~49

### broccoli/user/PENDING.md [done] todo~0 done~2

### broccoli/user/PENDING.md [done] todo~0 done~2

### ipwndfu/JAILBREAK-GUIDE.md [mixed] todo~1 done~1

### ipwndfu/README.md [open] todo~1 done~0

### project_mythara/README.md [open] todo~6 done~2
  - - [ ] **Local-model module** — Gemma Nano via MediaPipe LLM inference; first-class swap from MiniMax. (PRs wanted.)
  - - [ ] **Onboarding tutorial** — gesture-by-gesture intro for the rose-amulet, spine, PTT, alerts.
  - - [ ] **Plugin SDK** — third-party tools as Android Services discovered at runtime; Mythara loads them with permission gates.
  - - [ ] **Watch face + complications** — the rose lives on your Wear OS face and pulses with your HR.
