<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure: co-development guide (Grok Bot + ChatGPT + Ian)

## Mission
Open-source roof measurement tools so contractors and homeowners can get accurate measurements and check whether a quote is fair.

## Goals
- A free, open-source alternative to GAF QuickMeasure, EagleView and Hover for residential roof and gutter takeoffs, starting with Massachusetts.
- License: **MIT** (see LICENSE). Third-party components and their licenses: THIRD_PARTY.md (any permissive or other license is fine; just record it there).
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
- `tests/v0171_test.cjs`, `tests/v0172_test.cjs`, `tests/v0173_test.cjs` headless end-to-end tests (15 Ward St Hingham, 30 Lockwood Dr Weymouth, 49 Scotland St Hingham, 6 Harborview Rd Hull; override with RM_HOUSES)

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
- Free public imagery (MassGIS orthos, USGS NAIP) may be analysed in any useful way: pixel analysis, edge detection, edge snap of outline
  vertices ("Snap to edges", gradient search), skylight/dormer candidates.
- Never trace, snap, auto-detect, screen-capture, read pixels, or run computer vision on Google, Microsoft or Esri imagery, even composited.
- Drawing and outline editing stay locked while any reference layer is the main layer or an overlay. Tracing happens only on the free layer
  (swipe compare keeps the free layer interactive).
- Visual categorization (a person tapping eave/rake/etc. while looking) is allowed. It never changes geometry, and the report records which layers were on screen.
- Measurements the user takes in Google Earth etc. go in "Manual measurements", labelled "user-entered (Google Earth ruler)", and are never used in totals.
- Never put Google/Microsoft/Esri tiles, URLs or keys in a report or export.

Google logo: use only the unmodified official SVGs in www/icons (light on imagery). Height 16–19 dp, clear space 10 dp left/top/right and 5 dp bottom,
alt "Google Maps". Never recolour, crop or put it in reports.

## Task list (pick one, label results PASS/FAIL/NOT_PROVEN)
Done in 0.1.7.2 (headless PASS, on-device NOT_PROVEN): 2, 3 (opt-in), 5 (logo + session refresh; Azure attribution-on-zoom still open), 6, 7 (FEMA/ORNL USA Structures), 8 (partial: palette, big targets, aria; real TalkBack NOT_PROVEN).
1. NOT_PROVEN: on-device test of 0.1.7.1/0.1.7.2 (Save PDF to Downloads, Share PDF, print fallback, TalkBack) on a real phone; AVD rm34 never came online headless on the box (two more retries in 0.1.7.2).
2. Validate per-facet pitch against measured roofs before considering making it default.
3. Auto-detect from free data, more edge types: step/wall flashing candidates where the roofprint touches another structure; dormers from lidar height jumps.
4. Azure Maps: re-query Get Map Attribution on zoom/move end.
5. National parcels/assessor outside MA (county registries; see research/RESEARCH.md); Overture/Microsoft footprints as a second fallback.
6. Structures on lot outside MA (FEMA) and lidar pitch per detached structure.

## 0.1.7.3 notes for co-developers
- Roof model (lib/roofmodel.js): simple gable / wings / hip / flat chosen by per-facet lidar plane fits (lidar/facetfit.js); without lidar the model is
  ASSUMED and hips/valleys are UNVERIFIED candidates that are not counted until confirmed. The user can pick the model and add, delete or re-type lines.
- Whole-roof lidar (lidar/roofseg.js): region growing over all building points (no inset, +1.2 m buffer), robust plane refit, coplanar merge,
  small planes kept and flagged, plane adjacency -> ridge/hip/valley lines, height jumps -> upper-plane eave/rake or wall flashing (only where a wall
  rises above a lower roof plane), skylight candidates (voids/dips/low intensity). Lidar wins where confident; the footprint model fills gaps.
- Rakes are SLOPED everywhere a length is shown (plan × √(1+(rise/12)²), per-facet pitch when opted in); eaves are level.
- Report: three full pages (aerial + parcel, vector diagram, diagram over aerial), robust aerial (session tile cache, retries, grey tile on failure).
- CI does the heavy work (APK, headless tests, emulator smoke); keep box runs light.
- Private complex-roof test cases stay outside the repo (local only).

## 0.1.7.4 notes for co-developers
- Pixel analysis is allowed ONLY on free imagery (MassGIS 2025 orthos, NAIP). Google/Bing/Esri tiles are display-only: never read their pixels,
  never run edge detection or photogrammetry on them, and do not add a toggle for it.
- lib/orthoalign.js: ortho lean/offset estimate (outline + ridge/hip/valley gradient score, bounded search) and patch candidates. The report shifts
  the photo, not the measurements. Set window.RM_NO_ORTHO_ALIGN = true (or opt.noOrthoAlign) to compare with the unshifted photo.
- view3d.js (window.Roof3D): three.js 3-D view/editor, lazy-loaded from www/vendor/three/. Edits use the tag paths (tags.lineMoves, tags.lines,
  tags.facetPitch, ring overrides) and are logged in state.edits3d → result.edits_3d → report note + attributions.
- tags.js: dormers() (lidar dormer candidates with gutter LF / returns / inspect-and-clean), doubtful lidar ridges (lidar_doubt).
- sources.js: town-aware geocoding (townOf, town_mismatch); the app shows "not found in <TOWN>" or a WARNING.
- Tests: tests/v0174_test.cjs (CI report-tests job). WebGL in headless Chrome uses --use-gl=swiftshader --enable-unsafe-swiftshader.
