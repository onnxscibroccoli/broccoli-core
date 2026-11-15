/*!
 * structures.js v0.1.0 — RoofMeasure extras: every MassGIS structure on a tax lot.
 * UMD, no dependencies required for classify / overlap / lot totals.
 * Optional: pass opts.computeRoof or require('../core/roofcalc.js') in Node for measurements.
 *
 * Given a parcel point, lists ALL Building Structures footprints on the L3 tax lot,
 * classifies them by footprint area (shed < 200, garage 200–900, house > 900 sq ft),
 * and returns per-structure measurements plus a lot total.
 *
 * MassGIS Building Structures has no use/type attribute; class is an area heuristic.
 * Fail-closed: a failed parcel or building query returns status:"FAIL" and no invented structures.
 */
(function (root, factory) {
  if (typeof define === 'function' && define.amd) define([], factory);
  else if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.RoofStructures = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var VERSION = '0.1.0';
  var SHED_MAX_SQFT = 200;
  var GARAGE_MAX_SQFT = 900;
  var ON_LOT_MIN_OVERLAP = 0.50;
  var BUILDINGS_URL = 'https://services1.arcgis.com/hGdibHYSPO59RG1h/arcgis/rest/services/Building_Structures/FeatureServer/0/query';
  var PARCELS_URL = 'https://services1.arcgis.com/hGdibHYSPO59RG1h/arcgis/rest/services/Massachusetts_Property_Tax_Parcels/FeatureServer/0/query';
  var PARCEL_FIELDS = 'LOC_ID,MAP_PAR_ID,PROP_ID,SITE_ADDR,CITY,TOWN_ID,USE_CODE,STYLE,STORIES,YEAR_BUILT,RES_AREA,BLD_AREA,UNITS';
  var BUILDING_FIELDS = 'STRUCT_ID,SOURCE,SOURCEDATE,SOURCETYPE,AREA_SQ_FT,LOCAL_ID,TOWN_ID';
  var UA = 'roofmeasure-extras/0.1 (free public data; structures on parcel)';

  function r(x, d) {
    if (x == null || !isFinite(x)) return null;
    var m = Math.pow(10, d == null ? 1 : d);
    return Math.round(x * m) / m;
  }

  function classifyStructure(area) {
    if (area == null || !isFinite(area) || area < 0) return 'unknown';
    if (area < SHED_MAX_SQFT) return 'shed';
    if (area <= GARAGE_MAX_SQFT) return 'garage';
    return 'house';
  }

  function classificationRule() {
    return {
      shed: 'footprint_area_sqft < ' + SHED_MAX_SQFT,
      garage: SHED_MAX_SQFT + ' <= footprint_area_sqft <= ' + GARAGE_MAX_SQFT,
      house: 'footprint_area_sqft > ' + GARAGE_MAX_SQFT,
      on_lot_min_overlap: ON_LOT_MIN_OVERLAP,
      role: 'largest on-lot structure is primary; all others are accessory',
      caveat: 'MassGIS Building Structures (2-D) does not publish a building-use attribute. class is an area heuristic only. Verify on imagery.'
    };
  }

  function geomOf(obj) {
    if (!obj) throw new Error('missing geometry');
    if (obj.type === 'Feature') return obj.geometry;
    if (obj.geometry && obj.geometry.type) return obj.geometry;
    if (obj.type === 'Polygon' || obj.type === 'MultiPolygon') return obj;
    throw new Error('unrecognised geometry');
  }

  function outerRings(g) {
    g = geomOf(g);
    if (g.type === 'Polygon') return [g.coordinates[0]];
    if (g.type === 'MultiPolygon') return g.coordinates.map(function (p) { return p[0]; });
    throw new Error('unsupported ' + g.type);
  }

  function ringArea(ring) {
    var s = 0, n = ring.length;
    var closed = n > 1 && ring[0][0] === ring[n - 1][0] && ring[0][1] === ring[n - 1][1];
    var m = closed ? n - 1 : n;
    for (var i = 0; i < m; i++) {
      var a = ring[i], b = ring[(i + 1) % m];
      s += a[0] * b[1] - b[0] * a[1];
    }
    return s / 2;
  }

  function bboxOf(g) {
    var rings = outerRings(g), minx = Infinity, miny = Infinity, maxx = -Infinity, maxy = -Infinity;
    rings.forEach(function (ring) {
      ring.forEach(function (p) {
        if (p[0] < minx) minx = p[0];
        if (p[1] < miny) miny = p[1];
        if (p[0] > maxx) maxx = p[0];
        if (p[1] > maxy) maxy = p[1];
      });
    });
    return [minx, miny, maxx, maxy];
  }

  function centroidOf(g) {
    var ring = outerRings(g)[0];
    var a = ringArea(ring), cx = 0, cy = 0;
    var n = ring.length;
    var closed = n > 1 && ring[0][0] === ring[n - 1][0] && ring[0][1] === ring[n - 1][1];
    var m = closed ? n - 1 : n;
    if (Math.abs(a) < 1e-20) {
      var sx = 0, sy = 0;
      for (var i = 0; i < m; i++) { sx += ring[i][0]; sy += ring[i][1]; }
      return [sx / m, sy / m];
    }
    for (var j = 0; j < m; j++) {
      var p = ring[j], q = ring[(j + 1) % m], cross = p[0] * q[1] - q[0] * p[1];
      cx += (p[0] + q[0]) * cross;
      cy += (p[1] + q[1]) * cross;
    }
    return [cx / (6 * a), cy / (6 * a)];
  }

  // Sutherland–Hodgman clip of subject ring by a convex or concave clip ring (lon/lat).
  // For concave clip polygons we split via sequential half-planes of the clip edges
  // (correct for convex parcels; for concave parcels we fall back to a point-in-polygon
  // sample of the subject). Most MA tax parcels are simple convex or weakly concave.
  function isLeft(a, b, p) {
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);
  }
  function intersect(a, b, c, d) {
    var den = (a[0] - b[0]) * (c[1] - d[1]) - (a[1] - b[1]) * (c[0] - d[0]);
    if (Math.abs(den) < 1e-18) return a.slice();
    var t = ((a[0] - c[0]) * (c[1] - d[1]) - (a[1] - c[1]) * (c[0] - d[0])) / den;
    return [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
  }
  function closeRing(ring) {
    if (!ring.length) return ring;
    var a = ring[0], b = ring[ring.length - 1];
    if (a[0] === b[0] && a[1] === b[1]) return ring.slice();
    return ring.concat([a.slice()]);
  }
  function clipRings(subject, clip) {
    // Ensure clip is CCW (positive area) so "inside" is to the left of each edge.
    var clipR = clip.slice();
    if (clipR.length > 1 && clipR[0][0] === clipR[clipR.length - 1][0] && clipR[0][1] === clipR[clipR.length - 1][1]) clipR = clipR.slice(0, -1);
    if (ringArea(clipR) < 0) clipR = clipR.slice().reverse();
    var sub = subject.slice();
    if (sub.length > 1 && sub[0][0] === sub[sub.length - 1][0] && sub[0][1] === sub[sub.length - 1][1]) sub = sub.slice(0, -1);
    var output = sub;
    var cn = clipR.length;
    for (var i = 0; i < cn; i++) {
      var input = output;
      if (!input.length) return [];
      output = [];
      var a = clipR[i], b = clipR[(i + 1) % cn];
      for (var j = 0; j < input.length; j++) {
        var p = input[j], q = input[(j + 1) % input.length];
        var pIn = isLeft(a, b, p) >= -1e-15, qIn = isLeft(a, b, q) >= -1e-15;
        if (pIn && qIn) output.push(q);
        else if (pIn && !qIn) output.push(intersect(p, q, a, b));
        else if (!pIn && qIn) { output.push(intersect(p, q, a, b)); output.push(q); }
      }
    }
    return output;
  }

  function pointInRing(p, ring) {
    var n = ring.length;
    var closed = n > 1 && ring[0][0] === ring[n - 1][0] && ring[0][1] === ring[n - 1][1];
    var m = closed ? n - 1 : n, inside = false;
    for (var i = 0, j = m - 1; i < m; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      var denom = (yj - yi);
      if (((yi > p[1]) !== (yj > p[1])) && (p[0] < ((xj - xi) * (p[1] - yi) / (denom || 1e-20) + xi))) inside = !inside;
    }
    return inside;
  }

  // [android/bundle v0.1.8 fix] Exact intersection area of two simple polygons (either may be concave) by Green's theorem:
  // area(A∩B) = Σ shoelace over the parts of ∂A inside B + the parts of ∂B inside A (both CCW). Replaces the
  // Sutherland–Hodgman clip, which is only valid for convex clip polygons and returned 0 for a concave test parcel.
  function greenIntersectArea(A, B) {
    function open(r) { r = r.slice(); if (r.length > 1 && r[0][0] === r[r.length - 1][0] && r[0][1] === r[r.length - 1][1]) r.pop(); return r; }
    A = open(A); B = open(B);
    if (ringArea(A) < 0) A = A.slice().reverse();
    if (ringArea(B) < 0) B = B.slice().reverse();
    var ox = A[0][0], oy = A[0][1];
    var loc = function (r) { return r.map(function (p) { return [p[0] - ox, p[1] - oy]; }); };
    A = loc(A); B = loc(B);
    function part(P, Q) { // Σ over edges of P, the sub-segments inside Q
      var s = 0, n = P.length, m = Q.length;
      for (var i = 0; i < n; i++) {
        var a = P[i], b = P[(i + 1) % n], ts = [0, 1], dx = b[0] - a[0], dy = b[1] - a[1];
        for (var j = 0; j < m; j++) {
          var c = Q[j], d = Q[(j + 1) % m], ex = d[0] - c[0], ey = d[1] - c[1], den = dx * ey - dy * ex;
          if (Math.abs(den) < 1e-30) continue;
          var t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / den, u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / den;
          if (t > 0 && t < 1 && u >= 0 && u <= 1) ts.push(t);
        }
        ts.sort(function (x, y) { return x - y; });
        for (var k = 0; k + 1 < ts.length; k++) {
          var t0 = ts[k], t1 = ts[k + 1]; if (t1 - t0 < 1e-12) continue;
          var tm = (t0 + t1) / 2, mp = [a[0] + tm * dx, a[1] + tm * dy];
          if (!pointInRing(mp, Q)) continue;
          var p0 = [a[0] + t0 * dx, a[1] + t0 * dy], p1 = [a[0] + t1 * dx, a[1] + t1 * dy];
          s += p0[0] * p1[1] - p1[0] * p0[1];
        }
      }
      return s / 2;
    }
    return Math.max(0, part(A, B) + part(B, A));
  }

  function overlapFraction(building, parcel) {
    var bRings = outerRings(building);
    var pRings = outerRings(parcel);
    // Use the largest ring of each (ignore holes for the overlap test; parcels/buildings rarely have holes here).
    function largest(rings) {
      var best = rings[0], ba = Math.abs(ringArea(rings[0]));
      for (var i = 1; i < rings.length; i++) {
        var a = Math.abs(ringArea(rings[i]));
        if (a > ba) { best = rings[i]; ba = a; }
      }
      return best;
    }
    var b = largest(bRings), p = largest(pRings);
    var bA = Math.abs(ringArea(b));
    if (bA <= 0) return 0;
    var interA = greenIntersectArea(b, p); // android/bundle fix (concave parcels)
    // If the clip looks empty but the building centroid is inside the parcel, the parcel may be
    // concave and Hodgman failed; fall back to "centroid-in-parcel => 1, else 0" only as a last resort,
    // and never invent a partial fraction.
    if (interA < 1e-16) {
      var c = centroidOf({ type: 'Polygon', coordinates: [closeRing(b)] });
      return pointInRing(c, p) ? 1 : 0;
    }
    var frac = interA / bA;
    if (frac > 1.0001) frac = 1;
    return frac;
  }

  function onLot(building, parcel, minOverlap) {
    var frac = overlapFraction(building, parcel);
    return { ok: frac >= (minOverlap == null ? ON_LOT_MIN_OVERLAP : minOverlap), fraction: frac };
  }

  function parcelGetUrl(lat, lon) {
    var q = new URLSearchParams({
      geometry: lon + ',' + lat,
      geometryType: 'esriGeometryPoint',
      inSR: '4326',
      spatialRel: 'esriSpatialRelIntersects',
      outFields: PARCEL_FIELDS,
      outSR: '4326',
      f: 'geojson'
    });
    return PARCELS_URL + '?' + q.toString();
  }

  function buildingsEnvelopeUrl(xmin, ymin, xmax, ymax) {
    var q = new URLSearchParams({
      geometry: xmin + ',' + ymin + ',' + xmax + ',' + ymax,
      geometryType: 'esriGeometryEnvelope',
      inSR: '4326',
      spatialRel: 'esriSpatialRelIntersects',
      outFields: BUILDING_FIELDS,
      outSR: '4326',
      f: 'geojson'
    });
    return BUILDINGS_URL + '?' + q.toString();
  }

  function tryComputeRoof(feature, opts) {
    var fn = opts && opts.computeRoof;
    if (!fn && typeof require === 'function') {
      try { fn = require('../core/roofcalc.js').computeRoof; } catch (e) { fn = null; }
    }
    if (!fn) return null;
    try {
      var g = geomOf(feature);
      var c = centroidOf(g);
      return fn({
        geometry: g,
        lat: c[1],
        lon: c[0],
        pitch: (opts && opts.pitch) || '6/12',
        roofType: (opts && opts.roof_type) || 'gable',
        overhangFt: (opts && opts.overhang_ft) != null ? opts.overhang_ft : 1
      });
    } catch (e) {
      return { status: 'FAIL', error: String(e && e.message || e) };
    }
  }

  function listStructuresFromFeatures(parcel, features, opts) {
    opts = opts || {};
    var minOverlap = opts.min_overlap == null ? ON_LOT_MIN_OVERLAP : opts.min_overlap;
    var notes = (opts.notes || []).slice();
    var accepted = [], rejected = [];
    (features || []).forEach(function (f) {
      var props = f.properties || {};
      var rec = {
        struct_id: props.STRUCT_ID,
        source: props.SOURCE || props._source,
        sourcetype: props.SOURCETYPE,
        sourcedate: props.SOURCEDATE,
        massgis_area_sqft: props.AREA_SQ_FT != null ? r(+props.AREA_SQ_FT, 2) : null,
        footprint_geojson: { type: 'Feature', geometry: geomOf(f), properties: { STRUCT_ID: props.STRUCT_ID, AREA_SQ_FT: props.AREA_SQ_FT } }
      };
      try {
        var c = centroidOf(f);
        rec.centroid = { lat: r(c[1], 7), lon: r(c[0], 7) };
      } catch (e) { rec.centroid = null; }
      var ol;
      try { ol = onLot(f, parcel, minOverlap); }
      catch (e) {
        rec.reason = 'overlap test failed: ' + e.message;
        rejected.push(rec);
        return;
      }
      rec.overlap_fraction = r(ol.fraction, 3);
      rec.on_lot = ol.ok;
      if (!ol.ok) {
        rec.reason = 'overlap ' + rec.overlap_fraction + ' < ' + minOverlap;
        rejected.push(rec);
        return;
      }
      accepted.push(rec);
    });

    accepted.forEach(function (rec) {
      rec.measurements = tryComputeRoof(rec.footprint_geojson, opts);
      var computed = rec.measurements && rec.measurements.footprint_area_sqft;
      rec.computed_area_sqft = computed != null ? computed : null;
      var area = rec.massgis_area_sqft != null ? rec.massgis_area_sqft : rec.computed_area_sqft;
      rec.footprint_area_sqft = area != null ? r(area, 2) : null;
      rec.area_source = rec.massgis_area_sqft != null ? 'massgis_AREA_SQ_FT' : (rec.computed_area_sqft != null ? 'computed' : null);
      rec.class = classifyStructure(area);
    });
    accepted.sort(function (a, b) { return (b.footprint_area_sqft || 0) - (a.footprint_area_sqft || 0); });
    accepted.forEach(function (rec, i) {
      rec.role = (i === 0 && rec.footprint_area_sqft) ? 'primary' : 'accessory';
    });

    function sum(key, fromMeas) {
      var s = 0, n = 0;
      accepted.forEach(function (rec) {
        var v = fromMeas ? (rec.measurements && rec.measurements[key]) : rec[key];
        if (v == null) return;
        s += +v; n++;
      });
      return n ? r(s, 1) : null;
    }
    var counts = { house: 0, garage: 0, shed: 0, unknown: 0 };
    accepted.forEach(function (rec) { counts[rec.class] = (counts[rec.class] || 0) + 1; });
    var roof = sum('roof_area_sqft', true);
    var ds = 0, dsn = 0;
    accepted.forEach(function (rec) {
      var v = rec.measurements && rec.measurements.downspouts;
      if (v != null) { ds += +v; dsn++; }
    });
    var lotTotal = {
      n_structures: accepted.length,
      n_house: counts.house || 0,
      n_garage: counts.garage || 0,
      n_shed: counts.shed || 0,
      footprint_area_sqft: sum('footprint_area_sqft', false),
      roof_area_sqft: roof,
      squares: roof != null ? r(roof / 100, 2) : null,
      perimeter_ft: sum('perimeter_ft', true),
      eave_lf: sum('eave_lf', true),
      rake_lf: sum('rake_lf', true),
      gutter_lf: sum('gutter_lf', true),
      downspouts: dsn ? ds : null
    };
    var pp = (parcel && parcel.properties) || {};
    var status = parcel ? 'PASS' : 'FAIL';
    return {
      status: status,
      version: VERSION,
      module: 'extras/structures.js',
      query_point: (opts.lat != null && opts.lon != null) ? { lat: opts.lat, lon: opts.lon } : null,
      source: 'MassGIS Building Structures (2-D) + MassGIS L3 Property Tax Parcels',
      source_urls: {
        buildings_layer: BUILDINGS_URL.replace(/\/query$/, ''),
        parcels_layer: PARCELS_URL.replace(/\/query$/, '')
      },
      classification_rule: classificationRule(),
      defaults: {
        pitch: opts.pitch || '6/12',
        roof_type: opts.roof_type || 'gable',
        overhang_ft: opts.overhang_ft != null ? opts.overhang_ft : 1,
        note: 'pitch/roof_type are defaults unless the caller supplies measured values'
      },
      parcel: parcel ? {
        loc_id: pp.LOC_ID,
        site_addr: pp.SITE_ADDR,
        city: pp.CITY,
        town_id: pp.TOWN_ID,
        use_code: pp.USE_CODE,
        style: pp.STYLE,
        stories: pp.STORIES,
        year_built: pp.YEAR_BUILT,
        geometry: geomOf(parcel)
      } : null,
      structures: accepted,
      rejected_off_lot: rejected.map(function (rec) {
        var o = {};
        Object.keys(rec).forEach(function (k) { if (k !== 'footprint_geojson') o[k] = rec[k]; });
        return o;
      }),
      lot_total: lotTotal,
      requests: opts.requests || {},
      notes: notes
    };
  }

  async function listStructures(lat, lon, opts) {
    opts = Object.assign({ lat: lat, lon: lon }, opts || {});
    var requests = { parcel_get: parcelGetUrl(lat, lon) };
    opts.requests = requests;
    var headers = { 'User-Agent': UA };
    var parcelResp, parcelJson, parcel;
    try {
      parcelResp = await fetch(requests.parcel_get, { headers: headers });
      if (!parcelResp.ok) throw new Error('parcel HTTP ' + parcelResp.status);
      parcelJson = await parcelResp.json();
      parcel = (parcelJson.features || [])[0] || null;
    } catch (e) {
      return { status: 'FAIL', version: VERSION, query_point: { lat: lat, lon: lon },
        error: 'parcel query failed: ' + (e && e.message || e), requests: requests, structures: [], lot_total: null };
    }
    if (!parcel) {
      return { status: 'FAIL', version: VERSION, query_point: { lat: lat, lon: lon },
        error: 'No MassGIS L3 tax parcel intersected the point.', requests: requests, structures: [], lot_total: null };
    }
    var box = bboxOf(parcel);
    requests.buildings_envelope_get = buildingsEnvelopeUrl(box[0], box[1], box[2], box[3]);
    var bJson, features;
    try {
      var bResp = await fetch(requests.buildings_envelope_get, { headers: headers });
      if (!bResp.ok) throw new Error('buildings HTTP ' + bResp.status);
      bJson = await bResp.json();
      features = bJson.features || [];
    } catch (e) {
      return { status: 'FAIL', version: VERSION, query_point: { lat: lat, lon: lon },
        error: 'building query failed: ' + (e && e.message || e), requests: requests, structures: [], lot_total: null };
    }
    opts.notes = (opts.notes || []).concat([
      'buildings fetched by parcel envelope GET, then overlap-filtered (>= 50% of footprint inside the parcel).'
    ]);
    return listStructuresFromFeatures(parcel, features, opts);
  }

  return {
    VERSION: VERSION,
    SHED_MAX_SQFT: SHED_MAX_SQFT,
    GARAGE_MAX_SQFT: GARAGE_MAX_SQFT,
    ON_LOT_MIN_OVERLAP: ON_LOT_MIN_OVERLAP,
    classifyStructure: classifyStructure,
    classificationRule: classificationRule,
    overlapFraction: overlapFraction,
    onLot: onLot,
    parcelGetUrl: parcelGetUrl,
    buildingsEnvelopeUrl: buildingsEnvelopeUrl,
    listStructuresFromFeatures: listStructuresFromFeatures,
    listStructures: listStructures
  };
});
