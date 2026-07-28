#!/usr/bin/env python3

import subprocess
import time


ROOT="/data/data/com.termux/files/home/broccoli"


while True:

    print(
        "\n===== BROCC AGENT LOOP ====="
    )

    steps=[
        "python3 agent/context.py",
        "python3 agent/planner.py",
        "python3 agent/verifier.py"
    ]


    for step in steps:

        print("[RUN]",step)

        subprocess.run(
            step,
            shell=True,
            cwd=ROOT
        )


    print(
        "sleeping..."
    )

    time.sleep(60)
