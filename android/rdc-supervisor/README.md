# OmniKali RDC Supervisor

Small Android foreground supervisor for the Termux-hosted Desktop Commander Remote Device.

## Recovery chain

Android supervisor -> Termux RunCommandService -> Termux bash -> npx @wonderwhy-er/desktop-commander@latest remote.

The supervisor sends one fixed recovery command. It does not expose arbitrary shell.

## Required one-time security gates

Termux requires third-party RUN_COMMAND callers to request and receive com.termux.permission.RUN_COMMAND, and Termux must have allow-external-apps=true.

Grant Run commands in Termux environment to this APK in Android Settings. In Termux, set:

    mkdir -p ~/.termux
    grep -q '^allow-external-apps=' ~/.termux/termux.properties 2>/dev/null && sed -i 's/^allow-external-apps=.*/allow-external-apps=true/' ~/.termux/termux.properties || printf '\nallow-external-apps=true\n' >> ~/.termux/termux.properties

Then start the supervisor once from its UI.

## Monitoring semantics

- Foreground service with START_STICKY.
- Poll interval: 15 seconds.
- Restart backoff: 60 seconds.
- Android ActivityManager process observation is explicitly best-effort.
- The Termux-side recovery command independently checks for an existing Desktop Commander remote process.
- An atomic directory lock prevents duplicate restart commands.
- Termux state and logs are stored under ~/.omnikali/rdc-supervisor.
- Desktop Commander's persisted session is reused by ordinary restarts.

## Important limitation

Android third-party process APIs are not authoritative process control. Android documents getRunningAppProcesses as a testing/debugging-oriented API and limits visibility on modern releases. The implementation therefore treats absence as a recovery hint, not proof of death.

The next hardening step is a Shizuku-backed process probe plus a positive RDC heartbeat. The latter should be emitted by the Remote Device process after it reaches its connected state. This avoids false restarts when Android reports Termux as cached or temporarily invisible.

## Android 15

The service uses foreground-service type specialUse because this persistent recovery watchdog is not a dataSync job. The manifest declares the required special-use subtype. Live Android 15 installation and crash/restart acceptance remain NOT_PROVEN until the phone/RDC channel is restored.

## Current incident

During development on 2026-10-01 the RDC device became unreachable immediately after a process-boundary test. That is the exact failure mode this supervisor is intended to recover once installed and granted its two security prerequisites.
