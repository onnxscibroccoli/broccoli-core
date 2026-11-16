// RoofMeasure lidar lane: roof pitch + ridge bearing from free USGS 3DEP lidar (EPT on AWS, no key).
// Same output schema as lidar/pitch.py.  ES module, works in browsers and Node >= 18.
//
//   import { estimatePitch, estimatePitchFromPoints, footprintRidgeFallback } from '../lidar/pitch.js';
//   const r = await estimatePitch(footprintGeoJSON, { lazPerf?, fetch?, datasets?, timeoutMs? });
//   // r = { pitch:'7/12', pitch_rise, pitch_factor, pitch_deg, ridge_bearing_deg, ridge_source,
//   //       roof_shape_guess, pitch_source, pitch_confidence, samples_n, ridges[], planes[], notes[] }
//
// Never throws for data problems: falls back to 6/12 (pitch_source:'default') and to the footprint
// long axis for ridge_bearing_deg (ridge_source:'footprint_long_axis').
// LAZ decoding uses laz-perf (Apache-2.0, WASM). Node: `npm i laz-perf@0.0.7`. Browser: loaded from
// jsDelivr unless you pass opts.lazPerf (an initialised laz-perf module).

export const EPT_BASE = 'https://s3-us-west-2.amazonaws.com/usgs-lidar-public';
export const DEFAULT_DATASETS = ['MA_CentralEastern_1_2021', 'MA_NE_CMGP_Sandy_Z19_A1_2015'];
const LAZPERF_CDN = new URL('../vendor/laz-perf/', import.meta.url).href; // bundled offline (android/bundle)
const LAZPERF_ESM = new URL('../vendor/laz-perf/laz-perf.mjs', import.meta.url).href; // bundled offline
const R = 6378137.0;
const D2R = Math.PI / 180, R2D = 180 / Math.PI;

// ------------------------------------------------------------ geometry
export function merc(lon, lat) {
  return [lon * D2R * R, Math.log(Math.tan(Math.PI / 4 + (lat * D2R) / 2)) * R];
}
function ringArea(r) { let a = 0; for (let i = 0; i < r.length - 1; i++) a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1]; return a / 2; }
export function extractRing(gj) {
  if (typeof gj === 'string') gj = JSON.parse(gj);
  if (!gj) return null;
  if (gj.type === 'FeatureCollection') { for (const f of gj.features) { const r = extractRing(f); if (r) return r; } return null; }
  if (gj.type === 'Feature') return extractRing(gj.geometry);
  if (gj.type === 'Polygon') return gj.coordinates[0];
  if (gj.type === 'MultiPolygon') return gj.coordinates.map(p => p[0]).sort((a, b) => Math.abs(ringArea(b)) - Math.abs(ringArea(a)))[0];
  return null;
}
function pointInRing(x, y, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi + 1e-300) + xi) inside = !inside;
  }
  return inside;
}
function distToRing(x, y, ring) {
  let best = Infinity;
  for (let i = 0; i < ring.length - 1; i++) {
    const [x1, y1] = ring[i], [x2, y2] = ring[i + 1]; const dx = x2 - x1, dy = y2 - y1, L = dx * dx + dy * dy;
    const t = L === 0 ? 0 : Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / L));
    best = Math.min(best, Math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)));
  }
  return best;
}
export function longAxisBearing(ringM) {
  const pts = ringM[0][0] === ringM.at(-1)[0] && ringM[0][1] === ringM.at(-1)[1] ? ringM.slice(0, -1) : ringM;
  let best = null;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
    const a = Math.atan2(y2 - y1, x2 - x1), c = Math.cos(a), s = Math.sin(a);
    const us = pts.map(([x, y]) => x * c + y * s), vs = pts.map(([x, y]) => -x * s + y * c);
    const w = Math.max(...us) - Math.min(...us), h = Math.max(...vs) - Math.min(...vs);
    if (w * h <= 0) continue;
    if (!best || w * h < best.area) best = { area: w * h, ang: w >= h ? a : a + Math.PI / 2 };
  }
  return best ? (((90 - best.ang * R2D) % 180) + 180) % 180 : null;
}
const angDiff180 = (a, b) => { const d = Math.abs(a - b) % 180; return Math.min(d, 180 - d); };
const angDiff360 = (a, b) => { const d = Math.abs(a - b) % 360; return Math.min(d, 360 - d); };

// ------------------------------------------------------------ pitch math
const riseFromDeg = d => 12 * Math.tan(d * D2R);
export function fmtPitch(rise) { const r = Math.round(rise * 2) / 2; return `${r}/12`; }
function fitPlane(P, idx) { // least squares z = a x + b y + c via normal equations
  let sxx = 0, sxy = 0, sx = 0, syy = 0, sy = 0, n = 0, sxz = 0, syz = 0, sz = 0;
  for (const i of idx) { const x = P[i][0], y = P[i][1], z = P[i][2]; sxx += x * x; sxy += x * y; sx += x; syy += y * y; sy += y; n++; sxz += x * z; syz += y * z; sz += z; }
  const M = [[sxx, sxy, sx], [sxy, syy, sy], [sx, sy, n]], v = [sxz, syz, sz];
  const det = m => m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
  const D = det(M); if (Math.abs(D) < 1e-12) return null;
  return [0, 1, 2].map(k => det(M.map((row, r) => row.map((val, c) => (c === k ? v[r] : val)))) / D);
}
function planeProps(a, b) {
  const slope = Math.atan(Math.hypot(a, b)) * R2D;
  const aspect = a || b ? ((Math.atan2(-a, -b) * R2D) % 360 + 360) % 360 : 0;
  return [slope, aspect];
}
function rng(seed) { let s = seed >>> 0 || 1; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }
function ransacPlanes(P, { maxPlanes = 6, thresh = 0.12, minFrac = 0.06, iters = 400, seed = 1 } = {}) {
  const rand = rng(seed); const n0 = P.length; let remaining = P.map((_, i) => i); const planes = [];
  const minN = Math.max(10, minFrac * n0);
  while (planes.length < maxPlanes && remaining.length >= Math.max(12, minFrac * n0)) {
    let bestIn = null;
    for (let it = 0; it < iters; it++) {
      const p1 = P[remaining[(rand() * remaining.length) | 0]], p2 = P[remaining[(rand() * remaining.length) | 0]], p3 = P[remaining[(rand() * remaining.length) | 0]];
      const u = [p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]], v = [p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]];
      let nx = u[1] * v[2] - u[2] * v[1], ny = u[2] * v[0] - u[0] * v[2], nz = u[0] * v[1] - u[1] * v[0];
      const nn = Math.hypot(nx, ny, nz); if (nn < 1e-9 || Math.abs(nz) / nn < 0.25) continue;
      nx /= nn; ny /= nn; nz /= nn;
      const inl = [];
      for (const i of remaining) { const q = P[i]; if (Math.abs((q[0] - p1[0]) * nx + (q[1] - p1[1]) * ny + (q[2] - p1[2]) * nz) < thresh) inl.push(i); }
      if (!bestIn || inl.length > bestIn.length) bestIn = inl;
    }
    if (!bestIn || bestIn.length < minN) break;
    let co = fitPlane(P, bestIn); if (!co) break;
    let cosS = Math.cos(Math.atan(Math.hypot(co[0], co[1])));
    const inl = remaining.filter(i => Math.abs(P[i][2] - (co[0] * P[i][0] + co[1] * P[i][1] + co[2])) * cosS < thresh);
    if (inl.length < minN) break;
    co = fitPlane(P, inl); if (!co) break;
    let ss = 0; for (const i of inl) ss += (P[i][2] - (co[0] * P[i][0] + co[1] * P[i][1] + co[2])) ** 2;
    const [slope, aspect] = planeProps(co[0], co[1]);
    planes.push({ n: inl.length, frac: inl.length / n0, slope_deg: slope, aspect_deg: aspect, rms_m: Math.sqrt(ss / inl.length) });
    const set = new Set(inl); remaining = remaining.filter(i => !set.has(i));
  }
  return planes;
}

/** Core analysis. P: array of [x_east_m, y_north_m, z_m] roof points; ringLocal: footprint in same metres. */
export function analyzePoints(P, ringLocal = null, longAxis = null) {
  const notes = []; const planes = ransacPlanes(P); if (!planes.length) return null;
  const sloped = planes.filter(p => p.slope_deg >= 4 && p.slope_deg <= 65), flat = planes.filter(p => p.slope_deg < 4);
  const totS = sloped.reduce((s, p) => s + p.frac, 0), totF = flat.reduce((s, p) => s + p.frac, 0), explained = totS + totF;
  const out = { planes };
  if (totF > totS && totF > 0.3) {
    const w = flat.reduce((s, p) => s + p.n, 0);
    return { ...out, pitch_deg: flat.reduce((s, p) => s + p.slope_deg * p.n, 0) / w, shape: 'flat', ridge: null, ridges: [], confidence: Math.min(0.9, 0.4 + 0.5 * explained), notes };
  }
  if (!sloped.length) return null;
  const order = [...sloped].sort((a, b) => a.slope_deg - b.slope_deg); const W = order.reduce((s, p) => s + p.n, 0);
  let acc = 0, pitchDeg = order.at(-1).slope_deg; for (const p of order) { acc += p.n / W; if (acc >= 0.5) { pitchDeg = p.slope_deg; break; } }
  let major = sloped.filter(p => p.frac >= 0.08); if (!major.length) major = sloped.slice(0, 1);
  const pairs = [];
  for (let i = 0; i < major.length; i++) for (let j = i + 1; j < major.length; j++) {
    const p = major[i], q = major[j];
    if (angDiff360(p.aspect_deg, q.aspect_deg) > 140) {
      const r1 = 2 * (((p.aspect_deg + 90) % 180)) * D2R, r2 = 2 * (((q.aspect_deg + 90) % 180)) * D2R;
      const r = (((Math.atan2(p.n * Math.sin(r1) + q.n * Math.sin(r2), p.n * Math.cos(r1) + q.n * Math.cos(r2)) * R2D) / 2) % 180 + 180) % 180;
      pairs.push({ bearing_deg: (Math.round(r * 10) / 10) % 180, n: p.n + q.n, slopes_deg: [+p.slope_deg.toFixed(1), +q.slope_deg.toFixed(1)] });
    }
  }
  pairs.sort((a, b) => b.n - a.n);
  const ridges = []; for (const pr of pairs) if (ridges.every(r => angDiff180(pr.bearing_deg, r.bearing_deg) > 20)) ridges.push(pr);
  let ridge;
  if (ridges.length) ridge = ridges[0].bearing_deg;
  else { const top = major.reduce((a, b) => (b.n > a.n ? b : a)); ridge = (top.aspect_deg + 90) % 180; notes.push('no opposite plane pair; ridge taken perpendicular to largest plane aspect'); }
  const dirs = []; for (const a of major.map(p => p.aspect_deg).sort((x, y) => x - y)) if (dirs.every(d => angDiff360(a, d) > 35)) dirs.push(a);
  const nverts = ringLocal ? ringLocal.length - 1 : 0;
  let shape = 'complex';
  if (dirs.length === 1) shape = 'shed_or_partial';
  else if (dirs.length === 2 && angDiff360(dirs[0], dirs[1]) > 140) shape = 'gable';
  else if (dirs.length >= 3 && nverts && nverts <= 5) shape = 'hip';
  const spread = Math.sqrt(sloped.reduce((s, p) => s + p.n * (p.slope_deg - pitchDeg) ** 2, 0) / W);
  let conf = 0.35 + 0.35 * Math.min(1, explained / 0.8) + 0.2 * Math.max(0, 1 - spread / 10) + 0.1 * Math.min(1, P.length / 400);
  if (longAxis != null) {
    if (angDiff180(ridge, longAxis) < 20) conf += 0.05;
    else notes.push(`primary lidar ridge ${ridge.toFixed(0)} deg differs from footprint long axis ${longAxis.toFixed(0)} deg (cross-gable/L wing or ridge across short side) - check before eave/rake`);
  }
  return { ...out, pitch_deg: pitchDeg, shape, ridge, ridges, confidence: Math.round(Math.min(conf, 0.95) * 100) / 100, notes };
}

function result({ pitch_deg = null, rise = null, ...kw } = {}) {
  if (rise == null) rise = pitch_deg != null ? riseFromDeg(pitch_deg) : 6;
  if (pitch_deg == null) pitch_deg = Math.atan(rise / 12) * R2D;
  return {
    pitch: fmtPitch(rise), pitch_rise: Math.round(rise * 100) / 100,
    pitch_factor: Math.round(Math.sqrt(1 + (rise / 12) ** 2) * 1e4) / 1e4, pitch_deg: Math.round(pitch_deg * 100) / 100,
    ridge_bearing_deg: null, ridge_source: null, roof_shape_guess: 'unknown', pitch_source: 'default',
    pitch_confidence: 0, samples_n: 0, ridges: [], planes: [], notes: [], ...kw,
  };
}

/** Synchronous, no network: footprint long-axis ridge + default 6/12. */
export function footprintRidgeFallback(footprintGeoJSON) {
  const ctx = prepare(footprintGeoJSON);
  if (!ctx) return result({ notes: ['no polygon in input; default 6/12'] });
  return result({ ...ctx.baseKw, notes: ['no lidar used; ridge = footprint long axis (heuristic), pitch default 6/12'] });
}
function prepare(footprintGeoJSON) {
  let ring = extractRing(footprintGeoJSON); if (!ring || ring.length < 4) return null;
  if (ring[0][0] !== ring.at(-1)[0] || ring[0][1] !== ring.at(-1)[1]) ring = [...ring, ring[0]];
  const lat0 = ring.reduce((s, p) => s + p[1], 0) / ring.length, k = Math.cos(lat0 * D2R);
  const ringM = ring.map(p => merc(p[0], p[1])); const [ox, oy] = ringM[0];
  const ringLocal = ringM.map(([x, y]) => [(x - ox) * k, (y - oy) * k]);
  const la = longAxisBearing(ringLocal);
  const baseKw = la == null ? {} : { ridge_bearing_deg: Math.round(la * 10) / 10, ridge_source: 'footprint_long_axis', footprint_long_axis_deg: Math.round(la * 10) / 10 };
  return { ring, ringM, ringLocal, k, ox, oy, longAxis: la, baseKw };
}

/** Roof points already in local metres -> result (for tests / other data sources). */
export function estimatePitchFromPoints(points, footprintGeoJSON = null, source = 'points') {
  const ctx = footprintGeoJSON ? prepare(footprintGeoJSON) : null;
  const an = analyzePoints(points, ctx?.ringLocal ?? null, ctx?.longAxis ?? null);
  if (!an) return result({ ...(ctx?.baseKw || {}), samples_n: points.length, notes: ['no plane fit; default 6/12'] });
  const kw = { ...(ctx?.baseKw || {}) };
  if (an.ridge != null) Object.assign(kw, { ridge_bearing_deg: (Math.round(an.ridge * 10) / 10) % 180, ridge_source: 'lidar_planes' });
  else if (an.shape === 'flat') Object.assign(kw, { ridge_bearing_deg: null, ridge_source: 'flat_roof_no_ridge' });
  return result({
    pitch_deg: an.pitch_deg, roof_shape_guess: an.shape, pitch_source: source, pitch_confidence: an.confidence,
    samples_n: points.length, ridges: an.ridges,
    planes: an.planes.map(p => ({ n: p.n, frac: +p.frac.toFixed(3), slope_deg: +p.slope_deg.toFixed(1), pitch: fmtPitch(riseFromDeg(p.slope_deg)), aspect_deg: +p.aspect_deg.toFixed(1), rms_m: +p.rms_m.toFixed(3) })),
    notes: an.notes, ...kw,
  });
}

// ------------------------------------------------------------ EPT + LAZ
let _lazPerfPromise = null;
async function getLazPerf(opts) {
  if (opts.lazPerf) return opts.lazPerf;
  if (!_lazPerfPromise) _lazPerfPromise = (async () => {
    let mod;
    if (typeof window !== 'undefined') mod = await import(LAZPERF_ESM);
    else { try { mod = await import('laz-perf'); } catch { mod = await import(LAZPERF_ESM); } }
    const create = mod.createLazPerf || mod.create || mod.default?.createLazPerf || mod.default;
    return typeof window !== 'undefined' ? create({ locateFile: f => LAZPERF_CDN + f }) : create();
  })();
  return _lazPerfPromise;
}
function decodeLaz(LP, buf, bbox) { // returns array of [x,y,z,cls] in bbox (EPSG:3857)
  const dv = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);
  const sx = dv.getFloat64(131, true), sy = dv.getFloat64(139, true), sz = dv.getFloat64(147, true);
  const oxx = dv.getFloat64(155, true), oyy = dv.getFloat64(163, true), ozz = dv.getFloat64(171, true);
  const filePtr = LP._malloc(buf.byteLength); LP.HEAPU8.set(buf, filePtr);
  const laszip = new LP.LASZip(); const out = [];
  try {
    laszip.open(filePtr, buf.byteLength);
    const len = laszip.getPointLength(), fmt = laszip.getPointFormat() & 0x3f, count = laszip.getCount();
    const pp = LP._malloc(len);
    try {
      for (let i = 0; i < count; i++) {
        laszip.getPoint(pp);
        const v = new DataView(LP.HEAPU8.buffer, pp, len);
        const x = v.getInt32(0, true) * sx + oxx, y = v.getInt32(4, true) * sy + oyy;
        if (x < bbox[0] || x > bbox[2] || y < bbox[1] || y > bbox[3]) continue;
        const z = v.getInt32(8, true) * sz + ozz;
        const cls = fmt >= 6 ? v.getUint8(16) : v.getUint8(15) & 0x1f;
        out.push([x, y, z, cls, v.getUint16(12, true)]); // intensity (uint16, offset 12 in all LAS point formats)
      }
    } finally { LP._free(pp); }
  } finally { laszip.delete(); LP._free(filePtr); }
  return out;
}
async function getJSON(f, url, ms) { const r = await f(url, { signal: AbortSignal.timeout(ms) }); if (!r.ok) throw new Error(`HTTP ${r.status} ${url}`); return r.json(); }
export async function fetchEptPoints(dataset, bbox, opts = {}) {
  const f = opts.fetch || globalThis.fetch, ms = opts.timeoutMs || 30000, base = `${EPT_BASE}/${dataset}`;
  const meta = await getJSON(f, `${base}/ept.json`, ms);
  const [bx0, by0, bz0, bx1] = meta.bounds, cb = meta.boundsConforming, W = bx1 - bx0;
  if (bbox[2] < cb[0] || bbox[0] > cb[3] || bbox[3] < cb[1] || bbox[1] > cb[4]) return null;
  const hier = {}; Object.assign(hier, await getJSON(f, `${base}/ept-hierarchy/0-0-0-0.json`, ms));
  const wanted = [], stack = ['0-0-0-0'], zr = [-100, 600];
  while (stack.length) {
    const key = stack.pop(); if (!(key in hier)) continue;
    if (hier[key] === -1) { Object.assign(hier, await getJSON(f, `${base}/ept-hierarchy/${key}.json`, ms)); if (hier[key] === -1) continue; }
    const [d, x, y, z] = key.split('-').map(Number), s = W / 2 ** d;
    const nx0 = bx0 + x * s, ny0 = by0 + y * s, nz0 = bz0 + z * s;
    if (nx0 > bbox[2] || nx0 + s < bbox[0] || ny0 > bbox[3] || ny0 + s < bbox[1] || nz0 > zr[1] || nz0 + s < zr[0]) continue;
    if (hier[key] > 0) wanted.push(key);
    for (const dx of [0, 1]) for (const dy of [0, 1]) for (const dz of [0, 1]) stack.push(`${d + 1}-${2 * x + dx}-${2 * y + dy}-${2 * z + dz}`);
  }
  const LP = await getLazPerf(opts);
  const parts = await Promise.all(wanted.map(async key => {
    const r = await f(`${base}/ept-data/${key}.laz`, { signal: AbortSignal.timeout(ms) }); if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return decodeLaz(LP, new Uint8Array(await r.arrayBuffer()), bbox);
  }));
  return { points: parts.flat(), nodes: wanted.length };
}

/** Main API: footprint GeoJSON (EPSG:4326) -> pitch result. */
export async function estimatePitch(footprintGeoJSON, opts = {}) {
  const ctx = prepare(footprintGeoJSON);
  if (!ctx) return result({ notes: ['no polygon in input; default 6/12'] });
  const { ringM, ringLocal, k, ox, oy, longAxis, baseKw } = ctx; const inset = opts.insetM ?? 0.6;
  const xs = ringM.map(p => p[0]), ys = ringM.map(p => p[1]), pad = (opts.padM ?? 6) / k; // 0.1.7.6: 6 m (was 1.5) for outline registration + ground
  const bbox = [Math.min(...xs) - pad, Math.min(...ys) - pad, Math.max(...xs) + pad, Math.max(...ys) + pad];
  const notes = []; let pts = null, used = null;
  for (const ds of opts.datasets || DEFAULT_DATASETS) {
    try {
      const r = await fetchEptPoints(ds, bbox, opts);
      if (!r) { notes.push(`${ds}: footprint outside dataset bounds`); continue; }
      if (!r.points.length) { notes.push(`${ds}: no points in bbox`); continue; }
      pts = r.points; used = ds; notes.push(`${ds}: ${pts.length} points in bbox from ${r.nodes} EPT nodes`); break;
    } catch (e) { notes.push(`${ds}: fetch/decode failed: ${e.message || e}`); }
  }
  if (!pts) return result({ ...baseKw, notes: [...notes, 'no lidar points; default 6/12'] });
  const L = pts.map(([x, y, z, c, it]) => [(x - ox) * k, (y - oy) * k, z, c, it]);
  const inside = L.filter(([x, y]) => pointInRing(x, y, ringLocal) && distToRing(x, y, ringLocal) >= inset);
  const ground = L.filter(p => p[3] === 2).map(p => p[2]).sort((a, b) => a - b);
  const gz = ground.length ? ground[ground.length >> 1] : null;
  let P = inside.filter(p => p[3] === 6);
  if (P.length >= 30) notes.push(`using ${P.length} class-6 (building) points inside footprint (inset ${inset} m)`);
  else { P = inside.filter(p => ![2, 7, 9, 18].includes(p[3]) && (gz == null || p[2] > gz + 2)); notes.push(`class-6 sparse; using ${P.length} non-ground points >2 m above ground`); }
  P = P.map(p => [p[0], p[1], p[2]]);
  const dataUrl = `${EPT_BASE}/${used}/ept.json`;
  if (P.length < 25) return result({ ...baseKw, samples_n: P.length, data_url: dataUrl, notes: [...notes, 'too few roof points; default 6/12'] });
  const r = estimatePitchFromPoints(P, footprintGeoJSON, `lidar:usgs_3dep_ept:${used}`);
  const out = r.pitch_source === 'default' ? { ...r, data_url: dataUrl, notes: [...notes, ...r.notes] } : { ...r, data_url: dataUrl, ground_z_m: gz, notes: [...notes, ...r.notes] };
  // 0.1.7.3: keep the roof points (local metres) and the frame for per-facet plane fits (lidar/facetfit.js).
  // Non-enumerable so they never end up in JSON exports or reports.
  Object.defineProperty(out, 'points_local', { value: P, enumerable: false });
  Object.defineProperty(out, 'frame', { value: { ox, oy, k, merc: true }, enumerable: false });
  // 0.1.7.3: full roof cloud for lidar/roofseg.js: building points with NO inset, plus a 1.2 m buffer outside the
  // footprint (eave overhangs / narrow lower strips), with class and intensity: [x, y, z, cls, intensity, insideFootprint].
  const PF = L.filter(p => p[3] === 6 || (P.length < 30 && ![2, 7, 9, 18].includes(p[3]) && (gz == null || p[2] > gz + 2)))
    .map(p => { const ins = pointInRing(p[0], p[1], ringLocal); return (ins || distToRing(p[0], p[1], ringLocal) <= 1.2) ? [p[0], p[1], p[2], p[3], p[4] || 0, ins ? 1 : 0] : null; })
    .filter(Boolean);
  Object.defineProperty(out, 'points_full', { value: PF, enumerable: false });
  Object.defineProperty(out, 'ring_local', { value: ringLocal, enumerable: false });
  // 0.1.7.6: every building / elevated point in the padded bbox (outline registration vs the roofprint, lidar building extent)
  Object.defineProperty(out, 'points_bbox', { value: L.filter(p => p[3] === 6 || (![2, 7, 9, 18].includes(p[3]) && gz != null && p[2] > gz + 2)).map(p => [p[0], p[1], p[2], p[3]]), enumerable: false });
  Object.defineProperty(out, 'ground_points', { value: L.filter(p => p[3] === 2).map(p => [p[0], p[1], p[2]]), enumerable: false });
  Object.defineProperty(out, 'class_counts', { value: L.reduce((m, p) => (m[p[3]] = (m[p[3]] || 0) + 1, m), {}), enumerable: false });
  return out;
}
