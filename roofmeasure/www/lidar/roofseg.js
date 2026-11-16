/* SPDX-License-Identifier: MIT */
/* RoofMeasure 0.1.7.3 — whole-roof lidar segmentation (window.RoofSeg).
 * Input: lidar result from lidar/pitch.js (points_full: [x, y, z, cls, intensity, inside] in local metres, frame, ring_local).
 * Steps: local plane per point (k-nearest LSQ) -> region growing -> robust refit -> coplanar merge (small planes kept and
 * flagged, never dropped for size alone) -> plane adjacency -> intersection lines (ridge / hip / valley) and step edges
 * (height jumps) classified as eave / rake of the upper plane, or wall flashing only when a wall rises above the
 * adjacent lower roof plane -> skylight candidates (point voids / dips / intensity outliers inside a plane).
 * Everything is an estimate from free USGS 3DEP data; nothing here is verified (NOT_PROVEN). */
(function (root, factory) { var m = factory(); if (typeof module === 'object' && module.exports) module.exports = m; else root.RoofSeg = m; })(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var VERSION = '0.1.7.5-roofseg-3', M2FT = 3.280839895, R = 6378137, D2R = Math.PI / 180;
  function r2(v) { return Math.round(v * 100) / 100; } function r1(v) { return Math.round(v * 10) / 10; }
  function grid(P, cs) { var g = new Map(); P.forEach(function (p, i) { var k = Math.floor(p[0] / cs) + ',' + Math.floor(p[1] / cs); var a = g.get(k); if (!a) g.set(k, a = []); a.push(i); }); return g; }
  function near(P, g, cs, i, rad) { var p = P[i], cx = Math.floor(p[0] / cs), cy = Math.floor(p[1] / cs), n = Math.ceil(rad / cs), out = [], r2_ = rad * rad;
    for (var dx = -n; dx <= n; dx++) for (var dy = -n; dy <= n; dy++) { var a = g.get((cx + dx) + ',' + (cy + dy)); if (!a) continue;
      for (var j = 0; j < a.length; j++) { var q = P[a[j]], ddx = q[0] - p[0], ddy = q[1] - p[1]; if (ddx * ddx + ddy * ddy <= r2_) out.push(a[j]); } }
    return out; }
  function lsq(P, idx, w) { // z = a x + b y + c, weighted
    var sxx = 0, sxy = 0, syy = 0, sx = 0, sy = 0, sw = 0, sxz = 0, syz = 0, sz = 0, x0 = P[idx[0]][0], y0 = P[idx[0]][1];
    for (var t = 0; t < idx.length; t++) { var p = P[idx[t]], ww = w ? w[t] : 1, x = p[0] - x0, y = p[1] - y0, z = p[2];
      sxx += ww * x * x; sxy += ww * x * y; syy += ww * y * y; sx += ww * x; sy += ww * y; sw += ww; sxz += ww * x * z; syz += ww * y * z; sz += ww * z; }
    var A = [[sxx, sxy, sx], [sxy, syy, sy], [sx, sy, sw]], B = [sxz, syz, sz];
    var det = function (M) { return M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0]) + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]); };
    var D = det(A); if (!isFinite(D) || Math.abs(D) < 1e-9) return null;
    var sol = [0, 1, 2].map(function (k) { return det(A.map(function (row, r) { return row.map(function (v, c) { return c === k ? B[r] : v; }); })) / D; });
    var a = sol[0], b = sol[1], c = sol[2] - a * x0 - b * y0;
    var ss = 0; for (t = 0; t < idx.length; t++) { var q = P[idx[t]], e = q[2] - (a * q[0] + b * q[1] + c); ss += e * e; }
    return { a: a, b: b, c: c, rms: Math.sqrt(ss / idx.length) };
  }
  function robust(P, idx) { var pl = lsq(P, idx); if (!pl) return null;
    for (var it = 0; it < 5; it++) { var res = idx.map(function (i) { var p = P[i]; return Math.abs(p[2] - (pl.a * p[0] + pl.b * p[1] + pl.c)); });
      var s = res.slice().sort(function (x, y) { return x - y; })[res.length >> 1] * 1.4826 + 0.02, cc = 4.685 * s;
      var w = res.map(function (e) { return e < cc ? Math.pow(1 - (e / cc) * (e / cc), 2) : 0; }); var n = lsq(P, idx, w); if (!n) break; pl = n; }
    return pl; }
  function zAt(pl, x, y) { return pl.a * x + pl.b * y + pl.c; }
  function slopeDeg(pl) { return Math.atan(Math.hypot(pl.a, pl.b)) / D2R; }
  function aspectDeg(pl) { return (Math.atan2(-pl.a, -pl.b) / D2R + 360) % 360; } // downslope bearing (x east, y north)
  function rise(pl) { return 12 * Math.hypot(pl.a, pl.b); }
  function angD(a, b) { var d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; }
  function nAngle(p, q) { var n1 = [-p.a, -p.b, 1], n2 = [-q.a, -q.b, 1], d = (n1[0] * n2[0] + n1[1] * n2[1] + 1) / Math.hypot.apply(null, n1) / Math.hypot.apply(null, n2); return Math.acos(Math.min(1, d)) / D2R; }
  function toLL(fr, x, y) { var mx = x / fr.k + fr.ox, my = y / fr.k + fr.oy; return [r7(mx / R / D2R), r7((2 * Math.atan(Math.exp(my / R)) - Math.PI / 2) / D2R)]; }
  function r7(v) { return Math.round(v * 1e7) / 1e7; }
  function distSeg(px, py, a, b) { var dx = b[0] - a[0], dy = b[1] - a[1], L = dx * dx + dy * dy, t = L ? ((px - a[0]) * dx + (py - a[1]) * dy) / L : 0; t = Math.max(0, Math.min(1, t)); return Math.hypot(px - a[0] - t * dx, py - a[1] - t * dy); }
  function distRing(px, py, ring) { var m = Infinity; for (var i = 0; i + 1 < ring.length; i++) m = Math.min(m, distSeg(px, py, ring[i], ring[i + 1])); return m; }
  function snap(rs) { var n = Math.round(rs * 2) / 2; return (Math.abs(n - rs) <= 0.35 ? n : r1(rs)) + '/12'; }
  function conf(n, rms) { return n >= 60 && rms <= 0.08 ? 'high' : n >= 20 && rms <= 0.15 ? 'medium' : 'low'; }

  function segment(lidar, opts) {
    opts = opts || {};
    var P = lidar && lidar.points_full, fr = lidar && lidar.frame, ring = lidar && lidar.ring_local;
    var out = { version: VERSION, status: 'no_points', planes: [], lines: [], steps: [], skylights: [], notes: [], n_points: P ? P.length : 0 };
    if (!P || P.length < 30 || !fr) { out.notes.push('fewer than 30 roof points with full cloud; segmentation skipped'); return out; }
    var cs = 1.0, g = grid(P, cs), K = opts.radius_m || 1.1, N = P.length;
    // 1. local plane per point
    var loc = new Array(N);
    for (var i = 0; i < N; i++) { var nb = near(P, g, cs, i, K); loc[i] = nb.length >= 5 ? lsq(P, nb) : null; if (loc[i]) loc[i].nb = nb; }
    // 2. region growing (seeds = flattest local residual first)
    var order = []; for (i = 0; i < N; i++) if (loc[i] && loc[i].rms < 0.12) order.push(i);
    order.sort(function (x, y) { return loc[x].rms - loc[y].rms; });
    var lab = new Int32Array(N).fill(-1), regions = [];
    var ANG = opts.angle_deg || 12, DZ = opts.dist_m || 0.18;
    order.forEach(function (s) {
      if (lab[s] >= 0) return; var id = regions.length, mem = [s], pl = loc[s], q = [s]; lab[s] = id;
      while (q.length) { var c = q.pop(), nb = loc[c] ? loc[c].nb : near(P, g, cs, c, K);
        for (var t = 0; t < nb.length; t++) { var j = nb[t]; if (lab[j] >= 0 || !loc[j]) continue;
          var p = P[j]; if (Math.abs(p[2] - zAt(pl, p[0], p[1])) > DZ) continue; if (nAngle(loc[j], pl) > ANG && loc[j].rms < 0.12) continue;
          lab[j] = id; mem.push(j); q.push(j);
          if (mem.length % 25 === 0 && mem.length >= 25) { var np = lsq(P, mem); if (np) pl = np; } } }
      regions.push({ id: id, idx: mem });
    });
    // 3. keep regions >= minPts; small ones kept + flagged
    var MIN = opts.min_points || 6;
    var planes = regions.filter(function (r) { return r.idx.length >= MIN; }).map(function (r) { var pl = robust(P, r.idx); if (!pl) return null; pl.idx = r.idx; return pl; }).filter(Boolean)
      .filter(function (pl) { return slopeDeg(pl) <= 70; });
    // 4. coplanar merge (adjacent or not: the same plane split by a gap is still one plane)
    var merged = true;
    while (merged) { merged = false;
      for (var a = 0; a < planes.length && !merged; a++) for (var b = a + 1; b < planes.length && !merged; b++) {
        var A = planes[a], B = planes[b]; if (nAngle(A, B) > 3) continue;
        var cB = cent(P, B.idx); if (Math.abs(zAt(A, cB[0], cB[1]) - cB[2]) > 0.2) continue;
        var cA = cent(P, A.idx); if (Math.abs(zAt(B, cA[0], cA[1]) - cA[2]) > 0.2) continue;
        var idx = A.idx.concat(B.idx), pl = robust(P, idx); if (!pl) continue; pl.idx = idx; planes.splice(b, 1); planes[a] = pl; merged = true; } }
    planes.sort(function (x, y) { return y.idx.length - x.idx.length; });
    var pid = new Int32Array(N).fill(-1);
    planes.forEach(function (pl, k) { pl.k = k; pl.idx.forEach(function (i) { var p = P[i]; if (Math.abs(p[2] - zAt(pl, p[0], p[1])) <= 0.25) pid[i] = k; }); pl.idx = pl.idx.filter(function (i) { return pid[i] === k; }); });
    var totalIn = 0; planes.forEach(function (pl) { totalIn += pl.idx.length; });
    // plan area of each plane: occupied 0.5 m cells
    out.planes = planes.map(function (pl, k) {
      var cells = new Set(); pl.idx.forEach(function (i) { cells.add(Math.floor(P[i][0] / 0.5) + ',' + Math.floor(P[i][1] / 0.5)); });
      var c = cent(P, pl.idx), ins = pl.idx.filter(function (i) { return P[i][5]; }).length, rs = rise(pl);
      var area = cells.size * 0.25 * M2FT * M2FT, small = pl.idx.length < 25 || area < 40;
      // extents along strike (eave direction) and dip (down-slope) for dormer / gutter estimates
      var gl = Math.hypot(pl.a, pl.b), du = gl > 1e-6 ? [-pl.a / gl, -pl.b / gl] : [1, 0], su = [-du[1], du[0]];
      var ps = pl.idx.map(function (i) { return P[i][0] * su[0] + P[i][1] * su[1]; }).sort(function (x, y) { return x - y; });
      var pd = pl.idx.map(function (i) { return P[i][0] * du[0] + P[i][1] * du[1]; }).sort(function (x, y) { return x - y; });
      var q = function (a2, f) { return a2[Math.min(a2.length - 1, Math.max(0, Math.round((a2.length - 1) * f)))]; };
      var strike = (q(ps, 0.97) - q(ps, 0.03)) + 0.5, dip = (q(pd, 0.97) - q(pd, 0.03)) + 0.5;
      return { id: 'P' + (k + 1), n_points: pl.idx.length, rms_m: r2(pl.rms * 100) / 100, rise_raw: r2(rs), pitch: snap(rs), slope_deg: r1(slopeDeg(pl)), aspect_deg: rs < 0.6 ? null : r1(aspectDeg(pl)),
        plan_area_sqft_approx: Math.round(area), inside_frac: r2(ins / pl.idx.length), small: small, confidence: small ? 'low' : conf(pl.idx.length, pl.rms), centroid_lonlat: toLL(fr, c[0], c[1]), z_m: r2(c[2]),
        strike_len_ft: r1(strike * M2FT), dip_len_ft: r1(dip * M2FT),
        // 0.1.7.5: outline (convex hull) of low-slope planes, for roof-deck / flat-section candidates
        outline_lonlat: rs <= 2 ? hull(pl.idx.map(function (i) { return [P[i][0], P[i][1]]; })).map(function (h) { var ll = toLL(fr, h[0], h[1]); return [Math.round(ll[0] * 1e7) / 1e7, Math.round(ll[1] * 1e7) / 1e7]; }) : undefined };
    });
    out.coverage = r2(totalIn / N);
    // 5. adjacency: boundary point pairs between planes
    var pairs = {};
    for (i = 0; i < N; i++) { if (pid[i] < 0) continue; var nb2 = near(P, g, cs, i, 1.0);
      for (var t2 = 0; t2 < nb2.length; t2++) { var j2 = nb2[t2]; if (pid[j2] < 0 || pid[j2] <= pid[i]) continue;
        var key = pid[i] + '-' + pid[j2]; (pairs[key] = pairs[key] || []).push([i, j2]); } }
    Object.keys(pairs).forEach(function (key) {
      var pr = pairs[key]; if (pr.length < 3) return; var ab = key.split('-').map(Number), A = planes[ab[0]], B = planes[ab[1]];
      var mids = pr.map(function (q) { var p = P[q[0]], s = P[q[1]]; return [(p[0] + s[0]) / 2, (p[1] + s[1]) / 2]; });
      var gaps = mids.map(function (m) { return Math.abs(zAt(A, m[0], m[1]) - zAt(B, m[0], m[1])); }).sort(function (x, y) { return x - y; });
      var gap = gaps[gaps.length >> 1], ang = nAngle(A, B);
      if (ang < 4 && gap < 0.3) return;
      if (gap < 0.35) addIntersection(out, P, fr, ring, A, B, mids, pr.length);
      else addStep(out, P, fr, ring, A, B, mids, pr.length, gap);
    });
    // 5b. de-duplicate near-collinear lines of the same type (keep the better-supported one)
    out.lines = dedupe(out.lines, fr); out.steps = dedupe(out.steps, fr);
    // 6. skylight candidates inside planes (point voids, dips, intensity outliers)
    out.skylights = skylights(P, planes, fr, ring);
    out.status = 'ok';
    out.notes.push('whole-roof segmentation: ' + planes.length + ' planes from ' + N + ' building points (coverage ' + Math.round(out.coverage * 100) + '%); small planes are kept and flagged, not dropped');
    out.notes.push('lines from plane intersections (ridge/hip/valley) and height jumps (step edges); wall flashing only where a wall rises above an adjacent lower roof plane, otherwise the step is the upper plane\'s eave or rake');
    return out;
  }
  function dedupe(L, fr) {
    var lat = L.length ? L[0].coords_lonlat[0][1] : 0, kx = Math.cos(lat * D2R) * 111320, ky = 110540;
    function xy(p) { return [p[0] * kx, p[1] * ky]; }
    L = L.slice().sort(function (a, b) { return b.n_pairs - a.n_pairs; });
    var keep = [];
    L.forEach(function (l) { var a = xy(l.coords_lonlat[0]), b = xy(l.coords_lonlat[1]), dup = keep.some(function (k) {
        if (k.type !== l.type) return false; var c = xy(k.coords_lonlat[0]), d = xy(k.coords_lonlat[1]), hit = 0;
        for (var t = 0; t <= 10; t++) { var px = a[0] + (b[0] - a[0]) * t / 10, py = a[1] + (b[1] - a[1]) * t / 10; if (distSeg(px, py, c, d) < 1.0) hit++; }
        return hit >= 6; });
      if (!dup) keep.push(l); });
    return keep;
  }
  function cent(P, idx) { var x = 0, y = 0, z = 0; idx.forEach(function (i) { x += P[i][0]; y += P[i][1]; z += P[i][2]; }); return [x / idx.length, y / idx.length, z / idx.length]; }
  function extent(mids, d) { var ts = mids.map(function (m) { return m[0] * d[0] + m[1] * d[1]; }).sort(function (x, y) { return x - y; });
    var lo = ts[Math.floor(ts.length * 0.03)], hi = ts[Math.min(ts.length - 1, Math.ceil(ts.length * 0.97) - 1)]; return [lo - 0.35, hi + 0.35]; }
  function lineConf(np, A, B) { var m = Math.min(A.idx.length, B.idx.length); return np >= 12 && m >= 25 ? 'high' : np >= 6 && m >= 10 ? 'medium' : 'low'; }
  function addIntersection(out, P, fr, ring, A, B, mids, np) {
    var da = A.a - B.a, db = A.b - B.b, dc = A.c - B.c, L = Math.hypot(da, db); if (L < 1e-6) return;
    var nrm = [da / L, db / L], off = -dc / L, d = [-nrm[1], nrm[0]]; // line: nrm . p = off
    var ex = extent(mids, d), p0 = [nrm[0] * off + d[0] * ex[0], nrm[1] * off + d[1] * ex[0]], p1 = [nrm[0] * off + d[0] * ex[1], nrm[1] * off + d[1] * ex[1]];
    var plan = (ex[1] - ex[0]); if (plan < 0.6) return;
    var dz = A.a * d[0] + A.b * d[1], cA = cent(P, A.idx), sA = Math.sign(nrm[0] * cA[0] + nrm[1] * cA[1] - off) || 1;
    var probe = [nrm[0] * (off + 0.8 * sA) + d[0] * (ex[0] + ex[1]) / 2, nrm[1] * (off + 0.8 * sA) + d[1] * (ex[0] + ex[1]) / 2];
    var convex = zAt(A, probe[0], probe[1]) < zAt(B, probe[0], probe[1]);
    var type = !convex ? 'valley' : Math.abs(dz) < 0.09 ? 'ridge' : 'hip';
    var sl = plan * Math.sqrt(1 + dz * dz);
    out.lines.push({ type: type, plan_length_ft: r2(plan * M2FT), length_ft: r2(sl * M2FT), planes: ['P' + (A.k + 1), 'P' + (B.k + 1)], n_pairs: np, confidence: lineConf(np, A, B),
      coords_lonlat: [toLL(fr, p0[0], p0[1]), toLL(fr, p1[0], p1[1])], on_footprint: false, source: 'lidar plane intersection' });
  }
  function addStep(out, P, fr, ring, A, B, mids, np, gap) {
    // fit the step line through the boundary midpoints (PCA)
    var mx = 0, my = 0; mids.forEach(function (m) { mx += m[0]; my += m[1]; }); mx /= mids.length; my /= mids.length;
    var sxx = 0, sxy = 0, syy = 0; mids.forEach(function (m) { var x = m[0] - mx, y = m[1] - my; sxx += x * x; sxy += x * y; syy += y * y; });
    var th = 0.5 * Math.atan2(2 * sxy, sxx - syy), d = [Math.cos(th), Math.sin(th)];
    var ts = mids.map(function (m) { return (m[0] - mx) * d[0] + (m[1] - my) * d[1]; }).sort(function (x, y) { return x - y; });
    var lo = ts[Math.floor(ts.length * 0.03)] - 0.35, hi = ts[Math.min(ts.length - 1, Math.ceil(ts.length * 0.97) - 1)] + 0.35, plan = hi - lo; if (plan < 0.6) return;
    var p0 = [mx + d[0] * lo, my + d[1] * lo], p1 = [mx + d[0] * hi, my + d[1] * hi];
    var U = zAt(A, mx, my) > zAt(B, mx, my) ? A : B, Lw = U === A ? B : A;
    var edgeB = (Math.atan2(d[0], d[1]) / D2R + 360) % 180;
    function rel(pl) { if (rise(pl) < 0.6) return { para: false, up: false, flat: true }; var asp = aspectDeg(pl), t = angD(edgeB, asp) % 180; t = Math.min(t, 180 - t);
      var c = cent(P, pl.idx), dn = [Math.sin(asp * D2R), Math.cos(asp * D2R)], s = (mx - c[0]) * dn[0] + (my - c[1]) * dn[1];
      return { para: t < 45, up: s < 0, flat: false }; }
    var rU = rel(U), rL = rel(Lw);
    var onFp = ring ? (distRing(mx, my, ring) < 0.9 && distRing(p0[0], p0[1], ring) < 1.2 && distRing(p1[0], p1[1], ring) < 1.2) : false;
    // a wall rises above the lower plane only if the lower plane continues under/up to the step (its upslope or side edge)
    // and the upper roof surface is above the lower plane's surface along the step
    var wallAbove = !rL.flat ? (rL.up || rL.para) : true;
    var type, sub;
    if (wallAbove && !onFp) { type = 'wall_flashing'; sub = rL.para ? 'sidewall (step flashing)' : 'headwall'; }
    else { type = rU.flat ? 'eave' : rU.para ? 'rake' : 'eave'; sub = 'upper-plane ' + type + ' (wall drops below; no flashing)'; }
    var k = rise(U) / 12, sl = (type === 'rake') ? plan * Math.sqrt(1 + k * k) : plan;
    out.steps.push({ type: type, subtype: sub, plan_length_ft: r2(plan * M2FT), length_ft: r2(sl * M2FT), drop_ft: r1(gap * M2FT), upper: 'P' + (U.k + 1), lower: 'P' + (Lw.k + 1), n_pairs: np,
      confidence: lineConf(np, A, B), on_footprint: onFp, coords_lonlat: [toLL(fr, p0[0], p0[1]), toLL(fr, p1[0], p1[1])], source: 'lidar height jump' });
  }
  function skylights(P, planes, fr, ring) {
    var out = [], cs = 0.5;
    planes.forEach(function (pl) {
      if (pl.idx.length < 60 || rise(pl) < 0.6) return;
      var cells = new Map(), sumI = 0, sumI2 = 0;
      pl.idx.forEach(function (i) { var p = P[i], k = Math.floor(p[0] / cs) + ',' + Math.floor(p[1] / cs), c = cells.get(k); if (!c) cells.set(k, c = { n: 0, res: 0, it: 0 }); c.n++; c.res += p[2] - zAt(pl, p[0], p[1]); c.it += p[4]; sumI += p[4]; sumI2 += p[4] * p[4]; });
      var n = pl.idx.length, mI = sumI / n, sI = Math.sqrt(Math.max(1, sumI2 / n - mI * mI));
      // candidate cells: empty cells fully surrounded by occupied cells (radius 2), or cells with mean dip < -0.12 m, or intensity |z| > 2.5
      var keys = Array.from(cells.keys()).map(function (k) { return k.split(',').map(Number); });
      var minx = Math.min.apply(null, keys.map(function (k) { return k[0]; })), maxx = Math.max.apply(null, keys.map(function (k) { return k[0]; }));
      var miny = Math.min.apply(null, keys.map(function (k) { return k[1]; })), maxy = Math.max.apply(null, keys.map(function (k) { return k[1]; }));
      var flag = new Map();
      for (var x = minx + 2; x <= maxx - 2; x++) for (var y = miny + 2; y <= maxy - 2; y++) {
        var c = cells.get(x + ',' + y), why = null;
        if (!c) { var occ = 0, tot = 0; for (var dx = -2; dx <= 2; dx++) for (var dy = -2; dy <= 2; dy++) { if (Math.abs(dx) < 2 && Math.abs(dy) < 2) continue; tot++; if (cells.has((x + dx) + ',' + (y + dy))) occ++; }
          if (occ >= tot - 2) why = 'void'; }
        else if (c.res / c.n < -0.12) why = 'dip';
        else if ((c.it / c.n - mI) / sI < -2.5) why = 'intensity'; // glass often returns weak/low intensity
        if (why) flag.set(x + ',' + y, why);
      }
      // cluster flagged cells (8-connectivity); keep clusters of 2..24 cells (0.5..6 m2) away from the plane boundary
      var seen = new Set();
      flag.forEach(function (why, k0) {
        if (seen.has(k0)) return; var st = [k0], cl = []; seen.add(k0);
        while (st.length) { var k = st.pop(); cl.push(k); var xy = k.split(',').map(Number);
          for (var dx = -1; dx <= 1; dx++) for (var dy = -1; dy <= 1; dy++) { var kk = (xy[0] + dx) + ',' + (xy[1] + dy); if (flag.has(kk) && !seen.has(kk)) { seen.add(kk); st.push(kk); } } }
        if (cl.length < 2 || cl.length > 24) return;
        var onlyI = cl.every(function (k) { return flag.get(k) === 'intensity'; }); if (onlyI && cl.length < 3) return;
        var xs = cl.map(function (k) { return +k.split(',')[0]; }), ys = cl.map(function (k) { return +k.split(',')[1]; });
        var cx = (Math.min.apply(null, xs) + Math.max.apply(null, xs) + 1) / 2 * cs, cy = (Math.min.apply(null, ys) + Math.max.apply(null, ys) + 1) / 2 * cs;
        if (ring && distRing(cx, cy, ring) < 1.0) return;
        var w = (Math.max.apply(null, xs) - Math.min.apply(null, xs) + 1) * cs, h = (Math.max.apply(null, ys) - Math.min.apply(null, ys) + 1) * cs;
        var kinds = {}; cl.forEach(function (k) { kinds[flag.get(k)] = 1; });
        out.push({ plane: 'P' + (pl.k + 1), centroid_lonlat: toLL(fr, cx, cy), approx_w_ft: r1(w * M2FT), approx_h_ft: r1(h * M2FT), approx_area_sqft: Math.round(cl.length * cs * cs * M2FT * M2FT),
          evidence: Object.keys(kinds), confidence: 'low', status: 'NOT_PROVEN candidate', source: 'lidar ' + Object.keys(kinds).join('+') });
      });
    });
    return out.slice(0, 12);
  }
  function hull(pts) { // Andrew monotone chain
    var p = pts.slice().sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; }); if (p.length < 3) return p;
    function cr(o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }
    var lo = [], up = [], i;
    for (i = 0; i < p.length; i++) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], p[i]) <= 0) lo.pop(); lo.push(p[i]); }
    for (i = p.length - 1; i >= 0; i--) { while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], p[i]) <= 0) up.pop(); up.push(p[i]); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  }
  return { VERSION: VERSION, segment: segment, _robust: robust };
});
