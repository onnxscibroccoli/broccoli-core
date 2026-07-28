#!/usr/bin/env bash
set -euo pipefail
ROOT="${BROCCOLI_ROOT:-/data/data/com.termux/files/home/broccoli}"
COLD="${BROCCOLI_COLD:-$ROOT/cold_storage}"
mkdir -p "$COLD"
# Move heavy/legacy dirs if present at old locations
for legacy in "$HOME/old_broccoli" "$HOME/broccoli_data" "$HOME/repos"; do
  if [[ -d "$legacy" && "$legacy" != "$ROOT" ]]; then
    base=$(basename "$legacy")
    if [[ ! -e "$COLD/$base" ]]; then
      mv "$legacy" "$COLD/$base" && echo "Moved $legacy -> $COLD/$base"
    fi
  fi
done
export BROCCOLI_ROOT="$ROOT"
echo "Healer done. Active root: $ROOT"
