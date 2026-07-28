#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
PROMPT_FILE="${1:-$HOME/broccoli/spec/PULL_SPEC_PROMPT.txt}"
OUT="${2:-$HOME/broccoli/spec/BUILD_SPEC.md}"
RAW="$HOME/broccoli/spec/gemini_raw.txt"
MAX_WAIT=180
PROMPT="$(cat "$PROMPT_FILE")"
sh "$HOME/aim_rish_ensure.sh" 2>/dev/null || true
# Gemini app (not Google Search / puppy chrome prompt)
am start -a android.intent.action.VIEW -d "https://gemini.google.com/app" -p com.android.chrome 2>/dev/null \
  || am start -n com.google.android.apps.bard/.shellapp.ShellActivity 2>/dev/null \
  || am start -a android.intent.action.VIEW -d "https://gemini.google.com/app" 2>/dev/null
sleep 4
export AIM_ASK_MAX_WAIT="$MAX_WAIT"
export AIM_ASK_PROMPT="$PROMPT"
python3 <<'PY'
import os, subprocess, sys
prompt = os.environ["AIM_ASK_PROMPT"]
mx = int(os.environ.get("AIM_ASK_MAX_WAIT", "180"))
# paste via termux clipboard (avoids aim_ask_once.sh $1/$2 mixup)
subprocess.run(["termux-clipboard-set"], input=prompt.encode("utf-8"), check=False, timeout=20)
PY
if [ -f "$HOME/aim_ask_once.sh" ]; then
  # call with TIMEOUT first, prompt via stdin if script supports it
  if grep -q 'stdin.read' "$HOME/aim_ask_once.sh" 2>/dev/null; then
    AIM_ASK_MAX_WAIT="$MAX_WAIT" bash "$HOME/aim_ask_once.sh" < "$PROMPT_FILE" 2>&1 | tee "$RAW"
  else
    # patch-safe wrapper: only pass timeout as $1, prompt as $2 quoted
    AIM_ASK_MAX_WAIT="$MAX_WAIT" bash -c 'source "$HOME/aim_ask_once.sh" 2>/dev/null' 2>/dev/null || true
    bash "$HOME/aim_ask_once.sh" "$MAX_WAIT" "$(cat "$PROMPT_FILE")" 2>&1 | tee "$RAW" || \
    python3 "$HOME/aim_poll_gemini.py" "$MAX_WAIT" "$PROMPT_FILE" 2>&1 | tee "$RAW" || \
    python3 "$HOME/aim_submit.py" "$PROMPT_FILE" 2>&1 | tee "$RAW"
  fi
else
  python3 "$HOME/gemini_bootstrap.py" "$(cat "$PROMPT_FILE")" 2>&1 | tee "$RAW"
fi
# save reply
if [ -s "$RAW" ] && ! grep -qi 'brown puppy\|puppy\|udm=2' "$RAW"; then
  cp -f "$RAW" "$OUT"
elif [ -s "$HOME/aim_last_reply.txt" ]; then
  cp -f "$HOME/aim_last_reply.txt" "$OUT"
else
  termux-clipboard-get > "$OUT" 2>/dev/null || true
fi
wc -c "$OUT" "$RAW" 2>/dev/null
head -3 "$OUT" 2>/dev/null
