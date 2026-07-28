#!/data/data/com.termux/files/usr/bin/bash

set -Eeuo pipefail

ROOT="$HOME/broccoli"

mkdir -p \
    "$ROOT/modules/sysdump" \
    "$ROOT/data/sysdump" \
    "$ROOT/daemons" \
    "$ROOT/logs"


cat > "$ROOT/modules/sysdump/__init__.py" <<'PY'
PY


cat > "$ROOT/modules/sysdump/collector.py" <<'PY'
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
PY


cat > "$ROOT/modules/sysdump/buffer.py" <<'PY'
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
PY


cat > "$ROOT/modules/sysdump/replay.py" <<'PY'
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
PY


cat > "$ROOT/daemons/sysdumpd.py" <<'PY'
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
PY


chmod +x \
"$ROOT/daemons/sysdumpd.py" \
"$ROOT/modules/sysdump/"*.py


echo "[+] Patching brocc"


python3 - <<'PY'
from pathlib import Path

p=Path.home()/"broccoli/bin/brocc"

s=p.read_text()


insert=r'''
    sysdump)

        sub="${1:-tail}"

        case "$sub" in

            start)

                mkdir -p "$ROOT/logs"

                nohup \
                python3 \
                "$ROOT/daemons/sysdumpd.py" \
                >>"$ROOT/logs/sysdump.log" \
                2>&1 &

                echo "sysdump started"
            ;;


            tail)

                tail -20 \
                "$ROOT/data/sysdump/system.jsonl"
            ;;


            replay)

                cd "$ROOT"

                python3 \
                -m modules.sysdump.replay \
                "${2:-30}"
            ;;

        esac

        ;;

'''


marker='    probe)'

if 'sysdump)' not in s:

    s=s.replace(
        marker,
        insert+marker
    )

p.write_text(s)

PY


chmod +x "$ROOT/bin/brocc"

hash -r

echo
echo "SELF TEST"
echo

brocc help

echo
echo "Starting sysdump..."
echo

brocc sysdump start

sleep 12

echo
echo "TAIL:"
echo

brocc sysdump tail
