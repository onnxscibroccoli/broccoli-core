#!/data/data/com.termux/files/usr/bin/bash
RAW="${1:-}"
[ -z "$RAW" ] && RAW="$(cat)"
printf '%s' "$RAW" | sed 's/BROCCOLI_AGENT:.*//g; s/## Findings.*//g' | tr -d '\n' | head -c 160
