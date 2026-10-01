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

## Next gate

Use the working Termux execution environment as the trusted anchor:

```
RDC
  -> supported Termux external-command mechanism
  -> existing Broccoli entrypoint
  -> existing Rish/Shizuku path
  -> persistent proof artifact
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
