#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail

RISH_ENV_FILE="${BROCCOLI_RISH_ENV:-$HOME/.config/broccoli/rish/android-runtime.env}"
RISH_BIN="${BROCCOLI_RISH_BIN:-/data/data/com.termux/files/usr/bin/rish}"
RISH_APP="${RISH_APPLICATION_ID:-com.termux}"
CMD="$*"

[ -n "$CMD" ] || {
  echo "usage: rish_run.sh <shell-cmd>" >&2
  exit 2
}

[ -x "$RISH_BIN" ] || {
  echo "RISH_BIN_MISSING: $RISH_BIN" >&2
  exit 79
}

# Background callers may not inherit the Android runtime variables that an interactive Termux shell receives.
# Prefer the captured runtime environment whenever it exists.
if [ -r "$RISH_ENV_FILE" ]; then
  exec env -i \
    HOME="$HOME" \
    PWD="$PWD" \
    PREFIX="${PREFIX:-/data/data/com.termux/files/usr}" \
    TMPDIR="${TMPDIR:-/data/data/com.termux/files/usr/tmp}" \
    PATH="${PATH:-/data/data/com.termux/files/usr/bin:/system/bin}" \
    SHELL="${SHELL:-/data/data/com.termux/files/usr/bin/bash}" \
    TERM="${TERM:-xterm-256color}" \
    RISH_APPLICATION_ID="$RISH_APP" \
    RISH_PRESERVE_ENV="${RISH_PRESERVE_ENV:-0}" \
    /data/data/com.termux/files/usr/bin/bash -c '
      while IFS= read -r line; do
        case "$line" in
          BOOTCLASSPATH=*|DEX2OATBOOTCLASSPATH=*|SYSTEMSERVERCLASSPATH=*|ANDROID_*=*|LD_LIBRARY_PATH=*|LD_PRELOAD=*|CLASSPATH=*|EXTERNAL_STORAGE=*)
            export "$line"
            ;;
        esac
      done < "$1"
      exec "$3" -c "$2"
    ' _ "$RISH_ENV_FILE" "$CMD" "$RISH_BIN"
  exit $?
fi

if [ -n "${BOOTCLASSPATH:-}" ]; then
  exec "$RISH_BIN" -c "$CMD"
  exit $?
fi

echo "RISH_ENV_MISSING: $RISH_ENV_FILE" >&2
echo "Set BROCCOLI_RISH_ENV to a captured Android runtime environment." >&2
exit 78
