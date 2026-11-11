#!/usr/bin/env python3
"""Read-only, bounded GitHub PR inventory for safe Broccoli branch consolidation.

No checkout, merges, mutations, credential persistence, or feature-claim inference.
A base-branch reference is a *candidate* dependency, not proven merge ancestry.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
MAX_RECORDS = 1000


def _text(value: object, limit: int = 200) -> str:
    if not isinstance(value, str):
        raise ValueError("expected string")
    return " ".join(value.split())[:limit]


def fetch_open_prs(repo: str, token: str | None, max_pages: int = 10) -> list[dict]:
    """Fetch all visible open PRs; fail rather than silently truncate a large set."""
    if not REPO_PATTERN.fullmatch(repo):
        raise ValueError("expected GitHub owner/repository")
    if not 1 <= max_pages <= 10:
        raise ValueError("max_pages must be 1..10")
    collected: list[dict] = []
    for page in range(1, max_pages + 1):
        url = f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=100&page={page}"
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "Broccoli-portfolio-inventory/1"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=20) as response:
                page_data = json.load(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"GitHub PR inventory fetch failed (page {page}); no report emitted") from exc
        if not isinstance(page_data, list):
            raise ValueError("GitHub API did not return PR array")
        collected.extend(page_data)
        if len(collected) > MAX_RECORDS:
            raise ValueError("too many PRs, refusing partial output")
        if len(page_data) < 100:
            return collected
    raise ValueError("pagination limit hit; refusing incomplete report")


def normalize(repo: str, raw: list[dict]) -> list[dict]:
    if not REPO_PATTERN.fullmatch(repo) or not isinstance(raw, list):
        raise ValueError("invalid repo or PR list")
    if len(raw) > MAX_RECORDS:
        raise ValueError("PR inventory exceeds configured bound")
    result: list[dict] = []
    used: set[int] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("PR entry must be an object")
        number = item.get("number")
        if type(number) is not int or number <= 0 or number in used:
            raise ValueError("missing, invalid, or duplicate PR number")
        used.add(number)
        head, base = item.get("head"), item.get("base")
        if not isinstance(head, dict) or not isinstance(base, dict):
            raise ValueError("PR head/base missing")
        head_ref, base_ref = _text(head.get("ref")), _text(base.get("ref"))
        head_sha, base_sha = head.get("sha"), base.get("sha")
        if not head_ref or not base_ref or not isinstance(head_sha, str) or not SHA_PATTERN.fullmatch(head_sha):
            raise ValueError("invalid PR head")
        if base_sha is not None and (not isinstance(base_sha, str) or not SHA_PATTERN.fullmatch(base_sha)):
            raise ValueError("invalid PR base SHA")
        head_repo = head.get("repo")
        full_name = head_repo.get("full_name") if isinstance(head_repo, dict) else None
        result.append({
            "number": number,
            "title": _text(item.get("title", ""), 200),
            "draft": item.get("draft") is True,
            "base_ref": base_ref,
            "base_sha": base_sha,
            "head_ref": head_ref,
            "head_sha": head_sha,
            "same_repo_head": full_name == repo,
            "updated_at": _text(item.get("updated_at", ""), 48),
            "url": f"https://github.com/{repo}/pull/{number}",
            "possible_dependency_prs": [],
        })
    # Stacked branch detection is a hint only: no ancestry or compatibility check.
    branches: dict[str, list[int]] = {}
    for p in result:
        if p["same_repo_head"]:
            branches.setdefault(p["head_ref"], []).append(p["number"])
    for p in result:
        p["possible_dependency_prs"] = sorted(
            n for n in branches.get(p["base_ref"], []) if n != p["number"])
    return sorted(result, key=lambda p: p["number"])


def render_markdown(repo: str, records: list[dict]) -> str:
    def safe(x: object) -> str:
        return str(x).replace("|", "\\|").replace("[", "\\[").replace("]", "\\]").replace("`", "'")
    rows = [
        f"# Open PR and possible stacking inventory: {repo}",
        "",
        f"**Count:** {len(records)} open PRs.",
        "",
        "**Interpretation:** branch-name relationships are hints, **not proven Git ancestry or safe merge ordering**.",
        "No merge, release, production/deployment or approval has been executed by this report.",
        "",
        "| PR | Title | Head -> base | Draft | Potential parent PRs | SHA |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for p in records:
        deps = ", ".join(f"#{n}" for n in p["possible_dependency_prs"]) or "—"
        rows.append(f"| [#{p['number']}]({p['url']}) | {safe(p['title'])} | "
                    f"`{safe(p['head_ref'])}` → `{safe(p['base_ref'])}` | "
                    f"{'yes' if p['draft'] else 'no'} | {deps} | `{p['head_sha'][:12]}` |")
    rows += ["", "## Required next checks", "",
             "1. Confirm each potential parent is truly in the feature branch history using `git merge-base` and exact commits.",
             "2. Distinguish CI checks on feature branches from current main and from tested merge commits.",
             "3. Inspect policy/permission and release boundaries; reject unsafe mass merges.",
             "4. Record reviewer decisions and independent approvals separately from automated tests.",
             ""]
    return "\n".join(rows)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    p.add_argument("--fixture", type=Path, help="offline GitHub API response for regression tests")
    p.add_argument("--out", type=Path, required=True, help="output directory")
    p.add_argument("--max-pages", type=int, default=10)
    args = p.parse_args()
    if not REPO_PATTERN.fullmatch(args.repo):
        p.error("--repo must be owner/repository")
    raw = (json.loads(args.fixture.read_text(encoding="utf-8")) if args.fixture
           else fetch_open_prs(args.repo, os.getenv("GITHUB_TOKEN"), args.max_pages))
    records = normalize(args.repo, raw)
    data = {"schema_version": 1, "repository": args.repo, "state": "open",
            "evidence_scope": "GitHub PR metadata snapshot, not test or release evidence",
            "records": records}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "open-pr-inventory.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out / "open-pr-inventory.md").write_text(render_markdown(args.repo, records), encoding="utf-8")
    print(f"PR-INVENTORY OK: {len(records)} open PRs; output {args.out}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, RuntimeError) as error:
        print(f"PR-INVENTORY FAILED: {error}", file=sys.stderr)
        sys.exit(1)
