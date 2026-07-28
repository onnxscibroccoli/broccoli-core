#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")"
if [ "${BROCC_NO_SELF_MUTATE:-1}" = "1" ]; then
  echo "quarry_run: skipped (BROCC_NO_SELF_MUTATE=1)"
  exit 0
fi
exec python3 quarry_iter.py "$@"
