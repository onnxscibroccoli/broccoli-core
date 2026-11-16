/* SPDX-License-Identifier: MIT
 * RoofMeasure 0.1.7.3 — per-facet lidar plane fits (lidar/facetfit.js).
 * Input: the USGS 3DEP roof points kept by lidar/pitch.js (points_local, metres, frame {ox, oy, k}) and the roof
 * facets from lib/facets.js (polygon_lonlat, downslope_bearing_deg). For each facet:
 *   1. select lidar points inside the facet polygon, at least insetM (0.5 m) from its boundary (keeps ridge/hip/eave
 *      points of the neighbouring plane out),
 *   2. RANSAC (fixed seed, 0.15 m) for an initial plane, then IRLS with Tukey biweight weights (scale from the MAD),
 *   3. report point count, inliers, RMS residual, raw rise (x/12) with its standard error, aspect and the difference to
 *      the facet's downslope bearing,
 *   4. snap the rise to the nearest whole x/12 when it is within 0.5 of it, with a confidence grade,
 *   5. group facets whose fitted planes are coplanar (slope within 2.5 deg, aspect within 12 deg, offset within 0.2 m).
 * Nothing here looks at imagery. All results are NOT_PROVEN against measured roofs.
 * window.RoofFacetFit = { fitFacets, fitPlaneRobust, snapRise, VERSION }
 */
(function (root) {
  'use strict';
  var VERSION = '0.1.7.3-facetfit-1', D2R = Math.PI / 180, R2D = 180 / Math.PI, RM = 6378137.0;
  function merc(lon, lat) { return [lon * D2R * RM, Math.log(Math.tan(Math.PI / 4 + (lat * D2R) / 2)) * RM]; }
  function toLocal(fr, ll) { var m = merc(ll[0], ll[1]); return [(m[0] - fr.ox) * fr.k, (m[1] - fr.oy) * fr.k]; }
  function pip(x, y, poly) { var c = false; for (var i = 0, j = poly.length - 1; i < poly.length; j = i++) { var a = poly[i], b = poly[j];
    if (((a[1] > y) !== (b[1] > y)) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
  function dSeg(px, py, a, b) { var dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy, t = l2 ? ((px - a[0]) * dx + (py - a[1]) * dy) / l2 : 0;
    t = Math.max(0, Math.min(1, t)); return Math.hypot(px - a[0] - t * dx, py - a[1] - t * dy); }
  function dPoly(px, py, poly) { var m = Infinity; for (var i = 0; i < poly.length; i++) m = Math.min(m, dSeg(px, py, poly[i], poly[(i + 1) % poly.length])); return m; }
  function rng(seed) { var s = seed >>> 0 || 1; return function () { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
  function solve3(M, v) { // Cramer's rule
    function det(m) { return m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]); }
    var D = det(M); if (Math.abs(D) < 1e-12) return null;
    return [0, 1, 2].map(function (k) { return det(M.map(function (row, r) { return row.map(function (val, c) { return c === k ? v[r] : val; }); })) / D; });
  }
  function inv3(M) { var a = M; var d = a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0]) + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
    if (Math.abs(d) < 1e-12) return null;
    return [[(a[1][1] * a[2][2] - a[1][2] * a[2][1]) / d, (a[0][2] * a[2][1] - a[0][1] * a[2][2]) / d, (a[0][1] * a[1][2] - a[0][2] * a[1][1]) / d],
      [(a[1][2] * a[2][0] - a[1][0] * a[2][2]) / d, (a[0][0] * a[2][2] - a[0][2] * a[2][0]) / d, (a[0][2] * a[1][0] - a[0][0] * a[1][2]) / d],
      [(a[1][0] * a[2][1] - a[1][1] * a[2][0]) / d, (a[0][1] * a[2][0] - a[0][0] * a[2][1]) / d, (a[0][0] * a[1][1] - a[0][1] * a[1][0]) / d]]; }
  function wls(P, w, cx, cy) { // weighted z = a(x-cx) + b(y-cy) + c
    var s = [[0, 0, 0], [0, 0, 0], [0, 0, 0]], v = [0, 0, 0];
    for (var i = 0; i < P.length; i++) { if (!w[i]) continue; var x = P[i][0] - cx, y = P[i][1] - cy, z = P[i][2], r = [x, y, 1];
      for (var a = 0; a < 3; a++) { v[a] += w[i] * r[a] * z; for (var b = 0; b < 3; b++) s[a][b] += w[i] * r[a] * r[b]; } }
    var co = solve3(s, v); return co ? { co: co, XtWX: s } : null;
  }
  function median(a) { var b = a.slice().sort(function (x, y) { return x - y; }); var n = b.length; return n ? (n % 2 ? b[n >> 1] : (b[n / 2 - 1] + b[n / 2]) / 2) : NaN; }
  /** Robust plane z = a x + b y + c through P ([x, y, z] metres). Returns null if it cannot fit. */
  function fitPlaneRobust(P, o) {
    o = o || {}; var thr = o.thresh || 0.15, iters = o.iters || 300, rand = rng(o.seed || 7), n = P.length;
    if (n < 3) return null;
    var cx = 0, cy = 0; P.forEach(function (p) { cx += p[0]; cy += p[1]; }); cx /= n; cy /= n;
    var best = null, bestN = -1;
    for (var it = 0; it < iters; it++) {
      var p1 = P[(rand() * n) | 0], p2 = P[(rand() * n) | 0], p3 = P[(rand() * n) | 0];
      var u = [p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]], v = [p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]];
      var nx = u[1] * v[2] - u[2] * v[1], ny = u[2] * v[0] - u[0] * v[2], nz = u[0] * v[1] - u[1] * v[0], nn = Math.hypot(nx, ny, nz);
      if (nn < 1e-9 || Math.abs(nz) / nn < 0.25) continue;
      nx /= nn; ny /= nn; nz /= nn; var cnt = 0;
      for (var i = 0; i < n; i++) { var q = P[i]; if (Math.abs((q[0] - p1[0]) * nx + (q[1] - p1[1]) * ny + (q[2] - p1[2]) * nz) < thr) cnt++; }
      if (cnt > bestN) { bestN = cnt; best = [p1, nx, ny, nz]; }
    }
    if (!best) return null;
    var w = P.map(function (q) { return Math.abs((q[0] - best[0][0]) * best[1] + (q[1] - best[0][1]) * best[2] + (q[2] - best[0][2]) * best[3]) < thr ? 1 : 0; });
    var f = wls(P, w, cx, cy); if (!f) return null;
    var sigma = thr;
    for (var k = 0; k < 6; k++) { // IRLS, Tukey biweight
      var res = P.map(function (q) { return q[2] - (f.co[0] * (q[0] - cx) + f.co[1] * (q[1] - cy) + f.co[2]); });
      var inl = res.filter(function (r, i) { return w[i] > 0; }).map(Math.abs);
      sigma = Math.max(0.02, 1.4826 * median(inl.length ? inl : res.map(Math.abs)));
      var c = 4.685 * sigma;
      w = res.map(function (r) { var t = r / c; return Math.abs(t) < 1 ? (1 - t * t) * (1 - t * t) : 0; });
      var f2 = wls(P, w, cx, cy); if (!f2) break; f = f2;
    }
    var resF = P.map(function (q) { return q[2] - (f.co[0] * (q[0] - cx) + f.co[1] * (q[1] - cy) + f.co[2]); });
    var inIdx = []; resF.forEach(function (r, i) { if (Math.abs(r) < Math.max(2.5 * sigma, 0.06)) inIdx.push(i); });
    var ss = 0; inIdx.forEach(function (i) { ss += resF[i] * resF[i]; });
    var rms = inIdx.length ? Math.sqrt(ss / inIdx.length) : NaN;
    // covariance from the inlier (unweighted) normal matrix
    var w1 = P.map(function (_, i) { return inIdx.indexOf(i) >= 0 ? 1 : 0; }), f1 = wls(P, w1, cx, cy), Ci = f1 ? inv3(f1.XtWX) : null;
    var a = f.co[0], b = f.co[1], g = Math.hypot(a, b), seG = NaN;
    if (Ci && g > 1e-9 && inIdx.length > 3) { var s2 = ss / Math.max(1, inIdx.length - 3); seG = Math.sqrt(Math.max(0, (a * a * Ci[0][0] + b * b * Ci[1][1] + 2 * a * b * Ci[0][1]) * s2)) / g; }
    var slope = Math.atan(g) * R2D, aspect = g ? ((Math.atan2(-a, -b) * R2D) % 360 + 360) % 360 : null;
    return { a: a, b: b, c: f.co[2], cx: cx, cy: cy, n: n, n_inliers: inIdx.length, inlier_frac: inIdx.length / n, rms_m: rms, sigma_m: sigma,
      slope_deg: slope, aspect_deg: aspect, rise: 12 * g, se_rise: 12 * seG };
  }
  /** Snap a rise to the nearest whole x/12 when within tol (default 0.5). */
  function snapRise(rise, tol) { var r0 = Math.round(rise); return { rise: r0, pitch: r0 + '/12', delta: rise - r0, ok: Math.abs(rise - r0) <= (tol == null ? 0.5 : tol) }; }
  function angDiff360(a, b) { var d = Math.abs(a - b) % 360; return Math.min(d, 360 - d); }
  function grade(fp, aspDiff) {
    if (!fp) return 'none';
    if (fp.n_inliers >= 60 && fp.rms_m <= 0.08 && fp.se_rise <= 0.3 && aspDiff != null && aspDiff <= 20 && fp.inlier_frac >= 0.6) return 'high';
    if (fp.n_inliers >= 25 && fp.rms_m <= 0.15 && fp.se_rise <= 0.6 && aspDiff != null && aspDiff <= 30 && fp.inlier_frac >= 0.45) return 'medium';
    return 'low';
  }
  /** lidar: result of estimatePitch (needs points_local + frame). facets: [{id, polygon_lonlat, downslope_bearing_deg, plan_area_sqft}] */
  function fitFacets(lidar, facets, opts) {
    opts = opts || {}; var inset = opts.insetM == null ? 0.5 : opts.insetM, minN = opts.minPoints || 12;
    var out = { version: VERSION, method: 'per-facet robust plane fit: points inside each facet (inset ' + inset + ' m), RANSAC 0.15 m + Tukey IRLS; rise snapped to whole x/12 within 0.5; coplanar facets grouped',
      facets: [], groups: [], status: 'NOT_PROVEN' };
    var P = lidar && lidar.points_local, fr = lidar && lidar.frame;
    if (!P || !fr || !Array.isArray(facets)) { out.error = 'no lidar points kept (run Auto pitch first)'; return out; }
    var fits = [];
    facets.forEach(function (fx) {
      var row = { id: fx.id, downslope_bearing_deg: fx.downslope_bearing_deg, plan_area_sqft: fx.plan_area_sqft };
      if (!fx.polygon_lonlat || fx.polygon_lonlat.length < 4) { row.status = 'no_polygon'; out.facets.push(row); fits.push(null); return; }
      var poly = fx.polygon_lonlat.slice(0, -1).map(function (ll) { return toLocal(fr, ll); });
      var pts = P.filter(function (p) { return pip(p[0], p[1], poly) && dPoly(p[0], p[1], poly) >= inset; });
      row.n_points = pts.length;
      if (pts.length < minN) { row.status = 'too_few_points'; out.facets.push(row); fits.push(null); return; }
      var fp = fitPlaneRobust(pts, { seed: 7 });
      if (!fp || fp.n_inliers < minN) { row.status = 'no_fit'; out.facets.push(row); fits.push(null); return; }
      var ad = fp.aspect_deg == null || fx.downslope_bearing_deg == null ? null : angDiff360(fp.aspect_deg, fx.downslope_bearing_deg);
      var sn = snapRise(fp.rise);
      Object.assign(row, { n_inliers: fp.n_inliers, inlier_frac: +fp.inlier_frac.toFixed(2), rms_m: +fp.rms_m.toFixed(3), rise_raw: +fp.rise.toFixed(2), se_rise: +fp.se_rise.toFixed(2),
        slope_deg: +fp.slope_deg.toFixed(1), aspect_deg: fp.aspect_deg == null ? null : +fp.aspect_deg.toFixed(1), aspect_diff_deg: ad == null ? null : +ad.toFixed(1),
        pitch_snapped: sn.pitch, snap_delta: +sn.delta.toFixed(2), snap_ok: sn.ok, confidence: grade(fp, ad) });
      row.status = ad != null && ad > 30 ? 'aspect_mismatch' : 'fit';
      row.usable = row.status === 'fit' && (row.confidence === 'high' || row.confidence === 'medium');
      row.pitch_used = row.usable ? (sn.ok ? sn.pitch : (Math.round(fp.rise * 2) / 2) + '/12') : null;
      fp.pts = pts; fits.push(fp); out.facets.push(row);
    });
    // coplanar groups (union-find)
    var par = facets.map(function (_, i) { return i; }); function fnd(i) { while (par[i] !== i) i = par[i] = par[par[i]]; return i; }
    for (var i = 0; i < fits.length; i++) for (var j = i + 1; j < fits.length; j++) {
      var A = fits[i], B = fits[j]; if (!A || !B || A.aspect_deg == null || B.aspect_deg == null) continue;
      if (Math.abs(A.slope_deg - B.slope_deg) > 2.5 || angDiff360(A.aspect_deg, B.aspect_deg) > 12) continue;
      var mx = (A.cx + B.cx) / 2, my = (A.cy + B.cy) / 2;
      var za = A.a * (mx - A.cx) + A.b * (my - A.cy) + A.c, zb = B.a * (mx - B.cx) + B.b * (my - B.cy) + B.c;
      if (Math.abs(za - zb) <= 0.2) par[fnd(j)] = fnd(i);
    }
    var groups = {}; fits.forEach(function (f, i) { if (f) { var r = fnd(i); (groups[r] = groups[r] || []).push(i); } });
    Object.keys(groups).forEach(function (r) { var ids = groups[r]; if (ids.length < 2) return;
      var pts = []; ids.forEach(function (i) { pts = pts.concat(fits[i].pts); });
      var g = fitPlaneRobust(pts, { seed: 11 });
      out.groups.push({ facets: ids.map(function (i) { return facets[i].id; }), n_points: pts.length, rise_raw: g ? +g.rise.toFixed(2) : null, rms_m: g ? +g.rms_m.toFixed(3) : null,
        pitch_snapped: g ? snapRise(g.rise).pitch : null });
    });
    var used = out.facets.filter(function (r) { return r.usable; });
    out.n_facets = facets.length; out.n_usable = used.length; out.all_usable = used.length === facets.length && facets.length > 0;
    return out;
  }
  var api = { fitFacets: fitFacets, fitPlaneRobust: fitPlaneRobust, snapRise: snapRise, VERSION: VERSION };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.RoofFacetFit = api;
})(typeof self !== 'undefined' ? self : this);
