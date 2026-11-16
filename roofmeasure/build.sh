#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# RoofMeasure 0.1.7.x debug APK build (no Gradle): aapt2 + javac + d8 + zipalign + apksigner.
# Usage: ANDROID_HOME=/path/sdk JAVA_HOME=/path/jdk ./build.sh [out_dir]
# The signing keystore is NOT part of this source. A throwaway debug key is created OUTSIDE the tree
# (default ~/.roofmeasure/debug.keystore) unless KEYSTORE / KS_PASS / KS_ALIAS are given.
set -euo pipefail
R=$(cd "$(dirname "$0")" && pwd)
VC=${VERSION_CODE:-10705}; VN=${VERSION_NAME:-0.1.7.5}  # 0.1.7.x -> versionCode 10700+x (above v0.2.0 = 200, so it installs over it)
SDK=${ANDROID_HOME:?set ANDROID_HOME}; BTV=${BUILD_TOOLS:-34.0.0}; BT=$SDK/build-tools/$BTV; JAR=$SDK/platforms/android-34/android.jar
[ -n "${JAVA_HOME:-}" ] && export PATH=$JAVA_HOME/bin:$PATH
OUT=${1:-$R/out}; B=$(mktemp -d); mkdir -p "$B/classes" "$B/gen" "$B/assets" "$OUT"
cp -r "$R/www" "$B/assets/www"
grep -qE 'https://(unpkg|cdn\.jsdelivr)' "$B/assets/www/index.html" && { echo "CDN reference in www/index.html" >&2; exit 1; }
mkdir -p "$B/res"; cp -r "$R/android/res/." "$B/res/"; python3 "$R/android/make_icon.py" "$B/res/mipmap-xxhdpi/ic_launcher.png"
"$BT/aapt2" compile --dir "$B/res" -o "$B/res.zip"
"$BT/aapt2" link -I "$JAR" --manifest "$R/android/AndroidManifest.xml" -A "$B/assets" -o "$B/unsigned.apk" \
  --java "$B/gen" --min-sdk-version 24 --target-sdk-version 34 --version-code "$VC" --version-name "$VN" "$B/res.zip"
javac -nowarn -Xlint:-options -source 8 -target 8 -bootclasspath "$JAR" -d "$B/classes" $(find "$R/android/src" "$B/gen" -name '*.java')
"$BT/d8" --release --min-api 24 --lib "$JAR" --output "$B" $(find "$B/classes" -name '*.class')
python3 -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1],'a',zipfile.ZIP_DEFLATED); z.write(sys.argv[2],'classes.dex'); z.close()" "$B/unsigned.apk" "$B/classes.dex"
"$BT/zipalign" -p -f 4 "$B/unsigned.apk" "$B/aligned.apk"
KS=${KEYSTORE:-$HOME/.roofmeasure/debug.keystore}; KP=${KS_PASS:-android}; KA=${KS_ALIAS:-roofdebug}
if [ ! -f "$KS" ]; then mkdir -p "$(dirname "$KS")"; keytool -genkeypair -keystore "$KS" -storepass "$KP" -keypass "$KP" -alias "$KA" \
  -keyalg RSA -keysize 2048 -validity 3650 -dname "CN=RoofMeasure Debug" >/dev/null 2>&1; fi
APK="$OUT/RoofMeasure-$VN-debug.apk"
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:"$KP" --key-pass pass:"$KP" --ks-key-alias "$KA" --out "$APK" "$B/aligned.apk"
rm -f "$APK.idsig"; "$BT/apksigner" verify "$APK" && echo "signed: $APK"
cp "$B/classes.dex" "$OUT/classes.dex"; rm -rf "$B"
(cd "$OUT" && sha256sum "$(basename "$APK")" > SHA256SUMS && cat SHA256SUMS)
