#!/usr/bin/env python3

import sys
import os
import time


ROOT=os.path.expanduser("~/broccoli")

sys.path.insert(
    0,
    ROOT
)


from modules.sysdump.collector import collect
from modules.sysdump.buffer import append,trim


INTERVAL=int(
    os.environ.get(
        "SYSDUMP_INTERVAL",
        "10"
    )
)


while True:

    try:

        append(
            collect()
        )

        trim()

    except Exception as e:

        print(
            "SYSDUMP:",
            e,
            flush=True
        )


    time.sleep(INTERVAL)
