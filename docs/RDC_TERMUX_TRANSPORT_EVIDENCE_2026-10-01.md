# RDC to Termux Transport Evidence

**Date:** 2026-10-01 UTC  
**Status:** NOT_PROVEN  
**Scope:** Android device, Remote Desktop Commander child process

## Proven baseline

The trusted Termux-side path remains proven:

```
Broccoli -> rish -> Shizuku -> shell
```

The existing Broccoli/Rish implementation was not modified during this investigation.

## RDC observations

RDC successfully launched a child with the Termux shell:

- shell: `/data/data/com.termux/files/usr/bin/bash`
- Broccoli repository: `$HOME/broccoli-core`
- `rish` was discoverable at the Termux path.
- Direct RDC child invocation of `rish` returned exit code 0 but produced no observable stdout payload or persistent side effect.
- A `com.termux.RUN_COMMAND` broadcast returned exit code 0 but produced no persistent execution artifact.
- An explicit `RunCommandService` invocation returned exit code 0 but produced no persistent execution artifact.

These observations do **not** prove that Termux external-command execution is unavailable. They prove only that these RDC-created invocations did not produce the expected observable result.

## Architectural boundary

The evidence currently supports this boundary:

```
RDC
  -> Termux child/process environment                 PASS
  -> legacy Broccoli source discovery                 PASS
  -> direct rish invocation with observable effect   NOT_PROVEN
  -> Termux external-command execution                NOT_PROVEN
  -> Shizuku privileged execution from RDC child      NOT_PROVEN
```

The known-good path must remain untouched while this boundary is investigated.

## Failure-mode correction (2026-10-01, not a pass)

Two observations explain the empty RC=0 without treating Rish as broken:

1. `lib/rish_run.sh` execs `rish -c`. `app_process` does not reliably inherit the RDC pipe. Empty stdout plus RC=0 is not evidence that the shell command ran.
2. uid 2000(shell) cannot write `/data/data/com.termux`. A missing file under Termux home is the expected permission boundary, not a Rish failure. `am broadcast` / `am startservice` returning 0 only means ActivityManager accepted the intent.

Proof path that shell can write:

- `/storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt`
- `/data/local/tmp/RDC_TERMUX_ANCHOR.txt`

Probe, after `git pull` on device. It calls `lib/rish_run.sh` and does not edit it:

```
/data/data/com.termux/files/usr/bin/bash -lc 'bash $HOME/broccoli-core/tools/rdc_termux_anchor.sh'
```

Required artifact shape, produced inside the Rish command:

```
RDC_TERMUX_ANCHOR_OK
uid=2000(shell) ...
sdk=35
```

Until that file is fetched back from the device, this gate stays **NOT_PROVEN**.

## Off-device check

OmniKali (`kali`, 7.1.5) has no `adb` binary and no attached Android device. Desktop Commander `remote` is an OAuth bridge to mcp.desktopcommander.app for the host that runs it. It is not an Android transport and was not started.

## Next gate

Use the working Termux execution environment as the trusted anchor:

```
RDC
  -> login Termux bash
  -> tools/rdc_termux_anchor.sh
  -> existing lib/rish_run.sh
  -> shell-written shared artifact
```

Minimum success artifact:

```
RDC_TERMUX_ANCHOR_OK
uid=2000(shell)
sdk=35
```

Only after this transport gate passes should Ruto virtual-display work begin.

## Preservation rule

Do not modify `rish_run.sh`, `rish_cmd.sh`, or the legacy Broccoli implementation merely to accommodate the RDC transport boundary.
