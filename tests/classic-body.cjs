// v0.54.1: プレイヤーと村人を v0.32.1 のやわらかい体に戻した変更の回帰テスト
// - インラインスクリプトの構文
// - makeHuman が古い体（makeHumanClassic）を使い、プレイヤーだけ m.rigid
// - プレイヤー（m.rigid）はひじ・ひざに「ばねの遅れ」（くねくね）が出ない
// - 村人（古い体・rigid なし）は v0.32.1 のしなりを残す
// - 古い体では接地IK（f48Gait）を使わない
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
for (const [, attrs, code] of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
  if (!/\bsrc\s*=|type=["']application\/json/.test(attrs)) new vm.Script(code);
}

assert.equal((html.match(/function makeHumanClassic\(o\)\{/g) || []).length, 1, 'makeHumanClassic is defined once');
const disp = html.slice(html.indexOf('function makeHuman(o={}){'), html.indexOf('function makeHuman47('));
assert.ok(disp.includes('makeHumanClassic(player?CLASSIC_PLAYER_OPTS:o)'), 'player and villagers use the classic body');
assert.ok(disp.includes('m.rigid=player'), 'only the player is rigid');
assert.ok(disp.includes("m.layers={head:[],chest:[],legs:[],feet:[]}"), 'armor layer slots exist for f47ApplyVisual');
assert.ok(html.includes('const gait48=pm.anatomy48?f48Gait(dt):{enabled:false};'), 'grounded IK only for the anatomical rig');

// softPose を取り出して、ばねの遅れの有無を数値で確かめる
const start = html.indexOf('function softPose(m,dt,opt={}){');
const end = html.indexOf('\n}', start) + 2;
const ctx = vm.createContext({ Math });
vm.runInContext(`const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)); const lerp=(a,b,t)=>a+(b-a)*t;\n${html.slice(start, end)}`, ctx);
function rig(rigid) {
  const bone = () => ({ rotation: { x: 0, y: 0, z: 0, set(x, y, z) { this.x = x; this.y = y; this.z = z; } }, userData: {} });
  const armL = bone(), armR = bone(), legL = bone(), legR = bone();
  armL.userData.fore = bone(); armR.userData.fore = bone();
  legL.userData.shin = bone(); legR.userData.shin = bone();
  return { classic: true, rigid, soft: { lag: [0, 0], prev: [0, 0] }, armL, armR, legs: [legL, legR] };
}
function elbowRange(m) {
  const v = [];
  for (let i = 0; i < 60; i++) {
    m.armL.rotation.x = Math.sin(i * 0.4) * 0.8; // 腕を大きく振る
    ctx.softPose(m, 1 / 60, { elbow: 0.2, flop: 0.6 });
    v.push(m.armL.userData.fore.rotation.x);
  }
  return Math.max(...v) - Math.min(...v);
}
assert.ok(elbowRange(rig(true)) < 1e-9, 'player elbows do not lag (no wobble)');
assert.ok(elbowRange(rig(false)) > 0.01, 'villager elbows keep the classic soft lag');

console.log('PASS: classic body dispatch, player rigid (no wobble), villager soft lag, IK guarded, script syntax');
