#!/usr/bin/env python3
"""Thin client for broccoli-do-spike (C1)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT = os.environ.get(
    "SPIKE_URL", "https://broccoli-do-spike.onnxscibroccoli.workers.dev"
)


def req(method: str, url: str, body: dict | None = None) -> dict:
    data = None
    headers = {"accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["content-type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode() if e.fp else str(e)
        try:
            return json.loads(raw)
        except Exception:
            return {"ok": False, "error": raw or str(e)}


def main() -> int:
    p = argparse.ArgumentParser(description="Broccoli DO thin client")
    p.add_argument("--url", default=DEFAULT)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("health")

    c = sub.add_parser("write")
    c.add_argument("path")
    c.add_argument("content")

    c = sub.add_parser("read")
    c.add_argument("path")

    c = sub.add_parser("ls")
    c.add_argument("path", nargs="?", default="/workspace")

    c = sub.add_parser("task-create")
    c.add_argument("--goal", required=True)
    c.add_argument("--domain", required=True)
    c.add_argument("--id")
    c.add_argument("--notes", default="")

    c = sub.add_parser("task-get")
    c.add_argument("id")

    sub.add_parser("task-list")

    c = sub.add_parser("task-patch")
    c.add_argument("id")
    c.add_argument("--status")
    c.add_argument("--notes")

    c = sub.add_parser("receipt")
    c.add_argument("id")
    c.add_argument("--summary", required=True)
    c.add_argument("--github-ref", default="")

    args = p.parse_args()
    base = args.url.rstrip("/")

    if args.cmd == "health":
        out = req("GET", base + "/")
    elif args.cmd == "write":
        out = req("POST", base + "/write", {"path": args.path, "content": args.content})
    elif args.cmd == "read":
        q = urllib.parse.urlencode({"path": args.path})
        out = req("GET", f"{base}/read?{q}")
    elif args.cmd == "ls":
        q = urllib.parse.urlencode({"path": args.path})
        out = req("GET", f"{base}/ls?{q}")
    elif args.cmd == "task-create":
        body = {"goal": args.goal, "domain": args.domain, "notes": args.notes}
        if args.id:
            body["id"] = args.id
        out = req("POST", base + "/task", body)
    elif args.cmd == "task-get":
        q = urllib.parse.urlencode({"id": args.id})
        out = req("GET", f"{base}/task?{q}")
    elif args.cmd == "task-list":
        out = req("GET", base + "/tasks")
    elif args.cmd == "task-patch":
        body = {"id": args.id}
        if args.status:
            body["status"] = args.status
        if args.notes is not None:
            body["notes"] = args.notes
        out = req("PATCH", base + "/task", body)
    elif args.cmd == "receipt":
        out = req(
            "POST",
            base + "/receipt",
            {"id": args.id, "summary": args.summary, "github_ref": args.github_ref or None},
        )
    else:
        print("unknown", file=sys.stderr)
        return 2

    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
