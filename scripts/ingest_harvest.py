#!/usr/bin/env python3
"""Embed data/harvest JSONL into the local vector store."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.ingest.harvest import embed_harvest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ingest-harvest")
    parser.add_argument(
        "harvest_root",
        nargs="?",
        default=str(ROOT / "data" / "harvest"),
        help="Harvest directory or JSONL file",
    )
    parser.add_argument("--store-root", default="", help="Vector store directory")
    parser.add_argument("--provider", default="", help="Optional adapter name")
    args = parser.parse_args(argv)
    store = Path(args.store_root) if args.store_root else None
    result = embed_harvest(
        args.harvest_root,
        store_root=store,
        provider=args.provider or None,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
