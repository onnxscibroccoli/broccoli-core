/*!
 * facets.js v0.1.0 — RoofMeasure "facets" lane: roof facets + roof-line lengths from a 2-D roofprint.
 * UMD, no dependencies: CommonJS require(), AMD, ESM-via-bundler/CJS interop, and browser global window.RoofFacets.
 * Input coordinates: GeoJSON [lon, lat] EPSG:4326, or a local-feet ring (opts.units = 'ft' or auto-detected).
 * Lengths in feet, areas in sq ft. Pitch strings like "6/12" (rise per 12 run).
 *
 * Method: equal-pitch straight skeleton (wavefront simulation with edge + split events),
 * hip roof = skeleton faces; gable = skeleton with wing end-cap triangles converted to gable ends.
 * This is a HEURISTIC from the 2-D roofprint; accuracy vs EagleView-type reports is unproven.
 */
(function (root, factory) {
  if (typeof define === 'function' && define.amd) define([], factory);
  else if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.RoofFacets = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var VERSION = '0.1.0';
  var M_TO_FT = 3.280839895013123, D2R = Math.PI / 180, R2D = 180 / Math.PI;
  var WGS84_A = 6378137.0, WGS84_F = 1 / 298.257223563, WGS84_E2 = WGS84_F * (2 - WGS84_F);

  // ------------------------------------------------------------ pitch
  function parsePitch(p) {
    if (p == null || p === '') return null;
    if (typeof p === 'number') return p;
    var s = String(p).trim(), m = s.match(/^(-?\d*\.?\d+)\s*(?:\/\s*(\d*\.?\d+))?$/);
    if (!m) { var d = s.match(/^(\d*\.?\d+)\s*(deg|°)$/i); if (d) return Math.tan(+d[1] * D2R) * 12; throw new Error('bad pitch: ' + p); }
    var rise = +m[1], run = m[2] ? +m[2] : 12;
    return rise * 12 / run;
  }
  function pitchFactorRise(rise) { var r = rise / 12; return Math.sqrt(1 + r * r); }
  function pitchStr(rise) { return (Math.round(rise * 100) / 100) + '/12'; }

  // ------------------------------------------------------------ geometry helpers
  function localFrame(lon0, lat0) { // same WGS84 local tangent frame as core/roofcalc.js
    var s = Math.sin(lat0 * D2R), w = Math.sqrt(1 - WGS84_E2 * s * s);
    var N = WGS84_A / w, M = WGS84_A * (1 - WGS84_E2) / (w * w * w);
    var kx = N * Math.cos(lat0 * D2R) * D2R * M_TO_FT, ky = M * D2R * M_TO_FT;
    return { lon0: lon0, lat0: lat0,
      toXY: function (p) { return [(p[0] - lon0) * kx, (p[1] - lat0) * ky]; },
      toLL: function (q) { return [lon0 + q[0] / kx, lat0 + q[1] / ky]; } };
  }
  function area2(pts) { var s = 0; for (var i = 0, n = pts.length; i < n; i++) { var a = pts[i], b = pts[(i + 1) % n]; s += a[0] * b[1] - b[0] * a[1]; } return s / 2; }
  function sub(a, b) { return [a[0] - b[0], a[1] - b[1]]; }
  function add(a, b) { return [a[0] + b[0], a[1] + b[1]]; }
  function mul(a, k) { return [a[0] * k, a[1] * k]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1]; }
  function cross(a, b) { return a[0] * b[1] - a[1] * b[0]; }
  function len(a) { return Math.sqrt(a[0] * a[0] + a[1] * a[1]); }
  function dist(a, b) { return len(sub(a, b)); }
  function unit(a) { var l = len(a); return [a[0] / l, a[1] / l]; }
  function bearingXY(a, b) { return (Math.atan2(b[0] - a[0], b[1] - a[1]) * R2D + 360) % 360; } // 0=N, 90=E
  function axisDiff(b1, b2) { var d = Math.abs(((b1 - b2) % 180 + 180) % 180); return Math.min(d, 180 - d); } // 0..90

  function extractRing(input) {
    if (!input) throw new Error('no geometry');
    if (input.type === 'FeatureCollection') return extractRing(input.features[0]);
    if (input.type === 'Feature') return extractRing(input.geometry);
    if (input.type === 'Polygon') return input.coordinates[0];
    if (input.type === 'MultiPolygon') {
      var best = null, bestA = -1;
      input.coordinates.forEach(function (poly) { var r = poly[0], f = localFrame(r[0][0], r[0][1]); var a = Math.abs(area2(r.map(f.toXY))); if (a > bestA) { bestA = a; best = r; } });
      return best;
    }
    if (Array.isArray(input) && Array.isArray(input[0]) && typeof input[0][0] === 'number') return input;
    if (Array.isArray(input) && Array.isArray(input[0]) && Array.isArray(input[0][0])) return input[0];
    throw new Error('unsupported geometry');
  }
  function looksLonLat(ring) { return ring.every(function (p) { return Math.abs(p[0]) <= 180 && Math.abs(p[1]) <= 90; }) && (function () {
    var xs = ring.map(function (p) { return p[0]; }), ys = ring.map(function (p) { return p[1]; });
    return (Math.max.apply(null, xs) - Math.min.apply(null, xs)) < 0.05 && (Math.max.apply(null, ys) - Math.min.apply(null, ys)) < 0.05; })(); }

  /** open, dedupe, drop near-collinear vertices (perp distance < tol ft), CCW. */
  function cleanRing(ring, tol) {
    var r = ring.map(function (p) { return [+p[0], +p[1]]; });
    if (r.length > 1 && dist(r[0], r[r.length - 1]) < 1e-9) r.pop();
    var out = [];
    r.forEach(function (p) { if (!out.length || dist(out[out.length - 1], p) > 1e-6) out.push(p); });
    if (out.length > 1 && dist(out[0], out[out.length - 1]) <= 1e-6) out.pop();
    var changed = true;
    while (changed && out.length > 3) {
      changed = false;
      for (var i = 0; i < out.length && out.length > 3; i++) {
        var a = out[(i - 1 + out.length) % out.length], b = out[i], c = out[(i + 1) % out.length];
        var ac = sub(c, a), l = len(ac);
        var d = l < 1e-9 ? dist(a, b) : Math.abs(cross(ac, sub(b, a))) / l;
        if (d < tol || dist(a, b) < 1e-6) { out.splice(i, 1); changed = true; i--; }
      }
    }
    if (area2(out) < 0) out.reverse();
    return out;
  }
  /** mitred offset of CCW ring; d>0 = outward. */
  function offsetRing(ring, d) {
    var n = ring.length, lines = [];
    for (var i = 0; i < n; i++) {
      var a = ring[i], b = ring[(i + 1) % n], u = unit(sub(b, a)), nOut = [u[1], -u[0]];
      lines.push({ p: add(a, mul(nOut, d)), u: u });
    }
    var out = [];
    for (var j = 0; j < n; j++) {
      var L1 = lines[(j - 1 + n) % n], L2 = lines[j], den = cross(L1.u, L2.u);
      if (Math.abs(den) < 1e-9) out.push(L2.p);
      else { var t = cross(sub(L2.p, L1.p), L2.u) / den; out.push(add(L1.p, mul(L1.u, t))); }
    }
    return out;
  }

  // ------------------------------------------------------------ straight skeleton
  /**
   * Wavefront simulation of the straight skeleton of a simple CCW polygon (no holes).
   * Handles edge events (edge shrinks to 0), split events (reflex vertex hits an opposite edge),
   * and simultaneous/vertex events (coincident vertices -> pinch split). Returns
   * { nodes:[{p,t,orig}], arcs:[{a,b,faces:[e1,e2],reflex}], faces: [[nodeIds...]] per edge }.
   * Node height = t * rise/12 (t = inward offset distance in ft).
   */
  function straightSkeleton(poly, scale, weights) {
    var n = poly.length, EPS = Math.max(1e-7, 1e-7 * scale), MEPS = Math.max(1e-5, 2e-6 * scale);
    var edges = [];
    for (var i = 0; i < n; i++) { var a = poly[i], b = poly[(i + 1) % n], u = unit(sub(b, a)); edges.push({ a: a, b: b, u: u, nrm: [-u[1], u[0]], w: weights ? +weights[i] : 1 }); }
    var nodes = [], arcs = [], warnings = [];
    function nodeAt(p, t) {
      for (var k = 0; k < nodes.length; k++) if (dist(nodes[k].p, p) < MEPS && Math.abs(nodes[k].t - t) < MEPS * 10) return k;
      nodes.push({ p: [p[0], p[1]], t: t }); return nodes.length - 1;
    }
    for (i = 0; i < n; i++) nodes.push({ p: poly[i].slice(), t: 0, orig: i });
    function isReflex(ePrev, eNext) { return cross(edges[ePrev].u, edges[eNext].u) < -1e-9; }
    function mkV(p, node, ePrev, eNext) { return { p: p, node: node, ePrev: ePrev, eNext: eNext, reflex: isReflex(ePrev, eNext) }; }
    function velocity(v) {
      var n1 = edges[v.ePrev].nrm, n2 = edges[v.eNext].nrm, w1 = edges[v.ePrev].w, w2 = edges[v.eNext].w, det = cross(n1, n2);
      if (Math.abs(det) < 1e-9) { if (dot(n1, n2) > 0) return mul(n1, Math.max(w1, w2)); return null; }
      // solve n1.v = w1, n2.v = w2 (weighted wavefront; w = 0 for a vertical gable wall)
      return [(w1 * n2[1] - w2 * n1[1]) / det, (w2 * n1[0] - w1 * n2[0]) / det];
    }
    function finish(v, p, t) {
      var nid = nodeAt(p, t);
      if (nid !== v.node) arcs.push({ a: v.node, b: nid, faces: [v.ePrev, v.eNext], reflex: v.reflex });
      return nid;
    }
    var loops = [poly.map(function (p, i) { return mkV(p.slice(), i, (i - 1 + n) % n, i); })];
    var T = 0, guard = 0;
    while (loops.length && guard++ < 10000) {
      // cleanup / degenerate loops
      var changed = true, g2 = 0;
      while (changed && g2++ < 1000) {
        changed = false;
        for (var li = 0; li < loops.length; li++) {
          var L = loops[li], m = L.length;
          if (m <= 2) {
            if (m === 2) {
              var n0 = finish(L[0], L[0].p, T), n1 = finish(L[1], L[1].p, T);
              if (n0 !== n1) arcs.push({ a: n0, b: n1, faces: [L[0].eNext, L[1].eNext], reflex: false });
            } else if (m === 1) finish(L[0], L[0].p, T);
            loops.splice(li, 1); changed = true; break;
          }
          // merge consecutive coincident vertices
          for (var k = 0; k < m; k++) {
            var v = L[k], w = L[(k + 1) % m];
            if (dist(v.p, w.p) < MEPS) {
              var P = mul(add(v.p, w.p), 0.5), nid = finish(v, P, T); finish(w, P, T);
              var nv = mkV(P, nid, v.ePrev, w.eNext);
              if (k + 1 < m) L.splice(k, 2, nv); else { L.splice(k, 1, nv); L.splice(0, 1); }
              changed = true; break;
            }
          }
          if (changed) break;
          // pinch: non-consecutive coincident vertices
          for (var i1 = 0; i1 < m && !changed; i1++) for (var j1 = i1 + 2; j1 < m && !changed; j1++) {
            if (i1 === 0 && j1 === m - 1) continue;
            if (dist(L[i1].p, L[j1].p) < MEPS) {
              var vi = L[i1], vj = L[j1], X = mul(add(vi.p, vj.p), 0.5), nx = finish(vi, X, T); finish(vj, X, T);
              var loop1 = [mkV(X, nx, vj.ePrev, vi.eNext)].concat(L.slice(i1 + 1, j1));
              var loop2 = [mkV(X, nx, vi.ePrev, vj.eNext)].concat(L.slice(j1 + 1), L.slice(0, i1));
              loops.splice(li, 1, loop1, loop2); changed = true;
            }
          }
          if (changed) break;
          // split: vertex touching interior of a non-adjacent edge
          for (k = 0; k < m && !changed; k++) {
            var sv = L[k];
            for (var q = 0; q < m && !changed; q++) {
              if (q === k || (q + 1) % m === k) continue;
              var A = L[q].p, B = L[(q + 1) % m].p, AB = sub(B, A), l2 = dot(AB, AB);
              if (l2 < 1e-18) continue;
              var s = dot(sub(sv.p, A), AB) / l2; if (s <= 1e-9 || s >= 1 - 1e-9) continue;
              var foot = add(A, mul(AB, s));
              if (dist(foot, sv.p) < MEPS) {
                var E = L[q].eNext, ns = finish(sv, sv.p, T);
                var X1 = mkV(sv.p.slice(), ns, E, sv.eNext), X2 = mkV(sv.p.slice(), ns, sv.ePrev, E);
                var la, lb;
                // loop1: X1, k+1 ... q ; loop2: X2, q+1 ... k-1
                la = [X1]; for (var z = (k + 1) % m; z !== (q + 1) % m; z = (z + 1) % m) la.push(L[z]);
                lb = [X2]; for (z = (q + 1) % m; z !== k; z = (z + 1) % m) lb.push(L[z]);
                loops.splice(li, 1, la, lb); changed = true;
              }
            }
          }
          if (changed) break;
          // zero-area loop (all collinear): connect as a polyline ridge
          var ar = area2(L.map(function (x) { return x.p; }));
          if (Math.abs(ar) < MEPS * scale && m >= 3) {
            var ids = L.map(function (x) { return finish(x, x.p, T); });
            for (k = 0; k < m; k++) { var ka = ids[k], kb = ids[(k + 1) % m]; if (ka !== kb) arcs.push({ a: ka, b: kb, faces: [L[k].eNext, L[(k + 1) % m].ePrev], reflex: false, weight: 0.5 }); }
            warnings.push('degenerate zero-area wavefront loop at offset ' + T.toFixed(2) + ' ft closed as a doubly-traced ridge polyline (each segment counted at half weight)');
            loops.splice(li, 1); changed = true; break;
          }
        }
      }
      if (!loops.length) break;
      // compute velocities and next event time
      var tmin = Infinity;
      loops.forEach(function (L) { L.forEach(function (v) { v.vel = velocity(v); }); });
      loops.forEach(function (L) {
        var m = L.length;
        for (var k = 0; k < m; k++) {
          var v = L[k], w = L[(k + 1) % m];
          if (!v.vel || !w.vel) { tmin = 0; continue; }
          var d = edges[v.eNext].u, Lk = dot(sub(w.p, v.p), d), rate = dot(sub(w.vel, v.vel), d);
          if (rate < -1e-12) { var te = -Lk / rate; if (te >= -EPS && te < tmin) tmin = Math.max(0, te); }
          if (!v.reflex) continue;
          for (var q = 0; q < m; q++) {
            if (q === k || (q + 1) % m === k) continue;
            var a = L[q], b = L[(q + 1) % m], E = edges[a.eNext], nn = E.nrm, den = E.w - dot(nn, v.vel);
            if (den <= 1e-12 || !a.vel || !b.vel) continue;
            var dd = dot(nn, sub(v.p, a.p)); if (dd < -EPS) continue;
            var ts = dd / den; if (ts >= tmin) continue;
            var hit = add(v.p, mul(v.vel, ts)), A2 = add(a.p, mul(a.vel, ts)), B2 = add(b.p, mul(b.vel, ts));
            var AB = sub(B2, A2), l2 = dot(AB, AB); if (l2 < 1e-18) continue;
            var s = dot(sub(hit, A2), AB) / l2;
            if (s > -1e-7 && s < 1 + 1e-7) tmin = Math.max(0, ts);
          }
        }
      });
      if (!isFinite(tmin)) { warnings.push('no further events; wavefront aborted'); break; }
      if (tmin === 0 && loops.some(function (L) { return L.some(function (v) { return !v.vel; }); })) {
        // antiparallel adjacent edges in a >2 loop: should have been merged; force-finish
        warnings.push('degenerate vertex (antiparallel edges) at offset ' + T.toFixed(3));
        loops.forEach(function (L) { L.forEach(function (v) { if (!v.vel) v.vel = [0, 0]; }); });
        tmin = 1e-6;
      }
      T += tmin;
      loops.forEach(function (L) { L.forEach(function (v) { v.p = add(v.p, mul(v.vel, tmin)); }); });
    }
    if (guard >= 10000) warnings.push('event limit reached');
    // faces: walk arcs for each edge from node(b) to node(a)
    var faces = [];
    for (var e = 0; e < n; e++) {
      var fa = arcs.filter(function (r) { return r.faces[0] === e || r.faces[1] === e; });
      var start = (e + 1) % n, goal = e, cur = start, path = [start], used = {}, ok = true, g3 = 0;
      while (cur !== goal && g3++ < 500) {
        var nxt = -1;
        for (var r = 0; r < fa.length; r++) {
          if (used[r]) continue;
          if (fa[r].a === cur) { nxt = fa[r].b; used[r] = 1; break; }
          if (fa[r].b === cur) { nxt = fa[r].a; used[r] = 1; break; }
        }
        if (nxt < 0) { ok = false; break; }
        cur = nxt; path.push(cur);
      }
      if (!ok || cur !== goal) warnings.push('face for edge ' + e + ' did not close');
      if (path[path.length - 1] === goal) path.pop();
      faces.push([goal].concat(path)); // edge a, b, ... skeleton nodes back toward a
    }
    return { nodes: nodes, arcs: arcs, faces: faces, warnings: warnings, edges: edges };
  }

  // ------------------------------------------------------------ main
  function computeFacets(footprint, opts) {
    opts = opts || {};
    var notes = [], method = [];
    var ring0 = extractRing(footprint);
    var units = opts.units || (looksLonLat(ring0) ? 'lonlat' : 'ft');
    var frame = null, ring;
    if (units === 'lonlat') {
      var cx = 0, cy = 0, r0 = ring0.slice(); if (dist(r0[0], r0[r0.length - 1]) === 0) r0.pop();
      r0.forEach(function (p) { cx += p[0]; cy += p[1]; });
      frame = localFrame(cx / r0.length, cy / r0.length);
      ring = ring0.map(frame.toXY);
    } else ring = ring0.map(function (p) { return [+p[0], +p[1]]; });
    ring = cleanRing(ring, opts.simplify_ft == null ? 0.3 : opts.simplify_ft);
    if (ring.length < 3) throw new Error('footprint has fewer than 3 usable vertices');
    var footprintArea = area2(ring);
    var overhang = +opts.overhang_ft || 0;
    if (overhang) { ring = offsetRing(ring, overhang); notes.push('roofprint = footprint offset outward by ' + overhang + ' ft (mitred)'); }
    var planArea = area2(ring);

    var hasPitch = !(opts.pitch == null || opts.pitch === ''), hasPF = opts.pitch_factor != null && +opts.pitch_factor >= 1;
    var pitchSource = hasPitch || hasPF ? 'input' : 'default';
    var rise = hasPitch ? parsePitch(opts.pitch) : hasPF ? 12 * Math.sqrt(+opts.pitch_factor * +opts.pitch_factor - 1) : 6;
    if (!hasPitch && hasPF) notes.push('pitch derived from pitch_factor ' + opts.pitch_factor);
    var pf = pitchFactorRise(rise), k = rise / 12;
    if (pitchSource === 'default') notes.push('pitch not supplied; defaulted to 6/12');

    // ridge bearing
    var rbSource = 'input', rb = opts.ridge_bearing_deg;
    var longest = 0, longestB = 0;
    for (var i = 0; i < ring.length; i++) { var a = ring[i], b = ring[(i + 1) % ring.length], l = dist(a, b); if (l > longest) { longest = l; longestB = bearingXY(a, b) % 180; } }
    if (rb == null || isNaN(+rb)) { rb = longestB; rbSource = 'longest_edge'; } else rb = ((+rb % 180) + 180) % 180;

    var lidarRidges = Array.isArray(opts.ridges) ? opts.ridges.map(function (r) { return typeof r === 'number' ? r : r && r.bearing_deg; }).filter(function (b) { return b != null && !isNaN(+b); }).map(function (b) { return ((+b % 180) + 180) % 180; }) : [];
    if (rbSource === 'longest_edge' && lidarRidges.length) { rb = lidarRidges[0]; rbSource = 'ridges[0]'; }
    var lidarPlanes = Array.isArray(opts.planes) ? opts.planes.filter(function (p) { return p && p.aspect_deg != null && (p.pitch != null || p.slope_deg != null); }) : [];
    var xs = ring.map(function (p) { return p[0]; }), ys = ring.map(function (p) { return p[1]; });
    var scale = Math.max(Math.max.apply(null, xs) - Math.min.apply(null, xs), Math.max.apply(null, ys) - Math.min.apply(null, ys));
    var sk = straightSkeleton(ring, scale);
    sk.warnings.forEach(function (w) { notes.push('skeleton: ' + w); });
    var nodes = sk.nodes, n = ring.length;

    // roof type decision
    var rt = (opts.roof_type || 'auto').toLowerCase(), rtSource = 'input', rtConf = null;
    var hasBearing = (opts.ridge_bearing_deg != null && opts.ridge_bearing_deg !== '' && !isNaN(+opts.ridge_bearing_deg)) || lidarRidges.length > 0;
    var guess = opts.roof_shape_guess ? String(opts.roof_shape_guess).toLowerCase() : null;
    if (rt === 'auto' && guess) {
      if (guess === 'gable' || guess === 'hip' || guess === 'flat') { rt = guess; rtSource = 'roof_shape_guess'; rtConf = 'medium'; method.push('roof_shape_guess hint: ' + guess); }
      else notes.push('roof_shape_guess "' + guess + '" is not a usable roof_type hint; ignored');
    }
    var sp = stylePrior(opts.style);
    if (opts.style != null && opts.style !== '') {
      if (rt !== 'auto') notes.push('style "' + opts.style + '" ignored because roof_type was given explicitly (' + rt + ')');
      else notes.push('style prior (heuristic assessor-style mapping, not observed): "' + opts.style + '" -> ' + (sp ? sp.label : 'unknown style, no prior'));
    }
    if (rt === 'auto' && !hasBearing && sp && sp.unsupported) {
      return { facets: [], lines: { ridge_lf: null, hip_lf: null, valley_lf: null, eave_lf: null, rake_lf: null, wall_flashing_lf: null }, unsupported: true,
        method: 'unsupported style', roof_type: null, roof_type_source: 'style_prior', pitch: pitchStr(rise), pitch_source: pitchSource,
        ridge_bearing_deg: r2(rb), ridge_bearing_source: rbSource, plan_area_sqft: r2(planArea), footprint_area_sqft: r2(footprintArea),
        notes: notes.concat([sp.label + ': multi-pitch roof shape is not supported by the equal-pitch skeleton; no facets or lines produced (fail-closed). Pass roof_type explicitly to force an approximation.']), version: VERSION };
    }
    var ridgeArcs = sk.arcs.filter(function (r) { return Math.abs(nodes[r.a].t - nodes[r.b].t) < 1e-4 * Math.max(1, scale) && dist(nodes[r.a].p, nodes[r.b].p) > 1e-6; });
    var mainRidge = ridgeArcs.slice().sort(function (x, y) { return dist(nodes[y.a].p, nodes[y.b].p) - dist(nodes[x.a].p, nodes[x.b].p); })[0];
    if (rt === 'auto' && !hasBearing && sp && !sp.unsupported) {
      rt = sp.roof_type; rtSource = 'style_prior'; rtConf = sp.confidence;
      method.push('style prior: ' + sp.label + ' -> ' + rt + ' (confidence ' + sp.confidence + ')');
    }
    if (rt === 'auto') {
      rtSource = hasBearing ? 'ridge_bearing' : 'default';
      if (hasBearing) {
        var mrB = mainRidge ? bearingXY(nodes[mainRidge.a].p, nodes[mainRidge.b].p) : null;
        if (mrB == null || axisDiff(mrB, rb) <= 25) {
          rt = 'gable'; method.push('lidar-informed: ridge_bearing_deg ' + rb.toFixed(1) + ' parallels the main skeleton ridge' + (mrB == null ? ' (pyramid footprint; bearing picks the gable axis)' : ' (' + mrB.toFixed(1) + ')') + ' -> gable');
        } else {
          rt = 'hip'; method.push('lidar-informed: ridge_bearing_deg ' + rb.toFixed(1) + ' disagrees with footprint main ridge ' + mrB.toFixed(1) + ' by >25 deg -> kept hip (could be cross-gable; verify)');
        }
      } else { rt = 'hip'; method.push('auto: no ridge bearing supplied -> hip (default heuristic)'); }
    }
    if (rt === 'gable' && opts.gable_method === 'ridge_split') {
      return finishRidgeSplit(ring, frame, rb, rise, {
        notes: notes, method: method, rtSource: rtSource, rtConf: rtConf, pitchSource: pitchSource, rbSource: rbSource,
        footprintArea: footprintArea, planArea: planArea, overhang: overhang, units: units, planes: lidarPlanes, ppf: opts.pitch_per_facet,
        why: 'gable_method=ridge_split' });
    }
    if (rt === 'flat' || rise === 0) {
      return { facets: [{ id: 'F0', area_sqft: r2(planArea), plan_area_sqft: r2(planArea), pitch: '0/12' }],
        lines: { ridge_lf: 0, hip_lf: 0, valley_lf: 0, eave_lf: r2(perim(ring)), rake_lf: 0, wall_flashing_lf: 0 }, method: 'flat', roof_type: 'flat', roof_type_source: rtSource,
        pitch_source: pitchSource, ridge_bearing_source: rbSource, notes: notes.concat(['flat roof: single facet, all edges eave']) };
    }

    // working structures
    var arcs = sk.arcs.map(function (r) { return { a: r.a, b: r.b, reflex: r.reflex, faces: r.faces.slice(), weight: r.weight == null ? 1 : r.weight }; });
    var faces = sk.faces.map(function (f) { return f.slice(); });
    var removed = {}, edgeType = []; for (i = 0; i < n; i++) edgeType.push('eave');
    if (rt === 'gable') {
      var gset = gableEdges(ring, rb, rbSource === 'input');
      if (lidarRidges.length > 1) gset = gset.filter(function (e) { var eb = bearingXY(ring[e], ring[(e + 1) % n]); return lidarRidges.some(function (lb) { return axisDiff(lb, eb) >= 60; }); });
      method.push('gable: weighted straight skeleton - gable-end edges get wavefront speed 0 (vertical wall), all other edges speed 1; equivalent to rectangular-wing decomposition with one ridge per wing running to its gable end and valleys at wing junctions; arcs running up a gable wall are rakes (3-D)');
      if (lidarRidges.length > 1) method.push('lidar ridges[] (' + lidarRidges.map(function (b) { return b.toFixed(1); }).join(', ') + ' deg): gable ends restricted to edges perpendicular (>=60 deg) to a lidar ridge');
      if (gset.length) {
        var wts = []; for (i = 0; i < n; i++) wts.push(gset.indexOf(i) >= 0 ? 0 : 1);
        sk = straightSkeleton(ring, scale, wts);
        sk.warnings.forEach(function (w) { notes.push('weighted skeleton: ' + w); });
        nodes = sk.nodes;
        arcs = sk.arcs.map(function (r) { return { a: r.a, b: r.b, reflex: r.reflex, faces: r.faces.slice(), weight: r.weight == null ? 1 : r.weight }; });
        faces = sk.faces.map(function (f) { return f.slice(); });
        gset.forEach(function (e) { removed[e] = true; edgeType[e] = 'rake'; });
        notes.push('gable ends (edge idx): ' + gset.join(',') + '; ridge bearing ' + rb.toFixed(1) + ' deg (' + rbSource + ')');
      } else notes.push('gable requested but no gable-end edge qualified; result equals hip');
    } else method.push('hip: equal-pitch straight skeleton; each skeleton face = one facet; all roofprint edges are eaves');

    // facets
    var ppf = opts.pitch_per_facet || null, facets = [];
    for (var e = 0; e < n; e++) {
      if (removed[e]) continue;
      var poly = faces[e].map(function (id) { return nodes[id].p; });
      var pa = area2(poly);
      var fr = rise, dsb = (bearingXY(ring[e], ring[(e + 1) % n]) + 90) % 360;
      if (ppf && ppf[e] != null) fr = parsePitch(ppf[e]); else if (ppf && ppf['F' + e] != null) fr = parsePitch(ppf['F' + e]);
      else if (lidarPlanes.length) { var pm = matchPlane(lidarPlanes, dsb); if (pm != null) fr = pm; }
      var fct = { id: 'F' + e, edge_index: e, pitch: pitchStr(fr), plan_area_sqft: r2(pa), area_sqft: r2(pa * pitchFactorRise(fr)),
        edge_type: edgeType[e], eave_edge_ft: r2(dist(ring[e], ring[(e + 1) % n])), vertex_count: poly.length,
        downslope_bearing_deg: r2((bearingXY(ring[e], ring[(e + 1) % n]) + 90) % 360) };
      if (frame) fct.polygon_lonlat = poly.concat([poly[0]]).map(function (p) { var q = frame.toLL(p); return [r7(q[0]), r7(q[1])]; });
      else fct.polygon_ft = poly.map(function (p) { return [r2(p[0]), r2(p[1])]; });
      facets.push(fct);
    }
    if (lidarPlanes.length && !ppf) notes.push('lidar planes[]: facet pitch taken from the plane whose aspect is within 30 deg of the facet downslope bearing (areas only; geometry stays equal-pitch ' + pitchStr(rise) + ')');
    if (ppf) notes.push('pitch_per_facet applied to facet areas only; skeleton geometry and line lengths still assume equal pitch ' + pitchStr(rise));

    // lines
    var lines = { ridge_lf: 0, hip_lf: 0, valley_lf: 0, eave_lf: 0, rake_lf: 0, wall_flashing_lf: 0 }, lineList = [], cnt = { ridge: 0, hip: 0, valley: 0, rake: 0, wall_flashing: 0 };
    // wall flashing: a gable-wall arc that has a HIGHER collinear gable-wall arc over the same plan location is a
    // lower roof edge abutting a higher gable wall (step/wall flashing), not an exposed rake.
    var wallArcs = arcs.map(function (r, i) { return { r: r, i: i }; }).filter(function (o) {
      var r = o.r; return !r.dead && (removed[r.faces[0]] || removed[r.faces[1]]) && !(removed[r.faces[0]] && removed[r.faces[1]]) && dist(nodes[r.a].p, nodes[r.b].p) > 1e-6; });
    var flashing = {};
    wallArcs.forEach(function (o) {
      var A = nodes[o.r.a], B = nodes[o.r.b], m = mul(add(A.p, B.p), 0.5), hm = (A.t + B.t) / 2;
      flashing[o.i] = wallArcs.some(function (q) {
        if (q.i === o.i) return false;
        var C = nodes[q.r.a], D = nodes[q.r.b], cd = sub(D.p, C.p), l2 = dot(cd, cd), sPar = dot(sub(m, C.p), cd) / l2;
        if (sPar <= 1e-3 || sPar >= 1 - 1e-3) return false;
        if (Math.abs(cross(cd, sub(m, C.p))) / Math.sqrt(l2) > 0.01) return false;
        return C.t + sPar * (D.t - C.t) > hm + 0.01;
      });
    });
    arcs.forEach(function (r, ai) {
      if (r.dead) return;
      var pl = dist(nodes[r.a].p, nodes[r.b].p); if (pl < 1e-6) return;
      var dh = Math.abs(nodes[r.a].t - nodes[r.b].t) * k, type;
      if (removed[r.faces[0]] || removed[r.faces[1]]) { if (removed[r.faces[0]] && removed[r.faces[1]]) return; type = flashing[ai] ? 'wall_flashing' : 'rake'; }
      else if (r.ridge || Math.abs(nodes[r.a].t - nodes[r.b].t) < 1e-4 * Math.max(1, scale)) { type = 'ridge'; dh = 0; }
      else type = r.reflex ? 'valley' : 'hip';
      var wgt = r.weight == null ? 1 : r.weight, L3 = Math.sqrt(pl * pl + dh * dh) * wgt;
      lines[type + '_lf'] += L3; cnt[type] += wgt;
      var seg = { type: type, length_ft: r2(L3), weight: wgt, bearing_deg: r2(bearingXY(nodes[r.a].p, nodes[r.b].p) % 180), plan_length_ft: r2(pl), rise_ft: r2(dh), facets: r.faces.filter(function (x) { return !removed[x]; }).map(function (x) { return 'F' + x; }) };
      if (frame) seg.coords_lonlat = [nodes[r.a].p, nodes[r.b].p].map(function (p) { var q = frame.toLL(p); return [r7(q[0]), r7(q[1])]; });
      else seg.coords_ft = [nodes[r.a].p, nodes[r.b].p].map(function (p) { return [r2(p[0]), r2(p[1])]; });
      lineList.push(seg);
    });
    var edgesOut = [];
    for (e = 0; e < n; e++) {
      var el = dist(ring[e], ring[(e + 1) % n]);
      if (edgeType[e] !== 'rake') lines.eave_lf += el;
      edgesOut.push({ i: e, length_ft: r2(el), bearing_deg: r2(bearingXY(ring[e], ring[(e + 1) % n])), type: edgeType[e], sloped_length_ft: r2(edgeType[e] === 'rake' ? el * pf : el), auto: true });
    }
    Object.keys(lines).forEach(function (kk) { lines[kk] = r2(lines[kk]); });
    var totalArea = facets.reduce(function (s, f) { return s + f.area_sqft; }, 0), sumPlan = facets.reduce(function (s, f) { return s + f.plan_area_sqft; }, 0);
    if (Math.abs(sumPlan - planArea) > 0.005 * planArea) notes.push('WARNING: facet plan areas (' + sumPlan.toFixed(1) + ') do not sum to roofprint area (' + planArea.toFixed(1) + '); skeleton may be unreliable for this shape');
    notes.push('heuristic from the 2-D roofprint with an equal-pitch assumption; accuracy vs EagleView/measured reports is unproven');
    notes.push('line definitions: rake = exposed sloped gable edge, 3-D (drip edge), incl. the part of a higher gable end above a lower roof; wall_flashing = lower roof edge abutting a higher gable wall (3-D); eave = horizontal drip edge; hip/valley = true 3-D; ridge horizontal');
    return {
      facets: facets,
      lines: lines,
      line_counts: cnt,
      line_segments: lineList,
      edges: edgesOut,
      method: method.join('; '),
      roof_type: rt, roof_type_source: rtSource, roof_type_confidence: rtConf || (rtSource === 'input' ? 'input' : rtSource === 'ridge_bearing' ? 'medium' : 'low'),
      pitch: pitchStr(rise), pitch_source: pitchSource, pitch_factor: r4(pf),
      ridge_bearing_deg: r2(rb), ridge_bearing_source: rbSource,
      footprint_area_sqft: r2(footprintArea), plan_area_sqft: r2(planArea), overhang_ft: overhang,
      total_area_sqft: r2(totalArea), squares: r2(totalArea / 100),
      units_in: units,
      notes: notes,
      version: VERSION
    };
  }
  function rayDepth(pts, i, frac, eps) {
    var n = pts.length, a = pts[i], b = pts[(i + 1) % n], u = unit(sub(b, a)), nn = [-u[1], u[0]];
    var o = add(add(a, mul(sub(b, a), frac)), mul(nn, eps)), best = Infinity;
    for (var j = 0; j < n; j++) {
      if (j === i) continue;
      var c = pts[j], d = pts[(j + 1) % n], ex = d[0] - c[0], ey = d[1] - c[1], den = nn[0] * ey - nn[1] * ex;
      if (Math.abs(den) < 1e-12) continue;
      var t = ((c[0] - o[0]) * ey - (c[1] - o[1]) * ex) / den, s2 = ((c[0] - o[0]) * nn[1] - (c[1] - o[1]) * nn[0]) / den;
      if (t > eps && s2 >= -1e-9 && s2 <= 1 + 1e-9) best = Math.min(best, t);
    }
    return best;
  }
  function isRectangle(pts) {
    if (pts.length !== 4) return false;
    for (var i = 0; i < 4; i++) { var a = pts[(i + 3) % 4], b = pts[i], c = pts[(i + 1) % 4], u = sub(b, a), v = sub(c, b);
      if (Math.abs(dot(u, v) / (len(u) * len(v))) > Math.sin(10 * D2R)) return false; }
    return true;
  }
  /**
   * Gable-end edge selection (same rule as facets/python/facets.py gable_edges):
   *  - rectangle: the two edges perpendicular (>45 deg) to the ridge bearing;
   *  - else an edge with both end vertices convex whose wing depth (min inward ray at 25/50/75 %) exceeds
   *    its length (exact ties broken by being perpendicular to the ridge bearing);
   *  - when ridge_bearing_deg is an INPUT, an edge within 15 deg of perpendicular to it also qualifies even if
   *    one end vertex is reflex (stepped gable end), provided the wing depth along the ridge exceeds its length.
   */
  function gableEdges(pts, rb, ridgeInput) {
    var n = pts.length, lens = [], brg = [], i;
    for (i = 0; i < n; i++) { lens.push(dist(pts[i], pts[(i + 1) % n])); brg.push(bearingXY(pts[i], pts[(i + 1) % n])); }
    if (isRectangle(pts)) return brg.map(function (b, j) { return axisDiff(b, rb) > 45 ? j : -1; }).filter(function (j) { return j >= 0; });
    var scale = Math.max.apply(null, lens), eps = 1e-6 * scale, tol = 1e-6 * scale, convex = [], out = [];
    for (i = 0; i < n; i++) convex.push(cross(sub(pts[i], pts[(i - 1 + n) % n]), sub(pts[(i + 1) % n], pts[i])) > 0);
    for (i = 0; i < n; i++) {
      var perpIn = ridgeInput && axisDiff(brg[i], rb) >= 75;
      if (!((convex[i] && convex[(i + 1) % n]) || perpIn)) continue;
      var depth = Math.min(rayDepth(pts, i, 0.25, eps), rayDepth(pts, i, 0.5, eps), rayDepth(pts, i, 0.75, eps));
      if (depth > lens[i] + tol) out.push(i);
      else if (Math.abs(depth - lens[i]) <= tol && axisDiff(brg[i], rb) > 45) out.push(i);
    }
    return out;
  }
  function planeRise(p) { return p.pitch != null ? parsePitch(p.pitch) : Math.tan(+p.slope_deg * D2R) * 12; }
  function matchPlane(planes, downslope) {
    var best = null, bd = 31;
    planes.forEach(function (p) { var d = Math.abs(((+p.aspect_deg - downslope) % 360 + 540) % 360 - 180); if (d < bd) { bd = d; best = p; } });
    return best ? planeRise(best) : null;
  }
  /** clip CCW polygon to half-plane n.p >= c (Sutherland-Hodgman, one line; fine for concave input) */
  function clipHalf(poly, nrm, c) {
    var out = [];
    for (var i = 0; i < poly.length; i++) {
      var P = poly[i], Q = poly[(i + 1) % poly.length], sp = dot(nrm, P) - c, sq = dot(nrm, Q) - c;
      if (sp >= 0) out.push(P);
      if ((sp >= 0) !== (sq >= 0)) { var t = sp / (sp - sq); out.push(add(P, mul(sub(Q, P), t))); }
    }
    return out;
  }
  /** Gable by splitting the roofprint along one ridge line (bearing rb, through the middle of the across-ridge extent). */
  function finishRidgeSplit(ring, frame, rb, rise, ctx) {
    var n = ring.length, d = [Math.sin(rb * D2R), Math.cos(rb * D2R)], nrm = [d[1], -d[0]];
    var pr = ring.map(function (p) { return dot(nrm, p); }), lo = Math.min.apply(null, pr), hi = Math.max.apply(null, pr), c = (lo + hi) / 2;
    var k = rise / 12, pf = pitchFactorRise(rise);
    // ridge length = length of line n.p=c inside polygon
    var ts = [];
    for (var i = 0; i < n; i++) { var P = ring[i], Q = ring[(i + 1) % n], sp = dot(nrm, P) - c, sq = dot(nrm, Q) - c;
      if ((sp >= 0) !== (sq >= 0)) { var X = add(P, mul(sub(Q, P), sp / (sp - sq))); ts.push(dot(d, X)); } }
    ts.sort(function (a, b) { return a - b; });
    var ridge = 0, segs = [];
    for (i = 0; i + 1 < ts.length; i += 2) { ridge += ts[i + 1] - ts[i]; segs.push([ts[i], ts[i + 1]]); }
    var halves = [{ id: 'FA', poly: clipHalf(ring, nrm, c), down: (rb + 90) % 360 }, { id: 'FB', poly: clipHalf(ring, mul(nrm, -1), -c), down: (rb + 270) % 360 }];
    // downslope of half with n.p >= c points along +nrm; bearing of +nrm
    halves[0].down = (Math.atan2(nrm[0], nrm[1]) * R2D + 360) % 360; halves[1].down = (halves[0].down + 180) % 360;
    var facets = halves.filter(function (h) { return h.poly.length >= 3 && area2(h.poly) > 1e-6; }).map(function (h) {
      var fr = rise; if (ctx.ppf && ctx.ppf[h.id] != null) fr = parsePitch(ctx.ppf[h.id]); else if (ctx.planes.length) { var pm = matchPlane(ctx.planes, h.down); if (pm != null) fr = pm; }
      var pa = area2(h.poly), f = { id: h.id, pitch: pitchStr(fr), plan_area_sqft: r2(pa), area_sqft: r2(pa * pitchFactorRise(fr)), downslope_bearing_deg: r2(h.down), vertex_count: h.poly.length };
      if (frame) f.polygon_lonlat = h.poly.concat([h.poly[0]]).map(function (p) { var q = frame.toLL(p); return [r7(q[0]), r7(q[1])]; });
      else f.polygon_ft = h.poly.map(function (p) { return [r2(p[0]), r2(p[1])]; });
      return f;
    });
    var lines = { ridge_lf: ridge, hip_lf: 0, valley_lf: 0, eave_lf: 0, rake_lf: 0, wall_flashing_lf: 0 }, edges = [];
    for (i = 0; i < n; i++) {
      var a = ring[i], b = ring[(i + 1) % n], el = dist(a, b), eb = bearingXY(a, b), th = axisDiff(eb, rb), type = th <= 45 ? 'eave' : 'rake';
      var sl = type === 'eave' ? el : el * Math.sqrt(1 + Math.pow(Math.sin(th * D2R) * k, 2));
      lines[type + '_lf'] += sl;
      edges.push({ i: i, length_ft: r2(el), bearing_deg: r2(eb), type: type, sloped_length_ft: r2(sl), auto: true });
    }
    var lineList = segs.map(function (sg) { var A = add(mul(nrm, c), mul(d, sg[0])), B = add(mul(nrm, c), mul(d, sg[1]));
      var o = { type: 'ridge', length_ft: r2(sg[1] - sg[0]), plan_length_ft: r2(sg[1] - sg[0]), rise_ft: 0, weight: 1, bearing_deg: r2(rb), facets: ['FA', 'FB'] };
      if (frame) o.coords_lonlat = [A, B].map(function (p) { var q = frame.toLL(p); return [r7(q[0]), r7(q[1])]; }); else o.coords_ft = [A, B].map(function (p) { return [r2(p[0]), r2(p[1])]; });
      return o; });
    Object.keys(lines).forEach(function (kk) { lines[kk] = r2(lines[kk]); });
    var tot = facets.reduce(function (s, f) { return s + f.area_sqft; }, 0);
    var notes = ctx.notes.concat([
      'ridge-split gable (' + ctx.why + '): one ridge along ' + rb.toFixed(1) + ' deg through the middle of the roofprint\'s across-ridge extent; 2 planes; edges within 45 deg of the ridge = eave, others = rake (sloped)',
      'off-centre notches/bump-outs are absorbed into the two planes (eave heights may differ); no hips or valleys modelled in this mode',
      'heuristic from the 2-D roofprint with an equal-pitch assumption; accuracy vs EagleView/measured reports is unproven']);
    if (ctx.planes.length) notes.push('lidar planes[]: facet pitch matched by aspect (within 30 deg)');
    return { facets: facets, lines: lines, line_counts: { ridge: segs.length, hip: 0, valley: 0, rake: 0, wall_flashing: 0 }, line_segments: lineList, edges: edges,
      method: ctx.method.concat(['gable (ridge-split)']).join('; '), roof_type: 'gable', roof_type_source: ctx.rtSource,
      roof_type_confidence: ctx.rtConf || (ctx.rtSource === 'input' ? 'input' : 'medium'), pitch: pitchStr(rise), pitch_source: ctx.pitchSource,
      pitch_factor: r4(pf), ridge_bearing_deg: r2(rb), ridge_bearing_source: ctx.rbSource, footprint_area_sqft: r2(ctx.footprintArea),
      plan_area_sqft: r2(ctx.planArea), overhang_ft: ctx.overhang, total_area_sqft: r2(tot), squares: r2(tot / 100), units_in: ctx.units, notes: notes, version: VERSION };
  }
  /** Heuristic assessor-style -> roof_type prior. Returns null for unknown styles. */
  function stylePrior(style) {
    if (style == null || style === '') return null;
    var s = String(style).toUpperCase().replace(/[^A-Z]/g, '');
    if (/^(CAPE|CAPECOD|CC)/.test(s)) return { roof_type: 'gable', confidence: 'medium', label: 'Cape Cod (leans gable)' };
    if (/^(COL|COLONIAL)/.test(s)) return { roof_type: 'gable', confidence: 'medium', label: 'Colonial (leans gable)' };
    if (/^GAR/.test(s)) return { roof_type: 'gable', confidence: 'medium', label: 'Garrison (leans gable)' };
    if (/^SALT/.test(s)) return { roof_type: 'gable', confidence: 'low', label: 'Saltbox (leans gable; asymmetric slopes not modelled, equal pitch assumed)' };
    if (/^RAN/.test(s)) return { roof_type: 'hip', confidence: 'low', label: 'Ranch (ambiguous; default hip, low confidence)' };
    if (/^GAMB/.test(s)) return { unsupported: true, label: 'Gambrel' };
    if (/^MANS/.test(s)) return { unsupported: true, label: 'Mansard' };
    return null; // Split Level, Contemporary, etc.: no prior
  }
  function insertBetween(face, x, y, m) { // insert m between consecutive ids x,y (either order, cyclic)
    for (var i = 0; i < face.length; i++) {
      var a = face[i], b = face[(i + 1) % face.length];
      if ((a === x && b === y) || (a === y && b === x)) { face.splice(i + 1, 0, m); return true; }
    }
    return false;
  }
  function perim(r) { var s = 0; for (var i = 0; i < r.length; i++) s += dist(r[i], r[(i + 1) % r.length]); return s; }
  function r2(x) { return Math.round(x * 100) / 100; }
  function r4(x) { return Math.round(x * 1e4) / 1e4; }
  function r7(x) { return Math.round(x * 1e7) / 1e7; }

  /**
   * LiDAR plane hook (stub, fail-closed). Accepts precomputed planes from the lidar lane
   * ({planes:[{pitch, area_sqft?, polygon_lonlat?}]}) but does NOT fabricate facets from them yet.
   */
  function facetsFromPlanes(planesResult) {
    var ok = planesResult && Array.isArray(planesResult.planes) && planesResult.planes.length;
    return { facets: [], lines: null, method: 'lidar-planes (not implemented)', notes: [ok ? 'received ' + planesResult.planes.length + ' planes; plane-to-facet assembly not implemented; use computeFacets with pitch/ridge_bearing_deg instead' : 'no planes supplied'] };
  }

  return { VERSION: VERSION, computeFacets: computeFacets, straightSkeleton: straightSkeleton, parsePitch: parsePitch,
    cleanRing: cleanRing, stylePrior: stylePrior, offsetRing: offsetRing, localFrame: localFrame, facetsFromPlanes: facetsFromPlanes };
});
