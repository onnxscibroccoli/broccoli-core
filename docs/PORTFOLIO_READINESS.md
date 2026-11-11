# Portfolio reviewer readiness — broccoli-core

> **Status:** Reviewable documentation plan, not a production certification. **As of:** 2026-11-11. **Tracking:** [local issue](https://github.com/onnxscibroccoli/broccoli-core/issues/103) · [cross-repository ledger](https://github.com/onnxscibroccoli/broccoli-core/issues/102).  
> Do not interpret AI-assisted source development, successful offline tests or simulations as independently verified industry employment, compliance, or live operations.

## One-minute technical orientation

**Focus:** Accessibility-first Android automation and historical runtime. An extensive experimental Android/Termux runtime with event-bus implementations, semantic accessibility drivers, provider adapters, Shizuku/Rish access, and application-specific development branches.

**What is demonstrable:** The listed source files and explicitly scoped CI runs can be inspected. A reviewer can evaluate the code, rerun supported unit tests, and challenge the architecture decisions. Any claimed practical capability requires the corresponding test, environment, and source revision; not all systems are integrated or generally available.

## Source and reviewer starting points

| Evidence | Path |
| --- | --- |
| Intent-to-action kernel | [Inspect](https://github.com/onnxscibroccoli/broccoli-core/blob/main/runtime/kernel.py) |
| Android governor boundary tests | [Inspect](https://github.com/onnxscibroccoli/broccoli-core/blob/main/tests/test_android_governor_boundary.py) |
| Reference Python CI | [Inspect](https://github.com/onnxscibroccoli/broccoli-core/blob/main/.github/workflows/ci.yml) |
| Main README | [Inspect](https://github.com/onnxscibroccoli/broccoli-core/blob/main/README.md) |

## Executed CI references (historical, scoped)

| Check | Exact run |
| --- | --- |
| Parallax v2.2 APK branch build | [Run 42961641966](https://github.com/onnxscibroccoli/broccoli-core/actions/runs/42961641966) |
| Parallax branch Python CI | [Run 42961641965](https://github.com/onnxscibroccoli/broccoli-core/actions/runs/42961641965) |

These run links refer to the specific branch/commit shown on GitHub. They must not be silently attributed to a different current HEAD, production environment, device or approval state.

## Reproduce the relevant local checks

After cloning the repository and reviewing dependencies and safe environment requirements:

```sh
python3 -m unittest discover -s tests -t . -v
```

This is a **documented command**, not a claim that this portfolio PR executed it. Some modules require dependencies or privileges, and a missing dependency must be reported rather than converted into a false PASS.

## Ordered actionable changes

1. [ ] Inventory active PRs, branches, ancestry and overlapping runtime packages; do not merge solely by newest timestamp.
2. [ ] Map each capability to one canonical implementation and matching test, treating historical mirrors/logs as provenance only.
3. [ ] Add explicit reviewer quickstart and fail-closed action-governance example.
4. [ ] Separate Accubook/Parallax release concerns from the core Android automation runtime.
5. [ ] Scan historical logs/snapshots and unexpected artifacts before any public redistribution; never publish credentials.
6. [ ] Extract a clean broccoli-runtime repository only after design boundary and tests are validated.

## Maturity and verification boundary

Main includes a large historic/experimental corpus. Successful feature-branch APK builds prove compilation, not live device permission acquisition, cross-branch integration or production readiness.

## Release and artifact strategy

Use separate versioned APK releases for standalone apps with source SHA, test run, checksums and package name. Broccoli runtime needs a reproducible non-root package and an authorized live device test.

## Safe continuation after interruption

1. Follow the local issue and the [master execution ledger](https://github.com/onnxscibroccoli/broccoli-core/issues/102); inspect existing PRs before creating new ones.
2. Check `git rev-parse HEAD`, repo default branch, current feature branches and fresh Actions conclusions.
3. For each checklist item, implement the smallest change on a reviewable PR; record exact SHA, test scope, successes, failed/untested checks and outstanding decisions.
4. Keep a previously failing independent-approval requirement or live-device gate unresolved until a legitimately authorized actor/environment supplies evidence.
5. Re-read this document against source after changing implementation. Do **not** mark a checklist item complete merely because it is documented.

**Human-only / outside repository assertions:** employment history, professional tenure, team-management responsibilities, third-party audit and approvals.