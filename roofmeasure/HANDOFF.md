<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure handoff (state as of 0.1.7.6, 2026-11-16)

Read in order: this file, CODEVELOP.md (rules, build), CHANGELOG.md, docs/research/ (*.md notes; *.pdf + .txt reference papers from Ian: lidar structural pipeline, zero-cost measurement uncertainties).

## Repeat alpha install identity
- Every GitHub Actions run signs with a new debug key. Package IDs
  `com.ian.roofmeasure.alpha.c<commit-sha-8>` avoid signature conflicts
  with both the original stable package and previous CI alphas.
- These are side-by-side trial installations with separate Android data;
  stable alpha upgrades require a secure persistent signing key.
- Java class namespace still `com.ian.roofmeasure`; manifest activity,
  provider and native PDF folder names adjust per variant.

## Pitch summary/report mismatch (display correction only)
- User PDF: base 6/12 manual selector; two user-edited facets 12/12. One
  report calculated 2,023.5 sq ft but labelled the headline pitch 6/12.
  `pitchbasis.js` now displays the area calculation's basis (12/12 manual
  facets) separately from the base pitch (6/12). No quantity changes.
- No lidar roof cloud exists in that report. Actual physical pitch is
  NOT_PROVEN without independent rise/run or usable lidar height samples.

## User-supplied test feedback: photo feature review
- One roof report misidentified a chimney as a skylight, a second chimney was not detected,
  and rectangular skylight depictions were reported rotated 90°. The report provided NO
  lidar roof cloud and pitch remained manual. Do not embed the user's private house
  location, screenshot or PDFs in git.
- Candidate review controls: type and 90° rotation in report editor, mark unseen chimneys
  using Tag tool on map. Review is user-supplied visual evidence, not survey ground truth.
- Real pitch NOT_PROVEN by these screenshots; the 12/12 override is a visualization
  workaround, NOT a measured roof slope.
- Next: check pitch provenance and report consistency; verify the revised alpha on device.

## Parallel-installable 0.1.7.6 alpha
- CI builds `com.ian.roofmeasure.alpha`, labelled **RoofMeasure Alpha**, with versionName
  0.1.7.6/versionCode 10706 unchanged. Original `com.ian.roofmeasure` is unaffected.
- Alpha has a unique WebView storage sandbox, PDF content-provider authority and
  `Downloads/RoofMeasureAlpha/` output folder. The CI signing key remains throwaway.
- Omitting `PACKAGE_NAME` from build.sh still produces the original package.
- Actual installation on a phone NOT_PROVEN until user testing.

## Current state
- Version 0.1.7.6 (versionCode 10706) on `feat/roofmeasure-dev`. CI: `.github/workflows/roofmeasure.yml` builds the APK, runs headless report tests
  (tests/v0176_test.cjs, with regression gates), an emulator smoke test, and the Oakcrest Rd, Hingham benchmark matrix (houses 1-6). Artifacts (APK, PDFs, JSON) per run.
- Report page 1 is a 2x2 "window view": aerial, vector diagram, aerial+vector overlay, footage summary. Full-page versions of each follow.
- Lidar: USGS 3DEP EPT (6 m pad), whole-roof plane segmentation, per-facet pitch, lidar-vs-model residuals, roofprint-vs-lidar outline registration
  (lidar features moved into the roofprint frame), ortho offset from roof edges (lidar-plane brightness separation as a cross-check).
- Roof features (skylights, decks, dormers) are CANDIDATES and are not in the billable totals (provenance boundary).
- 3-D view/editor: www/view3d.js (three.js r187, MIT).

## Status by test house (PASS / FAIL / NOT_PROVEN), CI runs 43810427490 and 43811370932 (same numbers)
| House | Lidar residual (median) | Counted skylights | Deck | Dormers (cand.) | Status |
|---|---|---|---|---|---|
| 15 Ward St, Hingham | 0.05 ft PASS | 3 (7.1x5.0 NE, 4.4x2.0 SW, 3.9x1.8 SW) | none | 0 | residual PASS; skylights NOT_PROVEN (on the photo patches) |
| 6 Harborview Rd, Hull | 1.68 ft FAIL (per facet 0.24-3.42) | 0 (+1 lidar-only) | 183 sq ft, 12.8x14.3 ft, flat, inspect rubber/membrane | 1 | deck NOT_PROVEN (visual ~180; drawn ~1 m SE of the deck walls: lean) |
| 1 Oakcrest Rd | 0.48 ft | 0 (+1) | none | 3 | NOT_PROVEN |
| 2 Oakcrest Rd | 4.13 ft FAIL | 1 (9.8x4.5, doubtful) (+1) | none | 1 | NOT_PROVEN |
| 3 Oakcrest Rd | 0.42 ft | 0 | none | 1 | NOT_PROVEN |
| 4 Oakcrest Rd | 3.89 ft FAIL | 1 (+2 lidar-only on the two small squares on the north face) | none | 3 | NOT_PROVEN; was 9 |
| 5 Oakcrest Rd | 0.32 ft | 0 (+2) | none | 2 | NOT_PROVEN |
| 6 Oakcrest Rd | 0.84 ft | 0 (+2) | none | 3 | NOT_PROVEN |
| 30 Lockwood Dr, Weymouth | 1.52 ft | 0 | 81 sq ft | 1 | NOT_PROVEN |
| 49 Scotland St, Hingham | 0.04 ft PASS | 1 (3.1x2.3) | none (27x1.7 ft strip dropped) | 1 | NOT_PROVEN |

## CI runs
- 0.1.7.5: 43802526473 (all green; Oakcrest over-counted skylights 2-9 per house).
- 0.1.7.6 increment 1 (95fb691): 43809861417, all green. Counted skylights: 15 Ward 3, 6 Harborview 0, Oakcrest 1-6: 0/1/0/1/1/0
  (0.1.7.5: 5/7/4/9/4/2), 30 Lockwood 0, 49 Scotland 1. 6 Harborview deck 195 sq ft. Dormers were never used to exclude skylight patches
  (kept-only filter) and were missing from the summary: fixed in increment 2.
- 0.1.7.6 increment 2: dormer candidates used for exclusion + listed with gutter LF; deck rectangle on the house axis; decks < 5 ft wide dropped;
  facet badges join label collision avoidance. Run 43810427490 (45a573b), all green: 6 Harborview deck 183 sq ft (12.8 x 14.3 ft);
  dormer candidates: Oakcrest 1-6 = 3/1/1/3/2/3, 6 Harborview 1, 30 Lockwood 1, 49 Scotland 1, 15 Ward 0; skylight counts unchanged.
- 0.1.7.6 increment 3 (87316c8): run 43810906221 all green, same numbers; the deck label still sat under the F5 badge on the overlay page
  (badges are drawn in a separate pass there).
- 0.1.7.6 increment 4 (fd51e26): _features() computes the facet badge boxes itself. Run 43811370932 all green (apk, report-tests, emulator-smoke,
  Oakcrest 1-6); numbers as in the table; deck label now clear. CI APK sha256 c20e374edd512fb49d455fb8f832570c1847b392a040c200e044d8f821aa35cc.

- docs: e0cea8c adds docs/research/lidar_pipeline_spec.md (Ian's GNSS/geomatics pipeline spec, summary + QL2 applicability).
- 0.1.7.6 increment 5: spec items (5° coplanar merge, geodesic lidar line lengths, bilateral + 0.3 m erosion, skylight area/aspect/axis/
  rectangularity gates, lidar glass evidence, dormer 1.5-20 m² gate). Local check: 15 Ward 3 skylights (6.8x5.0, 4.3x1.9, 3.8x1.8),
  4 Oakcrest 0 (+2 lidar-only), 6 Harborview 0 (+1), deck 183. Run: (filled in after the run)

## Requirements
- Mission: open-source tools so contractors and homeowners get accurate roof measurements and can tell whether a quote is fair.
- Beat GAF QuickMeasure / EagleView / Hover using free data only. Stay on 0.1.7.x until Ian verifies on his phone. No accuracy claims.
- Label every roof structure: skylights (with sizes, measurement optional), dormers, decks (flag possible rubber roof underneath),
  wrapped ridges and extra ridges needing ridge cap.
- Dormer gutters, especially with returns: flag "inspect and clean" (debris causes water intrusion).
- Step flashing ONLY where a wall rises above a roof plane. An eave turning 90 degrees into a rake at roof pitch is eave + rake, not flashing.
- Rakes are sloped lengths at the true pitch. No phantom hips/valleys when lidar is weak; make them candidates.
- Use GitHub Actions (free runners) for heavy work. Push to `feat/roofmeasure-dev` only; no merges to main or force-pushes without Ian.
- One private internal test house is kept out of this repo. Never add private addresses.

## Increment 6 continuation (pending CI and visual verification)
- Experimental 3DEP-height-relative overlay correction for roof decks/dormers and candidate dormer markers.
  No geometry or quantity changes. Requires lidar ground, a supported near-eave height datum,
  and medium/high ortho confidence; skips otherwise. NOT_PROVEN until inspecting 6 Harborview PDF.
- The ortho offset may include survey registration error; it is not purely a camera-lean measurement.

## Next steps
1. Exact next step: lean model for features above the eaves (deck, dormers): shift x (feature height / eave height above lidar ground) so the
   6 Harborview deck lands on its walls in the overlay; then re-check 4 Oakcrest's two lidar-only skylight candidates against ortho patches
   (they sit on the two small squares on the north face but no ortho patch passed).
2. Dormers: lidar finds 1 on 6 Harborview (two visible beside the deck); check after increment 2.
   The deck outline still sits ~1 m SE of the deck walls in the photo: the deck is higher than the eaves, so it leans further (lean grows with height).
3. Lidar lines (plane intersections) are still in the lidar frame (~1 m off the roofprint): consider moving them too, then re-check totals.
4. 4 Oakcrest ortho shift: ambiguous; a lean model (shift proportional to lidar height) may separate eave and ridge evidence.
