#!/usr/bin/env python3
"""Exit 0 = OK (Grok + chat input). Exit 1 = wrong/missing. Prints JSON status."""
import json, re, sys, xml.etree.ElementTree as ET
from pathlib import Path

B = Path(__import__("os").environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
PKG = "ai.x.grok"
xml_path = B / "window_dump.xml"

def fail(reason, extra=None):
    o = {"ok": False, "reason": reason}
    if extra: o.update(extra)
    print(json.dumps(o))
    sys.exit(1)

if not xml_path.is_file() or xml_path.stat().st_size < 200:
    fail("no_dump")

text = xml_path.read_text(errors="replace")
if PKG not in text:
    fail("not_grok", {"top_pkg": "unknown"})

root = ET.parse(xml_path).getroot()
has_input = False
has_ask = False
voice_only = False
bad_screen = False

for el in root.iter("node"):
    p = el.attrib.get("package") or ""
    if PKG not in p and p:
        continue
    rid = el.attrib.get("resource-id") or ""
    t = (el.attrib.get("text") or "").strip()
    desc = (el.attrib.get("content-desc") or "").strip()
    if "chat_text_input" in rid:
        has_input = True
    if t == "Ask anything":
        has_ask = True
    if "Grok Voice" in desc or desc == "Start Grok Voice":
        voice_only = True
    # Obvious wrong surfaces (settings, login splash without input)
    if t in ("Log in", "Sign up", "Settings") and not has_input:
        bad_screen = True

# OK = Grok package + composer target exists
if has_input or has_ask:
    print(json.dumps({
        "ok": True,
        "reason": "grok_chat",
        "has_chat_text_input": has_input,
        "has_ask_anything": has_ask,
    }))
    sys.exit(0)

if bad_screen:
    fail("grok_wrong_screen")
fail("grok_no_composer", {"hint": "open chat thread with composer"})
