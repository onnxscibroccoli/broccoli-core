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
  var VERSION = '0.1.7.6-ortho-5';
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

  /** 0.1.7.6: lidar building mask (class-6 points, [lon, lat]) on a cell grid in mosaic pixels.
   * -> {cell (px), gx0, gy0, GW, GH, occ (Uint8Array), samples [[x, y, nx, ny]] on the mask boundary (outward normal), area_m2} */
  function lidarMask(ptsLL, m, opts) {
    opts = opts || {};
    if (!ptsLL || ptsLL.length < 30) return null;
    var lat = ptsLL[0][1], res = mpp(lat, m.z), c = (opts.cell_m || 0.5) / res, xs = [], ys = [];
    ptsLL.forEach(function (p) { var w = world(p[0], p[1], m.z); xs.push(w[0] - m.ox); ys.push(w[1] - m.oy); });
    var gx0 = Math.min.apply(null, xs) - 3 * c, gy0 = Math.min.apply(null, ys) - 3 * c;
    var GW = Math.ceil((Math.max.apply(null, xs) - gx0) / c) + 4, GH = Math.ceil((Math.max.apply(null, ys) - gy0) / c) + 4;
    if (GW * GH > 4e6) return null;
    var occ = new Uint8Array(GW * GH);
    for (var i = 0; i < xs.length; i++) occ[Math.floor((ys[i] - gy0) / c) * GW + Math.floor((xs[i] - gx0) / c)] = 1;
    function morph(a, dil) { var b = new Uint8Array(GW * GH);
      for (var y = 1; y < GH - 1; y++) for (var x = 1; x < GW - 1; x++) { var i = y * GW + x, v = a[i];
        if (dil) v = a[i] | a[i - 1] | a[i + 1] | a[i - GW] | a[i + GW]; else v = a[i] & a[i - 1] & a[i + 1] & a[i - GW] & a[i + GW]; b[i] = v; }
      return b; }
    occ = morph(morph(occ, true), false); // close 1 cell (fills point gaps)
    // keep connected components that touch opts.keepNear ([x, y] mosaic px points, e.g. the roofprint ring), else the largest
    var lab = new Int32Array(GW * GH).fill(-1), comps = [];
    for (var q0 = 0; q0 < GW * GH; q0++) { if (!occ[q0] || lab[q0] >= 0) continue; var st = [q0], n = 0; lab[q0] = comps.length;
      while (st.length) { var q = st.pop(); n++; [1, -1, GW, -GW].forEach(function (o) { var j = q + o; if (j >= 0 && j < GW * GH && occ[j] && lab[j] < 0) { lab[j] = comps.length; st.push(j); } }); }
      comps.push(n); }
    var keep = {};
    if (opts.keepNear) opts.keepNear.forEach(function (p) { var cx = Math.floor((p[0] - gx0) / c), cy = Math.floor((p[1] - gy0) / c);
      for (var dy = -2; dy <= 2; dy++) for (var dx = -2; dx <= 2; dx++) { var x = cx + dx, y = cy + dy; if (x >= 0 && y >= 0 && x < GW && y < GH && lab[y * GW + x] >= 0) keep[lab[y * GW + x]] = 1; } });
    if (!Object.keys(keep).length) { var bi = 0; comps.forEach(function (n, k) { if (n > comps[bi]) bi = k; }); keep[bi] = 1; }
    var area = 0;
    for (q0 = 0; q0 < GW * GH; q0++) { if (occ[q0] && !keep[lab[q0]]) occ[q0] = 0; if (occ[q0]) area++; }
    var S = [];
    for (var y = 1; y < GH - 1; y++) for (var x = 1; x < GW - 1; x++) { var k = y * GW + x; if (!occ[k]) continue;
      var nx = 0, ny = 0; for (var dy2 = -2; dy2 <= 2; dy2++) for (var dx2 = -2; dx2 <= 2; dx2++) { var X = x + dx2, Y = y + dy2;
        if (X < 0 || Y < 0 || X >= GW || Y >= GH) continue; if (!occ[Y * GW + X]) { nx += dx2; ny += dy2; } }
      if (!(occ[k - 1] && occ[k + 1] && occ[k - GW] && occ[k + GW])) { var L = Math.hypot(nx, ny); if (L < 1) continue;
        nx /= L; ny /= L; S.push([gx0 + (x + 0.5) * c + nx * c * 0.5, gy0 + (y + 0.5) * c + ny * c * 0.5, nx, ny]); } }
    return { cell: c, gx0: gx0, gy0: gy0, GW: GW, GH: GH, occ: occ, samples: S, area_m2: area * c * c * res * res, res: res };
  }
  /** 0.1.7.6: roofprint (mosaic px polygon P) vs lidar mask: best translation (IoU), and lidar building area outside the roofprint. */
  function outlineVsMask(P, M, opts) {
    opts = opts || {};
    var c = M.cell, res = M.res, R = Math.round((opts.max_shift_m || 4) / (c * res) * 2) / 2;
    function inP(x, y, dx, dy) { var ins = false; for (var i = 0, j = P.length - 1; i < P.length; j = i++) { var a = P[i], b = P[j], ay = a[1] + dy, by = b[1] + dy;
      if ((ay > y) !== (by > y) && x < (b[0] - a[0]) * (y - ay) / (by - ay) + a[0] + dx) ins = !ins; } return ins; }
    // ring raster at the cell centres (cells of the mask grid), for integer-cell shifts
    var ringCells = [];
    for (var y = 0; y < M.GH; y++) for (var x = 0; x < M.GW; x++) if (inP(M.gx0 + (x + 0.5) * c, M.gy0 + (y + 0.5) * c, 0, 0)) ringCells.push([x, y]);
    if (ringCells.length < 20) return null;
    var occN = 0; for (var q = 0; q < M.occ.length; q++) occN += M.occ[q];
    function iou(sx, sy) { var hit = 0; ringCells.forEach(function (p) { var X = p[0] + sx, Y = p[1] + sy; if (X >= 0 && Y >= 0 && X < M.GW && Y < M.GH && M.occ[Y * M.GW + X]) hit++; });
      return hit / (ringCells.length + occN - hit); }
    var best = { v: -1, x: 0, y: 0 }, i0 = iou(0, 0), Rc = Math.max(1, Math.round(R));
    for (var sy = -Rc; sy <= Rc; sy++) for (var sx = -Rc; sx <= Rc; sx++) { var v = iou(sx, sy) * (1 - 0.01 * Math.hypot(sx, sy) * c * res); if (v > best.v) best = { v: v, x: sx, y: sy }; }
    // lidar building cells farther than 1.5 m outside the (best-shifted) roofprint = building the roofprint does not cover
    var inR = new Uint8Array(M.GW * M.GH); ringCells.forEach(function (p) { var X = p[0] + best.x, Y = p[1] + best.y; if (X >= 0 && Y >= 0 && X < M.GW && Y < M.GH) inR[Y * M.GW + X] = 1; });
    var dil = inR, k = Math.round(1.5 / (c * res));
    for (var t = 0; t < k; t++) { var b2 = new Uint8Array(M.GW * M.GH); for (var y2 = 1; y2 < M.GH - 1; y2++) for (var x2 = 1; x2 < M.GW - 1; x2++) { var j = y2 * M.GW + x2; b2[j] = dil[j] | dil[j - 1] | dil[j + 1] | dil[j - M.GW] | dil[j + M.GW]; } dil = b2; }
    var out = 0; for (q = 0; q < M.occ.length; q++) if (M.occ[q] && !dil[q]) out++;
    var cm = c * res;
    return { dx_px: best.x * c, dy_px: best.y * c, dx_m: Math.round(best.x * cm * 100) / 100, dy_m: Math.round(-best.y * cm * 100) / 100, shift_m: Math.round(Math.hypot(best.x, best.y) * cm * 100) / 100,
      iou0: Math.round(i0 * 1000) / 1000, iou: Math.round(iou(best.x, best.y) * 1000) / 1000, at_limit: Math.abs(best.x) >= Rc || Math.abs(best.y) >= Rc,
      lidar_area_sqft: Math.round(occN * cm * cm * 10.764), roofprint_area_sqft: Math.round(ringCells.length * cm * cm * 10.764), outside_area_sqft: Math.round(out * cm * cm * 10.764) };
  }

  /** 0.1.7.6: region alignment. cells: [[x, y, label]] in mosaic px (labels = lidar roof planes, plus 'ground' cells).
   * For each translation d, sample the ortho at cell + d and score the correlation ratio eta^2 = between-label variance /
   * total variance: each roof plane faces the sun differently, so the planes are uniform patches of different brightness.
   * Much harder to fool than edge gradients (shadows, fences, porch edges). -> {dx_px, dy_px, eta0, eta, ratio, sep, confidence} */
  function etaFn(cells, m) {
    var labs = {}, nl = 0, L = new Int32Array(cells.length); cells.forEach(function (c, i) { if (!(c[2] in labs)) labs[c[2]] = nl++; L[i] = labs[c[2]]; });
    if (nl < 2) return null;
    var g = m.gray, W = m.W, H = m.H;
    if (!m.blur) { var b = new Float32Array(W * H); for (var y = 1; y < H - 1; y++) for (var x = 1; x < W - 1; x++) { var i = y * W + x;
      b[i] = (g[i] * 4 + g[i - 1] + g[i + 1] + g[i - W] + g[i + W]) / 8; } m.blur = b; }
    var B = m.blur, S = new Float64Array(nl), N = new Float64Array(nl);
    var f = function (dx, dy) { S.fill(0); N.fill(0); var tot = 0, tot2 = 0, n = 0;
      for (var k = 0; k < cells.length; k++) { var v = bil(B, W, H, cells[k][0] + dx, cells[k][1] + dy); if (v !== v) continue; S[L[k]] += v; N[L[k]]++; tot += v; tot2 += v * v; n++; }
      if (n < cells.length * 0.8) return 0; var mu = tot / n, vt = tot2 / n - mu * mu; if (vt <= 1e-6) return 0;
      var vb = 0; for (var j = 0; j < nl; j++) if (N[j]) { var mj = S[j] / N[j]; vb += N[j] * (mj - mu) * (mj - mu); }
      return vb / n / vt; };
    f.labels = nl; return f;
  }
  function regionAlign(cells, m, opts) {
    opts = opts || {};
    if (!cells || cells.length < 60) return null;
    var lat = opts.lat || 42, res = mpp(lat, m.z), R = Math.round((opts.max_shift_m || 8) / res), labs = {}, nl = 0;
    var L = new Int32Array(cells.length); cells.forEach(function (c, i) { if (!(c[2] in labs)) labs[c[2]] = nl++; L[i] = labs[c[2]]; });
    if (nl < 2) return null;
    var g = m.gray, W = m.W, H = m.H;
    if (!m.blur) { var b = new Float32Array(W * H); for (var y = 1; y < H - 1; y++) for (var x = 1; x < W - 1; x++) { var i = y * W + x;
      b[i] = (g[i] * 4 + g[i - 1] + g[i + 1] + g[i - W] + g[i + W]) / 8; } m.blur = b; }
    var B = m.blur, S = new Float64Array(nl), Q = new Float64Array(nl), N = new Float64Array(nl);
    function eta(dx, dy) { S.fill(0); N.fill(0); var tot = 0, tot2 = 0, n = 0;
      for (var k = 0; k < cells.length; k++) { var v = bil(B, W, H, cells[k][0] + dx, cells[k][1] + dy); if (v !== v) continue; S[L[k]] += v; N[L[k]]++; tot += v; tot2 += v * v; n++; }
      if (n < cells.length * 0.8) return 0; var mu = tot / n, vt = tot2 / n - mu * mu; if (vt <= 1e-6) return 0;
      var vb = 0; for (var j = 0; j < nl; j++) if (N[j]) { var mj = S[j] / N[j]; vb += N[j] * (mj - mu) * (mj - mu); }
      return vb / n / vt * (1 - 0.01 * Math.hypot(dx, dy) * res); }
    var best = { v: -1, x: 0, y: 0 }, grid = [];
    for (var dy = -R; dy <= R; dy += 2) for (var dx = -R; dx <= R; dx += 2) { var v = eta(dx, dy); grid.push([dx, dy, v]); if (v > best.v) best = { v: v, x: dx, y: dy }; }
    for (dy = best.y - 2; dy <= best.y + 2; dy += 0.5) for (dx = best.x - 2; dx <= best.x + 2; dx += 0.5) { v = eta(dx, dy); if (v > best.v) best = { v: v, x: dx, y: dy }; }
    var vals = grid.map(function (q) { return q[2]; }).sort(function (a, b2) { return a - b2; }), med = vals[vals.length >> 1] || 1e-6, ex = 1.5 / res, second = 0;
    grid.forEach(function (q) { if (Math.hypot(q[0] - best.x, q[1] - best.y) > ex && q[2] > second) second = q[2]; });
    var e0 = eta(0, 0), ratio = best.v / med, sep = second ? best.v / second : 9, atEdge = Math.abs(best.x) >= R - 1 || Math.abs(best.y) >= R - 1;
    var confidence = atEdge ? 'low' : (best.v >= 0.25 && sep >= 1.1) ? 'high' : (best.v >= 0.15 && sep >= 1.04) ? 'medium' : 'low';
    return { dx_px: best.x, dy_px: best.y, dx_m: Math.round(best.x * res * 100) / 100, dy_m: Math.round(-best.y * res * 100) / 100, shift_m: Math.round(Math.hypot(best.x, best.y) * res * 100) / 100,
      eta0: Math.round(e0 * 1000) / 1000, eta: Math.round(best.v * 1000) / 1000, ratio: Math.round(ratio * 100) / 100, sep: Math.round(sep * 100) / 100, confidence: confidence, labels: nl, cells: cells.length, at_limit: atEdge };
  }
  function para(a, b, c) { var d = a - 2 * b + c; return d < 0 ? Math.max(-0.5, Math.min(0.5, 0.5 * (a - c) / d)) : 0; }

  /** -> {dx_px, dy_px (world px; ortho roof = roofprint + d), dx_m (east +), dy_m (north +), shift_m, ratio, sep, confidence, applied, residuals} */
  function align(ringLL, m, opts) {
    opts = opts || {};
    if (!m.gx) sobel(m);
    var lat = ringLL[0][1], res = mpp(lat, m.z), R = Math.round((opts.max_shift_m || 8) / res);
    var es = edgeSamples(ringLL, m), S0 = opts.samples && opts.samples.length >= 40 ? opts.samples : es.S, LS = lineSamples(opts.lines, m), WL = LS.length >= 10 ? (opts.line_weight || 1) : 0;
    if (S0.length < 20) return { version: VERSION, status: 'too_small', applied: false };
    // score = outline gradient + interior-line gradient (a sunlit / shaded facet pair makes the ridge the strongest edge; without it
    // the search can lock an eave onto the ridge's light/dark boundary), times a mild prior against large shifts
    var ETA = opts.cells && opts.cells.length >= 60 ? etaFn(opts.cells, m) : null;
    // 0.1.7.6: the lidar-plane region score (eta^2) is reported as a cross-check only. Tried as a score factor: it moved
    // 6 Harborview Rd 5 m off the roof (shading of the roof deck walls), so the edge score alone decides the shift.
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
      method: 'bounded 2-D translation search (±' + Math.round(R * res * 10) / 10 + ' m) maximising ortho gradient along the roofprint edges' + (WL ? ' and ' + (opts.lines || []).length + ' ridge/hip/valley lines' : '') + (ETA ? '; cross-check: brightness separation of the ' + ETA.labels + ' lidar roof planes (eta^2) at 0 and at the shift' : '') + '; per-edge 1-D residual ±2 m',
      interior_lines: WL ? (opts.lines || []).length : 0, region: ETA ? { labels: ETA.labels, cells: opts.cells.length, eta0: Math.round(ETA(0, 0) * 1000) / 1000, eta: Math.round(ETA(fx, fy) * 1000) / 1000 } : null };
  }

  /** Skylight / chimney / vent candidates: compact bright or dark rectangles inside the (shifted) roof. */
  /** 0.1.7.6: edge-preserving bilateral smoothing (5 x 5, sigma_s 1.5 px, sigma_r 12 grey levels) of the roof window only; keeps
   * 2-3 px skylight frames that a Gaussian blur would wash out (pipeline spec, docs/research/lidar_pipeline_spec.md). */
  function bilateral(m, X0, Y0, X1, Y1) {
    var g = m.gray, W = m.W, out = new Float32Array(g), ws = [];
    for (var dy = -2; dy <= 2; dy++) for (var dx = -2; dx <= 2; dx++) ws.push([dx, dy, Math.exp(-(dx * dx + dy * dy) / (2 * 1.5 * 1.5))]);
    for (var y = Math.max(2, Y0 - 2); y <= Math.min(m.H - 3, Y1 + 2); y++) for (var x = Math.max(2, X0 - 2); x <= Math.min(W - 3, X1 + 2); x++) {
      var c = g[y * W + x], sw = 0, sv = 0;
      for (var k = 0; k < ws.length; k++) { var v = g[(y + ws[k][1]) * W + x + ws[k][0]], d = v - c, w = ws[k][2] * Math.exp(-d * d / (2 * 144)); sw += w; sv += w * v; }
      out[y * W + x] = sv / sw; }
    return out;
  }
  function patches(ringLL, m, al, opts) {
    opts = opts || {};
    var lat = ringLL[0][1], res = mpp(lat, m.z), zf = al && al.z ? Math.pow(2, m.z - al.z) : 1, sx = al && al.applied ? al.dx_px * zf : 0, sy = al && al.applied ? al.dy_px * zf : 0;
    var es = edgeSamples(ringLL, m), P = es.P.map(function (p) { return [p[0] + sx, p[1] + sy]; });
    var xs = P.map(function (p) { return p[0]; }), ys = P.map(function (p) { return p[1]; });
    var X0 = Math.max(2, Math.floor(Math.min.apply(null, xs))), X1 = Math.min(m.W - 3, Math.ceil(Math.max.apply(null, xs)));
    var Y0 = Math.max(2, Math.floor(Math.min.apply(null, ys))), Y1 = Math.min(m.H - 3, Math.ceil(Math.max.apply(null, ys)));
    if (X1 - X0 < 8 || Y1 - Y0 < 8) return [];
    function inside(x, y) { var c = false; for (var i = 0, j = P.length - 1; i < P.length; j = i++) { var a = P[i], b = P[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
    function dEdge(x, y) { var d = 1e9; for (var i = 0, j = P.length - 1; i < P.length; j = i++) { var a = P[i], b = P[j], vx = b[0] - a[0], vy = b[1] - a[1], L2 = vx * vx + vy * vy || 1,
      t = Math.max(0, Math.min(1, ((x - a[0]) * vx + (y - a[1]) * vy) / L2)); d = Math.min(d, Math.hypot(x - a[0] - t * vx, y - a[1] - t * vy)); } return d; }
    var W = X1 - X0 + 1, H = Y1 - Y0 + 1, inm = new Uint8Array(W * H), g = opts.bilateral === false ? m.gray : bilateral(m, X0, Y0, X1, Y1), inset = 0.7 / res;
    // 0.1.7.5: per-facet background. A sunlit and a shaded facet differ a lot, so a skylight is dark on a sunlit facet and
    // bright (glare) on a shaded one; compare each pixel with its OWN facet's median / MAD, away from facet boundaries.
    var FP = (opts.facets || []).map(function (poly) { return poly.map(function (p) { var w = world(p[0], p[1], m.z); return [w[0] - m.ox + sx, w[1] - m.oy + sy]; }); });
    function inP(P2, x, y) { var c = false; for (var i = 0, j = P2.length - 1; i < P2.length; j = i++) { var a = P2[i], b = P2[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
    function dP(P2, x, y) { var d = 1e9; for (var i = 0, j = P2.length - 1; i < P2.length; j = i++) { var a = P2[i], b = P2[j], vx = b[0] - a[0], vy = b[1] - a[1], L2 = vx * vx + vy * vy || 1,
      t = Math.max(0, Math.min(1, ((x - a[0]) * vx + (y - a[1]) * vy) / L2)); d = Math.min(d, Math.hypot(x - a[0] - t * vx, y - a[1] - t * vy)); } return d; }
    if (FP.length) {
      var fid = new Int16Array(W * H).fill(-1), vals = FP.map(function () { return []; }), fin = 0.45 / res;
      for (var yy = 0; yy < H; yy++) for (var xx = 0; xx < W; xx++) { var px = X0 + xx + 0.5, py = Y0 + yy + 0.5;
        for (var f = 0; f < FP.length; f++) if (inP(FP[f], px, py)) { if (dP(FP[f], px, py) > fin && dEdge(px, py) > 0.3 / res) { fid[yy * W + xx] = f; vals[f].push(g[(Y0 + yy) * m.W + X0 + xx]); } break; } }
      var med = vals.map(function (v) { if (v.length < 40) return null; var a = v.slice().sort(function (x, y) { return x - y; }); return a[a.length >> 1]; });
      var madF = vals.map(function (v, f) { if (med[f] == null) return null; var a = v.map(function (x) { return Math.abs(x - med[f]); }).sort(function (x, y) { return x - y; }); return Math.max(4, a[a.length >> 1] * 1.4826); });
      var diffF = new Float32Array(W * H), madPix = new Float32Array(W * H);
      for (var q0 = 0; q0 < W * H; q0++) { var fi = fid[q0]; if (fi < 0 || med[fi] == null) continue; inm[q0] = 1; diffF[q0] = g[(Y0 + ((q0 / W) | 0)) * m.W + X0 + q0 % W] - med[fi]; madPix[q0] = madF[fi]; }
      return finish(diffF, madPix, null);
    }
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
    var mad0 = Math.max(4, dl[dl.length >> 1] * 1.4826);
    return finish(diff, null, mad0);
    function finish(diff, madPix, madC) {
    var K = opts.k || 3.2, lab = new Int32Array(W * H).fill(-1), comps = [];
    function MAD(q) { return madPix ? madPix[q] : madC; }
    for (y = 0; y < H; y++) for (x = 0; x < W; x++) {
      var i0 = y * W + x; if (!inm[i0] || lab[i0] >= 0 || Math.abs(diff[i0]) < K * MAD(i0)) continue;
      var pol = diff[i0] > 0 ? 1 : -1, st = [i0], mem = []; lab[i0] = comps.length;
      while (st.length) { var q = st.pop(); mem.push(q); var qx = q % W, qy = (q / W) | 0;
        [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (o) { var nx = qx + o[0], ny = qy + o[1]; if (nx < 0 || ny < 0 || nx >= W || ny >= H) return; var j = ny * W + nx;
          if (lab[j] >= 0 || !inm[j] || diff[j] * pol < K * 0.6 * MAD(j)) return; lab[j] = comps.length; st.push(j); }); }
      comps.push({ pol: pol, mem: mem });
    }
    function closedFill(mem, WW) {
      var xs0 = 1e9, ys0 = 1e9, xs1 = -1e9, ys1 = -1e9; mem.forEach(function (q) { var x = q % WW, y = (q / WW) | 0; xs0 = Math.min(xs0, x); ys0 = Math.min(ys0, y); xs1 = Math.max(xs1, x); ys1 = Math.max(ys1, y); });
      var bw = xs1 - xs0 + 5, bh = ys1 - ys0 + 5, a = new Uint8Array(bw * bh); mem.forEach(function (q) { a[(((q / WW) | 0) - ys0 + 2) * bw + (q % WW) - xs0 + 2] = 1; });
      function mo(src, dil) { var o = new Uint8Array(bw * bh); for (var y = 1; y < bh - 1; y++) for (var x = 1; x < bw - 1; x++) { var i = y * bw + x;
        o[i] = dil ? (src[i] | src[i - 1] | src[i + 1] | src[i - bw] | src[i + bw]) : (src[i] & src[i - 1] & src[i + 1] & src[i - bw] & src[i + bw]); } return o; }
      a = mo(mo(a, true), false);
      var out2 = new Uint8Array(bw * bh), st = [0]; out2[0] = 1; // flood the outside from the corner; the rest is the filled blob
      while (st.length) { var q = st.pop(), x = q % bw, y = (q / bw) | 0; [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (o) { var nx = x + o[0], ny = y + o[1]; if (nx < 0 || ny < 0 || nx >= bw || ny >= bh) return; var j = ny * bw + nx; if (out2[j] || a[j]) return; out2[j] = 1; st.push(j); }); }
      var n = 0; for (var k = 0; k < bw * bh; k++) if (!out2[k]) n++; return n;
    }
    var out = [];
    comps.forEach(function (cpt) {
      var n = cpt.mem.length, area = n * res * res; if (opts.debug && n > 6) out.push({ dbg: 1, n: n, area: Math.round(area * 100) / 100, pol: cpt.pol, at: [X0 + (cpt.mem[0] % W), Y0 + ((cpt.mem[0] / W) | 0)] }); if (area < 0.25 || area > 6) return;
      var mx = 0, my = 0, ct = 0; cpt.mem.forEach(function (q) { mx += q % W; my += (q / W) | 0; ct += Math.abs(diff[q]); }); mx /= n; my /= n;
      var sxx = 0, syy = 0, sxy = 0; cpt.mem.forEach(function (q) { var a = q % W - mx, b = ((q / W) | 0) - my; sxx += a * a; syy += b * b; sxy += a * b; });
      var th = 0.5 * Math.atan2(2 * sxy, sxx - syy), u = [Math.cos(th), Math.sin(th)], lo = [1e9, 1e9], hi = [-1e9, -1e9];
      cpt.mem.forEach(function (q) { var a = q % W - mx, b = ((q / W) | 0) - my, s1 = a * u[0] + b * u[1], s2 = -a * u[1] + b * u[0];
        lo[0] = Math.min(lo[0], s1); hi[0] = Math.max(hi[0], s1); lo[1] = Math.min(lo[1], s2); hi[1] = Math.max(hi[1], s2); });
      var w = (hi[0] - lo[0] + 1) * res, h = (hi[1] - lo[1] + 1) * res, asp = Math.max(w, h) / Math.min(w, h);
      // 0.1.7.6: rectangularity of the CLOSED, hole-filled blob (a threshold blob is ragged at its rim; a segmentation mask is not)
      var fill = closedFill(cpt.mem, W) * res * res / (w * h);
      if (opts.debug) out.push({ dbg: 2, w: w, h: h, fill: fill, asp: asp }); if (fill < 0.5 || asp > 3.5 || Math.min(w, h) < 0.35) return;
      var mad = MAD(cpt.mem[0]);
      var ll = unworld(X0 + mx + 0.5 - sx + m.ox, Y0 + my + 0.5 - sy + m.oy, m.z); // back to roofprint coordinates
      out.push({ centroid_lonlat: [Math.round(ll[0] * 1e7) / 1e7, Math.round(ll[1] * 1e7) / 1e7], approx_w_ft: Math.round(Math.max(w, h) * 3.2808 * 10) / 10,
        approx_h_ft: Math.round(Math.min(w, h) * 3.2808 * 10) / 10, approx_area_sqft: Math.round(area * 10.764), polarity: cpt.pol > 0 ? 'bright' : 'dark',
        contrast: Math.round(ct / n / mad * 10) / 10, rectangularity: Math.round(fill * 100) / 100, angle_deg: Math.round(((w >= h ? th : th + Math.PI / 2) * 180 / Math.PI) * 10) / 10,
        background: madPix ? 'own facet' : 'local 2.5 m', z: m.z, source: 'ortho patch (MassGIS 2025 z' + m.z + ')', confidence: 'low' });
    });
    out.sort(function (a, b) { return b.contrast - a.contrast; });
    return out.slice(0, opts.max || 8);
    }
  }
  return { VERSION: VERSION, world: world, unworld: unworld, mpp: mpp, mosaic: mosaic, sobel: sobel, align: align, patches: patches, lidarMask: lidarMask, regionAlign: regionAlign, outlineVsMask: outlineVsMask, edgeSamples: edgeSamples };
});
