<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure changelog (0.1.7.x line — stays on 0.1.7.x until Ian verifies an improvement)

## 0.1.7.6 (versionCode 10706) — 2026-11-16
**User photo review increment:** Candidate corrections via report editor (skylight/chimney/vent/ignore, rotate 90°), including previously rejected patches; map-tap chimney marker for missed detections, distinct C/V PDF annotations, audit-labelled user-reviewed provenance. Automatic candidates cannot self-certify; no billable total or pitch changes. Deterministic offline test. Physical visual accuracy NOT_PROVEN.
**Parallel-installable alpha packaging:** CI package ID `com.ian.roofmeasure.alpha`, launcher label RoofMeasure Alpha, unique PDF provider authority and Downloads folder. The original package remains installed despite signing-key differences. Build-time generated manifest and package-detecting emulator smoke test; offline manifest regression. Physical-phone installation NOT_PROVEN.
**Increment 6 (experimental feature-parallax candidate, CI pending):** Height-relative, display-only aerial
correction for elevated lidar deck/dormer candidates, using the MassGIS ortho alignment, USGS 3DEP ground elevation,
and the 35th percentile of >=10 lidar roof points within 1.5 m of the eave. Candidate offset =
ortho_shift x (feature_z - eave_z) / (eave_z - ground_z). Skips missing/weak ground or eave evidence,
low-confidence ortho alignments, and implausible heights; never edits coordinates, outlines, dimensions,
skylight matching or billable totals. Candidate dormer markers added to vector and aerial reports.
New offline unit CI gate; real aerial and Android evidence NOT_PROVEN. Version remains 0.1.7.6.

Guidance from docs/research (Ian's papers): lines come from fitted lidar planes; 2-D / CV detections stay outside the billable totals.

- Outline vs lidar: the roofprint is compared with the lidar building mask (class-6 points within 6 m, 0.5 m grid) by IoU over
  ±4 m translations (lidar/pitch.js now fetches a 6 m pad and keeps `points_bbox` / `ground_points`). All three test houses show
  the same ~1.1 m roofprint-vs-lidar offset (15 Ward 0.5 E/1.0 S, 6 Harborview 1.5 E/1.0 S, 4 Oakcrest 1.0 E/0.5 S), so lidar
  features (decks, dormers, lidar skylights) are now moved into the roofprint frame before they are drawn or matched with photo
  patches. Lines, facets and totals are not moved. Appendix: IoU before/after and lidar building area outside the roofprint.
- Ortho offset: the edge-gradient search is unchanged (it is right on 15 Ward and 6 Harborview). A region score (brightness
  separation of the lidar roof planes in the photo, eta²) was tried as a factor and moved 6 Harborview 5 m off the roof, so it is
  reported as a cross-check only. 4 Oakcrest: shift unchanged (2.68 E / 2.19 S); the photo there is ambiguous by about 1 m
  (house shadow, porch edge) and the earlier "visibly offset" read was largely the house's shadow.
- Stricter skylights: both sides 1.5-12 ft, contrast >= 4 MAD, rectangularity >= 0.6, the ring 0.25-1.1 m around the patch on
  ONE lidar plane (>= 65 %), lidar returns on the patch within -0.25/+0.45 m of that plane (flush glass or a low curb), not on a
  deck, near a dormer or in a 3+ cluster. Lidar-only candidates (void / dip) are listed but not counted. Rejected patches and
  their reasons are in the Appendix. Totals/summary rows say "candidates, not in totals".
- Roof deck outline: principal-axis rectangle from the 5-95 % extents of the flat plane's points (the convex hull was inflated by
  stray edge points). 6 Harborview: 195 sq ft (14.9 x 13.0 ft), was 223.
- Skylight labels avoid the edge-length labels and number circles (15 Ward S3 / "EAVE 7.7" overlap).
- Dormers (lidar candidates) are listed in the summary with their gutter LF and "dormer gutters: inspect and clean"; candidate
  dormers now also exclude their window patches from the skylights (0.1.7.5 used confirmed dormers only, so none were excluded).
- Deck rectangle is square to the house (longest roofprint edge); flat strips under 5 ft wide are not decks. Facet badges are part of
  the label collision check.
- Pipeline spec (docs/research/lidar_pipeline_spec.md) items folded in:
  - coplanar plane merge under a 5° normal delta (was 3°): QL2 interswath steps (<= 0.08 m) split coplanar planes;
  - metric frame check: outline edges and areas already use a WGS84 local tangent frame (lib/roofcalc.js, geodesic lengths).
    The lidar works in Web Mercator x cos(lat), which is off by about +0.15 % east / -0.22 % north; lidar line lengths are now
    re-measured geodesically from their lon/lat ends (sloped = plan x the line's lidar slope ratio), deck areas via RoofCalc.areaSqft;
  - ortho preprocessing: 5 x 5 bilateral smoothing of the roof window, 0.3 m inward erosion from the outline;
  - skylight gates: 0.30-3.5 m², aspect <= 1:3.5, long side within 10° of the eave / ridge bearing, rectangularity of the closed,
    hole-filled blob >= 0.6 (the spec's 0.78 assumes segmentation masks; 15 Ward's skylights measure 0.62-0.69 on 15 cm pixels, so
    >= 0.78 is reported as "strict" evidence instead);
  - lidar skylight evidence: missing returns (patch density < 50 % of its plane) or an intensity anomaly (< 70 % or > 150 % of the
    plane; raw EPT intensity, no range / incidence normalisation) raise the confidence to medium;
  - dormer size gate 1.5-20 m² (16-215 sq ft plan).
  - Research list (not built): MobileSAM / SAM 2.1 Hiera-Tiny (ONNX, Apache-2.0), MLS + curvature for curved roofs, CLAHE, NDVI
    (MassGIS tiles are RGB), intensity normalisation (no trajectory in EPT).
- Tests: tests/v0176_test.cjs; CI gates 15 Ward residual <= 0.2 ft, 15 Ward 2-4 counted skylights, 6 Harborview deck 150-210 sq ft.

## 0.1.7.5 (versionCode 10705) — 2026-11-15
Same rules (free data only; Google/Bing/Esri display-only; candidates NOT_PROVEN; MIT).

- 3-D view, lidar points floating ("lidar points offset 81 ft"). Root cause: NOT a CRS/datum or ortho-shift error. The EPT points
  (EPSG:3857, metres) were converted to the roofprint frame correctly, and the ortho shift was never applied to them. The 81 ft is simply
  the absolute eave elevation: the model's eave sat at 0 ft and the label called the elevation baseline an "offset". The points
  floated because the MODEL was wrong (next item), and the baseline was the median over that wrong model. Fix: eave level =
  median(z − model height) over roof points; perpendicular point-to-facet residuals (median / 90th pct / max / bias per facet) shown in the
  3-D status line and a new appendix table. A ±4.5 ft roofprint↔lidar horizontal check is applied only when it clearly helps and is
  not at the search limit (6 Harborview Rd: the limit was hit and the shift NOT applied; its 2011 roofprint covers only part of today's
  house). 15 Ward St (lidar-verified gable): median residual 0.05 ft on both facets (max 16–17 ft = chimney/trees).
- Wings rendered as single tilted slabs. Root cause in lib/facets.js gableEdges(): footprint jogs (2–3 ft), bump-outs and the long sides
  of a cross wing were chosen as gable ends (vertical walls), so a few skeleton faces swallowed whole wings (2-D diagram and 3-D alike). Fix: a
  gable end must be ≥ 6 ft with both neighbouring edges ≥ half its length; a cross wing turns off the "perpendicular to the input
  ridge" rule. 3-D heights: skeleton facets = distance from their eave line × rise/12 (ridges, hips and valleys meet); ridge-split
  gables share one ridge height.
- Snap button: the ortho lean is estimated (same method as the report) and removed before snapping; the snapped ring stays in
  roofprint coordinates.
- Roof features (candidates, on the diagram, the overlay, the Totals and the new Window view): skylights WITH sizes from the free
  MassGIS 2025 orthos at z20 with a per-facet background (dark on a sunlit facet, glare on a shaded one) plus lidar candidates; patches on a
  roof deck, at a dormer, or in clusters of 3+ are excluded. Roof decks / flat sections from lidar low-slope planes (outline, area),
  flagged "possible rubber (EPDM) or membrane roof underneath: inspect".
- Window view: one 2 × 2 report page (aerial, diagram, overlay, quick footage summary: area, squares, pitch, eave, rake, ridge, hip,
  valley, drip edge, gutters, skylights, deck) and a "Window view" button in the app.
- Benchmark: Oakcrest Road, Hingham (the "Oakrest Road" next to 15 Ward St; MassGIS L3 parcels list 1–6 Oakcrest Rd) runs as a CI
  matrix with PDFs as artifacts. Tests: tests/v0175_test.cjs (RM_ONLY_HOUSES=1 for houses only).

## 0.1.7.4 (versionCode 10704) — 2026-11-15
Same rules: free data for every measurement (MassGIS roofprints, USGS 3DEP lidar, MassGIS 2025 orthos / NAIP); Google/Bing/Esri tiles stay display-only
(no pixel access, no edge detection, no photogrammetry, no toggle for it); no accuracy claims; labels PASS / FAIL / NOT_PROVEN. MIT.

- Ortho lean/offset (new lib/orthoalign.js). Root cause: the MassGIS 2025 orthos are not true orthos, so a roof can sit metres off its roofprint
  (15 Ward St: the overlay covered the sunlit facet and the lawn, not the whole roof). Fix: bounded 2-D translation search (±8 m, 2 px grid →
  1 px → sub-pixel) that maximises the ortho gradient along the roofprint edges AND the model ridge/hip/valley lines (a sunlit/shaded facet pair
  makes the ridge the strongest edge; outline-only scoring locked an eave onto the ridge boundary, 6.2 m the wrong way), with a mild prior
  against large shifts. Confidence from peak/median and peak/second; low confidence = not applied. The PHOTO is shifted (aerial and composite
  pages), the measurements stay on the roofprint. Appendix: offset, scores, per-edge residual (1-D ±2 m search; "—" = no clear edge).
  15 Ward St: 3.7 m E, 0.7 m S, high confidence; ridge now on the light/dark boundary (before/after PNG in the delivery).
- Geocoding: town-aware. MassGIS (6 candidates) and Census prefer a match in the town typed; a match in another town gives a WARNING in the
  app and a report note; no match gives "Address not found in <TOWN>". 30 Lockwood Drive and 49 Scotland Street do not exist in Hull in
  MassGIS, Census, OSM or the L3 parcels, so the fixtures stay 30 Lockwood Dr Weymouth and 49 Scotland St Hingham (labelled with their real
  towns) and a test checks the Hull spellings are reported not found. 6 Harborview Rd Hull unchanged.
- Skylight / chimney / vent candidates from MassGIS 2025 pixels (compact bright/dark patches vs a local background inside the shifted roof),
  fused with the lidar skylight candidates (within 1.2 m → medium). Appendix only, size optional (w × h ft shown), NOT counted.
- Dormer candidates from the lidar segmentation (gable dormer: ridge between two opposite minor planes; shed dormer: minor plane flatter than
  the main plane it faces with). Dormer gutter LF estimate, returns unknown/yes/no, keep/drop and add rows in the report editor; the gutter
  section flags dormer gutters (especially with returns) for inspect-and-clean because debris there can cause water intrusion.
- Doubtful lidar ridges: a lidar ridge more than 8° off the building axes (length-weighted from the roofprint), or between planes 6/12+ apart,
  or a line with under 75% of its length inside the roofprint, becomes an appendix candidate with the reason (not counted),
  e.g. a diagonal ridge across a wing.
- 3-D roof view / editor (new view3d.js, three.js r187 MIT, lazy-loaded): orbit/zoom; facets from the roofprint + facets model + pitch, lidar
  points coloured by residual; move outline vertices, ridge/hip/valley ends; set facet pitch; re-type lines. Edits go through the existing
  tag paths (lineMoves, line types, facetPitch, ring) so the measurements and the report update; the report marks them as user edits and
  lists the data sources (and any Google/Bing/Esri layers that were only viewed). Built from free data only.
- 30 Lockwood Dr Weymouth per-facet gap re-checked (1,520.2 off vs 1,704.4 on): two high-confidence steep plane fits (F9 17/12, 192 pts,
  RMS 0.047 m; F14 11/12, 174 pts) account for ≈ +180 sq ft vs the single 3.5/12. The house has mixed pitches; NOT_PROVEN which is right.
- Version 0.1.7.4 / 10704; tests/v0174_test.cjs (CI).

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
