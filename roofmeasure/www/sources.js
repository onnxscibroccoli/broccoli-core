/*!
 * sources.js — free footprint / geocoder fetchers for RoofMeasure (UMD; browser fetch or Node >= 18).
 * Depends on RoofCalc (core/roofcalc.js) for geometry. No API keys.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('../core/roofcalc.js'));
  else root.RoofSources = factory(root.RoofCalc);
})(typeof self !== 'undefined' ? self : this, function (RC) {
  'use strict';
  var ENDPOINTS = {
    massgisBuildings: 'https://services1.arcgis.com/hGdibHYSPO59RG1h/arcgis/rest/services/Building_Structures/FeatureServer/0/query',
    overpass: ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'],
    massgisGeocoder: 'https://arcgisserver.digital.mass.gov/arcgisserver/rest/services/MassGISStatewideGeocodeService/GeocodeServer/findAddressCandidates',
    censusGeocoder: 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress',
    nominatim: 'https://nominatim.openstreetmap.org/search'
  };

  function qs(o) { return Object.keys(o).map(function (k) { return encodeURIComponent(k) + '=' + encodeURIComponent(o[k]); }).join('&'); }
  function withTimeout(p, ms) {
    return Promise.race([p, new Promise(function (_, rej) { setTimeout(function () { rej(new Error('timeout ' + ms + 'ms')); }, ms); })]);
  }
  function getJSON(url, opts) {
    return withTimeout(fetch(url, opts), (opts && opts.timeoutMs) || 20000).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + url.split('?')[0]);
      return r.json();
    });
  }

  function pointInRing(pt, ring) {
    var x = pt[0], y = pt[1], inside = false;
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var xi = ring[i][0], yi = ring[i][1], xj = ring[j][0], yj = ring[j][1];
      if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) inside = !inside;
    }
    return inside;
  }
  /** Distance (ft) from pt to ring boundary, 0 if inside. */
  function distToRingFt(pt, ring) {
    if (pointInRing(pt, ring)) return 0;
    var f = RC.localFrame(pt[0], pt[1]), P = ring.map(f.toXY), best = Infinity;
    for (var i = 0; i < P.length; i++) {
      var a = P[i], b = P[(i + 1) % P.length], dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy;
      var t = L2 ? Math.max(0, Math.min(1, -(a[0] * dx + a[1] * dy) / L2)) : 0;
      best = Math.min(best, Math.hypot(a[0] + t * dx, a[1] + t * dy));
    }
    return best;
  }
  /** Ruling #6: pick the polygon containing pt, else the nearest within maxFt (default 98.4 ft = 30 m).
   *  Optional minSqft (default 0 = off) prefers the nearest building at least that big (skip sheds). */
  function pickBuilding(features, pt, maxFt, minSqft) {
    var lim = maxFt == null ? 98.4 : maxFt, minA = minSqft == null ? 0 : minSqft, list = [];  // ruling #6: contain, else nearest within 30 m
    (features || []).forEach(function (ft) {
      if (!ft.geometry) return;
      var ring = RC.extractRing(ft.geometry);
      list.push({ ft: ft, d: distToRingFt(pt, ring), a: RC.areaSqft(ring) });
    });
    list.sort(function (x, y) { return x.d - y.d; });
    var near = list.filter(function (c) { return c.d <= lim; });
    if (!near.length) return null;
    var best = near[0].d === 0 ? near[0] : (near.filter(function (c) { return c.a >= minA; })[0] || near[0]);
    return { feature: best.ft, distance_ft: best.d, contains: best.d === 0, area_sqft: best.a, candidates: list.length,
      skipped_smaller: best !== near[0] };
  }
  function envelope(lon, lat, radiusM) {
    var dLat = radiusM / 111320, dLon = radiusM / (111320 * Math.cos(lat * Math.PI / 180));
    return [lon - dLon, lat - dLat, lon + dLon, lat + dLat];
  }

  /** MassGIS Building Structures (2-D roofprints). Returns pick result with .source. */
  function fetchMassGIS(lon, lat, opts) {
    var o = opts || {}, e = envelope(lon, lat, o.radiusM || 45);
    var url = ENDPOINTS.massgisBuildings + '?' + qs({
      geometry: e.join(','), geometryType: 'esriGeometryEnvelope', inSR: 4326, spatialRel: 'esriSpatialRelIntersects',
      outFields: 'STRUCT_ID,AREA_SQ_FT,SOURCE,SOURCETYPE,SOURCEDATE,TOWN_ID', outSR: 4326, f: 'geojson'
    });
    return getJSON(url, o).then(function (fc) {
      if (fc.error) throw new Error('MassGIS error: ' + JSON.stringify(fc.error));
      var p = pickBuilding(fc.features, [lon, lat], o.maxFt, o.minSqft);
      if (!p) return null;
      p.source = 'MassGIS Building Structures (2-D) STRUCT_ID ' + (p.feature.properties.STRUCT_ID || '?') +
        (p.feature.properties.SOURCEDATE ? ', source date ' + p.feature.properties.SOURCEDATE : '');
      p.sourceType = p.feature.properties.SOURCETYPE || 'ROOFPRINT';
      p.url = url;
      return p;
    });
  }

  /** OSM buildings via Overpass (ODbL). Runtime fallback outside MA / when MassGIS is down. */
  function fetchOverpass(lon, lat, opts) {
    var o = opts || {}, r = o.radiusM || 40;
    var q = '[out:json][timeout:20];(way["building"](around:' + r + ',' + lat + ',' + lon + '););out geom;';
    var urls = ENDPOINTS.overpass.slice();
    function tryNext() {
      var u = urls.shift();
      if (!u) return Promise.reject(new Error('all Overpass endpoints failed'));
      return getJSON(u + '?data=' + encodeURIComponent(q), o).then(function (d) {
        var feats = (d.elements || []).filter(function (el) { return el.geometry && el.geometry.length >= 4; }).map(function (el) {
          return { type: 'Feature', properties: { osm_id: el.id, building: el.tags && el.tags.building },
            geometry: { type: 'Polygon', coordinates: [el.geometry.map(function (g) { return [g.lon, g.lat]; })] } };
        });
        var p = pickBuilding(feats, [lon, lat], o.maxFt, o.minSqft);
        if (p) { p.source = 'OpenStreetMap (Overpass) way ' + p.feature.properties.osm_id; p.url = u;
          p.warning = 'OSM footprint: community-traced wall outline, may be outdated or misaligned. Verify on imagery.'; }
        return p;
      }).catch(function (e) { if (urls.length) return tryNext(); throw e; });
    }
    return tryNext();
  }

  /** Ruling #8 chain: MassGIS -> Overture -> OSM Overpass (OSM result carries a warning). */
  function fetchFootprint(lon, lat, opts) {
    var log = [];
    var chain = [['MassGIS', fetchMassGIS]];
    var ov = (opts && opts.overture) || (typeof RoofOverture !== 'undefined' && RoofOverture.fetchOverture) ||
      (typeof module === 'object' && (function () { try { return require('./overture.js').fetchOverture; } catch (e) { return null; } })());
    if (ov && !(opts && opts.noOverture)) chain.push(['Overture', ov]);
    chain.push(['OSM Overpass', fetchOverpass]);
    var i = 0;
    function next() {
      if (i >= chain.length) return Promise.resolve({ result: null, log: log });
      var c = chain[i++];
      return c[1](lon, lat, opts).then(function (p) {
        if (p) { log.push(c[0] + ': hit (' + p.distance_ft.toFixed(1) + ' ft from click, ' + p.candidates + ' candidates)');
          if (p.warning) log.push('WARNING: ' + p.warning); return { result: p, log: log }; }
        log.push(c[0] + ': no building near point'); return next();
      }, function (e) { log.push(c[0] + ': ' + e.message); return next(); });
    }
    return next();
  }

  /** US Census one-line geocoder (free, US only). Note: no CORS headers in browsers -> Nominatim fallback. */
  function geocodeCensus(address, opts) {
    var url = ENDPOINTS.censusGeocoder + '?' + qs({ address: address, benchmark: 'Public_AR_Current', format: 'json' });
    return getJSON(url, opts).then(function (d) {
      var m = d.result && d.result.addressMatches && d.result.addressMatches[0];
      return m ? { lon: m.coordinates.x, lat: m.coordinates.y, label: m.matchedAddress, source: 'US Census Geocoder' } : null;
    });
  }
  function geocodeNominatim(address, opts) {
    var url = ENDPOINTS.nominatim + '?' + qs({ q: address, format: 'jsonv2', limit: 1, countrycodes: 'us' });
    return getJSON(url, opts).then(function (d) {
      return d && d[0] ? { lon: +d[0].lon, lat: +d[0].lat, label: d[0].display_name, source: 'OSM Nominatim' } : null;
    });
  }
  /** MassGIS statewide geocoder (MA Master Address points — usually lands on the building). CORS ok. */
  function geocodeMassGIS(address, opts) {
    var url = ENDPOINTS.massgisGeocoder + '?' + qs({ SingleLine: address, outSR: 4326, maxLocations: 1, f: 'json' });
    return getJSON(url, opts).then(function (d) {
      var c = d.candidates && d.candidates[0];
      return c && c.score >= 80 ? { lon: c.location.x, lat: c.location.y, label: c.address, score: c.score, source: 'MassGIS Statewide Geocoder' } : null;
    });
  }
  /** MassGIS -> US Census -> Nominatim. */
  function geocode(address, opts) {
    var chain = [geocodeMassGIS, geocodeCensus, geocodeNominatim];
    function next(i) {
      if (i >= chain.length) return Promise.resolve(null);
      return chain[i](address, opts).catch(function () { return null; }).then(function (r) { return r || next(i + 1); });
    }
    return next(0);
  }

  return { ENDPOINTS: ENDPOINTS, pointInRing: pointInRing, distToRingFt: distToRingFt, pickBuilding: pickBuilding,
    fetchMassGIS: fetchMassGIS, fetchOverpass: fetchOverpass, fetchFootprint: fetchFootprint,
    geocode: geocode, geocodeMassGIS: geocodeMassGIS, geocodeCensus: geocodeCensus, geocodeNominatim: geocodeNominatim };
});
