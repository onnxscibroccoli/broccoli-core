/*!
 * roofcalc.js v1.3.1 — shared geometry core for RoofMeasure (free residential roof & gutter estimator)
 * UMD: works as <script> (window.RoofCalc), CommonJS require(), and AMD. No dependencies.
 * Coordinates are [lon, lat] (GeoJSON order) in WGS84 degrees. Lengths in feet, areas in sq ft.
 *
 * STABLE PUBLIC API (v1): see README.md "core API". Do not rename; additions only.
 */
(function (root, factory) {
  if (typeof define === 'function' && define.amd) define([], factory);
  else if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.RoofCalc = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var VERSION = '1.3.2';
  var M_TO_FT = 3.280839895013123;
  var WGS84_A = 6378137.0, WGS84_F = 1 / 298.257223563, WGS84_B = WGS84_A * (1 - WGS84_F);
  var WGS84_E2 = WGS84_F * (2 - WGS84_F);
  var D2R = Math.PI / 180, R2D = 180 / Math.PI;

  var DEFAULTS = {
    pitch: '6/12',
    roofType: 'gable',        // 'gable' | 'hip' | 'flat'
    overhangFt: 1,            // overhang for wall-line footprints (OSM/Overture/manual). MassGIS roofprints default 0 (ruling #4)
    gutterEndExtFt: 1,        // gutter extension per eave end for wall-line footprints; defaults to the resolved overhang
    ftPerDownspout: 35,
    minDownspoutsPerRun: 1,   // lead ruling 22:36: per run max(1, ceil(run_lf/35))
    minRunFt: 0,              // eave runs shorter than this get no downspout (0 = every run gets >= 1)
    shortRunFt: 0,            // legacy (v1.0): runs with gutter < this get 1 downspout; 0 disables
    ridgeTolDeg: 15,          // with ridgeBearingDeg: edges within ±tol of parallel to ridge = eave
    simplifyFt: 0.3,          // drop near-collinear vertices closer than this to the chord
    wastePct: 10
  };

  var PITCHES = ['0/12', '1/12', '2/12', '3/12', '4/12', '5/12', '6/12', '7/12', '8/12', '9/12',
    '10/12', '11/12', '12/12', '14/12', '16/12', '18/12'];

  // ---------------------------------------------------------------- geodesy
  function haversineFt(a, b) {
    var R = 6371008.8;
    var p1 = a[1] * D2R, p2 = b[1] * D2R, dp = p2 - p1, dl = (b[0] - a[0]) * D2R;
    var h = Math.sin(dp / 2) * Math.sin(dp / 2) + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2);
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h))) * M_TO_FT;
  }

  /** Vincenty inverse on WGS84. Returns feet. Falls back to haversine if it fails to converge. */
  function geodesicDistanceFt(a, b) {
    if (a[0] === b[0] && a[1] === b[1]) return 0;
    var L = (b[0] - a[0]) * D2R;
    var U1 = Math.atan((1 - WGS84_F) * Math.tan(a[1] * D2R));
    var U2 = Math.atan((1 - WGS84_F) * Math.tan(b[1] * D2R));
    var sinU1 = Math.sin(U1), cosU1 = Math.cos(U1), sinU2 = Math.sin(U2), cosU2 = Math.cos(U2);
    var lambda = L, lambdaP, iter = 100, sinSigma, cosSigma, sigma, cosSqAlpha, cos2SigmaM;
    do {
      var sinL = Math.sin(lambda), cosL = Math.cos(lambda);
      sinSigma = Math.sqrt((cosU2 * sinL) * (cosU2 * sinL) +
        (cosU1 * sinU2 - sinU1 * cosU2 * cosL) * (cosU1 * sinU2 - sinU1 * cosU2 * cosL));
      if (sinSigma === 0) return 0;
      cosSigma = sinU1 * sinU2 + cosU1 * cosU2 * cosL;
      sigma = Math.atan2(sinSigma, cosSigma);
      var sinAlpha = cosU1 * cosU2 * sinL / sinSigma;
      cosSqAlpha = 1 - sinAlpha * sinAlpha;
      cos2SigmaM = cosSqAlpha !== 0 ? cosSigma - 2 * sinU1 * sinU2 / cosSqAlpha : 0;
      var C = WGS84_F / 16 * cosSqAlpha * (4 + WGS84_F * (4 - 3 * cosSqAlpha));
      lambdaP = lambda;
      lambda = L + (1 - C) * WGS84_F * sinAlpha *
        (sigma + C * sinSigma * (cos2SigmaM + C * cosSigma * (-1 + 2 * cos2SigmaM * cos2SigmaM)));
    } while (Math.abs(lambda - lambdaP) > 1e-12 && --iter > 0);
    if (iter === 0) return haversineFt(a, b);
    var uSq = cosSqAlpha * (WGS84_A * WGS84_A - WGS84_B * WGS84_B) / (WGS84_B * WGS84_B);
    var A = 1 + uSq / 16384 * (4096 + uSq * (-768 + uSq * (320 - 175 * uSq)));
    var B = uSq / 1024 * (256 + uSq * (-128 + uSq * (74 - 47 * uSq)));
    var dS = B * sinSigma * (cos2SigmaM + B / 4 * (cosSigma * (-1 + 2 * cos2SigmaM * cos2SigmaM) -
      B / 6 * cos2SigmaM * (-3 + 4 * sinSigma * sinSigma) * (-3 + 4 * cos2SigmaM * cos2SigmaM)));
    return WGS84_B * A * (sigma - dS) * M_TO_FT;
  }

  /** Initial bearing a->b, degrees clockwise from true north, 0..360. */
  function bearingDeg(a, b) {
    var p1 = a[1] * D2R, p2 = b[1] * D2R, dl = (b[0] - a[0]) * D2R;
    var y = Math.sin(dl) * Math.cos(p2);
    var x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl);
    return (Math.atan2(y, x) * R2D + 360) % 360;
  }

  // ------------------------------------------------- local tangent plane (ft)
  /** Build a local ENU-ish projection (feet) centred at lat0/lon0 using WGS84 radii of curvature. */
  function localFrame(lon0, lat0) {
    var s = Math.sin(lat0 * D2R), w = Math.sqrt(1 - WGS84_E2 * s * s);
    var N = WGS84_A / w, M = WGS84_A * (1 - WGS84_E2) / (w * w * w);
    var kx = N * Math.cos(lat0 * D2R) * D2R * M_TO_FT, ky = M * D2R * M_TO_FT;
    return {
      lon0: lon0, lat0: lat0,
      toXY: function (p) { return [(p[0] - lon0) * kx, (p[1] - lat0) * ky]; },
      toLL: function (q) { return [lon0 + q[0] / kx, lat0 + q[1] / ky]; }
    };
  }

  function ringCentroidLL(ring) {
    var sx = 0, sy = 0, n = ring.length;
    for (var i = 0; i < n; i++) { sx += ring[i][0]; sy += ring[i][1]; }
    return [sx / n, sy / n];
  }

  function signedAreaXY(pts) {
    var s = 0;
    for (var i = 0, n = pts.length; i < n; i++) {
      var a = pts[i], b = pts[(i + 1) % n];
      s += a[0] * b[1] - b[0] * a[1];
    }
    return s / 2;
  }

  // ------------------------------------------------------- ring handling
  /** Accepts a GeoJSON Feature/Polygon/MultiPolygon/ring; returns the outer ring (largest polygon). */
  function extractRing(input) {
    if (!input) throw new Error('no geometry');
    if (input.type === 'FeatureCollection') return extractRing(input.features[0]);
    if (input.type === 'Feature') return extractRing(input.geometry);
    if (input.type === 'Polygon') return input.coordinates[0];
    if (input.type === 'MultiPolygon') {
      var best = null, bestA = -1;
      input.coordinates.forEach(function (poly) {
        var r = poly[0], f = localFrame(r[0][0], r[0][1]);
        var a = Math.abs(signedAreaXY(r.map(f.toXY)));
        if (a > bestA) { bestA = a; best = r; }
      });
      return best;
    }
    if (Array.isArray(input) && Array.isArray(input[0]) && typeof input[0][0] === 'number') return input;
    if (Array.isArray(input) && Array.isArray(input[0]) && Array.isArray(input[0][0])) return input[0];
    throw new Error('unsupported geometry');
  }

  /**
   * Normalise a ring: open (no repeated closing vertex), no duplicate vertices, near-collinear
   * vertices removed (tolerance simplifyFt), counter-clockwise orientation.
   */
  function normalizeRing(ringIn, simplifyFt) {
    var tol = simplifyFt == null ? DEFAULTS.simplifyFt : simplifyFt;
    var ring = ringIn.map(function (p) { return [+p[0], +p[1]]; });
    if (ring.length > 1) {
      var f0 = ring[0], fl = ring[ring.length - 1];
      if (f0[0] === fl[0] && f0[1] === fl[1]) ring.pop();
    }
    var c = ringCentroidLL(ring), fr = localFrame(c[0], c[1]);
    var xy = ring.map(fr.toXY), keep = ring.slice(), kxy = xy.slice();
    // drop duplicates (< 0.05 ft)
    var outLL = [], outXY = [];
    for (var i = 0; i < keep.length; i++) {
      var prev = outXY[outXY.length - 1];
      if (prev && Math.hypot(kxy[i][0] - prev[0], kxy[i][1] - prev[1]) < 0.05) continue;
      outLL.push(keep[i]); outXY.push(kxy[i]);
    }
    if (outXY.length > 1 && Math.hypot(outXY[0][0] - outXY[outXY.length - 1][0], outXY[0][1] - outXY[outXY.length - 1][1]) < 0.05) {
      outLL.pop(); outXY.pop();
    }
    // remove near-collinear vertices iteratively
    var changed = tol > 0;
    while (changed && outXY.length > 3) {
      changed = false;
      for (var j = 0; j < outXY.length && outXY.length > 3; j++) {
        var a = outXY[(j - 1 + outXY.length) % outXY.length], b = outXY[j], d = outXY[(j + 1) % outXY.length];
        var len = Math.hypot(d[0] - a[0], d[1] - a[1]);
        var dist = len > 0 ? Math.abs((d[0] - a[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (d[1] - a[1])) / len : 0;
        // only collinear if b lies between a and d (not a spike)
        var dot = (b[0] - a[0]) * (d[0] - b[0]) + (b[1] - a[1]) * (d[1] - b[1]);
        if (dist < tol && dot > 0) { outXY.splice(j, 1); outLL.splice(j, 1); changed = true; j--; }
      }
    }
    if (outLL.length < 3) throw new Error('degenerate ring');
    if (signedAreaXY(outXY) < 0) outLL.reverse();
    return outLL;
  }

  function closeRing(ring) {
    var r = ring.slice();
    var a = r[0], b = r[r.length - 1];
    if (a[0] !== b[0] || a[1] !== b[1]) r.push([a[0], a[1]]);
    return r;
  }

  function toGeoJSON(ring, props) {
    return { type: 'Feature', properties: props || {}, geometry: { type: 'Polygon', coordinates: [closeRing(ring)] } };
  }

  // ----------------------------------------------------------- measures
  function edgeList(ring) {
    var out = [], n = ring.length;
    for (var i = 0; i < n; i++) {
      var a = ring[i], b = ring[(i + 1) % n];
      out.push({ i: i, from: a, to: b, length_ft: geodesicDistanceFt(a, b), bearing_deg: bearingDeg(a, b) });
    }
    return out;
  }

  function perimeterFt(ring) {
    return edgeList(ring).reduce(function (s, e) { return s + e.length_ft; }, 0);
  }

  /** Planar area in a local WGS84 tangent frame (accurate to <0.01% at house scale). */
  function areaSqft(ringIn) {
    var ring = extractRing(ringIn);
    var c = ringCentroidLL(ring), f = localFrame(c[0], c[1]);
    var r = ring.slice();
    if (r.length > 1 && r[0][0] === r[r.length - 1][0] && r[0][1] === r[r.length - 1][1]) r.pop();
    return Math.abs(signedAreaXY(r.map(f.toXY)));
  }

  // ------------------------------------------------------------ pitch
  /** Parse '6/12', '6', 6, or '26.57deg' -> rise per 12 run. */
  function parsePitch(p) {
    if (typeof p === 'number') return p;
    var s = String(p).trim().toLowerCase();
    var m = s.match(/^([\d.]+)\s*(?:\/|:|in)\s*([\d.]+)$/);
    if (m) return parseFloat(m[1]) * 12 / parseFloat(m[2]);
    m = s.match(/^([\d.]+)\s*(?:deg|°)$/);
    if (m) return Math.tan(parseFloat(m[1]) * D2R) * 12;
    if (/^[\d.]+$/.test(s)) return parseFloat(s);
    throw new Error('bad pitch: ' + p);
  }
  /** Slope multiplier: sloped length / horizontal length = sqrt(1 + (rise/12)^2). */
  function pitchFactor(p) { var r = parsePitch(p) / 12; return Math.sqrt(1 + r * r); }
  /** Hip/valley multiplier (plan length -> true length for a 45° plan hip): sqrt(2 + (rise/12)^2)/sqrt(2). */
  function hipValleyFactor(p) { var r = parsePitch(p) / 12; return Math.sqrt(2 + r * r) / Math.SQRT2; }
  function pitchDegrees(p) { return Math.atan(parsePitch(p) / 12) * R2D; }

  // ------------------------------------------------------ polygon offset
  /** Outward mitre offset of a CCW ring by d feet. Returns ring in lon/lat. */
  function offsetRing(ringIn, d) {
    var ring = normalizeRing(ringIn, 0);
    if (!d) return ring;
    var c = ringCentroidLL(ring), f = localFrame(c[0], c[1]);
    var P = ring.map(f.toXY), n = P.length, out = [];
    function lineOff(i) {
      var a = P[i], b = P[(i + 1) % n], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
      var nx = dy / L, ny = -dx / L; // outward normal for CCW
      return { p: [a[0] + nx * d, a[1] + ny * d], v: [dx / L, dy / L], n: [nx, ny] };
    }
    for (var i = 0; i < n; i++) {
      var l1 = lineOff((i - 1 + n) % n), l2 = lineOff(i);
      var den = l1.v[0] * l2.v[1] - l1.v[1] * l2.v[0];
      if (Math.abs(den) < 1e-6) { out.push([P[i][0] + l2.n[0] * d, P[i][1] + l2.n[1] * d]); continue; }
      var t = ((l2.p[0] - l1.p[0]) * l2.v[1] - (l2.p[1] - l1.p[1]) * l2.v[0]) / den;
      var q = [l1.p[0] + l1.v[0] * t, l1.p[1] + l1.v[1] * t];
      // cap extreme mitres on very sharp corners
      var mx = q[0] - P[i][0], my = q[1] - P[i][1], ml = Math.hypot(mx, my);
      if (ml > 4 * Math.abs(d)) { q = [P[i][0] + mx / ml * 4 * Math.abs(d), P[i][1] + my / ml * 4 * Math.abs(d)]; }
      out.push(q);
    }
    return out.map(f.toLL);
  }

  // ------------------------------------------------ eave / rake heuristic
  function raySegHit(o, dir, a, b) {
    var ex = b[0] - a[0], ey = b[1] - a[1];
    var den = dir[0] * ey - dir[1] * ex;
    if (Math.abs(den) < 1e-12) return null;
    var wx = a[0] - o[0], wy = a[1] - o[1];
    var t = (wx * ey - wy * ex) / den, u = (wx * dir[1] - wy * dir[0]) / den;
    return (t > 1e-6 && u >= -1e-9 && u <= 1 + 1e-9) ? t : null;
  }
  function rayDist(P, o, dir) {
    var best = Infinity;
    for (var i = 0, n = P.length; i < n; i++) {
      var t = raySegHit(o, dir, P[i], P[(i + 1) % n]);
      if (t != null && t < best) best = t;
    }
    return best;
  }

  /**
   * Auto-suggest eave/rake per edge from a 2-D roofprint (HEURISTIC).
   * gable: for each edge, measure the building depth D perpendicular to it (inward ray) and the
   *   wing length W parallel to it a few feet inside. If W >= D the local ridge runs parallel to
   *   the edge -> eave, else the edge is a gable end -> rake. Rectangles: long sides eave, short
   *   sides rake. L/T shapes: each wing handled locally.
   * hip / flat: every edge is an eave.
   * ridges (v1.2): opts.ridgeBearingsDeg [b1,b2,..] (or lidar ridges[] objects with bearing_deg). 2+ ridges ->
   *   per-wing heuristic AND parallel to some ridge = eave. Exactly 1 -> same as ridgeBearingDeg.
   * ridge: opts.ridgeBearingDeg (gable only) -> edges within ±opts.ridgeTolDeg (15°) of parallel to the
   *   ridge are eaves, others rakes. Hip/flat ignore it.
   * Returns array of 'eave'|'rake' aligned with ring edges (ring must be normalized/CCW).
   */
  /** Normalise opts.ridgeBearingsDeg (numbers or {bearing_deg}) -> finite numbers; [] if absent. */
  function ridgeList(co) {
    var a = co && co.ridgeBearingsDeg;
    if (!Array.isArray(a)) return [];
    return a.map(function (r) { return r && typeof r === 'object' ? Number(r.bearing_deg) : Number(r); })
      .filter(function (x) { return isFinite(x); });
  }
  function axisDiffDeg(a, b) { var d = Math.abs(((a - b) % 180 + 180) % 180); return Math.min(d, 180 - d); }

  function classifyEdges(ringIn, roofType, opts) {
    var ring = ringIn, type = roofType || DEFAULTS.roofType, co = opts || {};
    var n = ring.length;
    if (type === 'hip' || type === 'flat') { var all = []; for (var k = 0; k < n; k++) all.push('eave'); return all; }
    var ridges = ridgeList(co);
    if (ridges.length >= 2) {
      // multiple ridges (L/T/cross-gable from lidar): per-wing geometry decides, but an edge must also be
      // parallel (±tol) to one of the ridges to be an eave; edges parallel to no ridge are rakes.
      var tol2 = co.ridgeTolDeg == null ? DEFAULTS.ridgeTolDeg : co.ridgeTolDeg;
      var geo = classifyEdges(ring, 'gable');
      return edgeList(ring).map(function (e, i) {
        var par = ridges.some(function (rb) { return axisDiffDeg(e.bearing_deg, rb) <= tol2; });
        return par && geo[i] === 'eave' ? 'eave' : 'rake';
      });
    }
    if (ridges.length === 1) co = Object.assign({}, co, { ridgeBearingDeg: ridges[0] });
    if (co.ridgeBearingDeg != null && co.ridgeBearingDeg !== '' && isFinite(Number(co.ridgeBearingDeg))) {
      var rb = Number(co.ridgeBearingDeg), tol = co.ridgeTolDeg == null ? DEFAULTS.ridgeTolDeg : co.ridgeTolDeg;
      return edgeList(ring).map(function (e) { return axisDiffDeg(e.bearing_deg, rb) <= tol ? 'eave' : 'rake'; });
    }
    var c = ringCentroidLL(ring), f = localFrame(c[0], c[1]);
    var P = ring.map(f.toXY);
    if (signedAreaXY(P) < 0) throw new Error('ring must be CCW; call normalizeRing first');
    var res = [], metrics = [];
    for (var i = 0; i < n; i++) {
      var a = P[i], b = P[(i + 1) % n], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy);
      if (L < 1e-6) { res.push('rake'); metrics.push(null); continue; }
      var u = [dx / L, dy / L], inN = [-u[1], u[0]]; // inward normal for CCW
      var samples = [0.25, 0.5, 0.75], Ds = [], Ws = [];
      samples.forEach(function (s) {
        var m = [a[0] + dx * s, a[1] + dy * s];
        var o = [m[0] + inN[0] * 1e-3, m[1] + inN[1] * 1e-3];
        var D = rayDist(P, o, inN);
        if (!isFinite(D)) return;
        var depth = Math.min(D / 2, Math.max(2, Math.min(6, D / 4)));
        var q = [m[0] + inN[0] * depth, m[1] + inN[1] * depth];
        var W = rayDist(P, q, u) + rayDist(P, q, [-u[0], -u[1]]);
        Ds.push(D); Ws.push(W);
      });
      if (!Ds.length) { res.push('rake'); metrics.push(null); continue; }
      Ds.sort(function (x, y) { return x - y; }); Ws.sort(function (x, y) { return x - y; });
      var Dm = Ds[Math.floor(Ds.length / 2)], Wm = Ws[Math.floor(Ws.length / 2)];
      metrics.push({ depth: Dm, width: Wm });
      res.push(Wm >= Dm * 0.98 ? 'eave' : 'rake');
    }
    return res;
  }

  // ------------------------------------------------ gutters / downspouts
  /** Contiguous runs of eave edges (cyclic). Returns [{edges:[i..], length_ft}] */
  function eaveRuns(edges, types) {
    var n = edges.length, runs = [];
    if (types.every(function (t) { return t === 'eave'; })) {
      return [{ edges: edges.map(function (e) { return e.i; }), length_ft: edges.reduce(function (s, e) { return s + e.length_ft; }, 0), closed: true }];
    }
    var start = types.indexOf('rake');
    var cur = null;
    for (var k = 1; k <= n; k++) {
      var i = (start + k) % n;
      if (types[i] === 'eave') {
        if (!cur) { cur = { edges: [], length_ft: 0, closed: false }; runs.push(cur); }
        cur.edges.push(i); cur.length_ft += edges[i].length_ft;
      } else cur = null;
    }
    return runs;
  }

  /** Gutter LF = sum over continuous eave runs of (run length + 2*ext); closed all-eave loop gets no ext (ruling #13).
   *  Downspouts per contiguous eave run (lead ruling):
   *  max(minDownspoutsPerRun=1, ceil(run_lf / ftPerDownspout=35)), run_lf = plan eave length of the run; summed. */
  function gutterEstimate(edges, types, opts) {
    var o = Object.assign({}, DEFAULTS, opts || {});
    var eaveLf = 0, gutterLf = 0;
    edges.forEach(function (e, i) { if (types[i] === 'eave') eaveLf += e.length_ft; });
    var runs = eaveRuns(edges, types), ds = 0;
    runs.forEach(function (r) {
      // ruling #13: extension at the two ends of each continuous run only; a closed (wrap-around) run has no ends
      r.end_ext_ft = r.closed ? 0 : 2 * o.gutterEndExtFt;
      r.gutter_ft = r.length_ft + r.end_ext_ft;
      gutterLf += r.gutter_ft;
      r.downspouts = r.length_ft < o.minRunFt ? 0 : (r.gutter_ft < o.shortRunFt ? 1 : Math.max(o.minDownspoutsPerRun, Math.ceil(r.length_ft / o.ftPerDownspout)));
      ds += r.downspouts;
    });
    return { eave_lf: eaveLf, gutter_lf: gutterLf, downspouts: ds, runs: runs };
  }

  // ------------------------------------------------------ overhang by source
  /**
   * Ruling #4: MassGIS Building_Structures polygons are ROOFPRINTS (drip line, eaves included) -> 0 ft.
   * OSM / Overture / manual wall traces -> 1 ft. User value always wins.
   * Returns {overhangFt, overhangSource, gutterEndExtFt, gutterExtSource, footprintKind}.
   */
  function resolveOverhang(o) {
    o = o || {};
    var st = String(o.sourceType || '').toUpperCase(), src = String(o.source || '').toLowerCase();
    var roofprint = st === 'ROOFPRINT' || st === 'ROOFPRINT_SHIFTED' || (!st && /massgis/.test(src));
    var kind = roofprint ? 'roofprint' : (/osm|openstreetmap|overpass/.test(src) ? 'osm' : (/overture/.test(src) ? 'overture' : (st === 'FEMA_USA_STRUCTURES' || /usa structures|fema/.test(src) ? 'fema_usa_structures' : 'manual')));
    var userOh = o.overhangFt != null && o.overhangFt !== '' && isFinite(Number(o.overhangFt));
    var oh = userOh ? Number(o.overhangFt) : (roofprint ? 0 : DEFAULTS.overhangFt);
    var userExt = o.gutterEndExtFt != null && o.gutterEndExtFt !== '' && isFinite(Number(o.gutterEndExtFt));
    return {
      overhangFt: oh,
      overhangSource: userOh ? 'user' : (roofprint ? 'default:massgis_roofprint_includes_eaves' : 'default:' + kind + '_wall_footprint'),
      gutterEndExtFt: userExt ? Number(o.gutterEndExtFt) : oh,
      gutterExtSource: userExt ? 'user' : 'default:equals_overhang',
      footprintKind: kind
    };
  }

  /** Translate a ring so its centroid moves fromLL -> toLL, preserving every edge length (rigid move in a
   *  local tangent frame; ruling #5 drag-to-align). */
  function translateRing(ring, fromLL, toLL) {
    var c = ringCentroidLL(ring), f0 = localFrame(c[0], c[1]);
    var d0 = f0.toXY(fromLL), d1 = f0.toXY(toLL), nc = f0.toLL([d1[0] - d0[0], d1[1] - d0[1]]);
    var f1 = localFrame(nc[0], nc[1]);
    return ring.map(function (p) { return f1.toLL(f0.toXY(p)); });
  }

  // ------------------------------------------------------ full result
  function round(x, d) { var m = Math.pow(10, d == null ? 1 : d); return Math.round(x * m) / m; }

  /**
   * Main entry. opts: { geometry|ring, address, lat, lon, source, pitch, roofType, overhangFt,
   *   gutterEndExtFt, ftPerDownspout, minDownspoutsPerRun, overrides:{edgeIndex:'eave'|'rake'}, notes:[] }
   * Returns the shared CONTRACT.md result schema (+ a few extra fields).
   */
  function computeRoof(opts) {
    var oh = resolveOverhang(opts || {});
    var o = Object.assign({}, DEFAULTS, opts || {}, { overhangFt: oh.overhangFt, gutterEndExtFt: oh.gutterEndExtFt });
    var ring = normalizeRing(extractRing(o.geometry || o.ring), o.simplifyFt);
    var edges = edgeList(ring);
    var autoTypes = classifyEdges(ring, o.roofType, o);
    var overrides = o.overrides || {};
    var types = autoTypes.map(function (t, i) { return overrides[i] || t; });
    var pf = pitchFactor(o.pitch);
    var footprint = areaSqft(ring);
    var perim = edges.reduce(function (s, e) { return s + e.length_ft; }, 0);
    var outer = offsetRing(ring, o.overhangFt);
    var planWithOverhang = areaSqft(outer);
    var roofArea = planWithOverhang * pf;
    var g = gutterEstimate(edges, types, o);
    var rakePlan = 0, nRake = 0;
    edges.forEach(function (e, i) { if (types[i] === 'rake') { rakePlan += e.length_ft; nRake++; } });
    // Each gable-end plan edge carries two sloped rakes meeting at the ridge: total = (span + 2*overhang) * pf
    var rakePlanLf = nRake ? rakePlan + 2 * o.overhangFt * nRake : 0;   // ruling #7
    var rakeLf = rakePlanLf * pf;                                       // sloped = drip-edge length
    var c = ringCentroidLL(ring);
    var notes = (o.notes || []).slice();
    var rl = ridgeList(o);
    if (rl.length === 1) o.ridgeBearingDeg = rl[0];
    var multiRidge = rl.length >= 2;
    var hasRidge = !multiRidge && o.ridgeBearingDeg != null && o.ridgeBearingDeg !== '' && isFinite(Number(o.ridgeBearingDeg));
    if (multiRidge && o.roofType === 'gable') notes.push('Eave/rake per wing, constrained to ridge bearings ' + rl.join('°, ') + '° (±' + o.ridgeTolDeg + '°).');
    if (hasRidge && o.roofType === 'gable') notes.push('Eave/rake from ridge bearing ' + Number(o.ridgeBearingDeg) + '° (edges within ±' + o.ridgeTolDeg + '° of ridge = eave).');
    else notes.push('Eave/rake auto-classification is a heuristic from the 2-D roofprint (' + o.roofType + ' assumed); verify on imagery and click edges to correct.');
    if (oh.footprintKind === 'roofprint' && oh.overhangSource !== 'user') notes.push('MassGIS roofprint already includes eaves: overhang 0 ft by default. 2025 orthos may lean 2-6 m off the roofprint; drag to align (lengths unchanged).');
    notes.push('Roof area = (footprint offset by ' + o.overhangFt + ' ft overhang) x pitch factor ' + round(pf, 4) + ' for ' + o.pitch + '; ignores dormers, multiple pitches, and hidden roof planes.');
    if (o.roofType === 'flat') notes.push('Flat roof: all edges shown as eaves; real flat roofs may drain to scuppers/internal drains.');
    return {
      address: o.address || null,
      lat: o.lat != null ? o.lat : round(c[1], 7),
      lon: o.lon != null ? o.lon : round(c[0], 7),
      source: o.source || null,
      footprint_geojson: toGeoJSON(ring, { source: o.source || null }),
      footprint_area_sqft: round(footprint, 1),
      perimeter_ft: round(perim, 1),
      overhang_ft: o.overhangFt,
      overhang_source: oh.overhangSource,
      gutter_end_ext_ft: o.gutterEndExtFt,
      gutter_ext_source: oh.gutterExtSource,
      footprint_kind: oh.footprintKind,
      pitch: typeof o.pitch === 'number' ? o.pitch + '/12' : String(o.pitch),
      pitch_factor: round(pf, 4),
      roof_type: o.roofType,
      ridge_bearing_deg: hasRidge ? Number(o.ridgeBearingDeg) : (multiRidge ? rl[0] : null),
      ridge_bearings_deg: multiRidge ? rl : (hasRidge ? [Number(o.ridgeBearingDeg)] : []),
      eave_rake_method: (o.roofType !== 'gable') ? 'all_eave' : (multiRidge ? 'ridges_per_wing' : (hasRidge ? 'ridge_parallel_eave' : 'wing_depth_heuristic')),
      pitch_source: o.pitchSource || 'manual',
      pitch_confidence: o.pitchConfidence == null ? null : o.pitchConfidence,
      roof_plan_area_sqft: round(planWithOverhang, 1),
      roof_area_sqft: round(roofArea, 1),
      squares: round(roofArea / 100, 2),
      squares_with_waste: round(roofArea * (1 + o.wastePct / 100) / 100, 2),
      waste_pct: o.wastePct,
      edges: edges.map(function (e, i) {
        // 0.1.7.3: per-edge sloped length (contract ruling: rake in the UI is SLOPED). Rake = (plan span + 2 x overhang) x pitch
        // factor, same formula as rake_sloped_lf; eaves are level, so sloped = plan.
        var sl = types[i] === 'rake' ? (e.length_ft + 2 * o.overhangFt) * pf : e.length_ft;
        return { i: i, length_ft: round(e.length_ft, 2), plan_length_ft: round(e.length_ft, 2), sloped_length_ft: round(sl, 2), bearing_deg: round(e.bearing_deg, 1), type: types[i],
          auto: overrides[i] == null, auto_type: autoTypes[i], from: e.from, to: e.to };
      }),
      eave_lf: round(g.eave_lf, 1),
      rake_lf: round(rakeLf, 1),               // = rake_sloped_lf (kept for v1.0 compatibility)
      rake_plan_lf: round(rakePlanLf, 1),
      rake_sloped_lf: round(rakeLf, 1),
      gutter_lf: round(g.gutter_lf, 1),
      downspouts: g.downspouts,
      gutter_runs: g.runs.map(function (r) { return { edges: r.edges, closed: r.closed, length_ft: round(r.length_ft, 1), end_ext_ft: r.end_ext_ft, gutter_ft: round(r.gutter_ft, 1), downspouts: r.downspouts }; }),
      notes: notes,
      calc_version: VERSION
    };
  }

  // ------------------------------------------------------------ export
  function toCSV(r) {
    var lines = [];
    lines.push('field,value');
    ['address', 'lat', 'lon', 'source', 'footprint_area_sqft', 'perimeter_ft', 'overhang_ft', 'pitch', 'pitch_factor', 'roof_type',
      'overhang_source', 'pitch_source', 'pitch_confidence', 'roof_area_sqft', 'squares', 'squares_with_waste', 'eave_lf', 'rake_plan_lf', 'rake_sloped_lf', 'gutter_lf', 'downspouts'].forEach(function (k) {
      var v = r[k] == null ? '' : String(r[k]);
      lines.push(k + ',' + (/[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v));
    });
    lines.push('');
    lines.push('edge,length_ft,bearing_deg,type,auto');
    r.edges.forEach(function (e) { lines.push([e.i, e.length_ft, e.bearing_deg, e.type, e.auto].join(',')); });
    return lines.join('\n');
  }

  function toText(r) {
    var s = [];
    s.push('RoofMeasure estimate' + (r.address ? ' — ' + r.address : ''));
    s.push('Location: ' + r.lat + ', ' + r.lon + (r.source ? '  (footprint: ' + r.source + ')' : ''));
    s.push('Footprint: ' + r.footprint_area_sqft + ' sq ft, perimeter ' + r.perimeter_ft + ' ft');
    s.push('Roof (' + r.roof_type + ', ' + r.pitch + ', x' + r.pitch_factor + ', ' + r.overhang_ft + ' ft overhang): ' +
      r.roof_area_sqft + ' sq ft = ' + r.squares + ' squares (' + r.squares_with_waste + ' w/ ' + r.waste_pct + '% waste)');
    s.push('Eaves: ' + r.eave_lf + ' LF   Rake (sloped, drip-edge length): ' + r.rake_sloped_lf + ' LF (plan ' + r.rake_plan_lf + ' LF)');
    s.push('Gutter: ' + r.gutter_lf + ' LF   Downspouts: ' + r.downspouts);
    s.push('Edges:');
    r.edges.forEach(function (e) { s.push('  #' + e.i + ' ' + e.type.toUpperCase() + ' ' + e.length_ft + ' ft @ ' + e.bearing_deg + '°' + (e.auto ? '' : ' (manual)')); });
    r.notes.forEach(function (n) { s.push('Note: ' + n); });
    s.push('Not yet field-verified; check before ordering.');
    return s.join('\n');
  }

  // ------------------------------------------------------ web mercator
  var TILE = 256, MAX_LAT = 85.05112878;
  /** lon/lat -> world pixel coords at zoom z (256px tiles, z may be fractional). */
  function lonLatToWorld(lon, lat, z) {
    var scale = TILE * Math.pow(2, z);
    var la = Math.max(-MAX_LAT, Math.min(MAX_LAT, lat)) * D2R;
    return [(lon + 180) / 360 * scale, (1 - Math.log(Math.tan(la) + 1 / Math.cos(la)) / Math.PI) / 2 * scale];
  }
  function worldToLonLat(x, y, z) {
    var scale = TILE * Math.pow(2, z);
    var lon = x / scale * 360 - 180;
    var n = Math.PI - 2 * Math.PI * y / scale;
    return [lon, R2D * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)))];
  }
  /** Viewport helper: centre lon/lat, zoom, viewport size px -> {project([lon,lat])->[x,y], unproject([x,y])} */
  function viewport(center, zoom, width, height) {
    var c = lonLatToWorld(center[0], center[1], zoom);
    return {
      project: function (ll) { var w = lonLatToWorld(ll[0], ll[1], zoom); return [w[0] - c[0] + width / 2, w[1] - c[1] + height / 2]; },
      unproject: function (px) { return worldToLonLat(px[0] + c[0] - width / 2, px[1] + c[1] - height / 2, zoom); }
    };
  }
  /** Metres per CSS pixel at latitude for zoom z. */
  function metersPerPixel(lat, z) { return 156543.03392804097 * Math.cos(lat * D2R) / Math.pow(2, z); }
  /**
   * Parse a google.com/maps URL: '@lat,lon,17z' or '@lat,lon,123m' (satellite: metres of view height).
   * Returns {lat, lon, zoom, raw}. For 'm' form, needs viewportHeightPx to derive zoom (default 900).
   */
  function parseGoogleMapsUrl(url, viewportHeightPx) {
    var m = String(url).match(/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?),(\d+(?:\.\d+)?)([zma])/);
    if (!m) return null;
    var lat = parseFloat(m[1]), lon = parseFloat(m[2]), v = parseFloat(m[3]), unit = m[4], zoom;
    if (unit === 'z') zoom = v;
    else if (unit === 'm') {
      var h = viewportHeightPx || 900;
      zoom = Math.log2(156543.03392804097 * Math.cos(lat * D2R) * h / v);
    } else zoom = null; // 'a' = Earth altitude; caller must handle
    return { lat: lat, lon: lon, zoom: zoom, value: v, unit: unit };
  }

  // ----------------------------------------------------- edge snapping
  /** Sobel gradients on an ImageData-like {width,height,data(RGBA)}. Returns {gx,gy,mag,width,height,mean}. */
  function sobel(img) {
    var w = img.width, h = img.height, d = img.data, g = new Float32Array(w * h);
    for (var i = 0; i < w * h; i++) g[i] = 0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2];
    var gx = new Float32Array(w * h), gy = new Float32Array(w * h), mag = new Float32Array(w * h), sum = 0;
    for (var y = 1; y < h - 1; y++) for (var x = 1; x < w - 1; x++) {
      var k = y * w + x;
      var a = g[k - w - 1], b = g[k - w], c = g[k - w + 1], dd = g[k - 1], f = g[k + 1], gg = g[k + w - 1], hh = g[k + w], ii = g[k + w + 1];
      var sx = (c + 2 * f + ii) - (a + 2 * dd + gg), sy = (gg + 2 * hh + ii) - (a + 2 * b + c);
      gx[k] = sx; gy[k] = sy; mag[k] = Math.hypot(sx, sy); sum += mag[k];
    }
    return { gx: gx, gy: gy, mag: mag, width: w, height: h, mean: sum / (w * h) };
  }

  /**
   * Nudge each footprint edge toward the strongest parallel image edge within maxShiftPx, then
   * rebuild vertices as intersections of shifted adjacent edge lines.
   * ring: lon/lat ring. img: ImageData-like. project/unproject: lon/lat <-> image pixel.
   * Returns {ring, shiftsPx:[...], applied:boolean, reason}.
   */
  function snapRingToEdges(ringIn, img, project, unproject, opts) {
    var o = Object.assign({ maxShiftPx: 6, minGain: 1.2, minStrength: 2.0 }, opts || {});
    var ring = normalizeRing(ringIn, 0);
    var S;
    try { S = sobel(img); } catch (e) { return { ring: ring, shiftsPx: [], applied: false, reason: 'image unavailable: ' + e.message }; }
    var P = ring.map(project), n = P.length, shifts = [];
    function sampleNormalGrad(x, y, nx, ny) {
      var xi = Math.round(x), yi = Math.round(y);
      if (xi < 1 || yi < 1 || xi >= S.width - 1 || yi >= S.height - 1) return 0;
      var k = yi * S.width + xi;
      return Math.abs(S.gx[k] * nx + S.gy[k] * ny);
    }
    var lines = [];
    for (var i = 0; i < n; i++) {
      var a = P[i], b = P[(i + 1) % n], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy);
      var nx = L ? -dy / L : 0, ny = L ? dx / L : 0;
      var N = Math.max(5, Math.floor(L)), best = 0, bestScore = -1, base = 0;
      for (var s = -o.maxShiftPx; s <= o.maxShiftPx; s++) {
        var acc = 0;
        for (var t = 1; t < N; t++) {
          var fr = t / N; // skip ends (corners are noisy)
          if (fr < 0.1 || fr > 0.9) continue;
          acc += sampleNormalGrad(a[0] + dx * fr + nx * s, a[1] + dy * fr + ny * s, nx, ny);
        }
        if (s === 0) base = acc;
        // slight preference for small shifts
        var sc = acc * (1 - 0.02 * Math.abs(s));
        if (sc > bestScore) { bestScore = sc; best = s; }
      }
      var cnt = Math.max(1, Math.floor(N * 0.8));
      var strong = bestScore / cnt > o.minStrength * S.mean;
      if (!(strong && bestScore > base * o.minGain) || L < 4) best = 0;
      shifts.push(best);
      lines.push({ p: [a[0] + nx * best, a[1] + ny * best], v: L ? [dx / L, dy / L] : [1, 0] });
    }
    var out = [];
    for (var j = 0; j < n; j++) {
      var l1 = lines[(j - 1 + n) % n], l2 = lines[j];
      var den = l1.v[0] * l2.v[1] - l1.v[1] * l2.v[0];
      var q;
      if (Math.abs(den) < 1e-6) q = l2.p;
      else {
        var tt = ((l2.p[0] - l1.p[0]) * l2.v[1] - (l2.p[1] - l1.p[1]) * l2.v[0]) / den;
        q = [l1.p[0] + l1.v[0] * tt, l1.p[1] + l1.v[1] * tt];
        if (Math.hypot(q[0] - P[j][0], q[1] - P[j][1]) > 3 * o.maxShiftPx) q = P[j];
      }
      out.push(unproject(q));
    }
    var applied = shifts.some(function (s) { return s !== 0; });
    return { ring: applied ? out : ring, shiftsPx: shifts, applied: applied, reason: applied ? 'ok' : 'no stronger nearby edges' };
  }

  return {
    VERSION: VERSION, DEFAULTS: DEFAULTS, PITCHES: PITCHES, M_TO_FT: M_TO_FT,
    haversineFt: haversineFt, geodesicDistanceFt: geodesicDistanceFt, bearingDeg: bearingDeg,
    localFrame: localFrame, extractRing: extractRing, normalizeRing: normalizeRing, closeRing: closeRing, toGeoJSON: toGeoJSON,
    edgeList: edgeList, perimeterFt: perimeterFt, areaSqft: areaSqft, offsetRing: offsetRing,
    parsePitch: parsePitch, pitchFactor: pitchFactor, hipValleyFactor: hipValleyFactor, pitchDegrees: pitchDegrees,
    resolveOverhang: resolveOverhang, translateRing: translateRing,
    classifyEdges: classifyEdges, axisDiffDeg: axisDiffDeg, eaveRuns: eaveRuns, gutterEstimate: gutterEstimate, computeRoof: computeRoof,
    toCSV: toCSV, toText: toText,
    lonLatToWorld: lonLatToWorld, worldToLonLat: worldToLonLat, viewport: viewport, metersPerPixel: metersPerPixel,
    parseGoogleMapsUrl: parseGoogleMapsUrl, sobel: sobel, snapRingToEdges: snapRingToEdges
  };
});
