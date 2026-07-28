#!/usr/bin/env python3

import subprocess
import time
import sys


def rish(cmd):
    try:
        p = subprocess.run(
            ["rish"],
            input=cmd + "\nexit\n",
            capture_output=True,
            text=True,
            timeout=10
        )
        return p.stdout + p.stderr

    except Exception as exc:
        return str(exc)


def foreground():

    commands = [
        "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity'",
        "dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'"
    ]

    output = ""

    for command in commands:
        output += rish(command)

    return output


for attempt in range(30):

    out = foreground()

    print(out.strip())

    if "ai.x.grok" in out:
        print("GROK_FOREGROUND=1")
        sys.exit(0)

    time.sleep(1)


print("GROK_FOREGROUND=0")
sys.exit(1)
