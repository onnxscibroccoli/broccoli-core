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
  function showPreview(out, name) {
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
    rvSay('Aerial tiles ' + out.tiles.loaded + '/' + out.tiles.needed + '. Review, optionally edit, then Save or Share.');
    return true;
  }
  function preview(app, statusFn) {
    var say = statusFn || function () {};
    var result;
    try { result = buildResult(app); } catch (e) { say(e.message); return Promise.resolve(null); }
    say('Building report… (first time loads the offline report engine, ~5-15 s)');
    return render(result).then(function (out) {
      window.RoofReport.last = out;
      var name = 'RoofMeasure_' + result.slug;
      if (!showPreview(out, name)) deliver('save', out.html, name, say);
      else say('Report ready (preview open).');
      return out;
    }).catch(function (e) { say('Report failed: ' + (e && e.message || e)); throw e; });
  }

  window.RoofReport = { buildResult: buildResult, render: render, exportPdf: exportPdf, preview: preview, frameHtml: frameHtml, deliver: deliver, nativeCb: nativeCb, engine: engine, saveText: saveText,
    printInBrowser: printInBrowser, PYODIDE_URL: PYODIDE_URL, PY_BASE: PY_BASE };
})();
