#!/usr/bin/env node
// Pure presentation checks. Python remains the only rules implementation.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const sandbox = {};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../web/table-layout.js'), 'utf8') +
  '\nglobalThis.layoutAPI = TableLayout;', sandbox);
const T = sandbox.layoutAPI;
const plain = value => JSON.parse(JSON.stringify(value));
const move = (a, b, side = 'RIGHT') => ({tile: [Math.min(a,b),Math.max(a,b)], orientation: [a,b], side});
function separated(layout) {
  const boxes = layout.tiles.map(T.rect);
  for(let i=0;i<boxes.length;i++) for(let j=i+1;j<boxes.length;j++) {
    const a=boxes[i], b=boxes[j];
    assert.ok(a.left >= b.right || a.right <= b.left || a.top >= b.bottom || a.bottom <= b.top,
      'Tiles must not overlap');
  }
}
let checks = 0;
function check(name, test) {test(); checks++; console.log('PASS '+name);}

check('Doubles are transverse to the chain', () => {
  const l = T.history([{move:move(6,6)}]);
  const r = T.rect(l.tiles[0]);
  assert.equal(r.right-r.left,44); assert.equal(r.bottom-r.top,86);
});
check('Curves at both ends preserve face order and shared values', () => {
  const events = [{move:move(1,2)}, {move:move(2,3)}, {move:move(0,1,'LEFT')}];
  const l = T.history(events, {'1-2':'right','2-3':'up','0-1':'down'});
  assert.deepEqual(plain(l.tiles.map(t=>t.faces)), [[0,1],[1,2],[2,3]]);
  assert.equal(l.tiles[0].direction,'up'); assert.equal(l.tiles[2].direction,'up');
  separated(l);
});
check('Space occupied by earlier tiles cannot be reused', () => {
  const events = [{move:move(0,1)},{move:move(1,2)},{move:move(2,3)},{move:move(3,4)}];
  const l = T.history(events, {'0-1':'right','1-2':'up','2-3':'left','3-4':'down'});
  separated(l);
  assert.ok(!T.options(l,move(4,5)).some(c=>c.direction === T.opposite(l.tiles.at(-1).direction)));
  for(const candidate of T.options(l,move(4,5))) separated(candidate.layout);
});
const faces = [[0,0],[0,1],[1,1],[1,2],[2,2],[2,3],[3,3],[3,4],[4,4],[4,5],[5,5],[5,6],[6,6],[6,0]];
const events = faces.map(([a,b])=>({move:move(a,b)}));
check('Fourteen distinct public tiles fit with automatic bends', () => {
  const l = T.history(events);
  assert.deepEqual(plain(l.tiles.map(t=>t.faces)),faces);
  assert.ok(new Set(l.tiles.map(t=>t.direction)).size > 1);
  const b = T.bounds(l);
  assert.ok(b.right-b.left <= 520 && b.bottom-b.top <= 350);
  separated(l);
});
check('Replaying saved directions reconstructs the same coordinates', () => {
  const l = T.history(events);
  assert.deepEqual(plain(T.history(events,plain(l.used))),plain(l));
});
check('Undo removes a tile and passes add no graphical tile', () => {
  const partial = events.slice(0,-1);
  const l = T.history([...partial,{move:{pass:true}}]);
  assert.deepEqual(plain(l),plain(T.history(partial)));
  assert.equal(l.tiles.length,13);
});
check('Graphical selection does not mutate the public move or history', () => {
  const frozen = JSON.stringify(events);
  const l = T.history(events.slice(0,4));
  const original = JSON.stringify(l);
  const m = events[4].move, before = JSON.stringify(m);
  T.options(l,m);
  assert.equal(JSON.stringify(events),frozen);
  assert.equal(JSON.stringify(l),original);
  assert.equal(JSON.stringify(m),before);
});
check('Malformed saved directions are ignored', () => {
  assert.deepEqual(plain(T.cleanPreferences({'9-9':'up','2-1':'up','1-2':'diagonal','3-4':'up'})),{'3-4':'up'});
  assert.deepEqual(plain(T.cleanPreferences(null)),{});
});
console.log(JSON.stringify({checks,failed:0}));
