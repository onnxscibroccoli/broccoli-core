#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

LOCK_FILE="$HOME/.clipboard_command_loop.lock"
LOG_FILE="$HOME/clipboard_command_loop.log"

if [ -e "$LOCK_FILE" ]; then
    exit 1
fi

echo $$ > "$LOCK_FILE"

cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT INT TERM

LAST_HASH=""

echo "[Clipboard Agent] Started PID $$" >> "$LOG_FILE"

while true; do

    CLIP="$(termux-clipboard-get 2>/dev/null || true)"

    # Ignore empty clipboard
    [ -z "$CLIP" ] && sleep 2 && continue

    # Ignore our own results
    printf "%s" "$CLIP" | grep -q "^\[Clipboard Agent Result\]" && {
        sleep 2
        continue
    }

    HASH="$(printf "%s" "$CLIP" | sha256sum | cut -d' ' -f1)"

    [ "$HASH" = "$LAST_HASH" ] && {
        sleep 2
        continue
    }

    LAST_HASH="$HASH"

    {
        echo
        echo "[$(date '+%F %T')] Command:"
        echo "$CLIP"
    } >> "$LOG_FILE"

    OUTPUT="$(bash -lc "$CLIP" 2>&1)"

    RESULT="[Clipboard Agent Result]
Time: $(date '+%F %T')

Command:
$CLIP

Output:
$OUTPUT"

    printf "%s" "$RESULT" | termux-clipboard-set

    sleep 2
done
