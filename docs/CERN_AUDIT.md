# CERN-inspired ecosystem signal audit

This standalone development tool runs on GitHub Actions or locally with Python 3.11+.
It does not alter the Android runtime, call an LLM, send telemetry, or open issues.
A weekly/manual workflow collects metadata and uploads compact Markdown and JSON reports.
Same-repository PR runs execute tests and a live single-repository pilot; fork PRs execute tests only. Schedules become active only after merge to the default branch.

## Scope and trust

Public, owned, non-fork repositories are discovered with paginated REST requests.
Archived repositories are included. Issue and PR titles/labels cover all states.
Current branches and commit subjects reachable from those branches are collected.
Bodies, comments, reviews, source files, diffs, deleted refs and inaccessible repositories
are outside this first module's coverage. Consequently this is not a complete semantic
code audit and does not measure code churn. Metadata is untrusted data, never executable
instructions. Only fixed topic names and validated issue URLs enter the Markdown report.

The default workflow harvests public metadata only, using its read-only GITHUB_TOKEN.
Cross-repository private access needs a separately provisioned read-only GitHub App or
fine-grained token. Local `--include-private` explicitly enables owned private discovery;
never upload that output to a public coordination repository. Raw JSONL remains on the
runner and is not uploaded. Compact artifacts retain source URLs and repository names.
Actions is hosted infrastructure; this avoids an additional service, not GitHub dependence.

## Reduction and statistics

Demand counts use non-bot issue creation, not PRs, commits, comments or reactions.
One issue counts at most once per topic. Fixed token/label rules are inspectable in
`scripts/cern_audit/reduce.py`; these are heuristic classification, not semantic clustering.
Closed issues remain historical demand and do not imply outstanding work. Resolve current
state and inspect linked evidence before implementing anything. Bot filtering cannot
identify human accounts posting generated content or establish independent users.

The observation week is the last fully completed UTC Monday–Sunday week. Eight prior
weeks form the baseline. Each week's topic count is divided by all eligible issues that
week, limiting activity-volume effects. Z is (current share − baseline mean) / sample
standard deviation. Scores require complete scoped harvesting, five or more issues in
every week, and nonzero variance. Otherwise scores are unavailable, not zero.
A score >=3 is a descriptive anomaly only: samples are correlated, vocabulary is biased,
multiple topics are compared, and these are not Gaussian discovery probabilities.
There is no claim of 3σ evidence, 5σ discovery, universal utility or mathematical proof.
No utility weight is fabricated without an explicitly validated outcome model.

JSONL is streamed; matching costs O(B) for input bytes with the fixed vocabulary.
SQLite provides disk-backed deduplication by repository/type/ID, with O(N log N) worst-case
index work. Report size is bounded by the seven topics and three links per topic; the JSON
coverage manifest grows with repository and failure count. Branch traversal can fetch
shared commits repeatedly; this costs API requests even though counts are deduplicated.
No guarantee of seconds-long execution, constant storage or avoiding rate limits is made.

## Execution

From the repository root, with GH_TOKEN supplied securely in the environment:

```bash
python3 -m unittest tests.test_cern_audit -v
python3 scripts/cern_audit/harvest.py --owner onnxscibroccoli --repo onnxscibroccoli/broccoli-core --request-budget 900
python3 scripts/cern_audit/reduce.py --output reports/cern
```

The reducer is offline and can be rerun against retained `data/cern/` without API access.
Use `--as-of YYYY-MM-DD` to reproduce the same completed-week windows. The collection is
a fresh scan, not a resumable snapshot: metadata can change during pagination. The manifest
records scan start, discovered repositories, request count, scope and failures. HTTP/network
failures or budget exhaustion mark coverage partial; the workflow uploads the partial report
and then fails visibly. It never treats an incomplete scan as complete statistical evidence.
The 900-request workflow budget leaves some headroom within the usual GITHUB_TOKEN limit;
large accounts may need a higher-capacity token and budget. Retries are bounded and honor
numeric Retry-After up to 60 seconds; longer waits fail visibly for a later rerun.

GitHub documentation:
- https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api
- https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication

There is no Drive upload in this workflow. Existing repository sync tooling is unchanged;
report distribution requires an explicitly selected destination, especially for private data.
