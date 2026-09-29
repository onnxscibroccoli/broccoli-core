# Broccoli Core

**Status:** Active legacy/experimental automation platform  
**Repository:** `onnxscibroccoli/broccoli-core`  
**Documentation snapshot:** 2026-09-28 23:12 EDT

Broccoli Core is the oldest and largest automation-oriented repository in this account. It is an Android/Termux-centric agent runtime built around a local execution loop, provider integrations, persistent agent state, UI observation, and a large body of operational experiments.

It is important to understand what this repository is **and what it is not**. It is not the current canonical OmniKali production implementation. It is historical engineering material and a functioning collection of automation/runtime components that influenced later work. Its tree contains thousands of files, including source code, agent state, run records, mirrors, diagnostics, documentation, and generated artifacts. Treating the entire tree as clean application source would be a mistake.

## What it does

The core execution model is expressed around a local kernel:

```
text → classify → resolve schema → execute → confirm
```

The current README identifies `runtime/kernel.py` as the important starting point and exposes a direct smoke invocation:

```bash
python -c "from runtime.kernel import Kernel; print(Kernel().tick('turn on bluetooth'))"
```

The repository also contains a provider-agnostic problem-solving pipeline and managed transports. The documented managed set includes accessibility, clipboard, Grok provider integration, workflow execution, adaptive planning, knowledge graph, agent coordination, and plugin loading.

The repository also contains a real xAI/Grok integration intended for Termux. The checked-in documentation says the runtime uses an OAuth session when available and can fall back to an API key. Credentials themselves must never be committed.

## Major contents

The repository currently contains roughly **5,900 tracked tree entries**. The important architectural areas include:

- `runtime/` — local kernel and runtime primitives.
- `Agent/Broccoli/` — agent implementation, bootstrap logic, worker scripts, context/state, tools, and historical automation.
- `Agent/Broccoli/mirror/` — a substantial mirror of prior Android/Termux automation work.
- `Agent/Broccoli/docs/` — tool and workflow documentation.
- `Agent/Broccoli/meta/` — operational state, queues, iteration metadata, health information, and historical machine state.
- `.github/workflows/` — CI and edge-related workflows.
- Numerous `runs/`, `done/`, `fail/`, logs, snapshots, XML/UI captures, and generated state files.

There are also files that look like credential or secret-storage material in historical paths. **Do not publish or expose those files.** The README is documentation, not a claim that every historical artifact is safe to redistribute.

## Development-cycle assessment

This repository is best classified as **mature prototype / historical platform**, not as a clean greenfield project.

Evidence:

- Recent commits in September 2026 continue to improve the runtime and Watch-Me-Do/observer work.
- The tree contains both current runtime code and extensive historical state.
- CI workflows exist.
- The project has evolved through many experiments rather than a single clean release line.
- Later OmniKali work has separated the production control-plane concerns into newer repositories such as Helix, Grasshopper, and grasshopper-kubernetes.

The correct engineering approach is therefore **extract, preserve, and selectively reuse**, not blindly refactor this repository into the current production system.

## How to use it

For local kernel experimentation:

```bash
cd broccoli-core
python -c "from runtime.kernel import Kernel; print(Kernel().tick('turn on bluetooth'))"
```

For the documented Termux/Grok path:

```bash
cd "$HOME/broccoli-core"
chmod +x bin/broccoli bin/xai-oauth bin/brocc
./bin/broccoli status
./bin/broccoli ping
./bin/broccoli ask "Say hello from Broccoli Core."
```

OAuth setup, when intentionally using the historical Grok integration, is documented as:

```bash
./bin/xai-oauth login
./bin/xai-oauth status
```

Do not place credentials in Git. Do not assume a successful provider call proves that Android accessibility, the kernel, or the historical agent loop is production ready.

## How an AI model should work with this repository

**First:** read the root README and the relevant files under `Agent/Broccoli/docs/`.

**Second:** determine whether the task concerns the local kernel, provider integration, Android/Termux automation, historical state, or one of the mirrored subsystems.

**Third:** never treat `meta/`, run logs, queues, captures, or mirror artifacts as authoritative application code unless the task explicitly concerns those artifacts.

**Fourth:** preserve human control over the Android device. A model should not assume that a historical automation script is safe to execute merely because it exists.

**Fifth:** before deleting or rewriting large areas, identify the current production successor. For OmniKali work, inspect Helix/Grasshopper/grasshopper-kubernetes first.

Good model behavior is: inspect → identify provenance → reproduce a narrow behavior → test → document → change. Bad behavior is: recursively “clean up” the repository and accidentally erase the evidence that explains why later systems exist.

## What is proven vs. unproven

**Proven by repository evidence:** substantial runtime code exists; local kernel execution is documented; provider integration exists; CI/workflow automation exists; extensive Android/Termux automation history exists.

**Not proven by this repository alone:** current production availability, current credentials, current Android device state, current xAI account access, or equivalence with the newer OmniKali production control plane.

## Relationship to the broader system

Broccoli Core is best regarded as **ancestral infrastructure and an experimental automation laboratory**. Its ideas and artifacts inform later agent-control work, but it should not be used as the authoritative definition of the current OmniKali architecture.
