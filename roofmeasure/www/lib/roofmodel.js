/* SPDX-License-Identifier: MIT
 * RoofMeasure 0.1.7.3 — roof model choice for the facets lane (lib/roofmodel.js). Globals: window.RoofModel.
 * Models: 'simple' = gable with one ridge (lib/facets.js gable_method ridge_split; no hips or valleys),
 *         'wings'  = gable with wings / cross-gables (weighted straight skeleton; can create hips and valleys),
 *         'hip'    = equal-pitch straight skeleton (all edges eaves), 'flat'.
 * Auto (default):
 *   - with lidar roof points (lidar/pitch.js points_local): every candidate model's facets get a robust plane fit
 *     (lidar/facetfit.js). Score = lidar points explained by a facet plane whose aspect agrees with that facet
 *     (status 'fit') / all points inside the facets. Best score >= 0.6 wins ('lidar-verified'); near-ties
 *     (within 0.03) go to the simpler model (simple > wings > hip).
 *   - without lidar, or when no model reaches 0.6: 'simple' when the footprint fills >= 85% of its minimum-area
 *     bounding rectangle, else 'wings'. The model is flagged ASSUMED, and in 'wings'/'hip' every hip and valley is an
 *     unverified candidate that is NOT counted in the totals until the user confirms it (or picks the model).
 * The user can always pick the model (Roof model select); that choice is labelled 'user-selected'.
 */
(function (root) {
  'use strict';
  var VERSION = '0.1.7.3-roofmodel-1';
  var LABEL = { simple: 'Gable, one ridge', wings: 'Gable with wings / cross-gables', hip: 'Hip', flat: 'Flat' };
  function facetOpts(model) {
    if (model === 'simple') return { roof_type: 'gable', gable_method: 'ridge_split' };
    if (model === 'hip') return { roof_type: 'hip' };
    if (model === 'flat') return { roof_type: 'flat' };
    return { roof_type: 'gable' };
  }
  function coreRoofType(model) { return model === 'hip' ? 'hip' : model === 'flat' ? 'flat' : 'gable'; }
  function localXY(ring) {
    var lat0 = 0; ring.forEach(function (p) { lat0 += p[1]; }); lat0 /= ring.length;
    var ky = 364000, kx = ky * Math.cos(lat0 * Math.PI / 180), lon0 = ring[0][0], la0 = ring[0][1];
    return ring.map(function (p) { return [(p[0] - lon0) * kx, (p[1] - la0) * ky]; });
  }
  function area(P) { var s = 0; for (var i = 0; i < P.length; i++) { var a = P[i], b = P[(i + 1) % P.length]; s += a[0] * b[1] - b[0] * a[1]; } return Math.abs(s / 2); }
  /** footprint area / minimum-area bounding rectangle (edge-aligned rotating calipers). 1 = rectangle. */
  function rectangularity(ringLL) {
    var r = ringLL.slice(); if (r.length > 1 && r[0][0] === r[r.length - 1][0] && r[0][1] === r[r.length - 1][1]) r.pop();
    if (r.length < 3) return null;
    var P = localXY(r), A = area(P), best = Infinity;
    for (var i = 0; i < P.length; i++) {
      var a = P[i], b = P[(i + 1) % P.length], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy); if (L < 1e-6) continue;
      var ux = dx / L, uy = dy / L, mnU = Infinity, mxU = -Infinity, mnV = Infinity, mxV = -Infinity;
      P.forEach(function (q) { var u = q[0] * ux + q[1] * uy, v = -q[0] * uy + q[1] * ux; mnU = Math.min(mnU, u); mxU = Math.max(mxU, u); mnV = Math.min(mnV, v); mxV = Math.max(mxV, v); });
      best = Math.min(best, (mxU - mnU) * (mxV - mnV));
    }
    return best > 0 && isFinite(best) ? A / best : null;
  }
  function scoreFit(fit) {
    var tp = 0, good = 0;
    (fit.facets || []).forEach(function (x) { tp += x.n_points || 0; if (x.status === 'fit') good += x.n_inliers || 0; });
    return { score: tp ? good / tp : 0, points: tp, explained: good };
  }
  /** fin: tags.facetsInput result ({fp, opts}); lidar: estimatePitch result; user: select value. */
  function choose(fin, lidar, user, ringLL) {
    var F = root.RoofFacets, FF = root.RoofFacetFit;
    if (user && user !== 'auto' && LABEL[user]) return { model: user, source: 'user-selected', verified: true, label: LABEL[user], version: VERSION,
      reason: 'roof model picked by the user in the app' };
    var rect = ringLL ? rectangularity(ringLL) : null;
    var out = { version: VERSION, rectangularity: rect == null ? null : Math.round(rect * 1000) / 1000, scores: {} };
    if (lidar && /flat/.test(String(lidar.roof_shape_guess || '')) && /^lidar/.test(String(lidar.pitch_source || ''))) {
      return Object.assign(out, { model: 'flat', source: 'lidar-verified', verified: true, label: LABEL.flat, reason: 'lidar planes: flat roof' });
    }
    if (F && FF && lidar && lidar.points_local && fin) {
      ['simple', 'wings', 'hip'].forEach(function (m) {
        try {
          var f = F.computeFacets(fin.fp, Object.assign({}, fin.opts, facetOpts(m)));
          if (!f || f.unsupported || !f.facets || !f.facets.length) return;
          var s = scoreFit(FF.fitFacets(lidar, f.facets)); s.n_facets = f.facets.length; s.lines = f.lines; out.scores[m] = s;
        } catch (e) { out.scores[m] = { error: e.message, score: 0 }; }
      });
      var order = ['simple', 'wings', 'hip'], best = null;
      order.forEach(function (m) { var s = out.scores[m]; if (s && (best == null || s.score > out.scores[best].score + 0.03)) best = m; });
      Object.keys(out.scores).forEach(function (m) { out.scores[m].score = Math.round(out.scores[m].score * 1000) / 1000; });
      if (best && out.scores[best].score >= 0.6) {
        return Object.assign(out, { model: best, source: 'lidar-verified', verified: true, label: LABEL[best],
          reason: 'lidar per-facet plane fits explain ' + Math.round(out.scores[best].score * 100) + '% of roof points with model "' + LABEL[best] + '"' });
      }
      // whole-roof segmentation evidence: >= 2 confident hip lines and no confident gable-end rake steps -> hip
      var sg = lidar._seg || (root.RoofTags && root.RoofTags.lidarSeg ? root.RoofTags.lidarSeg(lidar) : null);
      var nHip = sg && sg.lines ? sg.lines.filter(function (l) { return l.type === 'hip' && l.confidence === 'high' && l.plan_length_ft >= 8; }).length : 0;
      out.seg_hip_lines = nHip;
      if (nHip >= 2 && out.scores.hip && out.scores.hip.score >= 0.45 && out.scores.hip.score >= (out.scores.simple ? out.scores.simple.score : 0)) {
        return Object.assign(out, { model: 'hip', source: 'lidar-verified', verified: true, label: LABEL.hip,
          reason: 'whole-roof lidar segmentation found ' + nHip + ' confident hip lines; per-facet fits explain ' + Math.round(out.scores.hip.score * 100) + '% with the hip model' });
      }
      out.lidar_note = 'lidar did not verify any model (best ' + (best ? LABEL[best] + ' ' + Math.round(out.scores[best].score * 100) + '%' : 'none') + ' < 60%)';
    }
    var m2 = rect != null && rect >= 0.85 ? 'simple' : 'wings';
    return Object.assign(out, { model: m2, source: 'assumed', verified: false, label: LABEL[m2],
      reason: (out.lidar_note ? out.lidar_note + '; ' : (lidar && lidar.points_local ? '' : 'no lidar; ')) + 'footprint fills ' + (rect == null ? '?' : Math.round(rect * 100)) +
        '% of its bounding rectangle -> ' + LABEL[m2] + ' assumed' + (m2 === 'simple' ? '' : '; hips/valleys are unverified candidates (not counted until confirmed)') });
  }
  var api = { choose: choose, facetOpts: facetOpts, coreRoofType: coreRoofType, rectangularity: rectangularity, LABEL: LABEL, VERSION: VERSION };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.RoofModel = api;
})(typeof self !== 'undefined' ? self : this);
