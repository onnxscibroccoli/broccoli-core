#!/usr/bin/env python3

import subprocess
import time


def run(cmd):

    try:
        p = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        return p.stdout.strip()

    except Exception as e:
        return "ERROR:" + str(e)


def collect():

    now=time.time()

    return {
        "timestamp": now,

        "time_iso":
            time.strftime(
                "%Y-%m-%dT%H:%M:%S",
                time.localtime(now)
            ),

        "foreground":
            run(
                "printf 'dumpsys activity activities\\nexit\\n' | rish"
            ),

        "window":
            run(
                "printf 'dumpsys window windows\\nexit\\n' | rish"
            ),

        "ui":
            run(
                "printf 'uiautomator dump /sdcard/sysdump.xml\\nexit\\n' | rish"
            ),

        "processes":
            run(
                "ps -A | head -50"
            ),

        "memory":
            run(
                "free -m"
            )
    }


if __name__=="__main__":
    import json
    print(json.dumps(collect(),indent=2))
