# Grasshopper philosophy pointer

Broccoli Core is the device executor and the older philosophy source. It is not the control plane.

## Current canonical knowledge

Cross-repository coordination:
- `omn-kali-knowledge-graph-master/docs/OMNIKALI_SYSTEM_KNOWLEDGE_GRAPH_2026-10-01.md`
- `omn-kali-knowledge-graph-master/docs/OMNIKALI_SYSTEM_GOALS_GRAPH_2026-10-01.md`
- `omn-kali-knowledge-graph-master/docs/BROCCOLI_ITERATION_KNOWLEDGE_2026-10-01.md`
- `omn-kali-knowledge-graph-master/docs/BROCCOLI_TRANSPORT_CONTRACT_2026-10-01.md`
- `omn-kali-knowledge-graph-master/goals/broccoli-transport-preflight-2026-10-01.yml`

Local philosophy:
- `docs/BROCCOLI_KNOWLEDGE_GRAPH.md` (`BROCCOLI-KG-2026-10-01`)
- `docs/BROCCOLI_IMPLEMENTATION_PHILOSOPHY.md`

## Non-negotiable transport invariant

The proven Android transport is:

`RDC/Termux -> broccoli-core -> lib/rish_run.sh -> Rish/Shizuku -> Android shell uid=2000`

Use:

`RISH_PRESERVE_ENV=0 bash ./lib/rish_run.sh ...`

The wrapper on `main` fails closed:
- exit `2` if no command
- exit `79` if `rish` is missing
- exit `78` if `android-runtime.env` is missing and live `BOOTCLASSPATH` is absent
- `env -i` plus an allowlisted Android runtime snapshot when the env file exists
- `RISH_PRESERVE_ENV` defaults to `0`

Capture `~/.config/broccoli/rish/android-runtime.env` only from interactive Termux that already has `BOOTCLASSPATH`. Never capture it from a reduced RDC caller. A readable bad snapshot is preferred over the live shell.

The 2026-10-01 investigation proved the previous RDC failure was a reduced caller environment/non-TTY boundary problem, not evidence that the known-good Rish layer was broken.

Therefore:
- do not treat RC=0 with empty output as success
- do not assume RDC and interactive Termux share an environment
- do not copy the whole Termux environment into persistent state
- do not create another Rish wrapper
- do not modify the known-good Rish layer before reproducing the caller boundary
- prove success with a target artifact and identity, not exit code alone
- answer the transport preflight before repeating a Rish experiment

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

For detailed transport failures, supervisor recovery, MCP, UI automation, APK inspection, Morphe gates, and historical degradation lessons, read the canonical Broccoli iteration record and the transport contract above.
