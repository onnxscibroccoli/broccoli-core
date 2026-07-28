#!/usr/bin/env python3

import subprocess
import shutil


def run(cmd):
    try:
        return subprocess.check_output(
            cmd,
            shell=True,
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
    except Exception:
        return ""


methods = [
    "termux-clipboard-get",
    "cmd clipboard get",
]

for method in methods:

    if method == "termux-clipboard-get":
        if not shutil.which(method):
            continue

    result = run(
        f"printf '%s\nexit\n' '{method}' | rish"
        if method != "termux-clipboard-get"
        else method
    )

    if result:
        print(result)
        raise SystemExit(0)


print("NO_CLIPBOARD_ACCESS")
