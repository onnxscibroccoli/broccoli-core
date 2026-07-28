#!/data/data/com.termux/files/usr/bin/bash
T="${1:-Broccoli}"; M="${2:-}"; I="${3:-broccoli}"
command -v termux-toast >/dev/null 2>&1 && termux-toast -g middle "$T: $M" 2>/dev/null || true
command -v termux-notification >/dev/null 2>&1 && termux-notification --id "$I" --title "$T" --content "$M" --priority high 2>/dev/null || true
