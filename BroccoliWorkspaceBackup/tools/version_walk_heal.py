#!/usr/bin/env python3
import os, sys, re, json, time, shutil, hashlib, subprocess
from pathlib import Path
BRO = Path.home() / "broccoli"
LIB = BRO / "lib"
GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
TEST = "BROCC_WALK reply exactly: LOOP_OK"
LOG = BRO / "reports/version_walk.log"
sys.path.insert(0, str(LIB))

def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text((LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else "") +
                   time.strftime("%H:%M:%S ")+m+"\n", encoding="utf-8")
    print(m)

def discover():
    seen, out = set(), []
    def add(name, path):
        if not path.is_dir(): return
        py = {p.name: p for p in path.glob("broccoli*.py")}
        if len(py) < 1: return
        key = tuple(sorted((k, p.stat().st_mtime_ns) for k,p in py.items()))
        if key in seen: return
        seen.add(key)
        out.append((name, py, max(p.stat().st_mtime for p in py.values())))
    add("current", LIB)
    pin = LIB / "_pinned_from_walk"
    if pin.is_dir(): add("pinned", pin)
    for root in [BRO/"archive", BRO/"backups", BRO/"snapshots", BRO/"heal", Path("/sdcard/Broccoli/pull")]:
        if not root.exists(): continue
        if (root/"lib").is_dir(): add(str(root/"lib"), root/"lib")
        for p in root.rglob("lib"):
            if p.is_dir() and any(p.glob("broccoli*.py")):
                add(str(p), p)
        for p in root.rglob("broccoli_input.py"):
            add(str(p.parent), p.parent)
    out.sort(key=lambda x: -x[2])
    return out[:35]

def try_bundle(name, pyfiles):
    staging = BRO / "state" / "walk_stage"
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir(parents=True)
    for fn, src in pyfiles.items():
        shutil.copy2(src, staging / fn)
    for must in ("broccoli_rish_shell.py", "broccoli_core_round.py"):
        s = LIB / must
        if s.exists() and not (staging/must).exists():
            shutil.copy2(s, staging / must)
    sys.path.insert(0, str(staging))
    for k in list(sys.modules.keys()):
        if k.startswith("broccoli_"): del sys.modules[k]
    from broccoli_core_round import full_round
    r = full_round(TEST)
    return r

def pin(name, pyfiles):
    pin = LIB / "_pinned_from_walk"
    pin.mkdir(exist_ok=True)
    for fn, src in pyfiles.items():
        if src.is_file(): shutil.copy2(src, pin / fn)
    (BRO/"meta/active_stack.json").write_text(json.dumps({
        "bundle": name, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "test": TEST,
    }, indent=2), encoding="utf-8")

def main():
    log("WALK_START")
    for name, pyfiles, _ in discover():
        log(f"TRY {name} n={len(pyfiles)}")
        try:
            r = try_bundle(name, pyfiles)
        except Exception as e:
            r = {"ok": False, "stage": "exception", "error": str(e)[:120]}
        log(f"  -> {json.dumps(r)[:280]}")
        if r.get("ok"):
            pin(name, pyfiles)
            (BRO/"reports/version_walk_result.json").write_text(json.dumps({"winner": name, "result": r}, indent=2))
            log(f"WINNER {name}")
            return 0
    log("WALK_NO_WINNER using broccoli_core_round only")
    from broccoli_core_round import full_round
    r = full_round(TEST)
    if r.get("ok"):
        pin("core_round_baseline", {"broccoli_core_round.py": LIB/"broccoli_core_round.py"})
    (BRO/"reports/version_walk_result.json").write_text(json.dumps({"winner": None, "last": r}, indent=2))
    return 1 if not r.get("ok") else 0

if __name__ == "__main__":
    sys.exit(main())
