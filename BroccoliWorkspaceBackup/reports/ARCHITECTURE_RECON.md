# Broccoli architecture (device recon)
Generated: 2026-07-07T07:19:18Z

## Binaries
- brocc: `/data/data/com.termux/files/home/brocc`
- rish: `/data/data/com.termux/files/usr/bin/rish`

## Grok packages (rish)
```
package:ai.x.grok
```

## Tools (~/broccoli/tools/)
- **agent_apply_reply.sh** (15 lines, sha c5438a931025) → —
- **agent_consume_iteration.sh** (8 lines, sha d22f327bbc09) → —
- **agent_daemon.sh** (48 lines, sha 4fca785475fa) → rish
- **agent_ensure_running.sh** (16 lines, sha d845392665a8) → —
- **agent_git_vault.sh** (47 lines, sha 2264eeb2f5e5) → —
- **agent_handler.sh** (46 lines, sha cfa792791a99) → —
- **agent_health.sh** (32 lines, sha e1b7b0b6dea7) → —
- **agent_loop.sh** (4 lines, sha db7a19c615b3) → —
- **agent_research_private.sh** (9 lines, sha 237ec53f19ed) → —
- **agent_should_wire.sh** (5 lines, sha 8bd47e2f0c69) → —
- **agent_tick.sh** (23 lines, sha c8e6ff1094ed) → —
- **agent_watch_grok_chat.sh** (33 lines, sha 715ab3dd8972) → rish
- **agent_wire_rish.sh** (11 lines, sha d451053840fa) → rish
- **agent_wrap.sh** (69 lines, sha 6a9ce9bbc762) → brocc
- **apply_inbox_patch.sh** (11 lines, sha 2085078f01a8) → —
- **b_cli.sh** (25 lines, sha c1aa1adc409b) → —
- **brocc_loop.sh** (10 lines, sha 74be7038954e) → —
- **broccoli-daemon.sh** (3 lines, sha 58014df1429f) → —
- **broccoli_agent.py** (135 lines, sha 6c4057b26e35) → brocc, rish, main
- **broccoli_brain.py** (90 lines, sha aa8afbcf0e8d) → brocc, rish, main
- **broccoli_entry.sh** (46 lines, sha e5994c47b6b1) → —
- **broccoli_pull.sh** (33 lines, sha 6dcfd2cdc405) → —
- **broccoli_supervisor.sh** (8 lines, sha 016a72ea0650) → —
- **broccoli_supervisor_loop.sh** (4 lines, sha a723e0ed22ee) → —
- **broccoli_worker.sh** (8 lines, sha d90288bbda66) → —
- **build_repair_wire_prompt.sh** (7 lines, sha 2ae4045d6171) → rish
- **codev_loop.sh** (29 lines, sha 0b2c596e5e8d) → —
- **codevel_boot.sh** (9 lines, sha 82d13e1c78f4) → —
- **codevel_wire.sh** (154 lines, sha d6b7304a1aad) → rish
- **codevel_wire_fast.sh** (148 lines, sha 065ececde0c4) → rish
- **collab_rish_loop.sh** (3 lines, sha 58014df1429f) → —
- **consume_response.sh** (22 lines, sha f8feb827cc4a) → —
- **coordinator_run.sh** (21 lines, sha 4add5475de19) → —
- **debug_send_dump.sh** (6 lines, sha 14134212643e) → —
- **deliver_to_mac.sh** (19 lines, sha eebab4539a93) → —
- **detect_interject.sh** (14 lines, sha c455a583fc16) → —
- **discover_directories.sh** (50 lines, sha d06c25fe881c) → rish
- **dismiss_tos_grok.sh** (54 lines, sha f193689873aa) → rish
- **dump_send_row.sh** (28 lines, sha 6cab86e0f285) → —
- **extract_chat_from_xml.py** (15 lines, sha b84ad2fbc228) → —
- **extract_grok_code.py** (17 lines, sha c7470a9ab27e) → —
- **find_send_tap.py** (13 lines, sha 1512981dc8e8) → rish
- **gap_analyze.py** (149 lines, sha a237804af704) → main
- **gap_enqueue_chat.sh** (10 lines, sha 809a833892c9) → —
- **gap_watch.sh** (10 lines, sha 0797c173eb88) → —
- **go_install.sh** (8 lines, sha 6e3be489845d) → —
- **google_secondary_test.py** (28 lines, sha 5f5441163856) → brocc, main
- **grok_foreground_then.sh** (50 lines, sha c02ab0eb430c) → rish
- **grok_smoke_validate.py** (22 lines, sha 94daa87e5bdf) → main
- **heal_cycle.sh** (10 lines, sha 997962b91cc0) → —
- **heal_research.sh** (13 lines, sha cafb38d92027) → —
- **heal_supervisor.sh** (10 lines, sha 91e538da7b0f) → —
- **heal_wire_fallback.sh** (19 lines, sha 0770386764a7) → —
- **inbox_to_queue.sh** (11 lines, sha 690adfdf6cd7) → —
- **inventory_md_tasks.py** (99 lines, sha 5652b3c9921d) → —
- **inventory_md_tasks.sh** (153 lines, sha a948a7c045a1) → —
- **investigate_system.py** (258 lines, sha fb21640f56cb) → rish, main
- **investigate_system.sh** (19 lines, sha f19750c6c4b4) → —
- **media_housekeeping.sh** (258 lines, sha 53af1c28347e) → —
- **notify_from_dump.sh** (21 lines, sha 90157137bea4) → —
- **notify_persistent_agent.sh** (9 lines, sha 9bc3741b2951) → rish
- **notify_status.sh** (34 lines, sha 459cc5da16f8) → —
- **notify_toast.sh** (5 lines, sha beef6aad54ab) → —
- **notify_watch.sh** (47 lines, sha 939bd7baf0f2) → —
- **open_codevel.sh** (23 lines, sha 669aa063b8dc) → rish
- **parse_grok_ui.py** (23 lines, sha 73b35dbf270e) → —
- **phrase_grok_dump.py** (52 lines, sha f8c02ec9005f) → main
- **prepare_mac_bundle.sh** (27 lines, sha e4b053d7bbff) → —
- **prepare_mac_bundle_redacted.sh** (17 lines, sha 677c90491f9c) → —
- **pull_mac_output.sh** (33 lines, sha 6dcfd2cdc405) → —
- **pull_spec_gemini.sh** (48 lines, sha adad58df56f5) → —
- **push_chat_lines_to_inbox.sh** (29 lines, sha 789947479708) → —
- **read_mission.sh** (19 lines, sha b73292f48f6a) → —
- **redact.sh** (9 lines, sha 95af682a6865) → —
- **reinit_agent.sh** (17 lines, sha e926eeadac09) → —
- **reply_to_next_action.py** (129 lines, sha 9cec6fbab030) → rish, main
- **report_to_queue.sh** (3 lines, sha fc3085623f93) → —
- **run_doc.sh** (22 lines, sha 79f9ff6d614d) → —
- **run_grok_smoke.sh** (20 lines, sha 3c668fdbd4ba) → —
- **safe_wire_message.sh** (5 lines, sha 5f156dca3292) → —
- **setup_vault_interactive.sh** (20 lines, sha aad4b17ba55e) → —
- **setup_wizard.sh** (57 lines, sha 3a34998ce40a) → —
- **show_queue.sh** (19 lines, sha 9ffc4a573606) → —
- **smoke_boot.sh** (24 lines, sha 9d357bbcda05) → rish
- **start_dev_task.sh** (24 lines, sha 8ab603bfd4be) → rish
- **termux_disk_clean.sh** (41 lines, sha f093e1b68f28) → —
- **termux_disk_investigate.sh** (97 lines, sha 048735c51c50) → —
- **toast_user.sh** (9 lines, sha 64eb9faf5a07) → rish
- **ui_dump_chat.py** (60 lines, sha fdc34ebf3a1e) → main
- **ui_dump_loop.py** (134 lines, sha a2f88c2949fb) → brocc, rish, main
- **ui_snapshot_save.sh** (8 lines, sha 1a346a8a6adf) → —
- **ui_state.py** (180 lines, sha 4eb423da5186) → main
- **user_touch_watch.sh** (13 lines, sha b1564589eb81) → —
- **version_manager.sh** (44 lines, sha e37a57363914) → —
- **wire_build_prompt.sh** (8 lines, sha 5c70e8395f88) → —
- **wire_daemon.sh** (38 lines, sha 207cbba55708) → —
- **wire_diag.sh** (9 lines, sha b685b9629ee8) → rish
- **wire_latency_test.sh** (12 lines, sha 8a6cf484f181) → —
- **wire_loop_full.sh** (82 lines, sha 6fd4a17f4d3a) → rish
- **wire_send_fast.sh** (88 lines, sha 3e9801bdb713) → rish
- **wire_send_immediate.sh** (32 lines, sha 1f0bec4fe972) → rish
- **wire_send_ui.sh** (34 lines, sha 1d7f47e3af2a) → rish
- **wire_ui_loop.sh** (49 lines, sha c13c4c825a4a) → —
- **write_sanitized_prompt.sh** (5 lines, sha 24277fbb7895) → —

## Data flow (from code edges only)

- `broccoli_agent.py` → `brocc` (subprocess/cli)
- `broccoli_agent.py` → `rish` (subprocess)
- `broccoli_brain.py` → `brocc` (subprocess/cli)
- `broccoli_brain.py` → `rish` (subprocess)
- `find_send_tap.py` → `rish` (subprocess)
- `google_secondary_test.py` → `brocc` (subprocess/cli)
- `investigate_system.py` → `rish` (subprocess)
- `reply_to_next_action.py` → `rish` (subprocess)
- `ui_dump_loop.py` → `brocc` (subprocess/cli)
- `ui_dump_loop.py` → `rish` (subprocess)
- `agent_daemon.sh` → `rish` (subprocess)
- `agent_watch_grok_chat.sh` → `rish` (subprocess)
- `agent_wire_rish.sh` → `rish` (subprocess)
- `agent_wrap.sh` → `brocc` (subprocess/cli)
- `build_repair_wire_prompt.sh` → `rish` (subprocess)
- `codevel_wire.sh` → `rish` (subprocess)
- `codevel_wire_fast.sh` → `rish` (subprocess)
- `discover_directories.sh` → `rish` (subprocess)
- `dismiss_tos_grok.sh` → `rish` (subprocess)
- `grok_foreground_then.sh` → `rish` (subprocess)
- `notify_persistent_agent.sh` → `rish` (subprocess)
- `open_codevel.sh` → `rish` (subprocess)
- `smoke_boot.sh` → `rish` (subprocess)
- `start_dev_task.sh` → `rish` (subprocess)
- `toast_user.sh` → `rish` (subprocess)
- `wire_diag.sh` → `rish` (subprocess)
- `wire_loop_full.sh` → `rish` (subprocess)
- `wire_send_fast.sh` → `rish` (subprocess)
- `wire_send_immediate.sh` → `rish` (subprocess)
- `wire_send_ui.sh` → `rish` (subprocess)

## Queue
- agent_task.txt bytes: 0

## Running (pgrep)
```
7981 python3 /data/data/com.termux/files/home/broccoli/tools/ui_dump_loop.py
12471 /data/data/com.termux/files/usr/bin/sh -c pgrep -af 'broccoli|brocc|ui_dump|supervisor' 2>/dev/null || true
17676 bash /data/data/com.termux/files/home/broccoli/tools/agent_loop.sh
18129 bash /data/data/com.termux/files/home/broccoli/tools/broccoli_supervisor_loop.sh
18158 bash /data/data/com.termux/files/home/broccoli/tools/wire_send_immediate.sh BROCCOLI ACT_IMMEDIATE: Reply BROCCOLI_LOOP_OK. (1) consume_response minimal patch (2) Gemini queries RV3→V4.1 RWA blockchain in Workspace. Do not wait—execute on wire.
18264 bash /data/data/com.termux/files/home/broccoli/lib/adb_rish.sh am force-stop com.android.chrome
18324 /system/bin/sh /data/data/com.termux/files/usr/bin/rish -c cat /data/local/tmp/broccoli_ui.xml
23783 bash /data/data/com.termux/files/home/broccoli/tools/collab_rish_loop.sh
30648 python3 /data/data/com.termux/files/home/broccoli_bootstrap.py watch
```

## Meta wire_coords.env
```
GROK_PKG=com.ai.x.grok
COLLAB_POLL_SEC=0
TYPING_IDLE_SEC=1
WIRE_COOLDOWN_SEC=0
WIRE_MODE=ask

```

Full JSON: `/data/data/com.termux/files/home/broccoli/reports/ARCHITECTURE_RECON.json`