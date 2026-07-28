#!/usr/bin/env python3
"""
Broccoli full-system investigator.
Scans tree, configs, scripts, logs; correlates failures; writes INVESTIGATION_REPORT.md + JSON.
"""
from __future__ import annotations
import json, os, re, subprocess
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

HOME = Path.home()
ROOT = HOME / "broccoli"
REPORTS = ROOT / "reports"
META = ROOT / "meta"

KEY_SCRIPTS = [
    "lib/adb_rish.sh", "lib/launch_grok_native.sh", "lib/ui_dump_rish.sh",
    "lib/user_idle_sec.sh", "lib/focus_pkg.sh",
    "tools/wire_send_ui.sh", "tools/wire_daemon.sh", "tools/find_send_tap.py",
    "tools/gap_watch.sh", "tools/gap_analyze.py", "tools/ui_state.py",
    "tools/agent_wrap.sh", "lib/grok_send_tap.py",
    "boot/GROK_NATIVE.conf",
]
KEY_FILES = [
    "INSTRUCTIONS.md", "task_box.txt", "queue/pending.txt", "queue/done.txt",
    "ui/last_ui.xml", "reports/wire_send.log", "reports/wire_daemon.log",
    "reports/loop_health.jsonl", "reports/manual_gap.jsonl",
    "thread/to_chat.md", "meta/WIRE_STOP",
]

def sh(cmd: str, timeout=25) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return str(e)

def file_info(p: Path) -> dict:
    if not p.is_file():
        return {"exists": False}
    st = p.stat()
    return {"exists": True, "bytes": st.st_size, "mtime": datetime.fromtimestamp(st.st_mtime).isoformat()}

def scan_tree() -> dict:
    if not ROOT.is_dir():
        return {"error": "no broccoli root"}
    by_ext = defaultdict(int)
    paths = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in (".git", "__pycache__")]
        for fn in fns:
            p = Path(dp) / fn
            rel = str(p.relative_to(ROOT))
            paths.append(rel)
            by_ext[p.suffix or "(noext)"] += 1
    return {"file_count": len(paths), "by_ext": dict(by_ext), "sample": sorted(paths)[:80]}

def grep_file(p: Path, patterns: list[str]) -> dict:
    if not p.is_file():
        return {}
    text = p.read_text(encoding="utf-8", errors="replace")
    out = {}
    for pat in patterns:
        out[pat] = len(re.findall(pat, text, re.I))
    return out

def audit_scripts() -> list[dict]:
    findings = []
    chrome_pat = re.compile(r"chrome|grok\.com|intent\.action\.VIEW", re.I)
    for rel in KEY_SCRIPTS:
        p = ROOT / rel
        fi = file_info(p)
        row = {"path": rel, **fi}
        if fi.get("exists"):
            t = p.read_text(encoding="utf-8", errors="replace")
            row["executable"] = os.access(p, os.X_OK)
            row["chrome_hits"] = len(chrome_pat.findall(t))
            row["launch_grok_native"] = "launch_grok_native" in t
            row["gap_watch"] = "gap_watch" in t
            row["ui_dump_rish"] = "ui_dump_rish" in t
            if row["chrome_hits"] and "agent_wrap" in rel or "grok_send_tap" in rel:
                findings.append({"severity": "high", "msg": f"{rel} still references Chrome/WEB", "fix": "route to launch_grok_native.sh only"})
            if rel.endswith("wire_send_ui.sh") and not row.get("gap_watch"):
                findings.append({"severity": "med", "msg": "wire_send_ui not hooked to gap_watch", "fix": "patch gap hooks on fail/success/timeout"})
            if rel.endswith("ui_dump_rish.sh") and "launch_grok_native" not in t:
                findings.append({"severity": "high", "msg": "ui_dump_rish may dump wrong FG", "fix": "foreground Grok before every dump"})
        else:
            findings.append({"severity": "high", "msg": f"missing {rel}", "fix": "install from RECOVER block"})
        row["_findings"] = []
    return findings

def analyze_last_ui() -> dict:
    p = ROOT / "ui/last_ui.xml"
    if not p.is_file() or p.stat().st_size < 400:
        return {"ok": False, "reason": "missing_or_tiny"}
    xml = p.read_text(encoding="utf-8", errors="replace")
    pkgs = sorted(set(re.findall(r'package="([^"]+)"', xml)))
    grok = "ai.x.grok" in xml
    comp = bool(re.search(r"chat_text_input|EditText", xml))
    send_nodes = []
    for m in re.finditer(r"<node([^>]+)/?>", xml):
        a = m.group(1)
        if 'clickable="true"' not in a:
            continue
        blob = a.lower()
        if not re.search(r"send|submit|imagebutton", blob):
            continue
        rid = re.search(r'resource-id="([^"]*)"', a)
        b = re.search(r'bounds="(\[[^\]]+\])"', a)
        send_nodes.append({"rid": rid.group(1) if rid else "", "bounds": b.group(1) if b else "", "voice": "voice" in blob or "mic" in blob})
    return {
        "ok": True, "bytes": len(xml), "grok_fg": grok, "packages": pkgs[:10],
        "has_composer": comp, "send_candidates": send_nodes[:12],
        "termux_only": pkgs == ["com.termux"] or (not grok and "com.termux" in pkgs),
    }

def tail_jsonl(p: Path, n=15) -> list:
    if not p.is_file():
        return []
    lines = p.read_text(errors="replace").splitlines()[-n:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            out.append({"raw": ln[:200]})
    return out

def parse_wire_send_log() -> dict:
    p = ROOT / "reports/wire_send.log"
    if not p.is_file():
        return {"lines": 0}
    lines = p.read_text(errors="replace").splitlines()
    counts = defaultdict(int)
    for ln in lines:
        for k in ("SEND start", "send_tap", "send_confirmed", "MANUAL_LIKELY", "FATAL", "reply=", "SKIP dup"):
            if k in ln:
                counts[k] += 1
    return {"lines": len(lines), "counts": dict(counts), "tail": lines[-20:]}

def live_probe() -> dict:
    """Optional live checks (rish, dump)."""
    probe = {"rish": None, "dump_bytes": None, "grok_after_dump": None}
    if not (ROOT / "lib/ui_dump_rish.sh").is_file():
        return probe
    out = sh(f"bash {ROOT}/lib/ui_dump_rish.sh 2>/dev/null | tail -1", timeout=45)
    probe["dump_bytes"] = out.strip().split()[-1] if out.strip() else None
    ui = analyze_last_ui()
    probe["grok_after_dump"] = ui.get("grok_fg")
    probe["packages_after_dump"] = ui.get("packages")
    probe["termux_trap"] = ui.get("termux_only")
    return probe

def build_findings(script_findings, ui, log_stats, probe) -> list[dict]:
    f = list(script_findings)
    if ui.get("termux_only"):
        f.append({"severity": "critical", "msg": "last_ui.xml is Termux-focused, not Grok", "fix": "ui_dump_rish must launch Grok + retry until ai.x.grok in XML"})
    if ui.get("ok") and ui.get("grok_fg") and not ui.get("send_candidates"):
        f.append({"severity": "high", "msg": "Grok FG but no send candidates in dump regex", "fix": "dump send row manually; patch find_send_tap.py with exact resource-id"})
    if log_stats.get("counts", {}).get("MANUAL_LIKELY", 0) > 0:
        f.append({"severity": "high", "msg": "wire_send logged MANUAL_LIKELY", "fix": "read to_chat.md Send controls; calibrate find_send_tap"})
    if probe.get("termux_trap"):
        f.append({"severity": "critical", "msg": "live probe still dumps Termux", "fix": "user must not focus Termux during dump; strengthen launch_grok_native loop"})
    q = ROOT / "queue/pending.txt"
    if q.is_file() and not q.read_text().strip():
        f.append({"severity": "med", "msg": "queue empty — daemon idle with nothing to send", "fix": "inbox_to_queue.sh or task_box.txt"})
    return sorted(f, key=lambda x: {"critical": 0, "high": 1, "med": 2, "low": 3}.get(x["severity"], 9))

def markdown_report(data: dict) -> str:
    lines = [
        "# Broccoli system investigation",
        f"Generated: {data['ts']}",
        "",
        "## Architecture (expected)",
        "- **Broccoli** = Termux executor (queue, sandbox, reports).",
        "- **Grok app** = accessibility only (dump/tap/paste/read).",
        "- **Wire** = daemon + wire_send_ui + ui_dump_rish (invariant: `ai.x.grok` in dump).",
        "",
        "## Tree",
        f"- Files under `~/broccoli`: **{data['tree']['file_count']}**",
        f"- Extensions: `{data['tree']['by_ext']}`",
        "",
        "## Key artifacts",
    ]
    for k, v in data["artifacts"].items():
        lines.append(f"- `{k}`: {v}")
    lines += ["", "## Last UI dump", "```json", json.dumps(data["ui"], indent=2), "```"]
    lines += ["", "## wire_send.log summary", "```json", json.dumps(data["wire_send"], indent=2), "```"]
    if data.get("live_probe"):
        lines += ["", "## Live probe (just ran ui_dump_rish)", "```json", json.dumps(data["live_probe"], indent=2), "```"]
    lines += ["", "## Findings (priority order)"]
    for i, x in enumerate(data["findings"], 1):
        lines.append(f"{i}. **[{x['severity'].upper()}]** {x['msg']}")
        lines.append(f"   - Fix: {x['fix']}")
    lines += [
        "",
        "## Co-dev window",
        f"- State file: `~/broccoli/meta/codev_window.json`",
        f"- Session: `{data['codev']['session_id']}`",
        "- Paste **this entire report** (or `reports/INVESTIGATION_REPORT.md`) into Mac Grok chat for full-context patches.",
        "- Re-run: `bash ~/broccoli/tools/investigate_system.sh --live`",
        "",
        "## Recommended next patches (ordered)",
    ]
    for x in data["findings"][:5]:
        lines.append(f"- {x['fix']}")
    return "\n".join(lines)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="run ui_dump_rish live probe")
    ap.add_argument("--no-live", action="store_true")
    args = ap.parse_args()
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    script_findings = audit_scripts()
    ui = analyze_last_ui()
    wire_send = parse_wire_send_log()
    artifacts = {k: file_info(ROOT / k) for k in KEY_FILES}
    live = live_probe() if args.live and not args.no_live else {}
    findings = build_findings(script_findings, ui, wire_send, live)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    codev = {
        "session_id": session_id,
        "opened_at": ts,
        "status": "open",
        "last_investigation": str(REPORTS / "INVESTIGATION_REPORT.md"),
        "next_action": findings[0]["fix"] if findings else "run wire smoke test",
        "findings_count": len(findings),
    }
    data = {
        "ts": ts,
        "tree": scan_tree(),
        "artifacts": artifacts,
        "ui": ui,
        "wire_send": wire_send,
        "loop_health_tail": tail_jsonl(REPORTS / "loop_health.jsonl"),
        "manual_gap_tail": tail_jsonl(REPORTS / "manual_gap.jsonl"),
        "findings": findings,
        "live_probe": live,
        "codev": codev,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    (REPORTS / "investigation.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    md = markdown_report(data)
    (REPORTS / "INVESTIGATION_REPORT.md").write_text(md, encoding="utf-8")
    (META / "codev_window.json").write_text(json.dumps(codev, indent=2), encoding="utf-8")
    (ROOT / "thread" / "to_chat.md").write_text(
        "## Co-dev: paste INVESTIGATION_REPORT.md to Mac Grok\n\n" + md[:12000],
        encoding="utf-8",
    )
    print(md)

if __name__ == "__main__":
    main()
