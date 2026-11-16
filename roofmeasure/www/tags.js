/* SPDX-License-Identifier: MIT
 * RoofMeasure 0.1.7.3 — visual categorization (user tags) + per-facet lidar plane pitch cross-check.
 * Pure helpers shared by app.js (live map) and report.js (PDF). Globals: window.RoofTags.
 * Tags are a human's visual categorization; they never change geometry. Only edge eave/rake (core overrides) and interior
 * ridge/hip/valley line types change report numbers; every other tag is listed with its own LF / area.
 */
(function () {
  'use strict';
  var EDGE_TAGS = { step_flashing: 'Step flashing', drip_edge: 'Drip edge', wall_flashing: 'Wall / headwall flashing', no_gutter: 'No gutter' };
  var AREA_TAGS = { steep: 'Steep-slope (shingle)', low_slope: 'Low-slope', flat: 'Flat', deck: 'Deck' };
  var LINE_TYPES = ['ridge', 'hip', 'valley'];
  var EXTRA_TYPES = ['wall_flashing', 'eave', 'rake']; // lidar-detected step edges (dormers, raised sections); user-retypable
  var ALL_TYPES = LINE_TYPES.concat(EXTRA_TYPES);
  function emptyTags() { return { edges: {}, lines: {}, linesKey: null, areas: {}, layers: {}, confirmed: {}, lengths: {}, added: [], skylights: [], skylightsDeleted: {}, dormers: {}, dormersAdded: [], facetPitch: {}, lineMoves: {} }; }
  function r1(x) { return Math.round(x * 10) / 10; }
  function r2(x) { return Math.round(x * 100) / 100; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function riseOf(p) { var m = /^\s*([\d.]+)\s*\/\s*12/.exec(String(p)); return m ? +m[1] : (isFinite(+p) ? +p : null); }
  function factorRise(rise) { return Math.sqrt(1 + (rise / 12) * (rise / 12)); }
  function pitchFromDeg(d) { var rise = Math.tan(d * Math.PI / 180) * 12; return { rise: r1(rise), label: (Math.round(rise * 2) / 2) + '/12' }; }
  function angDiff(a, b) { var d = Math.abs(((a - b) % 360 + 540) % 360 - 180); return d; }

  /* Same inputs report.js used in v0.1.7 (so the live map and the PDF see the same facets). */
  function facetsInput(r, lidar, useRidge) {
    var ridge = useRidge !== false && lidar && lidar.ridge_bearing_deg != null ? lidar.ridge_bearing_deg : undefined;
    return { fp: { type: 'Feature', geometry: r.footprint_geojson.geometry || r.footprint_geojson, properties: {} },
      opts: Object.assign({ pitch: r.pitch, roof_type: r.roof_type, ridge_bearing_deg: ridge, overhang_ft: r.overhang_ft || 0 },
        r.roof_model && window.RoofModel ? window.RoofModel.facetOpts(r.roof_model) : {}, ridgePointOpt(lidar, ridge)), ridge: ridge };
  }
  /* 0.1.7.3: whole-roof lidar segmentation (lidar/roofseg.js), computed once per lidar result. */
  function lidarSeg(lidar) {
    if (!lidar || !lidar.points_full || !window.RoofSeg) return null;
    if (!lidar._seg) { var sg; try { sg = window.RoofSeg.segment(lidar); } catch (e) { sg = { status: 'error', error: String(e && e.message || e), planes: [], lines: [], steps: [], skylights: [], notes: [] }; }
      Object.defineProperty(lidar, '_seg', { value: sg, enumerable: false, configurable: true }); }
    return lidar._seg;
  }
  /* the longest confident lidar ridge parallel to the ridge bearing places the ridge-split ridge (asymmetric gables) */
  function ridgePointOpt(lidar, ridge) {
    var sg = lidarSeg(lidar); if (!sg || ridge == null) return {};
    var best = null;
    (sg.lines || []).forEach(function (l) { if (l.type !== 'ridge' || l.confidence !== 'high') return;
      var a = l.coords_lonlat[0], b = l.coords_lonlat[1], k = Math.cos(a[1] * Math.PI / 180), br = (Math.atan2((b[0] - a[0]) * k, b[1] - a[1]) * 180 / Math.PI + 360) % 180;
      var d = Math.abs(br - ((ridge % 180) + 180) % 180); d = Math.min(d, 180 - d); if (d > 10) return;
      if (!best || l.plan_length_ft > best.plan_length_ft) best = l; });
    return best ? { ridge_point_lonlat: [(best.coords_lonlat[0][0] + best.coords_lonlat[1][0]) / 2, (best.coords_lonlat[0][1] + best.coords_lonlat[1][1]) / 2] } : {};
  }
  /* Reconcile the footprint model with lidar lines: lidar wins where confident (confirms or retypes a model line),
   * the model fills gaps; lidar lines the model lacks (dormer ridges, raised-section steps) are appended as segments
   * with source 'lidar' (counted when confidence is high and no plane is a flagged small plane; otherwise candidates). */
  function reconcileLidar(f, lidar, ringLL) {
    var sg = lidarSeg(lidar); if (!f || !sg || sg.status !== 'ok' || !Array.isArray(f.line_segments)) return null;
    var lat0 = null; (f.line_segments[0] && f.line_segments[0].coords_lonlat || sg.lines.concat(sg.steps).map(function (l) { return l.coords_lonlat[0]; })).some(function (p) { lat0 = p[1]; return true; });
    if (lat0 == null) return null;
    var kx = Math.cos(lat0 * Math.PI / 180) * 364567.2, ky = 364567.2, lon0 = null;
    function xy(p) { if (lon0 == null) lon0 = p[0]; return [(p[0] - lon0) * kx, (p[1] - lat0) * ky]; }
    function seg2(c) { return [xy(c[0]), xy(c[1])]; }
    function dps(p, a, b) { var dx = b[0] - a[0], dy = b[1] - a[1], L = dx * dx + dy * dy, t = L ? ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L : 0; t = Math.max(0, Math.min(1, t)); return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy); }
    function brg(s) { return (Math.atan2(s[1][0] - s[0][0], s[1][1] - s[0][1]) * 180 / Math.PI + 360) % 180; }
    function overlap(s, l) { // fraction of s within 3.3 ft of l, directions within 15 deg
      var d = Math.abs(brg(s) - brg(l)); d = Math.min(d, 180 - d); if (d > 20) return 0; var hit = 0;
      for (var t = 0; t <= 10; t++) { var p = [s[0][0] + (s[1][0] - s[0][0]) * t / 10, s[0][1] + (s[1][1] - s[0][1]) * t / 10]; if (dps(p, l[0], l[1]) <= 6) hit++; }
      return hit / 11; }
    var small = {}, rise = {}; (sg.planes || []).forEach(function (p) { small[p.id] = p.small; var m = /^(\d+(?:\.\d+)?)\/12$/.exec(String(p.pitch || '')); rise[p.id] = m ? +m[1] : null; });
    var polys = (f.facets || []).map(function (x) { return x.polygon_lonlat ? ringOf(x.polygon_lonlat).map(xy) : null; }).filter(Boolean);
    function inRoof(p) { if (!polys.length) return true; for (var k = 0; k < polys.length; k++) { var P = polys[k]; if (pointInRing(p, P)) return true;
      for (var j = 0; j + 1 < P.length; j++) if (dps(p, P[j], P[j + 1]) <= 0.5) return true; } return false; }
    function clipToRoof(sg2) { var N = 40, best = null, run = null;
      for (var t = 0; t <= N; t++) { var p = [sg2[0][0] + (sg2[1][0] - sg2[0][0]) * t / N, sg2[0][1] + (sg2[1][1] - sg2[0][1]) * t / N];
        if (inRoof(p)) { if (!run) run = [t, t]; else run[1] = t; if (!best || run[1] - run[0] > best[1] - best[0]) best = run.slice(); } else run = null; }
      if (!best) return null; var fr = (best[1] - best[0]) / N; if (fr * Math.hypot(sg2[1][0] - sg2[0][0], sg2[1][1] - sg2[0][1]) < 2) return null;
      var A = [sg2[0][0] + (sg2[1][0] - sg2[0][0]) * best[0] / N, sg2[0][1] + (sg2[1][1] - sg2[0][1]) * best[0] / N], B = [sg2[0][0] + (sg2[1][0] - sg2[0][0]) * best[1] / N, sg2[0][1] + (sg2[1][1] - sg2[0][1]) * best[1] / N];
      return [A, B, fr]; }
    var model = f.line_segments.filter(function (s) { return s.coords_lonlat && LINE_TYPES.indexOf(s.type) >= 0; });
    var added = 0, confirmed = 0, retyped = 0, doubtful = 0;
    // 0.1.7.4: building axes from the roofprint (length-weighted circular mean of 4 x edge bearing); a lidar ridge
    // more than 8 deg off both axes (e.g. a diagonal "ridge" across a wing), or between planes 6/12+ apart, is doubtful and stays a candidate
    var axis = null;
    if (Array.isArray(ringLL) && ringLL.length > 3) { var cs = 0, sn = 0; for (var e = 0; e + 1 < ringLL.length; e++) { var A = xy(ringLL[e]), B = xy(ringLL[e + 1]), Le = Math.hypot(B[0] - A[0], B[1] - A[1]);
      var th = Math.atan2(B[0] - A[0], B[1] - A[1]) * 4; cs += Le * Math.cos(th); sn += Le * Math.sin(th); } axis = ((Math.atan2(sn, cs) / 4) * 180 / Math.PI + 360) % 90; }
    function offAxis(L2) { if (axis == null) return 0; var d = Math.abs(brg(L2) % 90 - axis); return Math.min(d, 90 - d); }
    sg.lines.concat(sg.steps.filter(function (s) { return !s.on_footprint; })).forEach(function (l) {
      var L2 = seg2(l.coords_lonlat), strong = l.confidence === 'high' && !(l.planes || [l.upper, l.lower]).some(function (id) { return small[id]; });
      var hit = null, best = 0;
      model.forEach(function (s) { var o = Math.max(overlap(seg2(s.coords_lonlat), L2), overlap(L2, seg2(s.coords_lonlat))); if (o > best) { best = o; hit = s; } });
      if (hit && best >= 0.35) {
        if (strong) { hit.lidar_support = l.type;
          // lidar wins on TYPE and confirmation; the footprint-snapped model keeps its length/position (lidar line ends are trimmed
          // where gable-end points thin out, e.g. 15 Ward St ridge 45.4 lidar vs 48.4 roofprint gable to gable)
          if (hit.type === l.type) { hit.lidar_confirmed = true; confirmed++; }
          else if (LINE_TYPES.indexOf(l.type) >= 0 && !hit.user_tagged && f.roof_model_info && f.roof_model_info.verified) { hit.auto_type = hit.auto_type || hit.type; hit.type = l.type; hit.lidar_retyped = true; hit.lidar_confirmed = true; retyped++; } }
        return; }
      // clip to the roofprint (+0.5 ft): lidar lines can run past it where the cloud buffer or a porch/neighbour continues
      var cl = clipToRoof(L2); if (!cl) return;
      var doubt = null;
      var pl = l.planes || [l.upper, l.lower], dr = pl.length === 2 && rise[pl[0]] != null && rise[pl[1]] != null ? Math.abs(rise[pl[0]] - rise[pl[1]]) : 0;
      if (l.type === 'ridge' && offAxis(L2) > 8) doubt = 'ridge ' + Math.round(offAxis(L2)) + '° off the building axes (diagonal across the roof)' + (dr >= 3 ? '; its two planes differ by ' + dr + '/12' : '');
      else if (l.type === 'ridge' && dr >= 6) doubt = 'ridge between planes of very different pitch (' + pl.map(function (id) { return rise[id] + '/12'; }).join(' vs ') + ')';
      else if (cl[2] < 0.75) doubt = Math.round((1 - cl[2]) * 100) + '% of the line runs outside the roofprint';
      if (doubt) { strong = false; doubtful++; }
      var c0 = [lon0 + cl[0][0] / kx, lat0 + cl[0][1] / ky], c1 = [lon0 + cl[1][0] / kx, lat0 + cl[1][1] / ky];
      l = Object.assign({}, l, { coords_lonlat: [c0, c1], length_ft: r2(l.length_ft * cl[2]), plan_length_ft: r2(l.plan_length_ft * cl[2]), clipped: cl[2] < 0.999 });
      f.line_segments.push({ type: l.type, auto_type: l.type, length_ft: l.length_ft, plan_length_ft: l.plan_length_ft, coords_lonlat: l.coords_lonlat, weight: 1,
        source: 'lidar', lidar_source: l.source + (l.subtype ? ' — ' + l.subtype : ''), lidar_conf: l.confidence, lidar_strong: strong, lidar_doubt: doubt, drop_ft: l.drop_ft, planes: l.planes || [l.upper, l.lower] });
      added++;
    });
    f.lidar_seg_summary = { version: sg.version, n_planes: sg.planes.length, n_small: sg.planes.filter(function (p) { return p.small; }).length, coverage: sg.coverage,
      lines_added: added, lines_doubtful: doubtful, axis_deg: axis == null ? null : Math.round(axis * 10) / 10, model_lines_confirmed: confirmed, model_lines_retyped: retyped, skylight_candidates: (sg.skylights || []).length };
    return f.lidar_seg_summary;
  }
  /* 0.1.7.5: roof deck / flat-section candidates from the lidar segmentation (NOT_PROVEN). A low-slope plane (<= 1.5/12)
   * of 25+ sq ft that is mostly inside the roofprint but is not most of the roof is a roof deck or flat section; decks over
   * living space usually sit on a rubber (EPDM) or membrane roof, so it is flagged to inspect. */
  function decks(sg, ringLL) {
    if (!sg || !sg.planes) return [];
    var tot = 0; sg.planes.forEach(function (p) { tot += p.plan_area_sqft_approx || 0; });
    var out = [];
    sg.planes.forEach(function (p) {
      if (!(p.rise_raw <= 1.5) || (p.plan_area_sqft_approx || 0) < 25 || p.inside_frac < 0.6 || !p.outline_lonlat || p.outline_lonlat.length < 3) return;
      if (tot && p.plan_area_sqft_approx > 0.6 * tot) return; // a flat ROOF, not a deck
      var A = 0, O = p.outline_lonlat, kx = Math.cos(O[0][1] * Math.PI / 180) * 364000, ky = 364000;
      for (var i = 0; i < O.length; i++) { var a = O[i], b = O[(i + 1) % O.length]; A += (a[0] * kx) * (b[1] * ky) - (b[0] * kx) * (a[1] * ky); }
      var rc = p.rect && p.rect.area_sqft > 0 ? p.rect : null; // 0.1.7.6: robust rectangle (the hull is inflated by stray edge points)
      out.push({ key: 'K' + out.length, plane: p.id, outline_lonlat: rc ? rc.outline_lonlat : O, area_sqft: rc ? rc.area_sqft : Math.round(Math.abs(A) / 2), hull_area_sqft: Math.round(Math.abs(A) / 2),
        w_ft: rc ? rc.w_ft : null, h_ft: rc ? rc.h_ft : null, outline_method: rc ? rc.method : 'convex hull', points_area_sqft: p.plan_area_sqft_approx, pitch: p.pitch, z_m: p.z_m,
        n_points: p.n_points, centroid_lonlat: p.centroid_lonlat, type: 'roof deck / flat section', confidence: p.small ? 'low' : 'medium',
        inspect: 'Possible rubber (EPDM) or membrane roof under the deck or flat section: inspect seams, drains and flashing; replace with the roof if worn.',
        source: 'USGS 3DEP lidar low-slope plane ' + p.id });
    });
    return out;
  }
  /* 0.1.7.4: dormer candidates from the whole-roof lidar segmentation (NOT_PROVEN).
   * gable dormer: a lidar ridge between two minor planes facing opposite ways; shed dormer: a minor plane facing the
   * same way as a major plane but at least 2/12 flatter. Dormer gutters (often with returns) collect debris and can
   * let water in, so each dormer carries gutter fields and an inspect-and-clean flag. User edits (tags.dormers,
   * tags.dormersAdded) keep / size / add them. */
  function dormers(sg, tags) {
    var out = [], ed = (tags && tags.dormers) || {}, P = (sg && sg.planes) || [], byId = {};
    P.forEach(function (p) { byId[p.id] = p; });
    var tot = P.reduce(function (a, p) { return a + (+p.plan_area_sqft_approx || 0); }, 0) || 1;
    function major(p) { return p.plan_area_sqft_approx >= 0.15 * tot; }
    function minor(p) { return p && !major(p) && p.aspect_deg != null && p.plan_area_sqft_approx >= 12 && p.plan_area_sqft_approx <= 400; }
    function ad(a, b) { var d = Math.abs(a - b) % 360; return Math.min(d, 360 - d); }
    var used = {};
    (sg && sg.lines || []).forEach(function (l) {
      if (l.type !== 'ridge' || !l.planes || l.planes.length < 2) return; var A = byId[l.planes[0]], B = byId[l.planes[1]];
      if (!minor(A) || !minor(B) || ad(A.aspect_deg, B.aspect_deg) < 140) return;
      used[A.id] = used[B.id] = 1;
      out.push({ type: 'gable dormer', planes: [A.id, B.id], pitch: A.pitch, ridge_lf: l.plan_length_ft, coords_lonlat: l.coords_lonlat,
        centroid_lonlat: [(l.coords_lonlat[0][0] + l.coords_lonlat[1][0]) / 2, (l.coords_lonlat[0][1] + l.coords_lonlat[1][1]) / 2],
        gutter_lf_est: r2((+A.strike_len_ft || 0) + (+B.strike_len_ft || 0)), confidence: l.confidence === 'high' ? 'medium' : 'low' });
    });
    P.forEach(function (p) {
      if (used[p.id] || !minor(p)) return;
      var host = P.filter(function (q) { return major(q) && q.aspect_deg != null && ad(q.aspect_deg, p.aspect_deg) <= 30 && q.rise_raw - p.rise_raw >= 2; })[0];
      if (!host) return;
      out.push({ type: 'shed dormer', planes: [p.id], host: host.id, pitch: p.pitch, host_pitch: host.pitch, ridge_lf: null, centroid_lonlat: p.centroid_lonlat,
        gutter_lf_est: +p.strike_len_ft || null, confidence: p.small ? 'low' : 'medium' });
    });
    out = out.slice(0, 12).map(function (d, i) {
      var k = 'D' + i, e = ed[k] || {};
      return Object.assign(d, { key: k, source: 'lidar', kept: !!e.keep, returns: e.returns || 'unknown', gutter_lf: e.gutter_lf > 0 ? +e.gutter_lf : d.gutter_lf_est,
        inspect_clean: true, status: e.keep ? 'confirmed by user' : 'candidate (NOT_PROVEN, not counted)' });
    });
    ((tags && tags.dormersAdded) || []).forEach(function (a, j) {
      out.push({ key: 'UD' + j, type: a.type || 'dormer', source: 'user', kept: true, returns: a.returns || 'unknown', gutter_lf: +a.gutter_lf || null,
        note: a.note || '', inspect_clean: true, status: 'user-entered' });
    });
    return out;
  }
  function facetsKey(r, lidar, useRidge) {
    var i = facetsInput(r, lidar, useRidge); return JSON.stringify([i.fp.geometry.coordinates, i.opts]);
  }
  function liveFacets(r, lidar, useRidge) {
    var F = window.RoofFacets; if (!F || typeof F.computeFacets !== 'function' || !r) return null;
    var i = facetsInput(r, lidar, useRidge);
    try { var f = F.computeFacets(i.fp, i.opts); if (f && !f.unsupported) { f.roof_model_info = r.roof_model_info || null; if (r.use_lidar_lines !== false) reconcileLidar(f, lidar, window.RoofCalc && r.footprint_geojson ? window.RoofCalc.extractRing(r.footprint_geojson) : null); return f; } return null; } catch (e) { return null; }
  }
  /* Apply user interior-line types; recompute ridge/hip/valley LF from the segments. Returns list of changes.
   * 0.1.7.3: type 'none' = deleted by the user (not counted); hips/valleys of an ASSUMED wings/hip model are unverified
   * candidates (not counted) unless the user confirmed or retyped them; user-added lines (tags.added) are counted. */
  function applyLineTags(f, tags, key) {
    var changes = [];
    if (!f || !Array.isArray(f.line_segments)) return changes;
    var segs = f.line_segments, conf = (tags && tags.confirmed) || {};
    if (tags && tags.linesKey === key) Object.keys(tags.lines).forEach(function (k) {
      var s = segs[+k], t = tags.lines[k]; if (!s || !t || (ALL_TYPES.indexOf(t.type) < 0 && t.type !== 'none')) return;
      if (LINE_TYPES.indexOf(s.auto_type || s.type) < 0 && s.source !== 'lidar') return; // never re-type rake/wall arcs of the skeleton
      if (s.source !== 'lidar' && EXTRA_TYPES.indexOf(t.type) >= 0) return;
      if ((s.auto_type || s.type) !== t.type) changes.push({ i: +k, from: s.auto_type || s.type, to: t.type === 'none' ? 'deleted' : t.type, length_ft: s.length_ft, layer: t.layer });
      if (!s.auto_type) s.auto_type = s.type; s.type = t.type; s.user_tagged = true; s.deleted = t.type === 'none';
    });
    // 0.1.7.4: line endpoints moved in the 3-D editor (plan position; length scaled by the plan-length change)
    if (tags && tags.linesKey === key && tags.lineMoves) Object.keys(tags.lineMoves).forEach(function (k) {
      var s = segs[+k], mv = tags.lineMoves[k]; if (!s || !mv || !mv.coords_lonlat || !s.coords_lonlat) return;
      function pl(c) { var kx = Math.cos(c[0][1] * Math.PI / 180) * 364567.2; return Math.hypot((c[1][0] - c[0][0]) * kx, (c[1][1] - c[0][1]) * 364567.2); }
      var p0 = pl(s.coords_lonlat), p1 = pl(mv.coords_lonlat); if (!(p1 > 0.5)) return;
      var ratio = p0 > 0.01 ? (+s.length_ft || p0) / p0 : 1, old = s.length_ft;
      s.coords_lonlat = mv.coords_lonlat; s.plan_length_ft = r2(p1); s.length_ft = r2(p1 * ratio); s.user_moved = true; s.user_tagged = true;
      changes.push({ i: +k, from: s.type + ' ' + (+old).toFixed(1) + ' ft', to: 'moved in 3-D editor, ' + s.length_ft.toFixed(1) + ' ft', length_ft: s.length_ft, layer: mv.layer || '3-D editor' });
    });
    var mi = f.roof_model_info, unver = mi && !mi.verified && (mi.model === 'wings' || mi.model === 'hip');
    var verified = !!(mi && mi.verified);
    var cand = { hip_lf: 0, valley_lf: 0, n: 0 };
    segs.forEach(function (s, i) {
      // lidar lines count only when confident, not wall flashing, and (the roof model is lidar-verified, or it is a ridge: a confident
      // plane-intersection ridge needs ridge cap whatever the model)
      // (flashing needs a person to confirm that a sidewall really rises above the roof plane); otherwise candidates
      if (s.source === 'lidar') s.unverified = !!(!(s.lidar_strong && s.type !== 'wall_flashing' && (verified || s.type === 'ridge')) && !s.user_tagged && !conf['L' + i]);
      else s.unverified = !!(unver && !s.user_tagged && !conf['L' + i] && (s.type === 'hip' || s.type === 'valley'));
      if (s.unverified && !s.deleted) { cand[s.type + '_lf'] = (cand[s.type + '_lf'] || 0) + s.length_ft; cand.n++; }
    });
    var added = (tags && Array.isArray(tags.added)) ? tags.added.filter(function (a) { return a && ALL_TYPES.indexOf(a.type) >= 0 && +a.length_ft > 0; }) : [];
    if (f.lines) {
      LINE_TYPES.forEach(function (t) { f.lines[t + '_lf'] = 0; });
      var cnt = {}; LINE_TYPES.forEach(function (t) { cnt[t] = 0; });
      if (f.lines._wf_base == null) Object.defineProperty(f.lines, '_wf_base', { value: f.lines.wall_flashing_lf || 0, enumerable: false, writable: true });
      EXTRA_TYPES.forEach(function (t) { f.lines['lidar_' + t + '_lf'] = 0; });
      segs.forEach(function (s) { if (s.unverified || s.deleted) return;
        if (LINE_TYPES.indexOf(s.type) >= 0) { f.lines[s.type + '_lf'] += s.length_ft; cnt[s.type] += (s.weight == null ? 1 : s.weight); }
        else if (s.source === 'lidar' && EXTRA_TYPES.indexOf(s.type) >= 0) f.lines['lidar_' + s.type + '_lf'] += s.length_ft; });
      EXTRA_TYPES.forEach(function (t) { f.lines['lidar_' + t + '_lf'] = r2(f.lines['lidar_' + t + '_lf']); });
      // facets-model wall flashing (skeleton step walls) only counts when the model is verified; otherwise it is a candidate
      var wfBase = verified ? f.lines._wf_base : 0;
      if (!verified && f.lines._wf_base) { cand.wall_flashing_model_lf = (cand.wall_flashing_model_lf || 0) + f.lines._wf_base; }
      f.lines.wall_flashing_lf = r2(wfBase + f.lines.lidar_wall_flashing_lf);
      added.forEach(function (a) { if (LINE_TYPES.indexOf(a.type) >= 0) { f.lines[a.type + '_lf'] += +a.length_ft; cnt[a.type] += 1; } else { f.lines['lidar_' + a.type + '_lf'] = r2(f.lines['lidar_' + a.type + '_lf'] + +a.length_ft); if (a.type === 'wall_flashing') f.lines.wall_flashing_lf = r2(f.lines.wall_flashing_lf + +a.length_ft); } });
      LINE_TYPES.forEach(function (t) { f.lines[t + '_lf'] = r2(f.lines[t + '_lf']); if (f.line_counts) f.line_counts[t] = cnt[t]; });
    }
    f.line_candidates = { n: cand.n }; Object.keys(cand).forEach(function (k) { if (k !== 'n') f.line_candidates[k] = r2(cand[k]); });
    if (f.line_candidates.hip_lf == null) f.line_candidates.hip_lf = 0; if (f.line_candidates.valley_lf == null) f.line_candidates.valley_lf = 0;
    f.added_lines = added.map(function (a) { return { type: a.type, length_ft: r2(+a.length_ft), note: a.note || '', source: a.source || 'user-entered' }; });
    return changes;
  }
  function ringOf(poly) { return Array.isArray(poly && poly[0] && poly[0][0]) ? poly[0] : poly; }
  function pointInRing(p, P) {
    var c = false;
    for (var i = 0, j = P.length - 1; i < P.length; j = i++) {
      if (((P[i][1] > p[1]) !== (P[j][1] > p[1])) && (p[0] < (P[j][0] - P[i][0]) * (p[1] - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0])) c = !c;
    }
    return c;
  }
  function facetAt(f, ll) {
    if (!f || !f.facets) return null;
    for (var i = 0; i < f.facets.length; i++) { var x = f.facets[i]; if (x.polygon_lonlat && pointInRing(ll, ringOf(x.polygon_lonlat))) return x; }
    return null;
  }
  /* (d) per-facet pitch from lidar RANSAC planes: match each facet's downslope bearing to the plane aspect (±35°). Cross-check only. */
  function matchPlanes(facets, planes, tolDeg) {
    tolDeg = tolDeg || 35;
    var P = (planes || []).filter(function (p) { return p.slope_deg >= 4 && p.slope_deg <= 65; });
    return (facets || []).map(function (x) {
      var best = null;
      if (x.downslope_bearing_deg != null) P.forEach(function (p) {
        var d = angDiff(p.aspect_deg, x.downslope_bearing_deg);
        if (d <= tolDeg && (!best || p.n > best.p.n)) best = { p: p, d: d };
      });
      var out = { id: x.id, model_pitch: x.model_pitch || x.pitch, plan_area_sqft: x.plan_area_sqft, model_area_sqft: x.model_area_sqft || x.area_sqft, downslope_bearing_deg: x.downslope_bearing_deg };
      if (best) {
        var pp = pitchFromDeg(best.p.slope_deg), fac = 1 / Math.cos(best.p.slope_deg * Math.PI / 180);
        Object.assign(out, { lidar_pitch: pp.label, lidar_slope_deg: best.p.slope_deg, lidar_aspect_deg: best.p.aspect_deg, aspect_diff_deg: r1(best.d),
          plane_points: best.p.n, plane_rms_m: best.p.rms_m, lidar_area_sqft: r1(x.plan_area_sqft * fac) });
      }
      return out;
    });
  }

  /* Build the report payload from result r (after facets), the tag store and the lidar result. */
  function reportPayload(r, tags, lidar, lineChanges) {
    tags = tags || emptyTags(); var conf = tags.confirmed || {};
    var pf = +r.pitch_factor || 1;
    var sl = function (e) { return e.sloped_length_ft != null ? +e.sloped_length_ft : (e.type === 'rake' ? e.length_ft * pf : e.length_ft); };
    var edgeRows = [], tagLf = {};
    Object.keys(EDGE_TAGS).forEach(function (k) { tagLf[k] = { plan: 0, sloped: 0, n: 0, edges: [] }; });
    (r.edges || []).forEach(function (e) {
      var t = tags.edges[e.i]; var keys = t ? Object.keys(t).filter(function (k) { return EDGE_TAGS[k]; }) : [];
      var manual = e.auto === false || e.length_source === 'user edit';
      if (!keys.length && !manual) return;
      var sloped = sl(e);
      keys.forEach(function (k) { var a = tagLf[k]; a.plan += e.length_ft; a.sloped += sloped; a.n++; a.edges.push(e.i); });
      edgeRows.push({ i: e.i, type: e.type, auto_type: e.auto_type, manual: manual, plan_ft: r2(e.length_ft), sloped_ft: r2(sloped),
        tags: keys.map(function (k) { return EDGE_TAGS[k]; }), layer: keys.map(function (k) { return t[k]; }).filter(Boolean)[0] || (tags.layers['edge-type:' + e.i] || '') });
    });
    var facets = r.facets || [];
    var planeRows = lidar && Array.isArray(lidar.planes) && lidar.planes.length && facets.length ? matchPlanes(facets, lidar.planes) : [];
    var areaRows = [], byCat = {};
    var whole = tags.areas.ALL;
    var units = facets.length ? facets : [{ id: 'Whole roof', plan_area_sqft: r.roof_plan_area_sqft, area_sqft: r.roof_area_sqft, pitch: r.pitch }];
    var stale = Object.keys(tags.areas).filter(function (k) { return k !== 'ALL' && !facets.some(function (x) { return x.id === k; }); });
    units.forEach(function (x) {
      var t = tags.areas[x.id] || whole; if (!t) return;
      areaRows.push({ id: x.id, tag: AREA_TAGS[t.tag] || t.tag, plan_area_sqft: x.plan_area_sqft, area_sqft: x.area_sqft, pitch: x.pitch, layer: t.layer });
      var b = byCat[t.tag] = byCat[t.tag] || { label: AREA_TAGS[t.tag] || t.tag, area: 0, plan: 0, n: 0 };
      b.area += +x.area_sqft || 0; b.plan += +x.plan_area_sqft || 0; b.n++;
    });
    var layersUsed = {};
    Object.keys(tags.edges).forEach(function (i) { Object.keys(tags.edges[i]).forEach(function (k) { if (tags.edges[i][k]) layersUsed[tags.edges[i][k]] = 1; }); });
    Object.keys(tags.lines).forEach(function (i) { if (tags.lines[i].layer) layersUsed[tags.lines[i].layer] = 1; });
    Object.keys(tags.areas).forEach(function (i) { if (tags.areas[i].layer) layersUsed[tags.areas[i].layer] = 1; });
    Object.keys(tags.layers).forEach(function (k) { if (tags.layers[k]) layersUsed[tags.layers[k]] = 1; });
    Object.keys(tagLf).forEach(function (k) { tagLf[k].plan = r1(tagLf[k].plan); tagLf[k].sloped = r1(tagLf[k].sloped); });
    Object.keys(byCat).forEach(function (k) { byCat[k].area = r1(byCat[k].area); byCat[k].plan = r1(byCat[k].plan); });
    // per-measurement data source (every edge and interior line, auto-detected from free data only)
    var lidarOn = /^lidar/.test(String(r.pitch_source || ''));
    var M = { ridges_per_wing: 'eave/rake from USGS 3DEP lidar ridge bearings per wing + roofprint', ridge_parallel_eave: 'eave/rake from ' + (lidarOn ? 'USGS 3DEP lidar ' : '') + 'ridge bearing + roofprint',
      wing_depth_heuristic: 'eave/rake from 2-D outline heuristic (no ridge)', all_eave: 'all eaves (roof type ' + r.roof_type + ')' };
    var typeSrc = M[r.eave_rake_method] || String(r.eave_rake_method || 'auto');
    var lenSrc = 'roofprint/outline: ' + (r.source || 'manual outline');
    var sources = (r.edges || []).map(function (e) {
      var retag = e.auto === false, c = conf['E' + e.i];
      var le = e.length_source === 'user edit';
      return { kind: 'edge', id: 'E' + e.i, type: e.type, length_ft: r2(sl(e)), length_basis: e.type === 'rake' ? 'sloped (' + (e.sloped_basis || 'plan × pitch factor ' + pf) + ')' : 'plan (eaves are level)',
        length_source: le ? 'user edit (auto ' + (+e.length_ft_auto).toFixed(1) + ' ft plan)' : lenSrc, type_source: retag ? 'user retag (auto ' + e.auto_type + ')' : typeSrc,
        status: retag || le ? 'user-set' : (c ? 'confirmed by user' : 'auto (unconfirmed)') };
    });
    (r.line_segments || []).forEach(function (sg, i) {
      if (sg.unverified || sg.deleted) return; // candidates/deleted lines are listed in the report appendix, not here
      if (LINE_TYPES.indexOf(sg.type) < 0 && sg.source !== 'lidar') return;
      var c = conf['L' + i];
      var mi = r.roof_model_info || {};
      var lid = sg.source === 'lidar';
      sources.push({ kind: 'line', id: 'L' + i, type: sg.type, length_ft: r2(sg.length_ft), length_basis: lid ? 'lidar line (3-D)' : 'sloped 3-D (facets model)',
        length_source: lid ? 'USGS 3DEP lidar segmentation' : 'facets model "' + (mi.label || r.roof_model || '?') + '" (' + (mi.source || '?') + ')',
        type_source: sg.user_tagged ? 'user retag (auto ' + sg.auto_type + ')' : (lid ? 'lidar' : sg.lidar_confirmed ? 'facets model, lidar-confirmed' : 'facets model'),
        status: sg.user_tagged ? 'user-set' : (sg.unverified ? 'UNVERIFIED candidate (not counted)' : (c ? 'confirmed by user' : 'auto (unconfirmed)')) });
    });
    (r.added_lines || []).forEach(function (a, j) {
      sources.push({ kind: 'line', id: 'U' + j, type: a.type, length_ft: a.length_ft, length_basis: 'as entered', length_source: 'user-entered' + (a.note ? ' (' + a.note + ')' : ''),
        type_source: 'user', status: 'user-set' });
    });
    var nConf = sources.filter(function (x) { return x.status !== 'auto (unconfirmed)' && !/^UNVERIFIED/.test(x.status); }).length;
    return { per_facet_used: !!r.per_facet_pitch_used, sources: sources, n_checked: nConf, pitch_source: r.pitch_source, edge_rows: edgeRows, tag_lf: tagLf, line_changes: lineChanges || [], area_rows: areaRows, area_by_category: byCat,
      stale_area_tags: stale, plane_rows: planeRows, facet_fit: r.facet_fit || null, layers_used: Object.keys(layersUsed),
      any: edgeRows.length > 0 || (lineChanges || []).length > 0 || areaRows.length > 0 };
  }

  function sectionHtml(p) {
    if (!p) return '';
    var H = ['<section aria-labelledby="h-tags"><h2 id="h-tags">Visual categorization (user tags)</h2>'];
    if (!p.any) H.push('<p class="note">No edges, lines or areas were tagged by the user; eave/rake and ridge/hip/valley are the automatic classification.</p>');
    else {
      H.push('<p class="note">Tags are a person\'s visual categorization made in the app. Geometry and lengths come only from free sources ' +
        '(MassGIS / USGS / footprint or manual trace). Layers on screen while tagging: ' + esc(p.layers_used.join(', ') || 'not recorded') +
        '.</p>');
      if (p.edge_rows.length) {
        H.push('<table><thead><tr><th scope="col">Edge</th><th scope="col">Type</th><th scope="col">Plan ft</th><th scope="col">Sloped ft</th><th scope="col">Tags</th></tr></thead><tbody>');
        p.edge_rows.forEach(function (e) {
          H.push('<tr><th scope="row" class="n">' + e.i + '</th><td>' + esc(e.type) + (e.manual ? ' (user; auto ' + esc(e.auto_type) + ')' : '') + '</td><td class="n">' +
            e.plan_ft.toFixed(1) + '</td><td class="n">' + e.sloped_ft.toFixed(1) + '</td><td>' + esc(e.tags.join(', ') || '—') + '</td></tr>');
        });
        H.push('</tbody></table>');
        var tl = Object.keys(p.tag_lf).filter(function (k) { return p.tag_lf[k].n; });
        if (tl.length) {
          H.push('<table><thead><tr><th scope="col">Tag</th><th scope="col">Edges</th><th scope="col">Plan LF</th><th scope="col">LF (rake sloped)</th></tr></thead><tbody>');
          tl.forEach(function (k) { var a = p.tag_lf[k]; H.push('<tr><th scope="row">' + esc(EDGE_TAGS[k]) + '</th><td>' + a.edges.join(', ') + '</td><td class="n">' + a.plan.toFixed(1) + '</td><td class="n">' + a.sloped.toFixed(1) + '</td></tr>'); });
          H.push('</tbody></table>');
        }
      }
      if (p.line_changes.length) {
        H.push('<p>Interior lines re-typed by the user (ridge/hip/valley totals above include these): ' +
          p.line_changes.map(function (c) { return 'line ' + c.i + ' ' + esc(c.from) + ' → ' + esc(c.to) + ' (' + (+c.length_ft).toFixed(1) + ' ft)'; }).join('; ') + '.</p>');
      }
      if (p.area_rows.length) {
        H.push('<table><thead><tr><th scope="col">Facet / area</th><th scope="col">Category</th><th scope="col">Pitch</th><th scope="col">Plan sq ft</th><th scope="col">Roof sq ft</th></tr></thead><tbody>');
        p.area_rows.forEach(function (a) { H.push('<tr><th scope="row">' + esc(a.id) + '</th><td>' + esc(a.tag) + '</td><td>' + esc(a.pitch) + '</td><td class="n">' + (+a.plan_area_sqft).toFixed(1) + '</td><td class="n">' + (+a.area_sqft).toFixed(1) + '</td></tr>'); });
        H.push('</tbody></table><p>Area by category: ' + Object.keys(p.area_by_category).map(function (k) { var b = p.area_by_category[k];
          return esc(b.label) + ' ' + b.area.toFixed(1) + ' sq ft (' + (b.area / 100).toFixed(2) + ' squares, ' + b.n + ' facet' + (b.n === 1 ? '' : 's') + ')'; }).join('; ') + '. Untagged facets are not listed.</p>');
      }
      if (p.stale_area_tags.length) H.push('<p class="note">Dropped ' + p.stale_area_tags.length + ' area tag(s) whose facets no longer exist after edits.</p>');
    }
    H.push('<!--RM-DETAIL-->');
    if (p.sources && p.sources.length) {
      H.push('<h3>Measurement data sources (per edge / line)</h3><p class="note">Auto-detected from the roofprint/outline, USGS 3DEP lidar and the facets model. ' +
        'Uncounted candidates are in the Appendix. Pitch: ' + esc(p.pitch_source) + '. Checked by user: ' + p.n_checked + ' of ' + p.sources.length + '.</p>');
      H.push('<table class="compact"><thead><tr><th scope="col">ID</th><th scope="col">Type</th><th scope="col">Length ft</th><th scope="col">Length source</th><th scope="col">Type source</th><th scope="col">Status</th></tr></thead><tbody>');
      p.sources.forEach(function (x) { H.push('<tr><th scope="row">' + esc(x.id) + '</th><td>' + esc(x.type) + '</td><td class="n">' + (+x.length_ft).toFixed(1) + ' <span class="note">' + esc(x.length_basis) +
        '</span></td><td>' + esc(x.length_source) + '</td><td>' + esc(x.type_source) + '</td><td>' + esc(x.status) + '</td></tr>'); });
      H.push('</tbody></table>');
    }
    var ff = p.facet_fit;
    if (ff && ff.facets && ff.facets.length) {
      H.push('<h3>Per-facet lidar plane fits (NOT_PROVEN)</h3><p class="note">' + esc(ff.method) + '. Confidence: high = ≥60 inlier points, RMS ≤ 0.08 m, rise s.e. ≤ 0.3, aspect within 20° of the facet; ' +
        'medium = ≥25 points, RMS ≤ 0.15 m, s.e. ≤ 0.6, aspect within 30°. Only high/medium fits are used. ' +
        (p.per_facet_used ? 'OPT-IN ON: the roof area and rake above use these pitches.' : 'Opt-in is OFF: the totals above use the single pitch in the Summary.') + '</p>');
      H.push('<table class="compact"><thead><tr><th scope="col">Facet</th><th scope="col">Plan sq ft</th><th scope="col">Points (inliers)</th><th scope="col">RMS m</th><th scope="col">Rise raw ± s.e.</th><th scope="col">Snapped</th><th scope="col">Aspect Δ°</th><th scope="col">Confidence</th><th scope="col">Used</th></tr></thead><tbody>');
      ff.facets.forEach(function (x) {
        H.push('<tr><th scope="row">' + esc(x.id) + '</th><td class="n">' + (x.plan_area_sqft != null ? (+x.plan_area_sqft).toFixed(1) : '—') + '</td><td class="n">' + (x.n_points != null ? x.n_points : '—') + (x.n_inliers != null ? ' (' + x.n_inliers + ')' : '') +
          '</td><td class="n">' + (x.rms_m != null ? x.rms_m.toFixed(3) : '—') + '</td><td class="n">' + (x.rise_raw != null ? x.rise_raw.toFixed(2) + ' ± ' + x.se_rise.toFixed(2) : '—') + '</td><td>' + esc(x.pitch_snapped || '—') +
          '</td><td class="n">' + (x.aspect_diff_deg != null ? x.aspect_diff_deg.toFixed(0) : '—') + '</td><td>' + esc(x.confidence || x.status) + '</td><td>' + (x.usable ? esc(x.pitch_used) : 'no (' + esc(x.status) + ')') + '</td></tr>');
      });
      H.push('</tbody></table>');
      if (ff.groups && ff.groups.length) H.push('<p class="note">Coplanar facet groups (one physical plane split by the model): ' + ff.groups.map(function (g) { return esc(g.facets.join('+')) + ' ' + esc(g.pitch_snapped || '?') + ' (' + g.n_points + ' pts)'; }).join('; ') + '.</p>');
    }
    H.push('<!--/RM-DETAIL-->');
    if (p.user_measurements && p.user_measurements.length) {
      H.push('<h3>User-supplied measurements</h3><p class="note">Entered by the user from their own measurement (for example the Google Earth ruler or a tape on site). ' +
        'RoofMeasure did not compute or verify these and does not use them in any total above.</p><table><thead><tr><th scope="col">What</th><th scope="col">Value</th><th scope="col">Source</th><th scope="col">Entered (UTC)</th></tr></thead><tbody>');
      p.user_measurements.forEach(function (m) { H.push('<tr><th scope="row">' + esc(m.label) + '</th><td class="n">' + esc(m.value) + ' ' + esc(m.unit) + '</td><td>' + esc(m.source) + '</td><td>' + esc(m.entered_at || '') + '</td></tr>'); });
      H.push('</tbody></table>');
    }
    H.push('</section>');
    return H.join('');
  }
  function inject(html, section) {
    if (!section) return html;
    // per-edge source table and per-facet fit table go to the appendix (end of report), the rest before Notes
    var d0 = section.indexOf('<!--RM-DETAIL-->'), d1 = section.indexOf('<!--/RM-DETAIL-->');
    if (d0 >= 0 && d1 > d0) {
      var detail = section.slice(d0 + 16, d1); section = section.slice(0, d0) + section.slice(d1 + 17);
      if (detail.replace(/\s/g, '')) {
        detail = '<section aria-labelledby="h-det"><h2 id="h-det">Appendix — measurement sources and per-facet lidar fits</h2>' + detail + '</section>';
        var ft = html.lastIndexOf('<footer');
        html = ft < 0 ? html + detail : html.slice(0, ft) + detail + html.slice(ft);
      }
    }
    var at = html.indexOf('<section aria-labelledby="h-notes">');
    if (at < 0) at = html.lastIndexOf('</body>');
    return at < 0 ? html + section : html.slice(0, at) + section + html.slice(at);
  }
  window.RoofTags = { EDGE_TAGS: EDGE_TAGS, AREA_TAGS: AREA_TAGS, LINE_TYPES: LINE_TYPES, emptyTags: emptyTags, liveFacets: liveFacets, facetsKey: facetsKey,
    facetsInput: facetsInput, applyLineTags: applyLineTags, facetAt: facetAt, matchPlanes: matchPlanes, reportPayload: reportPayload, sectionHtml: sectionHtml,
    inject: inject, pointInRing: pointInRing, esc: esc, EXTRA_TYPES: EXTRA_TYPES, ALL_TYPES: ALL_TYPES, lidarSeg: lidarSeg, reconcileLidar: reconcileLidar, dormers: dormers, decks: decks };
})();
