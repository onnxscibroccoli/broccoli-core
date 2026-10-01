#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail

RISH_ENV_FILE="${BROCCOLI_RISH_ENV:-$HOME/.config/broccoli/rish/android-runtime.env}"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
CMD="$*"
[ -n "$CMD" ] || { echo "usage: rish_run.sh <shell-cmd>" >&2; exit 2; }

if [ -n "${BOOTCLASSPATH:-}" ]; then
  rish -c "$CMD"
  exit $?
fi

if [ ! -r "$RISH_ENV_FILE" ]; then
  echo "RISH_ENV_MISSING: $RISH_ENV_FILE" >&2
  exit 78
fi

exec env -i \
  HOME="$HOME" \
  PWD="$PWD" \
  PREFIX="${PREFIX:-/data/data/com.termux/files/usr}" \
  TMPDIR="${TMPDIR:-/data/data/com.termux/files/usr/tmp}" \
  PATH="${PATH:-/data/data/com.termux/files/usr/bin:/system/bin}" \
  SHELL="${SHELL:-/data/data/com.termux/files/usr/bin/bash}" \
  TERM="${TERM:-xterm-256color}" \
  RISH_APPLICATION_ID="$RISH_APPLICATION_ID" \
  RISH_PRESERVE_ENV="${RISH_PRESERVE_ENV:-0}" \
  /data/data/com.termux/files/usr/bin/bash -c 'while IFS= read -r line; do
  case "$line" in
    BOOTCLASSPATH=*|DEX2OATBOOTCLASSPATH=*|SYSTEMSERVERCLASSPATH=*|ANDROID_*=*|LD_LIBRARY_PATH=*|LD_PRELOAD=*|CLASSPATH=*|EXTERNAL_STORAGE=*)
      export "$line"
      ;;
  esac
done < "$1"
exec rish -c "$2"' _ "$RISH_ENV_FILE" "$CMD"
