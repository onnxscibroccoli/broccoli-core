"""ADB on device via Termux RISH context — production path."""
import os, subprocess

def rish_env():
    os.environ["RISH_APPLICATION_ID"] = os.environ.get("RISH_APPLICATION_ID", "com.termux")
    return os.environ.copy()

def adb_shell(args: str, timeout=30):
    """args: everything after `adb shell`, e.g. monkey -p pkg ..."""
    cmd = ["adb", "shell"] + args.split()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=rish_env())
    return r.returncode, (r.stdout or "") + (r.stderr or "")

def launch_app_monkey(package: str = None, wait_log=None):
    pkg = package or os.environ.get("BROCCOLI_GROK_PKG", "")
    if not pkg:
        return 1, "no BROCCOLI_GROK_PKG"
    rc, out = adb_shell(
        f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1"
    )
    if wait_log:
        wait_log(f"launch_monkey pkg={pkg} rc={rc}")
    return rc, out
