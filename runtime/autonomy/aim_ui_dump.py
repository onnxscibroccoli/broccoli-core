"""AIM_UI_DUMP — uiautomator hierarchy capture + parse for Grok chat."""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path.home() / "broccoli-core"
UI_DIR = ROOT / "meta" / "always_on" / "ui"
LEGACY_PATHS = [
    Path.home() / "broccoli" / "ui" / "last_ui.xml",
    Path("/data/local/tmp/broccoli_ui.xml"),
    Path.home() / "broccoli" / "reports" / "ui_dump.xml",
]
NOISE = re.compile(
    r"^(Ask|Send|Grok|Imagine|Explore|Home|Menu|Search|Voice|New chat|Speak|Ask anything|\s*)$",
    re.I,
)


def _run(cmd: List[str], timeout: int = 20) -> Tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, str(e)


def _rish(cmd: str, timeout: int = 20) -> Tuple[int, str]:
    for wrapper in (["rish", "-c", cmd], ["sh", "-c", cmd]):
        code, out = _run(wrapper, timeout=timeout)
        if out.strip() or code == 0:
            return code, out
    return 1, ""


def dump_ui(out_xml: Optional[Path] = None) -> Dict[str, Any]:
    UI_DIR.mkdir(parents=True, exist_ok=True)
    out_xml = out_xml or (UI_DIR / "last_ui.xml")
    tmp = "/data/local/tmp/broccoli_ui_dump.xml"
    attempts = []
    for cmd in (f"uiautomator dump {tmp}", f"uiautomator dump --compressed {tmp}"):
        code, out = _rish(cmd)
        attempts.append({"cmd": cmd, "code": code, "out": out[:300]})
        if code == 0:
            _, body = _rish(f"cat {tmp}")
            if body and "<hierarchy" in body:
                out_xml.write_text(body, encoding="utf-8", errors="replace")
                return {"ok": True, "path": str(out_xml), "bytes": len(body), "attempts": attempts}

    for p in LEGACY_PATHS:
        if p.is_file() and p.stat().st_size > 500:
            t = p.read_text(encoding="utf-8", errors="replace")
            if "<hierarchy" in t:
                out_xml.write_text(t, encoding="utf-8", errors="replace")
                return {"ok": True, "path": str(out_xml), "bytes": len(t), "source": str(p), "attempts": attempts}

    return {"ok": False, "path": str(out_xml), "attempts": attempts, "reason": "no_hierarchy"}


def _nodes(xml: str) -> List[Dict[str, str]]:
    out = []
    for m in re.finditer(r"<node([^>]+)/?>", xml):
        a = m.group(1)

        def g(k: str) -> str:
            mm = re.search(rf'{k}="([^"]*)"', a)
            return mm.group(1) if mm else ""

        out.append(
            {
                "text": g("text"),
                "desc": g("content-desc"),
                "rid": g("resource-id"),
                "klass": g("class"),
                "pkg": g("package"),
                "bounds": g("bounds"),
                "clickable": g("clickable"),
            }
        )
    return out


def _bounds_center(bounds: str) -> Optional[Dict[str, int]]:
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return {"x": (x1 + x2) // 2, "y": (y1 + y2) // 2, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "bounds": bounds}


def parse_xml(xml: str) -> Dict[str, Any]:
    nodes = _nodes(xml)
    packages = {n["pkg"] for n in nodes if n["pkg"]}
    composer = None
    mic = None
    send = None

    for n in nodes:
        c = _bounds_center(n["bounds"])
        if not c:
            continue
        rid = (n["rid"] or "").lower()
        desc = (n["desc"] or "").lower()
        text = (n["text"] or "").strip()
        klass = n["klass"] or ""

        if "EditText" in klass or "chat_text_input" in rid:
            if composer is None or c["y"] > composer["y"]:
                composer = {**c, "rid": n["rid"], "pkg": n["pkg"]}

        if any(k in desc or k in rid or k in text.lower() for k in ("dictation", "microphone", "mic", "voice")):
            if "start dictation" in desc or "mic" in rid or "dictation" in desc or "microphone" in desc:
                mic = {**c, "rid": n["rid"], "desc": n["desc"], "klass": klass}

        if text.lower() == "speak" or desc == "speak" or "speak" in desc:
            send = {**c, "rid": n["rid"], "text": text or n["desc"], "klass": klass, "role": "speak_or_send"}
        if text.lower() == "send" or "send" in rid or desc == "send":
            send = {**c, "rid": n["rid"], "text": text or n["desc"], "klass": klass, "role": "send"}

    if composer:
        row_y0 = composer["y"] - 120
        row_y1 = composer["y"] + 120
        candidates = []
        for n in nodes:
            if n.get("clickable") != "true":
                continue
            c = _bounds_center(n["bounds"])
            if not c or not (row_y0 <= c["y"] <= row_y1):
                continue
            klass = n["klass"] or ""
            if "ImageButton" not in klass and "Button" not in klass and "ImageView" not in klass:
                continue
            if c["x"] < composer["x"]:
                continue
            candidates.append((c["x"], {**c, "rid": n["rid"], "desc": n["desc"], "klass": klass, "role": "row_icon"}))
        candidates.sort(key=lambda x: x[0])
        if candidates:
            rightmost = candidates[-1][1]
            if mic and rightmost["x"] > mic["x"]:
                send = {**rightmost, "role": "up_arrow_right_of_mic"}
            elif send is None:
                send = rightmost

    lines, seen = [], set()
    for n in nodes:
        for f in ("text", "desc"):
            t = (n[f] or "").strip()
            if len(t) < 2 or len(t) > 6000 or NOISE.match(t) or t in seen:
                continue
            seen.add(t)
            lines.append(t)

    grok = any("ai.x.grok" in p for p in packages) or "ai.x.grok" in xml
    return {
        "ok": bool(xml and "<hierarchy" in xml),
        "bytes": len(xml),
        "packages": sorted(packages),
        "grok_fg": grok,
        "has_composer": composer is not None,
        "composer": composer,
        "mic": mic,
        "send": send,
        "chat_lines": lines[-30:],
        "last": lines[-1] if lines else "",
    }


def dump_and_parse() -> Dict[str, Any]:
    d = dump_ui()
    result: Dict[str, Any] = {"timestamp": int(time.time()), "dump": d}
    UI_DIR.mkdir(parents=True, exist_ok=True)
    if not d.get("ok"):
        result["parse"] = {"ok": False, "reason": d.get("reason", "dump_failed")}
        (UI_DIR / "last_dump.json").write_text(json.dumps(result, indent=2))
        return result
    xml = Path(d["path"]).read_text(encoding="utf-8", errors="replace")
    result["parse"] = parse_xml(xml)
    (UI_DIR / "last_dump.json").write_text(json.dumps(result, indent=2))
    try:
        leg = Path.home() / "broccoli" / "ui"
        leg.mkdir(parents=True, exist_ok=True)
        (leg / "last_ui.xml").write_text(xml, encoding="utf-8", errors="replace")
    except Exception:
        pass
    return result


def tap(x: int, y: int) -> Dict[str, Any]:
    code, out = _rish(f"input tap {x} {y}")
    return {"ok": code == 0, "x": x, "y": y, "out": out[:200]}


def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="AIM_UI_DUMP")
    p.add_argument("cmd", nargs="?", default="dump", choices=["dump", "parse", "report"])
    args = p.parse_args()
    if args.cmd in ("dump", "report"):
        print(json.dumps(dump_and_parse(), indent=2))
    else:
        xml_path = UI_DIR / "last_ui.xml"
        xml = xml_path.read_text(encoding="utf-8", errors="replace") if xml_path.is_file() else ""
        print(json.dumps(parse_xml(xml), indent=2))


if __name__ == "__main__":
    main()
