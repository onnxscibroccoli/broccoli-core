// SPDX-License-Identifier: MIT
/**
 * view3d.js — interactive 3-D roof model view and editor (0.1.7.4), three.js in the WebView.
 * Built ONLY from free data: the MassGIS roofprint (or a manual outline), the facets roof model at the measured pitch
 * (per-facet lidar pitch when used), and the USGS 3DEP lidar roof points (optional point layer). No imagery is used.
 * Orbit / zoom; move outline vertices; move ridge/hip/valley endpoints; set a facet's pitch; re-type a line.
 * Edits are written to the same state the 2-D editor uses (outline ring, tags.lineMoves, tags.lines, tags.facetPitch)
 * so they feed the measurements and the report, where they are listed as user edits.
 * Globals: window.Roof3D = { open, close, apply, info }.
 */
(function () {
  'use strict';
  var loading = null, S = null;
  var COL = { eave: 0x2563eb, rake: 0xea580c, ridge: 0xdc2626, hip: 0x9333ea, valley: 0x0d9488, wall_flashing: 0x64748b };
  function loadThree() {
    if (window.THREE && window.THREE.OrbitControls) return Promise.resolve();
    if (loading) return loading;
    loading = new Promise(function (res, rej) { var s = document.createElement('script'); s.src = 'vendor/three/three-rm.min.js';
      s.onload = function () { res(); }; s.onerror = function () { loading = null; rej(new Error('3-D library failed to load')); }; document.head.appendChild(s); });
    return loading;
  }
  function el(tag, attrs, html) { var e = document.createElement(tag); Object.keys(attrs || {}).forEach(function (k) { e.setAttribute(k, attrs[k]); }); if (html != null) e.innerHTML = html; return e; }

  function frame(ring) {
    var lon0 = 0, lat0 = 0; ring.forEach(function (p) { lon0 += p[0]; lat0 += p[1]; }); lon0 /= ring.length; lat0 /= ring.length;
    var ky = 110540 * 3.280839895, kx = Math.cos(lat0 * Math.PI / 180) * 111320 * 3.280839895;
    return { f: function (ll) { return [(ll[0] - lon0) * kx, (ll[1] - lat0) * ky]; }, b: function (p) { return [lon0 + p[0] / kx, lat0 + p[1] / ky]; } };
  }
  function dLine(p, a, b) { var dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1; return Math.abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / L; }
  function dSeg(p, a, b) { var dx = b[0] - a[0], dy = b[1] - a[1], L = dx * dx + dy * dy, t = L ? ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L : 0; t = Math.max(0, Math.min(1, t)); return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy); }
  function inPoly(p, P) { var c = false; for (var i = 0, j = P.length - 1; i < P.length; j = i++) { var a = P[i], b = P[j];
    if ((a[1] > p[1]) !== (b[1] > p[1]) && p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]) c = !c; } return c; }
  function nearPoly(p, P, tol) { if (inPoly(p, P)) return true; for (var i = 0; i < P.length; i++) if (dSeg(p, P[i], P[(i + 1) % P.length]) <= tol) return true; return false; }

  /* model: facets with a height function h(p) = distance to the facet's eave line x rise/12 */
  function buildModel(app, r) {
    var st = app.state, F = frame(st.ring), ring = st.ring.map(F.f);
    var facets = (r.facets || []).map(function (fx) {
      var poly = (fx.polygon_lonlat || []).map(F.f); if (poly.length > 2 && poly[0][0] === poly[poly.length - 1][0] && poly[0][1] === poly[poly.length - 1][1]) poly.pop();
      var rise = /^(\d+(?:\.\d+)?)\/12$/.exec(String(fx.pitch || '')), s = rise ? +rise[1] / 12 : 0;
      // height above the eave: distance up-slope from the facet's lowest (down-slope-most) point x rise/12
      var bd = (fx.downslope_bearing_deg != null ? fx.downslope_bearing_deg : NaN) * Math.PI / 180, d = [Math.sin(bd), Math.cos(bd)], ok = isFinite(bd) && s > 0;
      var tmax = ok ? Math.max.apply(null, poly.map(function (p) { return p[0] * d[0] + p[1] * d[1]; })) : 0;
      return { id: fx.id, pitch: fx.pitch, user: !!fx.user_pitch, poly: poly, plan: fx.plan_area_sqft, area: fx.area_sqft,
        h: function (p) { return ok ? Math.max(0, tmax - (p[0] * d[0] + p[1] * d[1])) * s : 0; } };
    }).filter(function (x) { return x.poly.length >= 3; });
    function zAt(p) { var z = 0, hit = false; facets.forEach(function (fx) { if (nearPoly(p, fx.poly, 0.6)) { var h = fx.h(p); if (!hit || h > z) { z = h; hit = true; } } }); return z; }
    var lines = (r.line_segments || []).map(function (sg, i) { return { i: i, sg: sg }; }).filter(function (x) { return x.sg.coords_lonlat && !x.sg.deleted && COL[x.sg.type] != null; })
      .map(function (x) { var a = F.f(x.sg.coords_lonlat[0]), b = F.f(x.sg.coords_lonlat[1]); return { i: x.i, type: x.sg.type, cand: !!x.sg.unverified, a: a, b: b, za: zAt(a), zb: zAt(b), len: x.sg.length_ft, src: x.sg.source }; });
    return { F: F, ring: ring, facets: facets, lines: lines, zAt: zAt };
  }

  function lidarCloud(app, M) {
    var L = app.state.lidar, P = L && L.points_full, fr = L && L.frame; if (!P || !fr || !P.length) return null;
    var R = 6378137, D = Math.PI / 180, pts = [], dz = [];
    for (var i = 0; i < P.length; i += Math.max(1, Math.floor(P.length / 6000))) { var p = P[i]; if (!p[5]) continue;
      var mx = p[0] / fr.k + fr.ox, my = p[1] / fr.k + fr.oy, ll = [mx / R / D, (2 * Math.atan(Math.exp(my / R)) - Math.PI / 2) / D], q = M.F.f(ll), z = p[2] * 3.280839895;
      pts.push([q[0], q[1], z]); dz.push(z - M.zAt(q)); }
    if (!pts.length) return null;
    var srt = dz.slice().sort(function (a, b) { return a - b; }), off = srt[srt.length >> 1];
    return { pts: pts.map(function (p, k) { return [p[0], p[1], p[2] - off, dz[k] - off]; }), offset_ft: off };
  }

  function v3(p, z) { return new THREE.Vector3(p[0], z, -p[1]); }

  function scene(M, cloud) {
    var T = THREE, g = new T.Group();
    M.facets.forEach(function (fx) {
      var tri = T.ShapeUtils.triangulateShape(fx.poly.map(function (p) { return new T.Vector2(p[0], p[1]); }), []), pos = [];
      tri.forEach(function (t) { t.forEach(function (k) { var p = fx.poly[k]; pos.push(p[0], fx.h(p), -p[1]); }); });
      var geo = new T.BufferGeometry(); geo.setAttribute('position', new T.Float32BufferAttribute(pos, 3)); geo.computeVertexNormals();
      var m = new T.Mesh(geo, new T.MeshLambertMaterial({ color: fx.user ? 0xfbbf24 : 0xcbd5e1, side: T.DoubleSide, transparent: true, opacity: 0.92 }));
      m.userData = { kind: 'facet', id: fx.id }; g.add(m);
      var c = [0, 0]; fx.poly.forEach(function (p) { c[0] += p[0] / fx.poly.length; c[1] += p[1] / fx.poly.length; }); fx.c = c;
    });
    // walls (outline extruded 9 ft down) and outline
    var wpos = []; M.ring.forEach(function (p, i) { var q = M.ring[(i + 1) % M.ring.length]; wpos.push(p[0], 0, -p[1], q[0], 0, -q[1], q[0], -9, -q[1], p[0], 0, -p[1], q[0], -9, -q[1], p[0], -9, -p[1]); });
    var wg = new T.BufferGeometry(); wg.setAttribute('position', new T.Float32BufferAttribute(wpos, 3)); wg.computeVertexNormals();
    g.add(new T.Mesh(wg, new T.MeshLambertMaterial({ color: 0x94a3b8, side: T.DoubleSide, transparent: true, opacity: 0.35 })));
    M.lines.forEach(function (l) {
      var geo = new T.BufferGeometry().setFromPoints([v3(l.a, l.za + 0.05), v3(l.b, l.zb + 0.05)]);
      var mat = l.cand ? new T.LineDashedMaterial({ color: COL[l.type], dashSize: 1.5, gapSize: 1, transparent: true, opacity: 0.6 }) : new T.LineBasicMaterial({ color: COL[l.type] });
      var ln = new T.Line(geo, mat); if (l.cand) ln.computeLineDistances(); ln.userData = { kind: 'line', i: l.i }; g.add(ln);
      // fat invisible pick tube
      var tube = new T.Mesh(new T.CylinderGeometry(0.6, 0.6, Math.max(0.5, Math.hypot(l.b[0] - l.a[0], l.b[1] - l.a[1], l.zb - l.za)), 6), new T.MeshBasicMaterial({ visible: false }));
      var A = v3(l.a, l.za), B = v3(l.b, l.zb); tube.position.copy(A.clone().add(B).multiplyScalar(0.5)); tube.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), B.clone().sub(A).normalize());
      tube.userData = { kind: 'line', i: l.i }; g.add(tube);
    });
    // eave/rake outline coloured by edge type
    (M.edgeTypes || []).forEach(function (t, i) { var p = M.ring[i], q = M.ring[(i + 1) % M.ring.length];
      g.add(new T.Line(new T.BufferGeometry().setFromPoints([v3(p, 0.05), v3(q, 0.05)]), new T.LineBasicMaterial({ color: COL[t] || 0x111111 }))); });
    var handles = new T.Group();
    M.ring.forEach(function (p, i) { var h = new T.Mesh(new T.SphereGeometry(0.9, 12, 8), new T.MeshBasicMaterial({ color: 0x22d3ee })); h.position.copy(v3(p, 0)); h.userData = { kind: 'vertex', i: i }; handles.add(h); });
    M.lines.forEach(function (l) { if (l.type !== 'ridge' && l.type !== 'hip' && l.type !== 'valley') return;
      [0, 1].forEach(function (e) { var h = new T.Mesh(new T.SphereGeometry(0.8, 12, 8), new T.MeshBasicMaterial({ color: COL[l.type] })); h.position.copy(v3(e ? l.b : l.a, e ? l.zb : l.za)); h.userData = { kind: 'end', i: l.i, end: e }; handles.add(h); }); });
    g.add(handles);
    var pts = null;
    if (cloud) { var pp = [], cc = [], col = new T.Color();
      cloud.pts.forEach(function (p) { pp.push(p[0], p[2], -p[1]); var e = Math.min(1, Math.abs(p[3]) / 3); col.setRGB(e, 1 - e * 0.7, 0.2); cc.push(col.r, col.g, col.b); });
      var pg = new T.BufferGeometry(); pg.setAttribute('position', new T.Float32BufferAttribute(pp, 3)); pg.setAttribute('color', new T.Float32BufferAttribute(cc, 3));
      pts = new T.Points(pg, new T.PointsMaterial({ size: 0.5, vertexColors: true })); g.add(pts); }
    return { group: g, handles: handles, points: pts };
  }

  function close() { if (!S) return; try { S.renderer.setAnimationLoop(null); S.renderer.dispose(); } catch (e) { /* ignore */ } S.box.remove(); S = null; }

  function open() {
    var app = window.RoofApp, st = app && app.state, say = function (m) { var s = document.getElementById('status'); if (s) s.textContent = m; };
    if (!st || !st.ring) { say('Pick a building first.'); return Promise.resolve(null); }
    return loadThree().then(function () { return build(app); }).catch(function (e) { say('3-D view unavailable: ' + e.message); return null; });
  }

  function build(app) {
    close();
    var T = THREE, st = app.state, r = window.RoofReport.buildResult(app);
    var M = buildModel(app, r); M.edgeTypes = (r.edges || []).map(function (e) { return e.type; });
    var cloud = lidarCloud(app, M);
    var box = el('div', { id: 'v3d', role: 'dialog', 'aria-label': '3-D roof model view and editor' });
    box.style.cssText = 'position:fixed;inset:0;z-index:5000;background:#0f172a;color:#fff;display:flex;flex-direction:column;font:14px Arial';
    var bar = el('div', { role: 'toolbar', 'aria-label': '3-D editor tools' });
    bar.style.cssText = 'display:flex;flex-wrap:wrap;gap:6px;padding:6px;background:#1e293b;align-items:center';
    var modes = [['orbit', 'Orbit / zoom'], ['vertex', 'Move outline vertex'], ['end', 'Move ridge/hip/valley end'], ['pitch', 'Set facet pitch'], ['type', 'Re-type line']];
    bar.innerHTML = modes.map(function (m) { return '<button type="button" data-v3m="' + m[0] + '" aria-pressed="' + (m[0] === 'orbit') + '" style="min-height:44px">' + m[1] + '</button>'; }).join('') +
      '<label style="min-height:44px;display:flex;align-items:center;gap:4px"><input type="checkbox" id="v3pts"' + (cloud ? ' checked' : ' disabled') + '> lidar points</label>' +
      '<button type="button" id="v3apply" style="min-height:44px;font-weight:bold">Apply edits</button><button type="button" id="v3undo" style="min-height:44px">Discard</button>' +
      '<button type="button" id="v3close" style="min-height:44px">Close 3-D</button>';
    var info = el('div', { id: 'v3info', 'aria-live': 'polite' }); info.style.cssText = 'padding:4px 8px;font-size:13px;background:#0b1220';
    var panel = el('div', { id: 'v3panel' }); panel.style.cssText = 'position:absolute;right:8px;top:110px;background:#1e293b;padding:8px;border-radius:6px;display:none;z-index:2';
    var view = el('div', { id: 'v3view' }); view.style.cssText = 'flex:1;position:relative;touch-action:none';
    box.appendChild(bar); box.appendChild(info); box.appendChild(view); view.appendChild(panel); document.body.appendChild(box);
    var W = view.clientWidth || window.innerWidth, H = view.clientHeight || (window.innerHeight - 120);
    var renderer = new T.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true }); renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); renderer.setSize(W, H); view.appendChild(renderer.domElement);
    var sc = new T.Scene(); sc.background = new T.Color(0x0f172a);
    sc.add(new T.AmbientLight(0xffffff, 0.75)); var dl = new T.DirectionalLight(0xffffff, 0.9); dl.position.set(-40, 80, 30); sc.add(dl);
    var ext = 10; M.ring.forEach(function (p) { ext = Math.max(ext, Math.abs(p[0]), Math.abs(p[1])); });
    var cam = new T.PerspectiveCamera(45, W / H, 0.5, ext * 20); cam.position.set(ext * 1.2, ext * 1.4, ext * 1.6);
    var ctl = new T.OrbitControls(cam, renderer.domElement); ctl.target.set(0, 4, 0); ctl.update();
    var grid = new T.GridHelper(Math.ceil(ext * 3 / 10) * 10, Math.ceil(ext * 3 / 10), 0x334155, 0x1e293b); grid.position.y = -9; sc.add(grid);
    var built = scene(M, cloud); sc.add(built.group);
    S = { box: box, renderer: renderer, scene: sc, cam: cam, ctl: ctl, M: M, built: built, r: r, mode: 'orbit', pending: { vertices: {}, ends: {}, types: {}, pitch: {} } };
    function upd() {
      var p = S.pending, n = Object.keys(p.vertices).length + Object.keys(p.ends).length + Object.keys(p.types).length + Object.keys(p.pitch).length;
      info.textContent = 'Roof ' + r.roof_area_sqft + ' sq ft (' + r.squares + ' sq) · eave ' + r.eave_lf + ' · rake ' + r.rake_lf + ' (sloped) · ridge ' + ((r.lines && r.lines.ridge_lf) || 0) +
        ' · hip ' + ((r.lines && r.lines.hip_lf) || 0) + ' · valley ' + ((r.lines && r.lines.valley_lf) || 0) + ' LF · pitch ' + r.pitch + (cloud ? ' · lidar points offset ' + cloud.offset_ft.toFixed(1) + ' ft' : '') +
        ' · free data only (roofprint, lidar, facets model)' + (n ? ' · ' + n + ' pending edit(s) — Apply to update the measurements' : '');
    }
    upd();
    Array.prototype.forEach.call(bar.querySelectorAll('[data-v3m]'), function (b) { b.onclick = function () { S.mode = b.dataset.v3m; panel.style.display = 'none';
      Array.prototype.forEach.call(bar.querySelectorAll('[data-v3m]'), function (x) { x.setAttribute('aria-pressed', String(x === b)); }); }; });
    document.getElementById('v3close').onclick = close;
    document.getElementById('v3undo').onclick = function () { build(app); };
    document.getElementById('v3pts').onchange = function (e) { if (built.points) built.points.visible = e.target.checked; };
    document.getElementById('v3apply').onclick = function () { apply(S.pending); };
    // picking / dragging
    var ray = new T.Raycaster(), ndc = new T.Vector2(), drag = null;
    function pick(ev, objs) { var rc = renderer.domElement.getBoundingClientRect(); ndc.set(((ev.clientX - rc.left) / rc.width) * 2 - 1, -((ev.clientY - rc.top) / rc.height) * 2 + 1);
      ray.setFromCamera(ndc, cam); return ray.intersectObjects(objs, false)[0]; }
    renderer.domElement.addEventListener('pointerdown', function (ev) {
      if (S.mode === 'orbit') return;
      if (S.mode === 'vertex' || S.mode === 'end') {
        var hit = pick(ev, built.handles.children.filter(function (h) { return h.userData.kind === (S.mode === 'vertex' ? 'vertex' : 'end'); }));
        if (!hit) return; ctl.enabled = false; drag = { h: hit.object, plane: new T.Plane(new T.Vector3(0, 1, 0), -hit.object.position.y) }; renderer.domElement.setPointerCapture(ev.pointerId); return;
      }
      var objs = built.group.children.filter(function (o) { return o.userData && o.userData.kind === (S.mode === 'pitch' ? 'facet' : 'line'); });
      var h2 = pick(ev, objs); if (!h2) return;
      if (S.mode === 'pitch') { var id = h2.object.userData.id, fx = M.facets.filter(function (f) { return f.id === id; })[0];
        panel.innerHTML = '<label>Pitch of ' + id + ' <select id="v3ps">' + window.RoofCalc.PITCHES.map(function (p) { return '<option' + (p === (S.pending.pitch[id] || fx.pitch) ? ' selected' : '') + '>' + p + '</option>'; }).join('') + '</select></label> <button type="button" id="v3pok">Set</button>';
        panel.style.display = 'block'; document.getElementById('v3pok').onclick = function () { S.pending.pitch[id] = document.getElementById('v3ps').value; h2.object.material.color.set(0xfbbf24); panel.style.display = 'none'; upd(); }; }
      else { var i = h2.object.userData.i, sg = r.line_segments[i];
        panel.innerHTML = '<label>Line L' + i + ' (' + sg.type + ', ' + (+sg.length_ft).toFixed(1) + ' ft) <select id="v3ts">' + window.RoofTags.ALL_TYPES.concat(['none']).map(function (t) { return '<option value="' + t + '"' + (t === (S.pending.types[i] || sg.type) ? ' selected' : '') + '>' + (t === 'none' ? 'delete' : t) + '</option>'; }).join('') + '</select></label> <button type="button" id="v3tok">Set</button>';
        panel.style.display = 'block'; document.getElementById('v3tok').onclick = function () { S.pending.types[i] = document.getElementById('v3ts').value; panel.style.display = 'none'; upd(); }; }
    });
    renderer.domElement.addEventListener('pointermove', function (ev) {
      if (!drag) return; var rc = renderer.domElement.getBoundingClientRect(); ndc.set(((ev.clientX - rc.left) / rc.width) * 2 - 1, -((ev.clientY - rc.top) / rc.height) * 2 + 1);
      ray.setFromCamera(ndc, cam); var p = new T.Vector3(); if (ray.ray.intersectPlane(drag.plane, p)) drag.h.position.set(p.x, drag.h.position.y, p.z);
    });
    renderer.domElement.addEventListener('pointerup', function () {
      if (!drag) return; var u = drag.h.userData, ll = M.F.b([drag.h.position.x, -drag.h.position.z]);
      if (u.kind === 'vertex') S.pending.vertices[u.i] = ll;
      else { var e = S.pending.ends[u.i] || r.line_segments[u.i].coords_lonlat.slice(); e[u.end] = ll; S.pending.ends[u.i] = e; }
      drag = null; ctl.enabled = true; upd();
    });
    renderer.setAnimationLoop(function () { ctl.update(); renderer.render(sc, cam); });
    window.addEventListener('resize', function () { if (!S) return; var w = view.clientWidth, h = view.clientHeight; renderer.setSize(w, h); cam.aspect = w / h; cam.updateProjectionMatrix(); });
    return info3();
  }

  /** edits: {vertices: {i: [lon,lat]}, ends: {i: [[lon,lat],[lon,lat]]}, types: {i: type|'none'}, pitch: {facetId: 'x/12'}} */
  function apply(edits) {
    var app = window.RoofApp, st = app.state, T = window.RoofTags, RC = window.RoofCalc; edits = edits || {};
    var tg = st.tags = st.tags || T.emptyTags(); tg.lineMoves = tg.lineMoves || {}; tg.facetPitch = tg.facetPitch || {};
    var log = (st.edits3d = st.edits3d || { n: 0, list: [] }), lab = '3-D editor';
    var useR = (document.getElementById('useRidge') || {}).checked !== false;
    var key = T.facetsKey(st.result, st.lidar, useR);
    if (tg.linesKey !== key) { tg.lines = {}; tg.lineMoves = {}; tg.linesKey = key; }
    Object.keys(edits.ends || {}).forEach(function (i) { tg.lineMoves[i] = { coords_lonlat: edits.ends[i], layer: lab }; log.list.push('moved L' + i); });
    Object.keys(edits.types || {}).forEach(function (i) { tg.lines[i] = { type: edits.types[i], layer: lab }; log.list.push('L' + i + ' → ' + edits.types[i]); });
    Object.keys(edits.pitch || {}).forEach(function (id) { tg.facetPitch[id] = edits.pitch[id]; log.list.push(id + ' pitch ' + edits.pitch[id]); });
    var vs = Object.keys(edits.vertices || {});
    if (vs.length) {
      var ring = st.ring.slice(); vs.forEach(function (i) { ring[+i] = edits.vertices[i]; log.list.push('vertex ' + i + ' moved'); });
      var ov = st.overrides; st.ring = RC.normalizeRing(ring, 0); st.overrides = ov; st.source = (st.source || '') + (/3-D edit/.test(st.source || '') ? '' : ' + 3-D edit');
      // the facets model is rebuilt from the new outline: line moves / types and facet pitches keyed to the old model are dropped
      tg.lineMoves = {}; tg.lines = {}; tg.facetPitch = {}; tg.linesKey = null;
    }
    log.n = log.list.length; log.summary = log.list.slice(-12).join('; ');
    if (app.render) app.render();
    if (S) return build(app);
    return info3();
  }
  function info3() {
    if (!S) return null; var r = S.r;
    return { facets: S.M.facets.length, lines: S.M.lines.length, handles: S.built.handles.children.length, lidar_points: S.built.points ? S.built.points.geometry.attributes.position.count : 0,
      roof_area_sqft: r.roof_area_sqft, squares: r.squares, ridge_lf: r.lines && r.lines.ridge_lf, max_z_ft: Math.max.apply(null, S.M.facets.map(function (f) { return Math.max.apply(null, f.poly.map(f.h)); })) };
  }
  window.Roof3D = { open: open, close: close, apply: apply, info: info3 };
})();
