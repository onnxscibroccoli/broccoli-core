
#!/usr/bin/env python3
import subprocess, sys, time, fcntl
from pathlib import Path
H, META = Path.home(), Path.home() / "broccoli/meta"
LOCK = Path("/data/data/com.termux/files/usr/tmp/brocc.watch.lock")
INTERVAL = int(__import__("os").environ.get("BROCC_WATCH_SEC", "25"))
BATCH = int(__import__("os").environ.get("BROCC_SYNC_BATCH", "80"))
DEBOUNCE = int(__import__("os").environ.get("BROCC_DEBOUNCE_SEC", "30"))

def fp():
    m = Path.home() / "broccoli"
    return sum((p.stat().st_size + int(p.stat().st_mtime)) for p in m.rglob("*") if p.is_file()) if m.is_dir() else 0

def main():
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    fd = open(LOCK, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("brocc_watch already running"); return
    print("RECURSIVE_LOOP_ON interval=%ss" % INTERVAL)
    last_fp, pending = None, None
    py = sys.executable
    while True:
        subprocess.run([py, str(META / "brocc_live_wire.py")], timeout=120, check=False)
        f = fp()
        if f != last_fp:
            pending = time.time()
            last_fp = f
        if pending and time.time() - pending >= DEBOUNCE:
            subprocess.run([py, str(H / "broccoli_storage_sync.py"), "sync", str(BATCH)], timeout=300, check=False)
            pending = None
        subprocess.run([py, str(META / "brocc_loop_emit.py")], timeout=120, check=False)
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
