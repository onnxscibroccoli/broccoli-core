"""`brocc grok status` — evidence packet, not a provider call."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from runtime.grok.evidence import collect
from runtime.grok.prompts import status_prompt
from runtime.grok.store import write_status


def root_from_env() -> Path:
    raw = os.environ.get("BROCC_ROOT")
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="brocc grok status")
    parser.add_argument("--json", action="store_true", help="print the envelope instead of the prompt")
    parser.add_argument("--no-store", action="store_true", help="do not write data/grok/status")
    parser.add_argument("--provider", action="store_true", help="record oauth file presence only; no live call")
    parser.add_argument("--device", action="store_true", help="probe dumpsys accessibility if available")
    parser.add_argument("--run-tests", action="store_true", help="run this package's unit tests")
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else root_from_env()
    envelope = collect(
        root,
        provider=args.provider,
        probe_device=args.device,
        run_tests=args.run_tests,
    )
    stored = None
    if not args.no_store:
        stored = write_status(root, envelope)
        envelope = dict(envelope)
        envelope["stored_at"] = str(stored)
    if args.json:
        print(json.dumps(envelope, indent=2, sort_keys=True))
    else:
        sys.stdout.write(status_prompt(envelope))
        if stored is not None:
            print(f"\nstored={stored}", file=sys.stderr)
    degraded = any((envelope.get("sections") or {}).get(name, {}).get("degraded") for name in ("git", "runtime"))
    return 2 if degraded else 0


if __name__ == "__main__":
    raise SystemExit(main())
