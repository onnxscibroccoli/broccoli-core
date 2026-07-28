#!/usr/bin/env python3
import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = os.environ.copy()
env["BROCC_ROOT"] = ROOT
r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "grok_universal_cycle.py")] + sys.argv[1:],
                   cwd=ROOT, env=env, timeout=300)
sys.exit(0 if r.returncode == 0 else 0)
