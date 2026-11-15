/* SPDX-License-Identifier: MIT
 * RoofMeasure 0.1.7.1 — visual categorization (user tags) + per-facet lidar plane pitch cross-check.
 * Pure helpers shared by app.js (live map) and report.js (PDF). Globals: window.RoofTags.
 * Tags are a human's visual categorization; they never change geometry. Only edge eave/rake (core overrides) and interior
 * ridge/hip/valley line types change report numbers; every other tag is listed with its own LF / area.
 */
(function () {
  'use strict';
  var EDGE_TAGS = { step_flashing: 'Step flashing', drip_edge: 'Drip edge', wall_flashing: 'Wall / headwall flashing', no_gutter: 'No gutter' };
  var AREA_TAGS = { steep: 'Steep-slope (shingle)', low_slope: 'Low-slope', flat: 'Flat', deck: 'Deck' };
  var LINE_TYPES = ['ridge', 'hip', 'valley'];
  function emptyTags() { return { edges: {}, lines: {}, linesKey: null, areas: {}, layers: {}, confirmed: {}, lengths: {} }; }
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
      opts: { pitch: r.pitch, roof_type: r.roof_type, ridge_bearing_deg: ridge, overhang_ft: r.overhang_ft || 0 }, ridge: ridge };
  }
  function facetsKey(r, lidar, useRidge) {
    var i = facetsInput(r, lidar, useRidge); return JSON.stringify([i.fp.geometry.coordinates, i.opts]);
  }
  function liveFacets(r, lidar, useRidge) {
    var F = window.RoofFacets; if (!F || typeof F.computeFacets !== 'function' || !r) return null;
    var i = facetsInput(r, lidar, useRidge);
    try { var f = F.computeFacets(i.fp, i.opts); return f && !f.unsupported ? f : null; } catch (e) { return null; }
  }
  /* Apply user interior-line types; recompute ridge/hip/valley LF from the segments. Returns list of changes. */
  function applyLineTags(f, tags, key) {
    var changes = [];
    if (!f || !Array.isArray(f.line_segments) || !tags || tags.linesKey !== key) return changes;
    var segs = f.line_segments;
    Object.keys(tags.lines).forEach(function (k) {
      var s = segs[+k], t = tags.lines[k]; if (!s || !t || LINE_TYPES.indexOf(t.type) < 0) return;
      if (LINE_TYPES.indexOf(s.type) < 0) return; // never re-type rake/wall arcs of the skeleton
      if (s.type !== t.type) changes.push({ i: +k, from: s.type, to: t.type, length_ft: s.length_ft, layer: t.layer });
      s.auto_type = s.type; s.type = t.type; s.user_tagged = true;
    });
    if (changes.length && f.lines) {
      LINE_TYPES.forEach(function (t) { f.lines[t + '_lf'] = 0; });
      var cnt = {}; LINE_TYPES.forEach(function (t) { cnt[t] = 0; });
      segs.forEach(function (s) { if (LINE_TYPES.indexOf(s.type) >= 0) { f.lines[s.type + '_lf'] += s.length_ft; cnt[s.type] += (s.weight == null ? 1 : s.weight); } });
      LINE_TYPES.forEach(function (t) { f.lines[t + '_lf'] = r2(f.lines[t + '_lf']); if (f.line_counts) f.line_counts[t] = cnt[t]; });
    }
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
    var edgeRows = [], tagLf = {};
    Object.keys(EDGE_TAGS).forEach(function (k) { tagLf[k] = { plan: 0, sloped: 0, n: 0, edges: [] }; });
    (r.edges || []).forEach(function (e) {
      var t = tags.edges[e.i]; var keys = t ? Object.keys(t).filter(function (k) { return EDGE_TAGS[k]; }) : [];
      var manual = e.auto === false || e.length_source === 'user edit';
      if (!keys.length && !manual) return;
      var sloped = e.type === 'rake' ? e.length_ft * pf : e.length_ft;
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
      return { kind: 'edge', id: 'E' + e.i, type: e.type, length_ft: r2(e.type === 'rake' ? e.length_ft * pf : e.length_ft), length_basis: e.type === 'rake' ? 'sloped (plan × pitch factor ' + pf + ')' : 'plan',
        length_source: le ? 'user edit (auto ' + (+e.length_ft_auto).toFixed(1) + ' ft plan)' : lenSrc, type_source: retag ? 'user retag (auto ' + e.auto_type + ')' : typeSrc,
        status: retag || le ? 'user-set' : (c ? 'confirmed by user' : 'auto (unconfirmed)') };
    });
    (r.line_segments || []).forEach(function (sg, i) {
      if (LINE_TYPES.indexOf(sg.type) < 0) return;
      var c = conf['L' + i];
      sources.push({ kind: 'line', id: 'L' + i, type: sg.type, length_ft: r2(sg.length_ft), length_basis: 'sloped 3-D (facets model)',
        length_source: 'facets straight-skeleton of roofprint at ' + r.pitch + (r.facets_lidar_inputs ? ' with lidar ridge' : ''),
        type_source: sg.user_tagged ? 'user retag (auto ' + sg.auto_type + ')' : 'facets model', status: sg.user_tagged ? 'user-set' : (c ? 'confirmed by user' : 'auto (unconfirmed)') });
    });
    var nConf = sources.filter(function (x) { return x.status !== 'auto (unconfirmed)'; }).length;
    return { per_facet_used: !!r.per_facet_pitch_used, sources: sources, n_checked: nConf, pitch_source: r.pitch_source, edge_rows: edgeRows, tag_lf: tagLf, line_changes: lineChanges || [], area_rows: areaRows, area_by_category: byCat,
      stale_area_tags: stale, plane_rows: planeRows, layers_used: Object.keys(layersUsed),
      any: edgeRows.length > 0 || (lineChanges || []).length > 0 || areaRows.length > 0 };
  }

  function sectionHtml(p) {
    if (!p) return '';
    var H = ['<section aria-labelledby="h-tags"><h2 id="h-tags">Visual categorization (user tags)</h2>'];
    if (!p.any) H.push('<p class="note">No edges, lines or areas were tagged by the user; eave/rake and ridge/hip/valley are the automatic classification.</p>');
    else {
      H.push('<p class="note">Tags are a person\'s visual categorization made in the app. Geometry and lengths come only from free sources ' +
        '(MassGIS / USGS / footprint or manual trace). Layers on screen while tagging: ' + esc(p.layers_used.join(', ') || 'not recorded') +
        '. Google, Microsoft and Esri layers are visual reference only and none of their imagery is in this report.</p>');
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
    if (p.sources && p.sources.length) {
      H.push('<h3>Measurement data sources (per edge / line)</h3><p class="note">All edges and lines were auto-detected from free data only (roofprint/outline, USGS 3DEP lidar, facets model); ' +
        'no measurement comes from Google, Microsoft or Esri imagery. Pitch: ' + esc(p.pitch_source) + '. Checked by user: ' + p.n_checked + ' of ' + p.sources.length + '.</p>');
      H.push('<table><thead><tr><th scope="col">ID</th><th scope="col">Type</th><th scope="col">Length ft</th><th scope="col">Length source</th><th scope="col">Type source</th><th scope="col">Status</th></tr></thead><tbody>');
      p.sources.forEach(function (x) { H.push('<tr><th scope="row">' + esc(x.id) + '</th><td>' + esc(x.type) + '</td><td class="n">' + (+x.length_ft).toFixed(1) + ' <span class="note">' + esc(x.length_basis) +
        '</span></td><td>' + esc(x.length_source) + '</td><td>' + esc(x.type_source) + '</td><td>' + esc(x.status) + '</td></tr>'); });
      H.push('</tbody></table>');
    }
    if (p.plane_rows.length) {
      H.push('<h3>Per-facet pitch from lidar planes (cross-check, NOT_PROVEN)</h3><p class="note">Each modelled facet is matched to the largest USGS 3DEP ' +
        'lidar RANSAC plane whose downslope direction is within 35° of the facet\'s. ' + (p.per_facet_used ? 'OPT-IN ON: the report roof area above is the per-facet sum below.' : 'The report totals above still use the single pitch shown in the Summary.') + '</p>');
      H.push('<table><thead><tr><th scope="col">Facet</th><th scope="col">Model pitch</th><th scope="col">Lidar plane pitch</th><th scope="col">Aspect Δ°</th><th scope="col">Plane pts</th><th scope="col">Plan sq ft</th><th scope="col">Roof sq ft (lidar pitch)</th></tr></thead><tbody>');
      var tot = 0, ok = true;
      p.plane_rows.forEach(function (x) {
        if (x.lidar_area_sqft == null) ok = false; else tot += x.lidar_area_sqft;
        H.push('<tr><th scope="row">' + esc(x.id) + '</th><td>' + esc(x.model_pitch) + '</td><td>' + (x.lidar_pitch ? esc(x.lidar_pitch) + ' (' + x.lidar_slope_deg.toFixed(1) + '°)' : 'no matching plane') +
          '</td><td class="n">' + (x.aspect_diff_deg != null ? x.aspect_diff_deg.toFixed(0) : '—') + '</td><td class="n">' + (x.plane_points || '—') + '</td><td class="n">' + (+x.plan_area_sqft).toFixed(1) +
          '</td><td class="n">' + (x.lidar_area_sqft != null ? x.lidar_area_sqft.toFixed(1) : '—') + '</td></tr>');
      });
      H.push('</tbody></table><p class="note">' + (ok ? 'Sum at per-facet lidar pitch: ' + tot.toFixed(1) + ' sq ft.' : 'Some facets had no matching plane; no per-facet total is given.') + '</p>');
    }
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
    var at = html.indexOf('<section aria-labelledby="h-notes">');
    if (at < 0) at = html.lastIndexOf('</body>');
    return at < 0 ? html + section : html.slice(0, at) + section + html.slice(at);
  }
  window.RoofTags = { EDGE_TAGS: EDGE_TAGS, AREA_TAGS: AREA_TAGS, LINE_TYPES: LINE_TYPES, emptyTags: emptyTags, liveFacets: liveFacets, facetsKey: facetsKey,
    facetsInput: facetsInput, applyLineTags: applyLineTags, facetAt: facetAt, matchPlanes: matchPlanes, reportPayload: reportPayload, sectionHtml: sectionHtml,
    inject: inject, pointInRing: pointInRing, esc: esc };
})();
