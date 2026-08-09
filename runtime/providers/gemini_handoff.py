"""Gemini handoff helper — file/GitHub only, no cloud connectors."""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path.home() / "broccoli-core"

def run_snapshot() -> Path:
    script = ROOT / "tools" / "gemini_device_snapshot.sh"
    subprocess.run(["bash", str(script)], cwd=str(ROOT), check=False)
    return ROOT / "meta" / "gemini" / "device_snapshot.md"

def show_prompt() -> str:
    p = ROOT / "meta" / "handoff" / "GEMINI_INIT_PROMPT.md"
    return p.read_text(encoding="utf-8") if p.is_file() else "(missing)"

def main() -> None:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["snapshot", "prompt", "paths"])
    args = p.parse_args()
    if args.cmd == "snapshot":
        path = run_snapshot()
        print(path)
        if path.is_file():
            print(path.read_text()[:2000])
    elif args.cmd == "prompt":
        print(show_prompt())
    else:
        print("snapshot_script", ROOT / "tools/gemini_device_snapshot.sh")
        print("snapshot_out", ROOT / "meta/gemini/device_snapshot.md")
        print("init_prompt", ROOT / "meta/handoff/GEMINI_INIT_PROMPT.md")

if __name__ == "__main__":
    main()
