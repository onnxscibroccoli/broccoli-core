#!/data/data/com.termux/files/usr/bin/bash
# One-shot status notification: running / idle / wire / last action.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
STATE="$HOME/broccoli/meta/agent_state.json"
MODE="idle"
DETAIL=""

if pgrep -f agent_daemon.sh >/dev/null 2>&1; then
  MODE="agent ON"
elif pgrep -f wire_daemon.sh >/dev/null 2>&1; then
  MODE="wire ON"
else
  MODE="daemons OFF"
fi

if [ -f "$STATE" ]; then
  DETAIL="$(python3 -c "import json; d=json.load(open('$STATE')); print(d.get('status','?'), 'cycle', d.get('cycle','?'), d.get('last_action','')[:40])" 2>/dev/null || true)"
fi

LAST="$(tail -1 "$HOME/broccoli/reports/wire_send.log" 2>/dev/null | head -c 120 || true)"
Q="$(head -1 "$HOME/broccoli/queue/pending.txt" 2>/dev/null | sed 's/^ASK|//' | head -c 80 || true)"

BODY="${MODE}"
[ -n "$DETAIL" ] && BODY="$BODY · $DETAIL"
[ -n "$Q" ] && BODY="$BODY · queue: $Q"
[ -n "$LAST" ] && BODY="$BODY · $LAST"

# Ongoing while agent running
ONG=0
pgrep -f agent_daemon.sh >/dev/null 2>&1 && ONG=1

bash "$HOME/broccoli/lib/notify.sh" "Broccoli · status" "$BODY" "$ONG"
