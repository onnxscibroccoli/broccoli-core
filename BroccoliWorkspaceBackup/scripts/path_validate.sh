#!/usr/bin/env bash
set -euo pipefail
EXPECTED="/data/data/com.termux/files/home/broccoli"
ROOT="${BROCCOLI_ROOT:-$EXPECTED}"
if [[ "$ROOT" != "$EXPECTED" ]]; then
  echo "FAIL: BROCCOLI_ROOT=$ROOT (expected $EXPECTED)" >&2
  exit 1
fi
case "$ROOT" in
  /data/data/com.termux/files/home/*) ;;
  *) echo "FAIL: not on internal Termux partition" >&2; exit 1 ;;
esac
echo "PASS: path validation"
