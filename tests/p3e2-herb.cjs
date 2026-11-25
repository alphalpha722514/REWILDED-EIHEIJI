const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');

function extract(name) {
  const start = html.search(new RegExp('^function ' + name + '\\(', 'm'));
  assert.ok(start >= 0, name + ' が見つからない');
  const end = html.indexOf('\nfunction ', start + 1);
  return html.slice(start, end < 0 ? html.length : end);
}

const e2Line = html.match(/^const E2=(.*)$/m);
assert.ok(e2Line, 'E2 の設定が見つからない');
const game = new vm.Script([
  e2Line[0],
  '};',
  'const e2Values = JSON.stringify([E2.herbN, E2.grow, E2.herbBack, E2.herbAid]);',
  extract('kamiGather'),
  extract('e2Plant'),
].join('\n'));

function setup(random, gatherT = 0) {
  const inv = { mherb: 4, stone: 3, naegi: 2 };
  const kami = { n: {}, pl: {} };
  const stats = { time: 314 };
  const toasts = [];
  const noop = () => {};
  const ctx = vm.createContext({
    inv, prog: { kami }, stats, P: { gatherT }, REG: { live: {} },
    F5: { regrow: { stone: 90 } },
    toast: message => toasts.push(message),
    sfx: noop, floatText: noop, chips: noop, kamiH: () => 0,
    kamiNodesUpdate: noop, g4CheckQuests: noop, saveGame: noop,
  });
  ctx.random = random;
  vm.runInContext('Math.random = () => random;', ctx);
  game.runInContext(ctx);
  return { ctx, inv, kami, stats, toasts };
}

const settings = setup(0.75);
assert.deepEqual(JSON.parse(vm.runInContext('e2Values', settings.ctx)), [12, 2400, 1200, { t: 600, k: 2 }]);

for (const [random, gatherT, got] of [[0.75, 0, 1], [0.25, 0, 2], [0.75, 1, 2]]) {
  const { ctx, inv, kami, stats, toasts } = setup(random, gatherT);
  ctx.kamiGather({ key: 'h0', k: 'herb', x: 0, z: 0 });
  assert.equal(inv.mherb, 4 + got);
  assert.equal(Object.hasOwn(inv, 'herb'), false);
  assert.equal(kami.n.h0, stats.time + 1200);
  assert.doesNotMatch(toasts[0], /undefined/);
  assert.equal(toasts[0], `山の薬草 +${got}（${inv.mherb}）`);
}

const { ctx, inv, kami, stats, toasts } = setup(0.75, 1);
ctx.kamiGather({ key: 's0', k: 'stone', x: 0, z: 0 });
assert.equal(inv.stone, 5);
assert.equal(toasts[0], '石 +2（5）');
ctx.e2Plant({ key: 'k0', x: 0, z: 0 });
assert.equal(inv.naegi, 1);
assert.equal(kami.pl.k0, stats.time);
assert.match(toasts[1], /遊んだ時間で約40分で広葉樹に育つ/);
assert.doesNotMatch(toasts[1], /ゲームの中の時間/);

console.log('PASS: E-2 の設定値・山の薬草と石の採集・植林時の表示');
