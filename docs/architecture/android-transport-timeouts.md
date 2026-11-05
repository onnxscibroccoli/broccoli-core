# Android transport timeout contract

Current state: In Development. Scope: canonical RishTransport and JSON action CLI.
No live-device acceptance is claimed.

## Why it matters

A tap or text action can finish on Android before its caller stops waiting.
A timeout therefore cannot establish that the action failed. Repeating it may
duplicate a side effect.

## Boundary and behavior

ActionDispatcher retains application authorization. RishTransport owns transport
execution and performs one attempt. Both direct subprocess TimeoutExpired and
Termux bridge TimeoutError produce a TransportResult with:

- status: OUTCOME_UNKNOWN
- ok: false
- returncode: 124 (local diagnostic only)
- stdout: empty
- stderr: fixed message without command or partial output

The JSON CLI forwards status and returns nonzero. Consumers must not interpret
a nonzero return code as permission to replay a mutation. COMPLETED denotes
process completion, not verified Android intent. FAILED denotes a nonzero
process result; it does not guarantee that no partial effects occurred.

## Regression evidence

The tests-only candidate 5021010dd9bbf17515a0b186e47e872a2ba4ae17 reproduced
three assertion failures in CI run 42054326838, Python 3.11 job 127338454582:
https://github.com/onnxscibroccoli/broccoli-core/actions/runs/42054326838

The full suite ran 154 tests with only the three new timeout tests failing.
The Python 3.12 matrix job was marked cancelled; it is not counted as a
completed validation. Final implementation verification belongs to the PR's
exact final candidate and tested merge revision, recorded in its description.

tests/test_transport_timeouts.py includes a real local subprocess that appends
one side-effect marker before timing out. The bridge and CLI fault injection
are offline fixtures; they do not prove live Termux or Shizuku behavior.

## Compatibility and rollback

TransportResult retains its original first three constructor fields, adding a
defaulted timed_out flag. Canonical timeouts now return a non-success result
instead of raising. Callers relying on an exception must inspect ok/status.
The CLI adds a status field. Existing mutation authorization remains required.

Rollback by reverting this increment on a development branch and rerunning the
rooted suite. Reverting restores the old ambiguity and diagnostic exposure;
do not call that a security remediation.

## Known limitations and next work

- Direct subprocess cleanup does not yet guarantee descendant cleanup.
- RunCommandService may continue after the caller times out.
- Captured output and shared-storage result files remain insufficiently bounded.
- Shared storage does not provide confidentiality or authenticated receipts.
- Cancellation, durable deduplication, and device-side outcome reconciliation
  require separate tests and implementation.
- Legacy execution paths still need a complete governor-boundary audit.
- Live device acceptance requires a separately authorized environment.
- This change makes no exactly-once or production-readiness claim.
