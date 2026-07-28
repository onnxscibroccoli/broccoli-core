#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
bash "$B/tools/wire_diag.sh" > "$B/reports/WIRE_DIAG.json" 2>&1 || true
printf '%s\n' "BROCCOLI: diagnose live wire. Reply WIRE_REPAIR_OK + fixes. Use rish -c for input/am. DIAG:" "$(cat "$B/reports/WIRE_DIAG.json" 2>/dev/null)" | head -c 3500 > "$B/queue/agent_task.txt"
cp "$B/queue/agent_task.txt" "$B/reports/SANITIZED_PROMPT.md"
echo repair_queued
