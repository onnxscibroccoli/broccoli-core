"""Accessible black-and-white roof-plan SVG from a RoofMeasure result JSON.

Public API (stdlib only):
    render_roof_svg(result: dict, width=640, height=480) -> str
    svg_text_equivalent(result) -> str

Geometry is read from result['footprint_geojson'] (CONTRACT.md). Lon/lat is
projected to local feet with an equirectangular projection at the footprint
centroid. Missing optional fields degrade gracefully: the renderer also
accepts a raw GeoJSON Feature/FeatureCollection/Polygon or a QA fixture
that carries massgis_roofprint, so callers can wrap or pass those through.
"""

from __future__ import annotations

import hashlib
import math
import re
from xml.sax.saxutils import escape

# WGS84 equatorial radius. Equirectangular x uses R * cos(lat0).
_M_PER_FT = 0.3048006096012192  # 1 international foot in metres, inverse of 3.280839895013123
_R_FT = 6378137.0 / (0.3048)  # feet; 0.3048 m/ft (international)
# Use the exact reciprocal used elsewhere in RoofMeasure:
_FT_PER_M = 3.280839895013123
_R_FT = 6378137.0 * _FT_PER_M

EDGE_TYPES = ("eave", "rake", "ridge", "hip", "valley")

# Dash patterns AND a text label (never colour alone). Tuned to stay
# distinct after black-and-white printing / photocopying.
DASH = {
    "eave": None,  # solid
    "rake": "7 3.5",
    "ridge": "15 4",
    "hip": "10 3 2.5 3",
    "valley": "8 3 2 3 2 3",
    "unknown": "2.5 2.5",
}
STROKE_W = {
    "eave": 2.6,
    "rake": 2.2,
    "ridge": 2.5,
    "hip": 2.2,
    "valley": 2.2,
    "unknown": 2.0,
}

FG = "#000000"
BG = "#FFFFFF"
# #000 on #FFF is 21:1, well above the 4.5:1 requirement.
_MIN_CONTRAST = 4.5

# Approximate Arial advance width in ems, slightly conservative (wide).
_CHAR_EM = 0.58


# ---------------------------------------------------------------------------
# Colour / contrast
# ---------------------------------------------------------------------------

def _hex_to_rgb(color: str):
    c = color.strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in c):
        return None
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def _lin(channel: int) -> float:
    s = channel / 255.0
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    rgb = _hex_to_rgb(color)
    if rgb is None:
        return 0.0
    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    l1 = relative_luminance(fg)
    l2 = relative_luminance(bg)
    hi, lo = (l1, l2) if l1 >= l2 else (l2, l1)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _is_num_pair(p) -> bool:
    return (
        isinstance(p, (list, tuple))
        and len(p) >= 2
        and isinstance(p[0], (int, float))
        and isinstance(p[1], (int, float))
        and not isinstance(p[0], bool)
    )


def _as_xy(p):
    return (float(p[0]), float(p[1]))


def _close_ring(ring):
    if not ring:
        return []
    out = [_as_xy(p) for p in ring]
    if len(out) >= 2 and _dist(out[0], out[-1]) < 1e-12:
        return out
    return out + [out[0]]


def _open_ring(ring):
    pts = [_as_xy(p) for p in ring]
    if len(pts) >= 2 and _dist(pts[0], pts[-1]) < 1e-9:
        pts = pts[:-1]
    return pts


def _dist(a, b) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _looks_lonlat(pts) -> bool:
    if not pts:
        return False
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    if not all(abs(x) <= 180.0 and abs(y) <= 90.0 for x, y in zip(xs, ys)):
        return False
    # A house in feet spans tens of feet; a lon/lat roofprint spans << 0.05°.
    return (max(xs) - min(xs)) < 0.05 and (max(ys) - min(ys)) < 0.05


def _signed_area(ring) -> float:
    pts = _open_ring(ring)
    n = len(pts)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return 0.5 * s


def _centroid(ring):
    pts = _open_ring(ring)
    if not pts:
        return 0.0, 0.0
    a = _signed_area(pts)
    if abs(a) < 1e-18:
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    cx = cy = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    return cx / (6.0 * a), cy / (6.0 * a)


def _polygon_area(ring) -> float:
    return abs(_signed_area(ring))


def extract_rings(geom) -> list:
    """Return a list of exterior rings (each a list of [x, y] pairs).

    Accepts a GeoJSON geometry, Feature, FeatureCollection, a bare
    coordinates array, or a Feature-shaped dict with a geometry key.
    Interior holes are ignored for callouts (footprints in this project
    have none); MultiPolygon yields one ring per part, largest first.
    """
    if geom is None:
        return []
    if isinstance(geom, (list, tuple)):
        if not geom:
            return []
        if _is_num_pair(geom[0]):
            return [_close_ring(geom)]
        if isinstance(geom[0], (list, tuple)) and geom[0] and _is_num_pair(geom[0][0]):
            # Ring or list of rings (Polygon coordinates).
            return [_close_ring(geom[0])]
        if isinstance(geom[0], (list, tuple)) and geom[0] and isinstance(geom[0][0], (list, tuple)):
            # MultiPolygon coordinates or list of polygons.
            if geom[0][0] and _is_num_pair(geom[0][0][0]):
                rings = [_close_ring(poly[0]) for poly in geom if poly]
                rings.sort(key=_polygon_area, reverse=True)
                return rings
        return []
    if not isinstance(geom, dict):
        return []
    gtype = geom.get("type")
    if gtype == "FeatureCollection":
        rings = []
        for feat in geom.get("features") or []:
            rings.extend(extract_rings(feat))
        rings.sort(key=_polygon_area, reverse=True)
        return rings
    if gtype == "Feature" or ("geometry" in geom and gtype not in ("Polygon", "MultiPolygon", "LineString", "MultiLineString", "Point")):
        return extract_rings(geom.get("geometry"))
    if gtype == "Polygon":
        coords = geom.get("coordinates") or []
        if not coords:
            return []
        return [_close_ring(coords[0])]
    if gtype == "MultiPolygon":
        rings = [_close_ring(poly[0]) for poly in (geom.get("coordinates") or []) if poly]
        rings.sort(key=_polygon_area, reverse=True)
        return rings
    if gtype in ("LineString", "MultiLineString", "Point", "MultiPoint"):
        return []
    # Fall through: maybe a QA massgis_roofprint Feature without type, or
    # a dict that is itself the geometry.
    if "coordinates" in geom:
        return extract_rings({"type": geom.get("type") or "Polygon", "coordinates": geom["coordinates"]})
    if "geometry" in geom:
        return extract_rings(geom["geometry"])
    if "features" in geom:
        return extract_rings({"type": "FeatureCollection", "features": geom["features"]})
    return []


def _extract_linestrings(obj, default_type="unknown") -> list:
    """Pull typed line segments out of assorted optional schema locations."""
    segs = []

    def add(coords, typ=None, length=None, extra=None):
        if not coords or len(coords) < 2:
            return
        pts = [_as_xy(p) for p in coords]
        typ_n = _norm_type(typ if typ is not None else default_type)
        rec = {"type": typ_n, "coords": pts}
        if length is not None:
            rec["length_ft"] = float(length)
        if extra:
            rec.update(extra)
        segs.append(rec)

    def from_geojson_line(g, typ=None, length=None):
        if not g:
            return
        if isinstance(g, dict):
            t = g.get("type")
            if t == "Feature":
                props = g.get("properties") or {}
                from_geojson_line(
                    g.get("geometry"),
                    typ or props.get("type") or props.get("kind"),
                    length or props.get("length_ft"),
                )
                return
            if t == "FeatureCollection":
                for feat in g.get("features") or []:
                    from_geojson_line(feat, typ, length)
                return
            if t == "LineString":
                add(g.get("coordinates") or [], typ, length)
                return
            if t == "MultiLineString":
                for ls in g.get("coordinates") or []:
                    add(ls, typ, length)
                return
            if "coordinates" in g and t not in ("Polygon", "MultiPolygon", "Point"):
                add(g.get("coordinates") or [], typ, length)
                return
        if isinstance(g, (list, tuple)) and g and _is_num_pair(g[0]):
            add(g, typ, length)

    if obj is None:
        return segs
    if isinstance(obj, dict):
        if obj.get("type") in ("Feature", "FeatureCollection", "LineString", "MultiLineString"):
            from_geojson_line(obj)
            return segs
        typ = obj.get("type") or obj.get("kind") or default_type
        length = obj.get("length_ft")
        for key in ("coords_lonlat", "coords", "coordinates", "points"):
            if obj.get(key):
                from_geojson_line(obj[key], typ, length) if isinstance(obj[key], dict) else add(obj[key], typ, length)
                return segs
        if obj.get("coords_ft"):
            rec_coords = [_as_xy(p) for p in obj["coords_ft"]]
            rec = {"type": _norm_type(typ), "coords": rec_coords, "_units": "ft"}
            if length is not None:
                rec["length_ft"] = float(length)
            segs.append(rec)
            return segs
        if obj.get("from") is not None and obj.get("to") is not None:
            add([obj["from"], obj["to"]], typ, length)
            return segs
        if obj.get("geometry"):
            from_geojson_line(obj["geometry"], typ, length)
            return segs
        # Mapping of type -> lines (or type_lf length-only, which we skip).
        for typ in EDGE_TYPES:
            for key in (typ, typ + "s", typ + "_coords", typ + "_lines"):
                if key in obj and not key.endswith("_lf"):
                    segs.extend(_extract_linestrings(obj[key], default_type=typ))
        if "segments" in obj:
            segs.extend(_extract_linestrings(obj["segments"], default_type=default_type))
        if "line_segments" in obj:
            segs.extend(_extract_linestrings(obj["line_segments"], default_type=default_type))
        if "geometry" in obj and obj["geometry"] not in (None,):
            from_geojson_line(obj["geometry"], default_type)
        return segs
    if isinstance(obj, (list, tuple)):
        if obj and _is_num_pair(obj[0]):
            add(obj, default_type)
            return segs
        for item in obj:
            segs.extend(_extract_linestrings(item, default_type=default_type))
        return segs
    return segs


def _norm_type(t) -> str:
    if t is None:
        return "unknown"
    s = str(t).strip().lower()
    if s in EDGE_TYPES:
        return s
    # Tolerate plural / aliases.
    aliases = {"eaves": "eave", "rakes": "rake", "ridges": "ridge", "hips": "hip", "valleys": "valley"}
    return aliases.get(s, "unknown")


def _fmt_ft(value, digits=1) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ""
    if digits == 0:
        return str(int(round(v)))
    txt = f"{v:.{digits}f}"
    if "." in txt:
        txt = txt.rstrip("0").rstrip(".")
    return txt


def _fmt_length_label(value) -> str:
    txt = _fmt_ft(value, 2 if abs(float(value) - round(float(value), 1)) > 0.04 else 1)
    if not txt:
        return ""
    return f"{txt} ft"


# ---------------------------------------------------------------------------
# Result coercion + projection
# ---------------------------------------------------------------------------

def _first(*values):
    for v in values:
        if v is not None:
            return v
    return None


def coerce_result(result) -> dict:
    """Return a CONTRACT-shaped dict, filling footprint_geojson from common alts.

    Does not invent measurements. Optional fields stay missing when absent.
    """
    if not isinstance(result, dict):
        return {"footprint_geojson": None, "_notes": ["result was not a dict"]}

    # Already a result (or close).
    if result.get("footprint_geojson"):
        out = dict(result)
        return out

    if result.get("massgis_roofprint"):
        feat = result["massgis_roofprint"]
        props = (feat.get("properties") if isinstance(feat, dict) else None) or {}
        parcel = result.get("parcel") or {}
        parcel_props = parcel.get("properties") if isinstance(parcel, dict) else {}
        if not isinstance(parcel_props, dict):
            parcel_props = {}
        assessor = result.get("assessor")
        if not assessor and parcel_props:
            assessor = {
                "style": parcel_props.get("STYLE") or parcel_props.get("style"),
                "stories": parcel_props.get("STORIES") or parcel_props.get("stories"),
                "year_built": parcel_props.get("YEAR_BUILT") or parcel_props.get("year_built"),
            }
        return {
            "address": _first(result.get("matched_address"), result.get("input_address"), result.get("address")),
            "lat": _first(result.get("roof_point_lat"), result.get("census_lat"), result.get("lat")),
            "lon": _first(result.get("roof_point_lon"), result.get("census_lon"), result.get("lon")),
            "source": "MassGIS Building Structures (2-D) roofprint",
            "footprint_geojson": feat,
            "footprint_area_sqft": _first(props.get("AREA_SQ_FT"), result.get("qa_area_sqft_computed"), result.get("footprint_area_sqft")),
            "perimeter_ft": _first(result.get("qa_perimeter_ft_computed"), result.get("perimeter_ft")),
            "slug": result.get("slug"),
            "edges": result.get("edges"),
            "facets": result.get("facets"),
            "lines": result.get("lines"),
            "line_segments": result.get("line_segments"),
            "pitch": result.get("pitch"),
            "assessor": assessor,
            "notes": result.get("notes") or [],
        }

    gtype = result.get("type")
    if gtype in ("FeatureCollection", "Feature", "Polygon", "MultiPolygon") or result.get("features") or result.get("geometry") or result.get("coordinates"):
        feat = result
        props = {}
        if gtype == "FeatureCollection" and result.get("features"):
            feat0 = result["features"][0]
            props = (feat0.get("properties") if isinstance(feat0, dict) else None) or {}
        elif gtype == "Feature":
            props = result.get("properties") or {}
        address = _first(result.get("address"), props.get("address"), props.get("SITE_ADDR"))
        struct = props.get("STRUCT_ID")
        if not address and struct:
            address = f"MassGIS STRUCT_ID {struct}"
        return {
            "address": address,
            "lat": result.get("lat"),
            "lon": result.get("lon"),
            "source": result.get("source") or "GeoJSON footprint",
            "footprint_geojson": result,
            "footprint_area_sqft": _first(result.get("footprint_area_sqft"), props.get("AREA_SQ_FT")),
            "perimeter_ft": result.get("perimeter_ft"),
            "slug": result.get("slug") or (str(struct).replace(" ", "_") if struct else None),
            "edges": result.get("edges"),
            "facets": result.get("facets"),
            "lines": result.get("lines"),
            "line_segments": result.get("line_segments"),
            "pitch": result.get("pitch"),
            "assessor": result.get("assessor"),
            "notes": result.get("notes") or [],
        }

    out = dict(result)
    out.setdefault("footprint_geojson", None)
    return out


def _footprint_rings(result) -> list:
    return extract_rings(result.get("footprint_geojson"))


def project_lonlat_to_ft(lon, lat, lon0, lat0):
    """Equirectangular projection to local feet at (lon0, lat0). y is north."""
    # x = R * cos(lat0) * Δlon_rad ; y = R * Δlat_rad
    lat0_rad = math.radians(lat0)
    x = _R_FT * math.cos(lat0_rad) * math.radians(lon - lon0)
    y = _R_FT * math.radians(lat - lat0)
    return (x, y)


def _origin_from_rings(rings):
    pts = []
    for r in rings:
        pts.extend(_open_ring(r))
    if not pts:
        return 0.0, 0.0, False
    if _looks_lonlat(pts):
        # Geographic centroid of the primary (largest) ring, in lon/lat.
        lon0, lat0 = _centroid(rings[0])
        return lon0, lat0, True
    return 0.0, 0.0, False


def _project_point(p, lon0, lat0, geographic: bool):
    if geographic:
        return project_lonlat_to_ft(p[0], p[1], lon0, lat0)
    return (float(p[0]), float(p[1]))


def _project_ring(ring, lon0, lat0, geographic: bool):
    pts = [_project_point(p, lon0, lat0, geographic) for p in _open_ring(ring)]
    if pts:
        pts = pts + [pts[0]]
    return pts


def projected_footprint_area_sqft(result) -> float:
    """Plan area of the primary footprint ring in square feet, or 0."""
    r = coerce_result(result)
    rings = _footprint_rings(r)
    if not rings:
        return 0.0
    lon0, lat0, geo = _origin_from_rings(rings)
    pr = _project_ring(rings[0], lon0, lat0, geo)
    return _polygon_area(pr)


def _bearing_deg(a, b) -> float:
    """0 = north, 90 = east, in the local-feet frame (y north)."""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0


# ---------------------------------------------------------------------------
# Edges, facets, interior lines
# ---------------------------------------------------------------------------

def _collect_edges(result, ring_ft):
    """Return perimeter (and any typed) edges with coords in local feet."""
    raw = result.get("edges") or []
    lon0, lat0, geo = result.get("_proj", (0.0, 0.0, False))
    edges = []
    ring_open = _open_ring(ring_ft)
    n = len(ring_open)

    def proj_pair(a, b):
        return _project_point(_as_xy(a), lon0, lat0, geo), _project_point(_as_xy(b), lon0, lat0, geo)

    if isinstance(raw, list) and raw:
        for idx, e in enumerate(raw):
            if not isinstance(e, dict):
                continue
            typ = _norm_type(e.get("type"))
            a = b = None
            if e.get("from") is not None and e.get("to") is not None:
                a, b = proj_pair(e["from"], e["to"])
            elif n >= 3:
                i = e.get("i")
                if not isinstance(i, int) or i < 0 or i >= n:
                    i = idx if idx < n else None
                if i is not None:
                    a, b = ring_open[i], ring_open[(i + 1) % n]
            if a is None or b is None:
                continue
            length = e.get("length_ft")
            if length is None:
                length = _dist(a, b)
            bearing = e.get("bearing_deg")
            if bearing is None:
                bearing = _bearing_deg(a, b)
            edges.append({
                "i": e.get("i") if e.get("i") is not None else idx,
                "type": typ if typ != "unknown" or e.get("type") else (typ),
                "length_ft": float(length),
                "bearing_deg": float(bearing) if bearing is not None else None,
                "a": a,
                "b": b,
                "source": "edges",
            })
        # If the edges array didn't yield a usable perimeter, fall through.
        if edges:
            return edges

    # Synthesize from the projected ring.
    for i in range(n):
        a, b = ring_open[i], ring_open[(i + 1) % n]
        edges.append({
            "i": i,
            "type": "unknown",
            "length_ft": _dist(a, b),
            "bearing_deg": _bearing_deg(a, b),
            "a": a,
            "b": b,
            "source": "ring",
        })
    return edges


def _display_numbers(edges):
    """1-based numbers for the diagram / desc. Preserve given i if already 1-based."""
    idxs = [e["i"] for e in edges if isinstance(e.get("i"), int)]
    zero_based = bool(idxs) and min(idxs) == 0
    out = []
    for n, e in enumerate(edges, start=1):
        if isinstance(e.get("i"), int):
            out.append(e["i"] + 1 if zero_based else e["i"])
        else:
            out.append(n)
    return out


def _facet_ring_raw(facet):
    if not isinstance(facet, dict):
        return None, None  # ring, units
    for key in ("polygon_lonlat", "polygon", "geojson", "geometry"):
        if facet.get(key):
            rings = extract_rings(facet[key])
            if rings:
                units = "lonlat" if (key == "polygon_lonlat" or _looks_lonlat(_open_ring(rings[0]))) else None
                return rings[0], units
    if facet.get("coordinates") and not _is_num_pair(facet.get("coordinates")[0] if facet["coordinates"] else None):
        rings = extract_rings(facet)
        if rings:
            return rings[0], None
    if facet.get("polygon_ft"):
        return _close_ring(facet["polygon_ft"]), "ft"
    return None, None


def _collect_facets(result):
    lon0, lat0, geo = result.get("_proj", (0.0, 0.0, False))
    facets_out = []
    raw = result.get("facets") or []
    if not isinstance(raw, list):
        return facets_out
    for i, f in enumerate(raw):
        if not isinstance(f, dict):
            continue
        ring, units = _facet_ring_raw(f)
        ring_ft = None
        if ring is not None:
            use_geo = geo if units is None else (units == "lonlat")
            if units == "ft":
                ring_ft = _close_ring(ring)
            else:
                ring_ft = _project_ring(ring, lon0, lat0, use_geo)
        facets_out.append({
            "id": f.get("id", i),
            "area_sqft": f.get("area_sqft") if f.get("area_sqft") is not None else f.get("plan_area_sqft"),
            "pitch": f.get("pitch") or result.get("pitch"),
            "ring_ft": ring_ft,
            "raw": f,
        })
    return facets_out


def _collect_interior_lines(result):
    lon0, lat0, geo = result.get("_proj", (0.0, 0.0, False))
    segs = []
    segs.extend(_extract_linestrings(result.get("line_segments")))
    segs.extend(_extract_linestrings(result.get("lines")))
    # Facet-level optional line geometry
    for f in result.get("facets") or []:
        if not isinstance(f, dict):
            continue
        for typ in ("ridge", "hip", "valley"):
            if f.get(typ):
                segs.extend(_extract_linestrings(f.get(typ), default_type=typ))
        if f.get("lines"):
            segs.extend(_extract_linestrings(f.get("lines")))
    out = []
    for s in segs:
        typ = _norm_type(s.get("type"))
        if typ not in ("ridge", "hip", "valley"):
            # Perimeter eave/rake already come from edges; skip duplicates.
            continue
        coords = s.get("coords") or []
        if len(coords) < 2:
            continue
        if s.get("_units") == "ft":
            pts = coords
        else:
            use_geo = geo
            # If the first point looks like lon/lat, project; if feet, don't.
            if coords and _looks_lonlat(coords):
                use_geo = True
            elif coords and not _looks_lonlat(coords):
                use_geo = False
            pts = [_project_point(p, lon0, lat0, use_geo) for p in coords]
        length = s.get("length_ft")
        if length is None:
            length = sum(_dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
        out.append({"type": typ, "pts": pts, "length_ft": float(length)})
    return out


# ---------------------------------------------------------------------------
# SVG utilities
# ---------------------------------------------------------------------------

def _esc(s) -> str:
    return escape("" if s is None else str(s), {"\"": "&quot;", "'": "&apos;"})


def _text_width(text: str, size: float) -> float:
    # Average glyph width with a little padding for bold-ish strokes / halo.
    return max(4.0, len(text) * size * _CHAR_EM + 2.0)


def _id_prefix(result, width, height) -> str:
    slug = str(result.get("slug") or result.get("address") or "roof")
    key = f"{slug}|{width}x{height}|{result.get('footprint_area_sqft')}"
    return "rd-" + hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()[:10]


def _point_in_poly(x, y, ring) -> bool:
    pts = _open_ring(ring)
    n = len(pts)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-16) + xi):
            inside = not inside
        j = i
    return inside


def _seg_intersect(a, b, c, d) -> bool:
    def cross(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_box(p, q, r):
        return (min(p[0], q[0]) - 1e-9 <= r[0] <= max(p[0], q[0]) + 1e-9
                and min(p[1], q[1]) - 1e-9 <= r[1] <= max(p[1], q[1]) + 1e-9)

    d1 = cross(a, b, c)
    d2 = cross(a, b, d)
    d3 = cross(c, d, a)
    d4 = cross(c, d, b)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    if abs(d1) < 1e-12 and on_box(a, b, c):
        return True
    if abs(d2) < 1e-12 and on_box(a, b, d):
        return True
    if abs(d3) < 1e-12 and on_box(c, d, a):
        return True
    if abs(d4) < 1e-12 and on_box(c, d, b):
        return True
    return False


def _rects_overlap(a, b, pad=0.0) -> bool:
    return not (
        a[0] + a[2] + pad <= b[0]
        or b[0] + b[2] + pad <= a[0]
        or a[1] + a[3] + pad <= b[1]
        or b[1] + b[3] + pad <= a[1]
    )


def _box_hits_polygon(box, ring, pad=0.0) -> bool:
    x, y, w, h = box
    x -= pad
    y -= pad
    w += 2 * pad
    h += 2 * pad
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    mid = (x + w / 2.0, y + h / 2.0)
    for p in corners + [mid]:
        if _point_in_poly(p[0], p[1], ring):
            return True
    # Polygon vertices inside the box.
    for px, py in _open_ring(ring):
        if x <= px <= x + w and y <= py <= y + h:
            return True
    # Edges intersect.
    poly = _open_ring(ring)
    n = len(poly)
    b_edges = [((x, y), (x + w, y)), ((x + w, y), (x + w, y + h)),
               ((x + w, y + h), (x, y + h)), ((x, y + h), (x, y))]
    for i in range(n):
        a1, a2 = poly[i], poly[(i + 1) % n]
        for b1, b2 in b_edges:
            if _seg_intersect(a1, a2, b1, b2):
                return True
    return False


def _clamp_box(box, width, height, inset=3.0):
    x, y, w, h = box
    x = min(max(x, inset), max(inset, width - inset - w))
    y = min(max(y, inset), max(inset, height - inset - h))
    return [x, y, w, h]


def _nearest_on_box(px, py, box):
    x, y, w, h = box
    return min(max(px, x), x + w), min(max(py, y), y + h)


def _leader_points(mid, box, normal, clearance=10.0):
    """Midpoint -> outward clearance -> box edge. Avoids chords through the roof."""
    out = (mid[0] + normal[0] * clearance, mid[1] + normal[1] * clearance)
    # If the clearance point already sits in the box, a single segment is enough.
    x, y, w, h = box
    if x <= out[0] <= x + w and y <= out[1] <= y + h:
        ax, ay = _nearest_on_box(mid[0], mid[1], box)
        return [mid, (ax, ay)]
    ax, ay = _nearest_on_box(out[0], out[1], box)
    # Degenerate: box is essentially at `out`.
    if _dist(out, (ax, ay)) < 0.6:
        return [mid, (ax, ay)]
    return [mid, out, (ax, ay)]


def _path_enters_polygon(pts, ring) -> bool:
    """True if an open polyline dips into the interior of `ring`."""
    if len(pts) < 2:
        return False
    poly = _open_ring(ring)
    n = len(poly)
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        # Skip a short stump at the very first vertex (edge midpoint sits on the
        # boundary, where point-in-polygon is unstable).
        t0 = 0.18 if i == 0 else 0.0
        for t in (t0, 0.35, 0.5, 0.65, 0.85):
            if t <= 0:
                continue
            x = a[0] + (b[0] - a[0]) * t
            y = a[1] + (b[1] - a[1]) * t
            if _point_in_poly(x, y, ring):
                return True
        for j in range(n):
            if _seg_intersect(a, b, poly[j], poly[(j + 1) % n]):
                # Intersecting the parent edge at `mid` is expected; only count
                # intersections that are not at the first endpoint.
                # A proper crossing with a *different* edge means the leader cuts
                # a corner. Mid-on-edge intersection has the point on that edge.
                ix, iy = a
                on_a = min(poly[j][0], poly[(j + 1) % n][0]) - 1e-6 <= ix <= max(poly[j][0], poly[(j + 1) % n][0]) + 1e-6 and                        min(poly[j][1], poly[(j + 1) % n][1]) - 1e-6 <= iy <= max(poly[j][1], poly[(j + 1) % n][1]) + 1e-6
                if not (i == 0 and on_a and _point_segment_dist(a, poly[j], poly[(j + 1) % n]) < 1.2):
                    # If the intersection is essentially at `a` on the parent edge, ignore.
                    if _point_segment_dist(a, poly[j], poly[(j + 1) % n]) > 1.2 or i > 0:
                        return True
    return False


def _point_segment_dist(p, a, b) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    if L2 < 1e-18:
        return _dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return _dist(p, (a[0] + t * dx, a[1] + t * dy))


def _nice_scale(span_ft: float) -> float:
    if span_ft <= 0:
        return 10.0
    target = max(5.0, span_ft * 0.28)
    candidates = [5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 250, 500]
    return float(min(candidates, key=lambda c: abs(c - target)))


def _path_from_ring(ring, to_svg) -> str:
    pts = [to_svg(p[0], p[1]) for p in _open_ring(ring)]
    if not pts:
        return ""
    d = [f"M {pts[0][0]:.2f},{pts[0][1]:.2f}"]
    for x, y in pts[1:]:
        d.append(f"L {x:.2f},{y:.2f}")
    d.append("Z")
    return " ".join(d)


def _stroke_attrs(typ: str) -> str:
    dash = DASH.get(typ, DASH["unknown"])
    width = STROKE_W.get(typ, STROKE_W["unknown"])
    parts = [
        f'stroke="{FG}"',
        f'stroke-width="{width}"',
        'fill="none"',
        'stroke-linecap="butt"',
        'stroke-linejoin="miter"',
    ]
    if dash:
        parts.append(f'stroke-dasharray="{dash}"')
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public: text equivalent
# ---------------------------------------------------------------------------

def _edge_sentence(num, typ, length, bearing) -> str:
    bits = [f"Edge {num}"]
    if typ and typ != "unknown":
        bits.append(typ)
    if length is not None:
        bits.append(_fmt_length_label(length))
    if bearing is not None:
        bits.append(f"bearing {_fmt_ft(bearing, 1)}°")
    return ", ".join(bits[:1] + bits[1:]) + "."


def _describe(result, edges, numbers, facets, interior, area_sqft) -> str:
    addr = result.get("address") or result.get("slug") or "unspecified address"
    parts = [f"Roof plan of {addr}."]
    if area_sqft:
        parts.append(f"Footprint { _fmt_ft(area_sqft, 1) } sq ft.")
    elif result.get("footprint_area_sqft"):
        parts.append(f"Footprint { _fmt_ft(result['footprint_area_sqft'], 1) } sq ft.")
    if result.get("pitch"):
        parts.append(f"Pitch {result.get('pitch')}.")
    parts.append(f"{len(edges)} numbered edge{'s' if len(edges) != 1 else ''}.")
    for e, num in zip(edges, numbers):
        parts.append(_edge_sentence(num, e.get("type"), e.get("length_ft"), e.get("bearing_deg")))
    if interior:
        parts.append("Interior roof lines:")
        for i, seg in enumerate(interior, start=1):
            parts.append(
                f"{seg['type'].capitalize()} {i}: {_fmt_length_label(seg['length_ft'])}."
            )
    labeled = [f for f in facets if f.get("area_sqft") is not None or f.get("pitch") or f.get("ring_ft")]
    if labeled:
        parts.append("Facets:")
        for f in labeled:
            fid = f.get("id")
            bits = [f"Facet {fid}"]
            if f.get("area_sqft") is not None:
                bits.append(f"{_fmt_ft(f['area_sqft'], 1)} sq ft")
            if f.get("pitch"):
                bits.append(f"pitch {f['pitch']}")
            parts.append(", ".join(bits) + ".")
    return " ".join(parts)


def svg_text_equivalent(result) -> str:
    """HTML list equivalent of the roof diagram (for accessibility / no-SVG)."""
    r = coerce_result(result if isinstance(result, dict) else {})
    rings = _footprint_rings(r)
    lon0 = lat0 = 0.0
    geo = False
    area = 0.0
    ring_ft = []
    if rings:
        lon0, lat0, geo = _origin_from_rings(rings)
        r["_proj"] = (lon0, lat0, geo)
        ring_ft = _project_ring(rings[0], lon0, lat0, geo)
        area = _polygon_area(ring_ft)
    edges = _collect_edges(r, ring_ft) if ring_ft else []
    numbers = _display_numbers(edges) if edges else []
    facets = _collect_facets(r)
    interior = _collect_interior_lines(r) if ring_ft or True else []
    addr = _esc(r.get("address") or r.get("slug") or "unspecified address")
    items = []
    if not edges and not rings:
        items.append("<li>No footprint geometry was provided.</li>")
    for e, num in zip(edges, numbers):
        items.append(
            "<li>"
            + _esc(_edge_sentence(num, e.get("type"), e.get("length_ft"), e.get("bearing_deg")))
            + "</li>"
        )
    facet_items = []
    for f in facets:
        bits = [f"Facet {f.get('id')}"]
        if f.get("area_sqft") is not None:
            bits.append(f"{_fmt_ft(f['area_sqft'], 1)} sq ft")
        if f.get("pitch"):
            bits.append(f"pitch {f['pitch']}")
        facet_items.append("<li>" + _esc(", ".join(bits) + ".") + "</li>")
    line_items = []
    for i, seg in enumerate(interior, start=1):
        line_items.append(
            "<li>" + _esc(f"{seg['type'].capitalize()} {i}: {_fmt_length_label(seg['length_ft'])}.") + "</li>"
        )
    head = f"Roof plan of {addr}."
    if area:
        head += f" Footprint {_esc(_fmt_ft(area, 1))} sq ft."
    elif r.get("footprint_area_sqft"):
        head += f" Footprint {_esc(_fmt_ft(r['footprint_area_sqft'], 1))} sq ft."
    if r.get("pitch"):
        head += f" Pitch {_esc(r.get('pitch'))}."
    html = [
        '<div class="roof-diagram-text">',
        f"<p>{head}</p>",
        "<ol>",
        *items,
        "</ol>",
    ]
    if line_items:
        html += ['<p>Interior roof lines:</p>', "<ul class=\"roof-lines\">", *line_items, "</ul>"]
    if facet_items:
        html += ['<p>Facets:</p>', "<ul class=\"roof-facets\">", *facet_items, "</ul>"]
    html.append("</div>")
    return "".join(html)


# ---------------------------------------------------------------------------
# Public: SVG
# ---------------------------------------------------------------------------

def render_roof_svg(result: dict, width=640, height=480) -> str:
    """Return an inline SVG string of the roof plan.

    The SVG uses role='img' with <title> and <desc> (the desc lists every
    edge). Edge types are distinguished by dash pattern, a text label, and a
    legend — never by colour alone. The drawing is black on white (contrast
    21:1) so it prints in black and white.
    """
    try:
        width = int(width)
        height = int(height)
    except (TypeError, ValueError):
        width, height = 640, 480
    if width < 200:
        width = 200
    if height < 160:
        height = 160

    r = coerce_result(result if isinstance(result, dict) else {})
    prefix = _id_prefix(r, width, height)
    rings = _footprint_rings(r)
    title_addr = r.get("address") or r.get("slug") or "unspecified address"
    title = f"Roof diagram: {title_addr}"

    if not rings:
        desc = "No footprint geometry was provided."
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" '
            f'aria-labelledby="{prefix}-title {prefix}-desc">'
            f'<title id="{prefix}-title">{_esc(title)}</title>'
            f'<desc id="{prefix}-desc">{_esc(desc)}</desc>'
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}"/>'
            f'<text x="{width/2:.1f}" y="{height/2:.1f}" text-anchor="middle" '
            f'font-family="Arial, Helvetica, sans-serif" font-size="14" fill="{FG}">'
            f"No footprint geometry</text></svg>"
        )

    lon0, lat0, geo = _origin_from_rings(rings)
    r["_proj"] = (lon0, lat0, geo)
    rings_ft = [_project_ring(ring, lon0, lat0, geo) for ring in rings]
    primary = rings_ft[0]
    area = _polygon_area(primary)
    edges = _collect_edges(r, primary)
    numbers = _display_numbers(edges)
    facets = _collect_facets(r)
    interior = _collect_interior_lines(r)
    desc = _describe(r, edges, numbers, facets, interior, area)

    # Bounds in feet (y north) from footprint, facets, and interior lines.
    xs, ys = [], []
    for ring in rings_ft:
        for x, y in _open_ring(ring):
            xs.append(x)
            ys.append(y)
    for f in facets:
        if f.get("ring_ft"):
            for x, y in _open_ring(f["ring_ft"]):
                xs.append(x)
                ys.append(y)
    for seg in interior:
        for x, y in seg["pts"]:
            xs.append(x)
            ys.append(y)
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span_x = max(maxx - minx, 1e-6)
    span_y = max(maxy - miny, 1e-6)
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0

    # Reserved layout: generous margins for outside callouts, plus boxes
    # for the north arrow, scale bar, and legend.
    legend_w, legend_h = 118.0, 108.0
    north_w, north_h = 44.0, 64.0
    scale_h = 36.0
    margin_l = 78.0
    margin_r = 86.0
    margin_t = 52.0
    margin_b = 58.0
    plot_x = margin_l
    plot_y = margin_t
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    if plot_w < 80 or plot_h < 80:
        # Very small canvas: shrink chrome.
        margin_l = margin_r = 50.0
        margin_t = 40.0
        margin_b = 44.0
        plot_x, plot_y = margin_l, margin_t
        plot_w = width - margin_l - margin_r
        plot_h = height - margin_t - margin_b

    scale = min(plot_w / span_x, plot_h / span_y) * 0.88

    def to_svg(x, y):
        return (
            plot_x + plot_w / 2.0 + (x - cx) * scale,
            plot_y + plot_h / 2.0 - (y - cy) * scale,  # north is up
        )

    # Reserved chrome boxes (in SVG px).
    north_box = [width - 10.0 - north_w, 8.0, north_w, north_h]
    # Place legend in the corner farthest from the polygon centroid in SVG.
    pcx, pcy = to_svg(cx, cy)
    if pcx < width / 2.0:
        legend_x = width - 8.0 - legend_w
    else:
        legend_x = 8.0
    if pcy < height / 2.0:
        legend_y = height - 8.0 - legend_h - 4.0
        # Keep off the scale bar (bottom centre/right).
        if legend_x > width / 2.0:
            legend_y = height - scale_h - 12.0 - legend_h
    else:
        legend_y = 8.0
        if legend_y < north_box[1] + north_box[3] and legend_x > width / 2.0:
            legend_y = north_box[1] + north_box[3] + 6.0
    legend_box = [legend_x, legend_y, legend_w, legend_h]
    scale_len_ft = _nice_scale(max(span_x, span_y))
    scale_px = scale_len_ft * scale
    scale_w = max(scale_px + 16.0, 70.0)
    # Bottom edge, opposite the legend when possible.
    if legend_x < width / 2.0:
        scale_x = width - 12.0 - scale_w
    else:
        scale_x = 12.0
    scale_box = [scale_x, height - 8.0 - scale_h, scale_w, scale_h]
    reserved = [north_box, legend_box, scale_box]

    primary_svg = [to_svg(p[0], p[1]) for p in _open_ring(primary)]
    # Outward normals in SVG space.
    # In feet (y north), CCW => outward is (dy, -dx). After y-flip, rotate carefully.
    area_ft = _signed_area(primary)  # +CCW in math (y north)
    # We'll compute outward in feet then transform the normal.

    def outward_normal_svg(a_ft, b_ft):
        dx, dy = b_ft[0] - a_ft[0], b_ft[1] - a_ft[1]
        L = math.hypot(dx, dy) or 1.0
        # Outward in feet: for CCW (+area) outward is (dy, -dx); for CW, opposite.
        if area_ft >= 0:
            nx, ny = dy / L, -dx / L
        else:
            nx, ny = -dy / L, dx / L
        # SVG: (x, -y) so the normal becomes (nx, -ny).
        sx, sy = nx, -ny
        sl = math.hypot(sx, sy) or 1.0
        return (sx / sl, sy / sl)

    # ----- callout placement -----
    callouts = []
    # Place shortest edges first (their midpoints cluster near corners).
    order = sorted(range(len(edges)), key=lambda i: edges[i]["length_ft"])
    placed_boxes = []

    def label_lines(e, num):
        typ = e.get("type") or "unknown"
        typ_txt = typ if typ != "unknown" else "edge"
        line1 = f"{num})  {_fmt_length_label(e['length_ft'])}"
        line2 = typ_txt
        return line1, line2

    font_size = 10.0
    line_gap = 12.0
    pad_x, pad_y = 3.5, 3.0

    for idx in order:
        e = edges[idx]
        num = numbers[idx]
        line1, line2 = label_lines(e, num)
        mid_ft = ((e["a"][0] + e["b"][0]) / 2.0, (e["a"][1] + e["b"][1]) / 2.0)
        mid = to_svg(*mid_ft)
        normal = outward_normal_svg(e["a"], e["b"])
        # Tangent (along edge) in SVG, for sliding.
        tdx, tdy = e["b"][0] - e["a"][0], e["b"][1] - e["a"][1]
        # SVG tangent is (tdx, -tdy)
        tx, ty = tdx, -tdy
        tl = math.hypot(tx, ty) or 1.0
        tx, ty = tx / tl, ty / tl
        tw = max(_text_width(line1, font_size), _text_width(line2, font_size - 0.5))
        box_w = tw + 2 * pad_x
        box_h = line_gap + font_size * 0.35 + 2 * pad_y
        def _try_box(box, off, steer=None):
            box = _clamp_box(box, width, height, inset=3.0)
            if _box_hits_polygon(box, primary_svg, pad=2.0):
                return None
            for other in placed_boxes + reserved:
                if _rects_overlap(box, other, pad=2.0):
                    return None
            steer_n = steer or normal
            clearance = min(max(off * 0.45, 8.0), 14.0)
            # Prefer a clean straight/dogleg leader. Try the steering
            # direction first (out of a notch mouth), then the edge normal.
            for nvec in (steer_n, normal):
                lpts = _leader_points(mid, box, nvec, clearance=clearance)
                if not _path_enters_polygon(lpts, primary_svg):
                    return (box, off, lpts)
            return None

        found = None
        # 1) Outward normal + along-edge slides (usual case).
        offsets = [16, 20, 24, 28, 34, 40, 48, 56, 66, 78, 92]
        slides = [0, 8, -8, 16, -16, 24, -24, 32, -32, 42, -42]
        for off in offsets:
            for sl in slides:
                cxb = mid[0] + normal[0] * off + tx * sl
                cyb = mid[1] + normal[1] * off + ty * sl
                got = _try_box([cxb - box_w / 2.0, cyb - box_h / 2.0, box_w, box_h], off)
                if got:
                    found = got
                    break
            if found:
                break
        # 2) Polar sweep. Needed when the outward normal points into a
        # narrow notch: the label has to escape through the mouth.
        if not found:
            base = math.atan2(normal[1], normal[0])
            angles = [base]
            for k in range(1, 13):  # ±15° ... ±180°
                angles.append(base + math.radians(k * 15))
                angles.append(base - math.radians(k * 15))
            for off in offsets + [100, 120]:
                for ang in angles:
                    cang, sang = math.cos(ang), math.sin(ang)
                    cxb = mid[0] + cang * off
                    cyb = mid[1] + sang * off
                    got = _try_box(
                        [cxb - box_w / 2.0, cyb - box_h / 2.0, box_w, box_h],
                        off,
                        steer=(cang, sang),
                    )
                    if got:
                        found = got
                        break
                if found:
                    break
        if not found:
            # Last resort: pick the polar candidate that stays on-canvas and
            # is least inside the polygon (still may be imperfect).
            best = None
            best_score = 1e18
            base = math.atan2(normal[1], normal[0])
            for off in (40, 56, 72, 92, 110):
                for k in range(0, 24):
                    ang = base + k * (2.0 * math.pi / 24)
                    cang, sang = math.cos(ang), math.sin(ang)
                    cxb = mid[0] + cang * off
                    cyb = mid[1] + sang * off
                    box = _clamp_box([cxb - box_w / 2.0, cyb - box_h / 2.0, box_w, box_h], width, height, 3.0)
                    score = 0.0
                    if _box_hits_polygon(box, primary_svg, pad=0.0):
                        score += 50.0
                    for other in placed_boxes + reserved:
                        if _rects_overlap(box, other, pad=0.0):
                            score += 20.0
                    lpts = _leader_points(mid, box, (cang, sang), 10.0)
                    if _path_enters_polygon(lpts, primary_svg):
                        score += 40.0
                    score += off * 0.1
                    if score < best_score:
                        best_score = score
                        best = (box, off, lpts)
            found = best or (
                _clamp_box([mid[0] + normal[0] * 40 - box_w / 2.0, mid[1] + normal[1] * 40 - box_h / 2.0, box_w, box_h], width, height, 3.0),
                40,
                _leader_points(mid, [0, 0, 0, 0], normal, 10.0),
            )
        box = found[0]
        lpts = found[2]
        placed_boxes.append(box)
        callouts.append({
            "idx": idx,
            "num": num,
            "edge": e,
            "mid": mid,
            "box": box,
            "line1": line1,
            "line2": line2,
            "type": e.get("type") or "unknown",
            "normal": normal,
            "leader": lpts,
        })
    callouts.sort(key=lambda c: c["idx"])

    # ----- assemble SVG -----
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="{prefix}-title {prefix}-desc">',
        f'<title id="{prefix}-title">{_esc(title)}</title>',
        f'<desc id="{prefix}-desc">{_esc(desc)}</desc>',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}"/>',
        "<defs>",
        # Halo filter alternative: we stroke text in white instead (more reliable in print).
    ]

    # Hatch patterns — angle/spacing only, all black. One per facet with a ring.
    hatch_ids = []
    angles = (0, 45, 90, 135, 22.5, 67.5, 112.5, 157.5)
    spacings = (6, 7, 8, 6.5, 7.5, 8.5, 5.5, 9)
    fi = 0
    for f in facets:
        if not f.get("ring_ft"):
            hatch_ids.append(None)
            continue
        pid = f"{prefix}-hatch-{fi}"
        ang = angles[fi % len(angles)]
        sp = spacings[fi % len(spacings)]
        # A horizontal rule rotated by `ang`. Pattern tile is large enough.
        tile = 24
        parts.append(
            f'<pattern id="{pid}" patternUnits="userSpaceOnUse" width="{tile}" height="{sp}" '
            f'patternTransform="rotate({ang:.1f})">'
            f'<line x1="0" y1="0" x2="{tile}" y2="0" stroke="{FG}" stroke-width="0.9"/>'
            f"</pattern>"
        )
        hatch_ids.append(pid)
        fi += 1
    parts.append("</defs>")

    # Footprint fill (white) so hatches sit on a clean ground.
    for ring in rings_ft:
        d = _path_from_ring(ring, to_svg)
        if d:
            parts.append(
                f'<path class="footprint-fill" d="{d}" fill="{BG}" stroke="none"/>'
            )

    # Pre-place facet labels (priority over interior-line labels).
    facet_labels = []  # dicts: id, x, y, text, box
    occupied = list(placed_boxes) + list(reserved)
    for f, hid in zip(facets, hatch_ids):
        ring = f.get("ring_ft")
        if not ring:
            continue
        fcx, fcy = _centroid(ring)
        sx, sy = to_svg(fcx, fcy)
        ring_svg = [to_svg(p[0], p[1]) for p in _open_ring(ring)]
        xs = [p[0] for p in ring_svg]
        ys = [p[1] for p in ring_svg]
        facet_w = max(xs) - min(xs) if xs else 0
        full_bits = [str(f.get("id"))]
        if f.get("area_sqft") is not None:
            full_bits.append(f"{_fmt_ft(f['area_sqft'], 1)} sq ft")
        if f.get("pitch"):
            full_bits.append(str(f["pitch"]))
        short_bits = [str(f.get("id"))]
        if f.get("area_sqft") is not None:
            short_bits.append(f"{_fmt_ft(f['area_sqft'], 0)}")
        candidates = [" · ".join(full_bits), " · ".join(short_bits), str(f.get("id"))]
        chosen = None
        for label in candidates:
            tw = _text_width(label, 9)
            if tw + 4 > max(facet_w, 8) and label != candidates[-1]:
                continue
            fbox = [sx - tw / 2.0 - 2, sy - 7, tw + 4, 14]
            # Prefer labels whose centre is inside the facet.
            if not _point_in_poly(sx, sy, ring_svg):
                continue
            if any(_rects_overlap(fbox, other, pad=1.0) for other in occupied):
                continue
            chosen = (label, fbox)
            break
        if chosen is None:
            # Last try: just the id, even if tight.
            label = str(f.get("id"))
            tw = _text_width(label, 8.5)
            fbox = [sx - tw / 2.0 - 1, sy - 6, tw + 2, 12]
            chosen = (label, fbox)
        facet_labels.append({"id": f.get("id"), "x": sx, "y": sy, "text": chosen[0], "box": chosen[1], "hid": hid, "ring": ring})
        occupied.append(chosen[1])

    # Pre-place interior line labels (drop a label if it will not fit).
    interior_drawn = []
    for i, seg in enumerate(interior):
        pts = [to_svg(p[0], p[1]) for p in seg["pts"]]
        typ = seg["type"]
        if len(pts) >= 2:
            a, b = pts[(len(pts) - 1) // 2], pts[len(pts) // 2]
            mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            dx, dy = b[0] - a[0], b[1] - a[1]
        else:
            mid = pts[0] if pts else (0, 0)
            dx, dy = 1, 0
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L  # perpendicular in SVG
        lab_full = f"{typ} {_fmt_length_label(seg['length_ft'])}"
        lab_short = typ
        placed_lab = None
        # Prefer longer segments; short stubs often have no room.
        plan_px = sum(_dist(pts[j], pts[j + 1]) for j in range(len(pts) - 1)) if len(pts) >= 2 else 0
        labels_to_try = [lab_full, lab_short] if plan_px >= 18 else [lab_short, lab_full]
        for lab in labels_to_try:
            tw = _text_width(lab, 8)
            bh, bw = 11.0, tw + 3
            for sign in (1, -1):
                for off in (8, 12, 16, 20, 6, 24):
                    lx = mid[0] + px * sign * off
                    ly = mid[1] + py * sign * off
                    fbox = [lx - bw / 2.0, ly - bh / 2.0, bw, bh]
                    if fbox[0] < 2 or fbox[1] < 2 or fbox[0] + fbox[2] > width - 2 or fbox[1] + fbox[3] > height - 2:
                        continue
                    if any(_rects_overlap(fbox, other, pad=1.5) for other in occupied):
                        continue
                    placed_lab = {"text": lab, "x": lx, "y": ly, "box": fbox, "type": typ}
                    break
                if placed_lab:
                    break
            if placed_lab:
                break
        if placed_lab:
            occupied.append(placed_lab["box"])
        interior_drawn.append({"seg": seg, "pts": pts, "type": typ, "label": placed_lab})

    # Facet hatches + labels.
    for fl, hid in zip(facet_labels, [f["hid"] for f in facet_labels]):
        if not hid:
            # Should not happen (we skipped ring-less facets).
            pass
        d = _path_from_ring(fl["ring"], to_svg)
        fid = _esc(fl["id"])
        if hid and d:
            parts.append(
                f'<path class="facet" data-facet-id="{fid}" d="{d}" '
                f'fill="url(#{hid})" stroke="{FG}" stroke-width="0.6" fill-opacity="1"/>'
            )
        sx, sy, label = fl["x"], fl["y"], fl["text"]
        parts.append(
            f'<g class="facet-label" data-facet-id="{fid}">'
            f'<text x="{sx:.2f}" y="{sy:.2f}" text-anchor="middle" dominant-baseline="middle" '
            f'font-family="Arial, Helvetica, sans-serif" font-size="9" '
            f'stroke="{BG}" stroke-width="3" paint-order="stroke" fill="{BG}" '
            f'stroke-linejoin="round">{_esc(label)}</text>'
            f'<text x="{sx:.2f}" y="{sy:.2f}" text-anchor="middle" dominant-baseline="middle" '
            f'font-family="Arial, Helvetica, sans-serif" font-size="9" fill="{FG}">'
            f"{_esc(label)}</text></g>"
        )
    # Facets that had a ring/hatch but were somehow dropped from facet_labels:
    # already included, because we iterated the same zip of facets with rings.

    # Interior ridge / hip / valley (lines always; labels when they fit).
    for item in interior_drawn:
        pts = item["pts"]
        typ = item["type"]
        d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        parts.append(
            f'<path class="roof-line" data-type="{typ}" d="{d}" {_stroke_attrs(typ)}/>'
        )
        lab = item["label"]
        if not lab:
            continue
        parts.append(
            f'<text class="roof-line-label" data-type="{typ}" x="{lab["x"]:.2f}" y="{lab["y"]:.2f}" '
            f'text-anchor="middle" dominant-baseline="middle" '
            f'font-family="Arial, Helvetica, sans-serif" font-size="8" '
            f'stroke="{BG}" stroke-width="3" paint-order="stroke" fill="{FG}" '
            f'stroke-linejoin="round">{_esc(lab["text"])}</text>'
        )

    # Perimeter edges (numbered). Draw on top of facets / interior lines.
    for e, num in zip(edges, numbers):
        ax, ay = to_svg(*e["a"])
        bx, by = to_svg(*e["b"])
        typ = e.get("type") or "unknown"
        parts.append(
            f'<line class="edge-stroke" data-type="{_esc(typ)}" data-index="{num}" '
            f'x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" {_stroke_attrs(typ)}/>'
        )

    # Callouts: leader + numbered length + type label, outside the polygon.
    for c in callouts:
        box = c["box"]
        mx, my = c["mid"]
        cxb = box[0] + box[2] / 2.0
        cyb = box[1] + box[3] / 2.0
        lpts = c.get("leader") or _leader_points(c["mid"], box, c.get("normal") or (0, -1), 10.0)
        if len(lpts) >= 2:
            dlead = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in lpts)
            leader_el = f'<path d="{dlead}" fill="none" stroke="{FG}" stroke-width="0.7"/>'
        else:
            leader_el = ""
        parts.append(
            f'<g class="edge-callout" data-index="{c["num"]}" data-type="{_esc(c["type"])}" '
            f'data-bbox="{box[0]:.2f},{box[1]:.2f},{box[2]:.2f},{box[3]:.2f}">'
            f"{leader_el}"
            f'<rect x="{box[0]:.2f}" y="{box[1]:.2f}" width="{box[2]:.2f}" height="{box[3]:.2f}" '
            f'fill="{BG}" stroke="none"/>'
            f'<text font-family="Arial, Helvetica, sans-serif" fill="{FG}" text-anchor="middle">'
            f'<tspan x="{cxb:.2f}" y="{box[1] + pad_y + font_size - 1:.2f}" font-size="{font_size:.1f}" '
            f'font-weight="700">{_esc(c["line1"])}</tspan>'
            f'<tspan x="{cxb:.2f}" y="{box[1] + pad_y + font_size - 1 + line_gap:.2f}" '
            f'font-size="{font_size - 0.5:.1f}">{_esc(c["line2"])}</tspan>'
            f"</text></g>"
        )

    # North arrow (points up = north in this projection).
    ncx = north_box[0] + north_box[2] / 2.0
    ntop = north_box[1] + 16.0
    nbot = north_box[1] + north_box[3] - 6.0
    parts.append(
        f'<g class="north-arrow" aria-hidden="true">'
        f'<polygon points="{ncx:.1f},{ntop:.1f} {ncx - 7:.1f},{ntop + 16:.1f} {ncx:.1f},{ntop + 12:.1f} '
        f'{ncx + 7:.1f},{ntop + 16:.1f}" fill="{FG}"/>'
        f'<line x1="{ncx:.1f}" y1="{ntop + 12:.1f}" x2="{ncx:.1f}" y2="{nbot:.1f}" '
        f'stroke="{FG}" stroke-width="2"/>'
        f'<text x="{ncx:.1f}" y="{ntop - 3:.1f}" text-anchor="middle" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="12" font-weight="700" fill="{FG}">N</text>'
        f"</g>"
    )

    # Scale bar in feet (alternating black/white rectangles, outlined).
    bar_x = scale_box[0] + 8.0
    bar_y = scale_box[1] + 8.0
    bar_h = 8.0
    nseg = 2 if scale_len_ft >= 10 else 1
    seg_ft = scale_len_ft / nseg
    parts.append('<g class="scale-bar">')
    for i in range(nseg):
        sx0 = bar_x + i * (scale_px / nseg)
        fill = FG if i % 2 == 0 else BG
        parts.append(
            f'<rect x="{sx0:.2f}" y="{bar_y:.2f}" width="{scale_px / nseg:.2f}" height="{bar_h}" '
            f'fill="{fill}" stroke="{FG}" stroke-width="1"/>'
        )
    parts.append(
        f'<text x="{bar_x:.2f}" y="{bar_y + bar_h + 12:.2f}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="10" fill="{FG}">0</text>'
        f'<text x="{bar_x + scale_px:.2f}" y="{bar_y + bar_h + 12:.2f}" text-anchor="end" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="10" fill="{FG}">'
        f"{_esc(_fmt_ft(scale_len_ft, 0))} ft</text>"
        f'<text x="{bar_x + scale_px / 2.0:.2f}" y="{bar_y - 3:.2f}" text-anchor="middle" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="9" fill="{FG}">Scale</text>'
        "</g>"
    )

    # Legend: every standard type, dash + text label (never colour alone).
    parts.append('<g class="legend">')
    parts.append(
        f'<rect x="{legend_box[0]:.2f}" y="{legend_box[1]:.2f}" width="{legend_box[2]:.2f}" '
        f'height="{legend_box[3]:.2f}" fill="{BG}" stroke="{FG}" stroke-width="1"/>'
        f'<text x="{legend_box[0] + 8:.2f}" y="{legend_box[1] + 14:.2f}" '
        f'font-family="Arial, Helvetica, sans-serif" font-size="10" font-weight="700" fill="{FG}">'
        f"Edge types</text>"
    )
    row_y = legend_box[1] + 28
    for typ in EDGE_TYPES:
        x1 = legend_box[0] + 8
        x2 = legend_box[0] + 40
        midy = row_y - 3
        parts.append(
            f'<line class="legend-swatch" data-type="{typ}" x1="{x1:.2f}" y1="{midy:.2f}" '
            f'x2="{x2:.2f}" y2="{midy:.2f}" {_stroke_attrs(typ)}/>'
            f'<text x="{x2 + 6:.2f}" y="{row_y:.2f}" '
            f'font-family="Arial, Helvetica, sans-serif" font-size="10" fill="{FG}">'
            f"{typ}</text>"
        )
        row_y += 16
    parts.append("</g>")

    parts.append("</svg>")
    return "".join(parts)
