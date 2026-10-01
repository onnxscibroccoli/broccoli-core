# RDC Termux Anchor Evidence — 2026-10-01

## Gate status

| Node | Status |
|---|---|
| Android API 35 | PASS |
| Shizuku/Rish | PASS |
| Broccoli → Rish | PASS |
| Rish → privileged shell | PASS |
| RDC → Termux process/filesystem | PASS |
| RDC → Rish observable execution | **PROVEN** |
| RDC → Termux external-command execution | NOT_PROVEN |
| Ruto | NOT_STARTED |
| Grok secondary display | NOT_STARTED |

## Acceptance artifact

Exact next acceptance artifact: `RDC_TERMUX_ANCHOR_OK`, `uid=2000(shell)`, `sdk=35`.

## Device command (run from Termux home)

```bash
cd ~/broccoli-core && RISH_PRESERVE_ENV=0 bash ./lib/rish_run.sh '{ echo RDC_TERMUX_ANCHOR_OK; id; echo sdk=$(getprop ro.build.version.sdk); } > /storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt; cp /storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt /data/local/tmp/RDC_TERMUX_ANCHOR.txt; echo WROTE; cat /storage/emulated/0/Download/RDC_TERMUX_ANCHOR.txt'
```

## Observed output (2026-10-01, ~01:16 EDT)

```text
WROTE
RDC_TERMUX_ANCHOR_OK
uid=2000(shell) gid=2000(shell) groups=2000(shell),1004(input),1007(log),1011(adb),1015(sdcard_rw),1028(sdcard_r),1078(ext_data_rw),1079(ext_obb_rw),3001(net_bt_admin),3002(net_bt),3003(inet),3006(net_bw_stats),3009(readproc),3011(uhid),3012(readtracefs) context=u:r:shell:s0
sdk=35
```

## Interpretation

- `RISH_PRESERVE_ENV=0` is the working caller flag for `lib/rish_run.sh`.
- The command must be run from inside the `broccoli-core` checkout; `./lib/rish_run.sh` fails with "No such file or directory" from Termux home.
- The artifact is a file written by the shell (uid 2000), not stdout. uid 2000 cannot write `/data/data/com.termux`, so the Download path (and `/data/local/tmp` fallback) is the correct proof location.
- `WROTE` followed by `cat` of the artifact is the acceptance check. RC=0 alone is not proof.
- `lib/rish_run.sh` and `lib/rish_cmd.sh` were not modified.

## Remaining blockers

1. RDC → Termux external-command execution (e.g. `am start` → Termux runs a command) is still NOT_PROVEN.
2. Ruto: NOT_STARTED.
3. Grok secondary display: NOT_STARTED.
