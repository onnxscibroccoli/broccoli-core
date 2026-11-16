#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# CI emulator smoke test for RoofMeasure (debug APK): install, launch with ?smoke=1 for each address, wait for the in-app
# report + native PDF save (RM_SMOKE lines in logcat), pull the PDFs from Downloads, take screenshots. Writes to $OUT.
set -uo pipefail
APK=${1:?apk}; OUT=${2:-smoke-out}; mkdir -p "$OUT"
PKG=$("${ANDROID_HOME:?}/build-tools/34.0.0/aapt2" dump badging "$APK" | awk -F "'" '/^package:/{print $2; exit}')
[ -n "$PKG" ] || { echo "APK package detection failed" >&2; exit 1; }
OUTDIR=RoofMeasure; [ "$PKG" = "com.ian.roofmeasure.alpha" ] && OUTDIR=RoofMeasureAlpha
adb wait-for-device
adb shell settings put global window_animation_scale 0; adb shell settings put global transition_animation_scale 0; adb shell settings put global animator_duration_scale 0
adb install -r -g "$APK" || { echo "install failed"; exit 1; }
adb shell dumpsys package $PKG | grep -E "versionName|versionCode" | tee "$OUT/package.txt"
adb shell dumpsys package com.google.android.webview | grep -m1 versionName | tee "$OUT/webview.txt" || true
fail=0; n=0
while IFS='|' read -r slug q; do
  [ -z "$slug" ] && continue; n=$((n+1))
  adb logcat -c
  adb shell am force-stop $PKG
  adb shell "am start -n $PKG/com.ian.roofmeasure.MainActivity --es rm_query '$q'"
  ok=""; for i in $(seq 1 90); do
    sleep 5
    [ $((i % 6)) -eq 0 ] && adb exec-out screencap -p > "$OUT/${slug}_t$((i*5))s.png"
    if adb logcat -d -s RoofMeasureJS:I | grep -q "RM_SMOKE save"; then ok=1; break; fi
    if adb logcat -d -s RoofMeasureJS:I | grep -q "RM_SMOKE FAIL"; then break; fi
  done
  sleep 3; adb exec-out screencap -p > "$OUT/${slug}_final.png"
  adb logcat -d > "$OUT/${slug}_logcat.txt"
  grep "RM_SMOKE" "$OUT/${slug}_logcat.txt" | sed 's/.*RM_SMOKE/RM_SMOKE/' > "$OUT/${slug}_smoke.txt"
  cat "$OUT/${slug}_smoke.txt"
  if grep -q "RM_SMOKE save OK" "$OUT/${slug}_smoke.txt"; then echo "PASS $slug"; else echo "FAIL $slug"; fail=$((fail+1)); fi
done < "${SMOKE_LIST:-$(dirname "$0")/ci_smoke_addresses.txt}"
adb shell ls -l /sdcard/Download/$OUTDIR/ | tee "$OUT/downloads.txt" || true
adb pull /sdcard/Download/$OUTDIR "$OUT/pdf" || true
echo "smoke: $((n-fail))/$n passed"; [ "$fail" -eq 0 ]
