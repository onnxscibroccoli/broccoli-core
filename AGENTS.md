# Broccoli Core agent operating contract

## Ownership (OMNIKALI-MODULARIZATION-2026-10-04)

`broccoli-core` is the **archive and historical lab**. Extract, do not clean.

Android Rish transport now lives in [`broccoli-rish`](https://github.com/onnxscibroccoli/broccoli-rish):

- `lib/rish_run.sh`
- `tools/android_transport.py` (`RishTransport`)
- `tools/termux_run_command.py`
- live probe scripts

Those files remain in this repo as provenance. Do not delete them. New transport edits go to `broccoli-rish`.

MCP/supervisor extract (`broccoli-mcp`) is **not** started until broccoli-rish has live uid=2000 evidence against that checkout.

## Do not

- recursively clean mirrors, logs, Word docs, `_quarantine`, or `Agent/Broccoli/mirror/`
- add a second `rish_run.sh`
- impersonate the phone executor from a workstation process
- copy this script pile into Grasshopper

## Agent surface here

If the task is Rish transport: stop and open `broccoli-rish`.
If the task is kernel/runtime/UI/AutoJS/history: stay here, one file at a time.

## Verify

```text
python3 -m unittest discover -s tests -t . -v
```

Live Rish proof:

```text
RISH_PRESERVE_ENV=0 bash ./lib/rish_run.sh 'echo BROCCOLI_RISH_OK; id; getprop ro.build.version.sdk'
```
