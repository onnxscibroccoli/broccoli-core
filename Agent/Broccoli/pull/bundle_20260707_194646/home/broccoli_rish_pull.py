
#!/usr/bin/env python3
"""Export Broccoli project to /sdcard/Broccoli/pull via shizuku/rish shell (adb-visible)."""
import json, os, shutil, subprocess, time
from pathlib import Path

H = Path.home()
R = H / "broccoli"
OUT = Path("/sdcard/Broccoli/pull")
OUT.mkdir(parents=True, exist_ok=True)
MANIFEST = OUT / "manifest.json"

def run(cmd, t=60):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)

def rish_sh(script, t=90):
    """Prefer rish CLI; fall back to shizuku -r sh -c."""
    for prefix in (
        'rish -c %s' % json.dumps(script),
        "shizuku -r sh -c %s" % json.dumps(script),
    ):
        r = run(prefix, t)
        if r.returncode == 0 or (r.stdout or r.stderr):
            return r
    return r

def termux_home_on_device():
    return "/data/data/com.termux/files/home"

def collect_inventory():
    files = []
    names = [
        "brocc", "broccoli_bootstrap.py", "broccoli_compose.py", "broccoli_worker.sh",
        "broccoli-daemon.sh", "broccoli_grok_job.py", "broccoli_agent.py", "broccoli_pulse.py",
        "broccoli_mac_ingest.py", "broccoli_agent_context.py", "broccoli_a11y.py",
        "broccoli_rish_pull.py", "broccoli_meta.py", "broccoli_research.py",
        "broccoli_user_wait.py", "google_ai_bootstrap.py", ".grok_ui_cal.json",
    ]
    for n in names:
        p = H / n
        if p.is_file():
            files.append({"path": str(p), "size": p.stat().st_size, "role": "root"})
    if R.is_dir():
        for p in sorted(R.rglob("*")):
            if p.is_file() and p.stat().st_size < 3_000_000:
                files.append({
                    "path": str(p),
                    "size": p.stat().st_size,
                    "role": "broccoli",
                    "rel": str(p.relative_to(R)),
                })
    return files

def sync_to_sdcard():
    """Python copy from Termux (always works); rish used for dumpsys/a11y extras."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    bundle = OUT / ("bundle_%s" % ts)
    bundle.mkdir(parents=True, exist_ok=True)
    inv = collect_inventory()
    for item in inv:
        src = Path(item["path"])
        if not src.is_file():
            continue
        if item.get("role") == "broccoli":
            dst = bundle / "broccoli" / item.get("rel", src.name)
        else:
            dst = bundle / "home" / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    # a11y dump on sdcard for Mac
    run("python3 %s dump 2>/dev/null" % (H / "broccoli_a11y.py"), 45)
    # rish: extra system-readable snapshot paths
    th = termux_home_on_device()
    rish_sh("ls -la %s 2>/dev/null | head -80" % th, 30)
    rish_sh("ls -la %s/broccoli 2>/dev/null | head -80" % th, 30)
    MANIFEST.write_text(json.dumps({
        "ts": ts,
        "termux_home": str(H),
        "bundle": str(bundle),
        "file_count": len(inv),
        "files": inv,
        "mac_pull": [
            "adb pull /sdcard/Broccoli/pull/manifest.json .",
            "adb pull /sdcard/Broccoli/pull/bundle_%s ." % ts,
            "adb pull /sdcard/Broccoli/ui/latest_a11y.xml .",
        ],
        "rish_pull_hint": "rish exec cat /sdcard/Broccoli/pull/manifest.json",
    }, indent=2))
    shutil.copy2(MANIFEST, OUT / "manifest_latest.json")
    (OUT / "PULL_README.txt").write_text(
        "Mac:\n  adb pull /sdcard/Broccoli/pull .\n  OR rish: cat /sdcard/Broccoli/pull/manifest_latest.json\n"
        "Phone:\n  brocc pull-rish\n  brocc ask 'LOOP_OK\\nNEXT_STEP: Mac pull manifest_latest.json'\n"
    )
    print("PULL_RISH_OK", len(inv), str(bundle))
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(sync_to_sdcard())
