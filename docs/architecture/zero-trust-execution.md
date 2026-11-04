# Broccoli Core: Android action authorization boundary

**Lifecycle:** In Development — source/test hardening branch; no live-device acceptance.  
**Review date:** 2026-11-04.  
**Owner:** Broccoli Core (non-root Android accessibility executor / historical reference).  
**Applicable interfaces:** `tools/actions.py`, `tools/android_action_cli.py`, `tools/android_action_policy.py`, `tools/android_transport.py`.

## Everyday explanation

A model's request to press a button is not permission to press it.
Broccoli Core must first decide whether the request is permitted for the
specific person, device, operation, and limited time window. If no trusted
authorization service is connected, the standard action dispatcher must refuse
device changes rather than assume approval.

## Trust boundary

```text
UNTRUSTED REQUEST OR AGENT
    -> Strict action-schema validation
    -> Governor decision (ALLOW | BLOCK | ESCALATE)
    -> Capability and device-context check [trusted governor responsibility]
    -> ActionDispatcher
    -> RishTransport / Termux RunCommandService
    -> canonical lib/rish_run.sh
    -> Android shell / supported accessibility interface
    -> Action result and outcome verification [separate development]
```

`ActionDispatcher` never trusts the caller's `confirm`, `mutating`, or
`authorization_reference` field as sufficient authority. A side-effecting
action must include explicit principal, device, operation, request, creation,
expiry, policy-version and authorization identifiers. A trusted injected
governor adapter must return an **ALLOW** decision bound to the same identities.
A missing adapter, BLOCK, ESCALATE, expired request, changed identity, invalid
schema, or unexpected property fails before the backend is invoked.

The deliberately unprivileged `android_action_cli.py` does not install a
governor adapter and **cannot perform mutations** by claiming its own
approval. It remains usable for allowlisted read-only inspection. This is a
security fail-closed transition; a trusted controller integration is required
before legitimate Android mutations can resume through this CLI.

`ui.dump` and `package.export` are treated as side effects because they
create files on shared storage. Dump contents may be privacy sensitive.

## Strict action rules

The dispatcher accepts only explicitly named operations. Parameter validation
includes package-name syntax, bounded display identifiers, integer-only and
bounded coordinates, gesture duration, text length and control characters,
allowed keyevent characters, and rejection of unknown properties. The CLI
limits input size, rejects duplicate JSON object keys and non-JSON numeric
constants, and never offers arbitrary shell-command execution.

The governor's decision must be trusted **as code and by its deployment
identity**, not by a client-supplied JSON string. The current contract
verifies decision binding and age but does not yet implement authenticated
server-side authorization, device lock/permission observation, a durable
approval ledger, signed decisions, or live accessibility context.

## Reproduction

```sh
python3 -m unittest tests.test_android_governor_boundary -v
python3 -m unittest tests.test_android_action_contract tests.test_actions -v
python3 -m unittest discover -s tests -t . -v
```

The offline tests use `tests/android_policy_fixture.py` to inject an explicitly
named **test-only** allow decision for existing command-format assertions.
This is not a production authorization implementation.

## Known limitations and open work

1. Other execution entry points, including legacy scripts and direct
   `RishTransport.run` consumers, are not automatically governed by this
   dispatcher. A repository-wide side-effect reachability audit must identify
   and harden or retire each path before claiming a universal governor.
2. Termux/RunCommandService output still uses a shared-storage compatibility
   path. Strong confidentiality is **not** established on shared storage.
3. The transport timeout and ambiguous post-mutation outcome contract remains
   to be hardened. A timeout is not proof that the action failed.
4. Durable request replay protection, event-bus correlation, signed
   authorization decisions and Android permission degradation require
   further implementation and device acceptance.
5. The built-in policy fixture is only for unit tests. Do not import it into
   a production dispatcher.
6. The proven Rish wrapper, non-root privilege model and supportable Android
   APIs remain unchanged.

## Security review and rollout

Review and test the change on the development branch. Confirm which
authorized controllers call `ActionDispatcher`, add a real trusted governor
adapter, run offline regression tests, then perform separately authorized
Android acceptance with real Shizuku and accessibility permission checks.
No historical evidence or credentials should be modified.

**Verification state:** OFFLINE_CI_PENDING; LIVE_DEVICE_NOT_TESTED;
GOVERNANCE_PENDING; PRODUCTION_NOT_VERIFIED.
