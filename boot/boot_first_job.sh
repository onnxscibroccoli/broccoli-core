#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$(pwd)/bin:$PATH"
export BROCC_NO_SELF_MUTATE=1
export RISH_ENABLED=1
[ "${SMOKE_ON_BOOT:-1}" = "1" ] && brocc smoke "${BOOT_MSG:-smoke test}" || true
