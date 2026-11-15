/*!
 * overture.js — tiny dependency-free reader for Overture Maps buildings PMTiles (v3) + MVT decoder.
 * Range-reads https://tiles.overturemaps.org/<release>/buildings.pmtiles (CORS *, no key).
 * Caveat: z14 vector tiles quantize to ~0.6 m at 42°N (extent 4096) and clip at tile edges,
 * so Overture footprints are approximate — use MassGIS first in MA.
 * UMD: window.RoofOverture or require('./overture.js').
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('../core/roofcalc.js'));
  else root.RoofOverture = factory(root.RoofCalc);
})(typeof self !== 'undefined' ? self : this, function (RC) {
  'use strict';
  var DEFAULT_URL = 'https://tiles.overturemaps.org/2026-10-21.0/buildings.pmtiles';
  var cache = {};

  function rangeGet(url, off, len) {
    return fetch(url, { headers: { Range: 'bytes=' + off + '-' + (off + len - 1) } }).then(function (r) {
      if (r.status !== 206 && r.status !== 200) throw new Error('PMTiles HTTP ' + r.status);
      return r.arrayBuffer();
    }).then(function (b) { return new Uint8Array(b); });
  }
  function decompress(bytes, comp) {
    if (comp === 1 || comp === 0) return Promise.resolve(bytes);
    if (comp !== 2) return Promise.reject(new Error('unsupported compression ' + comp));
    if (typeof DecompressionStream === 'undefined') return Promise.reject(new Error('no DecompressionStream'));
    var ds = new DecompressionStream('gzip');
    var stream = new Blob([bytes]).stream().pipeThrough(ds);
    return new Response(stream).arrayBuffer().then(function (b) { return new Uint8Array(b); });
  }
  function u64(b, o) { var lo = b[o] | b[o + 1] << 8 | b[o + 2] << 16 | (b[o + 3] << 24 >>> 0); lo >>>= 0; var hi = b[o + 4] | b[o + 5] << 8 | b[o + 6] << 16 | (b[o + 7] << 24 >>> 0); hi >>>= 0; return hi * 4294967296 + lo; }
  function parseHeader(b) {
    var magic = String.fromCharCode.apply(null, b.subarray(0, 7));
    if (magic !== 'PMTiles' || b[7] !== 3) throw new Error('not a PMTiles v3 archive');
    return { rootOff: u64(b, 8), rootLen: u64(b, 16), leafOff: u64(b, 40), dataOff: u64(b, 56),
      icomp: b[97], tcomp: b[98], ttype: b[99], minZ: b[100], maxZ: b[101] };
  }
  function Reader(b) { this.b = b; this.p = 0; }
  Reader.prototype.varint = function () {
    var r = 0, m = 1, c;
    do { c = this.b[this.p++]; r += (c & 0x7f) * m; m *= 128; } while (c & 0x80);
    return r;
  };
  function parseDir(b) {
    var rd = new Reader(b), n = rd.varint(), e = [], i, last = 0;
    for (i = 0; i < n; i++) { last += rd.varint(); e.push({ id: last, off: 0, len: 0, run: 0 }); }
    for (i = 0; i < n; i++) e[i].run = rd.varint();
    for (i = 0; i < n; i++) e[i].len = rd.varint();
    for (i = 0; i < n; i++) { var v = rd.varint(); e[i].off = (v === 0 && i > 0) ? e[i - 1].off + e[i - 1].len : v - 1; }
    return e;
  }
  function zxyToTileId(z, x, y) {
    var acc = 0; for (var t = 0; t < z; t++) acc += Math.pow(4, t);
    var n = Math.pow(2, z), d = 0, xy = [x, y];
    for (var s = n / 2; s >= 1; s /= 2) {
      var rx = (xy[0] & s) > 0 ? 1 : 0, ry = (xy[1] & s) > 0 ? 1 : 0;
      d += s * s * ((3 * rx) ^ ry);
      if (ry === 0) { if (rx === 1) { xy[0] = s - 1 - xy[0]; xy[1] = s - 1 - xy[1]; } var tmp = xy[0]; xy[0] = xy[1]; xy[1] = tmp; }
    }
    return acc + d;
  }
  function findEntry(entries, id) {
    var lo = 0, hi = entries.length - 1;
    while (lo <= hi) {
      var mid = (lo + hi) >> 1, c = id - entries[mid].id;
      if (c > 0) lo = mid + 1; else if (c < 0) hi = mid - 1; else return entries[mid];
    }
    if (hi >= 0) { var e = entries[hi]; if (e.run === 0) return e; if (id - e.id < e.run) return e; }
    return null;
  }
  function open(url) {
    if (cache[url]) return cache[url];
    cache[url] = rangeGet(url, 0, 16384).then(function (b) {
      var h = parseHeader(b);
      return decompress(b.subarray(h.rootOff, h.rootOff + h.rootLen), h.icomp).then(function (d) {
        h.root = parseDir(d); h.url = url; h.leaves = {}; return h;
      });
    });
    return cache[url];
  }
  function getTile(url, z, x, y) {
    return open(url).then(function (h) {
      var id = zxyToTileId(z, x, y);
      function walk(entries, depth) {
        var e = findEntry(entries, id);
        if (!e) return null;
        if (e.run > 0) return rangeGet(url, h.dataOff + e.off, e.len).then(function (t) { return decompress(t, h.tcomp); });
        if (depth > 3) throw new Error('directory too deep');
        var key = e.off + ':' + e.len;
        var p = h.leaves[key] || (h.leaves[key] = rangeGet(url, h.leafOff + e.off, e.len).then(function (b) { return decompress(b, h.icomp); }).then(parseDir));
        return p.then(function (le) { return walk(le, depth + 1); });
      }
      return walk(h.root, 0);
    });
  }

  // ------------------------------------------------------------ MVT decode (polygons only)
  function readMsg(b, start, end, cb) {
    var rd = new Reader(b); rd.p = start;
    while (rd.p < end) {
      var tag = rd.varint(), f = Math.floor(tag / 8), w = tag & 7;
      if (w === 0) cb(f, w, rd.varint());
      else if (w === 2) { var l = rd.varint(), s = rd.p; cb(f, w, s, s + l); rd.p = s + l; }
      else if (w === 5) { rd.p += 4; } else if (w === 1) { rd.p += 8; } else throw new Error('bad wire type ' + w);
    }
  }
  function packed(b, s, e) { var rd = new Reader(b), out = []; rd.p = s; while (rd.p < e) out.push(rd.varint()); return out; }
  function zz(n) { return (n % 2 === 1) ? -(n + 1) / 2 : n / 2; }
  function decodeRings(cmds) {
    var rings = [], cur = null, x = 0, y = 0, i = 0;
    while (i < cmds.length) {
      var c = cmds[i++], id = c & 7, cnt = c >> 3;
      if (id === 1 || id === 2) {
        for (var k = 0; k < cnt; k++) {
          x += zz(cmds[i++]); y += zz(cmds[i++]);
          if (id === 1) { cur = [[x, y]]; rings.push(cur); } else cur.push([x, y]);
        }
      } else if (id === 7) { if (cur) cur.push(cur[0].slice()); }
    }
    return rings;
  }
  /** Decode MVT bytes -> array of {layer, props, rings:[[[px,py]...]], extent} for polygon features. */
  function decodeMVT(b) {
    var feats = [];
    readMsg(b, 0, b.length, function (f, w, s, e) {
      if (f !== 3 || w !== 2) return;
      var name = '', extent = 4096, raw = [], keys = [], vals = [];
      readMsg(b, s, e, function (lf, lw, ls, le) {
        if (lf === 1) name = new TextDecoder().decode(b.subarray(ls, le));
        else if (lf === 5) extent = ls;
        else if (lf === 3) keys.push(new TextDecoder().decode(b.subarray(ls, le)));
        else if (lf === 4) { var v = null; readMsg(b, ls, le, function (vf, vw, vs, ve) { v = vw === 2 ? new TextDecoder().decode(b.subarray(vs, ve)) : vs; }); vals.push(v); }
        else if (lf === 2) raw.push([ls, le]);
      });
      raw.forEach(function (r) {
        var type = 0, geom = null, tags = [];
        readMsg(b, r[0], r[1], function (ff, fw, fs, fe) {
          if (ff === 3) type = fs; else if (ff === 4) geom = packed(b, fs, fe); else if (ff === 2) tags = packed(b, fs, fe);
        });
        if (type !== 3 || !geom) return;
        var props = {}; for (var t = 0; t + 1 < tags.length; t += 2) props[keys[tags[t]]] = vals[tags[t + 1]];
        feats.push({ layer: name, props: props, rings: decodeRings(geom), extent: extent });
      });
    });
    return feats;
  }

  /** Fetch Overture buildings around lon/lat, return pick result like RoofSources.fetchMassGIS. */
  function fetchOverture(lon, lat, opts) {
    var o = opts || {}, url = o.overtureUrl || DEFAULT_URL, z = 14;
    var w = RC.lonLatToWorld(lon, lat, z), tx = Math.floor(w[0] / 256), ty = Math.floor(w[1] / 256);
    return getTile(url, z, tx, ty).then(function (bytes) {
      if (!bytes) return null;
      var feats = decodeMVT(bytes).filter(function (f) { return /building/.test(f.layer) && !/part/.test(f.layer); });
      var gj = [];
      feats.forEach(function (f) {
        f.rings.forEach(function (r) {
          // exterior rings have positive shoelace area in MVT (y-down) coords
          var a = 0; for (var i = 0; i < r.length - 1; i++) a += r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1];
          if (a <= 0 || r.length < 4) return;
          var ring = r.map(function (p) { return RC.worldToLonLat((tx + p[0] / f.extent) * 256, (ty + p[1] / f.extent) * 256, z); });
          gj.push({ type: 'Feature', properties: f.props, geometry: { type: 'Polygon', coordinates: [ring] } });
        });
      });
      var S = (typeof RoofSources !== 'undefined') ? RoofSources : require('./sources.js');
      var p = S.pickBuilding(gj, [lon, lat], o.maxFt, o.minSqft);
      if (p) { p.source = 'Overture Maps buildings (PMTiles z14, simplified) id ' + (p.feature.properties.id || '?'); p.url = url; }
      return p;
    });
  }

  return { DEFAULT_URL: DEFAULT_URL, zxyToTileId: zxyToTileId, parseDir: parseDir, decodeMVT: decodeMVT, getTile: getTile, fetchOverture: fetchOverture };
});
