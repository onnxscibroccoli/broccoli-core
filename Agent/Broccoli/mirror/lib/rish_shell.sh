#!/data/data/com.termux/files/usr/bin/bash
# Rish: one shell line per docs — stdin to rish, no bogus am intents.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LINE="${*:-}"
if [ -z "$LINE" ] && [ ! -t 0 ]; then LINE="$(cat)"; fi
printf '%s\n' "$LINE" | rish
