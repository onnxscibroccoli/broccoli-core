#!/usr/bin/env python3
"""Paper trading bootstrap: portfolio + rules on DO, first paper task."""
from __future__ import annotations
import json, os, time, urllib.request
from datetime import datetime, timezone

SPIKE = os.environ.get("SPIKE_URL", "https://broccoli-do-spike.onnxscibroccoli.workers.dev").rstrip("/")
START_CASH = float(os.environ.get("PAPER_CASH", "10000"))

def http(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        SPIKE + path, data=data, method=method,
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    portfolio = {
        "cash": START_CASH,
        "currency": "USD",
        "positions": [],
        "peak_equity": START_CASH,
        "equity": START_CASH,
        "drawdown_pct": 0.0,
        "updated_at": now(),
        "mode": "paper",
    }
    rules = """# Paper trading rules
- Paper only until explicit live unlock
- Max single position: 25% of equity
- Log rationale on every fill
- needs_user before any real money
- Gemini Live must read portfolio.json + receipts first
"""
    http("POST", "/write", {"path": "finance/portfolio.json", "content": json.dumps(portfolio, indent=2) + "\n"})
    http("POST", "/write", {"path": "finance/rules.md", "content": rules})

    t = http("POST", "/task", {
        "goal": "Bootstrap paper portfolio and stand ready for first simulated trade",
        "domain": "paper_trading",
        "status": "running",
        "notes": f"Starting cash {START_CASH} USD",
    })
    task = t["task"]
    tid = task["id"]

    http("POST", "/receipt", {
        "id": tid,
        "summary": f"Paper portfolio initialized at {START_CASH} USD cash, 0 positions. Rules written. Ready for paper orders.",
    })
    http("PATCH", "/task", {
        "id": tid,
        "status": "done",
        "artifacts": [
            {"path": "/workspace/finance/portfolio.json", "kind": "portfolio"},
            {"path": "/workspace/finance/rules.md", "kind": "rules"},
        ],
    })
    print(json.dumps({"ok": True, "task_id": tid, "cash": START_CASH, "portfolio": "/workspace/finance/portfolio.json"}, indent=2))

if __name__ == "__main__":
    main()
