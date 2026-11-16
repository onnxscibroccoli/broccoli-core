/* RoofMeasure in-app PDF report (web/report.js). 0.1.7.1: user tags section, preview/edit, native save/share.
 * Renders the SAME report as /workspace/roofmeasure/report/build_report.py by running that exact Python file
 * (plus report/svg/diagram.py and shared/endpoints.json) inside Pyodide (CPython compiled to WebAssembly, stdlib only).
 * The live in-app result (core roofcalc.js + facets.js + lidar fields) is shaped like report/build_result.js, then
 * build_report.build(..., pdf=False) writes report.html / edges.csv / measurements.csv in Pyodide's in-memory FS.
 * PDF: Android -> window.RoofBridge.printHtml (WebView.createPrintDocumentAdapter + PrintManager, "Save as PDF");
 *      browser -> hidden iframe + window.print() (same Chrome print engine, @page Letter from the report CSS).
 * Aerial: MassGIS 2025 tiles (z19) fetched by JS (CORS ok) and handed to the Python renderer; offline -> labelled placeholder.
 * Globals: window.RoofReport = { buildResult, render, exportPdf, ready }.
 */
(function () {
  'use strict';
  var PYODIDE_URL = window.ROOF_PYODIDE_URL || new URL('vendor/pyodide/', document.baseURI).href /* bundled offline (android/bundle) */;
  var PY_BASE = window.ROOF_PY_BASE || new URL('../', document.baseURI).href; // dev: roofmeasure/ root (report/, shared/)
  var PY_FILES = ['report/build_report.py', 'report/svg/diagram.py', 'report/svg/READY.md', 'shared/endpoints.json'];
  var GLUE = [
    'import sys, json, types, os',
    'sys.path.insert(0, "/rm/report")',
    'import build_report as br',
    'import urllib.request as _ur',
    '_TILES = {}',
    '_RECORD = []',
    '_REC_MODE = [False]',
    'class _Resp:',
    '    def __init__(s, d): s.d = d',
    '    def read(s): return s.d',
    '    def __enter__(s): return s',
    '    def __exit__(s, *a): return False',
    'def _urlopen(req, timeout=None):',
    '    url = getattr(req, "full_url", None) or str(req)',
    '    _RECORD.append(url)',
    '    if url in _TILES and not _REC_MODE[0]:',
    '        d = _TILES[url]',
    '        if d is None: raise OSError("tile unavailable (offline?)")',
    '        return _Resp(d)',
    '    return _Resp(b"\\xff\\xd8" + b"0" * 600)',
    '_ur.urlopen = _urlopen',
    'class _Now:',
    '    def __init__(s, g): s.g = g',
    '    def astimezone(s): return s',
    '    def strftime(s, f): return s.g',
    'def tiles_needed(rjson):',
    '    del _RECORD[:]',
    '    _REC_MODE[0] = True',
    '    try: br.aerial_views(json.loads(rjson))',
    '    finally: _REC_MODE[0] = False',
    '    return json.dumps(list(dict.fromkeys(_RECORD)))',
    'def set_tile(url, data):',
    '    _TILES[url] = None if data is None else bytes(data)',
    'def render(rjson, generated):',
    '    br.datetime = types.SimpleNamespace(datetime=types.SimpleNamespace(now=lambda *a: _Now(generated)))',
    '    os.makedirs("/tmp/rm_in", exist_ok=True)',
    '    open("/tmp/rm_in/result.json", "w").write(rjson)',
    '    s = br.build("/tmp/rm_in/result.json", "/tmp/rm_out", pdf=False, flat=False)',
    '    rd = lambda n: open("/tmp/rm_out/" + n, encoding="utf-8").read()',
    '    s.pop("outputs", None)',
    '    return json.dumps({"html": rd("report.html"), "edges_csv": rd("edges.csv"), "measurements_csv": rd("measurements.csv"), "summary": s})'
  ].join('\n');

  var pyP = null;
  function loadScript(src) {
    return new Promise(function (res, rej) {
      var s = document.createElement('script'); s.src = src; s.onload = res;
      s.onerror = function () { rej(new Error('could not load ' + src)); }; document.head.appendChild(s);
    });
  }
  function withTimeout(p, ms, what) {
    return Promise.race([p, new Promise(function (_, rej) { setTimeout(function () { rej(new Error(what + ' timed out after ' + Math.round(ms / 1000) + ' s')); }, ms); })]);
  }
  function engine() {
    if (pyP) return pyP;
    pyP = (window.loadPyodide ? Promise.resolve() : loadScript(PYODIDE_URL + 'pyodide.js')).then(function () {
      return window.loadPyodide({ indexURL: PYODIDE_URL });
    }).then(function (py) {
      return Promise.all(PY_FILES.map(function (f) {
        return fetch(PY_BASE + f).then(function (r) { if (!r.ok) throw new Error('report engine file ' + f + ': HTTP ' + r.status); return r.text(); })
          .then(function (t) { var p = '/rm/' + f; py.FS.mkdirTree(p.slice(0, p.lastIndexOf('/'))); py.FS.writeFile(p, t); });
      })).then(function () { py.runPython(GLUE); return py; });
    });
    pyP = withTimeout(pyP, 120000, 'loading the offline report engine (Pyodide)');
    pyP.catch(function () { pyP = null; });
    return pyP;
  }

  function centroid(ring) {
    var x = 0, y = 0, n = ring.length; ring.forEach(function (p) { x += p[0]; y += p[1]; }); return [x / n, y / n];
  }
  function slugify(s) { return (String(s).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 60)) || 'report'; }

  function rOf(p) { var m = /^\s*([\d.]+)\s*\/\s*12/.exec(String(p)); return m ? +m[1] : null; }
  function pfOf(p) { var x = rOf(p); return x == null ? null : Math.sqrt(1 + (x / 12) * (x / 12)); }
  function pipLL(p, P) { var c = false; for (var i = 0, j = P.length - 1; i < P.length; j = i++) { if (((P[i][1] > p[1]) !== (P[j][1] > p[1])) && (p[0] < (P[j][0] - P[i][0]) * (p[1] - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0])) c = !c; } return c; }
  function dSegLL(p, a, b, kx) { var ax = (a[0] - p[0]) * kx, ay = a[1] - p[1], bx = (b[0] - p[0]) * kx, by = b[1] - p[1], dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy,
    t = l2 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / l2)) : 0; return Math.hypot(ax + t * dx, ay + t * dy); }
  /** facet whose polygon contains (or is nearest to) lon/lat point p */
  function facetNear(facets, p) {
    var kx = Math.cos(p[1] * Math.PI / 180), best = null, bd = Infinity;
    facets.forEach(function (fx) { var P = fx.polygon_lonlat; if (!P) return; var d = pipLL(p, P) ? 0 : Infinity;
      if (d) for (var i = 0; i + 1 < P.length; i++) d = Math.min(d, dSegLL(p, P[i], P[i + 1], kx));
      if (d < bd) { bd = d; best = fx; } });
    return best;
  }
  /** Opt-in per-facet pitch: facet areas from usable lidar fits; rakes sloped with the pitch of the facet each part of the rake bounds. */
  function applyPerFacet(r, edits, useLidar) {
    edits = edits || {}; if (useLidar == null) useLidar = true;
    var nEd = Object.keys(edits).filter(function (k) { return (r.facets || []).some(function (fx) { return fx.id === k; }); }).length;
    var fit = r.facet_fit || (nEd ? { facets: [] } : null);
    if (!nEd && !useLidar) return;
    if (!fit || ((!fit.facets || !fit.facets.length) && !nEd)) { r.notes.push('Per-facet lidar pitch was requested but no per-facet lidar fits are available (run Auto pitch); single pitch ' + r.pitch + ' used for all totals.'); return; }
    var byId = {}; fit.facets.forEach(function (x) { byId[x.id] = x; });
    var tot = 0, totU = 0, nUsed = 0;
    r.facets.forEach(function (fx) {
      var x = byId[fx.id]; fx.model_pitch = fx.pitch; fx.model_area_sqft = fx.area_sqft;
      if (edits[fx.id] && pfOf(edits[fx.id])) { x = { usable: true, pitch_used: edits[fx.id], confidence: 'user edit' }; fx.user_pitch = true; }
      else if (!useLidar) x = null;
      if (x && x.usable && x.pitch_used) { var pf = pfOf(x.pitch_used); fx.pitch = x.pitch_used; fx.pitch_source = x.confidence === 'user edit' ? 'user edit (3-D editor)' : 'lidar facet fit (' + x.confidence + ')'; fx.area_sqft = Math.round(fx.plan_area_sqft * pf * 10) / 10; nUsed++; }
      else { fx.pitch_source = 'single pitch (no usable lidar fit: ' + (x ? x.status + (x.confidence ? ', ' + x.confidence : '') : 'none') + ')'; }
      tot += +fx.area_sqft;
      totU += x && x.usable && x.pitch_used ? fx.plan_area_sqft * pfOf(x.pitch_used) : (+fx.model_area_sqft || 0);
    });
    if (!nUsed) { r.facets.forEach(function (fx) { fx.pitch = fx.model_pitch; fx.area_sqft = fx.model_area_sqft; }); r.notes.push('Per-facet lidar pitch was requested but no facet had a usable lidar fit; single pitch ' + r.pitch + ' used for all totals.'); return; }
    r.roof_area_sqft_single_pitch = r.roof_area_sqft; r.roof_area_sqft = Math.round(tot * 10) / 10;
    r.squares = Math.round(totU) / 100; r.squares_with_waste = Math.round(totU * (1 + r.waste_pct / 100)) / 100; // unrounded facet areas, same rounding as core
    // rakes: sample each rake edge, take the pitch of the facet it bounds
    var oh = +r.overhang_ft || 0, rakeSum = 0, rakePlan = 0;
    r.edges.forEach(function (e) {
      if (e.type !== 'rake' || !e.from || !e.to) return;
      var N = 20, sl = 0, plan = e.length_ft + 2 * oh, used = {};
      for (var k = 0; k < N; k++) { var t = (k + 0.5) / N, p = [e.from[0] + (e.to[0] - e.from[0]) * t, e.from[1] + (e.to[1] - e.from[1]) * t];
        var fx = facetNear(r.facets, p), pf = (fx && pfOf(fx.pitch)) || r.pitch_factor; used[fx ? fx.id + ' ' + fx.pitch : r.pitch] = 1; sl += plan / N * pf; }
      e.sloped_length_ft_single_pitch = e.sloped_length_ft; e.sloped_length_ft = Math.round(sl * 100) / 100; e.sloped_basis = 'per-facet pitch: ' + Object.keys(used).join(', ');
      rakeSum += e.sloped_length_ft; rakePlan += plan;
    });
    if (rakePlan) { r.rake_sloped_lf_single_pitch = r.rake_sloped_lf; r.rake_sloped_lf = r.rake_lf = Math.round(rakeSum * 10) / 10;
      // facets-model rake (drip edge) scaled by the same per-facet/single-pitch ratio so drip edge stays consistent
      if (r.lines && r.lines.rake_lf && r.rake_sloped_lf_single_pitch) { r.lines.rake_lf_single_pitch = r.lines.rake_lf; r.lines.rake_lf = Math.round(r.lines.rake_lf * r.rake_sloped_lf / r.rake_sloped_lf_single_pitch * 100) / 100; } }
    r.per_facet_pitch_used = true; r.per_facet_n_used = nUsed; r.facet_pitch_user_edits = nEd;
    if (nEd) r.notes.push('User edit (3-D editor): pitch set by hand on ' + nEd + ' facet(s): ' + Object.keys(edits).map(function (k) { return k + ' ' + edits[k]; }).join(', ') + '; areas and adjacent rakes use these pitches.');
    if (useLidar) r.notes.push('OPT-IN per-facet lidar pitch: roof area ' + r.roof_area_sqft + ' sq ft = sum over facets of plan area × pitch factor, using the snapped lidar plane-fit pitch for ' + nUsed + ' of ' +
      r.facets.length + ' facets (single pitch ' + r.pitch + ' for the rest); single-pitch area was ' + r.roof_area_sqft_single_pitch + ' sq ft. Rake (sloped) ' + r.rake_sloped_lf +
      ' LF uses the pitch of the facet each rake bounds (single-pitch rake ' + (r.rake_sloped_lf_single_pitch != null ? r.rake_sloped_lf_single_pitch : r.rake_sloped_lf) + ' LF). Eaves are level and unchanged. Ridge/hip/valley stay at ' + r.pitch + '. NOT_PROVEN against field measurements.');
  }

  /* Shape the live app result like report/build_result.js does for the reference report. */
  function buildResult(app) {
    var st = app.state, RC = window.RoofCalc;
    if (!st.result) throw new Error('Measure a roof first.');
    var r = JSON.parse(JSON.stringify(st.result));
    var ring = RC.extractRing(r.footprint_geojson);
    if (r.lat == null || r.lon == null) { var c = centroid(ring.slice(0, -1)); r.lon = +c[0].toFixed(7); r.lat = +c[1].toFixed(7); }
    if (!r.address) r.address = st.address || ('Roof at ' + (+r.lat).toFixed(6) + ', ' + (+r.lon).toFixed(6));
    if (!r.source) r.source = 'manual outline';
    r.notes = Array.isArray(r.notes) ? r.notes.slice() : [];
    var L = st.lidar, lidarUsed = L && /^lidar/.test(String(r.pitch_source || ''));
    if (lidarUsed) {
      r.lidar = { pitch_deg: L.pitch_deg, pitch_rise: L.pitch_rise, ridge_source: L.ridge_source, roof_shape_guess: L.roof_shape_guess,
        samples_n: L.samples_n, data_url: L.data_url, lidar_pitch_factor: L.pitch_factor };
      if (r.ridge_bearing_deg == null && L.ridge_bearing_deg != null) r.ridge_bearing_deg = L.ridge_bearing_deg;
      r.notes.push('Pitch ' + L.pitch + ' from USGS 3DEP lidar (' + L.pitch_source + ', confidence ' + L.pitch_confidence + ', ' + L.samples_n +
        ' building points); ridge bearing ' + L.ridge_bearing_deg + '° (' + L.ridge_source + '); lidar roof shape guess: ' + L.roof_shape_guess + '.');
    } else if (r.pitch_source === 'manual') {
      r.notes.push('Pitch ' + r.pitch + ' entered by hand in the app (not measured).');
    }
    // 0.1.7.2 structured edits: user edge lengths (report-side; footprint area and downspouts are not re-derived)
    var LE = (st.tags && st.tags.lengths) || {}, nLE = 0;
    Object.keys(LE).forEach(function (k) {
      var e = r.edges[+k], v = +LE[k]; if (!e || !isFinite(v) || v <= 0) return;
      var d = v - e.length_ft; if (Math.abs(d) < 0.005) return;
      e.length_ft_auto = e.length_ft; e.length_ft = Math.round(v * 100) / 100; e.plan_length_ft = e.length_ft; e.length_source = 'user edit'; nLE++;
      e.sloped_length_ft = Math.round((e.type === 'rake' ? (e.length_ft + 2 * (+r.overhang_ft || 0)) * r.pitch_factor : e.length_ft) * 100) / 100;
      if (e.type === 'eave') { r.eave_lf = Math.round((r.eave_lf + d) * 10) / 10; r.gutter_lf = Math.round((r.gutter_lf + d) * 10) / 10; }
      if (e.type === 'rake') { r.rake_plan_lf = Math.round((r.rake_plan_lf + d) * 10) / 10; r.rake_sloped_lf = r.rake_lf = Math.round(r.rake_plan_lf * r.pitch_factor * 10) / 10; }
      r.notes.push('Edge ' + e.i + ' length edited by the user: ' + e.length_ft.toFixed(1) + ' ft (auto ' + e.length_ft_auto.toFixed(1) + ' ft); ' + e.type + ' totals adjusted by ' + (d >= 0 ? '+' : '') + d.toFixed(1) + ' ft.');
    });
    if (nLE) r.notes.push(nLE + ' edge length(s) edited by the user: eave/gutter/rake totals include the edits; footprint area, roof area and downspout count are still from the outline.');
    var p = st.feature && st.feature.properties;
    if (p && p.STRUCT_ID) {
      r.source_detail = { struct_id: String(p.STRUCT_ID), sourcetype: p.SOURCETYPE || null, sourcedata: null,
        massgis_area_sqft_attr: p.AREA_SQ_FT != null ? +p.AREA_SQ_FT : null, calc: 'core/roofcalc.js computeRoof v' + (RC.VERSION || r.calc_version) };
    }
    if (st.geocoder) r.geocoder = st.geocoder;
    if (st.fetchedAt) r.fetched_at = st.fetchedAt;
    var F = window.RoofFacets, T = window.RoofTags, tags = st.tags || (T && T.emptyTags()), lineChanges = [];
    if (F && typeof F.computeFacets === 'function') {
      try {
        var useR = (document.getElementById('useRidge') || {}).checked !== false;
        var fin = T ? T.facetsInput(r, L, useR) : null, ridge = fin ? fin.ridge : undefined;
        var f = F.computeFacets(fin.fp, fin.opts);
        if (f && f.lines && !f.unsupported) {
          f.roof_model_info = r.roof_model_info || null;
          var segSum = (T && T.reconcileLidar && L && r.use_lidar_lines !== false) ? T.reconcileLidar(f, L, RC.extractRing(r.footprint_geojson)) : null;
          if (T) lineChanges = T.applyLineTags(f, tags, T.facetsKey(r, L, useR));
          if (segSum) {
            var SG = T.lidarSeg(L);
            r.lidar_seg = { version: SG.version, summary: segSum, coverage: SG.coverage, n_points: SG.n_points, notes: SG.notes, planes: SG.planes, steps: SG.steps, lines: SG.lines };
            var lidSegs = f.line_segments.filter(function (x) { return x.source === 'lidar'; });
            r.notes.push('Whole-roof lidar segmentation (' + SG.version + '): ' + SG.planes.length + ' planes (' + segSum.n_small + ' small, flagged), ' + lidSegs.length + ' extra line(s) not in the footprint model (' +
              lidSegs.filter(function (x) { return !x.unverified && !x.deleted; }).length + ' counted, the rest UNVERIFIED candidates), ' + segSum.model_lines_confirmed + ' model line(s) confirmed and ' + segSum.model_lines_retyped +
              ' re-typed by lidar.');
          }
          if (T.dormers && L) r.dormers = T.dormers(T.lidarSeg(L), tags);
          if (T.decks && L) r.decks = T.decks(T.lidarSeg(L));
          else if (tags && tags.dormersAdded && tags.dormersAdded.length && T.dormers) r.dormers = T.dormers(null, tags);
          var skyU = (tags && Array.isArray(tags.skylights)) ? tags.skylights : [], skyL = (L && T && T.lidarSeg(L) && T.lidarSeg(L).skylights) || [], skyDel = (tags && tags.skylightsDeleted) || {};
          r.skylights = skyL.map(function (k, i) { return Object.assign({ key: 'S' + i }, k); }).filter(function (k) { return !skyDel[k.key]; })
            .concat(skyU.map(function (k, i) { return { key: 'U' + i, centroid_lonlat: k.centroid_lonlat || null, approx_w_ft: +k.w_ft || null, approx_h_ft: +k.h_ft || null, approx_area_sqft: (+k.w_ft && +k.h_ft) ? Math.round(k.w_ft * k.h_ft) : null,
              evidence: ['user'], confidence: 'user-entered', status: 'user-entered', source: 'user', note: k.note || '' }; }));
          // 0.1.7.6: register the roofprint to the lidar building mask; lidar-derived 2-D features (decks, dormers, lidar skylights)
          // are moved into the roofprint frame so they land on the roof in the diagram and overlay. Lines / totals are untouched.
          var LO = L ? lidarOutline(L) : null;
          if (LO) { r.lidar_outline = LO; if (LO.applied) shiftFeatures(r, -LO.dx_m, -LO.dy_m); }
          if (f.line_candidates) r.line_candidates = f.line_candidates;
          if (f.added_lines && f.added_lines.length) r.added_lines = f.added_lines;
          r.lines = f.lines;
          r.facets = (f.facets || []).map(function (x) { return { id: x.id, area_sqft: x.area_sqft, plan_area_sqft: x.plan_area_sqft, pitch: x.pitch,
            edge_type: x.edge_type, edge_index: x.edge_index, downslope_bearing_deg: x.downslope_bearing_deg, polygon_lonlat: x.polygon_lonlat }; });
          if (Array.isArray(f.line_segments)) r.line_segments = f.line_segments;
          r.facets_ridge_bearing_source = f.ridge_bearing_source || null;
          r.facets_lidar_inputs = ridge != null && !!lidarUsed;
          if (f.line_counts) r.line_counts = f.line_counts;
          r.facets_source = 'facets computeFacets ' + (f.version || '') + ' (in-app lib/facets.js; method ' + String(f.method || '?').split(':')[0] + ', roof_type ' + f.roof_type + ')';
          var mi = r.roof_model_info;
          r.notes.push('Roof model: ' + (mi ? mi.label + ' (' + (mi.source === 'assumed' ? 'ASSUMED' : mi.source) + '; ' + mi.reason + ')' : 'not set') +
            '. Ridge/hip/valley lengths from the facets lane (' + (r.roof_model === 'simple' ? 'one ridge through the roofprint, no hips or valleys' : 'straight-skeleton model of the 2-D roofprint') + ', equal pitch)' +
            (lineChanges.length ? ', with ' + lineChanges.length + ' interior line(s) re-typed or deleted by the user' : '') + '.');
          if (f.line_candidates && f.line_candidates.n) r.notes.push('UNVERIFIED candidates NOT counted: ' + f.line_candidates.n + ' line(s) (' + Object.keys(f.line_candidates).filter(function (k) { return k !== 'n' && f.line_candidates[k]; }).map(function (k) { return k.replace('_lf', '') + ' ' + f.line_candidates[k] + ' ft'; }).join(', ') +
            ') from the assumed model or low-confidence lidar. Confirm them in the app (Confirm tool / report editor) or pick the roof model to count them.');
          if (f.added_lines && f.added_lines.length) r.notes.push(f.added_lines.length + ' interior line(s) entered by the user (' + f.added_lines.map(function (a) { return a.type + ' ' + a.length_ft + ' ft'; }).join(', ') + '); counted in the totals.');
        } else {
          r.notes.push('Facets lane returned no lines' + (f && f.unsupported ? ' (unsupported roof style)' : '') + '; ridge/hip/valley not measured.');
        }
      } catch (e) { r.notes.push('Facets lane error: ' + e.message + '; ridge/hip/valley not measured.'); }
    } else {
      r.notes.push('Facets module not loaded in the app; ridge/hip/valley not measured.');
    }
    // 0.1.7.3: per-facet lidar plane fits (lidar/facetfit.js) for every facet; used in totals only when the opt-in is on.
    var FF = window.RoofFacetFit;
    if (FF && r.facets && r.facets.length && L && L.points_local) {
      try { r.facet_fit = FF.fitFacets(L, r.facets); } catch (e) { r.notes.push('Per-facet lidar fit error: ' + e.message); }
    }
    var fpEd = (st.tags && st.tags.facetPitch) || {};
    if (st.perFacetPitch || Object.keys(fpEd).length) applyPerFacet(r, fpEd, !!st.perFacetPitch);
    if (T) {
      try {
        r.user_tags = T.reportPayload(r, tags, lidarUsed ? L : (L && L.planes ? L : null), lineChanges);
        if (r.user_tags.any) r.notes.push('User visual categorization: ' + r.user_tags.edge_rows.length + ' edge(s), ' + r.user_tags.line_changes.length +
          ' interior line(s), ' + r.user_tags.area_rows.length + ' area(s) tagged (see "Visual categorization").');
      } catch (e) { r.notes.push('Tag summary error: ' + e.message + ' (tags omitted).'); }
    }
    if (Array.isArray(st.manualMeas) && st.manualMeas.length) {
      r.user_measurements = st.manualMeas.map(function (m) { return { label: m.label, value: m.value, unit: m.unit, source: m.source, entered_at: m.entered_at }; });
      if (r.user_tags) r.user_tags.user_measurements = r.user_measurements;
      r.notes.push(r.user_measurements.length + ' user-supplied measurement(s) recorded (see "User-supplied measurements"); not computed by RoofMeasure and not used in its totals.');
    }
    if (st.geocodeWarning) r.notes.push(st.geocodeWarning);
    try { roofFeatures(r); } catch (e) { /* features are optional */ }
    if (st.edits3d && st.edits3d.n) { r.edits_3d = { n: st.edits3d.n, summary: st.edits3d.summary }; r.notes.push('User edits in the 3-D roof editor (' + st.edits3d.n + '): ' + st.edits3d.summary + '.'); }
    var refs = Object.keys(st.refLayersViewed || {});
    if (refs.length) r.reference_layers_viewed = refs;
    var un = (document.getElementById('userNotes') || {}).value;
    if (un && String(un).trim()) String(un).trim().split(/\n+/).forEach(function (line) { r.notes.push('User note: ' + line.trim()); });
    r.palette = (document.getElementById('palette') || {}).value === 'cb' ? 'cb' : 'std';
    r.core_version = RC.VERSION || r.calc_version;
    r.slug = slugify(r.address);
    // strip app-only edge geometry the report does not need (keeps the JSON small)
    return r;
  }

  /* 0.1.7.3 aerial robustness (bug B): tiles are cached per session (a later report, e.g. with per-facet pitch on, reuses the
   * bytes of an earlier one instead of re-downloading), each tile gets 3 tries (12/20/25 s), and every failure is recorded. */
  var TILE_CACHE = {}, TILE_LOG = [];
  function fetchOnce(url, ms) {
    var ctl = window.AbortController ? new AbortController() : null;
    var t = setTimeout(function () { if (ctl) ctl.abort(); }, ms);
    return fetch(url, ctl ? { signal: ctl.signal } : {}).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status); return r.arrayBuffer();
    }).then(function (b) { clearTimeout(t); var u = new Uint8Array(b); if (u.length < 500) throw new Error('tile too small (' + u.length + ' B)'); return u; },
      function (e) { clearTimeout(t); throw e; });
  }
  function fetchTile(url) {
    if (TILE_CACHE[url]) return Promise.resolve(TILE_CACHE[url]);
    var waits = [12000, 20000, 25000], i = 0;
    function attempt() {
      return fetchOnce(url, waits[i]).then(function (d) { TILE_CACHE[url] = d; return d; }, function (e) {
        TILE_LOG.push({ url: url.replace(/^.*\/tile\//, 'tile/'), attempt: i + 1, error: String(e && (e.name === 'AbortError' ? 'timeout ' + waits[i] / 1000 + ' s' : e.message || e)) });
        if (++i < waits.length) return attempt(); return null; });
    }
    return attempt();
  }
  function prefetchTiles(result) {
    return engine().then(function (py) { var need = JSON.parse(py.globals.get('tiles_needed')(JSON.stringify(result))); return Promise.all(need.map(fetchTile)); }).catch(function () { return null; });
  }

  function generatedStamp() {
    var d = new Date(), z = function (n) { return (n < 10 ? '0' : '') + n; };
    var tz = '';
    try { tz = new Intl.DateTimeFormat('en-US', { timeZoneName: 'short' }).formatToParts(d).filter(function (x) { return x.type === 'timeZoneName'; })[0].value; } catch (e) { tz = ''; }
    return d.getFullYear() + '-' + z(d.getMonth() + 1) + '-' + z(d.getDate()) + ' ' + z(d.getHours()) + ':' + z(d.getMinutes()) + (tz ? ' ' + tz : '');
  }

  /* 0.1.7.4: ortho lean/offset estimate + ortho patch candidates (free MassGIS ortho pixels only), from the
     tiles already fetched for the aerial pages. Sets result.ortho_align and result.ortho_patches. */
  /* 0.1.7.5: labelled roof features for the diagram / overlay / summary: skylights (ortho patches sized 1.3-6 ft a side,
   * plus lidar candidates and user skylights) and roof decks / flat sections (lidar flat planes). All candidates (NOT_PROVEN). */
  /* 0.1.7.6: lidar probe at a roofprint-frame lon/lat: dominant plane of the points in a 0.4-1.8 m ring around it, and the
   * height of the points on the patch relative to a local fit of that plane. -> fn(ll, halfSizeM) -> null | {ok, why, note} */
  function lidarProbe(r) {
    var A = window.RoofApp, L = A && A.state && A.state.lidar, T = window.RoofTags;
    if (!L || !L.points_full || !L.frame || !T || !T.lidarSeg) return null;
    var sg = T.lidarSeg(L), pid = sg && sg.point_plane; if (!pid) return null;
    var fr = L.frame, R = 6378137, D = Math.PI / 180, P = L.points_full, lo = r.lidar_outline && r.lidar_outline.applied ? r.lidar_outline : { dx_m: 0, dy_m: 0 };
    function loc(ll) { var mx = ll[0] * D * R, my = Math.log(Math.tan(Math.PI / 4 + ll[1] * D / 2)) * R; return [(mx - fr.ox) * fr.k + lo.dx_m, (my - fr.oy) * fr.k + lo.dy_m]; }
    return function (ll, hs) {
      var c = loc(ll), r0 = hs + 0.25, r1 = hs + 1.1, ring = [], on = [], cnt = {};
      for (var i = 0; i < P.length; i++) { var d = Math.hypot(P[i][0] - c[0], P[i][1] - c[1]);
        if (d <= hs) on.push(P[i]); else if (d >= r0 && d <= r1) { ring.push(i); if (pid[i] >= 0) cnt[pid[i]] = (cnt[pid[i]] || 0) + 1; } }
      if (ring.length < 8) return null;
      var top = Object.keys(cnt).sort(function (a, b) { return cnt[b] - cnt[a]; })[0], frac = top == null ? 0 : cnt[top] / ring.length;
      if (frac < 0.65) return { ok: false, why: 'straddles lidar planes (' + Math.round(frac * 100) + ' % on one plane: ridge / hip / valley / dormer edge)' };
      var Q = ring.filter(function (i) { return String(pid[i]) === top; }).map(function (i) { return P[i]; });
      // local LSQ plane z = a x + b y + c
      var n = Q.length, sx = 0, sy = 0, sz = 0, sxx = 0, syy = 0, sxy = 0, sxz = 0, syz = 0;
      Q.forEach(function (p) { var x = p[0] - c[0], y = p[1] - c[1]; sx += x; sy += y; sz += p[2]; sxx += x * x; syy += y * y; sxy += x * y; sxz += x * p[2]; syz += y * p[2]; });
      var M = [[sxx, sxy, sx], [sxy, syy, sy], [sx, sy, n]], v = [sxz, syz, sz];
      function det(m) { return m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]); }
      var dt = det(M); if (Math.abs(dt) < 1e-9) return null;
      function rep(k) { return M.map(function (row, i) { return row.map(function (x, j) { return j === k ? v[i] : x; }); }); }
      var a = det(rep(0)) / dt, b = det(rep(1)) / dt, c0 = det(rep(2)) / dt;
      // 0.1.7.6 lidar skylight evidence: missing returns (density on the patch vs the ring) and an intensity anomaly (glass is
      // specular: low or erratic returns). Raw EPT intensity (no range / incidence normalisation), so only relative to the ring.
      var aOn = Math.PI * hs * hs, aRing = Math.PI * (r1 * r1 - r0 * r0), dens = aOn > 0 && ring.length ? (on.length / aOn) / (ring.length / aRing) : null;
      var iR = Q.map(function (p) { return p[4] || 0; }).sort(function (x, y) { return x - y; }), iO = on.map(function (p) { return p[4] || 0; }).sort(function (x, y) { return x - y; });
      var iRat = iR.length && iO.length && iR[iR.length >> 1] > 0 ? iO[iO.length >> 1] / iR[iR.length >> 1] : null;
      var ev = []; if (dens != null && dens < 0.5) ev.push('few returns (' + Math.round(dens * 100) + ' % of the plane density)'); if (iRat != null && (iRat < 0.7 || iRat > 1.5)) ev.push('intensity ' + Math.round(iRat * 100) + ' % of the plane');
      var tail = ev.length ? '; lidar glass evidence: ' + ev.join(', ') : '';
      if (!on.length) return { ok: true, glass: true, note: 'no returns on the patch (glass?), on plane P' + (+top + 1) };
      var dz = on.map(function (p) { return p[2] - (a * (p[0] - c[0]) + b * (p[1] - c[1]) + c0); }).sort(function (x, y) { return x - y; }), med = dz[dz.length >> 1];
      if (med > 0.45) return { ok: false, why: 'raised ' + med.toFixed(2) + ' m above its lidar plane (dormer / chimney / vent box)' };
      if (med < -0.25) return { ok: false, why: 'sunk ' + (-med).toFixed(2) + ' m below its lidar plane (opening / lower roof)' };
      return { ok: true, glass: ev.length > 0, note: 'on plane P' + (+top + 1) + ', ' + on.length + ' returns ' + (med >= 0 ? '+' : '') + med.toFixed(2) + ' m (flush / curb)' + tail };
    };
  }
  function roofFeatures(r) {
    var tg = (window.RoofApp && window.RoofApp.state && window.RoofApp.state.tags) || {}, rm = tg.featuresRemoved || {};
    var sk = [], n = 0, c0 = (r.ortho_patches || [])[0], kx = Math.cos(((c0 && c0.centroid_lonlat[1]) || r.lat || 42) * Math.PI / 180) * 111320, ky = 110540;
    function dm(a, b) { return Math.hypot((a[0] - b[0]) * kx, (a[1] - b[1]) * ky); }
    var dorm = (r.dormers || []).filter(function (d) { return !d.deleted; }) /* 0.1.7.6: candidates too (was kept-only, so lidar dormers never excluded their window patches) */.map(function (d) { return d.centroid_lonlat || (d.coords_lonlat ? [(d.coords_lonlat[0][0] + d.coords_lonlat[1][0]) / 2, (d.coords_lonlat[0][1] + d.coords_lonlat[1][1]) / 2] : null); }).filter(Boolean);
    // 0.1.7.6: stricter skylight test. An ortho patch is counted as a skylight candidate only if
    //  - size: both sides 1.5-12 ft; contrast >= 4 x its facet's MAD; rectangularity >= 0.6;
    //  - lidar plane continuity: the points around it (a ring 0.25-1.1 m outside it) lie on ONE lidar plane (>= 65 %) and the points on it sit
    //    within -0.25 / +0.45 m of that plane (flush glass or a low curb; dormers, chimneys, vents and plane edges fail);
    //  - not on a roof deck, not within 2.5 m of a dormer, not in a cluster of 3+ patches.
    // Patches without enough lidar points around them are kept as "lidar not checked" candidates but not counted.
    var rej = [], LP = lidarProbe(r), AX = (function () { // building axis (longest roofprint edge), degrees CCW from east
      var R0 = r.footprint_geojson && window.RoofCalc.extractRing(r.footprint_geojson); if (!R0) return null; var best = 0, th = null, kx2 = Math.cos(R0[0][1] * Math.PI / 180);
      for (var i = 0; i + 1 < R0.length; i++) { var dx = (R0[i + 1][0] - R0[i][0]) * kx2, dy = R0[i + 1][1] - R0[i][1], L = Math.hypot(dx, dy); if (L > best) { best = L; th = Math.atan2(dy, dx) * 180 / Math.PI; } }
      return th; })();
    // patch angle_deg is in image axes (x east, y south, clockwise): CCW-from-east = -angle; compare modulo 90
    function axOff(a) { if (AX == null || a == null) return null; var d = ((-a - AX) % 90 + 180) % 90; return Math.min(d, 90 - d); }
    (r.ortho_patches || []).forEach(function (p) {
      var why = null, w = p.approx_w_ft, h = p.approx_h_ft;
      var am2 = w * h / 10.764, asp = Math.max(w, h) / Math.max(0.01, Math.min(w, h)), dax = axOff(p.angle_deg);
      if (w < 1.5 || h < 1.5) why = 'smaller than 1.5 ft (vent / pipe / trim)';
      else if (w > 12 || h > 12) why = 'larger than 12 ft (not a skylight)';
      // 0.1.7.6 gates from the pipeline spec (docs/research/lidar_pipeline_spec.md): 0.30-3.5 m2, width >= 0.35 m, aspect <= 3.5,
      // rectangularity >= 0.78, long side within 10 deg of the eave / ridge bearing
      else if (am2 < 0.30 || am2 > 3.5) why = 'area ' + am2.toFixed(2) + ' m2 outside 0.30-3.5 m2';
      else if (asp > 3.5) why = 'aspect 1:' + asp.toFixed(1) + ' (over 1:3.5)';
      else if ((p.contrast || 0) < 4) why = 'weak ortho contrast (' + p.contrast + ')';
      // the spec's 0.78 assumes segmentation masks; on 15 cm threshold blobs the rims round off (15 Ward's three skylights measure
      // 0.62-0.69), so the gate is 0.6 and >= 0.78 is reported as "strict rectangle" evidence
      else if ((p.rectangularity || 0) < 0.6) why = 'not rectangular (' + p.rectangularity + ' < 0.6)';
      else if (dax != null && dax > 10) why = Math.round(dax) + ' deg off the eave / ridge bearing (over 10)';
      else if ((r.decks || []).some(function (d) { return d.outline_lonlat && (pipLL(p.centroid_lonlat, d.outline_lonlat.concat([d.outline_lonlat[0]])) || d.outline_lonlat.some(function (q) { return dm(q, p.centroid_lonlat) < 1.0; })); })) why = 'on a roof deck (railing / boards)';
      else if (dorm.some(function (q) { return dm(q, p.centroid_lonlat) < 2.5; })) why = 'at a dormer (dormer window / trim)';
      else if ((r.ortho_patches || []).filter(function (o) { return o !== p && dm(o.centroid_lonlat, p.centroid_lonlat) < 2.0; }).length >= 2) why = 'cluster of 3+ patches (dormer window, trim or railing)';
      var lc = !why && LP ? LP(p.centroid_lonlat, Math.max(w, h) / 3.2808 / 2) : null;
      if (!why && lc && lc.ok === false) why = lc.why;
      if (why) { p.excluded = why; rej.push({ key: p.key, w_ft: w, h_ft: h, reason: why, centroid_lonlat: p.centroid_lonlat }); return; }
      sk.push({ key: p.key, centroid_lonlat: p.centroid_lonlat, w_ft: w, h_ft: h, angle_deg: p.angle_deg || 0, source: p.source + (p.lidar_match ? ' + lidar' : ''),
        evidence: p.polarity + ' patch on its facet, contrast ' + p.contrast + ', rectangularity ' + p.rectangularity + (p.rectangularity >= 0.78 ? ' (strict)' : '') + (dax != null ? ', ' + Math.round(dax) + ' deg off the roof axis' : '') + (lc ? '; lidar: ' + lc.note : '; lidar not checked'), confidence: lc ? (p.lidar_match || lc.glass ? 'medium' : 'low') : 'low',
        counted: !!lc, lidar_check: lc ? lc.note : 'not checked (too few lidar points)' });
    });
    (r.skylights || []).forEach(function (k) { if (k.ortho_match || !k.centroid_lonlat) return;
      sk.push({ key: k.key || ('L' + sk.length), centroid_lonlat: k.centroid_lonlat, w_ft: k.approx_w_ft || k.w_ft || null, h_ft: k.approx_h_ft || k.h_ft || null, angle_deg: 0,
        source: k.source === 'user' ? 'user' : (k.source || 'lidar'), confidence: k.source === 'user' ? 'user' : (k.confidence || 'low'), counted: k.source === 'user',
        lidar_check: k.source === 'user' ? 'user-entered' : 'lidar-only (no matching ortho patch): not counted' }); });
    sk = sk.filter(function (k) { return !rm[k.key]; });
    sk.forEach(function (k) { k.label = 'S' + (++n); });
    r.roof_features = { skylights: sk, decks: (r.decks || []).filter(function (d) { return !rm[d.key]; }), rejected: rej,
      dormers: (r.dormers || []).filter(function (d) { return !d.deleted; }),
      counts: { skylights: sk.filter(function (k) { return k.counted; }).length, skylight_candidates_uncounted: sk.filter(function (k) { return !k.counted; }).length, patches_rejected: rej.length },
      note: 'Candidates (NOT_PROVEN). Not in the billable totals; confirm on site or in the editor.' };
    return r.roof_features;
  }
  /* 0.1.7.6: roofprint vs lidar building mask in the lidar's local metres (class-6 points within 6 m, 0.5 m cells, closed
   * one cell). Best integer-cell translation (±4 m) by IoU; applied to lidar features only when it raises the IoU by >= 0.03 and
   * is not on the search limit. Also the lidar building area farther than 1.5 m outside the roofprint (current-house check). */
  function lidarOutline(L) {
    var ring = L.ring_local, P = (L.points_bbox || []).filter(function (p) { return p[3] === 6; });
    if (!ring || ring.length < 3 || P.length < 30) return null;
    var c = 0.5, x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    P.forEach(function (p) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); });
    ring.forEach(function (p) { x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]); });
    x0 -= 6; y0 -= 6; var GW = Math.ceil((x1 + 6 - x0) / c), GH = Math.ceil((y1 + 6 - y0) / c); if (GW * GH > 2e6) return null;
    var occ = new Uint8Array(GW * GH); P.forEach(function (p) { occ[Math.floor((p[1] - y0) / c) * GW + Math.floor((p[0] - x0) / c)] = 1; });
    function morph(a, dil) { var b = new Uint8Array(GW * GH); for (var y = 1; y < GH - 1; y++) for (var x = 1; x < GW - 1; x++) { var i = y * GW + x;
      b[i] = dil ? (a[i] | a[i - 1] | a[i + 1] | a[i - GW] | a[i + GW]) : (a[i] & a[i - 1] & a[i + 1] & a[i - GW] & a[i + GW]); } return b; }
    occ = morph(morph(occ, true), false);
    function pip(x, y) { var ins = false; for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) { var a = ring[i], b = ring[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) ins = !ins; } return ins; }
    var rc = [], occN = 0; for (var y = 0; y < GH; y++) for (var x = 0; x < GW; x++) { if (occ[y * GW + x]) occN++; if (pip(x0 + (x + 0.5) * c, y0 + (y + 0.5) * c)) rc.push([x, y]); }
    if (rc.length < 20) return null;
    function iou(sx, sy) { var h = 0; rc.forEach(function (p) { var X = p[0] + sx, Y = p[1] + sy; if (X >= 0 && Y >= 0 && X < GW && Y < GH && occ[Y * GW + X]) h++; }); return h / (rc.length + occN - h); }
    var best = { v: -1, x: 0, y: 0 }, R = 8;
    for (var sy = -R; sy <= R; sy++) for (var sx = -R; sx <= R; sx++) { var v = iou(sx, sy) - 0.002 * Math.hypot(sx, sy); if (v > best.v) best = { v: v, x: sx, y: sy }; }
    var i0 = iou(0, 0), i1 = iou(best.x, best.y), lim = Math.abs(best.x) >= R || Math.abs(best.y) >= R;
    var inR = new Uint8Array(GW * GH); rc.forEach(function (p) { var X = p[0] + best.x, Y = p[1] + best.y; if (X >= 0 && Y >= 0 && X < GW && Y < GH) inR[Y * GW + X] = 1; });
    for (var t = 0; t < 3; t++) inR = morph(inR, true);
    var out = 0; for (var q = 0; q < occ.length; q++) if (occ[q] && !inR[q]) out++;
    var F = 10.7639;
    // ring frame -> lidar frame shift in metres (east +, north +); local y is north-up (Web Mercator y), scale k ~ 1
    return { dx_m: best.x * c, dy_m: best.y * c, shift_m: Math.round(Math.hypot(best.x, best.y) * c * 100) / 100, iou0: Math.round(i0 * 1000) / 1000, iou: Math.round(i1 * 1000) / 1000,
      at_limit: lim, applied: !lim && i1 - i0 >= 0.03, lidar_area_sqft: Math.round(occN * c * c * F), roofprint_area_sqft: Math.round(rc.length * c * c * F), outside_area_sqft: Math.round(out * c * c * F),
      method: 'class-6 lidar points within 6 m on a 0.5 m grid (closed one cell) vs the roofprint: IoU over ±4 m translations; lidar building area > 1.5 m outside the roofprint' };
  }
  function shiftFeatures(r, dxm, dym) {
    var lat = r.lat || ((r.decks || [])[0] && r.decks[0].centroid_lonlat[1]) || 42.2, kx = Math.cos(lat * Math.PI / 180) * 111320, ky = 110540;
    function mv(p) { return p ? [Math.round((p[0] + dxm / kx) * 1e7) / 1e7, Math.round((p[1] + dym / ky) * 1e7) / 1e7] : p; }
    (r.decks || []).forEach(function (d) { d.centroid_lonlat = mv(d.centroid_lonlat); if (d.outline_lonlat) d.outline_lonlat = d.outline_lonlat.map(mv); d.lidar_registered = true; });
    (r.dormers || []).forEach(function (d) { if (d.source === 'user') return; if (d.centroid_lonlat) d.centroid_lonlat = mv(d.centroid_lonlat); if (d.coords_lonlat) d.coords_lonlat = d.coords_lonlat.map(mv); d.lidar_registered = true; });
    (r.skylights || []).forEach(function (k) { if (k.source === 'user' || !k.centroid_lonlat) return; k.centroid_lonlat = mv(k.centroid_lonlat); k.lidar_registered = true; });
  }
  /* 0.1.7.6: lidar roof-plane cells (0.5 m, labelled by roofseg plane) in mosaic pixels for the ortho region score, and the
   * roofprint vs lidar building-mask comparison (IoU, best translation, lidar building area outside the roofprint). */
  function lidarCells(m, ring, lo) {
    var A = window.RoofApp, L = A && A.state && A.state.lidar, O = window.RoofOrtho, T = window.RoofTags;
    if (!L || !L.points_full || !L.frame || !T || !T.lidarSeg) return null;
    var sg = T.lidarSeg(L), pid = sg && sg.point_plane; if (!pid) return null;
    var fr = L.frame, R = 6378137, D = Math.PI / 180;
    function ll(p) { var mx = p[0] / fr.k + fr.ox, my = p[1] / fr.k + fr.oy; return [mx / R / D, (2 * Math.atan(Math.exp(my / R)) - Math.PI / 2) / D]; }
    function px(p) { var q = ll(p), w = O.world(q[0], q[1], m.z); return [w[0] - m.ox, w[1] - m.oy]; }
    var res = O.mpp(ll(L.points_full[0])[1], m.z), c = 0.5 / res, cell = {}, ox = lo && lo.applied ? -lo.dx_m / res : 0, oy = lo && lo.applied ? lo.dy_m / res : 0; // into the roofprint frame
    function px0(p) { var q = px(p); return [q[0] + ox, q[1] + oy]; }
    L.points_full.forEach(function (p, i) { if (pid[i] < 0) return; var q = px0(p); cell[Math.floor(q[0] / c) + ',' + Math.floor(q[1] / c)] = pid[i]; });
    var cells = Object.keys(cell).map(function (k) { var a = k.split(',').map(Number); return [(a[0] + 0.5) * c, (a[1] + 0.5) * c, cell[k]]; });
    var out = { cells: cells.length >= 60 ? cells : null };
    return out;
  }
  function orthoStep(result, need, opt) {
    var O = window.RoofOrtho;
    if (!O || opt.noAerial || !result.footprint_geojson) return Promise.resolve(null);
    var tiles = need.map(function (u) { var m = /\/tile\/(\d+)\/(\d+)\/(\d+)/.exec(u); return m && TILE_CACHE[u] ? { z: +m[1], ty: +m[2], tx: +m[3], data: TILE_CACHE[u] } : null; }).filter(Boolean);
    if (!tiles.length) return Promise.resolve(null);
    var z = tiles[0].z, ring = window.RoofCalc.extractRing(result.footprint_geojson);
    if (!ring) return Promise.resolve(null);
    var t0 = Date.now();
    return O.mosaic(z, tiles.filter(function (t) { return t.z === z; })).then(function (m) {
      var lines = (result.line_segments || []).filter(function (g) { return /^(ridge|hip|valley)$/.test(g.type) && !g.deleted && !g.unverified && g.coords_lonlat && g.coords_lonlat.length === 2; })
        .map(function (g) { return g.coords_lonlat; });
      O._last = { m: m, ring: ring, lines: lines };
      var LC = lidarCells(m, ring, result.lidar_outline), al = O.align(ring, m, { apply: !opt.noOrthoAlign && !window.RM_NO_ORTHO_ALIGN, lines: lines, cells: LC && LC.cells });
      al.ms = Date.now() - t0; al.source = 'MassGIS 2025 ortho z' + z;
      result.ortho_align = al;
      // 0.1.7.5: skylight / vent patches at z20 (7.5 cm/px world grid of the 15 cm orthos) with a per-facet background
      var facetsLL = (result.facets || []).map(function (f) { return f.polygon_lonlat; }).filter(function (P) { return P && P.length > 3; });
      var z2 = z + 1, x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      ring.forEach(function (p) { var w = O.world(p[0], p[1], z2); x0 = Math.min(x0, w[0]); x1 = Math.max(x1, w[0]); y0 = Math.min(y0, w[1]); y1 = Math.max(y1, w[1]); });
      var pad = 40 + (al.applied ? Math.abs(al.dx_px) * 2 + Math.abs(al.dy_px) * 2 : 0), tpl = need.filter(function (u) { return /\/tile\/\d+\/\d+\/\d+/.test(u); })[0], urls = [];
      for (var tx = Math.floor((x0 - pad) / 256); tx <= Math.floor((x1 + pad) / 256); tx++) for (var ty = Math.floor((y0 - pad) / 256); ty <= Math.floor((y1 + pad) / 256); ty++)
        urls.push(tpl.replace(/\/tile\/\d+\/\d+\/\d+/, '/tile/' + z2 + '/' + ty + '/' + tx));
      var hi = urls.length <= 30 ? Promise.all(urls.map(function (u) { return fetchTile(u).then(function (d) { var q = /\/tile\/(\d+)\/(\d+)\/(\d+)/.exec(u); return { tx: +q[3], ty: +q[2], data: d }; }, function () { return null; }); }))
        .then(function (ts) { return O.mosaic(z2, ts.filter(Boolean)); }) : Promise.reject(new Error('roof too large for z' + z2));
      return hi.then(function (m2) { O._last2 = { m: m2, ring: ring, al: al, facets: facetsLL }; return O.patches(ring, m2, al, { facets: facetsLL }); }, function () { return O.patches(ring, m, al, { facets: facetsLL }); }).then(function (pt) {
        // fuse with lidar skylight candidates (within 1.2 m)
        var sky = result.skylights || [], kx = Math.cos(ring[0][1] * Math.PI / 180) * 111320, ky = 110540;
        pt.forEach(function (p, i) { p.key = 'O' + i;
          var hit = sky.filter(function (k) { return k.centroid_lonlat && Math.hypot((k.centroid_lonlat[0] - p.centroid_lonlat[0]) * kx, (k.centroid_lonlat[1] - p.centroid_lonlat[1]) * ky) < 1.2; })[0];
          if (hit) { p.lidar_match = hit.key; p.confidence = 'medium'; hit.ortho_match = p.key; } });
        result.ortho_patches = pt;
        roofFeatures(result);
        // Experimental height-aware placement applies only in the aerial composite; geometry/totals untouched.
        if (window.RoofFeatureLean) {
          var L = window.RoofApp && window.RoofApp.state && window.RoofApp.state.lidar;
          result.feature_lean = window.RoofFeatureLean.annotate(result, L, al);
          if (result.feature_lean.applied) result.notes.push('Experimental roof-feature ortho lean (' + result.feature_lean.applied +
            ' deck/dormer candidate(s), NOT_PROVEN): aerial overlay placement only; source geometry and quantities unchanged.');
        }
        return al;
      });
    }).catch(function (e) { result.ortho_align = { status: 'error', error: String(e && e.message || e), applied: false }; return null; });
  }

  /* -> Promise<{html, edges_csv, measurements_csv, summary, result}> */
  function render(result, opt) {
    opt = opt || {};
    var rjson = JSON.stringify(result);
    return engine().then(function (py) {
      var need = opt.noAerial ? [] : JSON.parse(py.globals.get('tiles_needed')(rjson));
      var log0 = TILE_LOG.length, set = py.globals.get('set_tile');
      function fetchAll(list) { return Promise.all(list.map(function (u) { return fetchTile(u).then(function (d) { return [u, d]; }); })); }
      return fetchAll(need).then(function (got) {
        got.forEach(function (x) { set(x[0], x[1]); });
        return orthoStep(result, need, opt).then(function (al) {
          if (!al || !al.applied) return got;
          // the raster is drawn shifted by the offset: fetch any tile the shifted boxes now need
          var need2 = JSON.parse(py.globals.get('tiles_needed')(JSON.stringify(result))), extra = need2.filter(function (u) { return need.indexOf(u) < 0; });
          need = need.concat(extra);
          return fetchAll(extra).then(function (g2) { g2.forEach(function (x) { set(x[0], x[1]); }); return got.concat(g2); });
        });
      }).then(function (got) {
        result.aerial_diag = { tiles_needed: need.length, tiles_loaded: got.filter(function (x) { return x[1]; }).length, cached: need.filter(function (u) { return !!TILE_CACHE[u]; }).length,
          failures: TILE_LOG.slice(log0).slice(-6) };
        rjson = JSON.stringify(result);
        var out = JSON.parse(py.globals.get('render')(rjson, opt.generated || generatedStamp()));
        if (window.RoofTags && result.user_tags) out.html = window.RoofTags.inject(out.html, window.RoofTags.sectionHtml(result.user_tags));
        out.result = result; out.tiles = { needed: need.length, loaded: got.filter(function (x) { return x[1]; }).length };
        return out;
      });
    });
  }

  function printInBrowser(html) {
    var old = document.getElementById('rm-report-frame'); if (old) old.remove();
    var f = document.createElement('iframe'); f.id = 'rm-report-frame'; f.title = 'Roof measurement report (print view)';
    f.style.cssText = 'position:fixed;right:0;bottom:0;width:1px;height:1px;border:0;opacity:0';
    document.body.appendChild(f);
    var d = f.contentWindow.document; d.open(); d.write(html); d.close();
    setTimeout(function () { f.contentWindow.focus(); f.contentWindow.print(); }, 300);
  }

  /* Button handler: build result -> render -> PDF print dialog. */
  function exportPdf(app, statusFn) {
    var say = statusFn || function () {};
    var result;
    var pend = app && app.state && app.state.lidarPending;
    if (pend) return pend.then(function () { return exportPdf(app, statusFn); }, function () { app.state.lidarPending = null; return exportPdf(app, statusFn); });
    try { result = buildResult(app); } catch (e) { say(e.message); return Promise.resolve(null); }
    say('Building PDF report… (first export loads the offline report engine, ~5-15 s)');
    return render(result).then(function (out) {
      window.RoofReport.last = out;
      var name = 'RoofMeasure_' + result.slug;
      if (window.RoofBridge && typeof window.RoofBridge.printHtml === 'function') {
        window.RoofBridge.printHtml(out.html, name);
        say('Report ready: choose "Save as PDF" in the Android print dialog. Aerial tiles ' + out.tiles.loaded + '/' + out.tiles.needed + '.');
      } else {
        printInBrowser(out.html);
        say('Report ready: choose "Save as PDF" in the print dialog. Aerial tiles ' + out.tiles.loaded + '/' + out.tiles.needed + '.');
      }
      return out;
    }).catch(function (e) { say('Report failed: ' + (e && e.message || e)); throw e; });
  }

  function saveText(name, text, type) {
    if (window.RoofBridge && typeof window.RoofBridge.save === 'function') { window.RoofBridge.save(name, text); return; }
    var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: type })); a.download = name; a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  }

  /* 0.1.7.1: preview overlay (display + edit text) -> Save PDF / Share PDF. */
  var current = null, nativeCb = {};
  function frameHtml() {
    var f = document.getElementById('rvFrame'), d = f && f.contentDocument;
    if (!d || !d.documentElement) return current && current.html;
    var ed = d.designMode === 'on'; if (ed) d.designMode = 'off';
    var h = '<!doctype html>\n' + d.documentElement.outerHTML; if (ed) d.designMode = 'on';
    return h;
  }
  function rvSay(m) { var e = document.getElementById('rvStatus'); if (e) e.textContent = m; }
  function deliver(kind, html, name, say) {
    var B = window.RoofBridge;
    if (B && kind === 'share' && typeof B.sharePdf === 'function') { B.sharePdf(html, name); say('Writing PDF… the share sheet opens when it is ready.'); return; }
    if (B && kind === 'save' && typeof B.savePdf === 'function') { B.savePdf(html, name); say('Writing PDF to Downloads…'); return; }
    if (B && typeof B.printHtml === 'function') { B.printHtml(html, name); say('Choose "Save as PDF" in the Android print dialog.'); return; }
    printInBrowser(html); say('Choose "Save as PDF" in the print dialog' + (kind === 'share' ? ', then share the saved file.' : '.'));
  }
  window.RoofReportNative = function (kind, ok, msg) { rvSay((ok ? '' : 'FAILED: ') + msg); var cb = nativeCb[kind]; if (cb) cb(ok, msg); };
  function showPreview(out, name, app, statusFn) {
    var v = document.getElementById('reportView'), f = document.getElementById('rvFrame');
    if (!v || !f) return false;
    current = { html: out.html, name: name };
    f.srcdoc = out.html; v.hidden = false;
    var ed = document.getElementById('rvEdit'); ed.classList.remove('on'); ed.textContent = 'Edit text';
    ed.onclick = function () { var d = f.contentDocument; if (!d) return; var on = d.designMode !== 'on'; d.designMode = on ? 'on' : 'off';
      ed.classList.toggle('on', on); ed.textContent = on ? 'Editing… (tap to stop)' : 'Edit text';
      rvSay(on ? 'Tap any text in the report to change it. Edits go into the saved/shared PDF only.' : 'Edits kept.'); };
    document.getElementById('rvSave').onclick = function () { deliver('save', frameHtml(), name, rvSay); };
    document.getElementById('rvShare').onclick = function () { deliver('share', frameHtml(), name, rvSay); };
    document.getElementById('rvClose').onclick = function () { var d = f.contentDocument; if (d) d.designMode = 'off'; v.hidden = true; };
    var mb = document.getElementById('rvMeas');
    if (mb) mb.onclick = function () { toggleMeasEditor(app, statusFn); };
    var me = document.getElementById('rvEditor'); if (me) me.hidden = true;
    rvSay('Aerial tiles ' + out.tiles.loaded + '/' + out.tiles.needed + '. Review, optionally edit, then Save or Share.');
    return true;
  }
  /* 0.1.7.2: detached structures (MassGIS parcel + structures, lib/structures.js) and per-facet solar index (lib/solar-est.js). */
  function enrich(r, app, say) {
    var Sx = window.RoofStructures, So = window.RoofSolar;
    if (So && r.facets && r.facets.length) {
      try {
        var out = So.solarForFacets(r.facets, +r.lat);
        if (out.status === 'PASS') r.solar = { source: 'in app: lib/solar-est.js (JS port of extras/solar.py estimate path; no PVWatts calls)', pvwatts: { tried: false, worked: false },
          facets: out.facets, totals: out.totals, notes: out.notes };
      } catch (e) { r.notes.push('Extras: solar exposure not available (' + e.message + ').'); }
    }
    if (!Sx || !Sx.listStructures || app.state.noStructures) return Promise.resolve(r);
    if (!/massgis/i.test(String(r.source || ''))) { r.notes.push('Extras: lot structures need a MassGIS roofprint (not available for this source).'); return Promise.resolve(r); }
    say('Looking up other structures on the tax lot (MassGIS) …');
    return withTimeout(Sx.listStructures(+r.lat, +r.lon, { computeRoof: window.RoofCalc.computeRoof, pitch: '6/12', roof_type: 'gable', overhang_ft: 0 }), 25000, 'lot structures').then(function (o) {
      if (!o || o.status !== 'PASS' || !o.structures || !o.structures.length) { r.notes.push('Extras: lot structures not available (' + ((o && (o.error || o.status)) || 'no result') + ').'); return r; }
      var pick = function (obj, keys) { var x = {}; keys.forEach(function (k) { x[k] = obj ? obj[k] : undefined; }); return x; };
      var keep = o.structures.map(function (sx) {
        var m = sx.measurements || {}; if (m.measured_by == null && m.calc_version) m.measured_by = 'core/roofcalc.js v' + m.calc_version;
        var row = pick(sx, ['struct_id', 'class', 'role', 'footprint_area_sqft', 'area_source', 'computed_area_sqft', 'overlap_fraction', 'on_lot', 'sourcetype']);
        row.measurements = pick(m, ['footprint_area_sqft', 'perimeter_ft', 'pitch', 'pitch_factor', 'overhang_ft', 'roof_area_sqft', 'squares', 'eave_lf', 'rake_lf', 'gutter_lf', 'downspouts', 'overhang_source', 'measured_by']);
        return row;
      });
      var parcel = pick(o.parcel || {}, ['loc_id', 'site_addr', 'city', 'area_sqft', 'style', 'stories', 'year_built']);
      try { if (o.parcel && o.parcel.geometry) r.parcel_geojson = o.parcel.geometry; } catch (e) { /* display only */ }
      r.lot_footprints = o.structures.filter(function (sx) { return sx.footprint_geojson; }).map(function (sx) { return { struct_id: sx.struct_id, role: sx.role, geometry: sx.footprint_geojson.geometry || sx.footprint_geojson }; });
      r.structures_on_lot = { source: 'live (in app): lib/structures.js listStructures', module: o.module, version: o.version, verified_at: o.verified_at,
        classification_rule: o.classification_rule, parcel: parcel, structures: keep, lot_total_tool: o.lot_total, rejected_off_lot: (o.rejected_off_lot || []).length };
      if (!r.assessor && (parcel.style || parcel.stories || parcel.year_built)) r.assessor = { style: parcel.style, stories: parcel.stories, year_built: parcel.year_built, source: 'MassGIS L3 parcel / assessor' };
      return r;
    }, function (e) { r.notes.push('Extras: lot structures not available (' + e.message + ').'); return r; });
  }
  /* Structured editor (0.1.7.3): roof model, edge type + length (rakes edited as SLOPED length), interior lines (retype, delete,
   * confirm/count), user-added lines, pitch, waste. Apply rebuilds the report from the live state. */
  function toggleMeasEditor(app, statusFn) {
    var box = document.getElementById('rvEditor'); if (!box || !app) return;
    if (!box.hidden) { box.hidden = true; return; }
    var st = app.state, r = st.result, T = window.RoofTags, E = T.esc, tg = st.tags, LE = tg.lengths || (tg.lengths = {});
    if (!Array.isArray(tg.added)) tg.added = [];
    var segs = (st.facetsLive && st.facetsLive.line_segments) || [], oh = +r.overhang_ft || 0, pf = +r.pitch_factor || 1;
    var pit = Array.prototype.map.call(document.getElementById('pitch').options, function (o) { return o.value; });
    var rmSel = document.getElementById('roofModel'), mi = r.roof_model_info || {};
    var shown = function (e) { var plan = LE[e.i] != null ? +LE[e.i] : e.length_ft; return e.type === 'rake' ? (plan + 2 * oh) * pf : plan; };
    var H = ['<h3>Edit measurements</h3><p class="note">Changes rebuild the report from the on-screen result. Edited values are marked in the report. ' +
      'Rake lengths are SLOPED (along the roof, drip-edge length); eave lengths are level.</p>',
      '<label>Roof model <select id="me-model" aria-label="Roof model">' + Array.prototype.map.call(rmSel.options, function (o) {
        return '<option value="' + o.value + '"' + (o.value === rmSel.value ? ' selected' : '') + '>' + E(o.textContent) + '</option>'; }).join('') + '</select></label> ' +
        '<span class="note">now: ' + E(mi.label || '?') + ' (' + E(mi.source || '?') + ')</span><br>',
      '<label>Pitch <select id="me-pitch">' + pit.map(function (p) { return '<option' + (p === r.pitch ? ' selected' : '') + '>' + E(p) + '</option>'; }).join('') + '</select></label> ',
      '<label>Waste % <input id="me-waste" type="number" min="0" step="1" value="' + r.waste_pct + '" style="width:60px"></label>',
      '<table><thead><tr><th>Edge</th><th>Type</th><th>Length ft</th><th>Basis</th></tr></thead><tbody>'];
    r.edges.forEach(function (e) {
      var v = shown(e);
      H.push('<tr><th scope="row">' + e.i + '</th><td><select data-me-type="' + e.i + '" aria-label="Edge ' + e.i + ' type"><option' + (e.type === 'eave' ? ' selected' : '') + '>eave</option><option' +
        (e.type === 'rake' ? ' selected' : '') + '>rake</option></select></td><td><input data-me-len="' + e.i + '" aria-label="Edge ' + e.i + (e.type === 'rake' ? ' sloped' : '') + ' length in feet" type="number" step="0.1" min="0.1" value="' +
        v.toFixed(1) + '" data-auto="' + v.toFixed(1) + '" style="width:80px"></td><td class="note">' + (e.type === 'rake' ? 'sloped (plan ' + (LE[e.i] != null ? +LE[e.i] : e.length_ft).toFixed(1) + ')' : 'level') + '</td></tr>');
    });
    H.push('</tbody></table>');
    var ls = segs.map(function (sg, i) { return { sg: sg, i: i }; }).filter(function (x) { return x.sg.source === 'lidar' || T.LINE_TYPES.indexOf(x.sg.auto_type || x.sg.type) >= 0; });
    if (ls.length) {
      H.push('<table><thead><tr><th>Line</th><th>Type</th><th>Length ft</th><th>Count it</th><th>Status / source</th></tr></thead><tbody>');
      ls.forEach(function (x) { var cur = x.sg.deleted ? 'none' : x.sg.type, types = x.sg.source === 'lidar' ? T.ALL_TYPES : T.LINE_TYPES;
        H.push('<tr><th scope="row">L' + x.i + '</th><td><select data-me-line="' + x.i + '" aria-label="Line ' + x.i + ' type">' + types.concat(['none']).map(function (t) {
          return '<option value="' + t + '"' + (cur === t ? ' selected' : '') + '>' + (t === 'none' ? 'delete (not counted)' : t) + '</option>'; }).join('') + '</select></td><td>' + (+x.sg.length_ft).toFixed(1) +
          '</td><td><input type="checkbox" data-me-conf="' + x.i + '" aria-label="Count line ' + x.i + ' (confirm)"' + (tg.confirmed['L' + x.i] ? ' checked' : '') + '></td><td class="note">' +
          (x.sg.deleted ? 'deleted' : x.sg.unverified ? 'UNVERIFIED candidate, not counted' : 'counted') + (x.sg.source === 'lidar' ? ' · lidar (' + E(x.sg.lidar_source || '') + ', ' + E(x.sg.lidar_conf || '') + ')' : x.sg.lidar_confirmed ? ' · lidar-confirmed' : '') + '</td></tr>'); });
      H.push('</tbody></table>');
    }
    H.push('<h4>Lines you add (user-entered; counted in the totals)</h4><table><thead><tr><th>Type</th><th>Length ft (sloped/3-D)</th><th>Note / source</th><th></th></tr></thead><tbody id="me-added">');
    var addRow = function (a, j) { return '<tr data-me-add="' + j + '"><td><select aria-label="Added line ' + j + ' type">' + T.ALL_TYPES.map(function (t) { return '<option' + (a.type === t ? ' selected' : '') + '>' + t + '</option>'; }).join('') +
      '</select></td><td><input type="number" step="0.1" min="0" aria-label="Added line ' + j + ' length in feet" value="' + (a.length_ft || '') + '" style="width:80px"></td><td><input type="text" aria-label="Added line ' + j + ' note" value="' + E(a.note || '') +
      '" placeholder="e.g. tape on site"></td><td><button type="button" data-me-del="' + j + '">Remove</button></td></tr>'; };
    tg.added.forEach(function (a, j) { H.push(addRow(a, j)); });
    H.push('</tbody></table><button type="button" id="me-addline">Add a line</button><br>');
    // skylights: lidar candidates (remove) + user-entered (add/remove)
    if (!Array.isArray(tg.skylights)) tg.skylights = []; if (!tg.skylightsDeleted) tg.skylightsDeleted = {};
    var skyL = (st.lidar && T.lidarSeg && T.lidarSeg(st.lidar) && T.lidarSeg(st.lidar).skylights) || [];
    H.push('<h4>Skylights (lidar candidates are NOT_PROVEN; keep, remove, or add your own)</h4><table><thead><tr><th>#</th><th>Size ft (w × h)</th><th>Evidence</th><th>Keep</th></tr></thead><tbody id="me-sky">');
    skyL.forEach(function (k, i) { H.push('<tr><th scope="row">S' + i + '</th><td>' + k.approx_w_ft + ' × ' + k.approx_h_ft + '</td><td class="note">' + E(k.source) + ' (' + E(k.confidence) + ')</td><td><input type="checkbox" data-me-skyl="S' + i + '" aria-label="Keep skylight candidate S' + i + '"' + (tg.skylightsDeleted['S' + i] ? '' : ' checked') + '></td></tr>'); });
    var skyRow = function (k, j) { return '<tr data-me-skyu="' + j + '"><th scope="row">U' + j + '</th><td><input type="number" step="0.1" min="0" aria-label="Skylight ' + j + ' width ft" value="' + (k.w_ft || '') + '" style="width:60px"> × <input type="number" step="0.1" min="0" aria-label="Skylight ' + j + ' height ft" value="' + (k.h_ft || '') + '" style="width:60px"></td><td><input type="text" aria-label="Skylight ' + j + ' note / location" value="' + E(k.note || '') + '" placeholder="e.g. rear plane, near ridge"></td><td><button type="button" data-me-del="sky' + j + '">Remove</button></td></tr>'; };
    tg.skylights.forEach(function (k, j) { H.push(skyRow(k, j)); });
    H.push('</tbody></table><button type="button" id="me-addsky">Add a skylight</button><br>');
    // dormers (0.1.7.4): lidar candidates (keep to count their gutters) + user-entered; returns yes/no; inspect & clean
    if (!tg.dormers) tg.dormers = {}; if (!Array.isArray(tg.dormersAdded)) tg.dormersAdded = [];
    var dmL = (st.lidar && T.lidarSeg && T.dormers) ? T.dormers(T.lidarSeg(st.lidar), { dormers: tg.dormers }) : [];
    var retSel = function (v, lab2) { return '<select aria-label="' + lab2 + '">' + ['unknown', 'yes', 'no'].map(function (o) { return '<option' + (v === o ? ' selected' : '') + '>' + o + '</option>'; }).join('') + '</select>'; };
    H.push('<h4>Dormers and dormer gutters (inspect and clean: debris at dormer gutters and returns can let water in)</h4><table><thead><tr><th>#</th><th>Type</th><th>Gutter LF</th><th>Returns</th><th>Keep</th></tr></thead><tbody id="me-dorm">');
    dmL.forEach(function (d) { if (d.source !== 'lidar') return; H.push('<tr data-me-dorl="' + d.key + '"><th scope="row">' + d.key + '</th><td>' + E(d.type) + ' (' + E(d.confidence) + ')</td><td><input type="number" step="0.1" min="0" aria-label="Dormer ' + d.key + ' gutter feet" value="' + (d.gutter_lf || '') + '" style="width:70px"></td><td>' +
      retSel(d.returns, 'Dormer ' + d.key + ' gutter returns') + '</td><td><input type="checkbox" aria-label="Keep dormer ' + d.key + '"' + (d.kept ? ' checked' : '') + '></td></tr>'); });
    var dRow = function (a, j) { return '<tr data-me-doru="' + j + '"><th scope="row">UD' + j + '</th><td><input type="text" aria-label="Dormer ' + j + ' type" value="' + E(a.type || 'dormer') + '" style="width:90px"></td><td><input type="number" step="0.1" min="0" aria-label="Dormer ' + j + ' gutter feet" value="' + (a.gutter_lf || '') + '" style="width:70px"></td><td>' +
      retSel(a.returns || 'unknown', 'Dormer ' + j + ' gutter returns') + '</td><td><button type="button" data-me-del="dor' + j + '">Remove</button></td></tr>'; };
    tg.dormersAdded.forEach(function (a, j) { H.push(dRow(a, j)); });
    H.push('</tbody></table><button type="button" id="me-adddorm">Add a dormer</button><br>');
    H.push('<button id="me-apply">Apply and rebuild report</button> <button id="me-reset">Reset edits</button>');
    box.innerHTML = H.join(''); box.hidden = false;
    var q = function (sel) { return box.querySelectorAll(sel); };
    var nAdd = tg.added.length;
    document.getElementById('me-addline').onclick = function () { var tb = document.getElementById('me-added'); tb.insertAdjacentHTML('beforeend', addRow({ type: 'hip' }, nAdd++)); };
    var nSky = tg.skylights.length;
    document.getElementById('me-addsky').onclick = function () { document.getElementById('me-sky').insertAdjacentHTML('beforeend', skyRow({}, nSky++)); };
    var nDor = tg.dormersAdded.length;
    document.getElementById('me-adddorm').onclick = function () { document.getElementById('me-dorm').insertAdjacentHTML('beforeend', dRow({}, nDor++)); };
    box.addEventListener('click', function (ev) { var b = ev.target.closest && ev.target.closest('[data-me-del]'); if (b) { var tr = b.closest('tr'); if (tr) tr.remove(); } });
    document.getElementById('me-reset').onclick = function () { tg.lengths = {}; st.overrides = {}; tg.lines = {}; tg.added = []; tg.skylights = []; tg.skylightsDeleted = {}; tg.dormers = {}; tg.dormersAdded = []; box.hidden = true; app.render && app.render(); preview(app, statusFn); };
    document.getElementById('me-apply').onclick = function () {
      var lab = 'report editor';
      var mv = document.getElementById('me-model').value;
      if (mv !== rmSel.value) { rmSel.value = mv; st.modelAuto = null; st.overrides = {}; tg.layers['roof-model'] = lab; }
      Array.prototype.forEach.call(q('[data-me-type]'), function (el) { var i = +el.dataset.meType; if (el.value !== r.edges[i].type) { st.overrides[i] = el.value; tg.layers['edge-type:' + i] = lab; } });
      Array.prototype.forEach.call(q('[data-me-len]'), function (el) { var i = +el.dataset.meLen, v = +el.value, e = r.edges[i];
        if (!isFinite(v) || v <= 0 || Math.abs(v - +el.dataset.auto) < 0.05) return;
        var typ = st.overrides[i] || e.type, plan = typ === 'rake' ? v / pf - 2 * oh : v; // rakes are entered sloped
        if (plan > 0) LE[i] = Math.round(plan * 100) / 100; });
      Array.prototype.forEach.call(q('[data-me-line]'), function (el) { var i = +el.dataset.meLine, sg = segs[i], cur = sg.deleted ? 'none' : sg.type;
        if (el.value !== cur) tg.lines[i] = { type: el.value, layer: lab }; });
      Array.prototype.forEach.call(q('[data-me-conf]'), function (el) { var k = 'L' + el.dataset.meConf; if (el.checked) tg.confirmed[k] = tg.confirmed[k] || lab; else delete tg.confirmed[k]; });
      tg.added = Array.prototype.map.call(q('[data-me-add]'), function (tr) { var sel = tr.querySelector('select'), ins = tr.querySelectorAll('input');
        return { type: sel.value, length_ft: +ins[0].value, note: ins[1].value, source: 'user-entered (report editor)' }; }).filter(function (a) { return a.length_ft > 0; });
      Array.prototype.forEach.call(q('[data-me-skyl]'), function (el) { if (el.checked) delete tg.skylightsDeleted[el.dataset.meSkyl]; else tg.skylightsDeleted[el.dataset.meSkyl] = lab; });
      tg.skylights = Array.prototype.map.call(q('[data-me-skyu]'), function (tr) { var ins = tr.querySelectorAll('input');
        return { w_ft: +ins[0].value || null, h_ft: +ins[1].value || null, note: ins[2].value, source: 'user-entered (report editor)' }; }).filter(function (k) { return k.w_ft || k.h_ft || k.note; });
      Array.prototype.forEach.call(q('[data-me-dorl]'), function (tr) { var ins = tr.querySelectorAll('input'), sel = tr.querySelector('select');
        tg.dormers[tr.dataset.meDorl] = { keep: ins[1].checked, gutter_lf: +ins[0].value || null, returns: sel.value, layer: lab }; });
      tg.dormersAdded = Array.prototype.map.call(q('[data-me-doru]'), function (tr) { var ins = tr.querySelectorAll('input'), sel = tr.querySelector('select');
        return { type: ins[0].value || 'dormer', gutter_lf: +ins[1].value || null, returns: sel.value, source: 'user-entered (report editor)' }; }).filter(function (a) { return a.gutter_lf || a.type; });
      var pe = document.getElementById('pitch'), pv = document.getElementById('me-pitch').value;
      if (pv !== r.pitch) { pe.value = pv; st.pitchSource = 'manual'; st.pitchConfidence = null; }
      document.getElementById('waste').value = document.getElementById('me-waste').value;
      app.render && app.render();
      box.hidden = true; preview(app, statusFn);
    };
  }
  function preview(app, statusFn) {
    var say = statusFn || function () {};
    var pend = app && app.state && app.state.lidarPending;
    if (pend) { say('Waiting for the lidar pitch to finish before building the report …'); return pend.then(function () { return preview(app, statusFn); }, function () { app.state.lidarPending = null; return preview(app, statusFn); }); }
    var result;
    try { result = buildResult(app); } catch (e) { say(e.message); return Promise.resolve(null); }
    // 0.1.7.5: lidar points vs the 3-D facets model (per-facet point-to-plane residuals) for the appendix
    try { if (window.Roof3D && window.Roof3D.registration) result.lidar_model_fit = window.Roof3D.registration(app, result); } catch (e) { result.lidar_model_fit = { error: String(e && e.message || e) }; }
    var pre = prefetchTiles(result); // aerial tiles download in parallel with the lot/solar lookups
    return Promise.all([enrich(result, app, say), pre]).then(function () {
      say('Building report… (first time loads the offline report engine, ~5-15 s)');
      return render(result);
    }).then(function (out) {
      window.RoofReport.last = out;
      var name = 'RoofMeasure_' + result.slug;
      if (!showPreview(out, name, app, statusFn)) deliver('save', out.html, name, say);
      else say('Report ready (preview open).');
      return out;
    }).catch(function (e) { say('Report failed: ' + (e && e.message || e)); throw e; });
  }

  window.RoofReport = { TILE_CACHE: TILE_CACHE, TILE_LOG: TILE_LOG, applyPerFacet: applyPerFacet, buildResult: buildResult, render: render, exportPdf: exportPdf, preview: preview, frameHtml: frameHtml, deliver: deliver, nativeCb: nativeCb, engine: engine, saveText: saveText,
    printInBrowser: printInBrowser, PYODIDE_URL: PYODIDE_URL, PY_BASE: PY_BASE };
})();
