#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
export BROCCOLI_DIR
echo "Soft resume — stay in THIS chat; hands off 6s"
bash "$B/ui_grok.sh" || exit 1
python3 "$B/grok_ui_coords.py" | tee "$B/last_coords.json"
python3 "$B/chat_copy_tap.py" 2>/dev/null | tee "$B/last_copy.json" || true
python3 <<'PY'
import json
from pathlib import Path
B = Path(__import__("os").environ["BROCCOLI_DIR"])
prof = json.loads((B / "chat_profile.json").read_text())
inj = prof.setdefault("inject", {})
c = json.loads((B / "last_coords.json").read_text())
if c.get("input"):
    inj["CHAT_INPUT_X"] = c["input"]["x"]
    inj["CHAT_INPUT_Y"] = c["input"]["y"]
inj["CHAT_PACKAGE"] = "ai.x.grok"
inj["CHAT_ACTIVITY"] = "ai.x.grok/.main.GrokActivity"
inj["SUBMIT_METHOD"] = c.get("send_method", "keyevent_66")
cc = prof.setdefault("copy_chip", {})
if (B / "last_copy.json").is_file():
    try:
        cp = json.loads((B / "last_copy.json").read_text())
        if cp.get("ok"):
            cc["last_calibrated_x"] = cp["x"]
            cc["last_calibrated_y"] = cp["y"]
    except Exception:
        pass
(B / "chat_profile.json").write_text(json.dumps(prof, indent=2), encoding="utf-8")
print("saved", json.dumps({"inject": inj, "copy": cc}, indent=2))
PY
