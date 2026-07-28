#!/usr/bin/env bash
set -eu
B="${BROCCOLI_DIR:-$HOME/broccoli}"

case "${1:-}" in
    set)
        termux-clipboard-set "$(cat "${2:?Error: Specify file path to copy to clipboard}")"
        ;;
    get)
        termux-clipboard-get
        ;;
    *)
        echo "Usage: clipboard.sh set|get [file]" >&2
        exit 1
        ;;
esac
