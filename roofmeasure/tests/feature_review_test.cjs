// SPDX-License-Identifier: MIT
const assert = require('node:assert/strict');
const review = require('../www/lib/feature-review.js');
const data = () => ({ ortho_patches: [
  {key:'O0',centroid_lonlat:[-70.1,42.1],approx_w_ft:6,approx_h_ft:5,angle_deg:32,source:'ortho'},
  {key:'O1',centroid_lonlat:[-70.2,42.2],approx_w_ft:4,approx_h_ft:2,angle_deg:-20,source:'ortho'}],
  roof_features: {skylights:[{key:'O0',centroid_lonlat:[-70.1,42.1],w_ft:6,h_ft:5,angle_deg:32,counted:false}],
    decks: [],dormers:[],rejected:[{key:'O1',reason:'axis gate'}],counts:{skylights:0}}});
const r = data(); const prior = JSON.stringify(r.ortho_patches);
const f = review.apply(r, {featureReviews:{O0:{kind:'chimney'},O1:{kind:'skylight',rotate90:true}},
  featuresAdded:[{type:'chimney',centroid_lonlat:[-70.3,42.3]}]});
assert.equal(f.chimneys.length,2);assert.equal(f.vents.length,0);assert.equal(f.skylights.length,1);
assert.equal(f.skylights[0].angle_deg,70);assert.equal(f.counts.skylights,1);
assert.equal(f.rejected.length,0);assert.equal(f.skylights[0].source.includes('user-identified'),true);
assert.equal(JSON.stringify(r.ortho_patches),prior);
const g=review.apply(data(),{});assert.equal(g.skylights.length,1);assert.equal(g.chimneys.length,0);
const h=review.apply(data(),{featureReviews:{O0:{kind:'auto',rotate90:true}}});
assert.equal(h.skylights[0].angle_deg,122);
const z=review.apply(data(),{featureReviews:{O0:{kind:'ignore'}}});assert.equal(z.skylights.length,0);
console.log('feature review classification/rotation/markers FAIL-CLOSED PASS');
