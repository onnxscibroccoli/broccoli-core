<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure changelog (0.1.7.x line — stays on 0.1.7.x until Ian verifies an improvement)

## 0.1.7.3 (versionCode 10703) — 2026-11-15
Same rules: free data for every measurement; free MassGIS/NAIP imagery may be analysed (edge snap, edge detection); Google/Bing/Esri stay display-only; no accuracy claims,
labels PASS / FAIL / NOT_PROVEN. License is now MIT (LICENSE, © 2026 Ian Cossette); third-party components are listed in THIRD_PARTY.md.

Root causes (compared with the Gemini bug spec):
- A) Phantom hips/valleys. Gemini's guess was "symmetric heuristics". What the code actually did: the app always ran the weighted straight skeleton
  ('wings' gable, or 'hip' when the lidar shape guess said hip) and never checked the model against the lidar. A footprint jog (15 Ward St edge 1,
  7.66 ft) became a phantom hip (7.66 ft), wall flashing (14.3 ft) and extra "step gable" rake (103.0 vs 88.7 ft).
  Fix: lib/roofmodel.js picks simple gable / wings / hip / flat by per-facet lidar fits (lidar/facetfit.js) plus whole-roof segmentation evidence.
  Without verification the model is ASSUMED, and its hips/valleys are UNVERIFIED candidates that are not counted. A Roof model selector, delete and
  re-type of lines, and user-added lines are in the app and the report editor.
- B) Aerial missing with per-facet on. Gemini's guess was "the PDF buffer unlinks raster streams during async RANSAC". There is no such coupling:
  the per-facet toggle does not touch the aerial code, and both modes drew the aerial in desktop and phone-viewport repros. The real fragility:
  any single tile failure or timeout (10 s, no retry) replaced the whole aerial with the placeholder; tiles were downloaded again on every render;
  and a report could start while lidar was still downloading. Fix: session tile cache, 3 tries (12/20/25 s), a grey tile for a failed tile (the
  aerial is still drawn), prefetch in parallel with the lot lookups, wait for pending lidar, and diagnostics on the page. Tested by aborting a tile.
  NOT_PROVEN on Ian's device.
- C) Rakes. Totals were already sloped, but per-edge tables, diagram/map labels and the editor showed plan length. Now every rake length shown is
  sloped, plan × √(1+(rise/12)²) (e.g. 20.22 ft plan at 12/12 → 28.59 ft), with the plan length in brackets. Per-facet pitch is used when opted in.
  Eaves stay level. Rake edits in the editor are entered as sloped lengths.
- D) Report layout: three full pages (page-break-before): aerial with roofprint, parcel and lot structures; vector diagram (edge numbers, pitch/area
  badges, ridge and interior lines, outward non-overlapping labels); and the diagram over the aerial. Colour plus line style, colour-blind palette,
  and dense mode (L<n> labels) for complex roofs.
- E) Lidar: per-facet robust plane fits (RANSAC + Tukey IRLS, min points, x/12 snapping with confidence, coplanar groups). New lidar/roofseg.js does
  whole-roof segmentation: region growing over all building points (no inset, +1.2 m buffer, so narrow strips are kept), coplanar merge, small
  planes kept and flagged, plane adjacency → ridge/hip/valley, and height jumps → upper-plane eave/rake. Wall flashing is assigned only where a
  wall rises above a lower roof plane. Skylight candidates come from voids, dips and low intensity. Lidar wins on type/confirmation where confident;
  the footprint model keeps its snapped lengths and fills the gaps; low-confidence lidar lines are candidates. An asymmetric gable ridge is placed
  on the lidar ridge line (15 Ward St: facets 553/878 sq ft plan instead of 673/758; area unchanged because both planes are 12/12).
- Skylights: lidar candidates (NOT_PROVEN, removable) plus manual add/remove in the report editor; count, size and location go in the report.
  Inference on free orthos is listed as next work.
- Orchestrator review (complex private test house, folded into 0.1.7.3 before release):
  - Eave/rake method is now a choice in the app ("Eave/rake method"): single dominant lidar ridge (DEFAULT: edges within 15° of the ridge
    bearing are eaves, the rest rakes) or per wing (each lidar ridge, for L/T/cross-gables). The report's Property block states the method used.
  - Counting policy: a lidar line is counted only if it is confident, it is not wall flashing (wall flashing always needs a person to confirm
    a sidewall rises above the roof), and either the roof model is lidar-verified or the line is a ridge (a confident plane-intersection ridge
    needs ridge cap whatever the model). With an ASSUMED model, facets-model step walls and lidar
    confirmations/retypes are not counted. Everything uncounted is left off the main diagrams and listed in a new report Appendix (with its own
    candidate diagram); tap a candidate on the map and Confirm, or set it in the report editor, to count it.
  - Condensed export: tables may break across pages (rows kept whole), smaller table text; lidar plane/step tables, skylight candidates,
    the per-edge measurement-source table and the per-facet fit table moved to the Appendix; the three full-page visuals stay.
  - Drip edge uses the facets-model rake (with step-gable ends) only when the roof model is lidar-verified or user-picked; with an ASSUMED
    model it uses the footprint rake (private complex house: 564.4 → 404.9 LF).
  - Per-facet squares are rounded from the unrounded facet areas, like core (15 Ward St per-facet on: 20.24 → 20.23).
- Report cleanup: one short "For estimating; verify on site." note replaces the disclaimer block; the repeated imagery/tracing wording and
  per-note "verify"/"NOT_PROVEN" tails are gone (data attributions stay). Candidate and "?" lines are never on the main diagrams.
- Edge snap ("Snap to edges", gradient search on the free MassGIS 2025 / NAIP ortho) stays enabled on free layers only. Ortho-based skylight and
  dormer candidates are next work (research list).
- CI: .github/workflows/roofmeasure.yml builds the APK with a throwaway key, runs the headless report tests and an emulator smoke test
  (debug builds accept --es rm_query 'addr=...&smoke=1'), and uploads the artifacts.

Number changes vs 0.1.7.2, 15 Ward St Hingham (lidar 12/12, simple gable lidar-verified):
- ridge 40.7 → 48.4 LF: the one ridge runs the full length, including the section over the west jog (ridge cap on top).
- hip 7.66 → 0, wall flashing 14.3 → 0: the phantom jog hip and wall are gone. Edge 1 (7.7 ft) is a normal eave on the ~1 ft strip; edge 2 is a rake.
- facets-model rake 103.0 → 88.7 LF, so drip edge 199.7 → 185.4 LF. Ridge cap 48.4 is unchanged (40.7 + 7.7 before, 48.4 + 0 now).
- Roof area 2,023.5 sq ft, squares 20.23, eave 96.7, rake 88.7 sloped (62.7 plan), gutter 96.7 and downspouts 5 are unchanged.
- Per-edge rake labels are now sloped: edge 0 28.6 (20.2 plan), edge 2 15.7 (11.1 plan), edge 4 44.3 (31.4 plan).
The complex private test house (local only) changes because of the model and lidar lines; see the local regression notes, not part of this repo.
New test houses: 30 Lockwood Dr Weymouth, 49 Scotland St Hingham, 6 Harborview Rd Hull (Ian listed the first two as Hull; the MassGIS geocoder
places 30 Lockwood Dr in Weymouth and 49 Scotland St in Hingham).

## 0.1.7.2 (versionCode 10702) — 2026-11-15
Same rules as 0.1.7.1: free data for every measurement, reference imagery display-only, no pixel analysis of reference imagery, no accuracy claims.
- Report aerial photo (item 2): build_report.py now draws the typed outline over the free MassGIS ortho thumbnail. Each edge is drawn in its type colour
  (eave blue, rake orange, step/wall flashing, etc.) with a black casing and a numbered circle that matches the edge tables. Interior lines are drawn too
  (ridge red, hip purple, valley teal) along with the dashed roofprint outline. The caption and alt text list the colours.
- Detached structures and solar (item 4): lib/structures.js and lib/solar-est.js are ported from v0.1.8/0.1.9 onto the live-result path.
  The report adds a "Structures on lot" section (MassGIS STRUCT_ID, sq ft, lot roof total) and a "Solar" section (offline Liu-Jordan exposure index
  per facet, no kWh claims, NOT_PROVEN), plus assessor rows taken from the parcel.
- Structured report edits (item 6): the report preview has a "Measurements" editor with these fields: edge type and length per edge, interior line types,
  pitch and waste. "Apply" re-runs build_report.py (Python in Pyodide). Edited lengths are marked "user edit (auto X ft plan)", status user-set,
  and they change the eave/rake/gutter totals with a note. Free-text "Edit text" is still available.
- Footprint fallback outside Massachusetts (item 7): FEMA/ORNL USA Structures (public domain, FeatureServer, CORS) is queried with a point + distance
  query when MassGIS has no structure. The app shows a warning and the default overhang is 1 ft (kind fema_usa_structures). Lidar pitch still comes from USGS 3DEP.
- Accessibility (item 8): a colour-blind-safe palette (Okabe-Ito) option and a large-targets option (tap tolerance ×1.6, bigger labels).
  Edge/line labels carry aria-labels. The edge list rows are focusable buttons that work with Enter/Space, so TalkBack can read them.
  #status is an aria-live region, the map has role=application with a label, and keyboard focus is visible.
- Google branding and session (item 5): the official Google Maps logo SVG is used (light/dark outline, unmodified, from Google's attribution
  asset pack; see www/icons/GOOGLE_LOGO_NOTICE.md, not MIT). It is 18 px high with 10 px clear space left and 5 px bottom, and the scale bar moved to
  bottom-right so it doesn't crowd the logo. The Map Tiles session is refreshed before expiry (checked every 5 min) and on tile 401/403 errors.
- Per-facet lidar pitch in totals (item 3, opt-in, off by default): when you turn it on, the roof area is the sum of the facet plan areas at each
  facet's matched lidar plane pitch. The single-pitch area stays in the report as roof_area_sqft_single_pitch, with a note. NOT_PROVEN.
- Bug fix (regression present in v0.1.7 and 0.1.7.1): if MapLibre's 'load' event never fired (a hanging or 404 tile, e.g. outside MA), the app never
  initialised. Init now runs on 'load', or 1.5 s after the style loads.
- Service worker cache rm-www-0.1.7.2; UA RoofMeasureAndroid/0.1.7.2.

### Numbers vs 0.1.7.1 (headless, live MassGIS/USGS, 2026-11-15 ET)
- 15 Ward St, Hingham: roof area, squares, pitch, eave/rake/gutter LF, downspouts and ridge/hip/valley lines are all identical
  to 0.1.7.1 (PASS). Two summary fields differ, both intentional: solar_present (false -> true, new solar section) and the new lot block (structures on lot:
  15 Ward St 2 structures including the detached garage, lot roof 2,251.5 sq ft).
- Opt-in per-facet (off by default, so not in the comparison): 15 Ward St 2,023.5 both ways.

## 0.1.7.1 (versionCode 10701) — 2026-11-15
Built from the reconstructed v0.1.7 source. The report is still built from the live on-screen result (v0.1.7 approach).
- Imagery: free, measurement-grade layers MassGIS 2025/2023/2021, USDA NAIP (USGS exportImage), USGS Imagery Only.
  Map fallback under MassGIS changed from Esri to USGS (free).
- Visual reference layers, display only: Esri World Imagery; Google satellite (Map Tiles API, your key, createSession + viewport attribution,
  "Google" wordmark); Azure Maps imagery (microsoft.imagery, your key, Get Map Attribution); Bing Maps aerial (legacy Enterprise key, Imagery Metadata).
  Keys live only in this device's localStorage and are never written to reports or exports.
- Three ways to view reference imagery: as the main layer, as an overlay over or under the free layer (opacity slider), and as a swipe compare
  (reference left of a divider, free layer right).
- Tracing lock: drawing, vertex drag/insert/delete, outline move and edge snap are disabled whenever a reference layer is the main layer or an
  overlay. Snap only runs on free layers. No screen capture, pixel reading or computer vision is ever done on reference imagery.
- Auto-detected edges come from free data only (MassGIS roofprint, USGS 3DEP lidar ridge/planes, facets straight-skeleton). They are drawn colour-coded with
  a black casing and a text label (type + length) over any layer, including interior ridge/hip/valley lines.
- Visual categorization: Tag tool for outline edges (eave, rake, step flashing, drip edge, wall flashing, no gutter), interior lines (ridge/hip/valley retag),
  and facets/areas (steep-slope, low-slope, flat, deck). Confirm tool plus "Confirm all shown". Eave/rake and line retags change the report numbers;
  other tags are listed with their LF and areas.
- Manual measurements: user-entered values (for example the Google Earth ruler or a tape on site) with a source label, shown in the report as user-supplied
  and never used in totals.
- Report: new "Visual categorization (user tags)" section with a per-edge and per-line data source and status table, tag LF totals, area by category,
  per-facet pitch from lidar RANSAC planes (cross-check, NOT_PROVEN), user-supplied measurements, user notes, and a list of the reference layers viewed.
- Report preview overlay: view, "Edit text" (designMode), then Save PDF or Share PDF.
- Android: RoofBridge.savePdf writes the PDF straight to Downloads/RoofMeasure (API 29+, MediaStore, no permission needed). RoofBridge.sharePdf writes
  the PDF and opens the share sheet through a private ReportProvider (content://, read grant). Both fall back to the print dialog on failure.
  The print path ignores a second onPageFinished (duplicate print jobs). The report engine load has a 120 s timeout with a clear error.
- High-contrast edges and large labels (on by default). Touch tap tolerance is unchanged at 20–22 px.
