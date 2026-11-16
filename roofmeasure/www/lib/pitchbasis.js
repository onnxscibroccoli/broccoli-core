/* SPDX-License-Identifier: MIT
 * Expose the slope used for reported area without conflating it with the base selector
 * or promoting manually adjusted 3-D facades to field-measured roof pitch.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.RoofPitchBasis = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  function describe(r) {
    var base = String(r.pitch || 'not provided'), source = String(r.pitch_source || 'not provided');
    if (!r.per_facet_pitch_used) return { display: base, source: source, base: base, mode: 'single', verified: false };
    var f = (r.facets || []), used = f.filter(function (x) { return x.pitch_source && x.pitch_source.indexOf('single pitch') !== 0; });
    if (!f.length || !used.length) return { display: base, source: source, base: base, mode: 'single', verified: false };
    var pitches = Array.from(new Set(f.map(function (x) { return x.pitch; })));
    var all = used.length === f.length, display = all && pitches.length === 1 ? pitches[0] : 'mixed (see facets)';
    var users = used.filter(function (x) { return x.pitch_source.indexOf('user edit') === 0; }).length;
    var text = users ? 'manual 3-D facet override (' + users + '/' + f.length + ' facets)' : 'lidar per-facet estimate';
    if (users && used.length > users) text += ' + lidar facet estimates';
    if (!all) text += ' + base pitch on ' + (f.length - used.length) + ' facet(s)';
    return { display: display, source: text + '; physical slope NOT_PROVEN without independent verification',
      base: base, mode: 'per-facet', verified: false };
  }
  return { describe: describe };
});
