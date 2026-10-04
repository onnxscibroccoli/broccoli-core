"""brocc grok status — evidence packet, no provider call."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from runtime.grok.evidence import collect_evidence, repo_root
from runtime.grok.prompts import render_prompt
from runtime.grok.store import write_status


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="brocc grok status")
    parser.add_argument("--json", action="store_true", help="emit the envelope as JSON")
    parser.add_argument("--no-store", action="store_true", help="do not write data/grok/status")
    args = parser.parse_args(argv)

    root = repo_root()
    envelope = collect_evidence(root)
    stored = None
    if not args.no_store:
        stored = write_status(root, envelope)
        envelope = dict(envelope)
        envelope["stored"] = str(stored)
    if args.json:
        print(json.dumps(envelope, indent=2, default=str))
    else:
        print(render_prompt(envelope))
        if stored:
            print(f"stored: {stored}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
