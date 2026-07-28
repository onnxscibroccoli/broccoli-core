#!/usr/bin/env python3

import json
import time
import sys

FILE="data/sysdump/system.jsonl"


def replay(seconds):

    cutoff=time.time()-seconds

    try:
        f=open(FILE)
    except:
        print("No sysdump history yet")
        return


    for line in f:

        try:
            obj=json.loads(line)

            if obj["timestamp"] >= cutoff:
                print(json.dumps(obj,indent=2))

        except:
            pass



if __name__=="__main__":

    replay(
        int(sys.argv[1])
        if len(sys.argv)>1
        else 30
    )
