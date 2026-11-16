// SPDX-License-Identifier: MIT
'use strict';
const assert = require('node:assert/strict');
const lean = require('../www/lib/featurelean.js');
const ring = [[0,0],[12,0],[12,12],[0,12]];
const pts = Array.from({length:24}, (_,i) => [i%2 ? 0.6 : 11.4, 0.5+(i%12), 38, 6, 80, 1]);
const L = {ground_z_m:30, ring_local:ring, points_full:pts};
const good = {applied:true, confidence:'high', dx_m:4, dy_m:-2};
const geom = [[-70,42],[-70.0001,42]];
const r = {decks:[{source:'USGS 3DEP lidar low-slope plane P3', z_m:40, outline_lonlat:geom}],
  dormers:[{source:'lidar',z_m:42},{source:'user',z_m:45}]};
const before = JSON.stringify(r.decks[0].outline_lonlat);
const out = lean.annotate(r,L,good);
assert.equal(out.applied,2);
assert.equal(out.baseline.source,'lidar edge-return 35th percentile');
assert.deepEqual([r.decks[0].overlay_lean.dx_m,r.decks[0].overlay_lean.dy_m],[1,-0.5]);
assert.deepEqual([r.dormers[0].overlay_lean.dx_m,r.dormers[0].overlay_lean.dy_m],[2,-1]);
assert.equal(r.dormers[1].overlay_lean,undefined);
assert.equal(JSON.stringify(r.decks[0].outline_lonlat),before,'must never mutate measured geometry');
assert.equal(lean.estimate({applied:false,confidence:'high',dx_m:4,dy_m:0},out.baseline,40),null);
assert.equal(lean.estimate({applied:true,confidence:'low',dx_m:4,dy_m:0},out.baseline,40),null);
assert.equal(lean.estimate(good,out.baseline,60),null,'unsupported high feature must fail closed');
const noGround = lean.annotate({decks:[{source:'lidar',z_m:40}]},{ring_local:ring,points_full:pts},good);
assert.equal(noGround.applied,0);
assert.match(noGround.reason,/ground datum/);
console.log('PASS: RoofFeatureLean height ratio, geometry immutability, and fail-closed guards');
