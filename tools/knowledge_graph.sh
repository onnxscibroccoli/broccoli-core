#!/data/data/com.termux/files/usr/bin/bash
cd ~/broccoli-core || exit 1
PYTHONPATH="$PWD" exec python3 runtime/memory/knowledge_graph.py --loop --interval 60
