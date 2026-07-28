#!/usr/bin/env python3
import json
from pathlib import Path
B = Path(__import__("os").environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
prof = json.loads((B / "chat_profile.json").read_text())
inj = prof.get("inject", {})
print(inj.get("CHAT_INPUT_X", 540), inj.get("CHAT_INPUT_Y", 2139),
      inj.get("CHAT_SEND_X", 1001), inj.get("CHAT_SEND_Y", 2203))
