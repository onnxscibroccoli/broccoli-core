# Broccoli (on-device)

- **Broccoli** = Termux executor: queue, scripts, `sandbox/from_grok`, reports.
- **Grok app** = accessibility layer only: UI dump (rish), tap composer/send, read replies. Not "the product."
- **Wire**: `wire_daemon.sh` after **≥3s user idle** → `wire_send_ui.sh` → dump until reply changes → `extract_grok_code.py` → run `block_*.sh`.
- **No Chrome** for wire. Use `launch_grok_native.sh` + `ui_dump_rish.sh` (must see `package="ai.x.grok"` in dump).
- **User does not paste chat into Termux** for the loop; script owns send/receive.
- **Stop**: `touch ~/broccoli/meta/WIRE_STOP && pkill -f wire_daemon.sh`

## Co-dev window (persistent)
1. `bash ~/broccoli/tools/investigate_system.sh --live` — full audit + live Grok dump probe.
2. Paste `~/broccoli/reports/INVESTIGATION_REPORT.md` to Mac Grok (full context, not tiny steps).
3. Apply returned patch blocks on device; re-run investigate until critical findings = 0.
4. Optional background: `nohup bash ~/broccoli/tools/codev_loop.sh 180 >> ~/broccoli/reports/codev_loop.log 2>&1 &`
5. State: `~/broccoli/meta/codev_window.json`

## Recursive agent (no manual paste-back)
- **Reasoning surface:** native Grok app (accessibility), not Mac chat.
- **Loop:** `agent_tick.sh` = investigate → report_to_queue → wire_send_ui → apply blocks → update agent_state.json.
- **Persistent:** `nohup bash ~/broccoli/tools/agent_daemon.sh &`
- **Stop:** `touch ~/broccoli/meta/AGENT_STOP`
- Mac/browser chat is optional; agent must close loop on phone alone.

## Voice / STT (user)
- User speech-to-text and voice in Grok stay fully available.
- Wire automation only: do not **tap** mic/voice/send-adjacent controls when auto-sending.
- Never disable voice, STT, or microphone for the user.

## Agent must not stop after install
- Never end install with `pkill agent_daemon` or `touch AGENT_STOP`.
- Always finish with: `bash ~/broccoli/tools/go_install.sh`
- Daemon waits: queue OR `agent_watch_grok_chat.sh` (rish UI new reply).
