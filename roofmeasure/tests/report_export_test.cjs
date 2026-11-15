// Headless proof of the in-app PDF export on the bundled android/www (v0.1.7+).
// node android/tests/report_export_test.cjs [outPdf]
// 1. serves android/www on 127.0.0.1, blocks every CDN host (unpkg, jsdelivr, cdnjs, googleapis) and logs all hosts hit
// 2. measures 15 Ward St, Hingham via ?addr=, runs Auto pitch (lidar, local laz-perf), builds the report in-app (Pyodide)
// 3. prints the in-app report HTML with Chrome page.pdf() (Letter, CSS page size) -> outPdf
// 4. fully-offline pass: all non-localhost requests aborted; report still renders with the labelled aerial placeholder
const PW = process.env.PW || '/usr/local/lib/pnpm/5/.pnpm/playwright-core@1.59.1/node_modules/playwright-core';
const { chromium } = require(PW);
const http = require('http'), fs = require('fs'), path = require('path');
const WWW = process.env.WWW || path.join(__dirname, '..', 'www');
const OUT = process.argv[2] || '/workspace/artifacts/roof-overlay/apk/sample_export_15_ward_st.pdf';
const EV = path.join(__dirname, 'evidence'); fs.mkdirSync(EV, { recursive: true });
const MIME = { '.html': 'text/html', '.js': 'application/javascript', '.mjs': 'application/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.wasm': 'application/wasm', '.zip': 'application/zip', '.py': 'text/plain', '.md': 'text/plain' };
const srv = http.createServer((q, s) => {
  const p = path.join(WWW, decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
  if (!p.startsWith(WWW) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { s.writeHead(404); return s.end(); }
  s.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(s);
});
const CDN = /(^|\.)(unpkg\.com|jsdelivr\.net|cdnjs\.cloudflare\.com|googleapis\.com|gstatic\.com)$/;
(async () => {
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + srv.address().port + '/';
  const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome',
    args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const res = { base, www: WWW };
  // ---------- pass 1: CDNs blocked, live MassGIS/USGS data
  {
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } });
    const hosts = {}, blocked = [], errs = [], local = {};
    await ctx.route('**/*', (route) => {
      const u = new URL(route.request().url());
      if (CDN.test(u.hostname)) { blocked.push(u.href); return route.abort(); }
      if (u.hostname === '127.0.0.1') local[u.pathname] = (local[u.pathname] || 0) + 1; else hosts[u.hostname] = (hosts[u.hostname] || 0) + 1;
      return route.continue();
    });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
    page.on('console', (m) => { if (m.type() === 'error') errs.push('console.error: ' + m.text()); });
    const t0 = Date.now();
    await page.goto(base + 'index.html?addr=' + encodeURIComponent('15 Ward St, Hingham, MA 02043'), { waitUntil: 'load' });
    await page.waitForFunction(() => window.RoofApp && window.RoofApp.result, null, { timeout: 60000 });
    await page.evaluate(() => window.RoofApp.autoPitch());
    const app = await page.evaluate(() => { const r = window.RoofApp.result; return { address: r.address, source: r.source, footprint_area_sqft: r.footprint_area_sqft,
      pitch: r.pitch, pitch_source: r.pitch_source, eave_lf: r.eave_lf, rake_plan_lf: r.rake_plan_lf, rake_sloped_lf: r.rake_sloped_lf, gutter_lf: r.gutter_lf,
      downspouts: r.downspouts, roof_area_sqft: r.roof_area_sqft, struct: window.RoofApp.state.feature && window.RoofApp.state.feature.properties.STRUCT_ID,
      pdfButton: !!document.getElementById('pdfBtn') }; });
    const t1 = Date.now();
    const out = await page.evaluate(() => window.RoofReport.render(window.RoofReport.buildResult(window.RoofApp)).then((o) => { window.__rep = o; return { summary: o.summary, tiles: o.tiles, htmlLen: o.html.length, measurements_csv: o.measurements_csv, lines: o.result.lines, notes: o.result.notes }; }));
    const t2 = Date.now();
    // the button path too (browser fallback -> hidden iframe + print(); headless print() is a no-op)
    await page.evaluate(() => { window.print = () => {}; });
    await page.click('#pdfBtn');
    await page.waitForFunction(() => /Report ready|Report failed/.test(document.getElementById('status').textContent), null, { timeout: 60000 });
    const btnStatus = await page.evaluate(() => document.getElementById('status').textContent);
    const frameHasReport = await page.evaluate(() => { const f = document.getElementById('rm-report-frame'); return !!(f && /Roof Measurement Report/.test(f.contentDocument.body.innerText)); });
    const html = await page.evaluate(() => window.__rep.html);
    fs.writeFileSync(path.join(EV, 'inapp_15_ward_st.html'), html);
    const rp = await ctx.newPage();
    await rp.setContent(html, { waitUntil: 'load' });
    await rp.pdf({ path: OUT, preferCSSPageSize: true, format: 'Letter' });
    await page.screenshot({ path: path.join(EV, 'inapp_15_ward_st_app.png') });
    Object.assign(res, { pass1: { app, report: out, ms_measure: t1 - t0, ms_report_first: t2 - t1, button_status: btnStatus, iframe_has_report: frameHasReport,
      cdn_blocked: blocked, external_hosts: hosts, local_files: local, errors: errs, pdf: OUT } });
    await ctx.close();
  }
  // ---------- pass 2: fully offline (only 127.0.0.1); feed the saved result, check placeholder + engine load
  {
    const ctx = await browser.newContext();
    const ext = [], errs = [];
    await ctx.route('**/*', (route) => { const u = new URL(route.request().url()); if (u.hostname !== '127.0.0.1') { ext.push(u.hostname); return route.abort(); } return route.continue(); });
    const page = await ctx.newPage();
    page.on('pageerror', (e) => errs.push('pageerror: ' + e.message));
    await page.goto(base + 'index.html?autopick=0', { waitUntil: 'load' });
    await page.waitForFunction(() => window.RoofReport && window.RoofCalc && window.RoofFacets, null, { timeout: 30000 });
    const r = JSON.parse(fs.readFileSync('/workspace/roofmeasure/report/out/15_ward_st_hingham/result.json', 'utf8'));
    delete r.structures_on_lot; delete r.solar;
    const o = await page.evaluate((r) => window.RoofReport.render(r).then((o) => ({ tiles: o.tiles, placeholder: /AERIAL IMAGE NOT AVAILABLE/.test(o.html), aerial: o.summary.aerial, roof: o.summary.roof_area_sqft })), r);
    res.pass2_offline = { report: o, aborted_external_hosts: [...new Set(ext)], errors: errs };
    await ctx.close();
  }
  await browser.close(); srv.close();
  fs.writeFileSync(path.join(EV, 'report_export_test.json'), JSON.stringify(res, null, 1));
  console.log(JSON.stringify(res, (k, v) => (k === 'local_files' || k === 'measurements_csv' ? undefined : v), 1));
})().catch((e) => { console.error('FAIL', e); srv.close(); process.exit(1); });
