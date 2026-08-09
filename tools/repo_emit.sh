#!/data/data/com.termux/files/usr/bin/bash

ROOT="$HOME/broccoli-core"
EVENTS="$ROOT/runtime/events"
mkdir -p "$EVENTS"

while true; do
    [ -f "$ROOT/meta/repo_governor.json" ] || { sleep 5; continue; }

    TS=$(date +%s)

    cp "$ROOT/meta/repo_governor.json" \
       "$EVENTS/repo_${TS}.json"

    sleep 5
done
