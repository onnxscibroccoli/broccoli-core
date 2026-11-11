# Reviewable open-PR dependency inventory

**Purpose:** When dozens of Broccoli Core PRs use non-main bases, reviewers need an accurate snapshot of the proposed merge structure before attempting consolidation. This module is read-only and executes entirely inside GitHub Actions.

## What it does

- Queries all currently visible open PRs using paginated GitHub REST (100/page, hard maximum 1,000).
- Records number, title, draft state, current head/base refs and SHAs, and updated time.
- Marks a **possible** stacked dependency when one PR's base branch matches another same-repository open PR's head branch.
- Produces both machine-readable JSON and a Markdown reviewer table.
- Fails closed for malformed input, duplicate numbers, API errors or pagination truncation.

**What it does not do:** checkout PR code, prove Git ancestry, calculate mergeability, merge branches, change issues, release binaries, certify tests, or use cloud/device authority.

## Quick local verification

```sh
PYTHONPATH=. python3 -m unittest discover -s scripts/portfolio/tests -v
# Synthetic file mode; replace input.json with a GitHub pull-request API array:
python3 scripts/portfolio/pr_inventory.py \
  --repo onnxscibroccoli/broccoli-core --fixture input.json --out /tmp/broccoli-pr-map
```

## Reproducible GitHub Actions execution

After this PR is reviewed and merged to the default branch, use **Actions → Broccoli Portfolio PR Inventory → Run workflow**. The workflow runs unit regressions first. On a manual dispatch, it fetches PR metadata with the workflow token's `pull-requests: read` permission, attaches a dated workflow artifact named `portfolio-open-pr-inventory-<sha>`, and appends the table to the job summary.

The artifact filename uses the **workflow source SHA**. Each record includes the **PR head SHA**. Neither is evidence of a successful feature merge; they only identify the scope of the metadata snapshot.

Do not install personal tokens or expose private environment state.

## Consolidation reviewer procedure

1. For each candidate parent relationship, use `git merge-base` / `git log` to prove ancestry, and inspect the full diff.
2. Evaluate tests for the exact candidate head and the tested merge commit; prefer a verified canonical module, not simply the newest feature branch.
3. Resolve conflicts and side-effect authorization explicitly.
4. Extract Accubook and Parallax into their separately tested owners when safe.
5. Request a genuinely independent reviewer for policies that require one. Do not bypass the acceptance gate.

Tracker: https://github.com/onnxscibroccoli/broccoli-core/issues/105. Parent program: https://github.com/onnxscibroccoli/broccoli-core/issues/102.

**Publication status:** Proposed workflow and tests only until GitHub Actions reports a successful run on this specific PR.
