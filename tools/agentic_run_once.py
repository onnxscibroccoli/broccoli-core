#!/usr/bin/env python3
import sys, json, os
from pathlib import Path
BRO = Path.home() / "broccoli"
sys.path.insert(0, str(BRO/"lib"))
from broccoli_agentic_chat import send_prompt_agentic
print(json.dumps(send_prompt_agentic(), indent=2))
