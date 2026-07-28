#!/usr/bin/env python3
import json, re, subprocess, sys, time
from pathlib import Path
HOME, ROOT = Path.home(), Path.home() / "broccoli"
REP, META, LIB, UI = ROOT/"reports", ROOT/"meta", ROOT/"lib", ROOT/"ui"
BOOT = HOME / "broccoli_bootstrap.py"
for d in (REP,META,LIB,UI): d.mkdir(parents=True, exist_ok=True)
LOG = REP / "smoke_lesson_live.log"
def say(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    LOG.open("a").write(line+"\n")
def toast(m):
    subprocess.run(["termux-toast","-g","bottom",m[:120]], timeout=8, capture_output=True)
def run(cmd, t=180):
    say("CMD "+cmd[:160])
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
def score(name, ok, el, notes=""):
    return {"method":name,"pass":ok,"elapsed_s":round(el,1),"notes":notes}

def D():
    toast("1/5 log replay"); t0=time.time()
    sl=REP/"smoke_last.txt"; text=sl.read_text(errors="replace") if sl.exists() else ""
    ok=bool(re.search(r'text="GROK_SMOKE_OK"',text)) or ("PASS" in text and "GROK_SMOKE_OK" in text)
    return score("D_log_replay",ok,time.time()-t0,f"len={len(text)}")

def C():
    toast("2/5 autoheal"); t0=time.time()
    r=run(f'python3 "{ROOT}/broccoli_meta_heal.py"')
    ok=False; notes=(r.stdout or "")+(r.stderr or "")
    cf=META/"smoke_cache.json"
    if cf.exists():
        try: ok=json.loads(cf.read_text()).get("status")=="PASS"
        except: pass
    if "UnboundLocalError" in notes: ok=False
    return score("C_autoheal",ok,time.time()-t0,notes[:80])

def B():
    toast("3/5 dump+parse"); t0=time.time()
    sys.path.insert(0,str(LIB))
    from grok_xml_parse import find_smoke_ok
    if BOOT.exists():
        run(f'python3 "{BOOT}" launch_grok',45)
        run(f'python3 "{BOOT}" scroll_chat_end',30)
        r=run(f'python3 "{BOOT}" dump_ui',60)
        raw=(r.stdout or "")+(r.stderr or "")
        if "<?xml" in raw:
            i,j=raw.find("<?xml"),raw.rfind("</hierarchy>")
            if j>i: (UI/"last_ui.xml").write_text(raw[i:j+12],errors="replace")
    xml=(UI/"last_ui.xml").read_text(errors="replace") if (UI/"last_ui.xml").exists() else ""
    hit=find_smoke_ok(xml)
    return score("B_dump_parse", hit=="GROK_SMOKE_OK", time.time()-t0, f"hit={hit!r}")

def E():
    toast("4/5 front gate"); t0=time.time()
    wf=ROOT/"workflow_front.py"
    if not wf.exists(): return score("E_workflow_front",False,0,"missing")
    r=run(f'python3 "{wf}"',150)
    text=(r.stdout or "")+(r.stderr or "")
    ok="TASK_READY" in text or "SMOKE_PASS" in text
    wf_rep=REP/"workflow_front.txt"
    if wf_rep.exists(): ok=ok or "PASS" in wf_rep.read_text(errors="replace")
    return score("E_workflow_front",ok,time.time()-t0,"front")

def A():
    toast("5/5 grok-smoke"); t0=time.time()
    if not BOOT.exists(): return score("A_grok_smoke",False,0,"no bootstrap")
    r=run(f'python3 "{BOOT}" grok-smoke 2>&1',180)
    text=(r.stdout or "")+(r.stderr or "")
    ok='text="GROK_SMOKE_OK"' in text or ("GROK_SMOKE_OK" in text and "FAIL ''" not in text[-500:])
    if 'text="GROK_SMOKE_OK"' in text and "grok FAIL" in text: ok=True  # XML win over poller
    return score("A_grok_smoke",ok,time.time()-t0,"poller")

def main():
    LOG.write_text(f"=== lesson {time.strftime('%F %T')} ===\n")
    say("LESSON START (foreground)")
    toast("Smoke lesson")
    results=[]
    for fn in (D,C,B,E,A):
        res=fn(); results.append(res)
        say(f"RESULT {res['method']}: PASS={res['pass']} {res['elapsed_s']}s {res['notes']}")
        time.sleep(1.2)
    passed=sorted([r for r in results if r["pass"]], key=lambda x:x["elapsed_s"])
    rec="NONE"
    if passed:
        rec="B_dump_parse + C_autoheal" if any(r["method"]=="B_dump_parse" for r in passed) and any(r["method"]=="C_autoheal" for r in passed) else passed[0]["method"]
    report={"results":results,"recommendation":rec,"winner":passed[0] if passed else None}
    (REP/"smoke_compare.json").write_text(json.dumps(report,indent=2))
    say("=== SUMMARY ===")
    for r in results: say(f"  {r['method']}: {'PASS' if r['pass'] else 'FAIL'} ({r['elapsed_s']}s)")
    say(f"RECOMMENDED: {rec}")
    toast(f"Winner: {rec[:35]}")
    return 0 if passed else 1
if __name__=="__main__": sys.exit(main())
