#!/data/data/com.termux/files/usr/bin/bash

ROOT="$HOME/broccoli-core"
EVENTS="$ROOT/runtime/events"
STATE="$ROOT/meta/repo_consumer.state"
LOG="$ROOT/reports/repo_consumer.log"

mkdir -p "$EVENTS" "$ROOT/meta" "$ROOT/reports"
touch "$STATE"

while true; do
    for EVENT in "$EVENTS"/repo_*.json; do
        [ -f "$EVENT" ] || { sleep 2; break; }

        grep -qxF "$EVENT" "$STATE" && continue

        echo "$(date '+%F %T') Processing $EVENT" >> "$LOG"

        python3 - <<PY
import json
with open("$EVENT") as f:
    d=json.load(f)
print(
    f"[RepoEvent] branch={d['branch']} "
    f"ahead={d['ahead']} "
    f"changes={d['changes']} "
    f"disk={d['disk_used']}"
)
PY

        echo "$EVENT" >> "$STATE"
    done

    sleep 2
done
