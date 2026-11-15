<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure changelog (0.1.7.x line — stays on 0.1.7.x until Ian verifies an improvement)

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
