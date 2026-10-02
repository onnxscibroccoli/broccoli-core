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


## 2026-10-01 Ruto virtual-display evidence

**PROVEN on live Samsung Android hardware**

- Ruto creates private displays through Android `VirtualDisplayAdapter`; shell overlay-display settings are the wrong mechanism.
- Ruto's privileged service launches apps with `ActivityOptions.setLaunchDisplayId` through a display-scoped Context and PendingIntent.
- Ruto's own flow produced a live Grok process, task, drawn/visible window, and SurfaceFlinger layers on virtual display 30.
- Direct `am start --display` is **DISPROVEN** as an equivalent attachment mechanism. Repeated tests produced task-only/stale states and could terminate the provider process/display lifecycle.
- Broccoli now has a provider-agnostic Ruto-backed surface adapter with five-part readiness evidence and fail-closed recovery.
- Final end-to-end recovery/ensure testing is pending restoration of the phone's Shizuku/Rish bridge after it reported `Server is not running`.

**Production invariant:** never report a provider surface ready from ActivityManager task presence alone.
