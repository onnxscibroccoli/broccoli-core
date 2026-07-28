\
"""Call broccoli_agentic_chat if it exposes open/focus chat. Patched when discovery finds real APIs."""
import sys
from pathlib import Path
BRO = Path.home() / "broccoli"
mode = (sys.argv[1] if len(sys.argv) > 1 else "reuse")
rish = BRO / "broccoli_agentic_chat.py"
if not rish.exists():
    raise SystemExit(2)
import importlib.util
spec = importlib.util.spec_from_file_location("broccoli_agentic_chat", rish)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

# Try common names — discovery will replace with real ones
for name in (
    "focus_grok_chat", "open_grok_chat", "ensure_chat_focus",
    "open_chat", "focus_chat", "start_grok_foreground",
):
    fn = getattr(m, name, None)
    if callable(fn):
        fn(new=(mode == "new"))
        print("OK", name, mode)
        raise SystemExit(0)

# Module-level run hooks
for name in ("main", "focus", "open"):
    fn = getattr(m, name, None)
    if callable(fn):
        fn()
        print("OK", name)
        raise SystemExit(0)

raise SystemExit(1)
