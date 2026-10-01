# OmniKali Android automation execution plane

Status: IMPLEMENTATION SCAFFOLD, LIVE AUTOMATION NOT_PROVEN.

All long-lived automation infrastructure on Android uses the same chain:

Android supervisor -> Termux RUN_COMMAND -> supervisord -> named automation service -> task runner.

Desktop Commander remains the device transport and recovery anchor. It is not itself the browser/mobile automation engine.

## Engines

### Playwright
Playwright is a task runner, not a permanent daemon. A task is launched as a supervised, bounded job through `tools/automation/playwright-task.sh`. The wrapper fails closed unless a task file is supplied and Playwright is installed.

### Appium
Appium is a long-lived WebDriver server and belongs under supervisord. The Android UiAutomator2 driver is required for native Android automation. Installation is deliberately separate from server startup so a missing driver cannot silently trigger package installation during recovery.

### RUTO
RUTO is treated as an external Android execution surface. No undocumented CLI is assumed. The adapter requires an explicit configured command or endpoint and reports NOT_CONFIGURED otherwise. This prevents the supervisor from inventing a RUTO interface.

## Human gates

Automation must pause when authentication, CAPTCHA, bot checks, consent, or another human-only gate is detected. The task state becomes HUMAN_REQUIRED and remains recoverable. The executor must not attempt to defeat the gate.

## Evidence

Each adapter emits:
- engine
- task id
- generation
- started_at
- heartbeat_at
- state
- exit code

Do not promote an adapter to PROVEN until a real phone acceptance records observe -> act -> reobserve -> verify.
