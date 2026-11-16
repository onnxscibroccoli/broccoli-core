<!-- SPDX-License-Identifier: MIT -->
# RoofMeasure handoff (state as of 0.1.7.5, 2026-11-15)

Read in order: this file, CODEVELOP.md (rules, build, imagery ToS), CHANGELOG.md, docs/research/*.md.

## Current state
- Version 0.1.7.5, commit 3c6d9af on `feat/roofmeasure-dev`. CI: `.github/workflows/roofmeasure.yml` builds the APK, runs headless report tests
  (tests/v017*_test.cjs), an emulator smoke test, and an Oakcrest Rd benchmark matrix. Artifacts (APK, PDFs, page PNGs) are uploaded per run.
- Report page 1 is a 2x2 "window view": aerial, vector diagram, aerial+vector overlay, footage summary. Full-page versions of each follow.
- Lidar: USGS 3DEP EPT, whole-roof plane segmentation, per-facet pitch, lidar-vs-model residuals, ortho offset estimated from roof lines.
- Lines that aren't confirmed are candidates (Appendix, excluded from totals) until the user promotes them.
- 3-D view/editor: www/view3d.js (three.js r187, MIT).

## Status by test house (PASS / FAIL / NOT_PROVEN)
- 15 Ward St, Hingham: lidar residual median 0.05 ft PASS. 4 skylight candidates with sizes NOT_PROVEN (S1 7.1x5.0 ft NE, S2 4.4x2.0 SW,
  S4 3.9x1.8 SW, S3 3.2x1.6 doubtful; S3 label overlaps an eave label). Owner says the report "looks on point".
- 6 Harborview Rd, Hull: roof deck ~223 sq ft flat, flagged "inspect: possible rubber/membrane roof" NOT_PROVEN (by eye ~180 sq ft, outline offset 1-2 m).
  Residual median 0.24-3.42 ft FAIL: MassGIS roofprint covers only part of the current house; horizontal correction hit its 4.5 ft cap.
- 30 Lockwood Dr, Weymouth and 49 Scotland St, Hingham: public test houses (geocoder warns when the town differs from the input).
- Oakcrest Rd, Hingham (next to 15 Ward), houses 1-6: benchmark runs clean in CI, but skylight counts (2-9 per house) over-count: FAIL.
  4 Oakcrest outline is visibly offset. No decks detected.

## Owner requirements (Ian Cossette)
- Mission: open-source tools so contractors and homeowners get accurate roof measurements and can tell whether a quote is fair.
- Beat GAF QuickMeasure / EagleView / Hover using free data only. Stay on 0.1.7.x until Ian verifies on his phone. No accuracy claims.
- Label every roof structure: skylights (with sizes, measurement optional), dormers, decks (flag possible rubber roof underneath),
  wrapped ridges and extra ridges needing ridge cap.
- Dormer gutters, especially with returns: flag "inspect and clean" (debris causes water intrusion).
- Step flashing ONLY where a wall rises above a roof plane. An eave turning 90 degrees into a rake at roof pitch is eave + rake, not flashing.
- Rakes are sloped lengths at the true pitch. No phantom hips/valleys when lidar is weak; make them candidates.
- Google/Bing/Esri: display-only reference layers (overlay, swipe, opacity). Never analyze their pixels. Analysis only on MassGIS/NAIP/lidar
  or the user's own photos/drone.
- Use GitHub Actions (free runners) for heavy work. Push to `feat/roofmeasure-dev` only; no merges to main or force-pushes without Ian.
- License MIT. Any dependency license is fine; list it in THIRD_PARTY.md. Don't raise licensing questions.
- One private internal test house is kept out of this repo by owner request. Never add private addresses.

## Next steps (0.1.7.6)
1. Align each house's outline to the free ortho/lidar BEFORE skylight detection (fixes Oakcrest over-counting and 6 Harborview offset).
2. Stricter skylight test: lidar plane continuity + ortho contrast + size limits + reject dormer-window clusters; report per-house counts.
3. Tighten the 6 Harborview deck outline (target close to the ~180 sq ft visual estimate) and handle roofprint vs current-house mismatch.
4. Fix the S3 label overlap on 15 Ward. Re-check 3-D screenshots.
5. Dormer + dormer-gutter labeling from lidar planes; open models on free ortho/street photos (see docs/research/deep_research_needed.md).
Report results per house as PASS / FAIL / NOT_PROVEN with CI run ids.
