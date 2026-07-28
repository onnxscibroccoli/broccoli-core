#!/usr/bin/env python3

import os
import json
import time


ROOT=os.path.expanduser("~/broccoli")

FILE=os.path.join(
    ROOT,
    "data/sysdump/system.jsonl"
)


RETENTION=int(
    os.environ.get(
        "SYSDUMP_RETENTION",
        "300"
    )
)


def append(record):

    os.makedirs(
        os.path.dirname(FILE),
        exist_ok=True
    )

    with open(FILE,"a") as f:
        f.write(
            json.dumps(record)
            + "\n"
        )


def trim():

    if not os.path.exists(FILE):
        return

    cutoff=time.time()-RETENTION

    keep=[]

    with open(FILE) as f:

        for line in f:

            try:

                obj=json.loads(line)

                if obj.get("timestamp",0)>=cutoff:
                    keep.append(line)

            except Exception:
                pass


    with open(FILE,"w") as f:
        f.writelines(keep)
