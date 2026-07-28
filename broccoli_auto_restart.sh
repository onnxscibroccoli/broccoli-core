export BROCC_MAX_CHILDREN=2
export BROCC_NO_SELF_MUTATE=1


#!/data/data/com.termux/files/usr/bin/bash


export RISH_ENABLED=1
export BROCC_RETRIES=4
export BROCC_RETRY_DELAY=1
cd "$(dirname "$0")"
[ -x boot/boot_first_job.sh ] && bash boot/boot_first_job.sh
exec python3 broccoli_bootstrap.py
