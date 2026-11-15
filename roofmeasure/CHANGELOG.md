<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure changelog (0.1.7.x line — stays on 0.1.7.x until Ian verifies an improvement)

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
