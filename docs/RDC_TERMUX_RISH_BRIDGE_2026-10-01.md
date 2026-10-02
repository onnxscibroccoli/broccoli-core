# RDC to Termux to Rish bridge evidence

Date: 2026-10-01
Device: android-phone-a146u / Samsung SM-A146U
Android API: 35

## Gate result

PASS: a Remote Desktop Commander child process can invoke Termux `RunCommandService`, and the invoked Termux command can execute the canonical Broccoli Rish wrapper.

The live chain is:

```text
RDC child
  -> /system/bin/am startservice
  -> com.termux/.app.RunCommandService
  -> Termux bash
  -> broccoli-core/lib/rish_run.sh
  -> Shizuku/Rish
  -> Android shell uid=2000
```

The Rish proof returned `uid=2000(shell)` and SDK 35 with exit code 0.

## Why this is the safe fix

The prior RDC child path lacked Android runtime variables such as `BOOTCLASSPATH`. Calling Rish directly from that reduced environment could hang. A timeout must not trigger an automatic retry because an Android mutation could already have occurred.

The transport now detects the reduced caller before invoking Rish. When the Android `am` and Termux bash endpoints exist and `BOOTCLASSPATH` is absent, it uses the Termux RunCommand bridge. Interactive Termux callers continue to use the canonical `lib/rish_run.sh` path directly.

No alternate Rish implementation was introduced. `lib/rish_run.sh` remains authoritative.

## Live evidence

- `device.identity`: PASS
- `ui.dump` through the lower-level canonical Rish path: PASS historically; a fresh RDC-originated `uiautomator dump` is currently NOT_PROVEN because the Android `uiautomator` process can hang on this live device.
- `package.inspect` for `com.openai.chatgpt`: PASS
- Rish result: `uid=2000(shell)`, API 35, device `a14xm`
- focused regression suite: 21/21 PASS

## Regression boundary

The complete historical Broccoli test discovery is not a valid clean baseline on this checkout. It currently reports missing legacy `runtime.*` modules plus placeholder/stale tests unrelated to this transport. Those failures were not attributed to this bridge.

The transport/action-focused suite was repaired where its tests had fallen behind the current `display_id` action contract and passes 21/21.

## Security and mutation rules

- Commands remain allowlisted by `ActionDispatcher`.
- Package names remain validated before package actions.
- `app.stop` still requires explicit confirmation.
- The bridge does not expose arbitrary shell as an Android action.
- Direct Rish timeouts are not retried through a second transport.
- The bridge uses a unique shared-storage result file and atomic rename.
- Raw Android runtime state remains inside the Termux process; only bounded command output crosses the bridge.

## Remaining gates

This closes the RDC to Rish caller-boundary gate. It does not bypass Android authentication, CAPTCHA, biometric prompts, Google 2-step verification, or GCP billing activation. Those remain human/provider gates and must be represented as such by the orchestration layer.
