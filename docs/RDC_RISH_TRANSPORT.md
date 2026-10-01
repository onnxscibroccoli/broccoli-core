# RDC -> Rish transport contract

## Verified 2026-10-01

The working path is:

RDC -> Termux background shell -> broccoli-core/lib/rish_run.sh -> Rish -> Shizuku -> Android shell

The connected Android device proved SDK 35, uid=2000(shell), target command execution, and named artifact creation.

## Background-caller lesson

A direct `rish -c ...` from a noninteractive RDC process can exit 0 without executing the command.

Shizuku documents `rish -c` for automation. A current Shizuku issue also documents the same reduced-environment symptom: interactive Termux succeeds while a reduced environment exits 0 without output.

Therefore Broccoli and Grasshopper must use `lib/rish_run.sh` for automated callers.

The wrapper restores the captured Android runtime variables before invoking Rish.

## Evidence rule

Exit code 0 alone is NOT_PROVEN.

The final artifact must contain `RDC_FINAL_RISH_OK` and `uid=2000(shell)` plus Android SDK identity.

## Design consequence

Rish remains the known-good privileged transport. Broccoli normalizes the caller. Grasshopper owns orchestration, evidence, checkpoints, and promotion.
