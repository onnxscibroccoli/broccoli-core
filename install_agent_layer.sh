#!/data/data/com.termux/files/usr/bin/bash

set -Eeuo pipefail

ROOT="$HOME/broccoli"

mkdir -p \
"$ROOT/agent" \
"$ROOT/state" \
"$ROOT/prompts" \
"$ROOT/reports/agent"


cat > "$ROOT/agent/context.py" <<'PY'
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
PY



cat > "$ROOT/agent/planner.py" <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path
import time


ROOT=Path.home()/"broccoli"


STATE=ROOT/"state/agent_state.json"

PROMPT=ROOT/"prompts/next_prompt.md"



def load():

    try:
        return json.loads(
            STATE.read_text()
        )

    except Exception:
        return {}



def plan():

    state=load()

    files=[
        x["path"]
        for x in state.get("files",[])
    ]


    objective=""

    if "modules/grok_focus.py" in files:
        objective=(
        "Improve Android foreground detection. "
        "Prefer UIAutomator package authority "
        "fallback when activity APIs fail."
        )

    else:
        objective=(
        "Create initial device automation modules."
        )


    text=f"""
Continue Broccoli development.

Generated:
{time.strftime("%Y-%m-%d %H:%M:%S")}

Current phase:
{state.get("phase")}

Known files:
{len(files)}

Next objective:

{objective}

Rules:

- Preserve working modules.
- Inspect before modifying.
- Create verification commands.
- Record failures.
- Keep rollback possible.
"""


    PROMPT.write_text(text.strip())


    state["next_objective"]=objective

    STATE.write_text(
        json.dumps(
            state,
            indent=2
        )
    )


    print(text)



if __name__=="__main__":
    plan()
PY



cat > "$ROOT/agent/verifier.py" <<'PY'
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
PY



cat > "$ROOT/agent/loop.py" <<'PY'
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
PY



chmod +x "$ROOT"/agent/*.py


echo "Agent layer installed."
