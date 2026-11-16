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
    "wall_flashing": {"code": "WF", "dash": "6 2 1 2", "w": 2.5, "desc": "dash-dot-dot line"},
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
        extra.append({"key": "rake_incl_step_gables_lf", "label": "Rake per roof model (drip edge)", "lf": f_rake,
                      "source": "result.lines.rake_lf (facets, lidar ridge)"})
        wf = lines_lf(r, "wall_flashing_lf")
        extra.append({"key": "wall_flashing_lf", "label": "Wall flashing", "lf": wf,
                      "source": "result.lines.wall_flashing_lf (facets, lidar ridge)" if wf is not None else None})
    L_ = r.get("lines") if isinstance(r.get("lines"), dict) else {}
    l_eave, l_rake = float(L_.get("lidar_eave_lf") or 0), float(L_.get("lidar_rake_lf") or 0)
    if l_eave or l_rake:
        extra.append({"key": "lidar_eave_lf", "label": "Eave of raised sections (lidar, level)", "lf": round(l_eave, 1), "source": "result.lines.lidar_eave_lf (lidar step edges, NOT_PROVEN)"})
        extra.append({"key": "lidar_rake_lf", "label": "Rake of raised sections (lidar, sloped)", "lf": round(l_rake, 1), "source": "result.lines.lidar_rake_lf (lidar step edges, NOT_PROVEN)"})
    mi_ = r.get("roof_model_info") if isinstance(r.get("roof_model_info"), dict) else {}
    model_ok = (not mi_) or mi_.get("verified") or mi_.get("source") == "user-selected"
    if f_rake is not None and model_ok:
        drip, drip_basis = round(eave + f_rake + l_eave + l_rake, 1), f"eave_lf {num(eave)} + facets-model rake (sloped) {num(f_rake)}"
    else:
        drip, drip_basis = round(eave + rake + l_eave + l_rake, 1), f"eave_lf {num(eave)} + core rake_lf (sloped) {num(rake)}" + ("" if f_rake is None else " (roof model ASSUMED, so its step-gable rakes are not used)")
    if l_eave or l_rake:
        drip_basis += f" + lidar raised-section eave {num(l_eave)} + rake {num(l_rake)}"
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
           "with the 2-D roofprint outline drawn as a white-and-black dashed line and each edge drawn in its type colour with its edge number.")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {2*half:.1f} {2*half:.1f}" width="100%" role="img" '
           f'aria-labelledby="ae-title ae-desc"><title id="ae-title">Aerial image</title><desc id="ae-desc">{esc(alt)}</desc>'
           + "".join(imgs) +
           f'<polygon points="{poly}" fill="none" stroke="#ffffff" stroke-width="4"/>'
           f'<polygon points="{poly}" fill="none" stroke="#000000" stroke-width="2" stroke-dasharray="6 4"/>'
           + aerial_markings(r, world, x0, y0, 2 * half) + '</svg>')
    marked = bool(r.get("edges")) and all(e.get("from") and e.get("to") for e in r["edges"])
    cap = ('MassGIS 2025 orthoimagery (15 cm); typed edges overlaid with the edge numbers used in the tables '
           '(blue eave, orange rake, red ridge, purple hip, teal valley; dashed = roofprint outline). Tile URL template from shared/endpoints.json.'
           if marked else 'MassGIS 2025 orthoimagery (15 cm); roofprint outline overlaid (dashed). Tile URL template from shared/endpoints.json.')
    return ("massgis_ortho_2025", f'<figure class="aerial">{svg}<figcaption>{cap}</figcaption></figure>')


AERIAL_COLORS = {"eave": "#1d4ed8", "rake": "#ea580c", "ridge": "#dc2626", "hip": "#9333ea", "valley": "#0d9488", "wall_flashing": "#64748b"}


def aerial_markings(r, world, x0, y0, size):
    """0.1.7.2: per-edge markings on the aerial photo: each outline edge drawn in its type colour with its edge number,
    plus interior ridge/hip/valley lines from the facets model (line_segments.coords_lonlat). Geometry comes only from the
    result (free data); nothing is derived from the imagery."""
    out = []
    fs = max(9.0, size / 32)
    for sg in r.get("line_segments") or []:
        c = sg.get("coords_lonlat")
        t = str(sg.get("type", "")).lower()
        if not c or len(c) < 2 or t not in ("ridge", "hip", "valley"):
            continue
        a, b = world(*c[0]), world(*c[1])
        col = AERIAL_COLORS.get(t, "#ffffff")
        out.append(f'<line x1="{a[0]-x0:.1f}" y1="{a[1]-y0:.1f}" x2="{b[0]-x0:.1f}" y2="{b[1]-y0:.1f}" stroke="#000" stroke-width="5" stroke-linecap="round"/>'
                   f'<line x1="{a[0]-x0:.1f}" y1="{a[1]-y0:.1f}" x2="{b[0]-x0:.1f}" y2="{b[1]-y0:.1f}" stroke="{col}" stroke-width="3" stroke-linecap="round"/>')
    labels = []
    for e in r.get("edges") or []:
        f, t2 = e.get("from"), e.get("to")
        if not f or not t2:
            continue
        a, b = world(*f), world(*t2)
        col = AERIAL_COLORS.get(str(e.get("type", "")).lower(), "#ffffff")
        out.append(f'<line x1="{a[0]-x0:.1f}" y1="{a[1]-y0:.1f}" x2="{b[0]-x0:.1f}" y2="{b[1]-y0:.1f}" stroke="#000" stroke-width="6" stroke-linecap="round"/>'
                   f'<line x1="{a[0]-x0:.1f}" y1="{a[1]-y0:.1f}" x2="{b[0]-x0:.1f}" y2="{b[1]-y0:.1f}" stroke="{col}" stroke-width="3.5" stroke-linecap="round"/>')
        if float(e.get("length_ft", 0)) >= 3:
            mx, my = (a[0] + b[0]) / 2 - x0, (a[1] + b[1]) / 2 - y0
            labels.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{fs*0.75:.1f}" fill="#fff" stroke="{col}" stroke-width="2"/>'
                          f'<text x="{mx:.1f}" y="{my + fs*0.35:.1f}" font-size="{fs:.1f}" font-family="Arial,sans-serif" font-weight="700" text-anchor="middle" fill="#111">{esc(e["i"])}</text>')
    return "".join(out + labels)


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


# ---------------------------------------------------------------- 0.1.7.3 full-page views (aerial / vector diagram / composite)
PALETTES = {
    "std": {"eave": "#1d4ed8", "rake": "#ea580c", "ridge": "#dc2626", "hip": "#9333ea", "valley": "#0d9488", "wall_flashing": "#64748b"},
    "cb":  {"eave": "#0072B2", "rake": "#E69F00", "ridge": "#D55E00", "hip": "#CC79A7", "valley": "#009E73", "wall_flashing": "#999999"},
}
PAGE_W, PAGE_H = 740.0, 860.0   # viewBox units for a full Letter page figure (7.4 in x 8.6 in)


def pal(r):
    return PALETTES.get(str(r.get("palette") or "std"), PALETTES["std"])


def _world(z):
    n = 2 ** z
    def w(lo, la):
        return ((lo + 180) / 360 * n * 256,
                (1 - math.log(math.tan(math.radians(la)) + 1 / math.cos(math.radians(la))) / math.pi) / 2 * n * 256)
    return w


def _rings_ll(g):
    """all outer rings (lon/lat) of a GeoJSON geometry/feature"""
    if not isinstance(g, dict):
        return []
    if g.get("type") == "Feature":
        return _rings_ll(g.get("geometry"))
    if g.get("type") == "Polygon":
        return [g["coordinates"][0]] if g.get("coordinates") else []
    if g.get("type") == "MultiPolygon":
        return [p[0] for p in g.get("coordinates") or [] if p]
    return []


def _tiles_svg(tpl, z, x0, y0, w, h, shift=(0.0, 0.0)):
    """Embed the tiles covering world-pixel box (x0, y0, w, h). Each tile is fetched on its own: a failed tile is drawn as a
    grey square instead of dropping the whole image (0.1.7.3 bug B). Returns (svg_fragment, loaded, needed, errors)."""
    import urllib.request
    imgs, loaded, needed, errs = [], 0, 0, []
    # shift = (dx, dy) world px: the ortho shows the roof at roofprint + shift (lean / registration), so the raster
    # is drawn moved by -shift and the roofprint overlay lands on the roof in the photo (0.1.7.4)
    sx_, sy_ = float(shift[0] or 0), float(shift[1] or 0)
    for ty in range(int((y0 + sy_) // 256), int((y0 + sy_ + h) // 256) + 1):
        for tx in range(int((x0 + sx_) // 256), int((x0 + sx_ + w) // 256) + 1):
            needed += 1
            url = tpl.replace("{z}", str(z)).replace("{x}", str(tx)).replace("{y}", str(ty))
            data = None
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "RoofMeasure-report/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                if len(data) < 500:
                    errs.append(f"tile {tx},{ty}: {len(data)} bytes")
                    data = None
            except Exception as ex:  # noqa
                errs.append(f"tile {tx},{ty}: {type(ex).__name__}")
                data = None
            X, Y = tx * 256 - x0 - sx_, ty * 256 - y0 - sy_
            if data is None:
                imgs.append(f'<rect x="{X:.1f}" y="{Y:.1f}" width="256" height="256" fill="#9ca3af"/>')
                continue
            loaded += 1
            mt = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
            imgs.append(f'<image x="{X:.1f}" y="{Y:.1f}" width="256.6" height="256.6" preserveAspectRatio="none" '
                        f'href="data:{mt};base64,{base64.b64encode(data).decode()}"/>')
    return "".join(imgs), loaded, needed, errs


def _fit_box(pts, aspect, margin, min_w):
    """box (x0, y0, w, h) around pts with the given w/h aspect and relative margin"""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, h = (max(xs) - min(xs)) * (1 + margin), (max(ys) - min(ys)) * (1 + margin)
    w = max(w, h * aspect, min_w)
    h = w / aspect
    return cx - w / 2, cy - h / 2, w, h


def _north_scale(W, H, px_per_ft, fg="#111", bg="#fff"):
    bar_ft = next(v for v in [5, 10, 20, 25, 50, 100, 200] if v * px_per_ft >= 90 or v == 200)
    L = bar_ft * px_per_ft
    return (f'<g aria-hidden="true"><rect x="{W-58}" y="8" width="50" height="70" fill="{bg}" fill-opacity="0.85" stroke="{fg}"/>'
            f'<line x1="{W-33}" y1="62" x2="{W-33}" y2="24" stroke="{fg}" stroke-width="2.5"/>'
            f'<polygon points="{W-33},14 {W-41},30 {W-25},30" fill="{fg}"/>'
            f'<text x="{W-33}" y="75" text-anchor="middle" font-size="13" font-weight="700" font-family="Arial" fill="{fg}">N</text>'
            f'<rect x="10" y="{H-44}" width="{L+20:.1f}" height="36" fill="{bg}" fill-opacity="0.85" stroke="{fg}"/>'
            f'<line x1="20" y1="{H-16}" x2="{20+L:.1f}" y2="{H-16}" stroke="{fg}" stroke-width="4"/>'
            f'<line x1="20" y1="{H-22}" x2="20" y2="{H-10}" stroke="{fg}" stroke-width="2"/><line x1="{20+L:.1f}" y1="{H-22}" x2="{20+L:.1f}" y2="{H-10}" stroke="{fg}" stroke-width="2"/>'
            f'<text x="20" y="{H-27}" font-size="12" font-family="Arial" fill="{fg}">{bar_ft} ft (approx.)</text></g>')


def _label(x, y, text, size=12, fg="#111", bg="#fff", anchor="middle", weight="700"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" font-weight="{weight}" font-family="Arial, sans-serif" '
            f'fill="{fg}" stroke="{bg}" stroke-width="3.5" paint-order="stroke">{esc(text)}</text>')


def edge_len_label(e):
    t = str(e.get("type", "")).lower()
    if t == "rake" and is_number(e.get("sloped_length_ft")):
        return f'{float(e["sloped_length_ft"]):.1f}\' sloped ({float(e["length_ft"]):.1f} plan)'
    return f'{float(e["length_ft"]):.1f}\''


def _overlay(r, P, scale_px_per_ft, casing=True, numbers=True, lengths=True, facets=True, show_cand=False):
    """Vector roof model drawn with projection P(lon, lat) -> (x, y). Geometry from the result only (free data)."""
    C = pal(r)
    out, labels = [], []
    fs = 13
    n_fac = len(r.get("facets") or [])
    n_int = sum(1 for sg in r.get("line_segments") or [] if sg.get("coords_lonlat") and not sg.get("deleted") and (show_cand or not sg.get("unverified")) and str(sg.get("type")) in ("ridge", "hip", "valley", "wall_flashing", "eave", "rake"))
    dense = n_int > 8  # many lines: label them L<i> (lengths in the Interior lines table) to keep the page readable
    # facets with pitch badges
    fboxes = []  # 0.1.7.6: label boxes, so skylight / edge labels avoid them
    if facets:
        for fx in r.get("facets") or []:
            ring = fx.get("polygon_lonlat")
            if not ring or len(ring) < 4:
                continue
            pts = [P(*p) for p in ring]
            out.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '" fill="#ffffff" fill-opacity="0.10" stroke="#ffffff" stroke-width="1" stroke-dasharray="3 3"/>')
            cx = sum(p[0] for p in pts[:-1]) / (len(pts) - 1)
            cy = sum(p[1] for p in pts[:-1]) / (len(pts) - 1)
            pa = fx.get("plan_area_sqft")
            src = str(fx.get("pitch_source") or "")
            t1 = f'{fx.get("id")}: {fx.get("pitch")}' + (" lidar" if "lidar" in src else "")
            t2 = f'{float(pa):.0f} sq ft plan' if is_number(pa) and n_fac <= 6 else ""
            if n_fac > 6:
                t1 = f'{fx.get("id")} {fx.get("pitch")}'
                fboxes.append((cx - 30, cy - 11, cx + 30, cy + 4))
                labels.append(f'<rect x="{cx-30:.1f}" y="{cy-11:.1f}" width="60" height="15" rx="4" fill="#111" fill-opacity="0.7"/>'
                              f'<text x="{cx:.1f}" y="{cy:.1f}" text-anchor="middle" font-size="9.5" font-weight="700" font-family="Arial" fill="#fff">{esc(t1)}</text>')
                continue
            fboxes.append((cx - 48, cy - 16, cx + 48, cy - 16 + (34 if t2 else 20)))
            labels.append(f'<rect x="{cx-48:.1f}" y="{cy-16:.1f}" width="96" height="{34 if t2 else 20}" rx="5" fill="#111" fill-opacity="0.78"/>'
                          f'<text x="{cx:.1f}" y="{cy-1:.1f}" text-anchor="middle" font-size="12" font-weight="700" font-family="Arial" fill="#fff">{esc(t1)}</text>'
                          + (f'<text x="{cx:.1f}" y="{cy+13:.1f}" text-anchor="middle" font-size="10.5" font-family="Arial" fill="#fff">{esc(t2)}</text>' if t2 else ""))
    # interior lines
    for i, sg in enumerate(r.get("line_segments") or []):
        c = sg.get("coords_lonlat")
        t = str(sg.get("type", "")).lower()
        lid = sg.get("source") == "lidar"
        if not c or len(c) < 2 or sg.get("deleted") or not (t in ("ridge", "hip", "valley") or (lid and t in ("wall_flashing", "eave", "rake"))):
            continue
        if sg.get("unverified") and not show_cand:
            continue  # candidates are not counted and are listed in the appendix, not drawn on the main diagrams
        a, b = P(*c[0]), P(*c[1])
        cand = bool(sg.get("unverified"))
        dash = ' stroke-dasharray="8 6"' if cand else (' stroke-dasharray="' + STYLE[t]["dash"] + '"' if STYLE[t]["dash"] and not casing else "")
        if t not in C:
            continue
        if casing:
            out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#000" stroke-width="7" stroke-linecap="round"{" stroke-opacity=\"0.5\"" if cand else ""}/>')
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{C[t]}" stroke-width="4" stroke-linecap="round"{dash}/>')
        L = float(sg.get("length_ft") or 0)
        if lengths and L >= 3:
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            nm = {"wall_flashing": "WALL FL"}.get(t, t.upper())
            if dense:
                labels.append(_label(mx, my - 5, f'L{i}{"?" if cand else ""}', size=9.5, fg="#111"))
            else:
                labels.append(_label(mx, my - 7, f'{"L:" if lid else ""}{nm}{"?" if cand else ""} {L:.1f}\'', size=11.5, fg=C[t] if not casing else "#111"))
    # skylights (lidar candidates dashed; user-entered with a location solid)
    for k in r.get("skylights") or []:
        c = k.get("centroid_lonlat")
        if not c:
            continue
        x, y = P(*c)
        user = k.get("source") == "user"
        if not user and not show_cand:
            continue
        out.append(f'<rect x="{x-7:.1f}" y="{y-7:.1f}" width="14" height="14" fill="#38bdf8" fill-opacity="0.35" stroke="#0369a1" stroke-width="2"{"" if user else " stroke-dasharray=\"3 2\""}/>')
        labels.append(_label(x, y - 10, f'{k.get("key")}{"" if user else "?"}', size=9.5, fg="#0369a1"))
    # outline edges
    A = 0.0
    E = [e for e in (r.get("edges") or []) if e.get("from") and e.get("to")]
    pts_all = [P(*e["from"]) for e in E]
    for k in range(len(pts_all)):
        x1, y1 = pts_all[k]; x2, y2 = pts_all[(k + 1) % len(pts_all)]
        A += x1 * y2 - x2 * y1
    placed = list(fboxes)
    for e in E:  # number circles occupy space too
        a, b = P(*e["from"]), P(*e["to"])
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        placed.append((mx - 12, my - 12, mx + 12, my + 12))
    for e in E:
        t = str(e.get("type", "")).lower()
        a, b = P(*e["from"]), P(*e["to"])
        col = C.get(t, "#ffffff")
        st = STYLE.get(t, OTHER_STYLE)
        dash = f' stroke-dasharray="{st["dash"]}"' if (st["dash"] and not casing) else ""
        if casing:
            out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#000" stroke-width="8" stroke-linecap="round"/>')
        out.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{col}" stroke-width="4.5" stroke-linecap="round"{dash}/>')
        dx, dy = b[0] - a[0], b[1] - a[1]
        Ln = math.hypot(dx, dy) or 1
        nx, ny = (dy / Ln, -dx / Ln) if A > 0 else (-dy / Ln, dx / Ln)  # outward normal (screen y down)
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        if numbers:
            labels.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="{fs*0.85:.1f}" fill="#fff" stroke="{col}" stroke-width="2.5"/>'
                          f'<text x="{mx:.1f}" y="{my + fs*0.38:.1f}" font-size="{fs:.1f}" font-family="Arial,sans-serif" font-weight="700" text-anchor="middle" fill="#111">{esc(e["i"])}</text>')
        if lengths and Ln > 18:
            txt = f'{t.upper()} {edge_len_label(e)}'
            tw, th = 6.1 * len(txt), 14
            best = None
            for off in (24, 42, 60, 78):          # simple collision avoidance: push the label further out until it is clear
                lx, ly = mx + nx * off, my + ny * off + 4
                lx = min(max(lx, tw / 2 + 4), PAGE_W - tw / 2 - 4)  # keep labels on the page
                box = (lx - tw / 2, ly - th + 2, lx + tw / 2, ly + 4)
                if not any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in placed):
                    best = (lx, ly, box)
                    break
            if best is None:
                lx, ly = min(max(mx + nx * 24, tw / 2 + 4), PAGE_W - tw / 2 - 4), my + ny * 24 + 4
                best = (lx, ly, (lx - tw / 2, ly - th + 2, lx + tw / 2, ly + 4))
            placed.append(best[2])
            labels.append(_label(best[0], best[1], txt, size=11, fg="#111"))
    return "".join(out) + _features(r, P, scale_px_per_ft, placed) + "".join(labels)


def _features(r, P, s, placed=None):
    """0.1.7.5: labelled roof features (candidates): roof decks / flat sections (brown, hatched by dashes) and skylights
    (rotated rectangles at their measured size). Drawn on the diagram and the overlay pages."""
    rf = r.get("roof_features") or {}
    out = []
    # facet pitch badges sit at the facet centroids on every page (some pages draw them in a separate pass): keep labels clear of them
    placed = list(placed) if placed is not None else []
    nf = len(r.get("facets") or [])
    for fx in r.get("facets") or []:
        ring = fx.get("polygon_lonlat")
        if ring and len(ring) >= 4:
            pts0 = [P(*p) for p in ring[:-1]]
            fcx, fcy = sum(p[0] for p in pts0) / len(pts0), sum(p[1] for p in pts0) / len(pts0)
            placed.append((fcx - 30, fcy - 11, fcx + 30, fcy + 4) if nf > 6 else (fcx - 48, fcy - 16, fcx + 48, fcy + 18))
    for d in rf.get("decks") or []:
        O = d.get("outline_lonlat") or []
        if len(O) < 3:
            continue
        pts = [P(*p) for p in O]
        pp = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        out.append(f'<polygon points="{pp}" fill="#a16207" fill-opacity="0.35" stroke="#000" stroke-width="4.5"/><polygon points="{pp}" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-dasharray="6 3"/>')
        # 0.1.7.6: two-line label placed clear of the facet badges / edge labels (centre, then above / below / beside the deck)
        pl = placed if placed is not None else []
        ys = [p[1] for p in pts]; xs = [p[0] for p in pts]
        tw = 150
        best = (cx, cy)
        for lx, ly in [(cx, cy), (cx, min(ys) - 22), (cx, max(ys) + 14), (max(xs) + tw / 2 + 6, cy), (min(xs) - tw / 2 - 6, cy)]:
            box = (lx - tw / 2, ly - 15, lx + tw / 2, ly + 13)
            if not any(box[0] < b2[2] and b2[0] < box[2] and box[1] < b2[3] and b2[1] < box[3] for b2 in pl):
                best = (lx, ly)
                break
        pl.append((best[0] - tw / 2, best[1] - 15, best[0] + tw / 2, best[1] + 13))
        out.append(_label(best[0], best[1] - 4, f'DECK ≈{num(d.get("area_sqft"), 0)} sq ft', size=11, fg="#7c2d12"))
        out.append(_label(best[0], best[1] + 10, 'inspect: rubber/membrane?', size=9.5, fg="#7c2d12"))
    for k in rf.get("skylights") or []:
        c = k.get("centroid_lonlat")
        if not c:
            continue
        x, y = P(*c)
        w = float(k.get("w_ft") or 2.5) * s
        h = float(k.get("h_ft") or 2.0) * s
        a = float(k.get("angle_deg") or 0)
        out.append(f'<g transform="translate({x:.1f},{y:.1f}) rotate({a:.1f})"><rect x="{-w/2:.1f}" y="{-h/2:.1f}" width="{w:.1f}" height="{h:.1f}" fill="#38bdf8" fill-opacity="0.45" stroke="#000" stroke-width="3.5"/>'
                   f'<rect x="{-w/2:.1f}" y="{-h/2:.1f}" width="{w:.1f}" height="{h:.1f}" fill="none" stroke="#e0f2fe" stroke-width="1.5"/></g>')
        sz = f' {num(k.get("w_ft"), 1)}×{num(k.get("h_ft"), 1)} ft' if k.get("w_ft") else ''
        txt = f'{k.get("label", "S")}{sz}' + ('' if k.get("counted", True) else '?')
        # 0.1.7.6: label collision avoidance against the edge-length labels / number circles (and earlier skylight labels)
        tw, th, r0 = 5.9 * len(txt), 13, max(w, h) / 2
        cand = [(x, y - r0 - 5), (x, y + r0 + 14), (x + r0 + tw / 2 + 4, y + 4), (x - r0 - tw / 2 - 4, y + 4), (x, y - r0 - 20), (x, y + r0 + 29)]
        pl = placed if placed is not None else []
        best = cand[0]
        for lx, ly in cand:
            box = (lx - tw / 2, ly - th + 2, lx + tw / 2, ly + 3)
            if not any(box[0] < b2[2] and b2[0] < box[2] and box[1] < b2[3] and b2[1] < box[3] for b2 in pl):
                best = (lx, ly)
                break
        pl.append((best[0] - tw / 2, best[1] - th + 2, best[0] + tw / 2, best[1] + 3))
        out.append(_label(best[0], best[1], txt, size=10.5, fg="#075985"))
    return "".join(out)


def _legend(r, x, y, cand=False, bg="#fff"):
    C = pal(r)
    items = [("eave", "Eave (level)"), ("rake", "Rake (sloped)"), ("ridge", "Ridge"), ("hip", "Hip"), ("valley", "Valley")]
    if any(sg.get("type") == "wall_flashing" and not sg.get("deleted") for sg in r.get("line_segments") or []) or float((r.get("lines") or {}).get("wall_flashing_lf") or 0) > 0:
        items.append(("wall_flashing", "Wall flashing"))
    H = [f'<g><rect x="{x}" y="{y}" width="150" height="{22 + 18 * (len(items) + (1 if cand else 0))}" fill="{bg}" fill-opacity="0.9" stroke="#111"/>'
         f'<text x="{x+8}" y="{y+16}" font-size="12" font-weight="700" font-family="Arial">Legend</text>']
    for k, (t, lab) in enumerate(items):
        yy = y + 32 + 18 * k
        H.append(f'<line x1="{x+8}" y1="{yy}" x2="{x+42}" y2="{yy}" stroke="#000" stroke-width="7"/><line x1="{x+8}" y1="{yy}" x2="{x+42}" y2="{yy}" stroke="{C[t]}" stroke-width="4"/>'
                 f'<text x="{x+50}" y="{yy+4}" font-size="11.5" font-family="Arial">{esc(lab)}</text>')
    if cand:
        yy = y + 32 + 18 * len(items)
        H.append(f'<line x1="{x+8}" y1="{yy}" x2="{x+42}" y2="{yy}" stroke="#9333ea" stroke-width="4" stroke-dasharray="8 6"/><text x="{x+50}" y="{yy+4}" font-size="11.5" font-family="Arial">unverified (?)</text>')
    H.append("</g>")
    return "".join(H)


def aerial_views(r):
    """All aerial-based figures of the report: (full-page aerial, composite). Each is (kind, svg-or-None, info). Cached per result."""
    tpl = ortho_template()
    res = {"aerial": None, "composite": None, "info": {}}
    if not tpl or os.environ.get("ROOFMEASURE_NO_AERIAL"):
        res["info"]["error"] = "no MassGIS ortho template"
        return res
    z = 19
    W = _world(z)
    oa = r.get("ortho_align") if isinstance(r.get("ortho_align"), dict) else {}
    shift = (float(oa.get("dx_px") or 0), float(oa.get("dy_px") or 0)) if oa.get("applied") and oa.get("z", 19) == z else (0.0, 0.0)
    res["info"]["shift_px"] = shift
    ring = ring_of(r["footprint_geojson"])
    lat0 = float(r["lat"])
    m_per_px = 156543.03392 * math.cos(math.radians(lat0)) / (2 ** z)
    px_per_ft = 0.3048 / m_per_px
    roof = [W(*p) for p in ring]
    aspect = PAGE_W / PAGE_H
    # --- page A: context (footprint + parcel + lot structures)
    ctx = list(roof)
    for g in [r.get("parcel_geojson")]:
        for rg in _rings_ll(g):
            ctx += [W(*p) for p in rg]
    x0, y0, w, h = _fit_box(ctx, aspect, 0.25, 260)
    frag, ld, nd, er = _tiles_svg(tpl, z, x0, y0, w, h, shift)
    sx = PAGE_W / w
    def PA(lo, la):
        p = W(lo, la)
        return ((p[0] - x0) * sx, (p[1] - y0) * sx)
    ov = []
    for rg in _rings_ll(r.get("parcel_geojson")):
        pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in (PA(*p) for p in rg))
        ov.append(f'<polygon points="{pts}" fill="none" stroke="#000" stroke-width="5"/><polygon points="{pts}" fill="none" stroke="#facc15" stroke-width="3" stroke-dasharray="12 6"/>')
    for st in r.get("lot_footprints") or []:
        if st.get("role") == "primary":
            continue
        for rg in _rings_ll(st.get("geometry")):
            pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in (PA(*p) for p in rg))
            ov.append(f'<polygon points="{pts}" fill="#ffffff" fill-opacity="0.12" stroke="#000" stroke-width="5"/><polygon points="{pts}" fill="none" stroke="#ffffff" stroke-width="2.5"/>')
    pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in (PA(*p) for p in ring))
    ov.append(f'<polygon points="{pts}" fill="none" stroke="#000" stroke-width="6"/><polygon points="{pts}" fill="none" stroke="#22d3ee" stroke-width="3.5"/>')
    if ld:
        res["aerial"] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PAGE_W:.0f} {PAGE_H:.0f}" width="100%" class="fullfig" role="img" aria-labelledby="pa-t pa-d">'
                         f'<title id="pa-t">Aerial photo, full page</title><desc id="pa-d">MassGIS 2025 orthoimagery around {esc(r["address"])} with the roofprint outlined in cyan'
                         f'{", the tax parcel boundary dashed yellow" if r.get("parcel_geojson") else ""} and other structures on the lot in white.</desc>'
                         f'<svg x="0" y="0" width="{PAGE_W:.0f}" height="{PAGE_H:.0f}" viewBox="0 0 {w:.2f} {h:.2f}" preserveAspectRatio="none">{frag}</svg>'
                         + "".join(ov) + _north_scale(PAGE_W, PAGE_H, px_per_ft * sx) + '</svg>')
    res["info"]["aerial"] = {"tiles_loaded": ld, "tiles_needed": nd, "errors": er[:6]}
    # --- page C: composite (roof only, tighter)
    x0, y0, w, h = _fit_box(roof, aspect, 0.55, 150)
    frag, ld2, nd2, er2 = _tiles_svg(tpl, z, x0, y0, w, h, shift)
    sx2 = PAGE_W / w
    def PC(lo, la):
        p = W(lo, la)
        return ((p[0] - x0) * sx2, (p[1] - y0) * sx2)
    if ld2:
        cand = False  # candidates are not drawn on the main pages (appendix)
        res["composite"] = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PAGE_W:.0f} {PAGE_H:.0f}" width="100%" class="fullfig" role="img" aria-labelledby="pc-t pc-d">'
                            f'<title id="pc-t">Roof diagram over the aerial photo</title><desc id="pc-d">The vector roof model (edges numbered as in the tables, colour-coded by type, '
                            'interior ridge/hip/valley lines, facet pitch badges) drawn over MassGIS 2025 orthoimagery. Geometry comes from the roofprint and lidar, not from the photo.</desc>'
                            f'<svg x="0" y="0" width="{PAGE_W:.0f}" height="{PAGE_H:.0f}" viewBox="0 0 {w:.2f} {h:.2f}" preserveAspectRatio="none">{frag}</svg>'
                            + _overlay(r, PC, px_per_ft * sx2) + _legend(r, 10, 10, cand) + _north_scale(PAGE_W, PAGE_H, px_per_ft * sx2) + '</svg>')
    res["info"]["composite"] = {"tiles_loaded": ld2, "tiles_needed": nd2, "errors": er2[:6]}
    return res


def vector_page(r, show_cand=False):
    """Full-page vector diagram (no imagery): local feet, north up. show_cand=True: appendix copy with the
    uncounted candidate lines drawn dashed."""
    ring = ring_of(r["footprint_geojson"])
    lat0 = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
    lon0 = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
    ky = 364000.0
    kx = ky * math.cos(math.radians(lat0))
    xy = [((p[0] - lon0) * kx, -(p[1] - lat0) * ky) for p in ring]
    x0, y0, w, h = _fit_box(xy, PAGE_W / PAGE_H, 0.22, 30)
    s = PAGE_W / w
    def PV(lo, la):
        return (((lo - lon0) * kx - x0) * s, (-(la - lat0) * ky - y0) * s)
    pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in (PV(*p) for p in ring))
    cand = show_cand and any(sg.get("unverified") for sg in r.get("line_segments") or [])
    sid = "pa" if show_cand else "pv"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PAGE_W:.0f} {PAGE_H:.0f}" width="100%" class="fullfig" role="img" aria-labelledby="{sid}-t {sid}-d">'
            f'<title id="{sid}-t">{"Candidate lines (not counted)" if show_cand else "Roof measurement diagram"}</title><desc id="{sid}-d">Plan view of the roof model at {esc(r["address"])}: outline edges numbered as in the tables '
            'and labelled with type and length (rakes sloped with the plan length in brackets, eaves level), interior ridge/hip/valley lines with lengths, '
            'and a pitch and plan-area badge on each facet. North is up.</desc>'
            f'<rect x="0" y="0" width="{PAGE_W:.0f}" height="{PAGE_H:.0f}" fill="#f8fafc" stroke="#595959"/>'
            f'<polygon points="{pts}" fill="#cbd5e1" stroke="none"/>'
            + _overlay(r, PV, s, casing=True, show_cand=show_cand) + _legend(r, 10, 10, cand) + _north_scale(PAGE_W, PAGE_H, s) + '</svg>')


def ortho_shift_text(r):
    oa = r.get("ortho_align") if isinstance(r.get("ortho_align"), dict) else {}
    if oa.get("applied"):
        return (f'Photo shifted {num(abs(oa.get("dx_m") or 0), 1)} m {"W" if (oa.get("dx_m") or 0) > 0 else "E"} and {num(abs(oa.get("dy_m") or 0), 1)} m '
                f'{"S" if (oa.get("dy_m") or 0) > 0 else "N"} so the roof in the photo sits on the roofprint (ortho lean/offset estimate, {esc(oa.get("confidence"))} confidence; residual in the Appendix).')
    if oa.get("status") == "ok" and oa.get("confidence") != "low":
        return f'Photo not shifted (ortho alignment turned off; estimate was {num(oa.get("shift_m"), 1)} m). The 2025 orthos are not true orthos, so roofs can sit a few metres off the roofprint.'
    if oa.get("status") == "ok":
        return f'Ortho offset estimate {num(oa.get("shift_m"), 1)} m was low-confidence and not applied. The 2025 orthos are not true orthos, so roofs can sit a few metres off the roofprint.'
    return 'The 2025 orthos are not true orthos, so roofs can sit a few metres off the roofprint.'


def ortho_appendix(r):
    oa = r.get("ortho_align") if isinstance(r.get("ortho_align"), dict) else {}
    H = []
    if oa.get("status") == "ok":
        H.append('<h3>Ortho lean / offset (free MassGIS 2025 pixels)</h3><p class="note">' + esc(oa.get("method")) +
                 f'. Estimated offset of the roof in the photo vs the roofprint: {num(oa.get("dx_m"), 2)} m east, {num(oa.get("dy_m"), 2)} m north '
                 f'({num(oa.get("shift_m"), 2)} m; edge score {esc(oa.get("score0"))} → {esc(oa.get("score"))}, peak/median {esc(oa.get("ratio"))}, peak/second {esc(oa.get("sep"))}, '
                 f'confidence {esc(oa.get("confidence"))}, {"applied to the aerial pages" if oa.get("applied") else "NOT applied"}). '
                 f'Residual per edge after the shift: median {num(oa.get("residual_median_m"), 2)} m, max {num(oa.get("residual_max_m"), 2)} m'
                 + (f'; {esc(oa.get("edges_no_clear_edge"))} edge(s) with no clear photo edge within ±2 m (shown —)' if oa.get("edges_no_clear_edge") else '') + ' '
                 '(what one translation cannot explain: lean differs with roof height, or the roofprint differs from the roof). Measurements use the roofprint, not the photo.</p>')
        rg = oa.get("region") if isinstance(oa.get("region"), dict) else None
        if rg:
            H.append(f'<p class="note">Cross-check (not used for the shift): brightness separation of the {esc(rg.get("labels"))} lidar roof planes in the photo, eta² {num(rg.get("eta0"), 3)} at no shift → {num(rg.get("eta"), 3)} at the shift.</p>')
        lo = r.get("lidar_outline") if isinstance(r.get("lidar_outline"), dict) else None
        if lo and lo.get("iou") is not None:
            H.append('<h3>Roofprint vs lidar building outline</h3><p class="note">' + esc(lo.get("method")) +
                     f'. Overlap (IoU) {num(lo.get("iou0"), 3)} as given → {num(lo.get("iou"), 3)} after {num(lo.get("dx_m"), 2)} m east, {num(lo.get("dy_m"), 2)} m north'
                     f'{" (" + "applied to the lidar features: decks, dormers, lidar skylights" + ")" if lo.get("applied") else " (not applied)"}. '
                     f'Lidar building {num(lo.get("lidar_area_sqft"), 0)} sq ft vs roofprint {num(lo.get("roofprint_area_sqft"), 0)} sq ft (plan, incl. overhangs); '
                     f'{num(lo.get("outside_area_sqft"), 0)} sq ft of lidar building lies more than 1.5 m outside the roofprint'
                     + (' — the roofprint may not cover the whole current house: check.' if float(lo.get("outside_area_sqft") or 0) >= 150 else '.') + '</p>')
        rj = (r.get("roof_features") or {}).get("rejected") or []
        if rj:
            H.append('<table class="compact"><caption>Ortho patches rejected as skylights (why)</caption><thead><tr><th scope="col">Patch</th><th scope="col">Size ft</th><th scope="col">Reason</th></tr></thead><tbody>'
                     + "".join(f'<tr><td>{esc(k.get("key"))}</td><td class="n">{num(k.get("w_ft"), 1)}×{num(k.get("h_ft"), 1)}</td><td>{esc(k.get("reason"))}</td></tr>' for k in rj[:20]) + '</tbody></table>')
        rs = oa.get("residuals") or []
        if rs:
            H.append('<table class="compact"><thead><tr><th scope="col">Edge</th>' + "".join(f'<th scope="col" class="n">{esc(x.get("edge"))}</th>' for x in rs[:24]) +
                     '</tr></thead><tbody><tr><th scope="row">Residual (m, along the edge normal)</th>' + "".join(f'<td class="n">{num(x.get("residual_m"), 2)}</td>' for x in rs[:24]) + '</tr></tbody></table>')
    elif oa.get("status"):
        H.append(f'<p class="note">Ortho offset estimate unavailable ({esc(oa.get("status"))} {esc(oa.get("error") or "")}).</p>')
    lf = r.get("lidar_model_fit") if isinstance(r.get("lidar_model_fit"), dict) else {}
    if lf.get("facets"):
        H.append('<h3>Lidar points vs the 3-D facets model</h3><p class="note">' + esc(lf.get("method")) +
                 f'. Model: {esc(lf.get("model"))}. Eave level {num(lf.get("eave_elev_ft"), 1)} ft elevation'
                 + (f', ground {num(lf.get("ground_elev_ft"), 1)} ft (eave {num(lf.get("eave_above_ground_ft"), 1)} ft above ground)' if lf.get("ground_elev_ft") is not None else '')
                 + f'. Median residual {num(lf.get("median_ft"), 2)} ft over {esc(lf.get("n_on_facets"))} roof points'
                 + (f'; roofprint-to-lidar registration shift {esc(lf["shift_ft"][0])} ft E / {esc(lf["shift_ft"][1])} ft N applied to the points (median {num(lf.get("median_unshifted_ft"), 2)} ft without it)' if lf.get("shift_applied") else ('; best registration shift hit the ±4.5 ft search limit (' + esc(lf["shift_search_limit"].get("dx")) + ' / ' + esc(lf["shift_search_limit"].get("dy")) + ' ft E/N), so it was NOT applied: the roofprint and the lidar may disagree (rebuilt or extended house?)' if lf.get("shift_search_limit") else '; no horizontal shift needed'))
                 + '. Large residuals on a facet mean the assumed model or its pitch does not match the lidar there (or trees / chimneys).</p>')
        H.append('<table class="compact"><thead><tr><th scope="col">Facet</th><th scope="col">Pitch</th><th scope="col" class="n">Points</th><th scope="col" class="n">Median (ft)</th>'
                 '<th scope="col" class="n">90th pct (ft)</th><th scope="col" class="n">Max (ft)</th><th scope="col" class="n">Bias (ft)</th></tr></thead><tbody>' +
                 "".join(f'<tr><th scope="row">{esc(x.get("facet"))}</th><td>{esc(x.get("pitch"))}</td><td class="n">{esc(x.get("n"))}</td><td class="n">{num(x.get("median_ft"), 2)}</td>'
                         f'<td class="n">{num(x.get("p90_ft"), 2)}</td><td class="n">{num(x.get("max_ft"), 2)}</td><td class="n">{num(x.get("bias_ft"), 2)}</td></tr>' for x in lf["facets"]) + '</tbody></table>')
    pt = r.get("ortho_patches") or []
    if pt:
        H.append('<table class="compact"><caption>Ortho patch candidates (skylight / chimney / vent; compact bright or dark rectangles in the free ortho, NOT_PROVEN)</caption><thead><tr>'
                 '<th scope="col">#</th><th scope="col" class="n">Approx. size (ft)</th><th scope="col" class="n">≈ sq ft</th><th scope="col">Tone</th><th scope="col" class="n">Contrast</th>'
                 '<th scope="col">Location (lon, lat)</th><th scope="col">Lidar match</th></tr></thead><tbody>')
        for k in pt:
            c = k.get("centroid_lonlat") or [0, 0]
            H.append(f'<tr><th scope="row">{esc(k.get("key"))}</th><td class="n">{num(k.get("approx_w_ft"), 1)} × {num(k.get("approx_h_ft"), 1)}</td><td class="n">{esc(k.get("approx_area_sqft"))}</td>'
                     f'<td>{esc(k.get("polarity"))}</td><td class="n">{esc(k.get("contrast"))}</td><td>{c[0]:.6f}, {c[1]:.6f}</td><td>{esc(k.get("lidar_match") or "—")}</td></tr>')
        H.append('</tbody></table>')
    dm = [d for d in (r.get("dormers") or [])]
    if dm:
        H.append('<table class="compact"><caption>Dormers (lidar candidates unless kept by the user; dormer gutters: inspect and clean)</caption><thead><tr><th scope="col">#</th><th scope="col">Type</th>'
                 '<th scope="col">Planes / pitch</th><th scope="col" class="n">Ridge LF</th><th scope="col" class="n">Gutter LF</th><th scope="col">Returns</th><th scope="col">Status</th></tr></thead><tbody>')
        for d in dm:
            H.append(f'<tr><th scope="row">{esc(d.get("key"))}</th><td>{esc(d.get("type"))}</td><td>{esc("+".join(d.get("planes") or []) or "—")} {esc(d.get("pitch") or "")}'
                     f'{(" on " + esc(d.get("host_pitch"))) if d.get("host_pitch") else ""}</td><td class="n">{num(d.get("ridge_lf"), 1) if is_number(d.get("ridge_lf")) else "—"}</td>'
                     f'<td class="n">{num(d.get("gutter_lf"), 1) if is_number(d.get("gutter_lf")) else "—"}</td><td>{esc(d.get("returns"))}</td><td>{esc(d.get("status"))} · {esc(d.get("confidence") or d.get("source"))}</td></tr>')
        H.append('</tbody></table>')
    return "".join(H)


def appendix_section(r):
    """Appendix: everything NOT counted (candidate / deleted lines, uncounted model wall flashing, lidar plane and
    step tables, skylight candidates). A person can promote any candidate to counted in the app (tap it, Confirm)
    or in the report editor; the totals in the body never include these."""
    sg, sky = r.get("lidar_seg"), r.get("skylights") or []
    skc = sky
    cands = [(i, x) for i, x in enumerate(r.get("line_segments") or []) if x.get("unverified") or x.get("deleted")]
    lc = r.get("line_candidates") or {}
    oapp = ortho_appendix(r)
    if not cands and not sg and not sky and not lc.get("wall_flashing_model_lf") and not oapp:
        return ""
    H = ['<section aria-labelledby="h-app" class="pb"><h2 id="h-app">Appendix — candidates and lidar detail (NOT counted)</h2>',
         '<p class="note">Nothing on this page is in the totals. Candidates come from the facets model (when the roof model is ASSUMED) or from the lidar '
         'segmentation (when the model is not lidar-verified, the line is low-confidence, or it is wall flashing). To count one, tap it on the map and choose '
         'Confirm (or set its type in the report editor); it then moves into the counted totals.</p>']
    if lc.get("wall_flashing_model_lf"):
        H.append(f'<p>Facets-model step walls (wall flashing) not counted because the roof model is not lidar-verified: {num(lc.get("wall_flashing_model_lf"), 1)} LF. '
                 'Add a wall-flashing line by hand only if a sidewall really rises above the roof plane.</p>')
    if cands:
        if any(x.get("coords_lonlat") and x.get("unverified") for _, x in cands):
            H.append('<figure class="fullpage" style="margin:0">' + vector_page(r, show_cand=True) + '<p class="cap">Candidate lines dashed with "?"; counted lines solid.</p></figure>')
        H.append('<table class="compact"><caption>Candidate and deleted lines (not counted)</caption><thead><tr><th scope="col">Line</th><th scope="col">Type</th>'
                 '<th scope="col" class="n">Length (ft)</th><th scope="col">Why not counted</th></tr></thead><tbody>')
        for i, x in cands:
            why = "deleted by user" if x.get("deleted") else (
                f'lidar {x.get("lidar_source") or "line"}, confidence {x.get("lidar_conf")}' + (f', drop {num(x.get("drop_ft"), 1)} ft' if is_number(x.get("drop_ft")) else "")
                + ("; wall flashing needs confirmation" if str(x.get("type")) == "wall_flashing" else "")
                + (f'; doubtful: {x.get("lidar_doubt")}' if x.get("lidar_doubt") else "")
                if x.get("source") == "lidar" else "facets-model line, roof model ASSUMED (not lidar-verified)")
            H.append(f'<tr><th scope="row">L{i}</th><td>{esc(str(x.get("type") or x.get("auto_type")).replace("_", " ").title())}</td><td class="n">{num(x.get("length_ft"), 1)}</td><td>{esc(why)}</td></tr>')
        H.append('</tbody></table>')
    if sg:
        H.append('<table class="compact"><caption>Lidar roof planes</caption><thead><tr><th scope="col">Plane</th><th scope="col" class="n">Points</th><th scope="col">Pitch</th>'
                 '<th scope="col" class="n">Rise (raw)</th><th scope="col" class="n">Facing (deg)</th><th scope="col" class="n">RMS (m)</th><th scope="col" class="n">Plan area ≈ (sq ft)</th><th scope="col">Confidence</th></tr></thead><tbody>')
        for p in (sg.get("planes") or [])[:30]:
            H.append(f'<tr><th scope="row">{esc(p.get("id"))}</th><td class="n">{esc(p.get("n_points"))}</td><td>{esc(p.get("pitch"))}</td><td class="n">{num(p.get("rise_raw"), 2)}</td>'
                     f'<td class="n">{num(p.get("aspect_deg"), 0) if is_number(p.get("aspect_deg")) else "flat"}</td><td class="n">{num(p.get("rms_m"), 3)}</td>'
                     f'<td class="n">{esc(p.get("plan_area_sqft_approx"))}</td><td>{esc(p.get("confidence"))}{" · small plane (flagged)" if p.get("small") else ""}</td></tr>')
        H.append('</tbody></table>')
        st = sg.get("steps") or []
        if st:
            H.append('<table class="compact"><caption>Height jumps (step edges) found in the lidar</caption><thead><tr><th scope="col">Class</th><th scope="col">Detail</th>'
                     '<th scope="col" class="n">Plan (ft)</th><th scope="col" class="n">Length (ft)</th><th scope="col" class="n">Drop (ft)</th><th scope="col">Planes</th><th scope="col">Counted?</th></tr></thead><tbody>')
            for x in st[:30]:
                cnt = "already in footprint edges" if x.get("on_footprint") else "see the lines tables"
                H.append(f'<tr><td>{esc(str(x.get("type")).replace("_", " "))}</td><td>{esc(x.get("subtype"))}</td><td class="n">{num(x.get("plan_length_ft"), 1)}</td>'
                         f'<td class="n">{num(x.get("length_ft"), 1)}</td><td class="n">{num(x.get("drop_ft"), 1)}</td><td>{esc(x.get("upper"))} over {esc(x.get("lower"))}</td><td>{esc(cnt)} · {esc(x.get("confidence"))}</td></tr>')
            H.append('</tbody></table>')

    if skc:
        H.append('<table class="compact"><caption>Skylights (lidar candidates: point voids, height dips or low intensity inside a plane; low confidence)</caption><thead><tr><th scope="col">#</th>'
                 '<th scope="col" class="n">Approx. size (ft)</th><th scope="col" class="n">≈ sq ft</th><th scope="col">Location (lon, lat)</th><th scope="col">Evidence / status</th></tr></thead><tbody>')
        for k in skc:
            c = k.get("centroid_lonlat")
            loc = f'{c[0]:.6f}, {c[1]:.6f}' + (f' (plane {k.get("plane")})' if k.get("plane") else "") if c else esc(k.get("note") or "—")
            sz = f'{num(k.get("approx_w_ft"), 1)} × {num(k.get("approx_h_ft"), 1)}' if is_number(k.get("approx_w_ft")) and is_number(k.get("approx_h_ft")) else "—"
            H.append(f'<tr><th scope="row">{esc(k.get("key"))}</th><td class="n">{sz}</td><td class="n">{esc(k.get("approx_area_sqft") or "—")}</td><td>{loc}</td>'
                     f'<td>{esc(", ".join(k.get("evidence") or []))} · {esc(k.get("status"))}{(" — " + esc(k.get("note"))) if k.get("note") and c else ""}</td></tr>')
        H.append('</tbody></table>')
    H.append(oapp)
    H.append('</section>')
    return "".join(H)


def lidar_seg_section(r):
    """Whole-roof lidar segmentation (planes, step edges) and skylight candidates/user skylights. All NOT_PROVEN."""
    sg, sky = r.get("lidar_seg"), r.get("skylights") or []
    if not sg and not sky:
        return ('<section aria-labelledby="h-seg"><h2 id="h-seg">Lidar roof segmentation and skylights</h2>'
                '<p class="note">No lidar roof cloud in this result (lidar off or unavailable); no planes, step edges or skylight candidates detected. '
                'Skylights can be added by hand in the report editor.</p></section>')
    H = ['<section aria-labelledby="h-seg"><h2 id="h-seg">Lidar roof segmentation and skylights (NOT_PROVEN)</h2>']
    if sg:
        sm = sg.get("summary") or {}
        H.append(f'<p class="note">Free USGS 3DEP lidar, {esc(sg.get("n_points"))} building points, {len(sg.get("planes") or [])} planes '
                 f'({esc(sm.get("n_small"))} small planes kept and flagged), coverage {num((sg.get("coverage") or 0) * 100, 0)}%. Lidar lines are counted only when the roof model is lidar-verified and the line is confident; '
                 f'wall flashing always needs a person to confirm a sidewall rises above the roof. Counted lines are in the Interior lines table, candidates in the Appendix ({esc(sm.get("lines_added"))} added; {esc(sm.get("model_lines_confirmed"))} model lines confirmed, '
                 f'{esc(sm.get("model_lines_retyped"))} re-typed). Wall flashing is only assigned where a wall rises above an adjacent lower roof plane; '
                 'otherwise a height jump is the upper plane\'s eave or rake.</p>')
    usr = [k for k in sky if k.get("source") == "user"]
    H.append(f'<p><b>Skylights: {len(usr)} user-entered</b>; {len(sky) - len(usr)} lidar candidate(s) (NOT_PROVEN, not counted) are listed in the Appendix. '
             'Plane and step-edge tables are in the Appendix.</p>')
    H.append('</section>')
    return "".join(H)


def feature_rows(r):
    """0.1.7.6: roof features are CANDIDATES (2-D ortho / lidar detections, NOT_PROVEN) and never part of the billable totals."""
    rf = r.get("roof_features") or {}
    sk, dk, dm = rf.get("skylights") or [], rf.get("decks") or [], rf.get("dormers") or []
    cs = [k for k in sk if k.get("counted", True)]
    un = [k for k in sk if not k.get("counted", True)]
    def lab(k):
        return f'{k.get("label")} {num(k.get("w_ft"), 1)}×{num(k.get("h_ft"), 1)} ft' if k.get("w_ft") else str(k.get("label"))
    txt = (f'{len(cs)}: ' + "; ".join(lab(k) for k in cs)) if cs else "none passed the checks"
    if un:
        txt += f' (+{len(un)} unchecked: ' + "; ".join(lab(k) + "?" for k in un) + ')'
    rows = [("Skylights (candidates, not in totals)", txt)]
    if dk:
        rows.append(("Roof deck / flat section (candidate, not in totals)", "; ".join(
            (f'≈{num(d.get("area_sqft"), 0)} sq ft' + (f' ({num(d.get("w_ft"), 1)}×{num(d.get("h_ft"), 1)} ft)' if d.get("w_ft") else '') + f' at {esc(d.get("pitch"))}: inspect for a rubber/membrane roof underneath') for d in dk)))
    if dm:
        rows.append(("Dormers (candidates, not in totals)", f'{len(dm)}: ' + "; ".join(f'{esc(d.get("key") or d.get("id") or "D")} {esc(d.get("type") or "dormer")}' + (f' (gutter ≈{num(d.get("gutter_lf"), 0)} LF)' if is_number(d.get("gutter_lf")) else '') for d in dm) + ' — dormer gutters: inspect and clean (debris, returns)'))
    return rows


def window_view(r, av):
    """0.1.7.5: one page, 2 × 2: aerial, diagram, overlay and a quick footage summary."""
    import re as _re
    def cp(svg):
        return _re.sub(r'\b(p[avc])-(t|d)\b', r'wv\1-\2', svg) if svg else '<div class="ph">not available</div>'
    _, _, mats = compute(r)
    L = r.get("lines") or {}
    rows = [("Roof area", f'{num(r["roof_area_sqft"])} sq ft'), ("Squares", num(r["squares"], 2)), ("Pitch", str(r["pitch"])),
            ("Eave", f'{num(r["eave_lf"])} LF'), ("Rake (sloped)", f'{num(r["rake_lf"])} LF'), ("Ridge", f'{num(L.get("ridge_lf") or 0)} LF'),
            ("Hip", f'{num(L.get("hip_lf") or 0)} LF'), ("Valley", f'{num(L.get("valley_lf") or 0)} LF'), ("Drip edge", f'{num(mats["drip_edge_lf"])} LF'),
            ("Gutters", f'{num(r["gutter_lf"])} LF, {esc(r["downspouts"])} downspouts')] + [(a, b) for a, b in feature_rows(r)]
    box = ('<div class="wvsum"><h3>Quick footage</h3><table class="compact"><tbody>' + "".join(f'<tr><th scope="row">{esc(a)}</th><td>{b}</td></tr>' for a, b in rows)
           + '</tbody></table><p class="note">Counted lines only (candidates in the Appendix). For estimating; verify on site.</p></div>')
    return ('<section class="fullpage pb" aria-labelledby="h-wv"><h2 id="h-wv">Window view</h2><div class="wv">'
            f'<div><h3>Aerial</h3>{cp(av.get("aerial"))}</div><div><h3>Diagram</h3>{cp(vector_page(r))}</div>'
            f'<div><h3>Overlay</h3>{cp(av.get("composite"))}</div>{box}</div></section>')


def fullpage_sections(r):
    av = aerial_views(r)
    info = av["info"]
    H = []
    def ph(what, inf):
        e = "; ".join((inf or {}).get("errors") or []) or info.get("error") or "unknown"
        d = r.get("aerial_diag") or {}
        return (f'<div class="ph fullph" role="note">{esc(what)} NOT AVAILABLE<br><span>The free MassGIS 2025 ortho tiles could not be loaded '
                f'({esc(e)}; app tile fetch: {esc(d.get("tiles_loaded", "?"))}/{esc(d.get("tiles_needed", "?"))} loaded'
                f'{", failures: " + esc("; ".join(x.get("error", "") for x in d.get("failures") or [])) if d.get("failures") else ""}). '
                'Paid imagery is never fetched. The vector diagram page is unaffected.</span></div>')
    a = info.get("aerial") or {}
    H.append(window_view(r, av))
    H.append('<section class="fullpage pb" aria-labelledby="h-fa"><h2 id="h-fa">Aerial photo</h2>'
             + (av["aerial"] or ph("AERIAL IMAGE", a))
             + f'<p class="cap">MassGIS 2025 statewide orthoimagery (15 cm, Commonwealth of Massachusetts), zoom 19, tiles {a.get("tiles_loaded", 0)}/{a.get("tiles_needed", 0)}. '
             'Cyan = roofprint used for the measurements' + ('; dashed yellow = MassGIS L3 tax parcel' if r.get("parcel_geojson") else '')
             + ('; white = other structures on the lot' if r.get("lot_footprints") else '') + '. ' + ortho_shift_text(r) + '</p></section>')
    H.append('<section class="fullpage pb" aria-labelledby="h-fv"><h2 id="h-fv">Roof diagram</h2>' + vector_page(r)
             + '<p class="cap">Roofprint + USGS lidar model. Edge numbers match the edge tables. Rake lengths are SLOPED '
             '(drip-edge length, plan length in brackets); eaves are level. Facet badges: pitch and plan area' + ('; "lidar" = per-facet lidar pitch used' if r.get("per_facet_pitch_used") else '')
             + '. "L:" = line detected in the lidar point cloud (not in the footprint model); '
             'with many lines they are labelled L&lt;n&gt; and their type and length are in the Interior lines table. Uncounted candidates are in the Appendix. '
             'Colour plus line style; colour-blind palette available in the app.</p></section>')
    c = info.get("composite") or {}
    H.append('<section class="fullpage pb" aria-labelledby="h-fc"><h2 id="h-fc">Diagram over aerial photo</h2>'
             + (av["composite"] or ph("AERIAL OVERLAY", c))
             + f'<p class="cap">The same vector model drawn over MassGIS 2025 orthoimagery (tiles {c.get("tiles_loaded", 0)}/{c.get("tiles_needed", 0)}) so eaves and rakes can be '
             'checked against the building. Blue eave, orange rake, red ridge, purple hip, teal valley (or the colour-blind palette). ' + ortho_shift_text(r) + '</p></section>')
    kind = "massgis_ortho_2025" if (av["aerial"] or av["composite"]) else "placeholder"
    return "".join(H), kind


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
    if "usa structures" in blob or "fema" in blob:
        a.append("FEMA / ORNL USA Structures building footprints (public FEMA FeatureServer; cite FEMA and ORNL), used outside MassGIS coverage.")
    if isinstance(r.get("structures_on_lot"), dict):
        a.append("MassGIS Level 3 Property Tax Parcels (lot boundary for the detached-structures list).")
    if isinstance(r.get("solar"), dict) and (r["solar"].get("pvwatts") or {}).get("worked"):
        a.append("NREL/NLR PVWatts v8 (public DEMO_KEY) for PVWatts-derived solar values.")
    if aerial_kind == "massgis_ortho_2025":
        oa = r.get("ortho_align") if isinstance(r.get("ortho_align"), dict) else {}
        a.append("MassGIS 2025 statewide orthoimagery (15 cm), Commonwealth of Massachusetts — aerial pages"
                 + ("; its pixels were also used for the lean/offset estimate and patch candidates" if oa.get("status") == "ok" else "") + ".")
    refs = r.get("reference_layers_viewed") or []
    if refs:
        a.append("Viewed in the app for reference only (no measurement, analysis or storage): " + ", ".join(str(x) for x in refs) + ".")
    e3 = r.get("edits_3d") or {}
    if e3.get("n"):
        a.append(f'User edits in the 3-D roof editor: {e3.get("n")} ({e3.get("summary") or ""}); built from the roofprint, lidar and facets model only.')
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
table { border-collapse: collapse; width: 100%; margin: 4px 0 8px; page-break-inside: auto; font-size: 8.5pt; }\ntr { page-break-inside: avoid; break-inside: avoid; }\ntable.compact { font-size: 8pt; } table.compact th, table.compact td { padding: 1px 4px; }
caption { text-align: left; font-weight: bold; padding: 2px 0 4px; color: #111; }
th, td { border: 1px solid #767676; padding: 2px 5px; text-align: left; vertical-align: top; }
thead th { background: #e3e8ee; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 6px 0; }
.kpi { border: 1px solid #767676; padding: 6px; } .kpi b { display: block; font-size: 14pt; } .kpi span { font-size: 8.5pt; }
.diagram { border: 0; max-height: 4.2in; display:block; margin:0 auto; }
.na { font-style: italic; color: #333; }
.formula { font-family: "Courier New", monospace; font-size: 9pt; }
.disclaimer { border: 2px solid #111; padding: 6px 10px; background: #fff; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.pb { page-break-before: always; break-before: page; }
.fullpage { page-break-inside: avoid; break-inside: avoid; }
.fullpage h2 { margin-top: 0; }
.fullfig { display: block; width: 100%; height: auto; max-height: 8.6in; border: 1px solid #595959; }
.wv { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.wv > div { min-width: 0; }
.wv h3 { margin: 0 0 2px; font-size: 11pt; }
.wv .fullfig { max-height: 4.1in; width: auto; max-width: 100%; }
.wvsum table { width: 100%; font-size: 9.5pt; }
.fullph { height: 8.0in; display: flex; flex-direction: column; justify-content: center; }
p.cap { font-size: 8.5pt; color: #333; margin: 4px 0 0; }
.note { font-size: 8.5pt; color: #333; }
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
    H.append('<section aria-labelledby="h-prop"><h2 id="h-prop">Property and data</h2><div>')
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
    mi = r.get("roof_model_info") if isinstance(r.get("roof_model_info"), dict) else None
    if mi:
        meta.append(("Roof model", f'{mi.get("label")} — {"ASSUMED" if mi.get("source") == "assumed" else mi.get("source")}: {mi.get("reason")}'))
    em = r.get("eave_rake_method")
    if em:
        EM = {"ridge_parallel_eave": "single dominant ridge — edges within 15° of the ridge bearing are eaves, the rest rakes",
              "ridges_per_wing": "per wing — each wing's geometry, constrained to every lidar ridge bearing",
              "wing_depth_heuristic": "per wing from the 2-D roofprint (no ridge bearing)", "all_eave": "all edges eave (hip/flat roof)"}
        rb = r.get("ridge_bearing_deg")
        meta.append(("Eave/rake method", EM.get(em, em) + (f" (ridge {num(rb, 1)}°)" if is_number(rb) and em == "ridge_parallel_eave" else "") + "; changeable in the app"))
    else:
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
             '</div><div class="kpis">'
             f'<div class="kpi"><b>{num(r["eave_lf"])} LF</b><span>Eaves (level)</span></div>'
             f'<div class="kpi"><b>{num(r["rake_lf"])} LF</b><span>Rakes, SLOPED (plan {num(r.get("rake_plan_lf")) if is_number(r.get("rake_plan_lf")) else "—"} LF)</span></div>'
             f'<div class="kpi"><b>{num(lines_lf(r, "ridge_lf")) if lines_lf(r, "ridge_lf") is not None else "—"} LF</b><span>Ridge</span></div>'
             f'<div class="kpi"><b>{num((lines_lf(r, "hip_lf") or 0) + (lines_lf(r, "valley_lf") or 0)) if r.get("lines") else "—"} LF</b><span>Hips + valleys (counted)</span></div>'
             '</div></section>')
    H.append(aerial[1])

    # edge list (0.1.7.3: replaces the small diagram; the full-page diagram is above)
    r["_diagram_source"] = "build_report.vector_page"
    H.append('<section class="pb" aria-labelledby="h-dg"><h2 id="h-dg">Edge list</h2>')
    H.append('<table><caption>Outline edges (text equivalent of the diagrams; numbers match the diagram). Rake lengths are SLOPED '
             '(drip-edge length = (plan span + 2 × overhang) × pitch factor' + (', per-facet lidar pitch' if r.get("per_facet_pitch_used") else '') + '); eaves are level.</caption><thead><tr>'
             '<th scope="col" class="n">Edge</th><th scope="col">Type</th><th scope="col" class="n">Plan length (ft)</th><th scope="col" class="n">Sloped length (ft)</th>'
             '<th scope="col" class="n">Bearing (°)</th><th scope="col">Classification</th></tr></thead><tbody>')
    for e in r["edges"]:
        auto = e.get("auto")
        cls = "auto (heuristic)" if auto is True else ("manual" if auto is False else "not stated")
        if e.get("length_source") == "user edit":
            cls += f'; length edited by user (auto {num(e.get("length_ft_auto"), 2)} ft plan)'
        t = str(e["type"]).lower()
        sl = e.get("sloped_length_ft")
        slc = (num(float(sl), 2) + (f' <span class="note">({esc(e.get("sloped_basis"))})</span>' if e.get("sloped_basis") else "")) if (t == "rake" and is_number(sl)) else ('level' if t == "eave" else "—")
        H.append(f'<tr><th scope="row" class="n">{esc(e["i"])}</th><td>{esc(str(e["type"]).title())}</td>'
                 f'<td class="n">{num(float(e["length_ft"]), 2)}</td><td class="n">{slc}</td>'
                 f'<td class="n">{num(e.get("bearing_deg"), 1) if is_number(e.get("bearing_deg")) else "—"}</td><td>{cls}</td></tr>')
    H.append('</tbody></table>')
    allsegs = [(i, sg) for i, sg in enumerate(r.get("line_segments") or []) if sg.get("source") == "lidar" or str(sg.get("auto_type") or sg.get("type")).lower() in ("ridge", "hip", "valley")]
    segs = [(i, sg) for i, sg in allsegs if not sg.get("unverified") and not sg.get("deleted")]
    n_app = len(allsegs) - len(segs)
    if segs or r.get("added_lines"):
        H.append('<table><caption>Counted interior lines (facets model + confident lidar lines; 3-D lengths)'
                 + (f' — {n_app} uncounted candidate/deleted line(s) are listed in the Appendix' if n_app else '') + '</caption><thead><tr><th scope="col">Line</th><th scope="col">Type</th>'
                 '<th scope="col" class="n">Length (ft)</th><th scope="col">Status</th></tr></thead><tbody>')
        for i, sg in segs:
            stt = "deleted by user (not counted)" if sg.get("deleted") else ("UNVERIFIED candidate (not counted)" if sg.get("unverified") else
                   ("user retag (auto " + str(sg.get("auto_type")) + ")" if sg.get("user_tagged") else "counted"))
            if sg.get("source") == "lidar":
                stt += f' — lidar: {sg.get("lidar_source")}, confidence {sg.get("lidar_conf")}' + (f', drop {num(sg.get("drop_ft"), 1)} ft' if is_number(sg.get("drop_ft")) else "")
            elif sg.get("lidar_retyped"):
                stt += f' — re-typed by lidar (model said {sg.get("auto_type")})'
            elif sg.get("lidar_confirmed"):
                stt += " — lidar-confirmed"
            H.append(f'<tr><th scope="row">L{i}</th><td>{esc(str(sg.get("type")).title() if not sg.get("deleted") else str(sg.get("auto_type") or "").title())}</td>'
                     f'<td class="n">{num(sg.get("length_ft"), 2)}</td><td>{esc(stt)}</td></tr>')
        for j, a in enumerate(r.get("added_lines") or []):
            H.append(f'<tr><th scope="row">U{j}</th><td>{esc(str(a.get("type")).title())}</td><td class="n">{num(a.get("length_ft"), 2)}</td>'
                     f'<td>user-entered{(" — " + esc(a.get("note"))) if a.get("note") else ""} (counted)</td></tr>')
        H.append('</tbody></table>')
    H.append('</section>')

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
    lc = r.get("line_candidates") if isinstance(r.get("line_candidates"), dict) else None
    if lc and lc.get("n"):
        H.append(f'<tr><th scope="row">Unverified hip/valley candidates</th><td class="n">{esc(lc.get("n"))}</td><td class="n">—</td>'
                 f'<td class="n"><span class="na">not counted</span></td><td>hip {num(lc.get("hip_lf"))} ft + valley {num(lc.get("valley_lf"))} ft from the ASSUMED roof model; confirm in the app to count them</td></tr>')
    H.append('</tbody></table>')
    if mats["extra_rows"]:
        H.append('<p>The primary Rake row is core\'s footprint-edge rake (plan LF and sloped LF). The extra rows come from the facets '
                 'roof model run with the lidar ridge (with wings it includes step-gable ends). Drip edge uses: ' + esc(mats["drip_edge_basis"]) + '.</p>')
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
    tot += feature_rows(r)
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
    dk = [d for d in (r.get("dormers") or []) if d.get("kept")]
    if dk:
        tl = sum(float(d.get("gutter_lf") or 0) for d in dk)
        H.append(f'<p><b>Dormer gutters: {len(dk)} dormer(s), ≈ {num(tl, 1)} LF</b> (not in the gutter totals above). Returns: '
                 + esc(", ".join(f'{d.get("key")} {d.get("returns")}' for d in dk))
                 + '. <b>Inspect and clean</b>: debris at dormer gutters and returns can let water in.</p>')
    H.append('</section>')

    H.append(lidar_seg_section(r))
    shtml, _lot = structures_section(r)
    H.append(shtml)
    H.append(solar_section(r))
    # notes, attribution, disclaimers
    H.append('<section aria-labelledby="h-notes"><h2 id="h-notes">Notes</h2>')
    H.append("<ul>" + "".join(f"<li>{esc(n)}</li>" for n in r["notes"]) + "</ul>" if r["notes"] else "<p>No notes in result.</p>")
    H.append('</section><section aria-labelledby="h-attr"><h2 id="h-attr">Data sources and attribution</h2><ul>' +
             "".join(f"<li>{esc(a)}</li>" for a in attributions(r, aerial[0])) + "</ul></section>")
    H.append('<section aria-labelledby="h-disc"><h2 id="h-disc" class="sr-only">Note</h2><p class="disclaimer"><b>For estimating; verify on site.</b></p></section>')
    H.append(appendix_section(r))
    H.append(f'<footer>RoofMeasure 0.1.7.6 report · {addr} · generated {esc(generated)} · RoofMeasure (MIT)</footer></main></body></html>')
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
    try:
        pages_html, kind = fullpage_sections(r)
    except Exception as ex:  # noqa  (0.1.7.3: a drawing error never drops the report; it is shown on the page)
        pages_html, kind = (f'<section class="fullpage pb"><h2>Aerial photo and diagrams</h2><div class="ph fullph" role="note">FIGURES NOT AVAILABLE<br>'
                            f'<span>{esc(type(ex).__name__)}: {esc(ex)}</span></div></section>'), "placeholder"
    aerial = (kind, pages_html)
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
