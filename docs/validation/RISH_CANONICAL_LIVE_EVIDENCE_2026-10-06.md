# Canonical Rish Live Evidence 2026-10-06

## Result

**R3 Broccoli -> Rish transport: PASS**

The canonical Broccoli wrapper was executed on the live physical Android/Termux node using the expected invocation:

`bash ./lib/rish_run.sh 'whoami; id; printf BROCCOLI_RISH_OK\\n'`

Observed:

- wrapper source: `~/broccoli-core/lib/rish_run.sh`
- captured Android runtime environment file: present
- `BOOTCLASSPATH`: present
- wrapper result: `shell`
- uid: `2000(shell)`
- security context: `u:r:shell:s0`
- marker: `BROCCOLI_RISH_OK`
- exit code: `0`

## Boundary note

Direct `rish -c` from the RDC-launched non-interactive shell returned no payload and is not treated as proof. The canonical wrapper is the tested transport contract because it reconstructs the required Android runtime environment and invokes Rish with the captured allowlisted variables.

The wrapper file is intentionally invoked through `bash`; its repository mode is 0644 and executable-bit state is therefore not used as the transport proof.

## Device

- Desktop Commander device: `localhost`
- Android: API 35 / Android 15
- Architecture: aarch64

## Next gate

RDC/worker integration remains a separate contract. This evidence proves Broccoli canonical wrapper -> Rish -> privileged shell, not that every RDC child process inherits the same transport.
