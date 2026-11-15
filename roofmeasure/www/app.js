/* RoofMeasure standalone page (MapLibre GL). Uses window.RoofCalc, RoofSources, RoofOverture. */
(function () {
  'use strict';
  var RC = window.RoofCalc, S = window.RoofSources;
  var $ = function (id) { return document.getElementById(id); };
  var MG = 'https://tiles.arcgis.com/tiles/hGdibHYSPO59RG1h/arcgis/rest/services/';
  // free: measurement-grade, public/open data (snap + report aerial allowed). ref: visual reference only (ToS: no derived content).
  var BASEMAPS = {
    massgis: { free: true, label: 'MassGIS 2025 orthos', tiles: [MG + 'Massachusetts_Aerial_Imagery_2025/MapServer/tile/{z}/{y}/{x}'],
      maxzoom: 20, attribution: 'Imagery: MassGIS / EOTSS, Spring 2025 15 cm orthos' },
    massgis2023: { free: true, label: 'MassGIS 2023 orthos', tiles: [MG + 'orthos2023/MapServer/tile/{z}/{y}/{x}'], maxzoom: 20, attribution: 'Imagery: MassGIS / EOTSS 2023 orthos' },
    massgis2021: { free: true, label: 'MassGIS 2021 orthos', tiles: [MG + 'orthos2021/MapServer/tile/{z}/{y}/{x}'], maxzoom: 20, attribution: 'Imagery: MassGIS / EOTSS 2021 orthos' },
    naip: { free: true, label: 'USDA NAIP', tiles: ['https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=jpgpng&f=image'],
      maxzoom: 19, attribution: 'USDA NAIP via USGS The National Map, public domain' },
    usgs: { free: true, label: 'USGS Imagery Only', tiles: ['https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}'],
      maxzoom: 16, attribution: 'USGS The National Map: Imagery (NAIP-based), public domain' },
    esri: { ref: true, label: 'Esri World Imagery (reference)', tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
      maxzoom: 19, attribution: 'Imagery © Esri, Maxar, Earthstar Geographics, and the GIS User Community — visual reference only' },
    google: { ref: true, key: 'google', label: 'Google satellite (reference)', maxzoom: 22, attribution: 'Google — visual reference only' },
    azure: { ref: true, key: 'azure', label: 'Microsoft Azure Maps imagery (reference)', maxzoom: 19, attribution: '© Microsoft Azure Maps — visual reference only' },
    bing: { ref: true, key: 'bing', label: 'Bing Maps aerial (reference)', maxzoom: 19, attribution: '© Microsoft Bing Maps — visual reference only' }
  };
  var KEYS_LS = 'roofmeasure.refkeys.v1';
  function loadKeys() { try { return JSON.parse(localStorage.getItem(KEYS_LS) || '{}') || {}; } catch (e) { return {}; } }
  var state = { pitchSource: 'manual', pitchConfidence: null, lidar: null, sourceType: null, ring: null, overrides: {}, source: null, address: null, click: null, mode: 'pick', draw: [], result: null, basemap: 'massgis', tags: window.RoofTags ? window.RoofTags.emptyTags() : null, tagTool: '', facetsLive: null, facetsKey: null, refLayersViewed: {} };
  var errors = [];
  window.addEventListener('error', function (e) { errors.push(String(e.message)); });

  function status(msg, append) { $('status').textContent = append ? $('status').textContent + '\n' + msg : msg; }
  function numOrNull(id) { var v = $(id).value; return v === '' || !isFinite(+v) ? null : +v; }
  function opts() {
    var o = { pitch: $('pitch').value, roofType: $('roofType').value, overhangFt: numOrNull('overhang'),
      gutterEndExtFt: numOrNull('gext'), ftPerDownspout: +$('ftds').value || 35, wastePct: +$('waste').value || 0,
      sourceType: state.sourceType, pitchSource: state.pitchSource, pitchConfidence: state.pitchConfidence };
    if ($('useRidge').checked && state.lidar && state.lidar.ridges && state.lidar.ridges.length) o.ridgeBearingsDeg = state.lidar.ridges;
    else if ($('useRidge').checked && state.lidar && state.lidar.ridge_bearing_deg != null) o.ridgeBearingDeg = state.lidar.ridge_bearing_deg;
    return o;
  }
  RC.PITCHES.forEach(function (p) { var o = document.createElement('option'); o.value = o.textContent = p; if (p === '6/12') o.selected = true; $('pitch').appendChild(o); });

  var params = new URLSearchParams(location.search);
  var center = [parseFloat(params.get('lon')) || -70.912947, parseFloat(params.get('lat')) || 42.213605];
  if (params.get('basemap') && BASEMAPS[params.get('basemap')]) { state.basemap = params.get('basemap'); $('basemap').value = state.basemap; }

  function rasterSource(k) { var b = BASEMAPS[k]; return { type: 'raster', tiles: b.tiles, tileSize: 256, maxzoom: b.maxzoom, attribution: b.attribution }; }
  if (!BASEMAPS[state.basemap].tiles) { state.basemap = 'massgis'; $('basemap').value = 'massgis'; }
  var map = new maplibregl.Map({
    container: 'map', center: center, zoom: 19, maxZoom: 22, preserveDrawingBuffer: true,
    style: { version: 8, sources: { ortho: rasterSource(state.basemap), fallback: rasterSource('usgs') },
      layers: [{ id: 'fallback', type: 'raster', source: 'fallback' }, { id: 'ortho', type: 'raster', source: 'ortho' }] }
  });
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }));
  map.addControl(new maplibregl.ScaleControl({ unit: 'imperial' }));
  window.RoofApp = { map: map, state: state, errors: errors, BASEMAPS: BASEMAPS };

  // ---- reference layers that need the user's own key (display only; never snapped, traced, measured or stored)
  var refAttr = { google: null, azure: null };
  function resolveKeyed(k) {
    var b = BASEMAPS[k], keys = loadKeys(), key = keys[b.key];
    if (!key) return Promise.reject(new Error(b.label + ' needs your own API key (Reference imagery keys).'));
    if (k === 'google') {
      return fetch('https://tile.googleapis.com/v1/createSession?key=' + encodeURIComponent(key), { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mapType: 'satellite', language: 'en-US', region: 'US' }) }).then(function (r) {
        if (!r.ok) throw new Error('Google createSession HTTP ' + r.status); return r.json(); }).then(function (j) {
        b.session = j.session; b.tiles = ['https://tile.googleapis.com/v1/2dtiles/{z}/{x}/{y}?session=' + encodeURIComponent(j.session) + '&key=' + encodeURIComponent(key)];
        b.tileKey = key; return b; });
    }
    if (k === 'azure') {
      b.tiles = ['https://atlas.microsoft.com/map/tile?api-version=2024-04-01&tilesetId=microsoft.imagery&zoom={z}&x={x}&y={y}&tileSize=256&subscription-key=' + encodeURIComponent(key)];
      b.tileKey = key; return Promise.resolve(b);
    }
    if (k === 'bing') {
      return fetch('https://dev.virtualearth.net/REST/v1/Imagery/Metadata/Aerial?uriScheme=https&include=ImageryProviders&key=' + encodeURIComponent(key)).then(function (r) {
        if (!r.ok) throw new Error('Bing metadata HTTP ' + r.status); return r.json(); }).then(function (j) {
        var res = j.resourceSets[0].resources[0];
        b.tiles = (res.imageUrlSubdomains || ['t0']).map(function (sd) { return res.imageUrl.replace('{subdomain}', sd).replace('{culture}', 'en-US'); });
        b.maxzoom = res.zoomMax || 19; b.attribution = (j.copyright || '© Microsoft') + ' — Bing Maps, visual reference only'; return b; });
    }
    return Promise.reject(new Error('unknown layer ' + k));
  }
  function updateRefAttribution() {
    var k = state.basemap, b = BASEMAPS[k], keys = loadKeys();
    if (!b || !b.ref || !map.getSource('ortho')) return;
    var bb = map.getBounds(), z = Math.round(map.getZoom());
    var url = null;
    if (k === 'google' && b.session) url = 'https://tile.googleapis.com/tile/v1/viewport?session=' + encodeURIComponent(b.session) + '&key=' + encodeURIComponent(keys.google || '') +
      '&zoom=' + z + '&north=' + bb.getNorth() + '&south=' + bb.getSouth() + '&east=' + bb.getEast() + '&west=' + bb.getWest();
    if (k === 'azure') url = 'https://atlas.microsoft.com/map/attribution?api-version=2024-04-01&tilesetId=microsoft.imagery&zoom=' + z + '&bounds=' +
      [bb.getWest(), bb.getSouth(), bb.getEast(), bb.getNorth()].join(',') + '&subscription-key=' + encodeURIComponent(keys.azure || '');
    if (!url) return;
    fetch(url).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (!j) return;
      var txt = k === 'google' ? 'Google' + (j.copyright ? ' · ' + j.copyright : '') : (j.copyrights || []).join(', ') || '© Microsoft';
      refAttr[k] = txt; $('refInfo').textContent = txt + ' — visual reference only';
    }).catch(function () {});
  }
  map.on('moveend', updateRefAttribution);
  function applyRefUi(k) {
    var b = BASEMAPS[k];
    $('refBanner').hidden = !b.ref; $('googleLogo').hidden = k !== 'google';
    $('refInfo').textContent = b.ref ? (b.attribution || b.label) : '';
    $('snapBtn').disabled = !b.free; $('snapBtn').title = b.free ? 'Nudge edges to strong roof lines in the ortho (free imagery only)' : 'Snap is disabled on visual-reference layers (their terms forbid derived content)';
    if (b.ref) state.refLayersViewed[b.label] = 1;
  }
  function setBasemap(k) {
    var b = BASEMAPS[k]; if (!b) return Promise.resolve();
    var ready = b.key ? resolveKeyed(k) : Promise.resolve(b);
    return ready.then(function () {
      state.basemap = k;
      if (map.getLayer('ortho')) map.removeLayer('ortho'); if (map.getSource('ortho')) map.removeSource('ortho');
      map.addSource('ortho', rasterSource(k));
      map.addLayer({ id: 'ortho', type: 'raster', source: 'ortho', paint: { 'raster-opacity': (+$('orthoOpacity').value || 0) / 100 } }, map.getLayer('fp-fill') ? 'fp-fill' : undefined);
      applyRefUi(k); updateRefAttribution();
      if (state.overlay && b.free) { var ov = state.overlay; setTimeout(function () { setOverlay(ov); }, 0); } else if (state.overlay && !b.free) { state.overlay = null; $('ovLayer').value = ''; if (map.getLayer('refover')) { map.removeLayer('refover'); map.removeSource('refover'); } }
      status('Imagery: ' + b.label + (b.ref ? ' — VISUAL REFERENCE ONLY (not used for measurement, tracing or snapping).' : ' (free; usable for snap and report).'));
    }).catch(function (e) { status(e.message); $('basemap').value = state.basemap; });
  }
  window.RoofApp.setBasemap = setBasemap;
  // ---- swipe compare: reference view (left of divider) over the free traceable main map. map2 never receives input.
  var map2 = null;
  function cmpLayout() {
    var pos = +$('cmpPos').value, w = map.getContainer().clientWidth, x = Math.round(w * pos / 100);
    $('map2').style.clipPath = 'inset(0 ' + (w - x) + 'px 0 0)'; $('cmpDivider').style.left = x + 'px';
  }
  function cmpSync() { if (map2) map2.jumpTo({ center: map.getCenter(), zoom: map.getZoom(), bearing: map.getBearing(), pitch: map.getPitch() }); }
  function setCompare(on) {
    var k = $('cmpLayer').value, b = BASEMAPS[k];
    if (!on) { $('map2').hidden = $('cmpDivider').hidden = true; if (map2) { map2.remove(); map2 = null; } $('cmpOn').checked = false; return Promise.resolve(); }
    var free = BASEMAPS[state.basemap].free ? Promise.resolve() : ($('basemap').value = 'massgis', setBasemap('massgis'));
    return free.then(function () { return b.key ? resolveKeyed(k) : b; }).then(function () {
      if (map2) { map2.remove(); map2 = null; }
      $('map2').hidden = $('cmpDivider').hidden = false;
      map2 = new maplibregl.Map({ container: 'map2', interactive: false, attributionControl: { compact: false, customAttribution: b.attribution },
        center: map.getCenter(), zoom: map.getZoom(), style: { version: 8, sources: { ref: rasterSource(k) }, layers: [{ id: 'ref', type: 'raster', source: 'ref' }] } });
      window.RoofApp.map2 = map2;
      if (b.ref) state.refLayersViewed[b.label] = 1;
      $('googleLogo').hidden = k !== 'google';
      cmpLayout(); cmpSync();
      status('Compare: ' + b.label + ' (left of the yellow divider) vs ' + BASEMAPS[state.basemap].label + ' (right; the only layer used for tracing/snapping).');
    }).catch(function (e) { status(e.message); setCompare(false); });
  }
  window.RoofApp.setCompare = setCompare;
  map.on('move', cmpSync); window.addEventListener('resize', function () { if (map2) { map2.resize(); cmpLayout(); } });
  $('cmpOn').onchange = function () { setCompare(this.checked); };
  $('cmpLayer').onchange = function () { if ($('cmpOn').checked) setCompare(true); };
  $('cmpPos').addEventListener('input', function () { if (map2) cmpLayout(); });
  // ---- reference overlay (Google/Bing/Azure/Esri) over or under the free layer, adjustable opacity. Display only.
  state.overlay = null;
  function setOverlay(k) {
    if (map.getLayer('refover')) map.removeLayer('refover'); if (map.getSource('refover')) map.removeSource('refover');
    state.overlay = null; $('refBanner').hidden = !BASEMAPS[state.basemap].ref; $('googleLogo').hidden = state.basemap !== 'google';
    if (!k) return Promise.resolve();
    var b = BASEMAPS[k];
    var free = BASEMAPS[state.basemap].free ? Promise.resolve() : ($('basemap').value = 'massgis', setBasemap('massgis'));
    return free.then(function () { return b.key ? resolveKeyed(k) : b; }).then(function () {
      map.addSource('refover', rasterSource(k));
      var under = $('ovPos').value === 'under';
      // 'under': reference below a semi-transparent free layer; 'over': reference above the free layer. Edges always on top.
      map.addLayer({ id: 'refover', type: 'raster', source: 'refover', paint: { 'raster-opacity': under ? 1 : (+$('ovOpacity').value || 0) / 100 } }, under ? 'ortho' : (map.getLayer('fp-fill') ? 'fp-fill' : undefined));
      if (under) map.setPaintProperty('ortho', 'raster-opacity', 1 - (+$('ovOpacity').value || 0) / 100);
      else map.setPaintProperty('ortho', 'raster-opacity', (+$('orthoOpacity').value || 0) / 100);
      state.overlay = k; state.refLayersViewed[b.label] = 1;
      $('refBanner').hidden = false; $('googleLogo').hidden = k !== 'google';
      $('refInfo').textContent = (b.attribution || b.label);
      if (state.mode === 'draw') setMode('pick');
      status('Overlay: ' + b.label + ' ' + (under ? 'under' : 'over') + ' ' + BASEMAPS[state.basemap].label + ' — VISUAL REFERENCE ONLY. Detected edges stay on top; ' +
        'outline drawing/dragging is paused while an overlay is shown (tag and confirm still work).');
    }).catch(function (e) { status(e.message); $('ovLayer').value = ''; });
  }
  window.RoofApp.setOverlay = setOverlay;
  $('ovLayer').onchange = function () { setOverlay(this.value); };
  $('ovPos').onchange = function () { if (state.overlay) setOverlay(state.overlay); };
  $('ovOpacity').addEventListener('input', function () {
    if (!state.overlay) return; var v = (+this.value || 0) / 100;
    if ($('ovPos').value === 'under') map.setPaintProperty('ortho', 'raster-opacity', 1 - v); else map.setPaintProperty('refover', 'raster-opacity', v);
  });
  function traceLocked() { return !BASEMAPS[state.basemap].free || !!state.overlay; }
  // ---- manual (user-supplied) measurements
  state.manualMeas = [];
  function renderMM() {
    $('mmList').innerHTML = state.manualMeas.map(function (m, i) {
      return '<div>' + window.RoofTags.esc(m.label) + ': <b>' + m.value + ' ' + window.RoofTags.esc(m.unit) + '</b> — ' + window.RoofTags.esc(m.source) +
        ' <button data-mm="' + i + '" style="min-height:0;padding:0 6px">×</button></div>'; }).join('');
    Array.prototype.forEach.call($('mmList').querySelectorAll('button[data-mm]'), function (b) { b.onclick = function () { state.manualMeas.splice(+b.dataset.mm, 1); renderMM(); }; });
  }
  $('mmAdd').onclick = function () {
    var v = $('mmValue').value, lab = $('mmLabel').value.trim();
    if (v === '' || !isFinite(+v)) { status('Enter a numeric value for the manual measurement.'); return; }
    state.manualMeas.push({ label: lab || 'measurement ' + (state.manualMeas.length + 1), value: +v, unit: $('mmUnit').value, source: $('mmSource').value,
      entered_at: new Date().toISOString().replace(/\.\d+Z$/, 'Z') });
    $('mmValue').value = ''; $('mmLabel').value = ''; renderMM();
  };
  window.RoofApp.renderMM = renderMM;
  $('orthoOpacity').addEventListener('input', function () { if (map.getLayer('ortho')) map.setPaintProperty('ortho', 'raster-opacity', (+this.value || 0) / 100); });
  (function initKeys() {
    var k = loadKeys(); $('keyGoogle').value = k.google || ''; $('keyAzure').value = k.azure || ''; $('keyBing').value = k.bing || '';
    $('keysSave').onclick = function () {
      var v = { google: $('keyGoogle').value.trim(), azure: $('keyAzure').value.trim(), bing: $('keyBing').value.trim() };
      try { localStorage.setItem(KEYS_LS, JSON.stringify(v)); status('Reference imagery keys saved on this device only.'); } catch (e) { status('Could not save keys: ' + e.message); }
    };
    $('keysClear').onclick = function () { try { localStorage.removeItem(KEYS_LS); } catch (e) {} $('keyGoogle').value = $('keyAzure').value = $('keyBing').value = ''; status('Keys cleared.');
      if (BASEMAPS[state.basemap].key) { $('basemap').value = 'massgis'; setBasemap('massgis'); } };
  })();
  $('basemap').onchange = function () { setBasemap(this.value); };
  map.on('load', function () { applyRefUi(state.basemap); });

  var labelMarkers = [];
  function emptyFC() { return { type: 'FeatureCollection', features: [] }; }
  map.on('load', function () {
    map.addSource('fp', { type: 'geojson', data: emptyFC() });
    map.addSource('edges', { type: 'geojson', data: emptyFC() });
    map.addSource('verts', { type: 'geojson', data: emptyFC() });
    map.addSource('drawing', { type: 'geojson', data: emptyFC() });
    map.addSource('facets', { type: 'geojson', data: emptyFC() });
    map.addSource('lines', { type: 'geojson', data: emptyFC() });
    map.addLayer({ id: 'fp-fill', type: 'fill', source: 'fp', paint: { 'fill-color': '#facc15', 'fill-opacity': 0.12 } });
    map.addLayer({ id: 'facets-fill', type: 'fill', source: 'facets', paint: { 'fill-opacity': ['case', ['has', 'tag'], 0.35, 0],
      'fill-color': ['match', ['get', 'tag'], 'deck', '#a16207', 'flat', '#64748b', 'low_slope', '#0891b2', 'steep', '#16a34a', '#000000'] } });
    map.addLayer({ id: 'facets-line', type: 'line', source: 'facets', paint: { 'line-color': '#ffffff', 'line-width': 0.6, 'line-opacity': 0.5 } });
    map.addLayer({ id: 'lines', type: 'line', source: 'lines', paint: { 'line-width': ['case', ['get', 'user'], 5, 4],
      'line-color': ['match', ['get', 'type'], 'ridge', '#dc2626', 'hip', '#9333ea', 'valley', '#0d9488', 'rake', '#ea580c', 'wall_flashing', '#64748b', '#ffffff'] } });
    map.addLayer({ id: 'lines-case', type: 'line', source: 'lines', paint: { 'line-width': 7, 'line-color': '#000000', 'line-opacity': 0.8 } });
    map.addLayer({ id: 'edges-case', type: 'line', source: 'edges', paint: { 'line-width': 8, 'line-color': '#000000', 'line-opacity': 0.8 } });
    map.addLayer({ id: 'edges-hit', type: 'line', source: 'edges', paint: { 'line-width': 16, 'line-opacity': 0 } });
    map.addLayer({ id: 'edges', type: 'line', source: 'edges', paint: { 'line-width': 4,
      'line-color': ['match', ['get', 'type'], 'eave', '#2563eb', '#ea580c'] } });
    // manual overrides: white dashes on top
    map.addLayer({ id: 'edges-manual', type: 'line', source: 'edges', filter: ['==', ['get', 'auto'], false],
      paint: { 'line-width': 2, 'line-color': '#ffffff', 'line-dasharray': [2, 2] } });
    map.addLayer({ id: 'edges-tag', type: 'line', source: 'edges', filter: ['==', ['get', 'tagged'], true],
      paint: { 'line-width': 3, 'line-color': '#facc15', 'line-offset': 4, 'line-dasharray': [1, 1] } });
    map.addLayer({ id: 'verts', type: 'circle', source: 'verts', paint: { 'circle-radius': 5, 'circle-color': '#fff', 'circle-stroke-color': '#111', 'circle-stroke-width': 1.5 } });
    map.addLayer({ id: 'drawing', type: 'line', source: 'drawing', paint: { 'line-color': '#22c55e', 'line-width': 2 } });
    window.RoofApp.ready = true;
    if (params.get('addr')) { $('addr').value = params.get('addr'); findAddress(); }
    else if (params.get('lat') && params.get('autopick') !== '0') pickAt(center);
  });

  // ------------------------------------------------------------ rendering
  function render() {
    labelMarkers.forEach(function (m) { m.remove(); }); labelMarkers = [];
    if (!state.ring) { ['fp', 'edges', 'verts'].forEach(function (s) { map.getSource(s).setData(emptyFC()); }); return; }
    var r;
    try { r = RC.computeRoof(Object.assign(opts(), { ring: state.ring, overrides: state.overrides, source: state.source, address: state.address,
      lat: state.click && state.click[1], lon: state.click && state.click[0], simplifyFt: 0 })); }
    catch (e) { status('Geometry error: ' + e.message); return; }
    state.result = r; window.RoofApp.result = r;
    $('ohSrc').textContent = $('overhang').value === '' ? '(auto: ' + r.overhang_ft + ' ft)' : '';
    $('pitchInfo').textContent = 'pitch_source: ' + r.pitch_source + (r.pitch_confidence != null ? ' · confidence ' + r.pitch_confidence : '') +
      (state.lidar && state.lidar.roof_shape_guess ? ' · shape guess ' + state.lidar.roof_shape_guess : '');
    state.ring = RC.extractRing(r.footprint_geojson).slice(0, -1);
    map.getSource('fp').setData(r.footprint_geojson);
    map.getSource('edges').setData({ type: 'FeatureCollection', features: r.edges.map(function (e) {
      var tg = state.tags && state.tags.edges[e.i];
      return { type: 'Feature', properties: { i: e.i, type: e.type, auto: e.auto, tagged: !!(tg && Object.keys(tg).length) }, geometry: { type: 'LineString', coordinates: [e.from, e.to] } };
    }) });
    map.getSource('verts').setData({ type: 'FeatureCollection', features: state.ring.map(function (p, i) {
      return { type: 'Feature', properties: { i: i }, geometry: { type: 'Point', coordinates: p } };
    }) });
    r.edges.forEach(function (e) {
      var tg = state.tags && state.tags.edges[e.i], ab = tg ? Object.keys(tg).map(function (k) { return { step_flashing: 'SF', drip_edge: 'DE', wall_flashing: 'WF', no_gutter: 'NG' }[k] || ''; }).join(' ') : '';
      var el = document.createElement('div'); el.className = 'lbl ' + e.type + (ab ? ' tagged' : '') + (state.tags && state.tags.confirmed['E' + e.i] ? ' ok' : '');
      el.textContent = e.type.toUpperCase() + ' ' + e.length_ft.toFixed(1) + "'" + (ab ? ' ' + ab : '');
      labelMarkers.push(new maplibregl.Marker({ element: el }).setLngLat([(e.from[0] + e.to[0]) / 2, (e.from[1] + e.to[1]) / 2]).addTo(map));
    });
    renderFacets(r);
    $('summary').innerHTML = '<table>' + [
      ['Footprint', r.footprint_area_sqft.toLocaleString() + ' sq ft'], ['Perimeter', r.perimeter_ft + ' ft'],
      ['Pitch factor', r.pitch + ' → ×' + r.pitch_factor], ['Overhang', r.overhang_ft + ' ft <span class="note">(' + r.overhang_source + ')</span>'],
      ['Eave/rake method', '<span class="note">' + r.eave_rake_method + (r.ridge_bearings_deg.length ? ' ' + r.ridge_bearings_deg.join('°, ') + '°' : '') + '</span>'], ['Roof area', r.roof_area_sqft.toLocaleString() + ' sq ft'],
      ['Squares', r.squares + ' (' + r.squares_with_waste + ' w/ ' + r.waste_pct + '%)'], ['Eaves', r.eave_lf + ' LF'],
      ['Rake (sloped, drip-edge length)', r.rake_sloped_lf + ' LF'], ['Gutter', r.gutter_lf + ' LF'], ['Downspouts', r.downspouts],
      ['Source', '<span class="note">' + (r.source || 'manual') + '</span>']
    ].map(function (x) { return '<tr><td>' + x[0] + '</td><td>' + x[1] + '</td></tr>'; }).join('') + '</table>';
    $('edges').innerHTML = '<table><tr><th>#</th><th>ft</th><th>bearing</th><th>type</th></tr>' + r.edges.map(function (e) {
      return '<tr data-i="' + e.i + '" style="cursor:pointer"><td>' + e.i + '</td><td>' + e.length_ft.toFixed(1) + '</td><td>' + e.bearing_deg.toFixed(0) +
        '°</td><td class="' + e.type + '">' + e.type + (e.auto ? '' : ' ✎') + '</td></tr>';
    }).join('') + '</table>';
    Array.prototype.forEach.call($('edges').querySelectorAll('tr[data-i]'), function (tr) { tr.onclick = function () { toggleEdge(+tr.dataset.i); }; });
  }
  // ------------------------------------------------------------ live facets / interior lines (same inputs as the report)
  function renderFacets(r) {
    var T = window.RoofTags; if (!T || !map.getSource('lines')) return;
    var useR = $('useRidge').checked, key = T.facetsKey(r, state.lidar, useR);
    if (state.tags.linesKey && state.tags.linesKey !== key) { state.tags.lines = {}; Object.keys(state.tags.confirmed).forEach(function (k) { if (k[0] === 'L') delete state.tags.confirmed[k]; }); }
    state.tags.linesKey = key;
    var f = T.liveFacets(r, state.lidar, useR); if (f) T.applyLineTags(f, state.tags, key);
    state.facetsLive = f; state.facetsKey = key; window.RoofApp.facetsLive = f;
    var segs = f && f.line_segments || [];
    map.getSource('lines').setData({ type: 'FeatureCollection', features: segs.map(function (s, i) {
      return s.coords_lonlat ? { type: 'Feature', properties: { i: i, type: s.type, user: !!s.user_tagged }, geometry: { type: 'LineString', coordinates: s.coords_lonlat } } : null; }).filter(Boolean) });
    segs.forEach(function (s2, i) {
      if (!s2.coords_lonlat || window.RoofTags.LINE_TYPES.indexOf(s2.type) < 0 || s2.length_ft < 2) return;
      var c = s2.coords_lonlat, el = document.createElement('div');
      el.className = 'lbl line ' + s2.type + (state.tags.confirmed['L' + i] ? ' ok' : '');
      el.textContent = s2.type.toUpperCase() + ' ' + (+s2.length_ft).toFixed(1) + "'";
      labelMarkers.push(new maplibregl.Marker({ element: el }).setLngLat([(c[0][0] + c[1][0]) / 2, (c[0][1] + c[1][1]) / 2]).addTo(map));
    });
    map.getSource('facets').setData({ type: 'FeatureCollection', features: (f && f.facets || []).map(function (x) {
      var t = state.tags.areas[x.id] || state.tags.areas.ALL, pr = { id: x.id }; if (t) pr.tag = t.tag;
      return x.polygon_lonlat ? { type: 'Feature', properties: pr, geometry: { type: 'Polygon', coordinates: [x.polygon_lonlat] } } : null; }).filter(Boolean) });
  }
  function layerLabel() { var b = BASEMAPS[state.basemap]; return b ? b.label + (b.ref ? ' (visual reference only)' : '') : state.basemap; }
  function nearestLine(p) {
    var f = state.facetsLive, best = null, t = tol(lastPointerType).edge;
    (f && f.line_segments || []).forEach(function (s, i) {
      if (!s.coords_lonlat || window.RoofTags.LINE_TYPES.indexOf(s.type) < 0) return;
      var a = map.project(s.coords_lonlat[0]), b = map.project(s.coords_lonlat[1]), d = segDist(p, [a.x, a.y], [b.x, b.y]);
      if (d <= t && (!best || d < best.d)) best = { i: i, d: d };
    });
    return best && best.i;
  }
  /** Apply the active tag tool at screen point p / lnglat ll. Returns true when handled. */
  function applyTag(p, ll) {
    var tool = state.tagTool; if (!tool || !state.result) return false;
    var kind = tool.split(':')[0], v = tool.split(':')[1], T = state.tags, lab = layerLabel() + (state.overlay ? ' + overlay ' + BASEMAPS[state.overlay].label + ' (visual reference only)' : '');
    if (kind === 'confirm') {
      var hc = hitTest(p, lastPointerType), lc = hc.edge == null ? nearestLine(p) : null;
      if (hc.edge != null) { var ke = 'E' + hc.edge; if (T.confirmed[ke]) delete T.confirmed[ke]; else T.confirmed[ke] = lab; render(); status('Edge ' + hc.edge + (T.confirmed[ke] ? ' confirmed.' : ' unconfirmed.')); return true; }
      if (lc != null) { var kl = 'L' + lc; if (T.confirmed[kl]) delete T.confirmed[kl]; else T.confirmed[kl] = lab; render(); status('Line ' + lc + (T.confirmed[kl] ? ' confirmed.' : ' unconfirmed.')); return true; }
      status('Tap an edge or interior line to confirm it.'); return true;
    }
    if (kind === 'edge') {
      var h = hitTest(p, lastPointerType); if (h.edge == null) { status('Tap an outline edge to tag it.'); return true; }
      var i = h.edge;
      if (v === 'eave' || v === 'rake') { state.overrides[i] = v; T.layers['edge-type:' + i] = lab; }
      else if (v === 'clear') { delete T.edges[i]; delete state.overrides[i]; }
      else { var e = T.edges[i] = T.edges[i] || {}; if (e[v]) delete e[v]; else e[v] = lab; if (!Object.keys(e).length) delete T.edges[i]; }
      render(); status('Edge ' + i + ': ' + v.replace('_', ' ') + ' (tagged on ' + lab + ').'); return true;
    }
    if (kind === 'line') {
      var li = nearestLine(p); if (li == null) { status('Tap an interior ridge/hip/valley line (red/purple/teal) to re-type it.'); return true; }
      if (v === 'clear') delete T.lines[li]; else T.lines[li] = { type: v, layer: lab };
      render(); status('Interior line ' + li + ' → ' + (v === 'clear' ? 'auto' : v) + '.'); return true;
    }
    if (kind === 'area') {
      var fx = window.RoofTags.facetAt(state.facetsLive, ll), id = fx ? fx.id : (state.facetsLive && state.facetsLive.facets && state.facetsLive.facets.length ? null : 'ALL');
      if (!id) { status('Tap inside a roof facet.'); return true; }
      if (v === 'clear') delete T.areas[id]; else T.areas[id] = { tag: v, layer: lab };
      render(); status((id === 'ALL' ? 'Whole roof' : 'Facet ' + id) + ': ' + (v === 'clear' ? 'untagged' : window.RoofTags.AREA_TAGS[v]) + '.'); return true;
    }
    return false;
  }
  window.RoofApp.applyTag = applyTag;
  $('confirmAllBtn').onclick = function () {
    if (!state.result) return; var lab = layerLabel() + (state.overlay ? ' + overlay ' + BASEMAPS[state.overlay].label + ' (visual reference only)' : '');
    state.result.edges.forEach(function (e) { state.tags.confirmed['E' + e.i] = lab; });
    (state.facetsLive && state.facetsLive.line_segments || []).forEach(function (s2, i) { if (window.RoofTags.LINE_TYPES.indexOf(s2.type) >= 0) state.tags.confirmed['L' + i] = lab; });
    render(); status('All shown edges and lines marked confirmed by you.');
  };
  function applyContrast() { document.body.classList.toggle('hc', $('hiContrast').checked);
    ['edges-case', 'lines-case'].forEach(function (l) { if (map.getLayer(l)) map.setLayoutProperty(l, 'visibility', $('hiContrast').checked ? 'visible' : 'none'); }); }
  $('hiContrast').onchange = applyContrast; map.on('load', applyContrast);
  $('tagTool').onchange = function () { state.tagTool = this.value; status(this.value ? 'Tag tool: ' + this.options[this.selectedIndex].text + ' — tap the map. (Dragging the outline is paused while tagging.)' : 'Tag tool off.'); };
  function toggleEdge(i) {
    if (!state.result) return;
    var cur = state.result.edges[i].type;
    state.overrides[i] = cur === 'eave' ? 'rake' : 'eave';
    render();
  }
  function setRing(ring, source) {
    state.ring = RC.normalizeRing(ring); state.overrides = {}; if (state.tags) { state.tags.edges = {}; state.tags.layers = {}; state.tags.confirmed = {}; } state.source = source || state.source; render();
  }
  window.RoofApp.setRing = setRing;
  ['pitch', 'roofType', 'overhang', 'gext', 'ftds', 'waste', 'useRidge'].forEach(function (id) { $(id).addEventListener('change', function () {
    if (id === 'roofType' || id === 'useRidge') state.overrides = {};
    if (id === 'pitch') { state.pitchSource = 'manual'; state.pitchConfidence = null; }
    render();
  }); });
  $('resetBtn').onclick = function () { state.overrides = {}; render(); };

  // ------------------------------------------------------------ picking
  function pickAt(ll) {
    state.click = ll; status('Looking up roofprint at ' + ll[1].toFixed(6) + ', ' + ll[0].toFixed(6) + ' …');
    return S.fetchFootprint(ll[0], ll[1], { radiusM: 30 }).then(function (res) {
      if (!res.result) { status('No building found.\n' + res.log.join('\n') + '\nUse "Draw manually".'); return; }
      state.source = res.result.source; state.sourceType = res.result.sourceType || null; state.lidar = null; if (window.RoofTags) state.tags = window.RoofTags.emptyTags();
      state.feature = res.result.feature || null; state.fetchedAt = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
      $('overhang').value = ''; $('gext').value = '';
      setRing(RC.extractRing(res.result.feature.geometry), res.result.source);
      if (res.result.warning) $('warn').textContent = '⚠ ' + res.result.warning; else $('warn').textContent = '';
      status(res.log.join('\n') + (res.result.skipped_smaller ? '\n(skipped a smaller nearby structure; click the exact roof if wrong)' : ''));
      var b = new maplibregl.LngLatBounds(); state.ring.forEach(function (p) { b.extend(p); });
      map.fitBounds(b, { padding: 80, maxZoom: 20.5, duration: 0 });
    }).catch(function (e) { status('Lookup failed: ' + e.message); });
  }
  window.RoofApp.pickAt = pickAt;
  function findAddress() {
    var a = $('addr').value.trim(); if (!a) return;
    status('Geocoding "' + a + '" …');
    S.geocode(a).then(function (g) {
      if (!g) { status('Address not found.'); return; }
      state.address = g.label; state.geocoder = g.source; map.jumpTo({ center: [g.lon, g.lat], zoom: 19.5 });
      status('Geocoded via ' + g.source + ': ' + g.label);
      return pickAt([g.lon, g.lat]);
    }).catch(function (e) { status('Geocode failed: ' + e.message); });
  }
  $('go').onclick = findAddress;
  $('addr').addEventListener('keydown', function (e) { if (e.key === 'Enter') findAddress(); });
  function setMode(m) { state.mode = m; $('pickBtn').classList.toggle('on', m === 'pick'); $('drawBtn').classList.toggle('on', m === 'draw');
    state.draw = []; map.getSource('drawing') && map.getSource('drawing').setData(emptyFC()); map.doubleClickZoom[m === 'draw' ? 'disable' : 'enable'](); }
  $('pickBtn').onclick = function () { setMode('pick'); };
  $('drawBtn').onclick = function () { if (traceLocked()) { status('Drawing is disabled on visual-reference layers (no tracing from Google/Microsoft/Esri imagery). Switch to MassGIS/NAIP, or use Swipe compare.'); return; } setMode('draw'); status('Click/tap roof corners; double-click or tap the first corner to finish.'); };

  // ------------------------------------------------------------ map interaction (pointer events: mouse, touch, pen)
  // Hit-testing is done in screen pixels against state.ring, with a bigger tolerance for fingers.
  var TOL = { mouse: { vert: 8, edge: 8 }, touch: { vert: 22, edge: 20 }, pen: { vert: 14, edge: 14 } };
  var lastPointerType = 'mouse', gesture = null, suppressClickUntil = 0;
  var container = map.getCanvasContainer();
  function tol(pt) { return TOL[pt] || TOL.touch; }
  function localPt(e) { var r = container.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; }
  function screenRing() { return (state.ring || []).map(function (p) { var q = map.project(p); return [q.x, q.y]; }); }
  function segDist(p, a, b) {
    var dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy;
    var t = L2 ? Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)) : 0;
    return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy);
  }
  function inside(p, P) {
    var c = false;
    for (var i = 0, j = P.length - 1; i < P.length; j = i++) {
      if (((P[i][1] > p[1]) !== (P[j][1] > p[1])) && (p[0] < (P[j][0] - P[i][0]) * (p[1] - P[i][1]) / (P[j][1] - P[i][1]) + P[i][0])) c = !c;
    }
    return c;
  }
  /** -> {vert:i|null, edge:i|null, inside:bool} at screen point p for pointer type pt */
  function hitTest(p, pt) {
    var P = screenRing(), t = tol(pt), res = { vert: null, edge: null, inside: false };
    if (P.length < 3) return res;
    var bv = Infinity, be = Infinity;
    P.forEach(function (q, i) { var d = Math.hypot(q[0] - p[0], q[1] - p[1]); if (d <= t.vert && d < bv) { bv = d; res.vert = i; } });
    P.forEach(function (q, i) { var d = segDist(p, q, P[(i + 1) % P.length]); if (d <= t.edge && d < be) { be = d; res.edge = i; } });
    res.inside = inside(p, P);
    return res;
  }
  window.RoofApp.hitTest = hitTest;
  function setVerts() {
    map.getSource('verts').setData({ type: 'FeatureCollection', features: state.ring.map(function (p, i) { return { type: 'Feature', properties: { i: i }, geometry: { type: 'Point', coordinates: p } }; }) });
    map.getSource('fp').setData(RC.toGeoJSON(state.ring));
  }
  function endGesture(cancelled) {
    var g = gesture; if (!g) return;
    gesture = null;
    map.dragPan.enable(); if (g.touchZoomWasOn) map.touchZoomRotate.enable();
    try { container.releasePointerCapture(g.id); } catch (e) { /* already released */ }
    if (!g.moved) return;
    suppressClickUntil = Date.now() + 450; // swallow the click the browser may send after a drag
    if (g.kind === 'move') {
      state.aligned = true; if (!/aligned/.test(state.source || '')) state.source = (state.source || '') + ' + aligned to ortho';
      render();
    } else { state.ring = RC.normalizeRing(state.ring, 0); render(); }
    window.RoofApp.lastGesture = { kind: g.kind, pointerType: g.type, cancelled: !!cancelled };
  }
  container.addEventListener('pointerdown', function (e) {
    lastPointerType = e.pointerType || 'mouse';
    if (!e.isPrimary || gesture || state.mode !== 'pick' || !state.ring || state.tagTool || traceLocked()) return;
    if (lastPointerType === 'mouse' && e.button !== 0) return;
    var p = localPt(e), h = hitTest(p, lastPointerType), kind = null;
    if (h.vert != null) kind = 'vert';
    else if (h.inside && !(lastPointerType === 'mouse' && h.edge != null)) kind = 'move';
    if (!kind) return; // empty map (or outside edge zone): let MapLibre pan/zoom as usual
    gesture = { kind: kind, id: e.pointerId, type: lastPointerType, i: h.vert, start: p, startLL: map.unproject(p).toArray(),
      ring: state.ring.map(function (q) { return q.slice(); }), moved: false, touchZoomWasOn: map.touchZoomRotate.isEnabled() };
    map.dragPan.disable(); // pointerdown precedes mousedown/touchstart, so MapLibre never starts a pan for this gesture
    if (lastPointerType !== 'mouse') map.touchZoomRotate.disable();
    try { container.setPointerCapture(e.pointerId); } catch (err) { /* synthetic events */ }
    e.preventDefault(); e.stopPropagation();
  }, { capture: true });
  container.addEventListener('pointermove', function (e) {
    if (!gesture) {
      if (e.pointerType === 'mouse' && state.ring && state.mode === 'pick') {
        var h = hitTest(localPt(e), 'mouse');
        map.getCanvas().style.cursor = h.vert != null ? 'move' : (h.edge != null ? 'pointer' : (h.inside ? 'grab' : ''));
      }
      return;
    }
    if (e.pointerId !== gesture.id) return;
    var p = localPt(e);
    if (!gesture.moved && Math.hypot(p[0] - gesture.start[0], p[1] - gesture.start[1]) < 3) return;
    gesture.moved = true; e.preventDefault(); e.stopPropagation();
    var ll = map.unproject(p).toArray();
    if (gesture.kind === 'move') state.ring = RC.translateRing(gesture.ring, gesture.startLL, ll); // rigid: lengths unchanged
    else state.ring[gesture.i] = ll;
    setVerts();
  }, { capture: true });
  container.addEventListener('pointerup', function (e) { if (gesture && e.pointerId === gesture.id) endGesture(false); }, { capture: true });
  container.addEventListener('pointercancel', function (e) { if (gesture && e.pointerId === gesture.id) endGesture(true); }, { capture: true });
  // Belt and braces: MapLibre's own touch pan must not run while a gesture is active.
  container.addEventListener('touchmove', function (e) { if (gesture) { e.preventDefault(); } }, { capture: true, passive: false });

  map.on('contextmenu', function (e) {
    if (!state.ring || state.ring.length <= 3 || state.mode !== 'pick' || traceLocked()) return;
    var h = hitTest([e.point.x, e.point.y], lastPointerType);
    if (h.vert == null) return;
    e.preventDefault();
    state.ring.splice(h.vert, 1); state.overrides = {}; state.tags.edges = {}; state.tags.confirmed = {}; render();
  });
  function finishDraw(pts) {
    if (pts.length >= 3) { if (window.RoofTags) state.tags = window.RoofTags.emptyTags(); state.click = pts[0]; state.sourceType = null; state.lidar = null; $('overhang').value = ''; $('gext').value = ''; setRing(pts, 'manual trace'); }
    setMode('pick');
  }
  map.on('click', function (e) {
    var ll = [e.lngLat.lng, e.lngLat.lat], p = [e.point.x, e.point.y];
    if (Date.now() < suppressClickUntil) return;
    if (state.mode === 'draw' && traceLocked()) { setMode('pick'); status('Drawing stopped: the main layer is visual reference only.'); return; }
    if (state.mode === 'draw') {
      // touch has no reliable dblclick: tapping the first corner again closes the outline
      if (state.draw.length >= 3) {
        var f = map.project(state.draw[0]);
        if (Math.hypot(f.x - p[0], f.y - p[1]) <= tol(lastPointerType).vert) { finishDraw(state.draw.slice()); return; }
      }
      state.draw.push(ll);
      map.getSource('drawing').setData({ type: 'Feature', geometry: { type: 'LineString', coordinates: state.draw } });
      return;
    }
    if (state.ring && state.tagTool && applyTag(p, ll)) return;
    if (state.ring) {
      var h = hitTest(p, lastPointerType);
      if (h.vert != null) return;
      if (h.edge != null) {
        if ((e.originalEvent.altKey || e.originalEvent.shiftKey) && traceLocked()) { status('Adding vertices is disabled on visual-reference layers.'); return; }
        if (e.originalEvent.altKey || e.originalEvent.shiftKey) { state.ring.splice(h.edge + 1, 0, ll); state.overrides = {}; state.tags.edges = {}; state.tags.confirmed = {}; render(); } // insert vertex
        else toggleEdge(h.edge);
        return;
      }
      if (h.inside) return; // tap inside current footprint = no re-pick
    }
    pickAt(ll);
  });
  map.on('dblclick', function () {
    if (state.mode !== 'draw') return;
    finishDraw(state.draw.slice(0, -1)); // dblclick also fired a click
  });

  // ------------------------------------------------------------ edge snap
  /** Build a tile mosaic around the ring at zoom z into an offscreen canvas; returns {img, project, unproject}. */
  function mosaic(ring, z) {
    var xs = [], ys = [];
    ring.forEach(function (p) { var w = RC.lonLatToWorld(p[0], p[1], z); xs.push(w[0]); ys.push(w[1]); });
    var pad = 48, x0 = Math.floor((Math.min.apply(null, xs) - pad) / 256), x1 = Math.floor((Math.max.apply(null, xs) + pad) / 256);
    var y0 = Math.floor((Math.min.apply(null, ys) - pad) / 256), y1 = Math.floor((Math.max.apply(null, ys) + pad) / 256);
    if ((x1 - x0 + 1) * (y1 - y0 + 1) > 36) return Promise.reject(new Error('footprint too large to snap'));
    var cv = document.createElement('canvas'); cv.width = (x1 - x0 + 1) * 256; cv.height = (y1 - y0 + 1) * 256;
    var ctx = cv.getContext('2d'), tpl = BASEMAPS[state.basemap].tiles[0], jobs = [];
    for (var tx = x0; tx <= x1; tx++) for (var ty = y0; ty <= y1; ty++) (function (tx, ty) {
      jobs.push(new Promise(function (res, rej) {
        var im = new Image(); im.crossOrigin = 'anonymous';
        im.onload = function () { ctx.drawImage(im, (tx - x0) * 256, (ty - y0) * 256); res(); };
        im.onerror = function () { rej(new Error('tile load failed ' + z + '/' + ty + '/' + tx)); };
        im.src = tpl.replace('{z}', z).replace('{x}', tx).replace('{y}', ty);
      }));
    })(tx, ty);
    return Promise.all(jobs).then(function () {
      var img;
      try { img = ctx.getImageData(0, 0, cv.width, cv.height); } // throws SecurityError if canvas tainted (no CORS)
      catch (e) { throw new Error('imagery canvas is tainted (no CORS) — snapping unavailable for this basemap'); }
      return { img: img, project: function (ll) { var w = RC.lonLatToWorld(ll[0], ll[1], z); return [w[0] - x0 * 256, w[1] - y0 * 256]; },
        unproject: function (px) { return RC.worldToLonLat(px[0] + x0 * 256, px[1] + y0 * 256, z); } };
    });
  }
  function snap() {
    if (!state.ring) { status('Pick a building first.'); return Promise.resolve(); }
    if (!BASEMAPS[state.basemap].free) { status('Snap is disabled on visual-reference layers (Google/Microsoft/Esri terms forbid derived content). Switch to MassGIS or NAIP.'); return Promise.resolve(); }
    var z = Math.min(BASEMAPS[state.basemap].maxzoom, 20);
    status('Snapping edges using ' + state.basemap + ' z' + z + ' imagery …');
    return mosaic(state.ring, z).then(function (m) {
      var res = RC.snapRingToEdges(state.ring, m.img, m.project, m.unproject, { maxShiftPx: z >= 20 ? 8 : 4 });
      window.RoofApp.lastSnap = res;
      var mpp = RC.metersPerPixel(state.ring[0][1], z) * RC.M_TO_FT;
      if (res.applied) { var ov = state.overrides; state.ring = RC.normalizeRing(res.ring, 0); state.overrides = ov; state.source = (state.source || '') + ' + edge-snapped'; render(); }
      status('Snap: ' + res.reason + '. Edge shifts (ft): ' + res.shiftsPx.map(function (s) { return (s * mpp).toFixed(1); }).join(', ') +
        '\n(+ = moved outward, − = inward; verify visually, re-pick to undo)');
    }).catch(function (e) { status('Snap unavailable: ' + e.message); });
  }
  window.RoofApp.snap = snap;
  $('snapBtn').onclick = snap;

  // ------------------------------------------------------------ lidar pitch
  var lidarMod = null;
  function autoPitch() {
    if (!state.ring) { status('Pick a building first.'); return Promise.resolve(); }
    status('Estimating pitch from USGS 3DEP lidar (≈1-3 s, ~20 small LAZ requests) …');
    var load = lidarMod ? Promise.resolve(lidarMod) : import(window.ROOF_LIDAR_URL || '../lidar/pitch.js').then(function (m) { lidarMod = m; return m; });
    return load.then(function (m) { return m.estimatePitch(RC.toGeoJSON(state.ring)); }).then(function (r) {
      state.lidar = r; window.RoofApp.lidar = r;
      var p = r.pitch;
      if (!Array.prototype.some.call($('pitch').options, function (o) { return o.value === p; })) {
        var op = document.createElement('option'); op.value = op.textContent = p; $('pitch').appendChild(op);
      }
      $('pitch').value = p; state.pitchSource = r.pitch_source; state.pitchConfidence = r.pitch_confidence;
      if (r.roof_shape_guess === 'hip' || r.roof_shape_guess === 'flat' || r.roof_shape_guess === 'gable') $('roofType').value = r.roof_shape_guess;
      state.overrides = {};
      render();
      status('Lidar: ' + r.pitch + ' (' + (r.pitch_deg != null ? r.pitch_deg.toFixed(1) + '°' : '?') + '), ridge ' + r.ridge_bearing_deg + '° [' + r.ridge_source + '], shape ' +
        r.roof_shape_guess + ', ' + r.pitch_source + ', confidence ' + r.pitch_confidence + ', n=' + r.samples_n +
        (r.ridges && r.ridges.length > 1 ? '\nRidges per wing: ' + r.ridges.map(function (x) { return x.bearing_deg + '°'; }).join(', ') : '') +
        (r.notes && r.notes.length ? '\n' + r.notes.join('\n') : '') + '\nYou can still change pitch/roof type/edges manually.');
    }).catch(function (e) { status('Lidar pitch unavailable: ' + e.message + ' — choose pitch manually.'); });
  }
  window.RoofApp.autoPitch = autoPitch;
  $('lidarBtn').onclick = autoPitch;

  // ------------------------------------------------------------ export
  function download(name, text, type) {
    if (window.RoofBridge && typeof window.RoofBridge.save === 'function') { window.RoofBridge.save(name, text); return; }
    var a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: type })); a.download = name; a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  }
  $('copyBtn').onclick = function () {
    if (!state.result) return; var t = RC.toText(state.result);
    (navigator.clipboard ? navigator.clipboard.writeText(t) : Promise.reject()).then(function () { status('Copied to clipboard.'); }, function () { prompt('Copy:', t); });
  };
  $('csvBtn').onclick = function () { if (state.result) download('roofmeasure.csv', RC.toCSV(state.result), 'text/csv'); };
  $('jsonBtn').onclick = function () { if (state.result) download('roofmeasure.json', JSON.stringify(state.result, null, 2), 'application/json'); };
  // PDF report (web/report.js renders report/build_report.py's exact HTML in Pyodide; Android prints via RoofBridge.printHtml)
  if ($('pdfBtn')) $('pdfBtn').onclick = function () {
    if (!window.RoofReport) { status('Report module not loaded.'); return; }
    window.RoofReport.preview(window.RoofApp, status).catch(function () {});
  };
  window.RoofApp.exportPdf = function () { return window.RoofReport.exportPdf(window.RoofApp, status); };
})();
