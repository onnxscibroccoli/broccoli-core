#!/usr/bin/env python3

import subprocess
import json
from pathlib import Path
import time


ROOT=Path.home()/"broccoli"

REPORT=ROOT/"reports/agent/latest.txt"



def run(cmd):

    try:

        p=subprocess.run(
            cmd,
            shell=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30
        )

        return {
            "cmd":cmd,
            "ok":p.returncode==0,
            "out":p.stdout[-1000:],
            "err":p.stderr[-1000:]
        }

    except Exception as e:

        return {
            "cmd":cmd,
            "ok":False,
            "err":str(e)
        }



def verify():

    checks=[
        "test -x bin/brocc",
        "python3 agent/context.py >/dev/null",
        "python3 agent/planner.py >/dev/null"
    ]


    results=[
        run(x)
        for x in checks
    ]


    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    REPORT.write_text(
        json.dumps(
            {
            "time":time.time(),
            "results":results
            },
            indent=2
        )
    )


    print(REPORT.read_text())



if __name__=="__main__":
    verify()
