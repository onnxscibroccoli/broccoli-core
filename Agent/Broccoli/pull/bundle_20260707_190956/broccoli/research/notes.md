# Android UI Automation Research Notes

- Shizuku: apps call system APIs via binder with user-granted shell/adb; common for input, package ops, privileged automation.
- Accessibility: prefer node-based actions (text, content-desc, bounds) over fixed coordinates when trees are stable.
- Termux: local orchestration (Python, worker, Shizuku CLI); keep jobs small and artifacts on disk under ~/broccoli/.
- Hybrid: Shizuku for injection/privileged ops; a11y/uiautomator dump for discovery; calibrate send/composer (e.g. 1001,1338).
- Reliability: scroll before read, FAIL on empty/junk, WAIT_FOR_USER for login/OAuth, smoke gate separate from full compose.

Sources (seed): github.com/RikkaApps/Shizuku, awesome-shizuku lists, Termux + Shizuku integration docs.
