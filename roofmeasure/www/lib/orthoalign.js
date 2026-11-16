// SPDX-License-Identifier: MIT
/**
 * orthoalign.js — ortho lean/offset estimate and skylight-like patch candidates from FREE imagery only
 * (MassGIS 2025 15 cm orthos, USGS NAIP). Never used on Google / Microsoft / Esri imagery.
 *
 * align(): the 2025 orthos are not true orthos, so a roof is displaced from its roofprint by relief (lean) and
 * registration error. Bounded 2-D translation search: score(d) = mean |gradient . edge normal| of the ortho
 * sampled along the roofprint edges shifted by d. Coarse grid (2 px), refine (1 px), sub-pixel parabola. Then a
 * per-edge 1-D residual search along each edge normal shows what a single translation cannot explain.
 * patches(): bright or dark compact rectangles inside the roof (after the shift) relative to a local background,
 * as skylight / chimney / vent CANDIDATES (NOT_PROVEN).
 * All coordinates: "world pixels" at zoom z (Web Mercator, 256-px tiles).
 */
(function (root, factory) { var m = factory(); if (typeof module === 'object' && module.exports) module.exports = m; else root.RoofOrtho = m; })(this, function () {
  'use strict';
  var VERSION = '0.1.7.4-ortho-2';
  function world(lon, lat, z) { var n = Math.pow(2, z) * 256, s = Math.sin(lat * Math.PI / 180);
    return [(lon + 180) / 360 * n, (0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)) * n]; }
  function unworld(x, y, z) { var n = Math.pow(2, z) * 256, lon = x / n * 360 - 180, t = Math.PI - 2 * Math.PI * y / n;
    return [lon, 180 / Math.PI * Math.atan(0.5 * (Math.exp(t) - Math.exp(-t)))]; }
  function mpp(lat, z) { return 156543.03392 * Math.cos(lat * Math.PI / 180) / Math.pow(2, z); }

  /** tiles: [{tx, ty, data: Uint8Array}] -> Promise<{gray, W, H, ox, oy, z}> (ox, oy = world px of the mosaic origin) */
  function mosaic(z, tiles) {
    var ok = tiles.filter(function (t) { return t && t.data; });
    if (!ok.length) return Promise.reject(new Error('no tiles'));
    var x0 = Math.min.apply(null, ok.map(function (t) { return t.tx; })), x1 = Math.max.apply(null, ok.map(function (t) { return t.tx; }));
    var y0 = Math.min.apply(null, ok.map(function (t) { return t.ty; })), y1 = Math.max.apply(null, ok.map(function (t) { return t.ty; }));
    var W = (x1 - x0 + 1) * 256, H = (y1 - y0 + 1) * 256;
    var cv = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(W, H) : Object.assign(document.createElement('canvas'), { width: W, height: H });
    var ctx = cv.getContext('2d');
    return Promise.all(ok.map(function (t) {
      var mt = t.data[0] === 0x89 ? 'image/png' : 'image/jpeg';
      return createImageBitmap(new Blob([t.data], { type: mt })).then(function (bm) { ctx.drawImage(bm, (t.tx - x0) * 256, (t.ty - y0) * 256); }, function () { /* missing tile stays black */ });
    })).then(function () {
      var d = ctx.getImageData(0, 0, W, H).data, g = new Float32Array(W * H);
      for (var i = 0, j = 0; i < g.length; i++, j += 4) g[i] = 0.299 * d[j] + 0.587 * d[j + 1] + 0.114 * d[j + 2];
      return { gray: g, W: W, H: H, ox: x0 * 256, oy: y0 * 256, z: z };
    });
  }
  function sobel(m) {
    var W = m.W, H = m.H, g = m.gray, gx = new Float32Array(W * H), gy = new Float32Array(W * H);
    for (var y = 1; y < H - 1; y++) for (var x = 1; x < W - 1; x++) {
      var i = y * W + x;
      gx[i] = (g[i - W + 1] + 2 * g[i + 1] + g[i + W + 1]) - (g[i - W - 1] + 2 * g[i - 1] + g[i + W - 1]);
      gy[i] = (g[i + W - 1] + 2 * g[i + W] + g[i + W + 1]) - (g[i - W - 1] + 2 * g[i - W] + g[i - W + 1]);
    }
    m.gx = gx; m.gy = gy; return m;
  }
  function bil(a, W, H, x, y) {
    if (x < 1 || y < 1 || x >= W - 2 || y >= H - 2) return NaN;
    var xi = x | 0, yi = y | 0, fx = x - xi, fy = y - yi, i = yi * W + xi;
    return a[i] * (1 - fx) * (1 - fy) + a[i + 1] * fx * (1 - fy) + a[i + W] * (1 - fx) * fy + a[i + W + 1] * fx * fy;
  }
  function edgeSamples(ringLL, m) {
    var P = ringLL.map(function (p) { var w = world(p[0], p[1], m.z); return [w[0] - m.ox, w[1] - m.oy]; });
    if (P.length > 2 && P[0][0] === P[P.length - 1][0] && P[0][1] === P[P.length - 1][1]) P.pop();
    var A = 0; for (var k = 0; k < P.length; k++) { var a = P[k], b = P[(k + 1) % P.length]; A += a[0] * b[1] - b[0] * a[1]; }
    var sgn = A > 0 ? 1 : -1, S = [], edges = [];
    for (var i = 0; i < P.length; i++) {
      var p = P[i], q = P[(i + 1) % P.length], dx = q[0] - p[0], dy = q[1] - p[1], L = Math.hypot(dx, dy);
      if (L < 6) continue;
      var nx = dy / L * sgn, ny = -dx / L * sgn, n = Math.max(3, Math.floor(L * 0.8 / 2)), es = [];
      for (var t = 0; t < n; t++) { var f = 0.1 + 0.8 * (t + 0.5) / n; es.push([p[0] + dx * f, p[1] + dy * f, nx, ny]); }
      S = S.concat(es); edges.push({ i: i, len_px: L, s: es });
    }
    return { S: S, edges: edges, P: P };
  }
  function score0(m, S, dx, dy) {
    var s = 0, n = 0;
    for (var k = 0; k < S.length; k++) { var p = S[k], a = bil(m.gx, m.W, m.H, p[0] + dx, p[1] + dy); if (a !== a) continue;
      var b = bil(m.gy, m.W, m.H, p[0] + dx, p[1] + dy); s += Math.abs(a * p[2] + b * p[3]); n++; }
    return n >= S.length * 0.6 ? s / n : 0;
  }
  /** interior roof lines (ridge / hip / valley, [[lon,lat],[lon,lat]]) -> samples with the line normal */
  function lineSamples(lines, m) {
    var S = [];
    (lines || []).forEach(function (ln) {
      var p = world(ln[0][0], ln[0][1], m.z), q = world(ln[1][0], ln[1][1], m.z); p = [p[0] - m.ox, p[1] - m.oy]; q = [q[0] - m.ox, q[1] - m.oy];
      var dx = q[0] - p[0], dy = q[1] - p[1], L = Math.hypot(dx, dy); if (L < 6) return;
      var n = Math.max(3, Math.floor(L * 0.8 / 2));
      for (var t = 0; t < n; t++) { var f = 0.1 + 0.8 * (t + 0.5) / n; S.push([p[0] + dx * f, p[1] + dy * f, dy / L, -dx / L]); }
    });
    return S;
  }
  function para(a, b, c) { var d = a - 2 * b + c; return d < 0 ? Math.max(-0.5, Math.min(0.5, 0.5 * (a - c) / d)) : 0; }

  /** -> {dx_px, dy_px (world px; ortho roof = roofprint + d), dx_m (east +), dy_m (north +), shift_m, ratio, sep, confidence, applied, residuals} */
  function align(ringLL, m, opts) {
    opts = opts || {};
    if (!m.gx) sobel(m);
    var lat = ringLL[0][1], res = mpp(lat, m.z), R = Math.round((opts.max_shift_m || 8) / res);
    var es = edgeSamples(ringLL, m), S0 = es.S, LS = lineSamples(opts.lines, m), WL = LS.length >= 10 ? (opts.line_weight || 1) : 0;
    if (S0.length < 20) return { version: VERSION, status: 'too_small', applied: false };
    // score = outline gradient + interior-line gradient (a sunlit / shaded facet pair makes the ridge the strongest edge; without it
    // the search can lock an eave onto the ridge's light/dark boundary), times a mild prior against large shifts
    var S = { length: S0.length };
    var score = function (m, SS, dx, dy) {
      if (SS !== S) return score0(m, SS, dx, dy);
      var v = score0(m, S0, dx, dy); if (WL) v = (v + WL * score0(m, LS, dx, dy)) / (1 + WL);
      return v * (1 - 0.015 * Math.hypot(dx, dy) * res);
    };
    var grid = [], best = { s: -1 }, vals = [];
    for (var dy = -R; dy <= R; dy += 2) for (var dx = -R; dx <= R; dx += 2) { var v = score(m, S, dx, dy); grid.push([dx, dy, v]); vals.push(v); if (v > best.s) best = { s: v, dx: dx, dy: dy }; }
    for (dy = best.dy - 2; dy <= best.dy + 2; dy++) for (dx = best.dx - 2; dx <= best.dx + 2; dx++) { v = score(m, S, dx, dy); if (v > best.s) best = { s: v, dx: dx, dy: dy }; }
    var sx = para(score(m, S, best.dx - 1, best.dy), best.s, score(m, S, best.dx + 1, best.dy));
    var sy = para(score(m, S, best.dx, best.dy - 1), best.s, score(m, S, best.dx, best.dy + 1));
    var fx = best.dx + sx, fy = best.dy + sy, sBest = score(m, S, fx, fy) || best.s;
    vals.sort(function (a, b) { return a - b; });
    var med = vals[vals.length >> 1] || 1, ex = 1.5 / res, second = 0;
    grid.forEach(function (g) { if (Math.hypot(g[0] - fx, g[1] - fy) > ex && g[2] > second) second = g[2]; });
    var s0 = score(m, S, 0, 0), ratio = sBest / med, sep = second ? sBest / second : 9;
    var atEdge = Math.abs(fx) >= R - 1 || Math.abs(fy) >= R - 1;
    var confidence = atEdge ? 'low' : (ratio >= 1.6 && sep >= 1.12) ? 'high' : (ratio >= 1.3 && sep >= 1.04) ? 'medium' : 'low';
    var applied = confidence !== 'low' && opts.apply !== false;
    var ux = applied ? fx : 0, uy = applied ? fy : 0;
    // per-edge residual after the global shift (1-D search along each edge normal, +-2 m)
    var Rr = Math.round(2 / res), residuals = es.edges.map(function (e) {
      var bt = 0, bs = -1, nx = e.s[0][2], ny = e.s[0][3];
      for (var t = -Rr; t <= Rr; t += 0.5) { var v2 = score0(m, e.s, ux + nx * t, uy + ny * t); if (v2 > bs) { bs = v2; bt = t; } }
      var edgeHit = Math.abs(bt) < Rr - 0.5; // a best offset on the search bound = no clear edge in the photo for this side
      return { edge: e.i, residual_m: edgeHit ? Math.round(bt * res * 100) / 100 : null, no_clear_edge: !edgeHit, length_m: Math.round(e.len_px * res * 10) / 10 };
    });
    var absr = residuals.filter(function (r) { return r.residual_m != null; }).map(function (r) { return Math.abs(r.residual_m); }).sort(function (a, b) { return a - b; });
    return { version: VERSION, status: 'ok', z: m.z, m_per_px: Math.round(res * 1000) / 1000, search_m: Math.round(R * res * 10) / 10,
      dx_px: Math.round(fx * 100) / 100, dy_px: Math.round(fy * 100) / 100, dx_m: Math.round(fx * res * 100) / 100, dy_m: Math.round(-fy * res * 100) / 100,
      shift_m: Math.round(Math.hypot(fx, fy) * res * 100) / 100, score0: Math.round(s0), score: Math.round(sBest), gain: Math.round(sBest / (s0 || 1) * 100) / 100,
      ratio: Math.round(ratio * 100) / 100, sep: Math.round(sep * 100) / 100, confidence: confidence, applied: applied,
      residual_median_m: absr.length ? absr[absr.length >> 1] : null, residual_max_m: absr.length ? absr[absr.length - 1] : null, edges_no_clear_edge: residuals.length - absr.length, residuals: residuals,
      method: 'bounded 2-D translation search (±' + Math.round(R * res * 10) / 10 + ' m) maximising ortho gradient along the roofprint edges' + (WL ? ' and ' + (opts.lines || []).length + ' ridge/hip/valley lines' : '') + '; per-edge 1-D residual ±2 m',
      interior_lines: WL ? (opts.lines || []).length : 0 };
  }

  /** Skylight / chimney / vent candidates: compact bright or dark rectangles inside the (shifted) roof. */
  function patches(ringLL, m, al, opts) {
    opts = opts || {};
    var lat = ringLL[0][1], res = mpp(lat, m.z), sx = al && al.applied ? al.dx_px : 0, sy = al && al.applied ? al.dy_px : 0;
    var es = edgeSamples(ringLL, m), P = es.P.map(function (p) { return [p[0] + sx, p[1] + sy]; });
    var xs = P.map(function (p) { return p[0]; }), ys = P.map(function (p) { return p[1]; });
    var X0 = Math.max(2, Math.floor(Math.min.apply(null, xs))), X1 = Math.min(m.W - 3, Math.ceil(Math.max.apply(null, xs)));
    var Y0 = Math.max(2, Math.floor(Math.min.apply(null, ys))), Y1 = Math.min(m.H - 3, Math.ceil(Math.max.apply(null, ys)));
    if (X1 - X0 < 8 || Y1 - Y0 < 8) return [];
    function inside(x, y) { var c = false; for (var i = 0, j = P.length - 1; i < P.length; j = i++) { var a = P[i], b = P[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
    function dEdge(x, y) { var d = 1e9; for (var i = 0, j = P.length - 1; i < P.length; j = i++) { var a = P[i], b = P[j], vx = b[0] - a[0], vy = b[1] - a[1], L2 = vx * vx + vy * vy || 1,
      t = Math.max(0, Math.min(1, ((x - a[0]) * vx + (y - a[1]) * vy) / L2)); d = Math.min(d, Math.hypot(x - a[0] - t * vx, y - a[1] - t * vy)); } return d; }
    var W = X1 - X0 + 1, H = Y1 - Y0 + 1, inm = new Uint8Array(W * H), g = m.gray, inset = 0.7 / res;
    // integral image for a local mean (radius ~2.5 m) over roof pixels only
    var I = new Float64Array((W + 1) * (H + 1)), C = new Float64Array((W + 1) * (H + 1));
    for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) {
      var ins = inside(X0 + x + 0.5, Y0 + y + 0.5) && dEdge(X0 + x + 0.5, Y0 + y + 0.5) > inset ? 1 : 0; inm[y * W + x] = ins;
      var v = ins ? g[(Y0 + y) * m.W + X0 + x] : 0, k = (y + 1) * (W + 1) + x + 1;
      I[k] = v + I[k - 1] + I[k - W - 1] - I[k - W - 2]; C[k] = ins + C[k - 1] + C[k - W - 1] - C[k - W - 2];
    }
    var r = Math.max(4, Math.round(2.5 / res)), diff = new Float32Array(W * H), dl = [];
    for (y = 0; y < H; y++) for (x = 0; x < W; x++) { if (!inm[y * W + x]) continue;
      var xa = Math.max(0, x - r), xb = Math.min(W, x + r + 1), ya = Math.max(0, y - r), yb = Math.min(H, y + r + 1);
      var s = I[yb * (W + 1) + xb] - I[ya * (W + 1) + xb] - I[yb * (W + 1) + xa] + I[ya * (W + 1) + xa];
      var c = C[yb * (W + 1) + xb] - C[ya * (W + 1) + xb] - C[yb * (W + 1) + xa] + C[ya * (W + 1) + xa];
      var dv = g[(Y0 + y) * m.W + X0 + x] - s / Math.max(1, c); diff[y * W + x] = dv; dl.push(Math.abs(dv)); }
    if (dl.length < 50) return [];
    dl.sort(function (a, b) { return a - b; });
    var mad = Math.max(4, dl[dl.length >> 1] * 1.4826), K = opts.k || 3.2, lab = new Int32Array(W * H).fill(-1), comps = [];
    for (y = 0; y < H; y++) for (x = 0; x < W; x++) {
      var i0 = y * W + x; if (!inm[i0] || lab[i0] >= 0 || Math.abs(diff[i0]) < K * mad) continue;
      var pol = diff[i0] > 0 ? 1 : -1, st = [i0], mem = []; lab[i0] = comps.length;
      while (st.length) { var q = st.pop(); mem.push(q); var qx = q % W, qy = (q / W) | 0;
        [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (o) { var nx = qx + o[0], ny = qy + o[1]; if (nx < 0 || ny < 0 || nx >= W || ny >= H) return; var j = ny * W + nx;
          if (lab[j] >= 0 || !inm[j] || diff[j] * pol < K * 0.6 * mad) return; lab[j] = comps.length; st.push(j); }); }
      comps.push({ pol: pol, mem: mem });
    }
    var out = [];
    comps.forEach(function (cpt) {
      var n = cpt.mem.length, area = n * res * res; if (area < 0.3 || area > 4.5) return;
      var mx = 0, my = 0, ct = 0; cpt.mem.forEach(function (q) { mx += q % W; my += (q / W) | 0; ct += Math.abs(diff[q]); }); mx /= n; my /= n;
      var sxx = 0, syy = 0, sxy = 0; cpt.mem.forEach(function (q) { var a = q % W - mx, b = ((q / W) | 0) - my; sxx += a * a; syy += b * b; sxy += a * b; });
      var th = 0.5 * Math.atan2(2 * sxy, sxx - syy), u = [Math.cos(th), Math.sin(th)], lo = [1e9, 1e9], hi = [-1e9, -1e9];
      cpt.mem.forEach(function (q) { var a = q % W - mx, b = ((q / W) | 0) - my, s1 = a * u[0] + b * u[1], s2 = -a * u[1] + b * u[0];
        lo[0] = Math.min(lo[0], s1); hi[0] = Math.max(hi[0], s1); lo[1] = Math.min(lo[1], s2); hi[1] = Math.max(hi[1], s2); });
      var w = (hi[0] - lo[0] + 1) * res, h = (hi[1] - lo[1] + 1) * res, fill = area / (w * h), asp = Math.max(w, h) / Math.min(w, h);
      if (fill < 0.55 || asp > 3.5 || Math.min(w, h) < 0.45) return;
      var ll = unworld(X0 + mx + 0.5 - sx + m.ox, Y0 + my + 0.5 - sy + m.oy, m.z); // back to roofprint coordinates
      out.push({ centroid_lonlat: [Math.round(ll[0] * 1e7) / 1e7, Math.round(ll[1] * 1e7) / 1e7], approx_w_ft: Math.round(Math.max(w, h) * 3.2808 * 10) / 10,
        approx_h_ft: Math.round(Math.min(w, h) * 3.2808 * 10) / 10, approx_area_sqft: Math.round(area * 10.764), polarity: cpt.pol > 0 ? 'bright' : 'dark',
        contrast: Math.round(ct / n / mad * 10) / 10, rectangularity: Math.round(fill * 100) / 100, source: 'ortho patch', confidence: 'low' });
    });
    out.sort(function (a, b) { return b.contrast - a.contrast; });
    return out.slice(0, opts.max || 8);
  }
  return { VERSION: VERSION, world: world, unworld: unworld, mpp: mpp, mosaic: mosaic, sobel: sobel, align: align, patches: patches };
});
