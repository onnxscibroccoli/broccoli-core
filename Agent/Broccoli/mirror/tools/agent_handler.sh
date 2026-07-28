#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
B="$HOME/broccoli"
STOP="$B/meta/AGENT_STOP"
LOG="$B/reports/agent_handler.log"
COOLDOWN="${AGENT_COOLDOWN_SEC:-15}"
idle(){ S="$(bash "$B/lib/user_idle_sec.sh" 2>/dev/null || echo 99)"; [ "${S:-0}" -ge 3 ]; }

bash "$B/tools/notify_toast.sh" "Handler" "ON" broccoli_handler
echo "$(date -Iseconds) handler start" >> "$LOG"

# Default mission pipeline (no user): git vault → wire smoke → research
[ -s "$B/queue/missions.txt" ] || cat > "$B/queue/missions.txt" <<'MQ'
GIT_SYNC
WIRE|wire_ok
RESEARCH
MQ

while [ ! -f "$STOP" ]; do
  bash "$B/tools/notify_persistent_agent.sh" 2>/dev/null || true
  if ! idle; then sleep 2; continue; fi
  LINE="$(head -1 "$B/queue/missions.txt" 2>/dev/null || true)"
  if [ -z "$LINE" ]; then
    bash "$B/tools/agent_research_private.sh" >>"$LOG" 2>&1 || true
    bash "$B/tools/agent_git_vault.sh" >>"$LOG" 2>&1 || true
    sleep 60
    continue
  fi
  case "$LINE" in
    GIT_SYNC|GIT*)
      bash "$B/tools/agent_git_vault.sh" >>"$LOG" 2>&1 || true ;;
    WIRE|*)
      TID="${LINE#WIRE|}"
      bash "$B/tools/agent_wire_rish.sh" "$TID" >>"$LOG" 2>&1 || true ;;
    RESEARCH*)
      bash "$B/tools/agent_research_private.sh" >>"$LOG" 2>&1 || true ;;
    *)
      bash "$B/tools/agent_wire_rish.sh" wire_ok >>"$LOG" 2>&1 || true ;;
  esac
  sed -i '1d' "$B/queue/missions.txt" 2>/dev/null || true
  bash "$B/tools/prepare_mac_bundle_redacted.sh"
  sleep "$COOLDOWN"
done
bash "$B/tools/notify_toast.sh" "Handler" "STOPPED" broccoli_handler
