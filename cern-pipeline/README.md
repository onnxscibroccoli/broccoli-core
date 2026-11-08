# CERN GitHub Signal Pipeline

Local-first, zero-infrastructure edge reduction for multi-repo GitHub presence.

## Architecture

```
[ Repos / Issues / PRs / Branches ]
              │
              ▼  (GitHub Actions runner)
[ harvest_github.py ]  → data/raw/*.json
              │
              ▼  O(N) stream
[ cern_reducer.py ]    → cern_signal_report.md
              │
              ▼
[ LLM / Autonomous agent ]
```

## Usage

1. This pipeline lives on the `cern-signal-pipeline` branch of broccoli-core.
2. Trigger the workflow manually (Actions → CERN GitHub Signal Audit → Run workflow) or let the weekly cron run.
3. Download the `cern-signal-report` artifact. It contains `cern_signal_report.md` (the only file an LLM should ingest) plus the raw JSON for debugging.

## Design Notes

- **Edge compute**: All heavy lifting stays on the runner. LLM only sees the final Markdown.
- **Linear time**: Single pass over harvested JSON; pandas vectorized Z-score.
- **Baseline**: Empirical distribution of topic frequencies in the current snapshot. For true historical Z-scores, store previous reports and diff.
- **Topic extraction**: Lightweight word frequency. Replace with embeddings or LLM-assisted clustering if needed later.
- **Rate limits**: `gh` CLI handles pagination and retries better than raw API for this scale.
- **Private repos**: Works with the default `GITHUB_TOKEN` when the workflow lives in a repo the token can see; for cross-repo private access use a PAT secret.

## Next Steps

- Persist historical snapshots for true time-series baselines.
- Add commit churn / branch metrics.
- Optional post-step that opens a summary issue or pings an agent.
