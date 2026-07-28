#!/data/data/com.termux/files/usr/bin/bash
# One-shot: rish open + chat FG + seed inbox from quarry/collab
set -e
export PATH="$HOME/bin:$PATH"
ROOT="$HOME/broccoli"
python3 "$ROOT/lib/rish_adb.py" || true
python3 "$ROOT/lib/grok_chat_foreground.py" || true
if [ -f "$ROOT/ui/collab_prompt.txt" ]; then
  cp "$ROOT/ui/collab_prompt.txt" "$ROOT/ui/loop_inbox.txt"
fi
echo "Wrote loop_inbox — starting loop (foreground, Ctrl+C to stop)"
python3 "$ROOT/lib/grok_open_loop.py" --once
