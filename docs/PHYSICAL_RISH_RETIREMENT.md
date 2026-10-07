# Physical Android transport retirement — 2026-10-07

Physical Android commands must enter `broccoli-core/lib/rish_run.sh`. The public
`bin/broccoli-rish` command already delegates there. The exported Shizuku launcher
at `/data/data/com.termux/files/usr/bin/rish` is an internal dependency of that
wrapper, not an automation entrypoint. Do not remove the exported launcher or its
DEX. New Shizuku exports remain supported through the existing runtime environment
capture and `BROCCOLI_RISH_BIN`; this change leaves the canonical wrapper unchanged.

Old shell and Python launchers now delegate to this wrapper, without raw Rish,
ADB, intent-broadcast, or local-shell fallback. Current runtime and generated
scripts use the same physical owner. Remote/cloud Android may use a separately
configured transport; it must not silently replace the physical route.

Archived raw launchers in Agent, backup, state/walk, nested copies, quarantine,
inbox, and pinned-walk sources are blocked explicitly while retaining the original
source for provenance. `docs/validation/physical-rish-retirement-2026-10-07.json`
records the 251 retired archived files. Do not restore or execute these files as
current code. Failed or missing physical transport is an error, not permission to
replay a mutation using another shell.

## Verification

```bash
python3 -m unittest tests.test_physical_rish_retirement -v
python3 -m unittest discover -s tests -t . -v
```

Regression checks cover intact quoted commands, single dispatch, exit propagation,
missing transport, no host fallback, active-source launch policy, and archive guards.
All changed Python files parse. Fifteen changed Python heredoc bodies parse. Existing
syntax defects in `tools/codevel_wire.sh` and four archived copies predate this work;
those copies are not accepted as execution evidence.

Baseline `95041af6e0acb75e5c03363e2becf13b959d0e96` ran 140 tests with one failure and
six errors due to missing `Dict` in `runtime/drivers/accessibility/public_backend.py`:
`tests.runtime.test_bootstrap_fault_injection`, `tests.runtime.test_bootstrap_integration`,
`tests.runtime.test_bootstrap_smoke`, `tests.runtime.test_runtime_loop_telemetry`,
`tests.test_core.TestBroccoliCore.test_01_runtime_startup`,
`tests.test_core.TestBroccoliCore.test_05_accessibility_driver`, and
`tests.test_hardened_core.HardenedCoreSmokeTest.test_required_runtime_modules_import`.
That baseline defect is repaired separately, without weakening the assertions.

Canonical wrapper SHA-256:
`73cb4a3840f218f7ad7d102aee62d956bb1de9e7bd895ce089b162e4075ee742`.
Offline tests do not promote this checkout to live R2 PASS. Fresh phone proof against
this exact proposed commit remains required; the dirty phone checkout is untouched.
