
#!/usr/bin/env python3
import argparse, json, shutil, time
from pathlib import Path
R, SD, MIRROR = Path.home() / "broccoli", Path("/sdcard/Broccoli"), Path("/sdcard/Broccoli/mirror")
MAN, MAX = SD / "mirror_manifest.json", 500_000_000


SKIP_VOLATILE_PARTS = (
    "meta/watch.log", "meta/grok_emit.log", "meta/grok_send_heal.log",
    "meta/live_wire.log", "meta/investigate.jsonl", "meta/loop_packet.json",
    "meta/loop_state.json", "meta/auto_into_state.json", "meta/clip_prompt_state.json",
)
def _skip_mirror_key(key):
    k = key.replace(chr(92), "/")
    if k.endswith(".log") or k.endswith(".lock"): return True
    return any(p in k for p in SKIP_VOLATILE_PARTS)

def rel(p):
    try: return str(p.relative_to(R))
    except ValueError: return p.name

def walk_src():
    o = {}
    if not R.is_dir(): return o
    for p in R.rglob("*"):
        if not p.is_file(): continue
        try:
            e = {"size": p.stat().st_size, "mtime": int(p.stat().st_mtime)}
            if p.stat().st_size > MAX: e["skip_huge"] = True
            o[rel(p)] = e
        except OSError: pass
    return o

def walk_dst():
    o = {}
    if not MIRROR.is_dir(): return o
    for p in MIRROR.rglob("*"):
        if not p.is_file(): continue
        try: o[str(p.relative_to(MIRROR))] = {"size": p.stat().st_size, "mtime": int(p.stat().st_mtime)}
        except OSError: pass
    return o

def verify():
    src, dst = walk_src(), walk_dst()
    miss, stale, ok = [], [], []
    for k, v in src.items():
        if v.get("skip_huge"): continue
        if k not in dst: miss.append(k)
        elif dst[k]["size"] != v["size"] or dst[k]["mtime"] < v["mtime"]: stale.append(k)
        else: ok.append(k)
    rep = {"ts": time.strftime("%F %T"), "missing": len(miss), "stale": len(stale), "ok": len(ok),
           "mac_pull": ["adb pull /sdcard/Broccoli/mirror_manifest.json .",
                        "adb pull /sdcard/Broccoli/mirror ./Broccoli-mirror",
                        "adb pull /sdcard/Broccoli/pull/CLIPBOARD_LAST.txt ."]}
    SD.mkdir(parents=True, exist_ok=True)
    rep["missing_sample"] = miss[:25]; rep["stale_sample"] = stale[:25]
    MAN.write_text(json.dumps(rep, indent=2))
    return rep, miss + stale

def sync(limit=100):
    _, todo = verify()
    n = 0
    for k in todo[: int(limit)]:
        s, d = R / k, MIRROR / k
        if s.is_file():
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    verify()
    return n

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["verify", "sync"])
    ap.add_argument("limit", nargs="?", type=int, default=100)
    a = ap.parse_args()
    print(json.dumps(verify()[0], indent=2) if a.cmd == "verify" else "SYNC_OK %s" % sync(a.limit))
