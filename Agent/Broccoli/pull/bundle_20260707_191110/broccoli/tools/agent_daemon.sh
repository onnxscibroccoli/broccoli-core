#!/data/data/com.termux/files/usr/bin/bash
# Persistent: wait for queue OR new Grok chat in UI dump. Wire fail does NOT stop daemon.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/agent_daemon.log"
STOP="$HOME/broccoli/meta/AGENT_STOP"
COOLDOWN="${AGENT_COOLDOWN_SEC:-25}"
IDLE_POLL="${AGENT_CHAT_POLL_SEC:-8}"

log(){ echo "$(date -Iseconds) $*" >> "$LOG"; }

idle_ok(){
  S="$(bash "$HOME/broccoli/lib/user_idle_sec.sh" 2>/dev/null || echo 99)"
  [ "${S:-0}" -ge 3 ]
}

log "agent_daemon start (only AGENT_STOP ends this)"

while [ ! -f "$STOP" ]; do
  bash "$HOME/broccoli/tools/notify_persistent_agent.sh" 2>/dev/null || true

  Q="$(head -1 "$HOME/broccoli/queue/pending.txt" 2>/dev/null | sed 's/^ASK|//' | tr -d '\n' || true)"

  if [ -n "$Q" ]; then
    if idle_ok; then
      log "tick queue len=${#Q}"
      if bash "$HOME/broccoli/tools/agent_tick.sh" >>"$LOG" 2>&1; then
        log "tick ok"
      else
        log "tick wire_fail — daemon continues"
      fi
      sleep "$COOLDOWN"
    else
      sleep 1
    fi
  else
    # No queue: watch Grok chat via rish dump (next message in any AI window)
    if idle_ok; then
      bash "$HOME/broccoli/tools/agent_watch_grok_chat.sh" >>"$LOG" 2>&1 || true
      sleep "$IDLE_POLL"
    else
      sleep 1
    fi
  fi
done

log "agent_daemon exit (AGENT_STOP)"
