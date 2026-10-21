#!/usr/bin/env bash
# Keep XFCE's VNC framebuffer usable when clients or stale resize requests
# collapse it to a phone-sized resolution. Runs only inside the desktop session.
set -u
export DISPLAY="${DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
BASE="$HOME/.omnikali"
mkdir -p "$BASE"
LOG="$BASE/display-watchdog.log"
exec 9>"$BASE/display-watchdog.lock"
flock -n 9 || exit 0
TARGET="${OMNIKALI_VNC_MODE:-1360x768}"
printf '%s started; target=%s display=%s\n' "$(date -Is)" "$TARGET" "$DISPLAY" >>"$LOG"
while true; do
  if xrandr --query >/dev/null 2>&1; then
    if ! xrandr --query 2>/dev/null | awk -v mode="$TARGET" '$1==mode {found=1} END {exit !found}'; then
      TARGET="1280x720"
    fi
    if ! xrandr --current 2>/dev/null | grep -q "current ${TARGET%x*} x ${TARGET#*x}"; then
      if xrandr --output VNC-0 --mode "$TARGET" >>"$LOG" 2>&1; then
        printf '%s restored framebuffer to %s\n' "$(date -Is)" "$TARGET" >>"$LOG"
      elif xrandr --output VNC-0 --mode 1280x720 >>"$LOG" 2>&1; then
        TARGET="1280x720"
        printf '%s fallback framebuffer to %s\n' "$(date -Is)" "$TARGET" >>"$LOG"
      else
        printf '%s ERROR unable to restore display mode\n' "$(date -Is)" >>"$LOG"
      fi
    fi
    xset s off >/dev/null 2>&1 || true
    xset -dpms >/dev/null 2>&1 || true
  fi
  sleep 5
done
