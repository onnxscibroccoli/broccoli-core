<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# RoofMeasure: Free OSINT + Android Report Research
Written 2026-11-15 04:20 ET by Grok Bot (research lane). Labels: PASS / FAIL / NOT_PROVEN. No accuracy claims are made for RoofMeasure.
Page: https://cursor.com/canvas/store-0e720087-d4bb-4e86-81c1-ea001b4e7a7b/dd121339-d524-471b-b433-4fcc4e24316a
Only this folder was written. No lane code was changed.

## 1. Executive ranking (top picks)
1. **Architecture: go back to the v0.1.x "live result" model, then go native.** The PDF must be a pure function of the on-screen, user-edited ReportModel. Move it from Pyodide to Kotlin `android.graphics.pdf.PdfDocument`. Keep the Python renderer as the golden reference for tests.
2. **Geometry: USGS 3DEP lidar (public domain) plus state lidar.** Use per-plane segmentation for per-facet pitch and true ridge/hip/valley topology. Roofer is GPLv3, so it fits our GPL-3.0-or-later license; use it as the reference algorithm, run off the device.
3. **Footprints:** state roofprints (MassGIS) first, then Microsoft US Building Footprints (ODbL), Overture (ODbL), and OSM last. Add FEMA USA Structures (CC BY 4.0) for height and story cross-checks.
4. **Imagery:** state orthos (MassGIS 15 cm, no restrictions), with NAIP (public domain, 60 cm) as the national fallback. OpenAerialMap (CC BY 4.0) where it exists. Mapillary/KartaView (CC BY-SA 4.0) and the user's own photos stand in for obliques.
5. **Discovery ("dorking"):** run Google/Bing operators by hand, plus the ArcGIS Hub Search API, the Common Crawl CDX index, and data.gov CKAN, to build a curated in-app registry of county parcel, permit, ortho and lidar endpoints. Don't automate SERP scraping. The Bing Search API was retired on 2025-08-11, and Google Custom Search is closed to new customers and ends on 2027-01-01.

**Avoid as measurement sources (their ToS forbid derived content):** Google Maps/Earth imagery and 45° imagery (ToS 3.2.3(c)); Bing/Azure Maps imagery; Esri World Imagery and Wayback exports (ArcGIS-only, with non-commercial limits on derived data); Apple Maps; Zillow/Redfin photo scraping; county Pictometry/EagleView viewers. The Google Solar API is acceptable only as an optional live cross-check with the user's own key, and its values should not be stored in the exported PDF (3.2.3(a)/(b)).

## 2. v0.1.7 vs v0.2.0: what v0.1.7 did better (evidence)
- v0.1.7 located: PASS. `/home/box/sand-data/agents/f8be2535-0d5d-488d-9a98-cf1eec4a8b8e/attachments/76020d4e9cde9693….apk`: 6,216,560 B, versionCode 7, versionName 0.1.7, built 01:18 ET 2026-11-15 (aapt2 badging). Source: `roofmeasure/web/report.js` (01:16), with the changelog in `roofmeasure/apk/HANDOFF.md` lines 26–31.
- v0.2.0: `artifacts/roof-overlay/deliver/send/RoofMeasure-pdf-debug-small.apk`, 19.7 MB, versionCode 200, a repack of the 27 MB build. Source: `roofmeasure/apk-pdf/`.

| Aspect | v0.1.7 (`web/report.js`) | v0.2.0 (`apk-pdf/web/report-*.js`) | Verdict |
|---|---|---|---|
| Input to report | `buildResult(app)` deep-copies the live `state.result` (report.js:87-141): on-screen edge labels, manual pitch, the user's ridge toggle (`#useRidge`), and the lidar result already computed | `report-launch.js` passes only the footprint geometry, address and source through sessionStorage; `report-app.js:69-122` re-runs lidar and recomputes everything | v0.1.7 better: the report matches what the user saw and edited. v0.2.0 discards edits (its README "Limits" says so) |
| Lidar | Reuses the on-screen lidar result | Re-fetches EPT (up to a 50 s timeout). On failure it falls back to "ASSUMED 6/12" even when the map had a lidar pitch | v0.1.7 better: one fetch, no silent downgrade |
| Size | 6.2 MB APK; Pyodide core only (14 MB unpacked), no numpy/shapely/pyproj | 27 MB (19.7 MB repack); Pyodide plus numpy, shapely, pyproj wheels | v0.1.7 better |
| Speed (headless desktop) | measure 2.63 s + first report 1.89 s (`android/tests/evidence/report_export_test.json`) | 6.8 s total (`apk-pdf/test/out_15ward/status.json`); the README estimates 10–60 s on a phone | v0.1.7 better |
| UI thread | Async fetch for aerial tiles (10 s abort each) | Synchronous XHR on the main thread for extras, assessor and aerial (README "Limits") | v0.1.7 better: v0.2.0 can freeze or ANR-risk |
| Navigation | Stays on the map page; offscreen WebView, then PrintManager (`printHtml`) | Navigates to report.html, the report replaces the page, then `printPdf` | v0.1.7 keeps state; v0.2.0 loses map state |
| Sections | 11 headings (no Diagram text description, Detached structures or Solar) | 14 headings, identical to the 15 Ward reference (`apk-pdf/test/compare_15ward.json`) | v0.2.0 more complete |
| On-device | Ian reports it produced a report: PASS (per Ian) | Ian reports v0.1.7 was better, which implies v0.2.0 did not produce a usable report: FAIL (per Ian), cause NOT_PROVEN | |

Conclusion: v0.1.7's live-result principle is right; v0.2.0's section completeness is right. The v0.1.8/0.1.9 line (`apk/HANDOFF.md` 33-51) already combines both: live result, Review & correct sheet, structures, solar, 6.3 MB, at `artifacts/roof-overlay/apk/RoofMeasure-debug.apk` (v0.1.9). It is the best immediate baseline, though on-device it is NOT_PROVEN.
Side finding: `android/www/lidar/pitch.js:85-111` already fits up to 6 RANSAC planes, but the report collapses them to one predominant pitch plus an equal-pitch straight-skeleton (`facets.js`). This is the biggest accuracy lever.

## 3. Source comparison
| Source | Coverage | Resolution | Cost | License / ToS | Access | Verdict |
|---|---|---|---|---|---|---|
| USGS 3DEP lidar | Most of CONUS, varies by project year | QL2 ≥2 pts/m²; QL1 ≥8 | Free | Public domain | EPT `s3://usgs-lidar-public` (AWS registry); COPC via Planetary Computer | TOP |
| MassGIS lidar + Building Structures | MA | Roofprints ≥150 sq ft, updated with 2021 imagery + lidar nDSM | Free | MassGIS open | ArcGIS REST | TOP (MA) |
| MassGIS orthos 2021/2023/2025 | MA | 15 cm (2025 Cape Cod 7.5 cm) | Free | "No restrictions", attribution appreciated | ArcGIS tile service | TOP (MA) |
| Other state ortho/lidar clearinghouses | Varies | Often 15–30 cm | Free | Usually public; check each | WMS/WMTS/ArcGIS | HIGH via registry |
| NAIP (USDA) | CONUS | 60 cm (some 30 cm) | Free | Public domain | AWS / Planetary Computer | Fallback image |
| Microsoft US Building Footprints | US | ML footprints (eave-ish) | Free | ODbL | GitHub downloads | Fallback footprint |
| Microsoft Global ML Footprints | Global, some heights | ML | Free | CDLA-Permissive-2.0 | GitHub | Fallback |
| Overture buildings | Global | Conflated OSM/MS/Google | Free | ODbL | GeoParquet (S3/Azure) | Fallback |
| OSM | Global | Variable | Free | ODbL | Overpass | Last resort |
| Google Open Buildings | Africa, S/SE Asia, LatAm, Caribbean; not the US | ML | Free | CC BY 4.0 / ODbL | Downloads | Not for US |
| FEMA USA Structures | US | Footprints + HEIGHT (m) | Free | CC BY 4.0 | FeatureServer + state FGDB | Height/story cross-check |
| County parcels/assessor | Varies | Year built, style, stories, sometimes roof cover | Free | Public records; varies | ArcGIS REST/Socrata | HIGH |
| Building permits | City/county open data | Roof replacement dates | Free | Public | Socrata/ArcGIS | Roof age |
| NOAA SPC storm reports / FEMA NFHL | US | Point reports / flood zones | Free | Public domain | CSV/REST | Hail/wind history (matches GAF's $10 add-on) |
| NLR (ex-NREL) PVWatts v8 | Global | Monthly kWh | Free key, rate-limited | US gov | developer.nlr.gov (nrel.gov retired) | Solar section |
| Google Solar API | 40+ countries, 472M buildings | Roof segments, pitch, azimuth | buildingInsights 10k/mo free; dataLayers 1k/mo | Maps ToS: no scraping/caching/derived content | REST, billing required | Optional live cross-check only |
| Project Sunroof | US | Area aggregates | Free | No per-building API | Data Explorer | Avoid |
| Google Maps/Earth imagery | Global | High | Paid/free tiers | 3.2.3(c) forbids tracing outlines or 3D models from imagery | — | AVOID |
| Bing/Azure Maps imagery | Global | High | Bing basic retired 2025-06-30 | Derivative works prohibited | — | AVOID |
| Esri World Imagery/Wayback | Global | High | Viewer free | Export needs ArcGIS org; derived data ArcGIS-only, non-commercial | — | AVOID (link-out for history only) |
| Apple Maps/MapKit | Global | High | — | Display only | — | AVOID |
| OpenAerialMap | Spotty | Drone/aerial cm-class | Free | CC BY 4.0 | API | HIGH when present |
| Mapillary / KartaView | Street-level | Photos | Free token | CC BY-SA 4.0 | API v4 | Elevation photos, gable pitch cross-check |
| Sentinel-2 | Global | 10 m | Free | Copernicus open | — | AVOID for geometry |
| User capture (photos, ARCore, drone+ODM) | Per job | cm-class | Free | User-owned; ODM AGPL (run off-device) | — | Best verification |

## 4. Dorking playbook (lawful discovery)
Google and Bing operators (run by hand in a browser; automated SERP scraping breaks the engines' terms):
- `intitle:"ArcGIS REST Services Directory" (building OR roofprint OR footprint) site:.gov`
- `inurl:"/arcgis/rest/services" inurl:FeatureServer (parcel OR assessor) "Year Built"`
- `inurl:ImageServer (lidar OR DSM OR nDSM OR "first return") site:.gov OR site:.us`
- `inurl:MapServer (orthos OR orthoimagery OR "aerial 2025" OR "leaf-off")`
- `inurl:"service=WMS" "GetCapabilities" orthoimagery` and `inurl:WMTSCapabilities.xml`
- `site:hub.arcgis.com ("building permits" OR "roof permit")`
- `site:data.*.gov roof permit` (Socrata)
- Bing extras: `instreamset:url:FeatureServer`, `contains:xml`, `inbody:"Year Built"`
- Oblique viewers (`"pictometry" OR "oblique" county viewer`): identify only. They are licensed, so don't scrape them.
Programmatic and lawful: ArcGIS Hub Search API (`hub.arcgis.com/api/search`); a service's own `?f=json`; the Common Crawl CDX index (`index.commoncrawl.org`, `url=*.arcgis.com/rest/services*`); data.gov CKAN; the USGS TNM Access API.
Legal notes: use only endpoints offered publicly without a login. Read each service's copyrightText, licenseInfo and "Use Limitations". Honor maxRecordCount, rate limits and robots.txt. Never reuse tokens or bypass auth. Minimize owner PII. Attribute every source in the PDF.

## 5. Accuracy methods
1. Per-facet lidar planes: normal-based region growing, then RANSAC refine, then a plane adjacency graph. Convex horizontal intersections are ridges, convex sloped ones are hips, concave ones are valleys, and outer boundaries are eaves or rakes. Clip to the roofprint. Reference implementations: Roofer (GPLv3, LoD2.2; needs about 10 pts/m² for good results), City3D, PolyFit.
2. Per-facet confidence from inlier count, RMS residual and plane-normal standard error. QL2 density (≥2 pts/m²) gives about 40 points on a 20 m² facet; flag low-support facets NOT_PROVEN.
3. Cross-validation: lidar pitch vs gable-photo pitch (phone gravity sensor or Mapillary) vs assessor style; roofprint area vs MassGIS AREA_SQ_FT vs MS footprint IoU; overhang from lidar returns outside the footprint; lidar vintage vs newest ortho (change detection).
4. Benchmarks to cite (no RoofMeasure claim): lidar roof-tilt MAE about 3° at 1 m and 5.0° at 2 m (IET RPG 2015, doi:10.1049/iet-rpg.2015.0388). EagleView-commissioned CompassData 2025: average area error 3.0%, slope error 1.1%. GAF: "about 95%" with a replacement policy. Haag/Kespry drone: 0.6% average area error. Building3D: a public roof-reconstruction benchmark.
5. Our own benchmark: 20 or more houses with tape/drone truth; report error per metric with PASS/FAIL thresholds before any accuracy wording.
6. Waste: a suggested % from complexity (facet count, hip+valley LF ratio), shown next to a 0–20% table, like EagleView's "Suggested".
7. Field capture: ARCore Raw Depth works best at 0.5–5 m, so it suits close detail, not roofs from the ground. Drone plus OpenDroneMap (AGPL, run off-device) is the highest-accuracy free path.

## 6. Android display / edit / export / share
- **ReportModel JSON** (versioned) as the single source of truth: property, sources[], roofprint, facets[{polygon, pitch, pitch_source, confidence}], edges[{type, length, auto_length, edited}], structures, photos[{uri, caption, markup}], notes, edit log.
- **UI:** Kotlin + Jetpack Compose. MapLibre Native Android (BSD-2) for the map and editing; osmdroid was archived on 2024-11-20. A Compose Canvas diagram editor: drag vertices, tap an edge to set its type, set per-facet pitch.
- **PDF:** native `android.graphics.pdf.PdfDocument` + Canvas: vector text, no dependencies, sub-second. Keep the WebView `createPrintDocumentAdapter` HTML path only as a fallback. PdfBox-Android (Apache-2.0) for merge and metadata. Avoid iText (AGPL/commercial) and on-device Pyodide (27 MB, 10–60 s).
- **Preview:** androidx.pdf `PdfViewerFragment` (1.0.0-beta01) or `EditablePdfViewerFragment` for ink markup; platform `PdfRenderer` as the fallback.
- **Share:** write to `cacheDir/reports/`, get a `FileProvider` URI, send `ACTION_SEND` with `application/pdf` and `FLAG_GRANT_READ_URI_PERMISSION`. Save with SAF `ACTION_CREATE_DOCUMENT`. Also export JSON, CSV, XML and DXF (QuickMeasure ships PDF/XML/DXF).
- **Offline:** Room for jobs, WorkManager for fetches, cached tiles only from open-licensed sources.
- **Tests:** the Python `build_report.py` output is the golden file; extend `apk-pdf/test/compare.py` (pages, headings, text) to the native PDF.

## 7. Feature parity (NOT_PROVEN = not verified from the vendor sample)
| Item | QuickMeasure | EagleView Premium | Hover | RoofMeasure now | Plan |
|---|---|---|---|---|---|
| Top-view aerial | Yes | Yes | Photos | Yes (MassGIS) | Per-edge markings |
| Obliques/side views | Side views, Past Views & Multiple Angles | N/S/E/W | User photos | No | Mapillary + user photos |
| 3D model | Interactive 3D, editable | 3D image | Interactive 3D | viewer3d lane (not in PDF) | LoD2 from lidar planes |
| Length diagram | Yes | Yes | Yes | Yes | — |
| Pitch per facet | Yes | Yes + arrows | Facets page | Single pitch | Per-facet lidar |
| Area per facet | Yes | Yes | Yes | Equal-pitch facets | Per-facet |
| Ridge/hip/valley/rake/eave | Yes | Yes | Yes | Yes | — |
| Flashing/step flashing | NOT_PROVEN | Yes | Yes | wall_flashing_lf | Lidar wall jumps |
| Penetrations | NOT_PROVEN | Yes | NOT_PROVEN | No | Manual + ortho |
| Waste table + suggested | Yes | Yes | Yes | 0–20% table | Complexity-suggested |
| Bill of materials | Yes | NOT_PROVEN | Yes | Gutters & materials | Expand |
| Attic estimate / ventilation | Yes | Estimated attic | NOT_PROVEN | No | Add |
| Structure complexity | NOT_PROVEN | Yes | NOT_PROVEN | No | Add |
| Multi-structure summary | Multi-family | All Structures | NOT_PROVEN | Detached structures | — |
| XML/DXF export | Yes | NOT_PROVEN | NOT_PROVEN | JSON/CSV | Add |
| Hail/wind history, codes | $10 add-on | NOT_PROVEN | No | No | NOAA SPC |
| Siding/windows | No | Separate product | Full exterior | No | Later |
| In-app edit | 3D edit | No | Yes | Review & correct (v0.1.8+) | Full editor |
| Data provenance per value | No | No | No | Yes | Keep |
| Solar | No | Separate | No | Yes | — |
| Assessor data | No | No | No | Yes | — |
| Price | $18–20 | Paid | Paid | Free | — |

## 8. Roadmap
- P0: make v0.1.9 (live result) the baseline and test it on Ian's phone. Keep Pyodide off the default path; if it is kept, the report must consume the live model.
- P1: ReportModel JSON + native PdfDocument renderer with all 14 reference sections; golden compare; FileProvider share; SAF save; PdfViewer preview.
- P2: per-facet lidar planes and edge topology with confidence; per-edge markings on the aerial photo; complexity-suggested waste; attic/complexity rows.
- P3: Compose and MapLibre editor; photo gallery with markup; edit log printed in Notes.
- P4: endpoint registry from Hub, Common Crawl and manual dorks; NAIP, MS footprints and FEMA fallbacks outside MA; NOAA storm history; permit-based roof age; XML/DXF export.
- P5: field capture (gable photo pitch gauge, Mapillary, drone/ODM import); 20+ house benchmark; publish PASS/FAIL error tables.

## Sources
- https://registry.opendata.aws/usgs-lidar/ ; https://www.usgs.gov/ngp-standards-and-specifications/lidar-base-specification-tables ; https://planetarycomputer.microsoft.com/dataset/group/3dep-lidar
- https://www.mass.gov/info-details/massgis-data-2025-aerial-imagery ; https://www.mass.gov/info-details/massgis-data-building-structures-2-d
- https://github.com/microsoft/USBuildingFootprints ; https://github.com/microsoft/GlobalMLBuildingFootprints ; https://docs.overturemaps.org/guides/buildings/
- https://gis-fema.hub.arcgis.com/pages/usa-structures
- https://developers.google.com/maps/billing-and-pricing/pricing ; https://cloud.google.com/maps-platform/terms ; https://developers.google.com/maps/documentation/tile/policies
- https://learn.microsoft.com/en-us/answers/questions/2344821/ ; https://blogs.bing.com/maps/2025/1/What-are-my-options-regarding-Bing-Maps-for-Enterprise-Retirement/
- https://www.esri.com/arcgis-blog/products/arcgis-living-atlas/imagery/wayback-export
- https://developer.nlr.gov/docs/solar/pvwatts/v8/ ; https://github.com/pvlib/pvlib-python/pull/2705
- https://help.mapillary.com/hc/en-us/articles/115001770409-CC-BY-SA-license-for-open-data
- https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement ; https://developers.google.com/custom-search/v1/overview
- https://developers.arcgis.com/hub/services/search/ ; https://index.commoncrawl.org/ ; https://commoncrawl.org/terms-of-use
- https://github.com/3DBAG/roofer ; https://innovation.3dbag.nl/roofer/data_requirements.html ; https://github.com/tudelft3d/City3D ; https://building3d.ucalgary.ca/ ; https://roofn3d.gis.tu-berlin.de/
- https://doi.org/10.1049/iet-rpg.2015.0388 ; https://www.eagleview.com/wp-content/uploads/2025/07/CompassData-Roof-Measurements-Analysis-2025-.pdf ; https://www.prnewswire.com/news-releases/independent-study-by-haag-engineering-verifies-the-precision-and-efficacy-of-using-kespry-industrial-drones-for-measuring-and-inspecting-roofs-300507406.html
- https://developers.google.com/ar/develop/java/depth/raw-depth
- https://github.com/osmdroid/osmdroid ; https://github.com/maplibre/maplibre-native ; https://developer.android.com/jetpack/androidx/releases/pdf ; https://developer.android.com/reference/android/graphics/pdf/PdfDocument ; https://developer.android.com/reference/androidx/core/content/FileProvider ; https://github.com/TomRoush/PdfBox-Android
- https://www.eagleview.com/wp-content/uploads/2025/07/Premium-Sample-Report-Residential-1.pdf (copy in refs/ev_premium.pdf) ; https://www.gaf.com/en-us/resources/business-services/quickmeasure ; https://help.hover.to/en/articles/1215021-understanding-hover-s-measurement-pdf
