<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure 0.1.7.6 (versionCode 10706)

**Mission:** open-source roof measurement tools so contractors and homeowners can get accurate measurements from free public data
and check whether a roofing quote is fair. Every number is traceable to its free data source and labelled; nothing is claimed as verified.

Based on the reconstructed v0.1.7 source; changes are in CHANGELOG.md. Headless test: `node tests/v0176_test.cjs <outdir>`
(older tests kept as tests/v0171_test.cjs … v0174_test.cjs) (Playwright + Chrome, live MassGIS/USGS; reference-imagery endpoints are blocked/mocked).
Test houses: 15 Ward St Hingham, 6 Harborview Rd Hull, 30 Lockwood Dr Weymouth, 49 Scotland St Hingham (30 Lockwood Drive and 49 Scotland
Street are not in Hull in any free source; the test checks the Hull spellings are reported not found) (override with RM_HOUSES='[{"slug":..,"addr":..}]').
CI: `.github/workflows/roofmeasure.yml` builds the APK (throwaway CI key), runs the headless report tests and an emulator smoke test
(tests/ci_emulator_smoke.sh: install, launch with `--es rm_query 'addr=...&smoke=1'` on debug builds, build the report, save the PDF), and uploads
APK, PDFs, screenshots and logcat as artifacts. Third-party components: THIRD_PARTY.md. 3-D roof view/editor: "3-D view / edit" button (view3d.js, three.js).

## Experimental feature parallax (0.1.7.6 increment 6)

`www/lib/featurelean.js` estimates a **NOT_PROVEN overlay-only** displacement for lidar deck/dormer
candidates from the shift of MassGIS imagery, USGS 3DEP near-eave points, and ground height.
It affects **only the aerial composite**; the vector diagram, source geometry and billable
roof quantities are unchanged. If the evidence is insufficient, the correction is skipped.
The measured ortho offset conflates camera perspective and possible georegistration error;
inspect the 6 Harborview deck position against its walls before treating the overlay as reliable.
Offline test: `node tests/featurelean_test.cjs`; CI also runs headless reports and emulator smoke.

## CI signature isolation for repeated alpha builds

Until a long-lived Android signing certificate is supplied through secure CI secrets,
every CI run uses a disposable debug signing key. Such APKs cannot update one another
under the *same package name*. CI now uses a **commit-specific alpha ID**:
`com.ian.roofmeasure.alpha.c<8-char-commit-sha>`. This permits each reviewed APK
to install beside the original app **and all prior test alphas**, with no
signature conflict. They do not share Android private app data; unique labelled
icons and Downloads folders distinguish them. Stable in-place alpha updates
will require a securely managed stable signing key; never commit it or derive
it from a public seed.

Manual build `PACKAGE_NAME=com.ian.roofmeasure.alpha.c1234abcd ./build.sh out/`.
The original package and prior simple `.alpha` package remain supported.

## Pitch provenance correction (0.1.7.6)

If someone edits facet pitch in the 3-D editor (e.g. both facets 12/12) while
the underlying pitch selector remains at 6/12, the PDF must **not** label a
12/12-area calculation as 6/12. It now shows **12/12 (manual facet override)**
as the basis and separately discloses **base selector 6/12** and its pitch
factor. Mixed pitches are shown as mixed and per-facet geometry is listed.
Neither manual facet adjustment nor aerial image proves physical pitch;
on-device actual pitch remains NOT_PROVEN if there are no lidar measurements.
Offline regression: `node tests/pitchbasis_test.cjs`.

## User roof-feature review (0.1.7.6)

MassGIS ortho patches are candidates for **skylights, chimneys or vents**: a rectangular
bright/dark patch alone cannot identify the structure. In the report preview choose
**Edit measurements → Roof feature candidates**. Every candidate, including automatic
rejections, supports **Automatic / Skylight / Chimney / Vent / Hide** and **Rotate 90°**.
A visually confirmed chimney is moved out of the skylight list. On the map use
**Tag tool → Add chimney** to mark a missed chimney's location (no fictitious size).
The PDF includes visually distinct C/V markers; edits do not change roof area/pitch.
No imagery or user correction is uploaded as telemetry. These confirmations establish
**user visual classification**, not field-measured dimensions. Test:
`node tests/feature_review_test.cjs`.

## Parallel-installable alpha APK (0.1.7.6)

GitHub Actions builds a separately installable **RoofMeasure Alpha** with application ID
`com.ian.roofmeasure.alpha`. It preserves Android version **0.1.7.6** (versionCode **10706**)
and does not overwrite the original `com.ian.roofmeasure`, even if it is signed with a different
certificate. The alpha has separate WebView data, a package-specific PDF content provider, and
saves PDFs under `Downloads/RoofMeasureAlpha/`. Java class namespace remains
`com.ian.roofmeasure` via fully qualified manifest components. Only the generated build-time
manifest changes. No signing secrets are committed.

```sh
PACKAGE_NAME=com.ian.roofmeasure.alpha ./build.sh out/
# out/RoofMeasure-0.1.7.6-alpha-debug.apk
PACKAGE_NAME=com.ian.roofmeasure ./build.sh out/ # original ID; same signature needed for upgrades
python3 -m unittest discover -s tests -p package_variant_test.py -v
```

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
