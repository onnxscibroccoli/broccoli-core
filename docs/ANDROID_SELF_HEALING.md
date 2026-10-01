# Android self-healing runtime

## Goal

Broccoli is a long-running local execution service on Android. The system must
recover from ordinary process death without pretending Android can be made
physically unable to terminate an application.

The reliability stack is:

1. Termux:Boot restores the supervisor after device reboot.
2. The supervisor holds a single-instance lock.
3. The supervisor discovers an already-running runtime before starting another.
4. The supervisor restarts the runtime when it is genuinely absent.
5. termux-wake-lock reduces sleep-related interruption.
6. Android battery/autostart settings are user-authorized controls and remain
   outside the shell-only contract.

## Important lesson

The old supervisor trusted a shared runtime.pid. Repeated launches could
produce multiple runtime/main.py processes because a PID file alone does not
prove process identity and because multiple supervisors could race.

The hardened supervisor therefore uses:

- atomic mkdir singleton lock
- supervisor identity validation
- independent child PID file
- live command-line identity validation
- process discovery fallback
- adoption of an already-running valid child
- restart only when no valid child exists

## Android boundary

Termux:Boot is an Android boot mechanism, not an immortality mechanism.
Android can still stop processes because of force-stop, resource pressure,
vendor-specific background management, crashes, thermal conditions, or user
action.

Therefore the production claim is:

AUTO_RESTORE + WAKE_LOCK + USER_CONFIGURED_BATTERY_POLICY

not:

ANDROID_CANNOT_KILL_PROCESS

## User-required settings

For persistent operation, the user should open Termux:Boot once after
installation and configure Android's battery/background policy so Termux and
Termux:Boot are not aggressively optimized.

Those settings cannot safely be asserted or changed from the unprivileged
Termux shell.

## Gate

A self-healing gate requires evidence for all of:

- exactly one supervisor
- exactly one valid runtime
- supervisor lock owner matches the running supervisor
- child PID identifies the expected runtime command
- boot launcher is executable
- wake-lock command is available or explicitly recorded unavailable
- runtime restart is observed after controlled termination
- reboot restoration is tested separately

A process count by itself is not sufficient evidence of health.
