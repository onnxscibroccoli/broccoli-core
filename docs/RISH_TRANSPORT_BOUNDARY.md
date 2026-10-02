# Rish transport boundary

The Broccoli Rish wrapper is a transport boundary, not proof of privileged execution.

## Required proof

A transport invocation is PASS only when all of these are true:

1. the Rish executable exists;
2. the invocation returns a meaningful result;
3. a target-side artifact is created;
4. the artifact contains a unique target marker;
5. the artifact contains target identity evidence such as uid/context.

An exit code of zero with empty stdout/stderr is NOT_PROVEN.

## RDC caller boundary

Remote Desktop Commander starts background children in a reduced Termux environment that can omit Android runtime variables such as `BOOTCLASSPATH`. Direct `rish` from that child is therefore not a valid health check even when it returns exit code 0. The supported path is `tools.android_transport.RishTransport`, which re-enters Termux through `RunCommandService` and then invokes the canonical `lib/rish_run.sh` wrapper.

An active Shizuku service is still required. Do not replace this boundary with Android permission grants to the Termux UID.

## Probe

Run from an actual Termux session after Shizuku is active:

    bash ~/broccoli-core/lib/rish_transport_probe.sh

The probe is deliberately fail-closed. It writes a target-side marker and rejects rc=0 with no artifact.

## RDC-specific gate

PASS. The supported bridge is:

    RDC child -> Termux RunCommandService -> lib/rish_run.sh -> Shizuku/Rish -> Android shell

Live evidence on 2026-10-01 returned `uid=2000(shell)` and Android API 35. The compatibility module `lib/broccoli_rish_shell.py` was revalidated on 2026-10-02 through the same transport and returned shell UID 2000, API 35, `wm size` 1080x2408, and a valid foreground package.

## Security rule

Never claim battery-optimization exemption, Android shell identity, or privileged transport from the Termux UID alone. Those require Android-side evidence.
