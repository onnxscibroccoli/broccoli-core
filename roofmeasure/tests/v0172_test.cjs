// SPDX-License-Identifier: MIT
// Headless test for RoofMeasure 0.1.7.2 (superset of the 0.1.7.1 test) (www/): report from the live result with user tags, preview/edit, reference layers (mocked keys),
// swipe compare, tracing lock, manual measurements. node tests/v0171_test.cjs <outDir>
const PW = process.env.PW || '/usr/local/lib/pnpm/5/.pnpm/playwright-core@1.59.1/node_modules/playwright-core';
const { chromium } = require(PW);
const http = require('http'), fs = require('fs'), path = require('path'), zlib = require('zlib');
const WWW = process.env.WWW || path.join(__dirname, '..', 'www');
const OUT = process.argv[2] || '/tmp/v0172'; fs.mkdirSync(OUT, { recursive: true });
const MIME = { '.html': 'text/html', '.js': 'application/javascript', '.mjs': 'application/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.wasm': 'application/wasm', '.zip': 'application/zip', '.py': 'text/plain', '.md': 'text/plain' };
const srv = http.createServer((q, s) => {
  const p = path.join(WWW, decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
  if (!p.startsWith(WWW) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { s.writeHead(404); return s.end(); }
  s.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(s);
});
function png(r, g, b) { // 256x256 solid PNG (mock reference tile)
  const W = 256, raw = Buffer.alloc((W * 3 + 1) * W); for (let y = 0; y < W; y++) for (let x = 0; x < W; x++) { const o = y * (W * 3 + 1) + 1 + x * 3; raw[o] = r; raw[o + 1] = g; raw[o + 2] = b; }
  const crc = (buf) => { let c, t = []; for (let n = 0; n < 256; n++) { c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } c = 0xffffffff; for (const v of buf) c = t[(c ^ v) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const ch = (ty, d) => { const l = Buffer.alloc(4); l.writeUInt32BE(d.length); const td = Buffer.concat([Buffer.from(ty), d]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([l, td, c]); };
  const ih = Buffer.alloc(13); ih.writeUInt32BE(W, 0); ih.writeUInt32BE(W, 4); ih[8] = 8; ih[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), ch('IHDR', ih), ch('IDAT', zlib.deflateSync(raw)), ch('IEND', Buffer.alloc(0))]);
}
const HOUSES = process.env.RM_HOUSES ? JSON.parse(process.env.RM_HOUSES) : [{ slug: '15_ward_st_hingham', addr: '15 Ward St, Hingham, MA 02043' }, { slug: '30_lockwood_dr_weymouth', addr: '30 Lockwood Dr, Weymouth, MA 02190' }, { slug: '49_scotland_st_hingham', addr: '49 Scotland Street, Hingham, MA 02043' }, { slug: '6_harborview_rd_hull', addr: '6 Harborview Road, Hull, MA 02045' }];
(async () => {
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + srv.address().port + '/';
  const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome', args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const res = { www: WWW, houses: {}, checks: {} };
  const MOCK = { google: 0, azure: 0, bing: 0 };
  for (const H of HOUSES) {
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } });
    const errs = [], hosts = {};
    await ctx.route('**/*', (route) => {
      const u = new URL(route.request().url());
      if (u.hostname === 'tile.googleapis.com') { MOCK.google++;
        if (/createSession/.test(u.pathname)) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ session: 'MOCKSESSION', expiry: '9999', tileWidth: 256, imageFormat: 'png' }) });
        if (/viewport/.test(u.pathname)) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ copyright: 'Imagery ©2026 MOCK', maxZoomRects: [] }) });
        return route.fulfill({ status: 200, contentType: 'image/png', body: png(200, 40, 40) }); }
      if (u.hostname === 'atlas.microsoft.com') { MOCK.azure++;
        if (/attribution/.test(u.pathname)) return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ copyrights: ['© MOCK Microsoft'] }) });
        return route.fulfill({ status: 200, contentType: 'image/png', body: png(40, 40, 200) }); }
      if (u.hostname === 'dev.virtualearth.net') { MOCK.bing++; return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ copyright: '© MOCK Bing',
        resourceSets: [{ resources: [{ imageUrl: 'https://mock-bing.invalid/tiles/a{quadkey}.jpeg?g=1', imageUrlSubdomains: ['t0'], zoomMax: 19 }] }] }) }); }
      if (u.hostname === 'mock-bing.invalid') return route.fulfill({ status: 200, contentType: 'image/png', body: png(40, 200, 40) });
      if (/(unpkg|jsdelivr|cdnjs)/.test(u.hostname)) return route.abort();
      if (u.hostname !== '127.0.0.1') hosts[u.hostname] = (hosts[u.hostname] || 0) + 1;
      return route.continue();
    });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
    page.on('console', (m) => { if (m.type() === 'error') errs.push('console.error: ' + m.text()); });
    await page.goto(base + 'index.html?addr=' + encodeURIComponent(H.addr), { waitUntil: 'load' });
    await page.waitForFunction(() => window.RoofApp && window.RoofApp.result, null, { timeout: 90000 });
    await page.evaluate(() => window.RoofApp.autoPitch());
    // tag via the real tap path (applyTag at projected screen points), plus a manual measurement
    const tagged = await page.evaluate(() => {
      const A = window.RoofApp, st = A.state, m = A.map, r = st.result, out = {}; st.noStructures = false;
      const mid = (e) => { const p = m.project([(e.from[0] + e.to[0]) / 2, (e.from[1] + e.to[1]) / 2]); return [p.x, p.y]; };
      const tap = (tool, p, ll) => { st.tagTool = tool; const ok = A.applyTag(p, ll || m.unproject(p).toArray()); st.tagTool = ''; return ok; };
      document.getElementById('confirmAllBtn').click(); out.confirmed = Object.keys(st.tags.confirmed).length;
      const e0 = r.edges[0], e1 = r.edges[1 % r.edges.length];
      out.step = tap('edge:step_flashing', mid(e0)); out.drip = tap('edge:drip_edge', mid(e1));
      const f = A.facetsLive;
      if (f && f.line_segments) { const i = f.line_segments.findIndex((s) => s.type === 'ridge' && s.coords_lonlat);
        if (i >= 0) { const s = f.line_segments[i]; const p = m.project([(s.coords_lonlat[0][0] + s.coords_lonlat[1][0]) / 2, (s.coords_lonlat[0][1] + s.coords_lonlat[1][1]) / 2]);
          out.line = tap('line:hip', [p.x, p.y]); out.line_i = i; } }
      if (f && f.facets && f.facets.length) { const fx = f.facets[0], P = fx.polygon_lonlat; let cx = 0, cy = 0; P.slice(0, -1).forEach((q) => { cx += q[0]; cy += q[1]; });
        const ll = [cx / (P.length - 1), cy / (P.length - 1)], p = m.project(ll); out.area = tap('area:deck', [p.x, p.y], ll); out.area_id = fx.id; }
      else { out.area = tap('area:flat', [0, 0], [0, 0]); }
      document.getElementById('mmLabel').value = 'Front eave (Google Earth ruler)'; document.getElementById('mmValue').value = '41.5';
      document.getElementById('mmAdd').click();
      document.getElementById('userNotes').value = 'Test note from headless run.';
      out.tags = JSON.parse(JSON.stringify(st.tags)); out.mm = st.manualMeas.length;
      return out;
    });
    await page.screenshot({ path: path.join(OUT, H.slug + '_app_tagged.png') });
    // report: button path -> preview overlay
    await page.click('#pdfBtn');
    await page.waitForFunction(() => /Report ready|Report failed/.test(document.getElementById('status').textContent), null, { timeout: 120000 });
    const st = await page.evaluate(() => document.getElementById('status').textContent);
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(OUT, H.slug + '_preview.png') });
    // edit text in preview, then take the edited HTML (what Save/Share would print)
    const edit = await page.evaluate(() => { document.getElementById('rvEdit').click(); const d = document.getElementById('rvFrame').contentDocument;
      const h1 = d.querySelector('h1'); const before = h1 ? h1.textContent : ''; if (h1) h1.textContent = before + ' (edited)'; document.getElementById('rvEdit').click();
      const html = window.RoofReport.frameHtml(); return { designOff: d.designMode, edited: /\(edited\)/.test(html), html }; });
    const html = edit.html;
    fs.writeFileSync(path.join(OUT, H.slug + '_report.html'), html);
    const rp = await ctx.newPage(); await rp.setContent(html, { waitUntil: 'load' });
    await rp.pdf({ path: path.join(OUT, H.slug + '_report.pdf'), preferCSSPageSize: true, format: 'Letter' }); await rp.close();
    const last = await page.evaluate(() => { const o = window.RoofReport.last; return { summary: o.summary, tiles: o.tiles, user_tags: o.result.user_tags, um: o.result.user_measurements,
      notes: o.result.notes, pitch: o.result.pitch, pitch_source: o.result.pitch_source, lines: o.result.lines }; });
    const aer = (html.match(/<figure class="aerial">[\s\S]*?<\/figure>/) || [''])[0];
    const v172 = { aerial_lines: (aer.match(/<line /g) || []).length, aerial_numbers: (aer.match(/<text /g) || []).length, aerial_caption_typed: /typed edges overlaid/.test(aer),
      struct: /id="h-struct"/.test(html), solar: /id="h-solar"/.test(html), assessor: /Year built \(assessor\)|Stories \(assessor\)|Assessor style/.test(html) };
    // structured editor: +1.0 ft on edge 0 length, apply -> rebuilt report
    const ed = await page.evaluate(async () => {
      const R = window.RoofReport.last.result, e0 = R.edges[0];
      document.getElementById('rvMeas').click();
      const inp = document.querySelector('[data-me-len="0"]'); inp.value = (e0.length_ft + 1).toFixed(2);
      document.getElementById('status').textContent = '';
      document.getElementById('me-apply').click();
      await new Promise((res) => { const t = setInterval(() => { if (/Report ready|Report failed/.test(document.getElementById('status').textContent)) { clearInterval(t); res(); } }, 200); });
      const R2 = window.RoofReport.last.result;
      return { type: e0.type, before: { eave: R.eave_lf, rake: R.rake_sloped_lf, gutter: R.gutter_lf, len: e0.length_ft }, after: { eave: R2.eave_lf, rake: R2.rake_sloped_lf, gutter: R2.gutter_lf, len: R2.edges[0].length_ft,
        src: R2.edges[0].length_source }, marked: /user edit \(auto/.test(window.RoofReport.last.html), roof_same: R.roof_area_sqft === R2.roof_area_sqft };
    });
    // undo the length edit so the remaining checks match 0.1.7.1 state
    await page.evaluate(() => { window.RoofApp.state.tags.lengths = {}; window.RoofApp.render(); });
    // opt-in per-facet lidar pitch
    const pf = await page.evaluate(async () => {
      const A = window.RoofApp; A.state.perFacetPitch = true; A.state.noStructures = true;
      const r = window.RoofReport.buildResult(A); A.state.perFacetPitch = false; A.state.noStructures = false;
      return { used: !!r.per_facet_pitch_used, roof: r.roof_area_sqft, single: r.roof_area_sqft_single_pitch, note: (r.notes || []).filter((n) => /per-facet/i.test(n))[0] };
    });
    await page.screenshot({ path: path.join(OUT, H.slug + '_preview_editor.png') });
    const pfHtml = await page.evaluate(async () => { const A = window.RoofApp; A.state.perFacetPitch = true; const r = window.RoofReport.buildResult(A); A.state.perFacetPitch = false;
      const o = await window.RoofReport.render(r); return o.html; });
    { const rp2 = await ctx.newPage(); await rp2.setContent(pfHtml, { waitUntil: 'load' });
      await rp2.pdf({ path: path.join(OUT, H.slug + '_report_perfacet_optin.pdf'), preferCSSPageSize: true, format: 'Letter' }); await rp2.close(); }
    v172.editor = ed; v172.per_facet_opt_in = pf;
    await page.evaluate(() => document.getElementById('rvClose').click());
    // reference layers with mocked keys
    const ref = await page.evaluate(async () => {
      const A = window.RoofApp, o = {};
      o.noKey = await A.setBasemap('google').then(() => A.state.basemap); // no key -> stays on massgis
      localStorage.setItem('roofmeasure.refkeys.v1', JSON.stringify({ google: 'MOCKKEY', azure: 'MOCKAZ', bing: 'MOCKBING' }));
      for (const k of ['google', 'azure', 'bing', 'esri']) { await A.setBasemap(k); await new Promise((r) => setTimeout(r, 1500));
        o[k] = { basemap: A.state.basemap, banner: !document.getElementById('refBanner').hidden, snapDisabled: document.getElementById('snapBtn').disabled,
          logo: !document.getElementById('googleLogo').hidden, refInfo: document.getElementById('refInfo').textContent }; }
      document.getElementById('drawBtn').click(); o.drawBlocked = A.state.mode !== 'draw'; o.drawStatus = document.getElementById('status').textContent;
      await A.snap(); o.snapStatus = document.getElementById('status').textContent;
      await A.setBasemap('massgis');
      document.getElementById('cmpLayer').value = 'google'; await A.setCompare(true); await new Promise((r) => setTimeout(r, 1500));
      o.compare = { on: !!A.map2, mainBasemap: A.state.basemap, map2Visible: !document.getElementById('map2').hidden, clip: document.getElementById('map2').style.clipPath };
      return o;
    });
    await page.screenshot({ path: path.join(OUT, H.slug + '_compare_google_mock.png') });
    await page.evaluate(() => window.RoofApp.setCompare(false));
    const ov = await page.evaluate(async () => {
      const A = window.RoofApp, o = {};
      document.getElementById('ovOpacity').value = '55'; await A.setOverlay('google'); await new Promise((r) => setTimeout(r, 1500));
      const order = A.map.getStyle().layers.map((l) => l.id);
      o.over = { overlay: A.state.overlay, layer: !!A.map.getLayer('refover'), opacity: A.map.getPaintProperty('refover', 'raster-opacity'), below_edges: order.indexOf('refover') < order.indexOf('edges'),
        banner: !document.getElementById('refBanner').hidden, labels: document.querySelectorAll('.lbl').length, lineLabels: document.querySelectorAll('.lbl.line').length };
      document.getElementById('drawBtn').click(); o.drawBlocked = A.state.mode !== 'draw';
      document.getElementById('ovPos').value = 'under'; await A.setOverlay('bing'); await new Promise((r) => setTimeout(r, 1200));
      const order2 = A.map.getStyle().layers.map((l) => l.id);
      o.under = { overlay: A.state.overlay, under_ortho: order2.indexOf('refover') < order2.indexOf('ortho'), orthoOpacity: A.map.getPaintProperty('ortho', 'raster-opacity') };
      return o;
    });
    await page.evaluate(async () => { document.getElementById('ovPos').value = 'over'; await window.RoofApp.setOverlay('google'); await new Promise((r) => setTimeout(r, 1500)); });
    await page.screenshot({ path: path.join(OUT, H.slug + '_overlay_google_mock.png') });
    const ex = await page.evaluate(async () => {
      const A = window.RoofApp, o = {}, lg = document.getElementById('googleLogo');
      o.logo = { visible: !lg.hidden, tag: lg.tagName, alt: lg.alt, src: lg.getAttribute('src'), height: lg.getBoundingClientRect().height };
      const B = A.BASEMAPS.google, s0 = B.session; B.sessionExpiry = Date.now() / 1000 + 100;
      o.due = A.googleDue(); o.refreshed = await A.refreshGoogle('test'); o.newSessionObj = B.sessionAt > 0;
      document.getElementById('palette').value = 'cb'; document.getElementById('palette').onchange();
      o.cbEave = JSON.stringify(A.map.getPaintProperty('edges', 'line-color')).includes('#0072B2');
      document.getElementById('palette').value = 'std'; document.getElementById('palette').onchange();
      o.edgeRowsAria = document.querySelectorAll('#edges tr[role=button][aria-label]').length; o.labelAria = document.querySelectorAll('.lbl[aria-label]').length;
      o.statusLive = document.getElementById('status').getAttribute('aria-live');
      return o;
    });
    await page.evaluate(() => window.RoofApp.setOverlay(''));
    res.houses[H.slug] = { address: H.addr, status: st, tagged, edit: { designOff: edit.designOff, edited: edit.edited }, report: last, ref, overlay: ov, v172, extra: ex, errors: errs, external_hosts: hosts,
      html_checks: { tags_section: /id="h-tags"/.test(html), user_meas: /User-supplied measurements/.test(html), per_facet: /Per-facet pitch from lidar planes/.test(html), sources_table: /Measurement data sources/.test(html), checked: (html.match(/Checked by user: (\d+) of (\d+)/) || []).slice(1),
        no_google_urls: !/googleapis|MOCKKEY|MOCKAZ|MOCKBING|virtualearth|atlas\.microsoft/.test(html), user_note: /Test note from headless run/.test(html),
        sections: (html.match(/<h2 id="h-[a-z]+"/g) || []).map((x) => x.slice(8, -1)) } };
    await ctx.close();
  }
  {
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } });
    const page = await ctx.newPage(); const errs = []; page.on('pageerror', (e) => errs.push(e.message));
    await page.goto(base + 'index.html?lat=30.2672&lon=-97.7431', { waitUntil: 'load' });
    await page.waitForFunction(() => window.RoofApp && (window.RoofApp.result || /No building found/.test(document.getElementById('status').textContent)), null, { timeout: 90000 });
    res.outside_ma = await page.evaluate(() => { const r = window.RoofApp.result; return r ? { source: r.source, overhang_source: r.overhang_source, footprint: r.footprint_area_sqft,
      warn: document.getElementById('warn').textContent, log: document.getElementById('status').textContent.slice(0, 400) } : { none: document.getElementById('status').textContent }; });
    res.outside_ma.errors = errs; await ctx.close();
  }
  res.mock_requests = MOCK;
  await browser.close(); srv.close();
  fs.writeFileSync(path.join(OUT, 'v0172_test.json'), JSON.stringify(res, null, 1));
  console.log(JSON.stringify(res, (k, v) => (k === 'notes' || k === 'plane_rows' || k === 'tags' ? undefined : v), 1));
})().catch((e) => { console.error('FAIL', e); srv.close(); process.exit(1); });
