#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")/.."
export PATH="$(pwd)/bin:$PATH"
exec brocc smoke "${1:-smoke test}"
