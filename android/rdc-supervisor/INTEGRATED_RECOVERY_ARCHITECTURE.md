# OmniKali Integrated Process Recovery Architecture

Status: DESIGN + IMPLEMENTATION SLICE, NOT LIVE-PROVEN

## Goal

Recover the execution stack without duplicate processes or a human restart after transient Android, Termux, or Desktop Commander failure.

Three supervision layers:

1. Android lifecycle supervisor
2. Termux service supervisor
3. Service-level health and restart logic

Android owns recovery of the Termux execution surface. Termux owns individual long-lived commands. Each layer fails closed when its security or health contract is not satisfied.

## Recovery hierarchy

Android OS
  -> boot/package-replacement receiver
  -> foreground recovery service
  -> WorkManager reconciliation/checkpoint work
  -> Termux RUN_COMMAND
  -> Termux shell
  -> supervisord
  -> rdc-remote service
  -> Desktop Commander remote session

Android is the outer safety net. supervisord is the inner process supervisor.

## Android layer

The native Android service is responsible for:

- keeping a visible foreground recovery service alive;
- detecting that the desired Termux execution surface is unavailable;
- invoking only the fixed Termux RUN_COMMAND recovery entry point;
- applying bounded retry and backoff;
- recording recovery state outside the Termux process tree;
- restarting its observation after boot and package replacement.

WorkManager is not the primary 24/7 watchdog. Android does not guarantee arbitrary background execution, and WorkManager is intended for deferrable persistent work. Use it for durable reconciliation, diagnostics, and repair checkpoints that can tolerate scheduling delay.

When immediate recovery is required, the foreground service remains the active control loop.

## Termux layer

Termux receives one fixed command from Android. That command bootstraps the Termux supervisor rather than directly launching every application.

The Termux supervisor owns:

- Desktop Commander remote;
- future Grasshopper/Broccoli agents;
- archive/index workers;
- other explicitly declared long-running services.

Each service gets a stable name, executable command, working directory, environment contract, log paths, restart policy, stop timeout, health check, and bounded restart behavior.

The supervisor must never restart a service solely because an Android process-visibility API temporarily failed.

## Health model

Use three states:

- ALIVE: process exists and its positive health signal is current.
- DEGRADED: process exists but its health signal is stale or unhealthy.
- DEAD: process is absent or has exited.

Process existence is only a liveness hint. The preferred positive signal is a heartbeat written by the service itself after its connection is established.

For Desktop Commander, the eventual contract is:

RDC process -> connected-state heartbeat -> persistent state journal

The Android layer can then ask Termux to reconcile the supervisor without guessing whether an invisible process is actually dead.

## Idempotence

Every recovery operation must be safe to run more than once.

Required rules:

- never launch a second RDC when a healthy instance already exists;
- use a lock around recovery commands;
- use a stable service name;
- record service PID and generation;
- do not treat a stale PID as proof of identity;
- verify command identity before killing/replacing a process;
- preserve the Desktop Commander persisted session.

## Durable state

Android-owned state:
 /sdcard/OmniKali/rdc-supervisor/

Suggested files:
- events.jsonl
- state.json
- last-recovery
- last-error
- generation

Termux-owned state:
 ~/.omnikali/rdc-supervisor/

Writes must be append-only or atomic tmp-to-rename updates.

## Security gates

Recovery remains disabled unless:

1. com.termux.permission.RUN_COMMAND is granted to the supervisor;
2. Termux allow-external-apps=true is explicitly enabled.

The Android app exposes no arbitrary command interface. The recovery entry point is fixed in the APK.

Future Shizuku integration should be a privileged observation and diagnostic plane, not a way around the explicit Termux security gate.

## Failure containment

Android supervisor crash:
- WorkManager/boot/package replacement provides a later reconciliation opportunity.
- Do not create an uncontrolled Android restart loop.

Termux unavailable:
- Android retries with bounded backoff.

RDC unavailable:
- Termux supervisor restarts only the RDC service.

RDC repeatedly crashes:
- exponential backoff and a restart budget prevent a tight loop;
- persistent evidence is emitted;
- state becomes DEGRADED or FAILED until the next reconciliation window.

## Implementation order

1. Preserve the existing Android foreground supervisor.
2. Add durable Android recovery journal.
3. Replace direct RDC launch with one Termux supervisor bootstrap command.
4. Add a declarative supervisord configuration for RDC.
5. Add positive RDC heartbeat and generation identity.
6. Add WorkManager reconciliation/checkpoint worker.
7. Add boot/package-replacement recovery.
8. Add optional Shizuku process observation.
9. Perform controlled kill tests at each boundary.
10. Record every result as PROVEN, FAILED, or NOT_PROVEN.

## Acceptance gates

A future live acceptance must separately prove:

A. Android supervisor survives RDC death.
B. Android supervisor invokes Termux without human interaction.
C. Termux supervisor starts RDC.
D. RDC reconnects using its persisted session.
E. No duplicate RDC process is created.
F. Repeated crashes respect backoff and restart budget.
G. Android reboot restores the chain.
H. Termux force-stop recovery is either proven or explicitly marked NOT_PROVEN.

No document or successful build counts as live acceptance evidence.


## Automation execution plane

Browser and mobile automation use the same recovery boundary rather than creating an independent Android control path:

Android lifecycle supervisor -> Termux RUN_COMMAND -> supervisord -> named automation service/job -> result journal.

Desktop Commander remains the transport and observation surface. Playwright is treated as a bounded browser task runner. Appium is treated as an optional long-lived WebDriver service, bound to loopback and enabled only after its driver installation is explicitly verified. RUTO is treated as an external execution surface; its adapter fails closed until a reviewed command or endpoint is configured.

Human-only gates such as OAuth approval, CAPTCHA, bot checks, or consent pause the specific job in a recoverable HUMAN_REQUIRED state. No automation layer attempts to bypass the gate.
