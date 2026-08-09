#!/data/data/com.termux/files/usr/bin/bash

ROOT="$HOME/broccoli-core"

while true; do
    for f in "$ROOT/runtime/events"/repo_*.json; do
        [ -e "$f" ] || { sleep 2; continue; }

        cp "$f" "$ROOT/runtime/event_bus/inbox/" 2>/dev/null
        rm -f "$f"
    done

    sleep 2
done
