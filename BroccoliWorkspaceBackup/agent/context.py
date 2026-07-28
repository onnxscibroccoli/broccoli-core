#!/usr/bin/env python3

import json
import os
import hashlib
import time
from pathlib import Path


ROOT = Path.home() / "broccoli"

STATE = ROOT / "state" / "agent_state.json"


IGNORE = {
    ".git",
    "__pycache__",
    "node_modules"
}


def sha256(path):

    h = hashlib.sha256()

    try:
        with open(path,"rb") as f:
            for chunk in iter(lambda:f.read(65536),b""):
                h.update(chunk)

        return h.hexdigest()

    except Exception:
        return None



def inventory():

    files=[]

    for base,dirs,names in os.walk(ROOT):

        dirs[:] = [
            d for d in dirs
            if d not in IGNORE
        ]

        for name in names:

            p=Path(base)/name

            try:
                files.append({
                    "path":str(p.relative_to(ROOT)),
                    "size":p.stat().st_size,
                    "hash":sha256(p)
                })

            except Exception:
                pass


    return files



def build_state():

    state={
        "project":"broccoli",
        "timestamp":time.strftime("%Y-%m-%dT%H:%M:%S"),
        "phase":"observer",
        "files":inventory(),
        "known_modules":[],
        "known_failures":[],
        "next_objective":""
    }

    return state



if __name__=="__main__":

    state=build_state()

    STATE.write_text(
        json.dumps(
            state,
            indent=2
        )
    )

    print(
        json.dumps(
            state,
            indent=2
        )
    )
