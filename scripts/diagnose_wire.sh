#!/usr/bin/env bash
set -euo pipefail
R="${BROCCOLI_ROOT:-$HOME/broccoli}"; cd "$R"
echo "=== wire ==="; ls -la state/infinite.lock meta/inbox/to_mac meta/inbox/from_mac 2>/dev/null
cat meta/inbox/to_mac/loop_packet.json 2>/dev/null; echo
wc -c mac/inbox.jsonl mac/processed.jsonl ui/loop_*.txt 2>/dev/null
ls -la inbox/grok_reply.txt ui/latest.xml thread/grok_last.txt 2>/dev/null
