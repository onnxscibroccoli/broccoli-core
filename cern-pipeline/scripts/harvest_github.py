#!/usr/bin/env python3
"""
CERN-style edge harvester for GitHub ecosystem metadata.
Uses GitHub CLI (gh) for authenticated, rate-limit-aware pagination.
Dumps issues, PRs, and basic commit stats to flat JSON files.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

OWNER = os.environ.get("GITHUB_OWNER", "")
if not OWNER:
    print("GITHUB_OWNER not set", file=sys.stderr)
    sys.exit(1)

RAW = Path("data/raw")
RAW.mkdir(parents=True, exist_ok=True)


def run_gh(args: list[str]) -> str:
    """Run gh CLI and return stdout. Fails hard on error."""
    cmd = ["gh"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        print(f"gh failed: {result.stderr}", file=sys.stderr)
        raise RuntimeError(result.stderr)
    return result.stdout


def list_repos() -> list[dict]:
    """List all repos for the owner (public + private visible to token)."""
    raw = run_gh([
        "repo", "list", OWNER,
        "--limit", "100",
        "--json", "name,isPrivate,description,updatedAt,url"
    ])
    return json.loads(raw)


def harvest_issues_prs(repo: str) -> tuple[list, list]:
    """Harvest open + closed issues and PRs with pagination via gh."""
    # Issues (includes PRs in GitHub API, but we separate)
    issues_raw = run_gh([
        "issue", "list",
        "--repo", f"{OWNER}/{repo}",
        "--state", "all",
        "--limit", "500",
        "--json", "number,title,body,state,createdAt,updatedAt,labels,comments,author"
    ])
    issues = json.loads(issues_raw) if issues_raw.strip() else []

    prs_raw = run_gh([
        "pr", "list",
        "--repo", f"{OWNER}/{repo}",
        "--state", "all",
        "--limit", "500",
        "--json", "number,title,body,state,createdAt,updatedAt,labels,comments,author,mergeable"
    ])
    prs = json.loads(prs_raw) if prs_raw.strip() else []

    return issues, prs


def main():
    print(f"Harvesting ecosystem for {OWNER}")
    repos = list_repos()
    print(f"Found {len(repos)} repositories")

    all_issues = []
    all_prs = []

    for r in repos:
        name = r["name"]
        print(f"  → {name}")
        try:
            issues, prs = harvest_issues_prs(name)
            for i in issues:
                i["_repo"] = name
            for p in prs:
                p["_repo"] = name
            all_issues.extend(issues)
            all_prs.extend(prs)
        except Exception as e:
            print(f"    WARN: skipped {name}: {e}")

    # Write flat files
    (RAW / "repos.json").write_text(json.dumps(repos, indent=2))
    (RAW / "issues.json").write_text(json.dumps(all_issues, indent=2))
    (RAW / "prs.json").write_text(json.dumps(all_prs, indent=2))

    print(f"Harvest complete: {len(all_issues)} issues, {len(all_prs)} PRs")


if __name__ == "__main__":
    main()
