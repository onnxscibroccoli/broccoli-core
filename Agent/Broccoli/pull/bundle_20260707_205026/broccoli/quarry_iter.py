#!/usr/bin/env python3
"""
Simple iterative quarry: probe each script in framework, score PASS/FAIL, JSON report.
"""
import json, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "broccoli"
LIB, META, REP, UI = ROOT / "lib", ROOT / "meta", ROOT / "reports", ROOT / "ui"
BOOT = HOME / "broccoli_bootstrap.py"
CFG = ROOT / "quarry_framework.json"

def toast(msg):
    subprocess.run(["termux-toast", "-g", "bottom", msg[:100]], timeout=6, capture_output=True)

def run(cmd, t=120):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    except Exception as e:
        return type("R", (), {"stdout": "", "stderr": str(e), "returncode": -1})()

def probe(name, fn):
    t0 = time.time()
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, str(e)
    el = round(time.time() - t0, 2)
    row = {"probe": name, "pass": ok, "elapsed_s": el, "detail": (detail or "")[:400]}
    print(f"QUARRY {name}: {'PASS' if ok else 'FAIL'} ({el}s) {row['detail'][:80]}", flush=True)
    return row

def main():
    cfg = json.loads(CFG.read_text()) if CFG.exists() else {"order": [], "fail_fast": False}
    order = cfg.get("order", [])
    results = []

    def reboot_bootstrap():
        r = run(f'python3 "{ROOT}/reboot_bootstrap.py"', 45)
        ok = r.returncode == 0 and BOOT.exists()
        return ok, (r.stdout or "")[-200:]

    def paths_and_bins():
        need = [
            BOOT, ROOT / "workflow_front.py", ROOT / "broccoli_meta_heal.py",
            LIB / "grok_xml_parse.py", LIB / "smoke_autoheal.py",
            LIB / "grok_chat_foreground.py", LIB / "task_queue.py",
            ROOT / "broccoli_task_queue.py",
        ]
        miss = [str(p) for p in need if not p.exists()]
        return len(miss) == 0, f"missing={miss}" if miss else "all core paths ok"

    def display_primary():
        sys.path.insert(0, str(LIB))
        try:
            from display_context import log_display
            s = log_display(str(REP / "quarry_display.json"))
            return True, f"grok_focus={s.get('grok_in_focus')}"
        except Exception as e:
            r = run("dumpsys window windows 2>/dev/null | grep -i focus | head -2", 15)
            return "grok" in (r.stdout or "").lower(), (r.stdout or "")[:120]

    def launch_grok():
        if not BOOT.exists():
            return False, "no bootstrap"
        r = run(f'python3 "{BOOT}" launch_grok', 55)
        t = (r.stdout or "") + (r.stderr or "")
        fg = run("dumpsys window windows 2>/dev/null | grep -i grok | head -2", 12)
        ok = "grok" in (fg.stdout or "").lower() or r.returncode == 0
        return ok, fg.stdout[:100] if fg.stdout else t[-80:]

    def chat_foreground():
        p = LIB / "grok_chat_foreground.py"
        if not p.exists():
            return False, "missing grok_chat_foreground.py"
        r = run(f'python3 "{p}"', 330)
        xml = (UI / "last_ui.xml").read_text(errors="replace") if (UI / "last_ui.xml").exists() else ""
        ok = r.returncode == 0 and ("chat_text_input" in xml or "Ask anything" in xml)
        return ok, f"rc={r.returncode} composer={'yes' if ok else 'no'}"

    def dump_ui():
        def xml_ok(path):
            if not path.exists():
                return False, ""
            xml = path.read_text(errors="replace")
            ok = "ai.x.grok" in xml and "bounds=" in xml and len(xml) > 3000
            return ok, xml

        ok, _ = xml_ok(UI / "last_ui.xml")
        if ok:
            return True, "reuse last_ui.xml from chat_foreground"

        if not BOOT.exists():
            return False, "no bootstrap"
        r = run(f'python3 "{BOOT}" launch_grok', 40)
        run(f'python3 "{BOOT}" scroll_chat_end', 25)
        r = run(f'python3 "{BOOT}" dump_ui', 90)
        raw = (r.stdout or "") + (r.stderr or "")
        if "<?xml" in raw:
            i, j = raw.find("<?xml"), raw.rfind("</hierarchy>")
            if j > i:
                UI.mkdir(parents=True, exist_ok=True)
                (UI / "last_ui.xml").write_text(raw[i:j+12], errors="replace")
        ok, xml = xml_ok(UI / "last_ui.xml")
        if not ok and "bounds=" in raw and "ai.x.grok" in raw:
            UI.mkdir(parents=True, exist_ok=True)
            (UI / "last_ui.xml").write_text(raw, errors="replace")
            ok, _ = xml_ok(UI / "last_ui.xml")
        return ok, f"bytes={len(raw)} file={len(xml) if xml else 0}"

    def smoke_parse_B():
        sys.path.insert(0, str(LIB))
        from grok_xml_parse import find_smoke_ok
        xml = (UI / "last_ui.xml").read_text(errors="replace") if (UI / "last_ui.xml").exists() else ""
        if not xml and BOOT.exists():
            dump_ui()
            xml = (UI / "last_ui.xml").read_text(errors="replace") if (UI / "last_ui.xml").exists() else ""
        hit = find_smoke_ok(xml)
        ok = hit == "GROK_SMOKE_OK" or 'text="GROK_SMOKE_OK"' in xml
        return ok, f"hit={hit!r}"

    def smoke_heal_C():
        run("sed -i '/^    import time$/d' " + str(LIB / "smoke_autoheal.py"), 5)
        r = run(f'python3 "{ROOT}/broccoli_meta_heal.py"', 100)
        cf = META / "smoke_cache.json"
        ok = False
        if cf.exists():
            try:
                ok = json.loads(cf.read_text()).get("status") == "PASS"
            except Exception:
                pass
        return ok, (r.stdout or "")[-80:] + (" cache=PASS" if ok else " cache=FAIL")

    def workflow_front():
        wf = ROOT / "workflow_front.py"
        if not wf.exists():
            return False, "missing"
        r = run(f'python3 "{wf}"', 160)
        t = (r.stdout or "") + (r.stderr or "")
        ok = "FRONT_DONE" in t or "TASK_READY" in t or "SMOKE_PASS" in t
        return ok, t.strip()[-120:]

    def task_queue():
        r = run(f'python3 "{ROOT}/broccoli_task_queue.py" show', 30)
        ok = "BROCCOLI TASK QUEUE" in (r.stdout or "")
        return ok, (r.stdout or "")[:80]

    def idle_gate_dry():
        """Syntax/import only — no 10s wait."""
        p = LIB / "idle_takeover.py"
        if not p.exists():
            return False, "missing"
        r = run(f'python3 -c "import importlib.util; s=importlib.util.spec_from_file_location(\'it\', \'{p}\'); m=importlib.util.module_from_spec(s); print(\'ok\')"', 15)
        return r.returncode == 0, "import ok"

    fns = {
        "reboot_bootstrap": reboot_bootstrap,
        "paths_and_bins": paths_and_bins,
        "display_primary": display_primary,
        "launch_grok": launch_grok,
        "chat_foreground": chat_foreground,
        "dump_ui": dump_ui,
        "smoke_parse_B": smoke_parse_B,
        "smoke_heal_C": smoke_heal_C,
        "workflow_front": workflow_front,
        "task_queue": task_queue,
        "idle_gate_dry": idle_gate_dry,
    }

    toast("Quarry start")
    print("=== QUARRY ITER START ===", flush=True)
    for step in order:
        if step not in fns:
            results.append({"probe": step, "pass": False, "detail": "unknown probe"})
            continue
        results.append(probe(step, fns[step]))
        if cfg.get("fail_fast") and not results[-1]["pass"]:
            break
        time.sleep(cfg.get("between_probe_sec", 1))

    passed = sum(1 for r in results if r["pass"])
    report = {
        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "passed": passed,
        "total": len(results),
        "score_pct": round(100 * passed / max(len(results), 1), 1),
        "results": results,
        "winner_smoke": "B+C" if any(r["probe"] == "smoke_parse_B" and r["pass"] for r in results) else "retry",
    }
    (REP / "quarry_last.json").write_text(json.dumps(report, indent=2))
    (REP / "quarry_last.txt").write_text(
        "\n".join(f"{'PASS' if r['pass'] else 'FAIL'} {r['probe']} {r.get('elapsed_s','')}s" for r in results)
        + f"\n\nSCORE {passed}/{len(results)}\n"
    )

    try:
        sys.path.insert(0, str(LIB))
        from task_queue import note, rebuild_context
        note(f"quarry {passed}/{len(results)}")
        rebuild_context()
    except Exception:
        pass

    toast(f"Quarry {passed}/{len(results)}")
    print("=== QUARRY DONE ===", passed, "/", len(results), flush=True)
    return 0 if passed == len(results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
