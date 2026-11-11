#!/usr/bin/env python3
"""Five-minute *read-only* portfolio campaign observer.

This is not an autonomous coding agent. It reports public GitHub state only.
GitHub cron is best-effort; a run may be delayed or dropped.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

OWNER = "onnxscibroccoli"
MASTER_REPO = "broccoli-core"
MASTER_ISSUE = 102
# Public original repositories only. Do not add private repos to this workflow.
REPOS = (
    "bank-it-operations-lab", "Grasshopper", "broccoli-core",
    "helix", "accubook", "TCL-orc", "civicpatch",
)
API = "https://api.github.com/repos"
MAX_PRS = 99  # fail if result may be truncated, rather than reporting wrong totals
REQUEST_BUDGET = 1 + (len(REPOS) * 2)


def api_json(url: str, token: str | None) -> object:
    if not url.startswith(f"{API}/{OWNER}/"):
        raise ValueError("API request not on allowlisted owner")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "broccoli-portfolio-watchdog/1",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urlopen(Request(url, headers=headers), timeout=10) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Read-only GitHub state unavailable at {url.split('?')[0]}") from exc


def evaluate(master: dict, states: dict, at: str) -> dict:
    if not isinstance(master, dict) or master.get("number") != MASTER_ISSUE:
        raise ValueError("master issue response malformed")
    state = master.get("state")
    if state not in ("open", "closed"):
        raise ValueError("master issue state missing")
    if state == "closed":
        if states:
            raise ValueError("closed campaign must not fetch additional repositories")
        return {
            "status": "CAMPAIGN_CLOSED", "checked_at": at, "master_issue": MASTER_ISSUE,
            "repos": [], "observation_only": True,
            "limitations": "Scheduled workflow still starts until cron is removed; no agent execution is implied.",
        }
    if set(states) != set(REPOS):
        raise ValueError("incomplete public flagship snapshot")
    items = []
    for repo in REPOS:
        obj = states[repo]
        prs, runs = obj.get("prs"), obj.get("runs")
        if not isinstance(prs, list) or len(prs) > MAX_PRS:
            raise ValueError(f"{repo}: PR result invalid or truncated")
        if not isinstance(runs, list):
            raise ValueError(f"{repo}: workflow run list invalid")
        for pr in prs:
            if not isinstance(pr, dict) or not isinstance(pr.get("number"), int):
                raise ValueError(f"{repo}: malformed PR entry")
            if pr.get("state") != "open":
                raise ValueError(f"{repo}: unexpected PR state")
        latest = None
        if runs:
            x = runs[0]
            if not isinstance(x, dict):
                raise ValueError(f"{repo}: workflow run malformed")
            latest = {
                "workflow": str(x.get("name") or "")[:100],
                "status": str(x.get("status") or "unknown")[:40],
                "conclusion": x.get("conclusion"),
                "head_branch": str(x.get("head_branch") or "")[:120],
                "head_sha": str(x.get("head_sha") or "")[:40],
                "url": str(x.get("html_url") or "")[:250],
            }
        items.append({
            "repository": f"{OWNER}/{repo}",
            "open_pr_count": len(prs),
            "draft_pr_count": sum(pr.get("draft") is True for pr in prs),
            "latest_workflow": latest,
        })
    return {
        "status": "OBSERVED_OPEN_CAMPAIGN",
        "checked_at": at,
        "master_issue": MASTER_ISSUE,
        "master_updated_at": str(master.get("updated_at") or "")[:48],
        "repos": items,
        "observation_only": True,
        "limitations": (
            "Open PR counts do not measure completed engineering. "
            "Latest CI runs may be on different branches than PRs; no production verification is inferred. "
            "Cron can be delayed or skipped; this monitor does not trigger LLM agents."
        ),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Portfolio five-minute public evidence snapshot",
        "",
        f"**Checked:** {report['checked_at']}",
        f"**State:** {report['status']}",
        "",
        "**This is monitoring, not continuous coding.** The watcher neither runs LLMs nor "
        "creates commits, approves PRs, publishes releases or modifies production.",
        "",
    ]
    if report["status"] == "OBSERVED_OPEN_CAMPAIGN":
        lines.extend([
            "| Public repo | Open PRs | Draft | Latest observed workflow / branch | Conclusion |",
            "| --- | ---: | ---: | --- | --- |",
        ])
        for row in report["repos"]:
            run = row["latest_workflow"]
            if run:
                name = run["workflow"].replace("|", "/")
                branch = run["head_branch"].replace("|", "/")
                ci = f"[{name}]({run['url']}) on `{branch}`"
                result = str(run["conclusion"] or run["status"]).replace("|", "/")
            else:
                ci, result = "No returned run", "NOT_VERIFIED"
            repo = row["repository"]
            lines.append(
                f"| [{repo}](https://github.com/{repo}) | {row['open_pr_count']} | "
                f"{row['draft_pr_count']} | {ci} | {result} |"
            )
    lines.extend([
        "", f"**Limitations:** {report['limitations']}",
        "",
        f"[Resumption ledger](https://github.com/{OWNER}/{MASTER_REPO}/issues/{MASTER_ISSUE})",
        "",
    ])
    return "\n".join(lines)


def observe(token: str | None, timestamp: str) -> dict:
    count = 0
    def get(url: str) -> object:
        nonlocal count
        count += 1
        if count > REQUEST_BUDGET:
            raise ValueError("GitHub API request budget exceeded")
        return api_json(url, token)

    master = get(f"{API}/{OWNER}/{MASTER_REPO}/issues/{MASTER_ISSUE}")
    if not isinstance(master, dict):
        raise ValueError("master response invalid")
    if master.get("state") == "closed":
        return evaluate(master, {}, timestamp)
    states = {}
    for repo in REPOS:
        prefix = f"{API}/{OWNER}/{repo}"
        pulls = get(prefix + "/pulls?state=open&per_page=100")
        runs = get(prefix + "/actions/runs?per_page=1")
        if not isinstance(runs, dict) or not isinstance(runs.get("workflow_runs"), list):
            raise ValueError(f"{repo}: malformed Actions response")
        states[repo] = {"prs": pulls, "runs": runs["workflow_runs"]}
    return evaluate(master, states, timestamp)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, help="Offline JSON fixture with master/states keys")
    parser.add_argument("--json-out", type=Path, help="Optional output snapshot, for manual dispatch")
    parser.add_argument("--summary", type=Path, help="Optional GitHub Step Summary path")
    args = parser.parse_args()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if args.fixture:
        bundle = json.loads(args.fixture.read_text(encoding="utf-8"))
        report = evaluate(bundle["master"], bundle["states"], now)
    else:
        report = observe(os.getenv("GITHUB_TOKEN"), now)
    content = markdown(report)
    print(content)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        args.summary.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, RuntimeError, OSError) as exc:
        print(f"PORTFOLIO WATCH FAILED CLOSED: {exc}", file=sys.stderr)
        sys.exit(1)
