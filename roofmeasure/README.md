<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure 0.1.7.5 (versionCode 10705)

**Mission:** open-source roof measurement tools so contractors and homeowners can get accurate measurements from free public data
and check whether a roofing quote is fair. Every number is traceable to its free data source and labelled; nothing is claimed as verified.

Based on the reconstructed v0.1.7 source; changes are in CHANGELOG.md. Headless test: `node tests/v0175_test.cjs <outdir>`
(older tests kept as tests/v0171_test.cjs … v0174_test.cjs) (Playwright + Chrome, live MassGIS/USGS; reference-imagery endpoints are blocked/mocked).
Test houses: 15 Ward St Hingham, 6 Harborview Rd Hull, 30 Lockwood Dr Weymouth, 49 Scotland St Hingham (30 Lockwood Drive and 49 Scotland
Street are not in Hull in any free source; the test checks the Hull spellings are reported not found) (override with RM_HOUSES='[{"slug":..,"addr":..}]').
CI: `.github/workflows/roofmeasure.yml` builds the APK (throwaway CI key), runs the headless report tests and an emulator smoke test
(tests/ci_emulator_smoke.sh: install, launch with `--es rm_query 'addr=...&smoke=1'` on debug builds, build the report, save the PDF), and uploads
APK, PDFs, screenshots and logcat as artifacts. Third-party components: THIRD_PARTY.md. 3-D roof view/editor: "3-D view / edit" button (view3d.js, three.js).

## Original v0.1.7 reconstruction notes

License: MIT (see LICENSE). Bundled third-party code keeps its own license (www/vendor/LICENSE.txt = MapLibre BSD-3; laz-perf Apache-2.0; Pyodide MPL-2.0).
No accuracy claims are made. Status labels: PASS / FAIL / NOT_PROVEN.

## Layout
- www/            the app exactly as shipped inside the v0.1.7 APK (assets/www): index.html, app.js, sources.js, overture.js,
                  report.js (in-app PDF via unmodified report/build_report.py + svg/diagram.py in Pyodide 0.27.7), lib/roofcalc.js,
                  lib/facets.js, lidar/pitch.js, py/report/*.py, vendor/ (MapLibre, laz-perf, Pyodide core).
- android/        AndroidManifest.xml, src/com/ian/roofmeasure/MainActivity.java (WebView + RoofBridge.printHtml -> PrintManager), res/, make_icon.py
- web-dev/        browser/dev variants of the web files (CDN URLs, ../facets path) as they were at the v0.1.7 build; www/ is authoritative.
- build.sh        Gradle-free build (aapt2, javac, d8, zipalign, apksigner).

## Build
    ANDROID_HOME=/path/to/sdk JAVA_HOME=/path/to/jdk17 ./build.sh out/   # VERSION_NAME / VERSION_CODE env override (0.1.7.x -> 10700+x)
Needs build-tools 34.0.0 and platforms/android-34. **No keystore is included.** build.sh creates a throwaway debug key at
~/.roofmeasure/debug.keystore (outside this tree) unless KEYSTORE/KS_PASS/KS_ALIAS are set. A different key means Android will
require uninstalling the old v0.1.7 before installing a rebuild.

## Verification (2026-11-15 ET)
Rebuilt from this tree and compared with the original v0.1.7 APK
(sha256 76020d4e9cde96931199d655449cff888993a463d4013bf00f56d9ad1ac1dd0a):
- PASS: all 36 non-signature files byte-identical (assets/www/*, classes.dex, resources.arsc, AndroidManifest.xml, res/ icon).
- classes.dex sha256 ca40ae18b5fe43a9de51f32babc661e7b5b9cfec78e6c04a86da8194407d0d57 (identical).
- Only META-INF signature files differ (different signing key) — expected.
- Note: there was no git history; source was recovered from the APK assets plus apk/src (MainActivity.java mtime 01:17 ET, dex-identical).
