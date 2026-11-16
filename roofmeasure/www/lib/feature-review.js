/* SPDX-License-Identifier: MIT
 * Human review of free-ortho/lidar roof feature candidates.
 * No machine-confidence upgrade: user marks describe a visual inspection, NOT field verification.
 * Geometry/billable totals untouched. No private addresses or training uploads.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.RoofFeatureReview = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  var KINDS = { auto: 1, skylight: 1, chimney: 1, vent: 1, ignore: 1 };
  function apply(r, tags) {
    var rf = r.roof_features || (r.roof_features = { skylights: [], decks: [], dormers: [], rejected: [], counts: {} });
    var reviews = (tags && tags.featureReviews) || {}, added = (tags && tags.featuresAdded) || [];
    var sk = (rf.skylights || []).slice(), chimneys = [], vents = [], hidden = [], addressed = {};
    var rejected = (rf.rejected || []).slice();
    var patches = (r.ortho_patches || []).concat((r.skylights || []).filter(function (k) {
      return !k.ortho_match && k.centroid_lonlat && !(r.ortho_patches || []).some(function (p) { return p.key === k.key; });
    }).map(function (k) { return { key: k.key, centroid_lonlat: k.centroid_lonlat,
      approx_w_ft: k.approx_w_ft || k.w_ft, approx_h_ft: k.approx_h_ft || k.h_ft,
      angle_deg: k.angle_deg || 0, source: k.source || 'lidar candidate' }; }));
    patches.forEach(function (p) {
      var v = reviews[p.key]; if (!v || !KINDS[v.kind] || v.kind === 'auto' && !v.rotate90) return;
      var kind = v.kind || 'auto', idx = sk.findIndex(function (x) { return x.key === p.key; });
      var base = idx < 0 ? { key: p.key, centroid_lonlat: p.centroid_lonlat,
        w_ft: p.approx_w_ft || null, h_ft: p.approx_h_ft || null, angle_deg: p.angle_deg || 0,
        source: p.source || 'candidate', counted: false } : sk[idx];
      var obj = Object.assign({}, base);
      if (v.rotate90) obj.angle_deg = (+obj.angle_deg || 0) + 90;
      if (kind === 'chimney' || kind === 'vent' || kind === 'ignore') {
        if (idx >= 0) sk.splice(idx, 1);
        if (kind === 'chimney') chimneys.push(Object.assign(obj, { type: 'chimney', source: 'user-identified from imagery', reviewed: true }));
        if (kind === 'vent') vents.push(Object.assign(obj, { type: 'vent', source: 'user-identified from imagery', reviewed: true }));
        if (kind === 'ignore') hidden.push(p.key);
      } else if (kind === 'skylight') {
        obj.source = 'user-identified from imagery (' + (p.source || 'candidate') + ')';
        obj.confidence = 'user review, not field verified';
        obj.counted = true; obj.reviewed = true; // counted only in the non-billable features list
        if (idx < 0) sk.push(obj); else sk[idx] = obj;
      } else if (idx >= 0) sk[idx] = obj;
      addressed[p.key] = true;
    });
    added.forEach(function (a, i) {
      if (!a || !a.centroid_lonlat || !['chimney', 'vent', 'skylight'].includes(a.type)) return;
      var o = { key: 'U' + i, centroid_lonlat: a.centroid_lonlat.slice(), type: a.type,
        source: 'user-placed marker on imagery', confidence: 'user visual review, NOT_PROVEN size',
        reviewed: true, counted: a.type === 'skylight', angle_deg: 0 };
      if (a.type === 'chimney') chimneys.push(o); else if (a.type === 'vent') vents.push(o); else sk.push(o);
    });
    // Keep human-reviewed candidate classification in the audit trail; it is not field ground truth.
    rf.skylights = sk; rf.chimneys = chimneys; rf.vents = vents; rf.reviews = { n: Object.keys(addressed).length + added.length,
      hidden: hidden, source: 'user visual corrections, NOT_PROVEN dimensions/pitch' };
    rf.rejected = rejected.filter(function (x) { return !addressed[x.key] || reviews[x.key].kind === 'auto'; });
    sk.forEach(function (k, i) { k.label = 'S' + (i + 1); });
    chimneys.forEach(function (k, i) { k.label = 'C' + (i + 1); });
    vents.forEach(function (k, i) { k.label = 'V' + (i + 1); });
    rf.counts = Object.assign({}, rf.counts, {
      skylights: sk.filter(function (k) { return k.counted; }).length,
      skylight_candidates_uncounted: sk.filter(function (k) { return !k.counted; }).length,
      chimneys_reviewed: chimneys.length, vents_reviewed: vents.length });
    return rf;
  }
  return { apply: apply };
});
