#!/data/data/com.termux/files/usr/bin/bash
command -v termux-notification >/dev/null 2>&1 || exit 0
termux-notification --id broccoli_agent --title "${1:-Broccoli}" --content "${2:-}" --priority high ${3:+--ongoing} 2>/dev/null || true
