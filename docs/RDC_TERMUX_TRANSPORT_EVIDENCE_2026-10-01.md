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

Interactive Termux, prompt `~/broccoli-core $`, 2026-10-01:

```
RISH_PRESERVE_ENV=0 bash ./lib/rish_run.sh 'echo BROCCOLI_RISH_OK; id; getprop ro.build.version.sdk'
```

Observed stdout:

```
BROCCOLI_RISH_OK
uid=2000(shell) gid=2000(shell) groups=2000(shell),1004(input),1007(log),1011(adb),1015(sdcard_rw),1028(sdcard_r),1078(ext_data_rw),1079(ext_obb_rw),3001(net_bt_admin),3002(net_bt),3003(inet),3006(net_bw_stats),3009(readproc),3011(uhid),3012(readtracefs) context=u:r:shell:s0
35
```

This proves the known-good wrapper when the caller sets `RISH_PRESERVE_ENV=0`. It does not prove an RDC-created child wrote the acceptance file. `lib/rish_run.sh` was not modified.

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

```
RDC
  -> Termux child/process environment                 PASS
  -> legacy Broccoli source discovery                 PASS
  -> Termux rish_run.sh with RISH_PRESERVE_ENV=0      PASS
  -> direct rish invocation with observable effect    NOT_PROVEN
  -> shell-written acceptance file                    NOT_PROVEN
  -> Termux external-command execution                NOT_PROVEN
  -> Shizuku privileged execution from RDC child      NOT_PROVEN
```

## Failure-mode correction

1. Caller must set `RISH_PRESERVE_ENV=0`. Preserving Termux `LD_LIBRARY_PATH` into `rish` is the difference between the interactive pass above and an empty RDC result.
2. `lib/rish_run.sh` execs `rish -c`. `app_process` does not reliably inherit the RDC pipe. Empty stdout plus RC=0 is not evidence that the shell command ran.
3. uid 2000(shell) cannot write `/data/data/com.termux`. Proof must be written by the Rish command to shared storage. `am` RC=0 only means ActivityManager accepted the intent.

Proof paths:

- `/storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt`
- `/data/local/tmp/RDC_TERMUX_ANCHOR.txt`

Probe commit `e49d505bd26dd3bf550d61914883bcd5330ab30a` sets `RISH_PRESERVE_ENV=0` and calls `lib/rish_run.sh` without editing it.

## Next gate

Same shell that just printed `BROCCOLI_RISH_OK`:

```
RISH_PRESERVE_ENV=0 bash ./lib/rish_run.sh '{ echo RDC_TERMUX_ANCHOR_OK; id; echo sdk=$(getprop ro.build.version.sdk); } > /storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt; cp /storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt /data/local/tmp/RDC_TERMUX_ANCHOR.txt; echo WROTE; cat /storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt'
```

Minimum success artifact:

```
RDC_TERMUX_ANCHOR_OK
uid=2000(shell)
sdk=35
```

Until that file is fetched back, this gate stays **NOT_PROVEN**. Ruto stays NOT_STARTED.

## Preservation rule

Do not modify `rish_run.sh`, `rish_cmd.sh`, or the legacy Broccoli implementation merely to accommodate the RDC transport boundary.
