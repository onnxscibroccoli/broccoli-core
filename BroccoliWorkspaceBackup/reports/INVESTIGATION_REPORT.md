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