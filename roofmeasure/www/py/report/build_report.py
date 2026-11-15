#!/usr/bin/env python3
"""RoofMeasure measurement-report generator (Python 3 stdlib only).

Usage:
  python3 report/build_report.py <result.json | qa_fixture.json> [--out report/out/<slug>/] [--no-pdf]

Input: a CONTRACT.md shared result JSON. A raw QA fixture (qa/fixtures/*.json, has
`massgis_roofprint` but no `footprint_geojson`) is first converted with
report/fixture_to_result.js (which calls the shared core/roofcalc.js computeRoof, read-only).
Outputs in --out: result.json (input as used), report.html, report.pdf, edges.csv, summary.json.
Exit codes: 0 ok, 2 usage, 3 schema validation failed (fail closed), 4 PDF render failed.
"""
import argparse, base64, csv, datetime, html, json, math, mimetypes, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REQUIRED = ["address", "lat", "lon", "source", "footprint_geojson", "footprint_area_sqft", "perimeter_ft",
            "overhang_ft", "pitch", "pitch_factor", "roof_area_sqft", "squares", "edges",
            "eave_lf", "rake_lf", "gutter_lf", "downspouts", "notes"]
EDGE_REQUIRED = ["i", "length_ft", "type"]
EDGE_TYPES = ["eave", "rake", "ridge", "hip", "valley"]
WASTE = [0, 5, 10, 15, 20]
# line patterns (not colour) distinguish edge types; text code is also printed on every label
STYLE = {
    "eave":   {"code": "E", "dash": "",          "w": 3.5, "desc": "solid thick line"},
    "rake":   {"code": "R", "dash": "10 6",      "w": 2.5, "desc": "long-dashed line"},
    "ridge":  {"code": "RG", "dash": "2 4",      "w": 2.5, "desc": "dotted line"},
    "hip":    {"code": "H", "dash": "12 4 2 4",  "w": 2.5, "desc": "dash-dot line"},
    "valley": {"code": "V", "dash": "4 3",       "w": 2.5, "desc": "short-dashed line"},
}
OTHER_STYLE = {"code": "?", "dash": "1 3", "w": 2, "desc": "fine dotted line"}


class SchemaError(Exception):
    pass


def esc(x):
    return html.escape("" if x is None else str(x), quote=True)


def num(x, d=1):
    if x is None:
        return "—"
    return f"{x:,.{d}f}"


def round_up_third(sq):
    """Round squares UP to the next 1/3 square (3-tab/architectural bundle convention: 3 bundles per square)."""
    return math.ceil(round(sq * 3, 6)) / 3.0


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def validate(r):
    missing = [k for k in REQUIRED if k not in r or r[k] is None]
    problems = []
    for k in ["lat", "lon", "footprint_area_sqft", "perimeter_ft", "overhang_ft", "pitch_factor",
              "roof_area_sqft", "squares", "eave_lf", "rake_lf", "gutter_lf", "downspouts"]:
        if k in r and r[k] is not None and not is_number(r[k]):
            problems.append(f"{k} must be a number (got {r[k]!r})")
    if "edges" in r and r["edges"] is not None:
        if not isinstance(r["edges"], list) or not r["edges"]:
            problems.append("edges must be a non-empty list")
        else:
            for j, e in enumerate(r["edges"]):
                miss = [k for k in EDGE_REQUIRED if not isinstance(e, dict) or k not in e]
                if miss:
                    problems.append(f"edges[{j}] missing {','.join(miss)}")
                elif not is_number(e["length_ft"]):
                    problems.append(f"edges[{j}].length_ft not a number")
    if r.get("footprint_geojson") is not None:
        try:
            ring_of(r["footprint_geojson"])
        except Exception as ex:  # noqa
            problems.append(f"footprint_geojson unusable: {ex}")
    if "notes" in r and r["notes"] is not None and not isinstance(r["notes"], list):
        problems.append("notes must be a list")
    if missing or problems:
        msg = []
        if missing:
            msg.append("missing required fields: " + ", ".join(missing))
        msg += problems
        raise SchemaError("; ".join(msg))


def ring_of(g):
    if g.get("type") == "FeatureCollection":
        g = g["features"][0]
    if g.get("type") == "Feature":
        g = g["geometry"]
    t = g.get("type")
    if t == "Polygon":
        ring = g["coordinates"][0]
    elif t == "MultiPolygon":
        ring = max((p[0] for p in g["coordinates"]), key=len)
    else:
        raise ValueError(f"unsupported geometry type {t!r}")
    if len(ring) < 4:
        raise ValueError("ring has fewer than 4 coordinates")
    return [(float(p[0]), float(p[1])) for p in ring]


def load_input(path):
    with open(path) as f:
        d = json.load(f)
    if "footprint_geojson" not in d and "massgis_roofprint" in d:
        node = shutil.which("node")
        if not node:
            raise SchemaError("input looks like a QA fixture but node is not available to convert it")
        p = subprocess.run([node, os.path.join(HERE, "fixture_to_result.js"), path], capture_output=True, text=True)
        if p.returncode != 0:
            raise SchemaError("fixture conversion failed: " + p.stderr.strip())
        d = json.loads(p.stdout)
        d["_converted_from_fixture"] = os.path.relpath(path)
    return d


# ---------------------------------------------------------------- derived numbers
def lines_lf(r, key):
    lines = r.get("lines") if isinstance(r.get("lines"), dict) else {}
    v = lines.get(key)
    return float(v) if is_number(v) else None


def compute(r):
    edges = r["edges"]
    by_type = {}
    for e in edges:
        t = str(e.get("type", "unknown")).lower()
        b = by_type.setdefault(t, {"count": 0, "plan_lf": 0.0})
        b["count"] += 1
        b["plan_lf"] += float(e["length_ft"])
    rows = []
    for t in EDGE_TYPES:
        if t in ("eave", "rake"):
            lf = float(r[f"{t}_lf"])
            src = "result." + t + "_lf"
            if t == "rake":
                src += " (sloped: plan span + 2×overhang per rake edge, × pitch factor)"
            alt = lines_lf(r, t + "_lf")
            rows.append({"type": t, "edges": by_type.get(t, {}).get("count", 0),
                         "plan_lf": by_type.get(t, {}).get("plan_lf", 0.0) if t in by_type else None,
                         "lf": lf, "source": src, "lines_lf": alt, "measured": True})
        else:
            lf = lines_lf(r, t + "_lf")
            rows.append({"type": t, "edges": by_type.get(t, {}).get("count", 0),
                         "plan_lf": by_type.get(t, {}).get("plan_lf") if t in by_type else None,
                         "lf": lf, "source": ("result.lines." + t + "_lf") if lf is not None else None,
                         "lines_lf": None, "measured": lf is not None})
    for t in sorted(set(by_type) - set(EDGE_TYPES)):
        rows.append({"type": t, "edges": by_type[t]["count"], "plan_lf": by_type[t]["plan_lf"], "lf": None,
                     "source": None, "lines_lf": None, "measured": False})
    roof = float(r["roof_area_sqft"])
    waste = []
    for w in WASTE:
        a = roof * (1 + w / 100.0)
        waste.append({"waste_pct": w, "area_sqft": round(a, 1), "squares": round(a / 100.0, 2),
                      "squares_order": round(round_up_third(a / 100.0), 2)})
    eave, rake = float(r["eave_lf"]), float(r["rake_lf"])
    ridge, hip = lines_lf(r, "ridge_lf"), lines_lf(r, "hip_lf")
    flid = facets_lidar(r)
    extra = []
    f_rake = lines_lf(r, "rake_lf") if flid else None
    if flid:
        extra.append({"key": "rake_incl_step_gables_lf", "label": "Rake incl. step gables (drip edge)", "lf": f_rake,
                      "source": "result.lines.rake_lf (facets, lidar ridge)"})
        wf = lines_lf(r, "wall_flashing_lf")
        extra.append({"key": "wall_flashing_lf", "label": "Wall flashing", "lf": wf,
                      "source": "result.lines.wall_flashing_lf (facets, lidar ridge)" if wf is not None else None})
    if f_rake is not None:
        drip, drip_basis = round(eave + f_rake, 1), f"eave_lf {num(eave)} + facets rake incl. step gables {num(f_rake)}"
    else:
        drip, drip_basis = round(eave + rake, 1), f"eave_lf {num(eave)} + core rake_lf (sloped) {num(rake)}"
    ridge_cap = None if (ridge is None and hip is None) else round((ridge or 0) + (hip or 0), 1)
    mats = {
        "starter_strip_lf": round(eave + rake, 1),
        "drip_edge_lf": drip,
        "drip_edge_basis": drip_basis,
        "ridge_cap_lf": ridge_cap,
        "ridge_cap_formula": ("not available: no ridge/hip data in result (result.lines absent)" if ridge_cap is None else
                              f"ridge_lf {num(ridge)} + hip_lf {num(hip)} = {num(ridge_cap)} LF"
                              + ("" if (ridge is not None and hip is not None) else " (missing term counted as 0)")),
    }
    mats["extra_rows"] = extra
    return rows, waste, mats


def facets_lidar(r):
    """Facets computed with a lidar ridge (RM Facets ruling): facets ridge_bearing_source == 'input' or lidar inputs flag."""
    return isinstance(r.get("lines"), dict) and (r.get("facets_ridge_bearing_source") == "input" or bool(r.get("facets_lidar_inputs")))


# ---------------------------------------------------------------- SVG diagram
def svg_diagram(r, W=640, H=430, pad=60):
    ring = ring_of(r["footprint_geojson"])
    lon0 = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
    lat0 = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
    ky = 364000.0  # ft per degree lat (approx; display only)
    kx = ky * math.cos(math.radians(lat0))
    xy = [((p[0] - lon0) * kx, (p[1] - lat0) * ky) for p in ring]
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1)
    s = min((W - 2 * pad) / (max(xs) - min(xs) or 1), (H - 2 * pad) / (max(ys) - min(ys) or 1))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    P = [(W / 2 + (x - cx) * s, H / 2 - (y - cy) * s) for x, y in xy]
    # signed area (screen coords, y down) to find outward normal
    A = sum(P[i][0] * P[i + 1][1] - P[i + 1][0] * P[i][1] for i in range(len(P) - 1))
    edges = r["edges"]
    out = []
    title = f"Roof diagram: {r['address']}"
    desc = (f"Plan-view outline of the 2-D roofprint with {len(edges)} numbered edges. "
            "Each label gives edge number, type code and plan length in feet. North is up.")
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" '
               f'role="img" aria-labelledby="dg-title dg-desc" class="diagram">')
    out.append(f'<title id="dg-title">{esc(title)}</title><desc id="dg-desc">{esc(desc)}</desc>')
    out.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff" stroke="#595959" stroke-width="1"/>')
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in P)
    out.append(f'<polygon points="{poly}" fill="#eef1f4" stroke="none"/>')
    nseg = len(P) - 1
    for k, e in enumerate(edges):
        i = int(e["i"]) if is_number(e.get("i")) else k
        if "from" in e and "to" in e:
            a = ((e["from"][0] - lon0) * kx, (e["from"][1] - lat0) * ky)
            b = ((e["to"][0] - lon0) * kx, (e["to"][1] - lat0) * ky)
            a = (W / 2 + (a[0] - cx) * s, H / 2 - (a[1] - cy) * s)
            b = (W / 2 + (b[0] - cx) * s, H / 2 - (b[1] - cy) * s)
        elif k < nseg:
            a, b = P[k], P[k + 1]
        else:
            continue
        t = str(e.get("type", "")).lower()
        st = STYLE.get(t, OTHER_STYLE)
        dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#111111" '
                   f'stroke-width="{st["w"]}"{dash} stroke-linecap="butt"/>')
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        nx, ny = (-dy / L, dx / L) if A < 0 else (dy / L, -dx / L)  # outward
        lx, ly = mx + nx * 18, my + ny * 18
        lab = f"#{i} {st['code']} {float(e['length_ft']):.1f}'"
        out.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" '
                   f'fill="#111111" stroke="#ffffff" stroke-width="3" paint-order="stroke">{esc(lab)}</text>')
    # north arrow + scale bar
    out.append(f'<g aria-hidden="true"><line x1="{W-30}" y1="50" x2="{W-30}" y2="20" stroke="#111" stroke-width="2"/>'
               f'<polygon points="{W-30},14 {W-36},26 {W-24},26" fill="#111"/>'
               f'<text x="{W-30}" y="66" text-anchor="middle" font-size="12" font-family="Arial" fill="#111">N</text></g>')
    bar_ft = next(v for v in [5, 10, 20, 25, 50, 100] if v * s >= 60 or v == 100)
    out.append(f'<g aria-hidden="true"><line x1="20" y1="{H-20}" x2="{20 + bar_ft * s:.1f}" y2="{H-20}" stroke="#111" stroke-width="3"/>'
               f'<text x="20" y="{H-28}" font-size="12" font-family="Arial" fill="#111">{bar_ft} ft (approx.)</text></g>')
    out.append("</svg>")
    return "".join(out)


_SVG_WORKER = "unset"


def svg_worker():
    """report/svg (other worker, read-only): used only if report/svg/READY.md exists and the import succeeds."""
    global _SVG_WORKER
    if _SVG_WORKER != "unset":
        return _SVG_WORKER
    _SVG_WORKER = None
    d = os.path.join(HERE, "svg")
    if os.path.isfile(os.path.join(d, "READY.md")) and not os.environ.get("ROOFMEASURE_INLINE_SVG"):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("roofmeasure_svg_diagram", os.path.join(d, "diagram.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if callable(getattr(mod, "render_roof_svg", None)) and callable(getattr(mod, "svg_text_equivalent", None)):
                _SVG_WORKER = mod
        except Exception as ex:  # noqa
            print(f"WARN: report/svg import failed ({ex}); using inline diagram", file=sys.stderr)
    return _SVG_WORKER


def diagram_html(r):
    """Returns (diagram_source, svg_html, extra_text_equivalent_html)."""
    mod = svg_worker()
    if mod is not None:
        try:
            return "report/svg/diagram.py", mod.render_roof_svg(r), mod.svg_text_equivalent(r)
        except Exception as ex:  # noqa
            print(f"WARN: report/svg render failed ({ex}); using inline diagram", file=sys.stderr)
    return "inline", svg_diagram(r), ""


def legend_svg(t):
    st = STYLE.get(t, OTHER_STYLE)
    dash = f' stroke-dasharray="{st["dash"]}"' if st["dash"] else ""
    return (f'<svg width="54" height="12" viewBox="0 0 54 12" aria-hidden="true" focusable="false">'
            f'<line x1="2" y1="6" x2="52" y2="6" stroke="#111" stroke-width="{st["w"]}"{dash}/></svg>')


# ---------------------------------------------------------------- aerial
ENDPOINTS = os.path.join(os.path.dirname(HERE), "shared", "endpoints.json")


def ortho_template():
    try:
        with open(ENDPOINTS) as f:
            ep = json.load(f)
        t = ep["endpoints"]["massgis_ortho_2025"]["xyz_template"]
        return t if "{z}" in t and "{x}" in t and "{y}" in t else None
    except Exception:  # noqa
        return None


def aerial_from_ortho(r, z=19, half=None):
    """MassGIS 2025 ortho tiles (XYZ template referenced in shared/endpoints.json), embedded as data URIs in an
    inline SVG with the roofprint overlaid. Returns None on any failure (caller shows a placeholder)."""
    import urllib.request
    tpl = ortho_template()
    if not tpl or os.environ.get("ROOFMEASURE_NO_AERIAL"):
        return None
    lat, lon = float(r["lat"]), float(r["lon"])
    n = 2 ** z
    def world(lo, la):
        return ((lo + 180) / 360 * n * 256,
                (1 - math.log(math.tan(math.radians(la)) + 1 / math.cos(math.radians(la))) / math.pi) / 2 * n * 256)
    ring = ring_of(r["footprint_geojson"])
    pts = [world(*p) for p in ring]
    cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    if half is None:
        ext = max(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
        half = max(60.0, min(160.0, ext * 1.1))
    x0, y0 = cx - half, cy - half
    imgs = []
    try:
        for ty in range(int(y0 // 256), int((y0 + 2 * half) // 256) + 1):
            for tx in range(int(x0 // 256), int((x0 + 2 * half) // 256) + 1):
                url = tpl.replace("{z}", str(z)).replace("{x}", str(tx)).replace("{y}", str(ty))
                req = urllib.request.Request(url, headers={"User-Agent": "RoofMeasure-report/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                if len(data) < 500:
                    return None
                mt = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
                imgs.append(f'<image x="{tx*256 - x0:.1f}" y="{ty*256 - y0:.1f}" width="256" height="256" '
                            f'href="data:{mt};base64,{base64.b64encode(data).decode()}"/>')
    except Exception:  # noqa
        return None
    poly = " ".join(f"{p[0]-x0:.1f},{p[1]-y0:.1f}" for p in pts)
    alt = (f"Aerial photo (MassGIS 2025 orthoimagery, zoom {z}) centred on the roof at {r['address']}, "
           "with the 2-D roofprint outline drawn as a white-and-black dashed line.")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {2*half:.1f} {2*half:.1f}" width="100%" role="img" '
           f'aria-labelledby="ae-title ae-desc"><title id="ae-title">Aerial image</title><desc id="ae-desc">{esc(alt)}</desc>'
           + "".join(imgs) +
           f'<polygon points="{poly}" fill="none" stroke="#ffffff" stroke-width="4"/>'
           f'<polygon points="{poly}" fill="none" stroke="#000000" stroke-width="2" stroke-dasharray="6 4"/></svg>')
    return ("massgis_ortho_2025", f'<figure class="aerial">{svg}<figcaption>MassGIS 2025 orthoimagery (15 cm); '
            'roofprint outline overlaid (dashed). Tile URL template from shared/endpoints.json.</figcaption></figure>')


def aerial_html(r, input_dir):
    cand = None
    for k in ("aerial_image", "aerial_image_url", "aerial_thumbnail", "image_url", "thumbnail_url", "ortho_url"):
        if isinstance(r.get(k), str) and r[k]:
            cand = r[k]
            break
    if cand is None and isinstance(r.get("imagery"), dict):
        for k in ("thumbnail_path", "path", "url", "tile_url", "image_url"):
            if isinstance(r["imagery"].get(k), str):
                cand = r["imagery"][k]
                break
    alt = f"Aerial image of the roof at {r['address']}"
    if cand:
        src = cand
        if not re.match(r"^(https?:|data:)", cand):
            p = cand if os.path.isabs(cand) else os.path.join(input_dir, cand)
            if os.path.isfile(p):
                mt = mimetypes.guess_type(p)[0] or "image/png"
                src = f"data:{mt};base64," + base64.b64encode(open(p, "rb").read()).decode()
            else:
                cand = None
        if cand:
            return ("embedded", f'<figure class="aerial"><img src="{esc(src)}" alt="{esc(alt)}" '
                    f'onerror="this.replaceWith(Object.assign(document.createElement(\'p\'),{{className:\'ph\',textContent:\'Aerial image could not be loaded.\'}}))">'
                    f'<figcaption>Aerial imagery referenced in the result JSON.</figcaption></figure>')
    o = aerial_from_ortho(r)
    if o:
        return o
    return ("placeholder", '<figure class="aerial"><div class="ph" role="note">AERIAL IMAGE NOT AVAILABLE<br>'
            '<span>No imagery in the result JSON and the free MassGIS ortho tile could not be loaded; paid imagery is not fetched.</span></div>'
            '<figcaption>Placeholder — see the roof diagram below.</figcaption></figure>')


# ---------------------------------------------------------------- attribution
def attributions(r, aerial_kind=None):
    blob = json.dumps({k: r.get(k) for k in ("source", "source_detail", "geocoder", "pitch_source", "notes", "requests",
                                              "facets_source", "lines_source")}).lower()
    a = []
    if "massgis" in blob:
        a.append("MassGIS (Bureau of Geographic Information), Building Structures (2-D) roofprints — "
                 "Commonwealth of Massachusetts, public data.")
    if "census" in blob:
        a.append("U.S. Census Bureau Geocoder (address to coordinates; street-segment interpolation).")
    if "3dep" in blob or "lidar" in blob or "usgs" in blob:
        a.append("USGS 3D Elevation Program (3DEP) lidar point cloud (public domain), used for pitch.")
    if "overture" in blob:
        a.append("Overture Maps Foundation buildings (ODbL/CDLA as applicable).")
    if "osm" in blob or "openstreetmap" in blob or "overpass" in blob:
        a.append("© OpenStreetMap contributors (ODbL).")
    if isinstance(r.get("structures_on_lot"), dict):
        a.append("MassGIS Level 3 Property Tax Parcels (lot boundary for the detached-structures list).")
    if isinstance(r.get("solar"), dict) and (r["solar"].get("pvwatts") or {}).get("worked"):
        a.append("NREL/NLR PVWatts v8 (public DEMO_KEY) for PVWatts-derived solar values.")
    if aerial_kind == "massgis_ortho_2025":
        a.append("MassGIS 2025 statewide orthoimagery (15 cm), Commonwealth of Massachusetts — aerial thumbnail.")
    if not a:
        a.append(f"Source as reported in result: {r.get('source')}.")
    return a


# ---------------------------------------------------------------- HTML
CSS = """
@page { size: Letter; margin: 0.55in; }
* { box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; color: #111; background: #fff; font-size: 10.5pt; line-height: 1.35; margin: 0; }
main { max-width: 7.4in; margin: 0 auto; }
header.top { border-bottom: 3px solid #1a3d5c; padding-bottom: 6px; margin-bottom: 10px; display: flex; justify-content: space-between; gap: 12px; }
h1 { font-size: 18pt; margin: 0; color: #1a3d5c; }
h2 { font-size: 13pt; color: #1a3d5c; border-bottom: 1px solid #595959; margin: 16px 0 6px; padding-bottom: 2px; page-break-after: avoid; }
.brand { font-weight: bold; font-size: 10pt; color: #1a3d5c; text-align: right; }
dl.meta { display: grid; grid-template-columns: max-content 1fr; gap: 1px 10px; margin: 0; }
dl.meta dt { font-weight: bold; } dl.meta dd { margin: 0; }
.grid { display: grid; grid-template-columns: 2.6in 1fr; gap: 12px; align-items: start; }
.aerial { margin: 0; } .aerial img { width: 100%; border: 1px solid #595959; }
.ph { border: 2px dashed #595959; background: #f4f4f4; padding: 30px 8px; text-align: center; font-weight: bold; color: #333; }
.ph span { font-weight: normal; font-size: 9pt; }
figcaption { font-size: 8.5pt; color: #333; }
table { border-collapse: collapse; width: 100%; margin: 4px 0 8px; page-break-inside: avoid; }
caption { text-align: left; font-weight: bold; padding: 2px 0 4px; color: #111; }
th, td { border: 1px solid #767676; padding: 3px 6px; text-align: left; vertical-align: top; }
thead th { background: #e3e8ee; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 6px 0; }
.kpi { border: 1px solid #767676; padding: 6px; } .kpi b { display: block; font-size: 14pt; } .kpi span { font-size: 8.5pt; }
.diagram { border: 0; max-height: 4.2in; display:block; margin:0 auto; }
.na { font-style: italic; color: #333; }
.formula { font-family: "Courier New", monospace; font-size: 9pt; }
.disclaimer { border: 2px solid #111; padding: 6px 10px; background: #fff; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.pb { page-break-before: always; }
footer { margin-top: 14px; font-size: 8.5pt; color: #333; border-top: 1px solid #767676; padding-top: 4px; }
ul { margin: 4px 0 4px 18px; padding: 0; }
"""


def assessor_rows(r):
    """Optional assessor info: result.assessor = {style, stories, year_built} or same keys at top level."""
    a = r.get("assessor") if isinstance(r.get("assessor"), dict) else {}
    rows = []
    for key, label in (("style", "Assessor style"), ("stories", "Stories (assessor)"), ("year_built", "Year built (assessor)")):
        v = a.get(key, r.get(key))
        if v not in (None, "", []):
            rows.append((label, str(v)))
    return rows


def structures_section(r):
    """Optional 'Detached structures' + lot total from result.structures_on_lot (extras/structures.py). '' if absent."""
    st = r.get("structures_on_lot")
    if not isinstance(st, dict) or not st.get("structures"):
        return "", None
    rows = st["structures"]
    acc = [x for x in rows if x.get("role") != "primary"]
    H = ['<section aria-labelledby="h-struct"><h2 id="h-struct">Detached structures</h2>']
    if not acc:
        H.append("<p>No other structures were found on this tax lot.</p>")
    H.append('<table><caption>All MassGIS structures on the tax lot (class is an area heuristic, not a use attribute)</caption><thead><tr>'
             '<th scope="col">STRUCT_ID</th><th scope="col">Class</th><th scope="col">Role</th><th scope="col" class="n">Footprint (sq ft)</th>'
             '<th scope="col" class="n">Roof area (sq ft)</th><th scope="col">Roof basis</th></tr></thead><tbody>')
    lot_fp = lot_roof = 0.0
    roof_ok = True
    for x in rows:
        prim = x.get("role") == "primary"
        fp = x.get("footprint_area_sqft")
        m = x.get("measurements") or {}
        if prim:
            roof, basis = r["roof_area_sqft"], f"this report ({r['pitch']}, {r.get('pitch_source') or 'source not provided'})"
        else:
            roof = m.get("roof_area_sqft")
            basis = (f"{m.get('measured_by') or 'extras tool'}: pitch {m.get('pitch')} ASSUMED, overhang {m.get('overhang_ft')} ft" if roof is not None else "not measured")
        if is_number(fp):
            lot_fp += fp
        if is_number(roof):
            lot_roof += roof
        else:
            roof_ok = False
        H.append(f'<tr><th scope="row">{esc(x.get("struct_id"))}</th><td>{esc(x.get("class"))}</td><td>{esc(x.get("role"))}</td>'
                 f'<td class="n">{num(fp, 2) if is_number(fp) else "—"}</td><td class="n">{num(roof) if is_number(roof) else "<span class=na>not measured</span>"}</td>'
                 f'<td>{esc(basis)}</td></tr>')
    H.append(f'<tr><th scope="row">Lot total</th><td>{len(rows)} structures</td><td>—</td><td class="n">{num(lot_fp, 2)}</td>'
             f'<td class="n">{num(lot_roof) if roof_ok else "<span class=na>incomplete</span>"}</td><td>sum of rows above</td></tr>')
    H.append('</tbody></table>')
    rule = st.get("classification_rule") or {}
    H.append(f'<p>Source: {esc(st.get("source"))}. Rule: shed {esc(rule.get("shed"))}; garage {esc(rule.get("garage"))}; house {esc(rule.get("house"))}; '
             f'on-lot if ≥ {esc(rule.get("on_lot_min_overlap"))} of the footprint lies in the parcel.</p></section>')
    total = {"n_structures": len(rows), "footprint_area_sqft": round(lot_fp, 2), "roof_area_sqft": round(lot_roof, 1) if roof_ok else None,
             "accessory": [{"struct_id": x.get("struct_id"), "class": x.get("class"), "footprint_area_sqft": x.get("footprint_area_sqft")} for x in acc]}
    return "".join(H), total


def solar_section(r):
    so = r.get("solar")
    if not isinstance(so, dict) or not so.get("facets"):
        return ""
    pv = so.get("pvwatts") or {}
    H = ['<section aria-labelledby="h-solar"><h2 id="h-solar">Solar exposure index (per facet)</h2>',
         '<table><caption>Annual solar exposure index by roof facet (1.0 = reference surface; see method column)</caption><thead><tr>'
         '<th scope="col">Facet</th><th scope="col" class="n">Azimuth (°)</th><th scope="col" class="n">Tilt (°)</th><th scope="col" class="n">Area (sq ft)</th>'
         '<th scope="col" class="n">Exposure index</th><th scope="col">Method</th><th scope="col" class="n">kWh/kW/yr</th></tr></thead><tbody>']
    for f in so["facets"]:
        pw = f.get("pvwatts") or {}
        src = str(f.get("exposure_index_source") or (f.get("estimate") or {}).get("method") or "")
        if src.startswith("pvwatts"):
            method = "PVWatts-derived (NREL/NLR PVWatts v8, vs south-facing same tilt)"
        else:
            method = "ESTIMATE (Liu-Jordan isotropic sky model; not PVWatts)"
        kwh = pw.get("ac_annual_kwh_per_kw")
        if is_number(kwh):
            kwh_s = f"{num(kwh, 0)} (PVWatts-derived)"
        elif is_number(pw.get("interpolated_kwh_per_kw_estimate")):
            kwh_s = f"{num(pw['interpolated_kwh_per_kw_estimate'], 0)} (interpolated from PVWatts-derived grid; not a direct run)"
        else:
            kwh_s = '<span class="na">not provided</span>'
        ei = f.get("exposure_index")
        H.append(f'<tr><th scope="row">{esc(f.get("id"))}</th><td class="n">{num(f.get("azimuth_deg"), 1) if is_number(f.get("azimuth_deg")) else "—"}</td>'
                 f'<td class="n">{num(f.get("tilt_deg"), 1) if is_number(f.get("tilt_deg")) else "—"}</td>'
                 f'<td class="n">{num(f.get("area_sqft")) if is_number(f.get("area_sqft")) else "—"}</td>'
                 f'<td class="n">{num(ei, 2) if is_number(ei) else "—"}</td><td>{esc(method)}</td><td class="n">{kwh_s}</td></tr>')
    t = so.get("totals") or {}
    H.append('</tbody></table>')
    H.append(f'<p>Area-weighted exposure index: {num(t.get("area_weighted_exposure_index"), 2) if is_number(t.get("area_weighted_exposure_index")) else "not provided"}. '
             f'PVWatts this run: {"used" if pv.get("worked") else "not used (no cached PVWatts result at this tilt; values are ESTIMATES)"}. '
             'No roof-total kWh is reported (no array size given). Source: ' + esc(so.get("source")) + '.</p></section>')
    return "".join(H)


def build_html(r, rows, waste, mats, aerial, generated):
    addr = esc(r["address"])
    pitch_src = r.get("pitch_source")
    lidar = isinstance(pitch_src, str) and ("lidar" in pitch_src.lower() or "3dep" in pitch_src.lower())
    assumed = pitch_src == "default"
    pitch_kind = "LiDAR-derived" if lidar else ("assumed" if assumed else ("source: " + str(pitch_src) if pitch_src else "source not stated"))
    conf = r.get("pitch_confidence")
    H = []
    H.append(f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
             f'<meta name="viewport" content="width=device-width, initial-scale=1">'
             f'<title>Roof Measurement Report — {addr}</title><style>{CSS}</style></head><body><main>')
    H.append('<header class="top"><div>'
             f'<h1>Roof Measurement Report</h1><p style="margin:2px 0 0;font-size:12pt"><strong>{addr}</strong></p></div>'
             f'<div class="brand">RoofMeasure<br><span style="font-weight:normal">Report generated {esc(generated)}</span></div></header>')
    H.append('<section aria-labelledby="h-prop"><h2 id="h-prop">Property and data</h2><div class="grid">')
    H.append(aerial[1])
    meta = [("Address", r["address"]),
            ("Report date", generated),
            ("Data fetched", r.get("fetched_at") or "not recorded"),
            ("Latitude, longitude", f"{float(r['lat']):.6f}, {float(r['lon']):.6f} (WGS84)"),
            ("Footprint source", r["source"]),
            ]
    sd = r.get("source_detail") or {}
    if sd.get("struct_id"):
        extra = ", ".join(x for x in (sd.get("sourcetype"), sd.get("sourcedata")) if x)
        meta.append(("MassGIS STRUCT_ID", sd["struct_id"] + (f" ({extra})" if extra else "")))
    for k, v in assessor_rows(r):
        meta.append((k, v))
    if r.get("geocoder"):
        meta.append(("Geocoder", r["geocoder"]))
    meta.append(("Roof type assumed", r.get("roof_type") or "not stated"))
    meta.append(("Calculation", f"roofcalc.js v{r['calc_version']}" if r.get("calc_version") else "not stated"))
    H.append('<dl class="meta">' + "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in meta) + "</dl></div></section>")

    # summary KPIs
    w10 = next(w for w in waste if w["waste_pct"] == 10)
    H.append('<section aria-labelledby="h-sum"><h2 id="h-sum">Summary</h2><div class="kpis">'
             f'<div class="kpi"><b>{num(r["roof_area_sqft"])} sq ft</b><span>Roof area (sloped, incl. overhang)</span></div>'
             f'<div class="kpi"><b>{num(r["squares"], 2)}</b><span>Squares (0% waste)</span></div>'
             f'<div class="kpi"><b>{esc(r["pitch"])}</b><span>Pitch ({esc(pitch_kind)}{(", confidence " + format(float(conf), ".2f")) if is_number(conf) else ""})</span></div>'
             f'<div class="kpi"><b>{num(w10["squares_order"], 2)}</b><span>Squares to order at 10% waste (rounded up to ⅓)</span></div>'
             '</div></section>')

    # diagram
    H.append('<section aria-labelledby="h-dg"><h2 id="h-dg">Roof diagram</h2>')
    dsrc, dsvg, dtext = diagram_html(r)
    r["_diagram_source"] = dsrc
    H.append(dsvg)
    if dtext:
        H.append('<h3 id="h-dg-text">Diagram text description</h3>' + dtext)
    present = sorted({str(e.get("type", "")).lower() for e in r["edges"]})
    H.append('<table><caption>Diagram legend (line pattern and text code; colour is not used)</caption><thead><tr>'
             '<th scope="col">Pattern</th><th scope="col">Code</th><th scope="col">Edge type</th><th scope="col">Shown in diagram</th></tr></thead><tbody>')
    for t in EDGE_TYPES:
        st = STYLE[t]
        H.append(f'<tr><td>{legend_svg(t)} {esc(st["desc"])}</td>'
                 f'<td>{st["code"]}</td><td>{t.title()}</td><td>{"yes" if t in present else "no (not in edge list)"}</td></tr>')
    H.append('</tbody></table>')
    # text equivalent
    worker_dg = dsrc != "inline"
    H.append('<table><caption>Edge list (text equivalent of the roof diagram; plan lengths)'
             + (' — diagram labels are numbered from 1 (label = edge i + 1)' if worker_dg else '') + '</caption><thead><tr>'
             '<th scope="col" class="n">Edge i</th>' + ('<th scope="col" class="n">Diagram label</th>' if worker_dg else '') + '<th scope="col">Type</th><th scope="col" class="n">Plan length (ft)</th>'
             '<th scope="col" class="n">Bearing (°)</th><th scope="col">Classification</th></tr></thead><tbody>')
    for e in r["edges"]:
        auto = e.get("auto")
        cls = "auto (heuristic)" if auto is True else ("manual" if auto is False else "not stated")
        lbl = f'<td class="n">{int(e["i"]) + 1}</td>' if worker_dg and is_number(e.get("i")) else ('<td class="n">—</td>' if worker_dg else '')
        H.append(f'<tr><th scope="row" class="n">{esc(e["i"])}</th>{lbl}<td>{esc(str(e["type"]).title())}</td>'
                 f'<td class="n">{num(float(e["length_ft"]), 2)}</td>'
                 f'<td class="n">{num(e.get("bearing_deg"), 1) if is_number(e.get("bearing_deg")) else "—"}</td><td>{cls}</td></tr>')
    H.append('</tbody></table></section>')

    # lengths by type
    H.append('<section aria-labelledby="h-len"><h2 id="h-len">Edge lengths by type</h2>')
    H.append('<table><caption>Linear feet by edge type (“not measured” = absent from the data; no values are invented)</caption><thead><tr>'
             '<th scope="col">Type</th><th scope="col" class="n">Edges</th><th scope="col" class="n">Plan LF (sum of edges)</th>'
             '<th scope="col" class="n">Reported LF</th><th scope="col">Source</th></tr></thead><tbody>')
    for row in rows:
        lf = f'{num(row["lf"])}' if row["measured"] else '<span class="na">not measured</span>'
        plan = num(row["plan_lf"]) if row["plan_lf"] is not None else '<span class="na">—</span>'
        src = esc(row["source"]) if row["source"] else '<span class="na">no data in result</span>'
        if row.get("lines_lf") is not None and not (row["type"] == "rake" and mats["extra_rows"]):
            src += f' (facets lines.{row["type"]}_lf = {num(row["lines_lf"])})'
        H.append(f'<tr><th scope="row">{esc(row["type"].title())}</th><td class="n">{row["edges"]}</td>'
                 f'<td class="n">{plan}</td><td class="n">{lf}</td><td>{src}</td></tr>')
    for x in mats["extra_rows"]:
        v = f'{num(x["lf"])}' if x["lf"] is not None else '<span class="na">not provided</span>'
        H.append(f'<tr><th scope="row">{esc(x["label"])}</th><td class="n">—</td><td class="n">—</td><td class="n">{v}</td>'
                 f'<td>{esc(x["source"]) if x["source"] else "<span class=na>not provided by facets output</span>"}</td></tr>')
    H.append('</tbody></table>')
    if mats["extra_rows"]:
        H.append('<p>The primary Rake row is core\'s footprint-edge rake (plan LF and sloped LF). The extra rows come from the facets '
                 'lane run with the lidar ridge: its rake includes step-gable ends. Drip edge uses: ' + esc(mats["drip_edge_basis"]) + '.</p>')
    H.append('</section>')

    # totals
    H.append('<section aria-labelledby="h-tot"><h2 id="h-tot">Areas and pitch</h2>')
    tot = [("Footprint area (2-D roofprint)", f'{num(r["footprint_area_sqft"])} sq ft'),
           ("Perimeter", f'{num(r["perimeter_ft"])} ft'),
           ("Overhang", f'{num(r["overhang_ft"])} ft'),
           ("Overhang source", r.get("overhang_source") or "not provided")]
    if is_number(r.get("roof_plan_area_sqft")):
        tot.append(("Plan area incl. overhang", f'{num(r["roof_plan_area_sqft"])} sq ft'))
    tot += [("Pitch", str(r["pitch"])),
            ("Pitch factor", f'{float(r["pitch_factor"]):.4f}'),
            ("Pitch source", (str(pitch_src) + (" (assumed default)" if assumed else "")) if pitch_src else "not provided"),
            ("Pitch confidence", f"{float(conf):.2f}" if is_number(conf) else "not provided")]
    if is_number(r.get("ridge_bearing_deg")):
        tot.append(("Ridge bearing", f'{num(r["ridge_bearing_deg"])}°'))
    if isinstance(r.get("facets"), list):
        tot.append(("Roof facets (facets lane)", str(len(r["facets"]))))
    tot += [("Roof area (sloped)", f'{num(r["roof_area_sqft"])} sq ft'),
            ("Squares (roof area ÷ 100)", num(r["squares"], 2))]
    H.append('<table><caption>Totals</caption><tbody>' +
             "".join(f'<tr><th scope="row">{esc(k)}</th><td class="n">{esc(v)}</td></tr>' for k, v in tot) + '</tbody></table>')
    H.append('<p class="formula">roof_area = plan_area_with_overhang × pitch_factor; pitch_factor = √(1 + (rise/12)²)</p></section>')

    # waste
    H.append('<section aria-labelledby="h-waste"><h2 id="h-waste">Waste factor</h2>')
    H.append('<table><caption>Roof area and squares by waste factor. Order quantity = squares rounded UP to the next ⅓ square (3 bundles per square).</caption>'
             '<thead><tr><th scope="col" class="n">Waste</th><th scope="col" class="n">Area (sq ft)</th><th scope="col" class="n">Squares (exact)</th>'
             '<th scope="col" class="n">Squares to order (↑⅓)</th></tr></thead><tbody>')
    for w in waste:
        H.append(f'<tr><th scope="row" class="n">{w["waste_pct"]}%</th><td class="n">{num(w["area_sqft"])}</td>'
                 f'<td class="n">{num(w["squares"], 2)}</td><td class="n">{num(w["squares_order"], 2)}</td></tr>')
    H.append('</tbody></table><p class="formula">area_w = roof_area × (1 + w/100); squares_order = ceil(3 × area_w/100) / 3</p></section>')

    # gutters + materials
    H.append('<section aria-labelledby="h-mat"><h2 id="h-mat">Gutters and materials estimate</h2>')
    H.append('<table><caption>Gutters and accessory materials (linear feet)</caption><thead><tr><th scope="col">Item</th>'
             '<th scope="col" class="n">Quantity</th><th scope="col">Formula</th></tr></thead><tbody>')
    eave, rake = float(r["eave_lf"]), float(r["rake_lf"])
    H.append(f'<tr><th scope="row">Gutter</th><td class="n">{num(r["gutter_lf"])} LF</td><td class="formula">result.gutter_lf (eave runs + end extensions, per roofcalc.js)</td></tr>')
    H.append(f'<tr><th scope="row">Downspouts</th><td class="n">{esc(r["downspouts"])}</td><td class="formula">result.downspouts (per gutter run)</td></tr>')
    H.append(f'<tr><th scope="row">Starter strip</th><td class="n">{num(mats["starter_strip_lf"])} LF</td><td class="formula">eave_lf {num(eave)} + rake_lf {num(rake)}</td></tr>')
    H.append(f'<tr><th scope="row">Drip edge</th><td class="n">{num(mats["drip_edge_lf"])} LF</td><td class="formula">{esc(mats["drip_edge_basis"])}</td></tr>')
    for x in mats["extra_rows"]:
        if x["key"] == "wall_flashing_lf":
            v = f'{num(x["lf"])} LF' if x["lf"] is not None else '<span class="na">not provided</span>'
            H.append(f'<tr><th scope="row">Wall flashing</th><td class="n">{v}</td><td class="formula">result.lines.wall_flashing_lf (facets){"" if x["lf"] is not None else " — absent, not invented"}</td></tr>')
    rc = f'{num(mats["ridge_cap_lf"])} LF' if mats["ridge_cap_lf"] is not None else '<span class="na">not available</span>'
    H.append(f'<tr><th scope="row">Ridge cap</th><td class="n">{rc}</td><td class="formula">{esc(mats["ridge_cap_formula"])}</td></tr>')
    H.append('</tbody></table>')
    if isinstance(r.get("gutter_runs"), list) and r["gutter_runs"]:
        H.append('<table><caption>Gutter runs</caption><thead><tr><th scope="col">Run</th><th scope="col">Edges</th>'
                 '<th scope="col" class="n">Eave length (ft)</th><th scope="col" class="n">Gutter (ft)</th><th scope="col" class="n">Downspouts</th></tr></thead><tbody>')
        for k, g in enumerate(r["gutter_runs"], 1):
            H.append(f'<tr><th scope="row">{k}</th><td>{esc(", ".join("#" + str(x) for x in g.get("edges", [])))}</td>'
                     f'<td class="n">{num(g.get("length_ft"))}</td><td class="n">{num(g.get("gutter_ft"))}</td><td class="n">{esc(g.get("downspouts"))}</td></tr>')
        H.append('</tbody></table>')
    H.append('</section>')

    shtml, _lot = structures_section(r)
    H.append(shtml)
    H.append(solar_section(r))
    # notes, attribution, disclaimers
    H.append('<section aria-labelledby="h-notes"><h2 id="h-notes">Notes</h2>')
    H.append("<ul>" + "".join(f"<li>{esc(n)}</li>" for n in r["notes"]) + "</ul>" if r["notes"] else "<p>No notes in result.</p>")
    H.append('</section><section aria-labelledby="h-attr"><h2 id="h-attr">Data sources and attribution</h2><ul>' +
             "".join(f"<li>{esc(a)}</li>" for a in attributions(r, aerial[0])) + "</ul></section>")
    disc = ["Eave/rake classification is a heuristic from the 2-D roofprint outline, not a 3-D roof model; verify each edge on imagery or on site."]
    if assumed:
        disc.append(f"Pitch {r['pitch']} is ASSUMED (default; not LiDAR-derived). Roof area, squares, rake length and materials scale with pitch.")
    elif not lidar:
        disc.append(f"Pitch {r['pitch']} source: {pitch_src or 'not provided'} (not LiDAR-derived); verify on site.")
    else:
        disc.append(f"Pitch is LiDAR-derived ({pitch_src}); confidence {num(conf, 2) if is_number(conf) else 'not provided'}. Mixed pitches are reduced to one dominant value.")
    if not any(row["measured"] for row in rows if row["type"] in ("ridge", "hip", "valley")):
        disc.append("Ridge, hip and valley lengths were not measured; ridge cap and valley materials are not included.")
    else:
        disc.append("Ridge/hip/valley lengths come from a straight-skeleton model of the 2-D roofprint at a single pitch (facets lane), not a measured 3-D roof; dormers and mixed pitches are not modelled.")
    disc += ["Roofprint outlines may be offset or dated relative to current construction (additions, dormers, porches).",
             "For estimating only — NOT for engineering, permitting, structural or insurance purposes. Verify all measurements on site before ordering."]
    H.append('<section aria-labelledby="h-disc"><h2 id="h-disc">Accuracy and limitations</h2><div class="disclaimer"><ul>' +
             "".join(f"<li>{esc(d)}</li>" for d in disc) + "</ul></div></section>")
    H.append(f'<footer>RoofMeasure report · {addr} · generated {esc(generated)} · free public data only</footer></main></body></html>')
    return "".join(H)


# ---------------------------------------------------------------- PDF
def find_chrome():
    for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        p = shutil.which(c)
        if p:
            return p
    return None


def render_pdf(html_path, pdf_path):
    chrome = find_chrome()
    if chrome:
        cmd = [chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
               "--run-all-compositor-stages-before-draw", "--virtual-time-budget=5000",
               f"--print-to-pdf={pdf_path}", "file://" + os.path.abspath(html_path)]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0:
                return "google-chrome headless (" + chrome + ")"
            err = p.stderr[-500:]
        except subprocess.TimeoutExpired:
            err = "timeout"
    else:
        err = "chrome not found"
    if shutil.which("weasyprint"):
        p = subprocess.run(["weasyprint", html_path, pdf_path], capture_output=True, text=True)
        if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0:
            return "weasyprint"
        err += " | weasyprint: " + p.stderr[-300:]
    raise RuntimeError("PDF render failed: " + err)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")[:60] or "report"


def build(input_path, out_dir=None, pdf=True, flat=None):
    r = load_input(input_path)
    validate(r)
    slug = r.get("slug") or slugify(r["address"])
    # Canonical report/out/<slug>/ (+ flat copies) is written ONLY by build_all.sh (explicit --out + --flat).
    # Ad-hoc / API calls without an out_dir go to report/out/adhoc/<slug>/ so other lanes can't clobber canonical outputs.
    if flat is None:
        flat = False
    out_dir = out_dir or os.path.join(HERE, "out", "adhoc", slug)
    os.makedirs(out_dir, exist_ok=True)
    rows, waste, mats = compute(r)
    aerial = aerial_html(r, os.path.dirname(os.path.abspath(input_path)))
    generated = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    with open(os.path.join(out_dir, "result.json"), "w") as f:
        json.dump(r, f, indent=1)
    html_path = os.path.join(out_dir, "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(build_html(r, rows, waste, mats, aerial, generated))
    with open(os.path.join(out_dir, "edges.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["i", "type", "length_ft", "bearing_deg", "auto"])
        for e in r["edges"]:
            w.writerow([e["i"], e["type"], e["length_ft"], e.get("bearing_deg", ""), e.get("auto", "")])
    with open(os.path.join(out_dir, "measurements.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["field", "value"])
        for k in ("address", "lat", "lon", "source", "footprint_area_sqft", "perimeter_ft", "overhang_ft"):
            w.writerow([k, r[k]])
        w.writerow(["overhang_source", r.get("overhang_source") or "not provided"])
        for k in ("pitch", "pitch_factor"):
            w.writerow([k, r[k]])
        for k in ("pitch_source", "pitch_confidence", "ridge_bearing_deg", "roof_type"):
            w.writerow([k, r.get(k) if r.get(k) is not None else "not provided"])
        for k in ("roof_area_sqft", "squares", "eave_lf", "rake_lf", "gutter_lf", "downspouts"):
            w.writerow([k, r[k]])
        for row in rows:
            if row["type"] in ("ridge", "hip", "valley"):
                w.writerow([row["type"] + "_lf", round(row["lf"], 2) if row["measured"] else "not measured"])
        w.writerow(["starter_strip_lf", mats["starter_strip_lf"]]); w.writerow(["drip_edge_lf", mats["drip_edge_lf"]])
        w.writerow(["drip_edge_basis", mats["drip_edge_basis"]])
        for x in mats["extra_rows"]:
            w.writerow([x["key"], round(x["lf"], 2) if x["lf"] is not None else "not provided"])
        w.writerow(["ridge_cap_lf", mats["ridge_cap_lf"] if mats["ridge_cap_lf"] is not None else "not available"])
        for wt in waste:
            w.writerow([f"squares_order_waste_{wt['waste_pct']}pct", wt["squares_order"]])
    renderer = None
    pdf_path = os.path.join(out_dir, "report.pdf")
    if pdf:
        renderer = render_pdf(html_path, pdf_path)
    summary = {
        "slug": slug, "address": r["address"], "lat": r["lat"], "lon": r["lon"], "source": r["source"],
        "generated": generated, "input": os.path.relpath(input_path),
        "footprint_area_sqft": r["footprint_area_sqft"], "perimeter_ft": r["perimeter_ft"],
        "overhang_ft": r["overhang_ft"], "overhang_source": r.get("overhang_source") or "not provided",
        "pitch": r["pitch"], "pitch_factor": r["pitch_factor"], "ridge_bearing_deg": r.get("ridge_bearing_deg"),
        "roof_type": r.get("roof_type"), "core_version": r.get("core_version") or r.get("calc_version"),
        "facets_source": r.get("facets_source"), "lines": r.get("lines"),
        "pitch_source": r.get("pitch_source"), "pitch_confidence": r.get("pitch_confidence"),
        "roof_area_sqft": r["roof_area_sqft"], "squares": r["squares"],
        "edge_count": len(r["edges"]),
        "lengths_by_type": {row["type"]: (round(row["lf"], 1) if row["measured"] else "not measured") for row in rows},
        "eave_lf": r["eave_lf"], "rake_lf": r["rake_lf"], "gutter_lf": r["gutter_lf"], "downspouts": r["downspouts"],
        "waste_table": waste, "squares_rounding": "ceil to next 1/3 square",
        "materials": mats, "aerial": aerial[0], "pdf_renderer": renderer, "diagram_source": r.pop("_diagram_source", None),
        "lot": structures_section(r)[1], "solar_present": bool(solar_section(r)),
        "outputs": {k: os.path.join(out_dir, k) for k in ("report.html", "report.pdf", "edges.csv", "measurements.csv", "summary.json", "result.json")},
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    if flat:  # BOARD.md interface: report/out/<slug>.{html,pdf,csv,json}
        parent = os.path.dirname(os.path.abspath(out_dir.rstrip("/")))
        for src, ext in (("report.html", "html"), ("report.pdf", "pdf"), ("edges.csv", "csv"), ("summary.json", "json"),
                         ("measurements.csv", "measurements.csv")):
            sp = os.path.join(out_dir, src)
            if os.path.isfile(sp):
                shutil.copyfile(sp, os.path.join(parent, f"{slug}.{ext}"))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description="RoofMeasure measurement-report generator")
    ap.add_argument("input", help="CONTRACT result JSON or QA fixture JSON")
    ap.add_argument("--out", help="output directory (default report/out/adhoc/<slug>/; build_all.sh writes report/out/<slug>/)")
    ap.add_argument("--flat", action="store_true", help="also write flat copies <parent-of-out>/<slug>.{html,pdf,csv,json,measurements.csv}")
    ap.add_argument("--no-pdf", action="store_true", help="skip PDF rendering")
    a = ap.parse_args(argv)
    try:
        s = build(a.input, a.out, pdf=not a.no_pdf, flat=a.flat)
    except SchemaError as e:
        print(f"ERROR: schema validation failed for {a.input}: {e}", file=sys.stderr)
        return 3
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 4
    print(f"OK {s['slug']}: roof {s['roof_area_sqft']} sqft, {s['squares']} sq, edges {s['edge_count']}, "
          f"pdf={s['pdf_renderer']} -> {os.path.dirname(s['outputs']['report.html'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
