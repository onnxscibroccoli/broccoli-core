<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure handoff (state as of 0.1.7.6, 2026-11-16)

Read in order: this file, CODEVELOP.md (rules, build), CHANGELOG.md, docs/research/ (*.md notes; *.pdf + .txt reference papers from Ian: lidar structural pipeline, zero-cost measurement uncertainties).

## Current state
- Version 0.1.7.6 (versionCode 10706) on `feat/roofmeasure-dev`. CI: `.github/workflows/roofmeasure.yml` builds the APK, runs headless report tests
  (tests/v0176_test.cjs, with regression gates), an emulator smoke test, and the Oakcrest Rd, Hingham benchmark matrix (houses 1-6). Artifacts (APK, PDFs, JSON) per run.
- Report page 1 is a 2x2 "window view": aerial, vector diagram, aerial+vector overlay, footage summary. Full-page versions of each follow.
- Lidar: USGS 3DEP EPT (6 m pad), whole-roof plane segmentation, per-facet pitch, lidar-vs-model residuals, roofprint-vs-lidar outline registration
  (lidar features moved into the roofprint frame), ortho offset from roof edges (lidar-plane brightness separation as a cross-check).
- Roof features (skylights, decks, dormers) are CANDIDATES and are not in the billable totals (provenance boundary).
- 3-D view/editor: www/view3d.js (three.js r187, MIT).

## Status by test house (PASS / FAIL / NOT_PROVEN)  — CI run: see "CI runs" below
- 15 Ward St, Hingham: lidar residual median 0.05 ft PASS. Skylights: 3 counted (7.1x5.0 NE, 4.4x2.0 SW, 3.9x1.8 SW), doubtful 3.2x1.6 rejected
  (not rectangular) NOT_PROVEN. Ortho shift unchanged (3.68 E / 0.71 S). Ian approved the report.
- 6 Harborview Rd, Hull: roof deck 195 sq ft (14.9 x 13.0 ft rectangle, was 223 hull), flat, "inspect: possible rubber/membrane" NOT_PROVEN
  (visual ~180). Lidar features moved 1.5 m W / 1.0 m N into the roofprint frame. 0 counted skylights (dormer-window patches rejected).
  Residual median 0.24-3.42 ft per facet FAIL (unchanged; model is an assumed hip around the deck).
- 4 Oakcrest Rd, Hingham: skylights 9 -> 1 counted (+2 lidar-only, not counted) NOT_PROVEN. Ortho shift unchanged; photo ambiguous ~1 m.
- 1-3, 5, 6 Oakcrest Rd: see the benchmark summary in the CI run.
- 30 Lockwood Dr, Weymouth and 49 Scotland St, Hingham: public test houses.

## CI runs
- 0.1.7.5: 43802526473 (all green; Oakcrest over-counted skylights 2-9 per house).
- 0.1.7.6 increment 1: (filled in after the run)

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

## Next steps
1. Check the 0.1.7.6 CI artifacts (overlay pages of 15 Ward, 6 Harborview, 4 Oakcrest) visually; per-house counts are in bench-oakcrest-*/summary.txt.
2. Dormer detection finds 0 dormers on 6 Harborview (two visible beside the deck): improve tags.dormers (minor planes beside a flat deck).
3. Lidar lines (plane intersections) are still in the lidar frame (~1 m off the roofprint): consider moving them too, then re-check totals.
4. 4 Oakcrest ortho shift: ambiguous; a lean model (shift proportional to lidar height) may separate eave and ridge evidence.
