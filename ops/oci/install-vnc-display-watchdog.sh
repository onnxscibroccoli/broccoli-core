#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install -d "$HOME/.omnikali" "$HOME/.config/autostart"
install -m 0755 "$ROOT/omnikali-vnc-display-watchdog.sh" "$HOME/.omnikali/vnc-display-watchdog.sh"
cat >"$HOME/.config/autostart/omnikali-vnc-display.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=OmniKali VNC Display Watchdog
Comment=Automatically restore readable XFCE VNC resolution and window decorations
Exec=/home/grasshopper/.omnikali/vnc-display-watchdog.sh
Terminal=false
X-GNOME-Autostart-enabled=true
DESKTOP
if [[ "${DISPLAY:-:1}" == :1 ]]; then
  nohup "$HOME/.omnikali/vnc-display-watchdog.sh" >/dev/null 2>&1 </dev/null &
fi
printf 'Installed auto-repair watchdog and XFCE autostart entry. Log: %s\n' "$HOME/.omnikali/display-watchdog.log"
