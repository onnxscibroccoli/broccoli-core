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
    '    try: br.aerial_from_ortho(json.loads(rjson))',
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
      e.length_ft_auto = e.length_ft; e.length_ft = Math.round(v * 100) / 100; e.length_source = 'user edit'; nLE++;
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
          if (T) lineChanges = T.applyLineTags(f, tags, T.facetsKey(r, L, useR));
          r.lines = f.lines;
          r.facets = (f.facets || []).map(function (x) { return { id: x.id, area_sqft: x.area_sqft, plan_area_sqft: x.plan_area_sqft, pitch: x.pitch,
            edge_type: x.edge_type, edge_index: x.edge_index, downslope_bearing_deg: x.downslope_bearing_deg, polygon_lonlat: x.polygon_lonlat }; });
          if (Array.isArray(f.line_segments)) r.line_segments = f.line_segments;
          r.facets_ridge_bearing_source = f.ridge_bearing_source || null;
          r.facets_lidar_inputs = ridge != null && !!lidarUsed;
          if (f.line_counts) r.line_counts = f.line_counts;
          r.facets_source = 'facets computeFacets ' + (f.version || '') + ' (in-app lib/facets.js; method ' + String(f.method || '?').split(':')[0] + ', roof_type ' + f.roof_type + ')';
          r.notes.push('Ridge/hip/valley lengths from the facets lane (straight-skeleton model of the 2-D roofprint, equal pitch)' +
            (lineChanges.length ? ', with ' + lineChanges.length + ' interior line(s) re-typed by the user' : '') + '; verify on site.');
        } else {
          r.notes.push('Facets lane returned no lines' + (f && f.unsupported ? ' (unsupported roof style)' : '') + '; ridge/hip/valley not measured.');
        }
      } catch (e) { r.notes.push('Facets lane error: ' + e.message + '; ridge/hip/valley not measured.'); }
    } else {
      r.notes.push('Facets module not loaded in the app; ridge/hip/valley not measured.');
    }
    if (T && st.perFacetPitch && r.facets && r.facets.length && L && Array.isArray(L.planes) && L.planes.length) {
      var pr = T.matchPlanes(r.facets, L.planes);
      if (pr.every(function (x) { return x.lidar_area_sqft != null; })) {
        var tot = 0;
        r.facets.forEach(function (fx, i) { fx.model_pitch = fx.pitch; fx.model_area_sqft = fx.area_sqft; fx.pitch = pr[i].lidar_pitch; fx.area_sqft = pr[i].lidar_area_sqft; tot += pr[i].lidar_area_sqft; });
        r.roof_area_sqft_single_pitch = r.roof_area_sqft; r.roof_area_sqft = Math.round(tot * 10) / 10;
        r.squares = Math.round(r.roof_area_sqft) / 100; r.squares_with_waste = Math.round(r.roof_area_sqft * (1 + r.waste_pct / 100)) / 100;
        r.per_facet_pitch_used = true;
        r.notes.push('OPT-IN per-facet lidar pitch: roof area ' + r.roof_area_sqft + ' sq ft is the sum of facet plan areas at each facet\'s matched lidar plane pitch ' +
          '(single-pitch ' + r.pitch + ' area was ' + r.roof_area_sqft_single_pitch + ' sq ft). Rake, ridge/hip/valley and the Summary pitch still use ' + r.pitch + '. NOT_PROVEN against field measurements.');
      } else r.notes.push('Per-facet lidar pitch was requested but some facets had no matching lidar plane; single pitch ' + r.pitch + ' used for all totals.');
    } else if (st.perFacetPitch) r.notes.push('Per-facet lidar pitch was requested but no lidar planes/facets are available; single pitch used.');
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
    var refs = Object.keys(st.refLayersViewed || {});
    if (refs.length) r.notes.push('Visual reference layers viewed in the app (display only; nothing measured, traced, snapped or stored from them): ' + refs.join(', ') + '.');
    var un = (document.getElementById('userNotes') || {}).value;
    if (un && String(un).trim()) String(un).trim().split(/\n+/).forEach(function (line) { r.notes.push('User note: ' + line.trim()); });
    r.notes.push('Report generated in the RoofMeasure app from the on-screen measurement (edge labels and pitch as shown at export time).');
    r.core_version = RC.VERSION || r.calc_version;
    r.slug = slugify(r.address);
    // strip app-only edge geometry the report does not need (keeps the JSON small)
    return r;
  }

  function fetchTile(url) {
    var ctl = window.AbortController ? new AbortController() : null;
    var t = setTimeout(function () { if (ctl) ctl.abort(); }, 10000);
    return fetch(url, ctl ? { signal: ctl.signal } : {}).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status); return r.arrayBuffer();
    }).then(function (b) { clearTimeout(t); return new Uint8Array(b); }, function () { clearTimeout(t); return null; });
  }

  function generatedStamp() {
    var d = new Date(), z = function (n) { return (n < 10 ? '0' : '') + n; };
    var tz = '';
    try { tz = new Intl.DateTimeFormat('en-US', { timeZoneName: 'short' }).formatToParts(d).filter(function (x) { return x.type === 'timeZoneName'; })[0].value; } catch (e) { tz = ''; }
    return d.getFullYear() + '-' + z(d.getMonth() + 1) + '-' + z(d.getDate()) + ' ' + z(d.getHours()) + ':' + z(d.getMinutes()) + (tz ? ' ' + tz : '');
  }

  /* -> Promise<{html, edges_csv, measurements_csv, summary, result}> */
  function render(result, opt) {
    opt = opt || {};
    var rjson = JSON.stringify(result);
    return engine().then(function (py) {
      var need = opt.noAerial ? [] : JSON.parse(py.globals.get('tiles_needed')(rjson));
      return Promise.all(need.map(function (u) { return fetchTile(u).then(function (d) { return [u, d]; }); })).then(function (got) {
        var set = py.globals.get('set_tile');
        got.forEach(function (x) { set(x[0], x[1]); });
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
      r.structures_on_lot = { source: 'live (in app): lib/structures.js listStructures', module: o.module, version: o.version, verified_at: o.verified_at,
        classification_rule: o.classification_rule, parcel: parcel, structures: keep, lot_total_tool: o.lot_total, rejected_off_lot: (o.rejected_off_lot || []).length };
      if (!r.assessor && (parcel.style || parcel.stories || parcel.year_built)) r.assessor = { style: parcel.style, stories: parcel.stories, year_built: parcel.year_built, source: 'MassGIS L3 parcel / assessor' };
      return r;
    }, function (e) { r.notes.push('Extras: lot structures not available (' + e.message + ').'); return r; });
  }
  /* Structured editor: edge type + length, interior line types, pitch, waste; Apply rebuilds the report from the live state. */
  function toggleMeasEditor(app, statusFn) {
    var box = document.getElementById('rvEditor'); if (!box || !app) return;
    if (!box.hidden) { box.hidden = true; return; }
    var st = app.state, r = st.result, T = window.RoofTags, E = T.esc, tg = st.tags, LE = tg.lengths || (tg.lengths = {});
    var segs = (st.facetsLive && st.facetsLive.line_segments) || [];
    var pit = Array.prototype.map.call(document.getElementById('pitch').options, function (o) { return o.value; });
    var H = ['<h3>Edit measurements</h3><p class="note">Changes rebuild the report from the on-screen result. Edited values are marked in the report.</p>',
      '<label>Pitch <select id="me-pitch">' + pit.map(function (p) { return '<option' + (p === r.pitch ? ' selected' : '') + '>' + E(p) + '</option>'; }).join('') + '</select></label> ',
      '<label>Waste % <input id="me-waste" type="number" min="0" step="1" value="' + r.waste_pct + '" style="width:60px"></label>',
      '<table><thead><tr><th>Edge</th><th>Type</th><th>Length ft</th></tr></thead><tbody>'];
    r.edges.forEach(function (e) {
      H.push('<tr><th scope="row">' + e.i + '</th><td><select data-me-type="' + e.i + '" aria-label="Edge ' + e.i + ' type"><option' + (e.type === 'eave' ? ' selected' : '') + '>eave</option><option' +
        (e.type === 'rake' ? ' selected' : '') + '>rake</option></select></td><td><input data-me-len="' + e.i + '" aria-label="Edge ' + e.i + ' length in feet" type="number" step="0.1" min="0.1" value="' +
        (LE[e.i] != null ? LE[e.i] : e.length_ft.toFixed(1)) + '" data-auto="' + e.length_ft.toFixed(1) + '" style="width:80px"></td></tr>');
    });
    H.push('</tbody></table>');
    var ls = segs.map(function (sg, i) { return { sg: sg, i: i }; }).filter(function (x) { return T.LINE_TYPES.indexOf(x.sg.type) >= 0; });
    if (ls.length) {
      H.push('<table><thead><tr><th>Line</th><th>Type</th><th>Length ft</th></tr></thead><tbody>');
      ls.forEach(function (x) { H.push('<tr><th scope="row">L' + x.i + '</th><td><select data-me-line="' + x.i + '" aria-label="Line ' + x.i + ' type">' + T.LINE_TYPES.map(function (t) {
        return '<option' + (x.sg.type === t ? ' selected' : '') + '>' + t + '</option>'; }).join('') + '</select></td><td>' + (+x.sg.length_ft).toFixed(1) + '</td></tr>'); });
      H.push('</tbody></table>');
    }
    H.push('<button id="me-apply">Apply and rebuild report</button> <button id="me-reset">Reset edits</button>');
    box.innerHTML = H.join(''); box.hidden = false;
    var q = function (sel) { return box.querySelectorAll(sel); };
    document.getElementById('me-reset').onclick = function () { tg.lengths = {}; st.overrides = {}; tg.lines = {}; box.hidden = true; app.render && app.render(); preview(app, statusFn); };
    document.getElementById('me-apply').onclick = function () {
      var lab = 'report editor';
      Array.prototype.forEach.call(q('[data-me-type]'), function (el) { var i = +el.dataset.meType; if (el.value !== r.edges[i].type) { st.overrides[i] = el.value; tg.layers['edge-type:' + i] = lab; } });
      Array.prototype.forEach.call(q('[data-me-len]'), function (el) { var i = +el.dataset.meLen, v = +el.value;
        if (isFinite(v) && v > 0 && Math.abs(v - +el.dataset.auto) >= 0.05) LE[i] = v; else if (LE[i] != null && Math.abs(v - +el.dataset.auto) < 0.05) delete LE[i]; });
      Array.prototype.forEach.call(q('[data-me-line]'), function (el) { var i = +el.dataset.meLine; if (el.value !== segs[i].type || tg.lines[i]) tg.lines[i] = { type: el.value, layer: lab }; });
      var pe = document.getElementById('pitch'), pv = document.getElementById('me-pitch').value;
      if (pv !== r.pitch) { pe.value = pv; st.pitchSource = 'manual'; st.pitchConfidence = null; }
      document.getElementById('waste').value = document.getElementById('me-waste').value;
      app.render && app.render();
      box.hidden = true; preview(app, statusFn);
    };
  }
  function preview(app, statusFn) {
    var say = statusFn || function () {};
    var result;
    try { result = buildResult(app); } catch (e) { say(e.message); return Promise.resolve(null); }
    return enrich(result, app, say).then(function () {
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

  window.RoofReport = { buildResult: buildResult, render: render, exportPdf: exportPdf, preview: preview, frameHtml: frameHtml, deliver: deliver, nativeCb: nativeCb, engine: engine, saveText: saveText,
    printInBrowser: printInBrowser, PYODIDE_URL: PYODIDE_URL, PY_BASE: PY_BASE };
})();
