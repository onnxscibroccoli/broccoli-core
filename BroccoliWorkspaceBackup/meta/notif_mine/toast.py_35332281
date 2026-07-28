import subprocess, shutil, os
def toast(msg, long=False):
    msg = (msg or "")[:120]
    if not msg: return False
    for cmd in (
        ["termux-toast", "-g", "bottom", msg] if not long else ["termux-toast", "-g", "bottom", "-s", "long", msg],
        ["termux-notification", "--title", "Broccoli", "--content", msg, "--priority", "default", "--id", "broccoli"],
    ):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, timeout=8, capture_output=True)
                return True
            except Exception:
                pass
    # fallback: vibrate short pulse so something happens
    if shutil.which("termux-vibrate"):
        try:
            subprocess.run(["termux-vibrate", "-d", "80"], timeout=3, capture_output=True)
        except Exception:
            pass
    print("TOAST", msg, flush=True)
    return False
def step(label):
    toast(f"Broccoli: {label}")
