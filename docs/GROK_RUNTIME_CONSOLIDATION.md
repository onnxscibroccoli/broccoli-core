# Broccoli Core Runtime Consolidation Analysis

**Agent:** Grok (Principal Systems Architect)
**Date:** 2026-11-11
**Status:** IN_PROGRESS — SOURCE_PRESENT / STATIC_CHECKED
**Tracks:** [#102](https://github.com/onnxscibroccoli/broccoli-core/issues/102) [#105](https://github.com/onnxscibroccoli/broccoli-core/issues/105) [#104](https://github.com/onnxscibroccoli/broccoli-core/pull/104) [#106](https://github.com/onnxscibroccoli/broccoli-core/pull/106)

## Facts (from inspected source)

- Main HEAD `runtime/kernel.py` implements Kernel with IntentSchemaEngine, OnnxIntentClassifier, AutomationEngine.
- EventBus import prefers `runtime.eventbus.bus` with fallback to `runtime.event_bus`.
- Dry-run default; fail-closed on schema resolution.
- Inventory PR #106 (branch `feat/portfolio-pr-inventory-20261111`, SHA `6204fb869bb897339357f224e0f1ff06bfc55fc7`) provides deterministic read-only PR inventory tooling and CI artifacts. Initial CI tests passed per campaign notes.
- Readiness PR #104 documents reviewer path and maturity boundaries (docs only).
- Multiple open PRs exist for vector memory (#53-#55), Rish/Ruto surfaces (#67), Parallax APKs (#72/#73), etc. Stacked bases present; no mass merge authorized.

## Assumptions

- Latest timestamp does not equal best implementation.
- Canonical runtime should support non-root Android, explicit authorization, provider-agnostic AI, event-driven communication, fail-closed governance.
- Extraction to separate `broccoli-runtime` repo deferred until boundary and tests established.

## Recommendations

1. Use inventory tooling from #106 to generate dependency graph of open PRs.
2. Compare kernel/eventbus implementations across active feature branches for correctness and compatibility.
3. Identify single authoritative module per capability (kernel, event bus, governor, providers, Android transport).
4. Open narrowly scoped PRs for repairs; never automatic mass merge.
5. Preserve provenance of historical artifacts.

## Verification Record

Repository: onnxscibroccoli/broccoli-core
Branch: agent/grok-broccoli-runtime-consolidation-20261111
Commit SHA: (this commit)
Test command: (none yet; analysis)
Environment: GitHub API inspection
Expected result: Documented current state
Observed result: Kernel and inventory tooling source retrieved
Evidence URL: this file + linked PRs
Remaining limitations: Full branch-by-branch comparison and live device tests NOT_VERIFIED. Human review required for extraction boundary.

## Next Actions

- Generate PR inventory report via workflow if #106 merged or dispatchable.
- Inspect Grasshopper control-plane and Helix lineage for cross-repo dependencies.
- Claim next independent task if this analysis is accepted.
