# report/svg — READY

Lane: SVG roof diagram (stdlib only). Written only under `/workspace/roofmeasure/report/svg/`.
Finished 22:44 ET Saturday Nov 14 2026 (deadline 23:50 ET).

## API

Module: `report/svg/diagram.py` (also re-exported from `report/svg/__init__.py`).

```python
render_roof_svg(result: dict, width=640, height=480) -> str
svg_text_equivalent(result) -> str
```

`render_roof_svg` returns an inline SVG string:

- Drawn from `result['footprint_geojson']` (CONTRACT.md). Lon/lat is converted to local feet with an equirectangular projection at the footprint centroid (`x = R cos(lat0) Δlon`, `y = R Δlat`, `R = 6378137 m`, y = north = up in the SVG).
- `role="img"` with `<title>` and `<desc>`; the desc lists every numbered edge as text (plus interior lines and facets when present).
- Edges are numbered with `length_ft` callouts placed outside the polygon; boxes are tested not to overlap each other or the footprint.
- Edge types `eave` / `rake` / `ridge` / `hip` / `valley` use a distinct dash pattern **and** a text label **and** a legend (never colour alone). All strokes/fills are `#000000` or `#FFFFFF` (contrast 21:1, requirement ≥ 4.5:1) so the figure prints in black and white.
- North arrow and a scale bar in feet.
- When `result['facets']` has a `polygon` / `geojson` / `polygon_lonlat` (or `geometry`) ring, each facet is hatched (angle/spacing, not colour) and labeled with area / pitch. Labels shrink or drop to the facet id when the facet is too small.
- Ridge / hip / valley segments are drawn when present on `result['line_segments']`, `result['lines']`, or a facet. On-diagram labels are omitted only when they would collide; they always appear in `<desc>` and in `svg_text_equivalent`.

`svg_text_equivalent` returns an HTML `<div>` with a short summary and an `<ol>` of every edge (plus `<ul>` lists for interior lines and facets when present). Text is XML-escaped.

Missing optional fields degrade: no crash, no invented measurements. If `footprint_geojson` is absent, the renderer will still accept a raw GeoJSON `Feature` / `FeatureCollection` / `Polygon` or a QA fixture that carries `massgis_roofprint`. Missing `edges` are synthesized from the ring (type `unknown`, labeled “edge”). Missing facets / lines are skipped.

Helpers used by the tests (not part of the required API): `coerce_result`, `projected_footprint_area_sqft`, `contrast_ratio`.

## How to call it

From `/workspace/roofmeasure` (add the package dir to `sys.path`):

```python
import json, sys
sys.path.insert(0, "report/svg")
from diagram import render_roof_svg, svg_text_equivalent

result = json.load(open("qa/fixtures/reference_248476_884962.json"))
# QA fixtures and bare GeoJSON are coerced automatically:
svg = render_roof_svg(result)          # also accepts a CONTRACT result dict
html = svg_text_equivalent(result)
```

Integrator: pass the CONTRACT result (with `footprint_geojson`, optional `edges`, `facets`, `line_segments` / `lines`, `address`, `pitch`). The SVG is a complete `<svg xmlns=...>` element, suitable for inlining in the HTML report.

## Tests — exact commands and outputs

Cwd for both commands: `/workspace/roofmeasure`. Both were run after the final code change, at 22:44 ET Nov 14 2026.

### Command 1

```
python3 report/svg/tests/test_diagram.py
```

Output (exit 0):

```
test_contrast_black_on_white (__main__.ApiTests.test_contrast_black_on_white) ... ok
test_exports (__main__.ApiTests.test_exports) ... ok
test_empty_dict (__main__.DegradeTests.test_empty_dict) ... ok
test_invalid_width_height_falls_back (__main__.DegradeTests.test_invalid_width_height_falls_back) ... ok
test_missing_optional_edges_types_facets (__main__.DegradeTests.test_missing_optional_edges_types_facets) ... ok
test_none_and_bad_types (__main__.DegradeTests.test_none_and_bad_types) ... ok
test_facets_hatched_and_labeled (__main__.FacetAndLineTests.test_facets_hatched_and_labeled) ... ok
test_leonard_facets_fixture_renders (__main__.FacetAndLineTests.test_leonard_facets_fixture_renders) ... ok
test_ridge_hip_valley_lines_drawn (__main__.FacetAndLineTests.test_ridge_hip_valley_lines_drawn) ... ok
test_callouts_outside_polygon_and_nonoverlapping (__main__.FixtureRenderTests.test_callouts_outside_polygon_and_nonoverlapping) ... ok
test_desc_lists_every_edge (__main__.FixtureRenderTests.test_desc_lists_every_edge) ... ok
test_every_required_fixture_renders (__main__.FixtureRenderTests.test_every_required_fixture_renders) ... ok
test_only_black_and_white_fills_and_strokes (__main__.FixtureRenderTests.test_only_black_and_white_fills_and_strokes) ... ok
test_required_fixtures_present (__main__.FixtureRenderTests.test_required_fixtures_present) ... ok
test_types_use_dash_and_text_and_legend (__main__.FixtureRenderTests.test_types_use_dash_and_text_and_legend)
Types must not be encoded by colour alone. ... ok
test_write_samples (__main__.SampleWriteTests.test_write_samples) ... ok
test_escapes_html (__main__.TextEquivalentTests.test_escapes_html) ... ok
test_is_html_list (__main__.TextEquivalentTests.test_is_html_list) ... ok
test_projected_area_near_massgis (__main__.WardStTests.test_projected_area_near_massgis) ... ok
test_reference_house_id_in_source_or_desc (__main__.WardStTests.test_reference_house_id_in_source_or_desc) ... ok
test_wraps_bare_geojson (__main__.WardStTests.test_wraps_bare_geojson) ... ok

----------------------------------------------------------------------
Ran 21 tests in 0.141s

OK
```

### Command 2

```
python3 -m unittest discover -s report/svg/tests -t report/svg
```

Output (exit 0):

```
.....................
----------------------------------------------------------------------
Ran 21 tests in 0.140s

OK
```

### What the tests covered

Required inputs (wrapped to a minimal CONTRACT result when they were not already one):

- `/workspace/roofmeasure/qa/fixtures/hingham_14_leonard_st.json`
- `/workspace/roofmeasure/qa/fixtures/hingham_36_arnold_rd.json`
- `/workspace/roofmeasure/qa/fixtures/reference_248476_884962.json`
- `/workspace/roofmeasure/qa/fixtures/weymouth_37_prescott_st.json`
- `/workspace/roofmeasure/tests/fixtures_15_ward_st_hingham.geojson.json` (bare FeatureCollection; wrapped with address “15 Ward St, Hingham, MA 02043”)

Additional fixtures (for hatch + ridge/hip/valley coverage; not claimed as surveyed measurements):

- `report/svg/tests/fixtures/15_ward_st_hingham_facets.json`
- `report/svg/tests/fixtures/hingham_14_leonard_st_facets.json`

These were produced by running `facets.computeFacets()` on the 2-D MassGIS roofprint (equal-pitch straight-skeleton heuristic, default 6/12) and are labeled as such in `_facets_source` / `notes`.

Reference-house area check (equirectangular at centroid vs MassGIS `AREA_SQ_FT` 1430.71706696): projected plan area **1431.769531 sq ft** (0.0736% high). The test allows 1%.

`test_write_samples` writes the SVGs (and two HTML text-equivalents) under `report/svg/samples/`.

## Samples

| File | Source |
|---|---|
| `report/svg/samples/hingham_14_leonard_st.svg` | QA fixture |
| `report/svg/samples/hingham_36_arnold_rd.svg` | QA fixture |
| `report/svg/samples/reference_248476_884962.svg` | QA fixture (same house as Ward St) |
| `report/svg/samples/weymouth_37_prescott_st.svg` | QA fixture |
| `report/svg/samples/15_ward_st_hingham.svg` | wrapped bare GeoJSON |
| `report/svg/samples/15_ward_st_hingham.text.html` | text equivalent of the above |
| `report/svg/samples/15_ward_st_hingham_facets.svg` | heuristic facets + lines |
| `report/svg/samples/15_ward_st_hingham_facets.text.html` | text equivalent of the above |
| `report/svg/samples/hingham_14_leonard_st_facets.svg` | heuristic facets + lines |

After the unit tests passed, the sample SVGs were also rasterized with headless Chrome for a visual check (not a unit test): callouts sit outside the polygon, notch leaders no longer cut across the roof, facet hatches and ridge/hip/valley dashes are distinct in black and white. On dense hip roofs some short interior-line labels are dropped when they would collide; those lengths remain in `<desc>` and in the HTML list.

## Paths

```
/workspace/roofmeasure/report/svg/diagram.py
/workspace/roofmeasure/report/svg/__init__.py
/workspace/roofmeasure/report/svg/READY.md
/workspace/roofmeasure/report/svg/tests/test_diagram.py
/workspace/roofmeasure/report/svg/tests/__init__.py
/workspace/roofmeasure/report/svg/tests/fixtures/15_ward_st_hingham_facets.json
/workspace/roofmeasure/report/svg/tests/fixtures/hingham_14_leonard_st_facets.json
/workspace/roofmeasure/report/svg/samples/*.svg
/workspace/roofmeasure/report/svg/samples/*.text.html
```

## Limits (fail closed)

- I did not edit files outside `report/svg/`.
- I did not run the integrator’s `renderReport`, produce a PDF, or copy anything to `/workspace/artifacts/`.
- Facet / line geometry in the `*_facets` fixtures is a 2-D heuristic, not a surveyed roof. QA fixtures themselves have no `edges` / `facets`; those samples show type “edge” and a dotted unknown stroke until the integrator supplies typed edges.
- I did not independently survey the MassGIS areas; I only compared the equirectangular plan area of the Ward St ring to the `AREA_SQ_FT` attribute on that GeoJSON.
