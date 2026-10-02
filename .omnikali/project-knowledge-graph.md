# OmniKali Cross-Repository Knowledge Graph

**GRAPH TAG:** OMNIKALI-KG-2026-09-28  
**Snapshot:** 2026-09-28 EDT

## Hierarchy
```
OMNIKALI
├── Public edge: omnikali
├── Control plane: helix
├── Reference/control contracts: Grasshopper
├── Persistent desktop: kali-node
├── Scalable desktop: grasshopper-kubernetes
├── Historical evidence: broccoli-core, GPTOmniKali-full-stack
├── Legacy edge: omnikali-link
└── Experimental/independent: kiln, lattice, publications, Shizuku projects
```

## Rules for future agents
1. Read this graph before cross-repository changes.
2. Treat live acceptance evidence as stronger than README claims.
3. Never replace validated production architecture with an unverified redesign.
4. Distinguish pod/process health from user-visible desktop health.
5. Preserve restore points before risky changes.
6. Use real authentication and real end-to-end acceptance, not synthetic sessions.
7. Record proven facts, observations, hypotheses, planned work, failures, recovery, and timestamps.
8. Update this graph in every affected repository after material architecture changes.
9. Do not infer implementation from repository names. Empty repositories remain empty until code and tests prove otherwise.
10. Resolve duplicate ownership before creating another implementation.

## Current evidence
Helix task lifecycle, PostgreSQL persistence, worker lease recovery, replacement-worker recovery, real Kali execution, and fencing/idempotency behavior have previously been exercised. Re-verify after changes.

**Canonical graph marker:** `OMNIKALI-KG-2026-09-28`

## Broccoli Android transport evidence — 2026-10-02

- Live RDC-to-Termux-to-Rish proof returned Android shell uid 2000, API 35, device a14xm. The fail-closed `lib/rish_transport_probe.sh` now routes through `RishTransport` and writes verifiable evidence to shared storage.
- scripts/autojs_run.py smoke passed against org.autojs.autojs.modify through the canonical RishTransport bridge.
- Transient AutoJS health failures were observed both as cold-start marker timeouts and a one-off Rish launch `Server is not running` result; the side-effect-free smoke probe now retries either case at most once, while read/fsm remain single-shot.
- Legacy AutoJS read/fsm payloads are currently absent and now fail fast; AutoJS remains optional behind the Rish/UIAutomator/accessibility path.
- Rooted full-suite validation (`python3 -m unittest discover -s tests -t . -v`) passed 136/136 tests on-device. The earlier discovery failure was import-path shadowing from `tests/runtime`, not missing production modules. CI is aligned to this rooted command.
