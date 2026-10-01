# RDC -> Rish live evidence 2026-10-01

Status: PASS

Connected Android device: a14xm
Android SDK: 35

Verified path:

RDC -> Termux -> broccoli-core/lib/rish_run.sh -> Rish -> Shizuku -> Android shell

Observed target identity:

uid=2000(shell)

Observed marker:

RDC_FINAL_RISH_OK

The artifact was written to shared Download and read back by the RDC process.

Important: direct `rish -c` from the reduced RDC environment previously exited 0 without executing. The captured Android runtime environment fixed that boundary. Automated callers now use the Broccoli wrapper rather than direct Rish.

The supervisor also had a real duplication bug. Under `set -o pipefail`, `ps | grep -Fq` could make a healthy child look dead when `ps` received SIGPIPE. The supervisor therefore started a new runtime every interval. The repaired supervisor uses captured `ps` output plus an atomic lock directory. Live steady-state verification now shows one supervisor and one runtime child.
