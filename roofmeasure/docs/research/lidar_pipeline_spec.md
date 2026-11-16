<!-- SPDX-License-Identifier: MIT -->
# Lidar roof pipeline spec ("Principal GNSS / Geomatics"), summary

Source: a pipeline spec Ian supplied (2026-11-16). Below is a faithful section-by-section summary, then how it applies to RoofMeasure's
free data (USGS 3DEP QL2 + MassGIS orthos) and what is already implemented (see CHANGELOG / HANDOFF for versions).

## Part A: high-density lidar pipeline (sub-centimetre target)
1. **Ingest and octree indexing.** LAS/LAZ into a dynamic octree; each leaf voxel (depth d_max) stores statistical moments of its
   points, for fast multi-scale neighbourhood queries and to separate dense structural returns from sparse noise.
2. **Radiometric calibration / intensity normalisation** (from the lidar range equation):
   - range compensation: normalise to a reference range R0 (inverse-square attenuation, I·(R/R0)²);
   - angle-of-incidence correction between the beam and the local plane normal n, with an empirical exponent k for rough,
     non-Lambertian surfaces;
   - specular surfaces (glass): isolate the specular part from the angular deviation to the reflection vector R = L − 2(L·n)n;
   - atmospheric attenuation: transmission factor η_atm from meteorological data / vertical extinction.
3. **Segmentation and watertight topology.**
   - Multi-scale RANSAC + region growing, minimising orthogonal residuals of Ax + By + Cz + D = 0 with A² + B² + C² = 1;
     grow while distance ≤ 0.01 m and normal deviation ≤ 2°.
   - Ridges / hips / valleys = intersection lines of adjacent fitted planes (direction n1 × n2); solving these gives closed loops that
     bound every facet.
4. **Curved roofs (differential geometry).**
   - MLS surface reconstruction: local bivariate polynomial g(x, y) with Gaussian weights θ(r) = exp(−r²/h²).
   - Principal curvatures κ1, κ2 and directions from the Weingarten map; K = κ1κ2, H = (κ1 + κ2)/2:
     K > 0 elliptic (domes, cupolas); K = 0, H ≠ 0 parabolic (barrel vaults, developable); K < 0 hyperbolic (saddles, hypars).
   - Area from the first fundamental form I = E du² + 2F du dv + G dv² (E = r_u·r_u, F = r_u·r_v, G = r_v·r_v):
     A = ∬ sqrt(EG − F²) du dv. Developable surfaces (K = 0) are unrolled isometrically to a flat pattern.
5. **Semantic classes.**
   - Dormers: secondary planar clusters intersecting a primary facet. Gable dormer = two planes forming a ridge that ends at the
     primary face; shed dormer = one shallower plane bounded by vertical cheeks.
   - Skylights: candidate facets that are flush (distance ≤ τ_flush), whose normalised intensity matches glass, and that have no
     solid sub-surface returns beneath.
   - Decks: return density in the sub-canopy layer separates slatted (penetrable) decking from solid flooring.
6. **Topology optimisation and multi-pass analysis.** Closed-loop constraints on all ridges, valleys and rakes; compare multiple
   passes to remove false positives from specular reflections and transient objects.

## Part B: estimator-grade pipeline on public data
1. **Sloped lengths.** Pitch multiplier sqrt(1 + (p/12)²) on rakes, hips and valleys (e.g. 12/12: 20.2 ft plan × 1.4142 = 28.6 ft).
   Eaves are level (Δz = 0): plan length = true length. Ridges/hips/valleys from analytic plane-plane intersection instead of an
   unweighted straight skeleton (which makes phantom hips on gable ends). Intersection noise falls with sqrt(N) of the plane
   support; 3DEP QL2 needs noise gating (≤ 0.08 m vertical) so planes do not fragment.
2. **Data fusion.**
   | Layer | Quality | Role | Failure mode / mitigation |
   |---|---|---|---|
   | USGS 3DEP lidar (EPT/LAZ) | ≥ 2 pts/m² (QL2) to ≥ 8 (QL1); ≤ 10 cm vertical RMSE | planes, pitch, ridges/valleys | interswath steps ≤ 0.08 m split coplanar planes: merge coplanar planes under a 5° normal delta |
   | State orthos (MassGIS) | 7.5-15 cm GSD, RGB-IR, leaf-off | edge snapping, skylight/dormer detection | canopy, 2-6 m building lean: leaf-off, true-ortho corrections |
   | Footprints (Overture / Microsoft) | 129-158 M polygons | 2-D prior | miss 19-33 % of small structures; trace outer roof edges incl. overhangs |
   Coordinates: store EPSG:4326, compute lengths/areas in a parcel-centred ENU tangent plane or UTM, never raw Web Mercator
   (scale error up to +35 % at northern latitudes).
3. **Gated computer vision.**
   - Preprocessing: 0.3 m (2 px) inward roof-mask erosion (no gutters / edges); bilateral smoothing + CLAHE instead of Gaussian blur;
     NIR NDVI ≥ 0.30 vegetation mask; CIELAB shadow suppression.
   - Models: Apache-2.0 MobileSAM (9.66 M params, ~10.5 MB quantised) or SAM 2.1 Hiera-Tiny (~155 MB) via ONNX Runtime Web /
     Transformers.js, offline; avoid AGPL-3.0 Ultralytics packages.
   - Gates: axis within ±10° of the parent ridge/eave bearing; skylight 0.30-3.5 m², width ≥ 0.35 m; dormer 1.5-20 m²;
     chimney 0.25-2.5 m²; rectangularity (area / min bounding box) ≥ 0.78; aspect 1:1 to 1:3.5.
4. **Edit propagation (client-side DAG).** Overhang change → perimeter offset → plan area → sloped area/squares, gutter LF, sloped
   rake, hip/valley, drip edge. Pitch override → sloped facet area (A2D / cos θ), squares, sloped rake and hip/valley
   (sqrt(L2D² + Δz²)), solar index, low-slope warnings; eave plan lengths unchanged.
5. **PDF layout.** Dedicated full pages: aerial, vector diagram (edge numbers, pitch callouts, lengths), overlay.

## Applicability to free 3DEP QL2
- Sub-centimetre boundaries need TLS or UAV lidar. 3DEP QL2 is about 2-8 pts/m² with about 10 cm vertical RMSE and interswath steps
  up to 0.08 m, so plane thresholds must be decimetre-scale (RoofMeasure grows regions at 0.18 m / 12°), not 0.01 m / 2°.
- Intensity in EPT is raw (no range / incidence normalisation, no trajectory), so "glass intensity" can only be a relative anomaly
  against the surrounding plane; "no sub-surface returns" becomes "few or no returns on the patch".
- MassGIS tiles served to the app are RGB: no NIR, so no NDVI.

## Status in RoofMeasure (0.1.7.6)
- Done: plane-intersection lines (lidar/roofseg.js); pitch multiplier on rakes/hips/valleys only; coplanar merge at < 5°; full-page
  aerial / diagram / overlay pages; dormer (gable vs shed) candidates; skylight lidar check (flush, few returns, intensity anomaly);
  skylight / dormer gates from Part B §3; 0.3 m inward erosion; local metric frame check (see CHANGELOG 0.1.7.6).
- Research list: MobileSAM / SAM 2.1 Hiera-Tiny via ONNX (licence OK, ~10-155 MB download); MLS + curvature (K, H) for curved roofs;
  intensity normalisation (needs trajectory data 3DEP EPT does not carry); closed-loop topology solver; CLAHE; edit-propagation DAG
  as an explicit graph (the app recomputes everything on each edit today).
