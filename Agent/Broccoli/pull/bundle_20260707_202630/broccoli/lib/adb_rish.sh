#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
bash "$HOME/aim_rish_ensure.sh" 2>/dev/null || true
printf '%s\n' "$@" | rish
