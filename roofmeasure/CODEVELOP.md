<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure: co-development guide (Grok Bot + ChatGPT + Ian)

## Goals
- A free, open-source alternative to GAF QuickMeasure, EagleView and Hover for residential roof and gutter takeoffs, starting with Massachusetts.
- License: **MIT** (see LICENSE). Bundled third-party code keeps its own license (MapLibre BSD-3, laz-perf Apache-2.0, Pyodide MPL-2.0).
- **Free data only** for anything measured: MassGIS roofprints and orthos, USGS 3DEP lidar, USDA NAIP, OSM/Overture footprints (ODbL), and the user's own trace.
- Android app (WebView shell, no Gradle) that measures on the map, lets the user view, edit, export and share a PDF report. The report is built from the
  **live on-screen result** (the v0.1.7 approach), never from a hidden re-computation.
- **No accuracy claims.** Reports say "for estimating only; verify on site".

## Version rule
Stay on **0.1.7.x** (0.1.7.1, 0.1.7.2, …) until Ian verifies on his phone that an update is an improvement. versionCode = 10700 + x.
Never bump to 0.1.8/0.2.x on this branch without Ian's explicit OK.

## Status labels (fail-closed)
Every claim in a handoff, test or report is **PASS** (shown by a test or evidence file), **FAIL**, or **NOT_PROVEN** (not yet shown; this is the default).
"It should work" is NOT_PROVEN.

## Repository rules
- Work on branch `feat/roofmeasure-dev` only. No other branches, no PR merges, no force-push, no published releases without Ian.
- Never commit a keystore (`*.keystore`, `*.jks`), APKs, or blobs over 50 MB. `.gitignore` covers out/, *.apk, *.keystore.
- Keep `www/` runnable offline (no CDN URLs; build.sh fails on unpkg/jsdelivr references).

## Layout
- `www/` app (index.html, app.js, sources.js, overture.js, tags.js, report.js, lib/roofcalc.js, lib/facets.js, lidar/pitch.js, py/report/*.py, vendor/)
- `android/` AndroidManifest.xml, MainActivity.java (WebView + RoofBridge), ReportProvider.java, android/print/RmPdfWriter.java, res/
- `web-dev/` browser/dev variants of the v0.1.7 web files (reference only; www/ is authoritative)
- `tests/v0171_test.cjs` headless end-to-end test (15 Ward St Hingham)

## Build
    export ANDROID_HOME=/path/to/android-sdk JAVA_HOME=/path/to/jdk17   # build-tools 34.0.0, platforms/android-34
    ./build.sh out/                      # -> out/RoofMeasure-0.1.7.1-debug.apk + SHA256SUMS
    VERSION_NAME=0.1.7.2 VERSION_CODE=10702 ./build.sh out/
A throwaway debug key is created at ~/.roofmeasure/debug.keystore unless KEYSTORE/KS_PASS/KS_ALIAS are set. To install over Ian's existing app,
sign with the same debug key Ian's earlier APKs used (kept outside git).
Test: `node tests/v0171_test.cjs /tmp/out` (needs Chrome + playwright-core; set PW= and CHROME= paths).

## Imagery terms of service (hard rules)
| Layer | Use in RoofMeasure | Why |
|---|---|---|
| MassGIS orthos 2021/2023/2025, USGS NAIP / Imagery Only | Measure, snap, report aerial | Public / open data |
| Google (Map Tiles API, user's key) | Display only: main layer, overlay, swipe compare | Maps ToS 3.2.3(a–c) and Map Tiles policies: no caching or scraping, no derived content (no tracing or digitizing from imagery), no image analysis or machine interpretation; Google logo and viewport attribution must be shown |
| Microsoft Azure Maps / Bing Maps (user's key) | Display only | Attribution from Get Map Attribution / metadata must be shown; no derived data. Bing basic keys retired 2025-06-30; Enterprise keys end 2028-06-30 |
| Esri World Imagery | Display only | ArcGIS terms; attribution required; derived data restricted |
Concretely:
- Never trace, snap, auto-detect, screen-capture, read pixels, or run computer vision on Google, Microsoft or Esri imagery, even composited.
- Drawing and outline editing stay locked while any reference layer is the main layer or an overlay. Tracing happens only on the free layer
  (swipe compare keeps the free layer interactive).
- Visual categorization (a person tapping eave/rake/etc. while looking) is allowed. It never changes geometry, and the report records which layers were on screen.
- Measurements the user takes in Google Earth etc. go in "Manual measurements", labelled "user-entered (Google Earth ruler)", and are never used in totals.
- Never put Google/Microsoft/Esri tiles, URLs or keys in a report or export.

## Task list (pick one, label results PASS/FAIL/NOT_PROVEN)
1. NOT_PROVEN: on-device test of 0.1.7.1 (Save PDF to Downloads, Share PDF, print fallback) on a real phone and on the emulator (AVD rm34 did not boot headless on the box).
2. Per-edge markings on the report's aerial photo (draw the typed, labelled outline over the MassGIS thumbnail in build_report.py's aerial section).
3. Per-facet pitch: use lidar plane pitch per facet in the totals (behind a toggle), not just the cross-check table. Needs a validation set.
4. Auto-detect from free data, more edge types: step flashing and wall flashing candidates where the roofprint touches another structure; dormers from lidar height jumps.
5. Map Tiles API: render the official Google logo image (not text) and refresh the session before expiry; check the Azure attribution on zoom changes.
6. Detached structures and solar sections (in v0.1.8/0.1.9) ported onto the 0.1.7.x live-result path.
7. Report editing: structured edits (edge type/length table) in the preview, re-rendered by Python, in addition to free-text designMode edits.
8. National fallback: Microsoft US Building Footprints / Overture where MassGIS has none; county parcel registry (see research/RESEARCH.md).
9. Accessibility: TalkBack labels for map edges (list view mirrors the map), larger hit targets option, colour-blind-safe palette option.
