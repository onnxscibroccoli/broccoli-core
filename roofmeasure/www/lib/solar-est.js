/* solar-est.js — JS port of the ESTIMATE path of extras/solar.py (v0.1.x): Liu-Jordan isotropic-sky exposure index.
 * Offline; never reports kWh (PVWatts is not called from the app). Same constants and formulas as solar.py:
 *   equinox solar-noon beam, Erbs et al. 1982 diffuse fraction Kd(KT=0.5)=0.391, PVWatts default albedo 0.20,
 *   R = (1-fd)*Rb + fd*(1+cos b)/2 + rho*(1-cos b)/2, index = R / R_ref (south-facing, tilt = |lat|).
 * window.RoofSolar = { pitchToTiltDeg, estimateExposure, solarForFacets }
 */
(function (root) {
  'use strict';
  var FD = 0.391, ALB = 0.20, D2R = Math.PI / 180;
  function rnd(x, d) { if (x == null || !isFinite(x)) return null; var m = Math.pow(10, d == null ? 3 : d); return Math.round(x * m) / m; }
  function pitchToTiltDeg(p) {
    if (p == null || p === '') throw new Error('pitch is required');
    if (typeof p === 'number') return Math.atan(p / 12) / D2R;
    var s = String(p).trim();
    if (/deg$|°$/i.test(s)) return parseFloat(s.replace(/deg|°/ig, ''));
    if (s.indexOf('/') >= 0) { var a = s.split('/'), rise = +a[0], run = +a[1]; return run === 0 ? 90 : Math.atan(rise / run) / D2R; }
    return Math.atan(+s / 12) / D2R;
  }
  function estimateExposure(tiltDeg, azDeg, lat) {
    var phi = +lat, beta = tiltDeg * D2R, gamma = (((+azDeg) % 360) + 360) % 360 * D2R;
    var alpha = (90 - Math.abs(phi)) * D2R, gs = (phi >= 0 ? 180 : 0) * D2R, sa = Math.sin(alpha), ca = Math.cos(alpha);
    if (sa <= 1e-9) return { method: 'liu_jordan_isotropic_estimate', status: 'FAIL', exposure_index: null, kwh_claimed: false };
    function R(b, g) { var ct = sa * Math.cos(b) + ca * Math.sin(b) * Math.cos(gs - g); var rb = Math.max(ct, 0) / sa;
      return (1 - FD) * rb + FD * (1 + Math.cos(b)) / 2 + ALB * (1 - Math.cos(b)) / 2; }
    var r = R(beta, gamma), rr = R(Math.abs(phi) * D2R, (phi >= 0 ? 180 : 0) * D2R);
    return { method: 'liu_jordan_isotropic_estimate', status: 'PASS', labeled: 'ESTIMATE', R: rnd(r, 4), R_ref: rnd(rr, 4),
      exposure_index: rr > 0 ? rnd(r / rr, 4) : null, ac_annual_kwh_per_kw: null, kwh_claimed: false };
  }
  /* facets: [{id, downslope_bearing_deg|azimuth_deg, pitch|tilt_deg, area_sqft}] -> same shape as solar.py (estimate path) */
  function solarForFacets(facets, lat) {
    var out = [], notes = [], num = 0, den = 0;
    (facets || []).forEach(function (f) {
      var az = f.azimuth_deg != null ? f.azimuth_deg : (f.downslope_bearing_deg != null ? f.downslope_bearing_deg : f.azimuth);
      var tilt = f.tilt_deg != null ? f.tilt_deg : (f.pitch != null ? pitchToTiltDeg(f.pitch) : null);
      if (tilt == null || az == null) { notes.push('skipped facet ' + f.id + ': no tilt/azimuth'); return; }
      az = ((+az % 360) + 360) % 360;
      var e = estimateExposure(+tilt, az, lat), area = f.area_sqft != null ? +f.area_sqft : null;
      var it = { id: f.id, azimuth_deg: rnd(az, 2), tilt_deg: rnd(+tilt, 2), pitch: f.pitch, area_sqft: area != null ? rnd(area, 2) : null,
        exposure_index: e.exposure_index, exposure_index_source: 'liu_jordan_isotropic_estimate', kwh_claimed: false,
        estimate: { exposure_index: e.exposure_index, method: e.method, labeled: 'ESTIMATE', R: e.R }, pvwatts: { ac_annual_kwh_per_kw: null } };
      if (it.exposure_index != null && it.area_sqft) { num += it.exposure_index * it.area_sqft; den += it.area_sqft; }
      out.push(it);
    });
    return { status: out.length ? 'PASS' : 'FAIL', module: 'android solar-est.js (port of extras/solar.py estimate path)', facets: out,
      totals: { n_facets: out.length, area_sqft: den ? rnd(den, 2) : null, area_weighted_exposure_index: den ? rnd(num / den, 4) : null, roof_system_kwh: null },
      pvwatts: { tried: false, worked: false }, notes: notes.concat(['Liu-Jordan isotropic-sky ESTIMATE only; no kWh reported (PVWatts not called offline).']) };
  }
  root.RoofSolar = { pitchToTiltDeg: pitchToTiltDeg, estimateExposure: estimateExposure, solarForFacets: solarForFacets };
  if (typeof module === 'object' && module.exports) module.exports = root.RoofSolar;
})(typeof self !== 'undefined' ? self : this);
