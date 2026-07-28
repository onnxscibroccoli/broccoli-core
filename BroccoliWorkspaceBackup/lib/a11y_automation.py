#!/data/data/com.termux/files/usr/bin/env python3
"""Accessibility automation: dump UI, find nodes, tap, inject text. Uses RISH + optional Broccoli a11y APK."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

HOME = Path.home()
BRO = HOME / "broccoli"
UI = BRO / "ui" / "last_ui.xml"
RISH_APP = os.environ.get("RISH_APPLICATION_ID", "com.termux")

# Optional: your installed a11y helper APK broadcasts (set if you built broccoli a11y)
A11Y_PKG = os.environ.get("BROCC_A11Y_PKG", "")  # e.g. com.broccoli.a11y
A11Y_ACTION_TAP = os.environ.get("BROCC_A11Y_ACTION_TAP", "com.broccoli.a11y.TAP")
A11Y_ACTION_PASTE_SEND = os.environ.get("BROCC_A11Y_ACTION_PASTE_SEND", "com.broccoli.a11y.PASTE_SEND")


def rish(cmd: str, timeout: int = 25) -> tuple[int, str]:
    env = {**os.environ, "RISH_APPLICATION_ID": RISH_APP}
    try:
        r = subprocess.run(
            ["rish", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return r.returncode, ((r.stdout or "") + (r.stderr or "")).strip()
    except Exception as e:
        return 1, str(e)


def ensure_rish() -> bool:
    p = HOME / "aim_rish_ensure.sh"
    if p.is_file():
        subprocess.run(["bash", str(p)], timeout=30, check=False)
    c, o = rish("echo RISH_OK")
    return c == 0 and "RISH_OK" in o


def dump_ui() -> Path:
    sh = BRO / "lib" / "ui_dump_rish.sh"
    if sh.is_file():
        subprocess.run(["bash", str(sh)], timeout=45, check=False)
    return UI


def _attrs(node: ET.Element) -> dict:
    return {k: (node.get(k) or "") for k in ("text", "content-desc", "resource-id", "class", "bounds", "clickable")}


def find_nodes(
    xml_path: Path,
    *,
    text_contains: str = "",
    desc_contains: str = "",
    rid_contains: str = "",
    class_contains: str = "",
) -> list[dict]:
    if not xml_path.is_file():
        return []
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        raw = xml_path.read_text(encoding="utf-8", errors="replace")
        # fallback regex for broken dumps
        nodes = []
        for m in re.finditer(r'<node[^>]+>', raw):
            tag = m.group(0)
            if text_contains and text_contains not in tag:
                continue
            b = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
            if b:
                x1, y1, x2, y2 = map(int, b.groups())
                nodes.append({"bounds": [x1, y1, x2, y2], "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2, "raw": tag[:200]})
        return nodes

    out = []
    for el in root.iter("node"):
        a = _attrs(el)
        blob = " ".join(a.values())
        if text_contains and text_contains.lower() not in blob.lower():
            continue
        if desc_contains and desc_contains.lower() not in blob.lower():
            continue
        if rid_contains and rid_contains not in a.get("resource-id", ""):
            continue
        if class_contains and class_contains not in a.get("class", ""):
            continue
        b = a.get("bounds", "")
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b)
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        out.append({**a, "bounds": [x1, y1, x2, y2], "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2})
    return out


def tap(cx: int, cy: int) -> bool:
    if A11Y_PKG:
        c, o = rish(
            f'am broadcast -a {A11Y_ACTION_TAP} --ei x {cx} --ei y {cy} -p {A11Y_PKG}'
        )
        if c == 0:
            return True
    c, _ = rish(f"input tap {cx} {cy}")
    return c == 0


def set_clipboard(text: str) -> None:
    try:
        subprocess.run(["termux-clipboard-set"], input=text, text=True, timeout=8, check=False)
    except Exception:
        pass
    # Shizuku clipper if installed
    rish(f'cmd clipboard set "{text[:500].replace(chr(34), "")}"'[:800], timeout=10)


def paste_and_send_heuristic(app_key: str) -> bool:
    """Tap composer, paste, tap send — per-app hints."""
    dump_ui()
    hints = {
        "grok": [
            ("rid", "edit", "composer"),
            ("desc", "Message", ""),
            ("class", "EditText", ""),
        ],
        "chatgpt": [
            ("rid", "input", ""),
            ("desc", "Message", ""),
            ("class", "EditText", ""),
        ],
        "gemini": [
            ("rid", "input", ""),
            ("desc", "Ask", ""),
            ("class", "EditText", ""),
        ],
    }
    send_hints = [
        ("desc", "Send", ""),
        ("text", "Send", ""),
        ("rid", "send", ""),
    ]
    composer = None
    for kind, a, b in hints.get(app_key, hints["grok"]):
        if kind == "rid":
            nodes = find_nodes(UI, rid_contains=a)
        elif kind == "desc":
            nodes = find_nodes(UI, desc_contains=a)
        else:
            nodes = find_nodes(UI, class_contains=a)
        nodes = [n for n in nodes if n.get("clickable") != "false" or kind == "class"]
        if nodes:
            composer = nodes[-1]
            break
    if not composer:
        # bottom-center fallback
        w, h = 1080, 2400
        tap(w // 2, int(h * 0.92))
    else:
        tap(composer["cx"], composer["cy"])
    time.sleep(0.4)
    rish("input keyevent 279")  # PASTE
    time.sleep(0.5)
    dump_ui()
    for kind, a, b in send_hints:
        nodes = find_nodes(UI, desc_contains=a) if kind == "desc" else find_nodes(UI, text_contains=a) if kind == "text" else find_nodes(UI, rid_contains=a)
        if nodes:
            tap(nodes[-1]["cx"], nodes[-1]["cy"])
            return True
    rish("input keyevent 66")  # ENTER
    return True


def extract_assistant_messages(xml_path: Path, skip_clip: bool = True) -> list[str]:
    if not xml_path.is_file():
        return []
    texts = []
    try:
        for el in ET.parse(xml_path).getroot().iter("node"):
            t = (el.get("text") or "").strip()
            d = (el.get("content-desc") or "").strip()
            for s in (t, d):
                if len(s) < 4:
                    continue
                if skip_clip and s.startswith("CLIP_V2_"):
                    continue
                if s.startswith("BROCC_RESULT") or s.startswith("BROCC_TASK"):
                    continue
                texts.append(s)
    except ET.ParseError:
        raw = xml_path.read_text(encoding="utf-8", errors="replace")
        texts = re.findall(r'text="([^"]{4,8000})"', raw)
    # dedupe preserve order, prefer longer assistant blobs
    seen = set()
    out = []
    for t in texts:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[-15:]


def last_assistant_text() -> str:
    dump_ui()
    msgs = extract_assistant_messages(UI)
    return msgs[-1] if msgs else ""


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "help"
    app = os.environ.get("BROCC_CHAT_APP", "grok")
    if not ensure_rish():
        print("FAIL rish")
        return 2
    if cmd == "dump":
        dump_ui()
        print(UI)
        return 0
    if cmd == "tap" and len(argv) >= 4:
        tap(int(argv[2]), int(argv[3]))
        return 0
    if cmd == "last":
        print(last_assistant_text()[:12000])
        return 0
    if cmd == "send_clip":
        text = sys.stdin.read() if not sys.stdin.isatty() else Path(argv[2]).read_text(encoding="utf-8")
        set_clipboard(text)
        subprocess.run(["bash", str(BRO / "lib" / "shizuku_apps.sh"), app, "foreground"], check=False)
        time.sleep(1.0)
        paste_and_send_heuristic(app)
        print("A11Y_SEND ok")
        return 0
    print("usage: a11y_automation.py dump|last|send_clip|tap x y")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
