#!/usr/bin/env python3
"""Patch restart script + enforce spawn cap metadata."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PERMS = ROOT / "broccoli_permissions.json"
RESTART = ROOT / "broccoli_auto_restart.sh"
MAIN = ROOT / "broccoli_main_v2.1.0.py"


def load_perms():
    if PERMS.exists():
        return json.loads(PERMS.read_text(encoding="utf-8"))
    return {}


def save_perms(data):
    PERMS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def patch_restart(max_children: int):
    if not RESTART.exists():
        RESTART.write_text(
            "#!/data/data/com.termux/files/usr/bin/bash\n"
            "export BROCC_MAX_CHILDREN=%d\n"
            "export BROCC_NO_SELF_MUTATE=1\n"
            "cd \"$(dirname \"$0\")\"\n"
            "exec python3 broccoli_main_v2.1.0.py\n" % max_children,
            encoding="utf-8",
        )
        RESTART.chmod(0o755)
        print("Created broccoli_auto_restart.sh")
        return
    text = RESTART.read_text(encoding="utf-8")
    text = re.sub(r"export BROCC_MAX_CHILDREN=\d+", "", text)
    text = re.sub(r"export BROCC_NO_SELF_MUTATE=\d+", "", text)
    if "BROCC_NO_SELF_MUTATE" not in text:
        text = "export BROCC_NO_SELF_MUTATE=1\n" + text
    if "BROCC_MAX_CHILDREN" not in text:
        text = "export BROCC_MAX_CHILDREN=%d\n" % max_children + text
    RESTART.write_text(text, encoding="utf-8")
    print("Patched broccoli_auto_restart.sh")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-children", type=int, default=2)
    args = ap.parse_args()
    data = load_perms()
    data["max_child_processes"] = args.max_children
    data.setdefault("block_spawn_unless_whitelisted", True)
    save_perms(data)
    patch_restart(args.max_children)
    if not MAIN.exists():
        print("WARN: broccoli_main_v2.1.0.py not in", ROOT)
    print("OK guardrails applied, max_children=%d" % args.max_children)


if __name__ == "__main__":
    main()
