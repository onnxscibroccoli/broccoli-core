#!/usr/bin/env python3
"""Compare script intent vs UI: what user likely did that automation did not."""
import json, re, sys
from pathlib import Path
from datetime import datetime, timezone

HOME = Path.home()
UI = HOME / "broccoli/ui/last_ui.xml"
LOG = HOME / "broccoli/reports/wire_send.log"
GAP = HOME / "broccoli/reports/manual_gap.jsonl"
CHAT = HOME / "broccoli/thread/to_chat.md"

def read_ui():
    if not UI.is_file():
        return ""
    return UI.read_text(encoding="utf-8", errors="replace")

def packages(xml):
    return sorted(set(re.findall(r'package="([^"]+)"', xml)))

def composer_text(xml):
    for pat in [
        r'chat_text_input[^>]*text="([^"]*)"',
        r'EditText[^>]*package="ai\.x\.grok"[^>]*text="([^"]*)"',
    ]:
        m = re.search(pat, xml)
        if m:
            return m.group(1).strip()
    return ""

def chat_tail(xml, n=12):
    lines, seen = [], set()
    for m in re.finditer(r'text="([^"]{2,4000})"', xml):
        t = m.group(1).strip()
        if t in seen:
            continue
        seen.add(t)
        lines.append(t)
    return lines[-n:]

def last_send_log_lines(n=25):
    if not LOG.is_file():
        return []
    return LOG.read_text(errors="replace").splitlines()[-n:]

def infer_gap(msg, xml, send_log):
    comp = composer_text(xml)
    tail = chat_tail(xml)
    pkgs = packages(xml)
    grok_fg = "ai.x.grok" in xml
    script_did = []
    script_failed = []
    user_likely = []

    for ln in send_log:
        if "send_tap" in ln or "send_confirmed" in ln:
            script_did.append(ln.strip()[-120:])
        if "MANUAL_LIKELY" in ln or "send_enter" in ln or "FATAL" in ln or "TIMEOUT" in ln:
            script_failed.append(ln.strip()[-120:])

    frag = (msg or "")[:35]
    msg_in_thread = frag and any(frag in t for t in tail)
    composer_has = frag and frag in comp

    if not grok_fg:
        user_likely.append("foreground was not ai.x.grok during dump — user may have switched app or dump ran on wrong window")
    if composer_has and not msg_in_thread:
        user_likely.append("text still in composer — script paste/send did not complete; user may need to tap Send")
    if msg_in_thread and not any("send_confirmed" in x for x in send_log):
        user_likely.append("message appears in chat but script never logged send_confirmed — user likely tapped Send manually")
    if "MANUAL_LIKELY" in "\n".join(send_log):
        user_likely.append("script logged MANUAL_LIKELY — auto send tap/enter did not match UI")
    if not user_likely and msg_in_thread:
        user_likely.append("none detected — automation may have worked")

    send_nodes = []
    for m in re.finditer(r'<node([^>]+)/?>', xml):
        a = m.group(1)
        if "clickable=\"true\"" not in a:
            continue
        blob = a.lower()
        if not re.search(r"send|submit|imagebutton", blob):
            continue
        if "voice" in blob or "mic" in blob:
            continue
        rid = re.search(r'resource-id="([^"]*)"', a)
        b = re.search(r'bounds="(\[[^\]]+\])"', a)
        send_nodes.append({
            "rid": rid.group(1) if rid else "",
            "bounds": b.group(1) if b else "",
        })

    return {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "grok_fg": grok_fg,
        "packages": pkgs[:8],
        "composer_preview": comp[:200],
        "chat_tail": tail[-6:],
        "send_candidates": send_nodes[:6],
        "script_did": script_did[-5:],
        "script_failed": script_failed[-8:],
        "user_likely_manual": user_likely,
        "prompt_frag": frag,
    }

def format_for_chat(report):
    lines = [
        "## Broccoli wire gap (auto)",
        f"- time: {report['ts']}",
        f"- grok foreground: {report['grok_fg']}",
        f"- packages: {', '.join(report['packages'])}",
        f"- prompt (frag): {report['prompt_frag']}",
        "",
        "### What script tried",
    ]
    for x in report["script_did"] or ["(nothing logged)"]:
        lines.append(f"- {x}")
    lines += ["", "### What failed / uncertain"]
    for x in report["script_failed"] or ["(none)"]:
        lines.append(f"- {x}")
    lines += ["", "### What user likely did (not script)"]
    for x in report["user_likely_manual"]:
        lines.append(f"- {x}")
    if report["send_candidates"]:
        lines += ["", "### Send controls in last UI dump"]
        for s in report["send_candidates"]:
            lines.append(f"- `{s['rid']}` {s['bounds']}")
    lines += ["", "### Chat tail (dump)"]
    for t in report["chat_tail"]:
        lines.append(f"- {t[:200]}")
    lines.append("")
    lines.append("**Fix target:** `~/broccoli/tools/find_send_tap.py` and `wire_send_ui.sh` confirm step.")
    return "\n".join(lines)

def main():
    msg = sys.argv[1] if len(sys.argv) > 1 else ""
    xml = read_ui()
    slog = last_send_log_lines()
    report = infer_gap(msg, xml, slog)
    GAP.parent.mkdir(parents=True, exist_ok=True)
    with GAP.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")
    text = format_for_chat(report)
    CHAT.write_text(text, encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
