# Grasshopper philosophy pointer

Broccoli Core is the device executor and the older philosophy source. It is not the control plane.

## Current canonical knowledge

Cross-repository coordination:
- `omn-kali-knowledge-graph-master/docs/OMNIKALI_SYSTEM_KNOWLEDGE_GRAPH_2026-10-01.md`
- `omn-kali-knowledge-graph-master/docs/OMNIKALI_SYSTEM_GOALS_GRAPH_2026-10-01.md`
- `omn-kali-knowledge-graph-master/docs/BROCCOLI_ITERATION_KNOWLEDGE_2026-10-01.md`

Local philosophy:
- `docs/BROCCOLI_KNOWLEDGE_GRAPH.md` (`BROCCOLI-KG-2026-10-01`)
- `docs/BROCCOLI_IMPLEMENTATION_PHILOSOPHY.md`

## Non-negotiable transport invariant

The proven Android transport is:

`RDC/Termux -> broccoli-core -> lib/rish_run.sh -> Rish/Shizuku -> Android shell uid=2000`

Use:

`RISH_PRESERVE_ENV=0 bash ./lib/rish_run.sh ...`

The 2026-10-01 investigation proved the previous RDC failure was a reduced caller environment/non-TTY boundary problem, not evidence that the known-good Rish layer was broken.

Therefore:
- do not treat RC=0 with empty output as success
- do not assume RDC and interactive Termux share an environment
- do not copy the whole Termux environment into persistent state
- do not create another Rish wrapper
- do not modify the known-good Rish layer before reproducing the caller boundary
- prove success with a target artifact and identity, not exit code alone

## Philosophy to preserve

Adopt:
- cheap matcher/cascade before expensive providers
- one intent -> one schema
- dry-run -> execute -> event -> remember
- phone closes its own loop
- deterministic executor with replaceable model
- `.new -> self_test -> mv` promotion

Do not adopt:
- root log piles
- duplicate scripts
- placeholder milestone claims
- docs that only say "see chat"
- historical checkout modernization without an explicit goal
- chat-mediated paste-back as the Android execution loop

For detailed transport failures, supervisor recovery, MCP, UI automation, APK inspection, Morphe gates, and historical degradation lessons, read the canonical Broccoli iteration record above.
