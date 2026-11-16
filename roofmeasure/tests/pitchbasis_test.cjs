// SPDX-License-Identifier: MIT
const assert = require('node:assert/strict');
const B = require('../www/lib/pitchbasis.js');
const r = {pitch:'6/12',pitch_source:'manual',per_facet_pitch_used:true,facets:[
 {id:'FA',pitch:'12/12',pitch_source:'user edit (3-D editor)'},
 {id:'FB',pitch:'12/12',pitch_source:'user edit (3-D editor)'}]};
const x=B.describe(r);
assert.equal(x.display,'12/12');assert.match(x.source,/manual 3-D facet override/);assert.equal(x.verified,false);
const y=B.describe({...r,per_facet_pitch_used:false});assert.equal(y.display,'6/12');
const z=B.describe({...r,facets:[r.facets[0],{id:'FB',pitch:'6/12',pitch_source:'single pitch (no usable lidar fit)'}]});
assert.equal(z.display,'mixed (see facets)');assert.match(z.source,/base pitch/);
assert.equal(r.pitch,'6/12');
console.log('pitch calculation basis and manual provenance PASS');
