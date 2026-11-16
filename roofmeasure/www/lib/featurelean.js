/* SPDX-License-Identifier: MIT */
/* Experimental, overlay-only ortho relief displacement for lidar roof features.
 * The ortho offset includes unknown georegistration bias, so this correction is
 * a NOT_PROVEN visual candidate, never a measurement or a change to roof geometry. */
(function (root, factory) {
  var lib = factory();
  if (typeof module === 'object' && module.exports) module.exports = lib;
  else root.RoofFeatureLean = lib;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  function finite(n) { return typeof n === 'number' && isFinite(n); }
  function qtile(a, f) {
    if (!a.length) return null;
    var b = a.slice().sort(function (x, y) { return x - y; });
    return b[Math.min(b.length - 1, Math.max(0, Math.floor((b.length - 1) * f)))];
  }
  function distance(x, y, a, b) {
    var vx = b[0] - a[0], vy = b[1] - a[1], den = vx * vx + vy * vy;
    var t = den ? Math.max(0, Math.min(1, ((x - a[0]) * vx + (y - a[1]) * vy) / den)) : 0;
    return Math.hypot(x - a[0] - t * vx, y - a[1] - t * vy);
  }
  // Eave datum from edge-of-roof lidar returns; do not infer it from a failed complex model.
  function baseline(L, r) {
    if (!L || !finite(L.ground_z_m)) return { ok: false, reason: 'no lidar ground datum' };
    var ground = L.ground_z_m, ring = L.ring_local || [], pts = L.points_full || [], near = [];
    if (ring.length >= 3) pts.forEach(function (p) {
      if (p[3] !== 6 || !p[5] || !finite(p[2])) return;
      var d = Infinity;
      for (var i = 0; i < ring.length; i++)
        d = Math.min(d, distance(p[0], p[1], ring[i], ring[(i + 1) % ring.length]));
      if (d <= 1.5) near.push(p[2]);
    });
    var z = near.length >= 10 ? qtile(near, 0.35) : null, source = 'lidar edge-return 35th percentile';
    var fit = r && r.lidar_model_fit;
    if (z == null && fit && finite(fit.eave_elev_ft) && finite(fit.median_ft) && fit.median_ft <= 1) {
      z = fit.eave_elev_ft / 3.280839895; source = 'lidar-to-facet fitted eave (median residual <= 1 ft)';
    }
    if (!finite(z) || z - ground < 2.5 || z - ground > 25)
      return { ok: false, reason: 'eave datum or height unsupported', ground_z_m: ground, edge_points: near.length };
    return { ok: true, ground_z_m: ground, eave_z_m: z, eave_height_m: z - ground,
      edge_points: near.length, source: source };
  }
  function estimate(al, ref, z) {
    if (!al || !al.applied || !['high', 'medium'].includes(al.confidence) ||
        !finite(al.dx_m) || !finite(al.dy_m) || !ref || !ref.ok || !finite(z)) return null;
    var above = z - ref.eave_z_m;
    if (above < 0.35 || above > 8) return null;
    var scale = above / ref.eave_height_m;
    if (scale > 0.75) return null;
    var dx = al.dx_m * scale, dy = al.dy_m * scale;
    if (Math.hypot(dx, dy) > 2.5) return null;
    return { dx_m: Math.round(dx * 1000) / 1000, dy_m: Math.round(dy * 1000) / 1000,
      height_above_eave_m: Math.round(above * 100) / 100, height_ratio: Math.round((1 + scale) * 1000) / 1000,
      status: 'NOT_PROVEN', method: 'ortho eave shift x (feature height - eave height) / eave height; overlay only' };
  }
  function annotate(result, L, al) {
    var ref = baseline(L, result), info = { status: 'NOT_PROVEN', applied: 0, checked: 0,
      reason: ref.ok ? 'experimental display correction; perspective and source registration not independently separated' : ref.reason,
      baseline: ref, method: 'height-relative ortho lean; aerial overlay only; no edits to polygons, dimensions, or billable totals' };
    if (!al || !al.applied || !['high', 'medium'].includes(al.confidence)) {
      info.reason = 'ortho alignment absent, unapplied, or low confidence'; return info;
    }
    if (!ref.ok) return info;
    function apply(d) {
      if (!d || d.source === 'user' || d.source === 'user-entered') return;
      info.checked++;
      var off = estimate(al, ref, d.z_m);
      if (off) { d.overlay_lean = off; info.applied++; }
    }
    (result.decks || []).forEach(apply);
    (result.dormers || []).forEach(apply);
    return info;
  }
  return { baseline: baseline, estimate: estimate, annotate: annotate };
});
