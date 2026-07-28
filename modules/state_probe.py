#!/usr/bin/env python3
"""Probe Grok UI state — single source of truth for gates."""
import json, os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = "/sdcard/broccoli_window_dump.xml"

def snap(timeout=22):
    try:
        subprocess.run(["bash", "ui_snapshot.sh"], cwd=ROOT, timeout=timeout, capture_output=True)
    except subprocess.TimeoutExpired:
        pass

def read_dump():
    try:
        return open(DUMP, encoding="utf-8", errors="ignore").read()
    except Exception:
        return ""

def new_chat_focused(xml: str) -> bool:
    low = xml.lower()
    return "new chat" in low and 'focused="true"' in low

def probe(*, refresh=True) -> dict:
    if refresh:
        snap()
    xml = read_dump()
    r = subprocess.run(["python3", "screen_state.py"], cwd=ROOT, capture_output=True, text=True, timeout=15)
    try:
        st = json.loads(r.stdout or "{}")
    except Exception:
        st = {}
    st["_dump_len"] = len(xml)
    st["new_chat_focused"] = new_chat_focused(xml)
    st["has_composer"] = bool(st.get("chat_text_input") or st.get("can_inject"))
    st["in_grok_chat"] = bool(
        st.get("on_grok")
        or st.get("fg_package") == "ai.x.grok"
        or st.get("screen") == "grok_chat_composer"
    )
    return st

def precondition(state: dict) -> tuple[bool, str]:
    if not state.get("in_grok_chat"):
        return False, "not_in_grok"
    if state.get("new_chat_focused"):
        return False, "new_chat_focused_open_sidebar_or_open_thread"
    return True, "ok"

if __name__ == "__main__":
    import json as J
    print(J.dumps(probe(), indent=2))
