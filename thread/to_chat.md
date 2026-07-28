## Co-dev: paste INVESTIGATION_REPORT.md to Mac Grok

# Broccoli system investigation
Generated: 2026-07-07T00:06:30-04:00

## Architecture (expected)
- **Broccoli** = Termux executor (queue, sandbox, reports).
- **Grok app** = accessibility only (dump/tap/paste/read).
- **Wire** = daemon + wire_send_ui + ui_dump_rish (invariant: `ai.x.grok` in dump).

## Tree
- Files under `~/broccoli`: **305**
- Extensions: `{'.log': 37, '.txt': 57, '.md': 15, '.py': 46, '.json': 57, '.sh': 66, '.pid': 1, '(noext)': 3, '.jsonl': 4, '.1783317057': 1, '.xml': 7, '.lock': 1, '.consumed': 1, '.flag': 1, '.cur': 1, '.last': 1, '.ts': 2, '.hash': 1, '.conf': 3}`

## Key artifacts
- `INSTRUCTIONS.md`: {'exists': True, 'bytes': 2013, 'mtime': '2026-07-06T23:59:31.044002'}
- `task_box.txt`: {'exists': True, 'bytes': 46, 'mtime': '2026-07-06T23:58:22.752002'}
- `queue/pending.txt`: {'exists': True, 'bytes': 96, 'mtime': '2026-07-06T23:58:27.636002'}
- `queue/done.txt`: {'exists': True, 'bytes': 131, 'mtime': '2026-07-06T23:17:00.580002'}
- `ui/last_ui.xml`: {'exists': True, 'bytes': 16402, 'mtime': '2026-07-06T23:55:44.212002'}
- `reports/wire_send.log`: {'exists': True, 'bytes': 2000, 'mtime': '2026-07-07T00:06:29.416002'}
- `reports/wire_daemon.log`: {'exists': True, 'bytes': 2605, 'mtime': '2026-07-06T23:17:00.552002'}
- `reports/loop_health.jsonl`: {'exists': False}
- `reports/manual_gap.jsonl`: {'exists': True, 'bytes': 4108, 'mtime': '2026-07-06T23:29:52.480002'}
- `thread/to_chat.md`: {'exists': True, 'bytes': 3863, 'mtime': '2026-07-06T23:47:26.720002'}
- `meta/WIRE_STOP`: {'exists': False}

## Last UI dump
```json
{
  "ok": true,
  "bytes": 16398,
  "grok_fg": true,
  "packages": [
    "ai.x.grok"
  ],
  "has_composer": false,
  "send_candidates": [],
  "termux_only": false
}
```

## wire_send.log summary
```json
{
  "lines": 46,
  "counts": {
    "SEND start": 5,
    "send_tap": 10,
    "reply=": 2
  },
  "tail": [
    "2026-07-06T23:17:00-04:00 reply=Start new chat",
    "2026-07-06T23:28:52-04:00 SEND start len=764",
    "2026-07-06T23:29:53-04:00 SEND start len=655",
    "TAP 540 1195",
    "2026-07-06T23:33:54-04:00 send_tap attempt=1",
    "TAP 540 1195",
    "2026-07-06T23:33:55-04:00 send_tap attempt=1",
    "2026-07-06T23:33:57-04:00 SEND len=33",
    "2026-07-06T23:35:54-04:00 dump_bytes=29986",
    "{\"err\": \"no_send\"}",
    "{\"err\": \"no_composer\"}",
    "{\"err\": \"no_composer\"}",
    "2026-07-06T23:47:26-04:00 SEND len=33",
    "2026-07-06T23:49:08-04:00 dump_bytes=8265",
    "{\"err\": \"no_send\"}",
    "2026-07-06T23:54:28-04:00 SEND len=29",
    "2026-07-06T23:54:42-04:00 SEND len=29",
    "2026-07-06T23:59:03-04:00 SEND len=91",
    "2026-07-07T00:05:13-04:00 dump fail",
    "2026-07-07T00:06:29-04:00 dump fail"
  ]
}
```

## Findings (priority order)
1. **[HIGH]** tools/agent_wrap.sh still references Chrome/WEB
   - Fix: route to launch_grok_native.sh only
2. **[HIGH]** lib/grok_send_tap.py still references Chrome/WEB
   - Fix: route to launch_grok_native.sh only
3. **[HIGH]** Grok FG but no send candidates in dump regex
   - Fix: dump send row manually; patch find_send_tap.py with exact resource-id
4. **[MED]** wire_send_ui not hooked to gap_watch
   - Fix: patch gap hooks on fail/success/timeout

## Co-dev window
- State file: `~/broccoli/meta/codev_window.json`
- Session: `20260707_000630`
- Paste **this entire report** (or `reports/INVESTIGATION_REPORT.md`) into Mac Grok chat for full-context patches.
- Re-run: `bash ~/broccoli/tools/investigate_system.sh --live`

## Recommended next patches (ordered)
- route to launch_grok_native.sh only
- route to launch_grok_native.sh only
- dump send row manually; patch find_send_tap.py with exact resource-id
- patch gap hooks on fail/success/timeout
--- DEVICE_OUTPUT 2026-07-07T00:06:31-04:00 ---
===== BROCCOLI DEVICE OUTPUT 2026-07-07T00:06:31-04:00 =====
## DAEMONS
21460 bash /data/data/com.termux/files/home/broccoli/tools/heal_supervisor.sh
27349 bash /data/data/com.termux/files/home/broccoli/tools/agent_daemon.sh

## QUEUE
ASK|Broccoli agent: last reply received. Reply with one short ASK line for next wire step only.

## AGENT_ITERATION
{
  "cycle": 1,
  "last_prompt": "Broccoli agent: last reply received. Reply with one short ASK line for next wire step only.",
  "last_reply": "ITER_OK",
  "last_fp": "",
  "status": "sending",
  "next_prompt": "Broccoli agent: last reply received. Reply with one short ASK line for next wire step only."
}
## INVENTORY (head)
# Broccoli inventory
Generated: 2026-07-07T00:06:26-04:00

## Daemons
- agent_daemon: 27349 bash /data/data/com.termux/files/home/broccoli/tools/agent_daemon.sh
- heal_supervisor: 21460 bash /data/data/com.termux/files/home/broccoli/tools/heal_supervisor.sh

## Runtime
### queue_pending
- bytes: 96
  - ASK|Broccoli agent: last reply received. Reply with one short ASK line for next wire step only.
### task_box
- bytes: 46
  - # Mission: recursive wire until DONE in reply
### agent_iteration
- bytes: 307
  - {
  -   "cycle": 1,
  -   "last_prompt": "Broccoli agent: last reply received. Reply with one short ASK line for next wire s
  -   "last_reply": "ITER_OK",
  -   "last_fp": "",
  -   "status": "sending",
### grok_last
- bytes: 23
  - Start new chat
  - ITER_OK
### to_chat
- bytes: 3863
  - ## Co-dev: paste INVESTIGATION_REPORT.md to Mac Grok
  - 
  - # Broccoli system investigation
  - Generated: 2026-07-06T23:47:26-04:00
  - 
  - ## Architecture (expected)
### investigation
- bytes: 3809
  - # Broccoli system investigation
  - Generated: 2026-07-06T23:47:26-04:00
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

## Markdown (35)

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

### broccoli/reports/INVESTIGATION_REPORT.md [open] todo~10 done~2

### broccoli/reports/INVESTIGATION_REPORT.md [open] todo~10 done~2

### broccoli/research/notes.md [open] todo~1 done~0

### broccoli/research/notes.md [open] todo~1 done~0

### broccoli/spec/BUILD_SPEC.md [mixed] todo~0 done~0

### broccoli/spec/BUILD_SPEC.md [mixed] todo~0 done~0

### broccoli/tasks/current/TASK.md [done] todo~0 done~3

### broccoli/tasks/current/TASK.md [done] todo~0 done~3

### broccoli/thread/conversation.md [mixed] todo~0 done~0

### broccoli/thread/conversation.md [mixed] todo~0 done~0

### broccoli/thread/to_chat.md [open] todo~10 done~2

### broccoli/thread/to_chat.md [open] todo~10 done~2

### broccoli/user/PENDING.md [done] todo~0 done~2

### broccoli/user/PENDING.md [done] todo~0 done~2

### ipwndfu/JAILBREAK-GUIDE.md [mixed] todo~1 done~1

### ipwndfu/README.md [open] todo~1 done~0

## INVESTIGATION (head)
# Broccoli system investigation
Generated: 2026-07-07T00:06:30-04:00

## Architecture (expected)
- **Broccoli** = Termux executor (queue, sandbox, reports).
- **Grok app** = accessibility only (dump/tap/paste/read).
- **Wire** = daemon + wire_send_ui + ui_dump_rish (invariant: `ai.x.grok` in dump).

## Tree
- Files under `~/broccoli`: **305**
- Extensions: `{'.log': 37, '.txt': 57, '.md': 15, '.py': 46, '.json': 57, '.sh': 66, '.pid': 1, '(noext)': 3, '.jsonl': 4, '.1783317057': 1, '.xml': 7, '.lock': 1, '.consumed': 1, '.flag': 1, '.cur': 1, '.last': 1, '.ts': 2, '.hash': 1, '.conf': 3}`

## Key artifacts
- `INSTRUCTIONS.md`: {'exists': True, 'bytes': 2013, 'mtime': '2026-07-06T23:59:31.044002'}
- `task_box.txt`: {'exists': True, 'bytes': 46, 'mtime': '2026-07-06T23:58:22.752002'}
- `queue/pending.txt`: {'exists': True, 'bytes': 96, 'mtime': '2026-07-06T23:58:27.636002'}
- `queue/done.txt`: {'exists': True, 'bytes': 131, 'mtime': '2026-07-06T23:17:00.580002'}
- `ui/last_ui.xml`: {'exists': True, 'bytes': 16402, 'mtime': '2026-07-06T23:55:44.212002'}
- `reports/wire_send.log`: {'exists': True, 'bytes': 2000, 'mtime': '2026-07-07T00:06:29.416002'}
- `reports/wire_daemon.log`: {'exists': True, 'bytes': 2605, 'mtime': '2026-07-06T23:17:00.552002'}
- `reports/loop_health.jsonl`: {'exists': False}
- `reports/manual_gap.jsonl`: {'exists': True, 'bytes': 4108, 'mtime': '2026-07-06T23:29:52.480002'}
- `thread/to_chat.md`: {'exists': True, 'bytes': 3863, 'mtime': '2026-07-06T23:47:26.720002'}
- `meta/WIRE_STOP`: {'exists': False}

## Last UI dump
```json
{
  "ok": true,
  "bytes": 16398,
  "grok_fg": true,
  "packages": [
    "ai.x.grok"
  ],
  "has_composer": false,
  "send_candidates": [],
  "termux_only": false
}
```

## wire_send.log summary
```json
{
  "lines": 46,
  "counts": {
    "SEND start": 5,
    "send_tap": 10,
    "reply=": 2
  },
  "tail": [
    "2026-07-06T23:17:00-04:00 reply=Start new chat",
    "2026-07-06T23:28:52-04:00 SEND start len=764",
    "2026-07-06T23:29:53-04:00 SEND start len=655",
    "TAP 540 1195",
    "2026-07-06T23:33:54-04:00 send_tap attempt=1",
    "TAP 540 1195",
    "2026-07-06T23:33:55-04:00 send_tap attempt=1",
    "2026-07-06T23:33:57-04:00 SEND len=33",
    "2026-07-06T23:35:54-04:00 dump_bytes=29986",
    "{\"err\": \"no_send\"}",
    "{\"err\": \"no_composer\"}",
    "{\"err\": \"no_composer\"}",
    "2026-07-06T23:47:26-04:00 SEND len=33",
    "2026-07-06T23:49:08-04:00 dump_bytes=8265",
    "{\"err\": \"no_send\"}",
    "2026-07-06T23:54:28-04:00 SEND len=29",
    "2026-07-06T23:54:42-04:00 SEND len=29",
    "2026-07-06T23:59:03-04:00 SEND len=91",
    "2026-07-07T00:05:13-04:00 dump fail",
    "2026-07-07T00:06:29-04:00 dump fail"
  ]
}
```

## Findings (priority order)
1. **[HIGH]** tools/agent_wrap.sh still references Chrome/WEB
   - Fix: route to launch_grok_native.sh only
2. **[HIGH]** lib/grok_send_tap.py still references Chrome/WEB
   - Fix: route to launch_grok_native.sh only
3. **[HIGH]** Grok FG but no send candidates in dump regex

## WIRE_LOG (tail)
TAP 540 1195
2026-07-06T23:33:55-04:00 send_tap attempt=1
2026-07-06T23:33:57-04:00 SEND len=33
2026-07-06T23:35:54-04:00 dump_bytes=29986
{"err": "no_send"}
{"err": "no_composer"}
{"err": "no_composer"}
2026-07-06T23:47:26-04:00 SEND len=33
2026-07-06T23:49:08-04:00 dump_bytes=8265
{"err": "no_send"}
2026-07-06T23:54:28-04:00 SEND len=29
2026-07-06T23:54:42-04:00 SEND len=29
2026-07-06T23:59:03-04:00 SEND len=91
2026-07-07T00:05:13-04:00 dump fail
2026-07-07T00:06:29-04:00 dump fail
===== END =====
---

--- DEVICE_OUTPUT 2026-07-07T00:12:39-04:00 ---
===== BROCCOLI DEVICE OUTPUT 2026-07-07T00:12:39-04:00 =====
## DAEMONS
21460 bash /data/data/com.termux/files/home/broccoli/tools/heal_supervisor.sh
27349 bash /data/data/com.termux/files/home/broccoli/tools/agent_daemon.sh

## QUEUE
ASK|Wire probe: reply one word WIRE_OK

## AGENT_ITERATION
{
  "cycle": 3,
  "last_prompt": "ITER_OK",
  "last_reply": "ITER_OK",
  "last_fp": "",
  "status": "idle",
  "next_prompt": "Wire probe: reply one word WIRE_OK"
}
## INVENTORY (head)
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


## INVESTIGATION (head)
# Broccoli system investigation
Generated: 2026-07-07T00:06:30-04:00

## Architecture (expected)
- **Broccoli** = Termux executor (queue, sandbox, reports).
- **Grok app** = accessibility only (dump/tap/paste/read).
- **Wire** = daemon + wire_send_ui + ui_dump_rish (invariant: `ai.x.grok` in dump).

## Tree
- Files under `~/broccoli`: **305**
- Extensions: `{'.log': 37, '.txt': 57, '.md': 15, '.py': 46, '.json': 57, '.sh': 66, '.pid': 1, '(noext)': 3, '.jsonl': 4, '.1783317057': 1, '.xml': 7, '.lock': 1, '.consumed': 1, '.flag': 1, '.cur': 1, '.last': 1, '.ts': 2, '.hash': 1, '.conf': 3}`

## Key artifacts
- `INSTRUCTIONS.md`: {'exists': True, 'bytes': 2013, 'mtime': '2026-07-06T23:59:31.044002'}
- `task_box.txt`: {'exists': True, 'bytes': 46, 'mtime': '2026-07-06T23:58:22.752002'}
- `queue/pending.txt`: {'exists': True, 'bytes': 96, 'mtime': '2026-07-06T23:58:27.636002'}
- `queue/done.txt`: {'exists': True, 'bytes': 131, 'mtime': '2026-07-06T23:17:00.580002'}
- `ui/last_ui.xml`: {'exists': True, 'bytes': 16402, 'mtime': '2026-07-06T23:55:44.212002'}
- `reports/wire_send.log`: {'exists': True, 'bytes': 2000, 'mtime': '2026-07-07T00:06:29.416002'}
- `reports/wire_daemon.log`: {'exists': True, 'bytes': 2605, 'mtime': '2026-07-06T23:17:00.552002'}
- `reports/loop_health.jsonl`: {'exists': False}
- `reports/manual_gap.jsonl`: {'exists': True, 'bytes': 4108, 'mtime': '2026-07-06T23:29:52.480002'}
- `thread/to_chat.md`: {'exists': True, 'bytes': 3863, 'mtime': '2026-07-06T23:47:26.720002'}
- `meta/WIRE_STOP`: {'exists': False}

## Last UI dump
```json
{
  "ok": true,
  "bytes": 16398,
  "grok_fg": true,
  "packages": [
    "ai.x.grok"
  ],
  "has_composer": false,
  "send_candidates": [],
  "termux_only": false
}
```

## wire_send.log summary
```json
{
  "lines": 46,
  "counts": {
    "SEND start": 5,
    "send_tap": 10,
    "reply=": 2
  },
  "tail": [
    "2026-07-06T23:17:00-04:00 reply=Start new chat",
    "2026-07-06T23:28:52-04:00 SEND start len=764",
    "2026-07-06T23:29:53-04:00 SEND start len=655",
    "TAP 540 1195",
    "2026-07-06T23:33:54-04:00 send_tap attempt=1",
    "TAP 540 1195",
    "2026-07-06T23:33:55-04:00 send_tap attempt=1",
    "2026-07-06T23:33:57-04:00 SEND len=33",
    "2026-07-06T23:35:54-04:00 dump_bytes=29986",
    "{\"err\": \"no_send\"}",
    "{\"err\": \"no_composer\"}",
    "{\"err\": \"no_composer\"}",
    "2026-07-06T23:47:26-04:00 SEND len=33",
    "2026-07-06T23:49:08-04:00 dump_bytes=8265",
    "{\"err\": \"no_send\"}",
    "2026-07-06T23:54:28-04:00 SEND len=29",
    "2026-07-06T23:54:42-04:00 SEND len=29",
    "2026-07-06T23:59:03-04:00 SEND len=91",
    "2026-07-07T00:05:13-04:00 dump fail",
    "2026-07-07T00:06:29-04:00 dump fail"
  ]
}
```

## Findings (priority order)
1. **[HIGH]** tools/agent_wrap.sh still references Chrome/WEB
   - Fix: route to launch_grok_native.sh only
2. **[HIGH]** lib/grok_send_tap.py still references Chrome/WEB
   - Fix: route to launch_grok_native.sh only
3. **[HIGH]** Grok FG but no send candidates in dump regex

## WIRE_LOG (tail)
2026-07-06T23:33:57-04:00 SEND len=33
2026-07-06T23:35:54-04:00 dump_bytes=29986
{"err": "no_send"}
{"err": "no_composer"}
{"err": "no_composer"}
2026-07-06T23:47:26-04:00 SEND len=33
2026-07-06T23:49:08-04:00 dump_bytes=8265
{"err": "no_send"}
2026-07-06T23:54:28-04:00 SEND len=29
2026-07-06T23:54:42-04:00 SEND len=29
2026-07-06T23:59:03-04:00 SEND len=91
2026-07-07T00:05:13-04:00 dump fail
2026-07-07T00:06:29-04:00 dump fail
2026-07-07T00:09:10-04:00 dump fail
2026-07-07T00:10:10-04:00 SEND len=34
===== END =====
---
