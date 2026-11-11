# Five-minute portfolio campaign observer

**Tracking:** [issue #108](https://github.com/onnxscibroccoli/broccoli-core/issues/108) · [master ledger #102](https://github.com/onnxscibroccoli/broccoli-core/issues/102)

This GitHub Actions workflow runs on a **best-effort five-minute cron** after its source is merged to `main`. It provides a bounded public repository status snapshot, not an LLM coding session or a mechanism to extend Grok, Grok Bot, or ChatGPT context/usage.

## Behavior

- Performs offline regression tests before reading any external state.
- Fetches issue #102 to see whether the campaign is open.
- If closed, stops after the single master-issue read. GitHub will still schedule a lightweight job until this workflow's cron is removed or disabled.
- If open, reads public PR and latest Actions run metadata for the seven flagship repositories only; private repository names and data are excluded.
- Writes exact observed metadata to the workflow **job summary**. A manual dispatch additionally publishes a short-retention JSON artifact.
- **Does not** write issues, push code, open PRs, trigger bots, charge model APIs, publish releases, access user devices, or auto-merge.

## Scheduling and limits

GitHub's `schedule` is best-effort, not a guaranteed five-minute clock. Scheduled runs may start late or occasionally be dropped. The cron is `*/5 * * * *` (UTC), which is approximately 288 runs/day. Although this is a small read-only workload with a three-minute timeout, it can consume significant runner minutes over time. Review GitHub Actions usage before enabling it indefinitely. No paid third-party services are invoked.

Only `main` schedules; a draft PR does **not** create a recurring trigger. The workflow is restricted to public repository paths and a maximum of 15 GitHub REST calls per non-closed run. It fails closed rather than silently truncating PR counts.

**Stop mechanism:** disable workflow in GitHub Actions or merge a PR removing `schedule`. Closing issue #102 causes minimal-state mode but does not stop scheduling altogether.

## Verification

Offline:

```sh
PYTHONPATH=. python3 -m unittest discover -s scripts/portfolio_watch/tests -v
```

Then, only after this PR is reviewed/merged, run `Actions → Portfolio Five-Minute Evidence Watch → Run workflow` and inspect the exact workflow summary and artifact. Compare open PR counts and CI status to GitHub UI. Confirm the first scheduled occurrence appears with `event=schedule`.

## Important distinctions

- A new green workflow means the **observer and its public API requests** succeeded, not that any engineering deliverable passed validation.
- The most recent CI run displayed for a repository might refer to a different branch from the current PR; never infer a PR's verified status from the latest run alone.
- The observer does not command Grok or Grok Bot and does not create a persistent ChatGPT session. Each agent must explicitly claim and execute tasks, then update #102 and its own PR.
- This observer cannot certify an actual production deployment, external reviewer approval, WCAG conformance, or job/employment experience.
