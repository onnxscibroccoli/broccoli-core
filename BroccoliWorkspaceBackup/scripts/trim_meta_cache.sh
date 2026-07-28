#!/usr/bin/env bash
set -euo pipefail
ROOT="${BROCCOLI_ROOT:-$HOME/broccoli}"
APPLY=0; [[ "${1:-}" == "--apply" ]] && APPLY=1
CACHE="$ROOT/meta/cache"; [[ -d "$CACHE" ]] || exit 0
cd "$CACHE"
keep(){ local p="$1" n; n=$(ls -t $p 2>/dev/null|head -1||true); [[ -n "$n" ]]||return 0
  for f in $p; do [[ "$f"=="$n" ]]&&continue
    [[ $APPLY -eq 1 ]]&&rm -f -- "$f"&&echo DEL "$f"||echo WOULD_DEL "$f"; done; }
keep FS_DISCOVERY.md_*; keep discover_directories.sh_*; keep notify_toast.sh_*
keep deliver_to_mac.sh_*; keep notify.sh_*; keep user_task_wait.py_*; keep toast.py_*'
