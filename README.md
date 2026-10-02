# Broccoli Core

**Status:** Active historical automation platform / experimental runtime  
**Repository:** `onnxscibroccoli/broccoli-core`  
**Documentation snapshot:** 2026-09-28 23:12 EDT

Broccoli Core is the oldest and largest automation-oriented repository in this account. It contains an Android/Termux-centric agent runtime, local execution kernel, provider integrations, UI observation, agent state, operational tooling, and a very large historical mirror.

It is **not the current canonical OmniKali production implementation**. New production work should inspect Helix, Grasshopper, and grasshopper-kubernetes first.

## Core execution model

The documented kernel is:

```
text → classify → resolve schema → execute → confirm
```

The repository exposes a direct local smoke invocation:

```bash
python -c "from runtime.kernel import Kernel; print(Kernel().tick('turn on bluetooth'))"
```

The project also contains a provider-agnostic problem-solving pipeline and managed transports for accessibility, clipboard, provider, workflow, planning, knowledge, agent coordination, and plugins.

## Contents

The tree contains roughly **5,900 entries**, far more than a normal application repository. Major areas include:

- `runtime/` — kernel/runtime implementation.
- `Agent/Broccoli/` — agent source, bootstrap, worker, context, tools, and state.
- `Agent/Broccoli/mirror/` — large historical Android/Termux automation mirror.
- `Agent/Broccoli/docs/` — tool and workflow documentation.
- `Agent/Broccoli/meta/` — queues, iteration state, health, task metadata, and operational records.
- `.github/workflows/` — CI and edge workflows.
- historical `runs/`, `done/`, `fail/`, UI captures, diagnostics, and generated artifacts.

Some historical paths look like credential or secret-storage locations. **Never expose or publish credential material.** The repository's existence does not mean every historical artifact is safe to redistribute.

## Development cycle

**MATURE PROTOTYPE / HISTORICAL PLATFORM.**

Recent September 2026 commits still touch the runtime and observer/Watch-Me-Do work, but the repository has accumulated years-equivalent experimental state and mirrors. It should therefore be maintained by provenance, not by indiscriminate cleanup.

The engineering rule is: **extract, preserve, and selectively reuse.**

## How to use it

For kernel experiments:

```bash
cd broccoli-core
python -c "from runtime.kernel import Kernel; print(Kernel().tick('turn on bluetooth'))"
```

For the documented Termux provider path:

```bash
cd "$HOME/broccoli-core"
chmod +x bin/broccoli bin/xai-oauth bin/brocc
./bin/broccoli status
./bin/broccoli ping
./bin/broccoli ask "Say hello from Broccoli Core."
```

OAuth setup is documented through `bin/xai-oauth`. Keep credentials outside Git.

## AI model instructions

Before changing anything, classify the target:

1. current runtime;
2. provider integration;
3. Android/Termux automation;
4. historical state;
5. mirror/provenance;
6. documentation.

Never treat generated state, queues, logs, captures, or mirror artifacts as authoritative source without verifying their provenance.

For OmniKali work, compare the requested change against Helix/Grasshopper before copying architecture forward.

A model should use the sequence:

**inspect → establish provenance → reproduce a narrow behavior → test → document → modify.**

Do not recursively “clean” this repository. Doing so can destroy the evidence that explains later architecture.

## What this repository proves

It proves that substantial local agent/runtime and Android automation code exists, that a local kernel model is implemented, that provider integration exists, and that extensive operational tooling was developed.

It does **not**, by itself, prove current production availability, current credentials, current device state, or equivalence with the current OmniKali production system.

**Bottom line:** Broccoli Core is an important ancestor and experimental laboratory for the agent-control lineage, not the current production source of truth.


## Cross-Repository Knowledge Graph

**GRAPH TAG: `OMNIKALI-KG-2026-09-28`**

This repository participates in the OmniKali cross-project knowledge graph. **Future AI agents MUST read the graph before making cross-repository architectural changes.** It records repository ownership, dependencies, validated evidence, known failure modes, development state, and consolidation rules.

Graph file: [`.omnikali/project-knowledge-graph.md`](.omnikali/project-knowledge-graph.md)

**Agent rule:** do not treat this README or repository name as proof of runtime capability. Verify against tests, acceptance evidence, production contracts, and live behavior. Preserve restore points before risky changes, make the smallest atomic change, record evidence and timestamps, and update the graph whenever architecture, ownership, dependencies, proof, or failure knowledge changes.

## Android / Termux transport status (2026-10-02)

On the Samsung Android 15 device, privileged Android automation from Remote Desktop Commander must use `tools.android_transport.RishTransport`. RDC/background children can lack Android runtime variables such as `BOOTCLASSPATH`; direct `rish` calls from that reduced environment can return misleading results. `RishTransport` re-enters the full Termux context through `RunCommandService` and then invokes the canonical `lib/rish_run.sh` wrapper.

AutoJS remains an **optional** adapter. The installed default package is `org.autojs.autojs.modify`. Verify the package/activity/transport without Grok-specific payloads with:

```bash
cd "$HOME/broccoli-core"
python3 scripts/autojs_run.py smoke
```

The legacy `read` and `fsm` modes require `/sdcard/broccoli/autojs/grok_read_chat.js` and `/sdcard/broccoli/autojs/grok_button_fsm.js`. If those payloads are absent, the adapter now fails immediately instead of waiting for an output file that cannot be produced. The primary production-capable Android path remains Rish + UIAutomator / accessibility surfaces; AutoJS should not be made a hard dependency.
