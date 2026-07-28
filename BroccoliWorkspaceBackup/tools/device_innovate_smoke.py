#!/usr/bin/env python3
import json, sys
sys.path.insert(0, str(__import__("pathlib").Path.home() / "broccoli" / "lib"))
from broccoli_device import device_ready, foreground_pkg, rish_ok
from broccoli_rish_shell import shell

def main():
    out = {"device_ready": device_ready(), "foreground": foreground_pkg()}
    try:
        out["wm_size"] = shell("wm size")
    except Exception as e:
        out["wm_size_error"] = str(e)
    print(json.dumps(out, indent=2))
    if not out["device_ready"].get("rish_ok"):
        sys.exit(2)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
