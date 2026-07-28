#!/usr/bin/env bash
R="${BROCCOLI_ROOT:-$HOME/broccoli}"
head -80 "$R/bin/brocc"; echo ---; head -40 "$R/bin/wire"
grep -rn 'closed_loop\|brocc_wire\|core_round' "$R/bin" "$R/lib"/*.py 2>/dev/null | head -40 || true
