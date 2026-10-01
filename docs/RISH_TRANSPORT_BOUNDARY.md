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

## RDC limitation

Remote Desktop Commander starts Termux commands as the application UID. Rish requires an active Shizuku service. A non-interactive RDC process can invoke the Rish launcher while still receiving no target output if Shizuku is not running.

Do not repair this by granting Android shell permissions from the Termux UID. Android correctly rejects cmd deviceidle whitelist with android.permission.DEVICE_POWER for this UID.

## Probe

Run from an actual Termux session after Shizuku is active:

    bash ~/broccoli-core/lib/rish_transport_probe.sh

The probe is deliberately fail-closed. It writes a target-side marker and rejects rc=0 with no artifact.

## RDC-specific gate

RDC -> Rish remains NOT_PROVEN until the same probe is launched through RDC and the target artifact is observable.

The supported bridge is:

    RDC -> Termux process -> Rish -> Shizuku service -> Android shell

The missing dependency is the active Shizuku service, not the Broccoli wrapper.

## Security rule

Never claim battery-optimization exemption, Android shell identity, or privileged transport from the Termux UID alone. Those require Android-side evidence.
