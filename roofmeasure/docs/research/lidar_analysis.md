# RoofMeasure 0.1.7.3: lidar analysis (per-facet fits and whole-roof segmentation)

Status: **NOT_PROVEN**. We have no ground truth except Ian's statement that 15 Ward St, Hingham is 12/12; the lidar agrees with that.
Nothing here is an accuracy claim. Generated 2026-11-15 (America/New_York) from the headless app (same code as the APK).

## Data used
- **Source:** USGS 3DEP lidar served as **Entwine Point Tiles (EPT)**: `s3-us-west-2.amazonaws.com/usgs-lidar-public/<dataset>/ept.json`.
  The hierarchy is in ept-hierarchy/*.json, and point data is LAZ in ept-data/*.laz, decoded in-app with laz-perf (WASM).
  - We query EPT nodes by bounding box, not COPC; COPC files exist for some 3DEP projects, but the EPT bucket covers all of them.
  - Datasets: `MA_CentralEastern_1_2021` first, then `MA_NE_CMGP_Sandy_Z19_A1_2015`. Coordinates are EPSG:3857 (Web Mercator); heights are metres.
- **Classes (ASPRS):**
  - Class 6 (building) is used for the roof.
  - Class 2 (ground) gives the ground height.
  - 1 (unclassified), 3/4/5 (vegetation), 7 (noise) and 18 (high noise) are ignored.
  - If there are fewer than 30 class-6 points, non-ground points more than 2 m above ground are used instead.
- **Point density:** at 15 Ward St, 1,238 building points cover a roof of about 133 m² plan plus the buffer, so about 7 pts/m². Scan lines are about 0.7 m apart.
- **Intensity:** present (uint16, offset 12 in every LAS point format). Values at 15 Ward St range from about 21,800 to 62,000.
  - It is used only as weak evidence for skylight candidates (low-intensity clusters).
  - Return number and scan angle are not used yet.
- **What each step reads:**
  - pitch.js (single pitch) uses class-6 points inside the footprint with a 0.6 m inset.
  - facetfit.js uses the same set, with points kept at least 0.5 m from the facet boundary.
  - roofseg.js uses all building points with no inset, plus a 1.2 m buffer outside the footprint. That buffer keeps narrow strips and eave overhangs.
- **Vintage:** the lidar is from 2021 and the roofprints are from 2011–2019 (MassGIS). Additions built after 2021, and lean in the 2025 orthos, are not visible in the lidar.

## Methods
1. **Single pitch (0.1.7.2, unchanged):** global RANSAC planes, then a weighted pitch.
2. **Per-facet fit (lidar/facetfit.js):**
   - Take the points inside each model facet polygon, at least 0.5 m from its boundary.
   - Fit RANSAC (0.15 m, fixed seed), then Tukey IRLS with MAD scale.
   - Report n, inliers, RMS, rise ± standard error, x/12 snapping (nearest whole x/12 within 0.5), aspect vs model downslope, and confidence high/medium/low.
   - Status is `fit`, `aspect_mismatch` (>30°) or `too_few_points` (<12).
   - Coplanar facets (slope ≤2.5°, aspect ≤12°, offset ≤0.2 m) are grouped and refit.
3. **Model choice (lib/roofmodel.js):**
   - score = inliers of usable facets ÷ points in facets, for simple gable, wings (skeleton) and hip.
   - The model is lidar-verified if the best score is ≥0.6.
   - Otherwise, if ≥2 confident lidar hip lines exist and hip scores at least as high as simple, hip is chosen as lidar-verified.
   - Otherwise the model is ASSUMED (simple if the footprint fills ≥85% of its minimum bounding rectangle, else wings), and its hips/valleys are not counted.
4. **Whole-roof segmentation (lidar/roofseg.js):**
   - Fit a local plane per point (neighbours within 1.1 m).
   - Region-grow from the flattest seeds (normal ≤12°, plane distance ≤0.18 m).
   - Refit each region robustly and merge coplanar regions.
   - Keep planes of ≥6 points; planes under 25 points or 40 sq ft are flagged as small, not dropped.
   - Find boundary pairs (≤1 m) between planes and classify each boundary:
     - Height gap <0.35 m: intersection line, either ridge (horizontal, convex), hip (sloped, convex) or valley (concave).
     - Otherwise: step edge. It is wall flashing (headwall or sidewall) only when the lower plane runs up or alongside the step. Otherwise it is the upper plane's eave or rake.
     - Steps that lie on the footprint are already counted as outline edges.
   - Remove near-collinear duplicates.
   - Skylight candidates: 0.5 m cells inside planes that are point voids surrounded by points, dips below −0.12 m, or low intensity (z < −2.5, ≥3 cells). Each is 0.5–6 m², at least 1 m from the boundary, and always low confidence.
5. **Reconciliation (tags.js):**
   - A confident lidar line (high confidence, no small plane) that overlaps a model line confirms or re-types it. The model line keeps its roofprint-snapped length.
   - Lidar lines the model lacks are clipped to the roofprint and added. They are counted if confident; otherwise they are candidates.
   - The user can confirm, delete or re-type any line.

## Per-site results (all MassGIS roofprints, lidar MA_CentralEastern_1_2021)

| Site | Building pts (inset) | Single pitch | Shape guess | Scores simple / wings / hip | Chosen model | Area single / per-facet new / per-facet old (sq ft) |
|---|---|---|---|---|---|---|
| PRIVATE complex test house (local only) | 9593 | 8/12 | complex | 0.164 / 0.31 / 0.37 | wings (assumed) | 5270.9 / 5303.5 / 4940.6 |
| 15 WARD STREET, HINGHAM, MA, 02043 | 867 | 12/12 | gable | 0.885 / 0.881 / 0.632 | simple (lidar-verified) | 2023.5 / 2023.5 / 2023.5 |
| 250005_887609 | 3192 | 5/12 | shed_or_partial | 0.26 / 0.256 / 0.153 | simple (assumed) | 1316.7 / 1316.7 / 1316.7 |
| 249469_887717 | 2435 | 10.5/12 | gable | 0.877 / 0.876 / 0.516 | simple (lidar-verified) | 1787.9 / 1751.5 / 1769.7 |
| 249754_888132 | 1477 | 6.5/12 | gable | 0.95 / 0.95 / 0.717 | simple (lidar-verified) | 2733.0 / 2734.4 / 2733.0 |
| 257290_888447 | 2805 | 7.5/12 | gable | 0.759 / 0.756 / 0.5 | simple (lidar-verified) | 1846.6 / 1882.0 / 1864.3 |
| 257552_888022 | 3018 | 4.5/12 | hip | 0.527 / 0.518 / 0.758 | hip (lidar-verified) | 2367.3 / 2401.3 / 2373.8 |
| 257506_887663 | 990 | 8/12 | gable | 0.781 / 0.778 / 0.53 | simple (lidar-verified) | 1953.8 / 1953.8 / 1953.8 |
| 263376_883117 | 1039 | 5/12 | gable | 0.53 / 0.531 / 0.449 | simple (assumed) | 1673.5 / 1673.5 / 1673.5 |
| 263663_883484 | 2809 | 5/12 | hip | 0.648 / 0.649 / 0.892 | hip (lidar-verified) | 2095.1 / 2095.1 / 2111.2 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | 1890 | 3.5/12 | complex | 0.536 / 0.572 / 0.604 | hip (lidar-verified) | 1520.2 / 1704.3 / 1865.9 |
| 49 SCOTLAND STREET, HINGHAM, MA, 02043 | 1820 | 4/12 | gable | 0.916 / 0.877 / 0.69 | simple (lidar-verified) | 1533.2 / 1533.2 / 1533.2 |
| 6 HARBORVIEW ROAD, HULL, MA, 02045 | 911 | 8.5/12 | complex | 0.488 / 0 / 0.533 | simple (assumed) | 1783.2 / 1801.0 / 1783.2 |

### Per-facet fits of the chosen model

| Site | Facet | Plan sq ft | Points / inliers | RMS m | Rise raw ± se | Snapped | Aspect Δ° | Confidence | Status | Old method pitch |
|---|---|---|---|---|---|---|---|---|---|---|
| PRIVATE complex test house (local only) | F1 | 2115.2 | 4705 / 1309 | 0.041 | 5.7 ± 0.01 | 6/12 | 1.1 | low | fit | 5.5/12 |
| PRIVATE complex test house (local only) | F5 | 918.7 | 1641 / 600 | 0.021 | 3.58 ± 0.01 | 4/12 | 79.6 | low | aspect_mismatch | 5.5/12 |
| PRIVATE complex test house (local only) | F9 | 69.9 | 47 / 43 | 0.021 | 8.02 ± 0.05 | 8/12 | 0.4 | medium | fit | 8/12 |
| PRIVATE complex test house (local only) | F11 | 846.4 | 1722 / 808 | 0.025 | 8.14 ± 0.01 | 8/12 | 1 | medium | fit | 8/12 |
| PRIVATE complex test house (local only) | F15 | 225.8 | 338 / 290 | 0.023 | 9.61 ± 0.03 | 10/12 | 1.9 | high | fit | 8/12 |
| PRIVATE complex test house (local only) | F17 | 209.7 | 244 / 242 | 0.042 | 9.49 ± 0.07 | 9/12 | 0.2 | high | fit | 5.5/12 |
| 15 WARD STREET, HINGHAM, MA, 02043 | FA | 672.8 | 378 / 326 | 0.022 | 12.04 ± 0.01 | 12/12 | 0.1 | high | fit | 12/12 |
| 15 WARD STREET, HINGHAM, MA, 02043 | FB | 758.0 | 385 / 349 | 0.024 | 12.02 ± 0.01 | 12/12 | 0 | high | fit | 12/12 |
| 250005_887609 | FA | 607.7 | 1518 / 1360 | 1.033 | 3.18 ± 0.27 | 3/12 | 43.7 | low | aspect_mismatch | 5/12 |
| 250005_887609 | FB | 607.7 | 1243 / 718 | 0.025 | 4.81 ± 0.01 | 5/12 | 0.4 | medium | fit | 5/12 |
| 249469_887717 | FA | 672.8 | 1095 / 977 | 0.034 | 10.24 ± 0.01 | 10/12 | 0.4 | high | fit | 10/12 |
| 249469_887717 | FB | 672.8 | 1079 / 929 | 0.026 | 10.25 ± 0.01 | 10/12 | 0.3 | high | fit | 10.5/12 |
| 249754_888132 | FA | 1201.5 | 651 / 614 | 0.029 | 6.41 ± 0.01 | 6/12 | 0.7 | high | fit | 6.5/12 |
| 249754_888132 | FB | 1201.6 | 716 / 685 | 0.046 | 6.65 ± 0.01 | 7/12 | 1 | high | fit | 6.5/12 |
| 257290_888447 | FA | 783.0 | 1248 / 947 | 0.045 | 7.78 ± 0.02 | 8/12 | 0.3 | high | fit | 8/12 |
| 257290_888447 | FB | 783.0 | 1208 / 918 | 0.03 | 7.57 ± 0.01 | 8/12 | 0 | high | fit | 7.5/12 |
| 257552_888022 | F0 | 427.9 | 335 / 304 | 0.029 | 4.9 ± 0.02 | 5/12 | 1.7 | high | fit | 5/12 |
| 257552_888022 | F1 | 680.3 | 716 / 604 | 0.02 | 4.75 ± 0.01 | 5/12 | 0.6 | high | fit | 4.5/12 |
| 257552_888022 | F2 | 427.9 | 478 / 356 | 0.019 | 4.69 ± 0.02 | 5/12 | 1 | high | fit | 4.5/12 |
| 257552_888022 | F3 | 680.3 | 866 / 552 | 0.022 | 4.79 ± 0.01 | 5/12 | 1 | high | fit | 4.5/12 |
| 257506_887663 | FA | 812.8 | 475 / 444 | 0.046 | 7.92 ± 0.02 | 8/12 | 0 | high | fit | 8/12 |
| 257506_887663 | FB | 812.8 | 425 / 259 | 0.054 | 7.85 ± 0.04 | 8/12 | 0 | high | fit | 8/12 |
| 263376_883117 | FA | 772.2 | 471 / 280 | 0.02 | 5.07 ± 0.02 | 5/12 | 0.3 | medium | fit | 5/12 |
| 263376_883117 | FB | 772.6 | 446 / 206 | 0.023 | 5 ± 0.04 | 5/12 | 0.2 | medium | fit | 5/12 |
| 263663_883484 | F0 | 670.6 | 891 / 772 | 0.027 | 5.18 ± 0.01 | 5/12 | 1.3 | high | fit | 5/12 |
| 263663_883484 | F1 | 296.4 | 299 / 288 | 0.02 | 4.98 ± 0.02 | 5/12 | 1 | high | fit | 5/12 |
| 263663_883484 | F2 | 670.6 | 748 / 651 | 0.022 | 5.23 ± 0.01 | 5/12 | 0.7 | high | fit | 5.5/12 |
| 263663_883484 | F3 | 296.4 | 293 / 279 | 0.023 | 5.36 ± 0.02 | 5/12 | 0.7 | high | fit | 5.5/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F0 | 30.6 | 0 / None | None | None ± None | None | None | None | too_few_points | 3.5/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F1 | 98.3 | 76 / 76 | 0.016 | 3.26 ± 0.06 | 3/12 | 89.4 | low | aspect_mismatch | None |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F2 | 88.4 | 57 / 45 | 0.035 | 4.11 ± 0.19 | 4/12 | 5.9 | medium | fit | 3.5/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F3 | 24.9 | 0 / None | None | None ± None | None | None | None | too_few_points | None |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F4 | 38.3 | 8 / None | None | None ± None | None | None | None | too_few_points | 3.5/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F5 | 32.1 | 0 / None | None | None ± None | None | None | None | too_few_points | 17/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F6 | 157.0 | 92 / 70 | 0.056 | 3.77 ± 0.24 | 4/12 | 12.7 | high | fit | 3.5/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F7 | 80.3 | 7 / None | None | None ± None | None | None | None | too_few_points | None |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F8 | 108.6 | 22 / 18 | 0.045 | 4.13 ± 0.43 | 4/12 | 0.2 | low | fit | 3.5/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F9 | 192.7 | 192 / 178 | 0.047 | 17.05 ± 0.09 | 17/12 | 1.7 | high | fit | 17/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F10 | 72.5 | 35 / 27 | 0.087 | 15.7 ± 0.54 | 16/12 | 89.5 | low | aspect_mismatch | 11/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F11 | 28.0 | 0 / None | None | None ± None | None | None | None | too_few_points | None |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F12 | 177.7 | 132 / 64 | 0.037 | 0.73 ± 0.14 | 1/12 | 6 | medium | fit | 11/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F13 | 82.1 | 50 / 31 | 0.042 | 10.97 ± 0.45 | 11/12 | 93.4 | low | aspect_mismatch | 17/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F14 | 172.6 | 174 / 170 | 0.024 | 11.04 ± 0.04 | 11/12 | 0 | high | fit | 11/12 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | F15 | 75.3 | 58 / 37 | 0.028 | 10.61 ± 0.15 | 11/12 | 89.5 | low | aspect_mismatch | None |
| 49 SCOTLAND STREET, HINGHAM, MA, 02043 | FA | 727.2 | 840 / 733 | 0.016 | 3.82 ± 0.01 | 4/12 | 0.2 | high | fit | 4/12 |
| 49 SCOTLAND STREET, HINGHAM, MA, 02043 | FB | 727.2 | 743 / 655 | 0.016 | 3.89 ± 0.01 | 4/12 | 0.2 | high | fit | 4/12 |
| 6 HARBORVIEW ROAD, HULL, MA, 02045 | FA | 726.6 | 391 / 228 | 0.022 | 8.57 ± 0.02 | 9/12 | 0.1 | medium | fit | 8.5/12 |
| 6 HARBORVIEW ROAD, HULL, MA, 02045 | FB | 728.6 | 433 / 190 | 0.029 | 8.5 ± 0.02 | 9/12 | 0 | low | fit | 8.5/12 |

### Whole-roof segmentation summary

| Site | Points | Coverage | Planes (small) | Lines: ridge / hip / valley (LF, confident) | Steps: wall flashing / eave / rake (LF) | Skylight candidates |
|---|---|---|---|---|---|---|
| PRIVATE complex test house (local only) | 12780 | 87% | 25 (7) | 173.1 / 70.2 / 34.3 | 154.7 / 0 / 16.5 | 7 |
| 15 WARD STREET, HINGHAM, MA, 02043 | 1238 | 96% | 2 (0) | 45.4 / 0 / 0 | 0 / 0 / 0 | 0 |
| 250005_887609 | 4545 | 61% | 4 (1) | 34.0 / 0 / 0 | 5.6 / 0 / 0 | 0 |
| 249469_887717 | 3647 | 90% | 5 (2) | 49.7 / 28.0 / 0 | 0 / 0 / 0 | 0 |
| 249754_888132 | 1975 | 94% | 3 (1) | 42.9 / 0 / 0 | 0 / 0 / 0 | 0 |
| 257290_888447 | 3937 | 95% | 6 (1) | 71.5 / 66.4 / 0 | 0 / 0 / 0 | 0 |
| 257552_888022 | 4261 | 91% | 9 (4) | 65.1 / 96.2 / 0 | 0 / 0 / 0 | 2 |
| 257506_887663 | 1401 | 98% | 5 (0) | 53.8 / 21.5 / 18.5 | 42.3 / 0 / 0 | 1 |
| 263376_883117 | 1387 | 96% | 5 (1) | 40.1 / 9.8 / 0 | 70.0 / 0 / 0 | 0 |
| 263663_883484 | 3656 | 93% | 10 (2) | 17.1 / 83.7 / 0 | 0 / 0 / 0 | 2 |
| 30 LOCKWOOD DR, WEYMOUTH, MA, 02190 | 3044 | 77% | 8 (2) | 53.5 / 0 / 6.0 | 25.4 / 0 / 0 | 0 |
| 49 SCOTLAND STREET, HINGHAM, MA, 02043 | 2576 | 90% | 4 (1) | 39.4 / 0 / 0 | 0 / 0 / 0 | 0 |
| 6 HARBORVIEW ROAD, HULL, MA, 02045 | 1358 | 94% | 8 (0) | 27.1 / 103.0 / 14.8 | 30.9 / 0 / 0 | 1 |

## Findings
- **15 Ward St, Hingham (known 12/12):**
  - Both facets fit 12.04 ± 0.01 and 12.02 ± 0.01 (RMS 0.022–0.024 m, about 330 inliers each), snapped to 12/12 with high confidence. This agrees with the known pitch (one house; NOT_PROVEN in general).
  - Segmentation finds exactly two planes and one ridge.
  - The west jog is the same SW plane continuing as a ~1.2 ft plan strip past the ridge. It ends at the eave of edge 1, with the wall dropping below.
  - So the right takeoff is: ridge on top for the full 48.4 ft, an eave on edge 1, rakes on edges 0, 2 and 4, and no step or wall flashing. That is what 0.1.7.3 reports.
  - The ridge is about 1 m north-east of the footprint centre line (asymmetric gable), so the ridge is now placed on the lidar ridge line.
- **Old vs new per-facet method:**
  - The old aspect match "found" a pitch for every facet, even hip ends that do not exist.
  - The new per-facet fit reports those as `aspect_mismatch` or `too_few_points`, which is what makes model verification possible.
- **Simple gables** (249754_888132, 249469_887717, 257506_887663, 257290_888447, 49 Scotland St) verify as simple gables at 0.76–0.95.
  The wings skeleton scores the same on rectangles, so ties go to simple. Per-facet pitch differs from the single pitch by up to 0.5/12 on some
  facets, which changes the area by up to ±2%.
- **Hips:**
  - 263663_883484 and 257552_888022 verify as hip (0.89 and 0.76).
  - 6 Harborview Rd, Hull: the per-facet hip score is 0.53, but segmentation finds 5 confident hip lines, so it is chosen as hip.
- **Complex roofs:**
  - 30 Lockwood Dr, Weymouth: planes from 2/12 to 17/12 (gambrel or mixed). The single pitch of 3.5/12 badly under-states it: 1,520 sq ft single vs 1,704 per-facet. Use per-facet, and verify.
  - The private complex test house has 25 planes, 7 of them small. Many dormer-like steps and short ridges are found. Its wall-flashing total is large and not proven.
- **Failure modes:**
  - Trees over the roof (250005_887609: shape guess shed_or_partial, RMS 1.37 m on the global fit; only 26% of points explained).
  - Sparse gable-end points: lidar lines end 1–3 ft short, so model lengths are kept.
  - Roofprint vs lidar offsets on older roofprints.
  - 2021 lidar vs current buildings.
- **Skylights:**
  - The void/dip/intensity candidates are mostly noise at about 7 pts/m² (a skylight is 2–8 m² at most and often shows no void).
  - They stay low confidence and removable, and the user can add skylights by hand. Needs ground truth.

## 0.1.7.3 final counting policy (after the Orchestrator review)
- A lidar line is counted only if it is confident, it is not wall flashing, and either the roof model is lidar-verified or the line is a ridge.
- With an ASSUMED model, facets-model hips/valleys/step walls and lidar retypes are candidates (Appendix); drip edge uses the footprint rake.
- Eave/rake default = single dominant lidar ridge; per-wing is a UI choice. Private complex house: eave/rake 255.5/149.4 LF (matches the
  reference; per-wing gave 283.4/115.9). Counted ridge 98.6 LF, hip/valley/wall flashing 0 counted, 24 candidates in the Appendix.
- All values NOT_PROVEN without ground truth (15 Ward St pitch 12/12 is the only known value and lidar matches it).

## 0.1.7.4 (local notes)
- Ortho lean: outline-only gradient scoring is ambiguous on gables with a sunlit/shaded facet pair (15 Ward locked the NE eave onto the ridge
  boundary, 6.2 m S). Adding model ridge/hip/valley lines to the score fixed it (3.7 m E, 0.7 m S, ratio 6.8, sep 1.15, high).
- Doubtful ridges: >8° off roofprint axes or planes ≥6/12 apart -> candidate. Private complex test house: 26.8 ft ridge 10° off axis (planes 3.5/12 vs 8.5/12) now a candidate;
  a 27.5 ft on-axis 8/12 vs 4/12 ridge stays counted (4/12 rule was too aggressive).
- 30 Lockwood Dr Weymouth per-facet gap (1520 → 1704): F9 17/12 (192 pts, RMS 0.047) and F14 11/12 (174 pts) high-confidence fits; mixed-pitch roof.
- Open: 3-D view of ASSUMED multi-wing models (facets from the wings skeleton) renders tall slab-like planes; needs per-facet eave edge from the model.
- Open: 30 Lockwood Drive / 49 Scotland Street not in Hull in MassGIS, Census, OSM, L3 parcels — confirm with Ian.
