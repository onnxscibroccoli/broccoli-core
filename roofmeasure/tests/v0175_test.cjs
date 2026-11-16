// SPDX-License-Identifier: MIT
// Headless test for RoofMeasure 0.1.7.5 (www/): roof features (skylights with sizes, roof decks), window view, lidar-vs-model residuals; plus 0.1.7.4: ortho lean/offset (with a no-align "before" copy), ortho patch and dormer
// candidates, doubtful lidar ridges, town-aware geocoding (Hull addresses), 3-D roof view/editor (open, pitch edit, ridge-end
// move, screenshots), plus everything from 0.1.7.3: roof model choice (no phantom hips), sloped rakes everywhere, whole-roof lidar segmentation
// (extra lines, small planes, skylight candidates), report editor (sloped rake edit, delete/add line, skylight add/remove, roof model),
// per-facet on/off PDFs, aerial robustness (one tile aborted -> grey tile, aerial still drawn), colour-blind palette, outside MA.
// node tests/v0175_test.cjs <outDir>
const PW = process.env.PW || '/usr/local/lib/pnpm/5/.pnpm/playwright-core@1.59.1/node_modules/playwright-core';
const { chromium } = require(PW);
const http = require('http'), fs = require('fs'), path = require('path');
const WWW = process.env.WWW || path.join(__dirname, '..', 'www');
const OUT = process.argv[2] || '/tmp/v0175/test'; fs.mkdirSync(OUT, { recursive: true });
const MIME = { '.html': 'text/html', '.js': 'application/javascript', '.mjs': 'application/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.wasm': 'application/wasm', '.zip': 'application/zip', '.py': 'text/plain', '.md': 'text/plain', '.svg': 'image/svg+xml' };
const srv = http.createServer((q, s) => {
  const p = path.join(WWW, decodeURIComponent(q.url.split('?')[0]).replace(/^\/+/, '') || 'index.html');
  if (!p.startsWith(WWW) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { s.writeHead(404); return s.end(); }
  s.writeHead(200, { 'Content-Type': MIME[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(s);
});
// 30 Lockwood Dr and 49 Scotland St do not exist in Hull in any free source (MassGIS geocoder + L3 parcels, Census, OSM); the only
// matches are in Weymouth and Hingham, so those are the fixtures, and the Hull spellings are checked for a clear "not found in HULL".
const HOUSES = process.env.RM_HOUSES ? JSON.parse(process.env.RM_HOUSES) : [{ slug: '15_ward_st_hingham', addr: '15 Ward St, Hingham, MA 02043' }, { slug: '6_harborview_rd_hull', addr: '6 Harborview Road, Hull, MA 02045' }, { slug: '30_lockwood_dr_weymouth', addr: '30 Lockwood Dr, Weymouth, MA 02190' }, { slug: '49_scotland_st_hingham', addr: '49 Scotland Street, Hingham, MA 02043' }];
const ONLY = !!process.env.RM_ONLY_HOUSES; // benchmark runs: houses only
const HULL_FORMS = ['30 Lockwood Drive, Hull, MA 02045', '49 Scotland Street, Hull, MA 02045', '6 Harborview Road, Hull, MA 02045'];
const sum = (r) => ({ roof: r.roof_area_sqft, squares: r.squares, eave: r.eave_lf, rake_sloped: r.rake_lf, rake_plan: r.rake_plan_lf, pitch: r.pitch, model: r.roof_model_info && { model: r.roof_model_info.model, source: r.roof_model_info.source },
  lines: r.lines, cand: r.line_candidates, edges: r.edges.map((e) => [e.i, e.type, e.length_ft, e.sloped_length_ft]), diag: r.aerial_diag, pfu: r.per_facet_n_used || 0, sky: (r.skylights || []).length,
  seg: r.lidar_seg && r.lidar_seg.summary, palette: r.palette,
  ortho: r.ortho_align && Object.assign({}, r.ortho_align, { residuals: undefined }), ortho_patches: (r.ortho_patches || []).length, dormers: (r.dormers || []).map((d) => [d.key, d.type, d.gutter_lf, d.confidence]),
  features: r.roof_features && { skylights: (r.roof_features.skylights || []).map((k) => [k.label, k.w_ft, k.h_ft, k.source, k.centroid_lonlat]), decks: (r.roof_features.decks || []).map((d) => [d.area_sqft, d.pitch, d.n_points, d.confidence]) }, model_fit: r.lidar_model_fit && { median_ft: r.lidar_model_fit.median_ft, shift: r.lidar_model_fit.shift_ft, eave_above_ground_ft: r.lidar_model_fit.eave_above_ground_ft, facets: (r.lidar_model_fit.facets || []).map((f) => [f.facet, f.pitch, f.n, f.median_ft, f.max_ft]) },
  doubtful: (r.line_segments || []).filter((s) => s.lidar_doubt).map((s) => [s.type, s.length_ft, s.lidar_doubt]) });
const htmlChecks = (h) => ({ fullpages: (h.match(/class="fullpage pb"/g) || []).length, aerial_missing: /AERIAL IMAGE NOT AVAILABLE/.test(h), overlay_missing: /AERIAL OVERLAY NOT AVAILABLE/.test(h),
  sloped_label: /sloped \(/.test(h), seg_section: /id="h-seg"/.test(h), mit: /MIT-licensed/.test(h), no_ref_urls: !/googleapis|virtualearth|atlas\.microsoft|MOCKKEY/.test(h),
  sections: (h.match(/<h2 id="h-[a-z]+"/g) || []).map((x) => x.slice(8, -1)) });
async function pdf(ctx, html, file) { const rp = await ctx.newPage(); await rp.setContent(html, { waitUntil: 'load' }); await rp.pdf({ path: file, format: 'Letter', preferCSSPageSize: true }); await rp.close(); }
(async () => {
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const base = 'http://127.0.0.1:' + srv.address().port + '/';
  const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome', args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const res = { www: WWW, houses: {} };
  for (const H of HOUSES) {
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } }); const page = await ctx.newPage(); const errs = [];
    await ctx.route(/tile\.googleapis\.com|atlas\.microsoft\.com|virtualearth\.net/, (r) => r.abort());
    page.on('pageerror', (e) => errs.push(e.message));
    await page.goto(base + 'index.html?addr=' + encodeURIComponent(H.addr), { waitUntil: 'load' });
    await page.waitForFunction(() => window.RoofApp && window.RoofApp.result, null, { timeout: 90000 });
    const o = { no_lidar: await page.evaluate(() => ({ model: window.RoofApp.state.result.roof_model_info, lines: (window.RoofApp.facetsLive || {}).lines })) };
    await page.evaluate(() => window.RoofApp.autoPitch());
    { // "before": same report without the ortho shift (overlay as 0.1.7.3 drew it)
      const x = await page.evaluate(async () => { const A = window.RoofApp; A.state.perFacetPitch = false; window.RM_NO_ORTHO_ALIGN = true;
        const out = await window.RoofReport.preview(A, () => {}); window.RM_NO_ORTHO_ALIGN = false; document.getElementById('rvClose').click(); return { html: out.html, oa: out.result.ortho_align }; });
      fs.writeFileSync(path.join(OUT, H.slug + '_no_ortho_align.html'), x.html); await pdf(ctx, x.html, path.join(OUT, H.slug + '_no_ortho_align.pdf'));
      o.no_align = x.oa && { applied: x.oa.applied, shift_m: x.oa.shift_m };
    }
    for (const pf of [false, true]) {
      const x = await page.evaluate(async (pf) => { const A = window.RoofApp; A.state.perFacetPitch = pf; const out = await window.RoofReport.preview(A, () => {});
        document.getElementById('rvClose').click(); return { html: out.html, r: out.result }; }, pf);
      const nm = H.slug + (pf ? '_per_facet_on' : '_per_facet_off');
      fs.writeFileSync(path.join(OUT, nm + '.html'), x.html); await pdf(ctx, x.html, path.join(OUT, nm + '.pdf'));
      o[pf ? 'pf_on' : 'pf_off'] = { ...sum(x.r), html: htmlChecks(x.html) };
    }
    // 3-D roof view / editor: open, screenshot, set a facet pitch, move a ridge end, screenshot, numbers before/after
    o.view3d = await page.evaluate(async () => { try {
      const A = window.RoofApp, st = A.state; st.perFacetPitch = false;
      const i0 = await window.Roof3D.open(); if (!i0) return { error: 'open failed: ' + document.getElementById('status').textContent };
      return { open: i0 }; } catch (e) { return { error: String(e && e.message || e) }; } });
    if (!o.view3d.error) {
      await page.waitForTimeout(800); await page.screenshot({ path: path.join(OUT, H.slug + '_3d_view.png') });
      o.view3d.edit = await page.evaluate(async () => { try {
        const A = window.RoofApp, r0 = window.RoofReport.buildResult(A), f0 = r0.facets[0];
        const rid = (r0.line_segments || []).map((s, i) => [s, i]).find(([s]) => s.type === 'ridge' && !s.deleted && !s.unverified && s.coords_lonlat);
        const ed = { pitch: {} , ends: {} }; ed.pitch[f0.id] = f0.pitch === '10/12' ? '9/12' : '10/12';
        if (rid) { const c = rid[0].coords_lonlat, d = [(c[1][0] - c[0][0]) * 0.1, (c[1][1] - c[0][1]) * 0.1]; ed.ends[rid[1]] = [[c[0][0] + d[0], c[0][1] + d[1]], c[1]]; }
        const i1 = await window.Roof3D.apply(ed); const r1 = window.RoofReport.buildResult(A);
        return { facet: f0.id, from: f0.pitch, to: ed.pitch[f0.id], area_before: r0.roof_area_sqft, area_after: r1.roof_area_sqft, ridge_before: r0.lines && r0.lines.ridge_lf, ridge_after: r1.lines && r1.lines.ridge_lf,
          moved_line: rid ? rid[1] : null, edits_3d: r1.edits_3d, facet_src: (r1.facets.find((x) => x.id === f0.id) || {}).pitch_source, info: i1 }; } catch (e) { return { error: String(e && e.message || e) }; } });
      await page.waitForTimeout(800); await page.screenshot({ path: path.join(OUT, H.slug + '_3d_after_edit.png') });
      const x3 = await page.evaluate(async () => { window.Roof3D.close(); const out = await window.RoofReport.preview(window.RoofApp, () => {}); document.getElementById('rvClose').click(); window.RoofApp.state.tags = window.RoofTags.emptyTags(); window.RoofApp.state.edits3d = null; return { html: out.html }; });
      o.view3d.report_mentions_edit = /3-D roof editor/.test(x3.html);
      fs.writeFileSync(path.join(OUT, H.slug + '_after_3d_edit.html'), x3.html);
    }
    // report editor: edit the first rake as SLOPED length, delete interior line 0, add a valley line and a skylight, keep model
    o.editor = await page.evaluate(async () => { try {
      const A = window.RoofApp, st = A.state; st.perFacetPitch = false;
      await window.RoofReport.preview(A, () => {});
      document.getElementById('rvMeas').click();
      const box = document.getElementById('rvEditor'), rk = A.state.result.edges.find((e) => e.type === 'rake') || A.state.result.edges[0];
      const inp = box.querySelector('[data-me-len="' + rk.i + '"]'); const before = +inp.value; inp.value = (before + 2).toFixed(1);
      const ln = box.querySelector('[data-me-line]'); if (ln) ln.value = 'none';
      document.getElementById('me-addline').click(); const tr = box.querySelector('#me-added tr:last-child'); tr.querySelector('select').value = 'valley'; tr.querySelectorAll('input')[0].value = '6.5'; tr.querySelectorAll('input')[1].value = 'tape on site';
      document.getElementById('me-addsky').click(); const sk = box.querySelector('#me-sky tr:last-child'); const si = sk.querySelectorAll('input'); si[0].value = '2.5'; si[1].value = '4'; si[2].value = 'rear plane';
      document.getElementById('me-apply').click();
      await new Promise((r) => setTimeout(r, 300)); await (window.RoofReport.last && Promise.resolve());
      for (let k = 0; k < 100 && !(window.RoofReport.last && window.RoofReport.last.result && window.RoofReport.last.result.added_lines); k++) await new Promise((r) => setTimeout(r, 200));
      const r = window.RoofReport.last.result, e = r.edges.find((x) => x.i === rk.i);
      document.getElementById('rvClose').click();
      return { edited_edge: rk.i, edited_type: rk.type, entered_sloped: before + 2, after_sloped: e.sloped_length_ft, after_plan: e.length_ft, user_edit: !!e.user_length, deleted_line0: !!(r.line_segments && r.line_segments[ln ? +ln.dataset.meLine : 0] || {}).deleted,
        added_lines: r.added_lines, skylights_user: (r.skylights || []).filter((k) => k.source === 'user').length, lines: r.lines, html_has_user_sky: /rear plane/.test(window.RoofReport.last.html) };
    } catch (e) { return { error: String(e && e.message || e) }; } });
    o.errors = errs; res.houses[H.slug] = o; await ctx.close(); fs.writeFileSync(path.join(OUT, 'v0175_test.partial.json'), JSON.stringify(res, null, 1));
  }
  if (!ONLY) { // aerial robustness: abort one MassGIS ortho tile every time -> grey tile, aerial page still drawn, failure listed
    const ctx = await browser.newContext({ viewport: { width: 420, height: 860 } }); const page = await ctx.newPage(); let aborted = null; const errs = [];
    page.on('pageerror', (e) => errs.push(e.message));
    await ctx.route(/Massachusetts_Aerial_Imagery_2025\/MapServer\/tile\/19\//, (r) => { const u = r.request().url(); if (!aborted) aborted = u; return u === aborted ? r.abort() : r.continue(); });
    await page.goto(base + 'index.html?addr=' + encodeURIComponent(HOUSES[0].addr), { waitUntil: 'load' });
    await page.waitForFunction(() => window.RoofApp && window.RoofApp.result, null, { timeout: 90000 });
    await page.evaluate(() => window.RoofApp.autoPitch());
    const x = await page.evaluate(async () => { const A = window.RoofApp; const o = [];
      for (const pf of [false, true]) { A.state.perFacetPitch = pf; const out = await window.RoofReport.preview(A, () => {}); document.getElementById('rvClose').click();
        o.push({ pf, diag: out.result.aerial_diag, missing: /AERIAL IMAGE NOT AVAILABLE/.test(out.html), has_aerial_svg: /class="fullfig"/.test(out.html), html: out.html }); }
      return o; });
    fs.writeFileSync(path.join(OUT, 'tile_failure_per_facet_on.html'), x[1].html); await pdf(ctx, x[1].html, path.join(OUT, 'tile_failure_per_facet_on.pdf'));
    res.tile_failure = { aborted_url: aborted, runs: x.map((y) => ({ pf: y.pf, diag: y.diag, missing: y.missing, has_aerial_svg: y.has_aerial_svg })), errors: errs };
    await ctx.close();
  }
  if (!ONLY) { // town-aware geocoding: the Hull spellings
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } }); res.hull_geocode = [];
    for (const a of HULL_FORMS) { const page = await ctx.newPage(); await page.goto(base + 'index.html?addr=' + encodeURIComponent(a), { waitUntil: 'load' });
      await page.waitForFunction(() => window.RoofApp && (window.RoofApp.result || /not found|WARNING/i.test(document.getElementById('status').textContent)), null, { timeout: 90000 }).catch(() => {});
      res.hull_geocode.push(await page.evaluate((a) => ({ asked: a, address: window.RoofApp.state.address || null, warning: window.RoofApp.state.geocodeWarning || null, status: document.getElementById('status').textContent.slice(0, 200), result: !!window.RoofApp.result }), a)); await page.close(); }
    await ctx.close();
  }
  if (!ONLY) { // colour-blind palette
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } }); const page = await ctx.newPage();
    await page.goto(base + 'index.html?addr=' + encodeURIComponent(HOUSES[0].addr), { waitUntil: 'load' });
    await page.waitForFunction(() => window.RoofApp && window.RoofApp.result, null, { timeout: 90000 });
    res.palette_cb = await page.evaluate(async () => { const s = document.getElementById('palette'); s.value = 'cb'; s.dispatchEvent(new Event('change'));
      const out = await window.RoofReport.preview(window.RoofApp, () => {}); return { palette: out.result.palette, okabe_blue: /#0072B2/i.test(out.html) }; });
    await ctx.close();
  }
  if (!ONLY) { // outside MA
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 900 } }); const page = await ctx.newPage(); const errs = []; page.on('pageerror', (e) => errs.push(e.message));
    await page.goto(base + 'index.html?lat=30.2672&lon=-97.7431', { waitUntil: 'load' });
    await page.waitForFunction(() => window.RoofApp && (window.RoofApp.result || /No building found/.test(document.getElementById('status').textContent)), null, { timeout: 90000 });
    res.outside_ma = await page.evaluate(() => { const r = window.RoofApp.result; return r ? { source: r.source, footprint: r.footprint_area_sqft, model: r.roof_model_info && r.roof_model_info.source } : { none: document.getElementById('status').textContent }; });
    res.outside_ma.errors = errs; await ctx.close();
  }
  await browser.close(); srv.close();
  fs.writeFileSync(path.join(OUT, 'v0175_test.json'), JSON.stringify(res, null, 1));
  console.log(JSON.stringify(res, (k, v) => (k === 'edges' || k === 'sections' ? undefined : v), 1));
})().catch((e) => { console.error('FAIL', e); srv.close(); process.exit(1); });
