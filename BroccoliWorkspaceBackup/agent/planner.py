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
