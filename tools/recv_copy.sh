#!/data/data/com.termux/files/usr/bin/bash
export BRO=~/broccoli
export PATH="$PREFIX/bin:$BRO/bin:$BRO/tools:$PATH"
export PYTHONPATH=$BRO/lib
export RISH_APPLICATION_ID=com.termux
export BROCCOLI_RECV_MODE=copy_rish
python3 -c "
import sys; sys.path.insert(0,'$BRO/lib')
from broccoli_recv_copy_rish import recv_via_copy_rish
import os
t=os.environ.get('BROCC_TASK','')
r,m=recv_via_copy_rish(task=t or 'BROCC_TASK reply exactly: LOOP_OK')
print('REPLY:', r[:500])
print('META:', m)
"
