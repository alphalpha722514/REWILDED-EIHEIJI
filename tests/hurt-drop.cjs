const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');

function extract(name, required = true) {
  const start = html.search(new RegExp('^function ' + name + '\\(', 'm'));
  if (start < 0 && !required) return '';
  assert.ok(start >= 0, name + ' was not found');
  const end = html.indexOf('\nfunction ', start + 1);
  return html.slice(start, end < 0 ? html.length : end);
}

const optional = ['logAttrSet', 'f4CarrySet', 'logAttrNorm'].map(name => extract(name, false));
const game = new vm.Script([
  ...['hurtPlayer', 'f4DropAll', 'f4DropLog', 'f4Busy', 'f31Armor'].map(name => extract(name)),
  ...optional,
].join('\n'));

function setup({ carry = 0, push = false, hp = 50, iframe = false, drive = false,
  suzuki = false, dead = false, cut = 0.25 } = {}) {
  const P = { x: 4, z: 7, facing: 0.7, hp, iframe, dead };
  const f4 = {
    carry,
    logs: [[1, 2, 0, 'k']],
    cart: { x: 3, z: 5, a: 0, push, logs: ['k'] },
  };
  if (optional.some(Boolean)) f4.cart.logA = [null];
  const calls = {};
  function record(name, result) {
    return (...args) => {
      (calls[name] ??= []).push(args);
      return result;
    };
  }
  const vignette = { style: {} };
  const ctx = vm.createContext({
    P, prog: { f4 }, S: { time: 12, shake: 0 }, TGV: { on: suzuki },
    TRUCK: { drive }, TRUCK_SYS: { hp: { beast: 0.5 } },
    P3D: { fish: false }, SZR: { on: false }, heavyRing: { visible: true },
    f11InvDmg: (...args) => record('f11InvDmg', args[0])(...args),
    f47Stats: record('f47Stats', { cut, knock: 0, steady: 0 }),
    f78Wpn: record('f78Wpn', null),
    perfectOK: record('perfectOK', false), perfectDodge: record('perfectDodge'),
    truckDamage: record('truckDamage'), szHurt: record('szHurt', false),
    szRescueCancel: record('szRescueCancel'), p3dStop: record('p3dStop'),
    playerDie: record('playerDie'), floatText: record('floatText'),
    sfx: record('sfx'), toast: record('toast'), f4LogsDirty: record('f4LogsDirty'),
    $: record('$', vignette), setTimeout: record('setTimeout'),
  });
  game.runInContext(ctx);
  return {
    P, f4, calls,
    hit: () => ctx.hurtPlayer(9, P.x + 3, P.z, 2.5, null),
    armorDamage: () => ctx.f31Armor(9),
  };
}

function assertDropped(P, f4, calls, before) {
  assert.equal(f4.carry, 0);
  assert.equal(f4.logs.length, before.length + 1);
  assert.deepEqual(f4.logs.slice(0, -1), before);
  const [x, z, , size] = f4.logs.at(-1);
  assert.equal(size, 'k');
  assert.equal(x, P.x + Math.sin(P.facing) * 0.9);
  assert.equal(z, P.z + Math.cos(P.facing) * 0.9);
  assert.deepEqual(calls.toast, [['丸太を落とした', true]]);
  assert.deepEqual(calls.f4LogsDirty, [[]]);
}

const failures = [];
function check(name, run) {
  try {
    run();
  } catch (error) {
    failures.push(name);
    console.error(name, error);
  }
}

check('A: carried log drops on damage', () => {
  const { P, f4, calls, hit, armorDamage } = setup({ carry: 'k' });
  const expectedHp = P.hp - armorDamage();
  const before = structuredClone(f4.logs);
  assert.equal(hit(), true);
  assert.equal(P.hp, expectedHp);
  assertDropped(P, f4, calls, before);
});

check('B: cart is released with cargo intact', () => {
  const { f4, calls, hit } = setup({ push: true });
  const before = structuredClone(f4);
  assert.equal(hit(), true);
  assert.equal(f4.cart.push, false);
  assert.deepEqual(f4.cart.logs, before.cart.logs);
  assert.deepEqual(f4.cart.logA, before.cart.logA);
  assert.deepEqual(f4.logs, before.logs);
  assert.deepEqual(calls.toast, [['一輪車から手を離した', true]]);
});

check('C: iframe preserves HP and transport', () => {
  const { P, f4, calls, hit } = setup({ carry: 'k', push: true, iframe: true });
  const before = structuredClone(f4);
  const hp = P.hp;
  assert.equal(hit(), false);
  assert.deepEqual(f4, before);
  assert.equal(P.hp, hp);
  assert.equal(calls.toast, undefined);
});

check('D: driving routes damage to the truck', () => {
  const { f4, calls, hit } = setup({ carry: 'k', drive: true });
  assert.equal(hit(), false);
  assert.equal(f4.carry, 'k');
  assert.deepEqual(calls.truckDamage, [[4.5]]);
});

check('E: Suzuki handles the hit', () => {
  const { P, f4, calls, hit } = setup({ carry: 'k', suzuki: true });
  assert.equal(hit(), false);
  assert.equal(f4.carry, 'k');
  assert.deepEqual(calls.szHurt, [[9, P.x + 3, P.z, 2.5, null]]);
});

check('F: dead player retains the log', () => {
  const { f4, hit } = setup({ carry: 'k', dead: true });
  assert.equal(hit(), false);
  assert.equal(f4.carry, 'k');
});

check('G: hit without transport leaves logs and cart alone', () => {
  const { f4, calls, hit } = setup();
  const before = structuredClone(f4);
  assert.equal(hit(), true);
  assert.deepEqual(f4, before);
  assert.equal(calls.toast, undefined);
});

check('H: lethal damage drops the log before playerDie', () => {
  const { P, f4, calls, hit } = setup({ carry: 'k', hp: 1 });
  const before = structuredClone(f4.logs);
  assert.equal(hit(), true);
  assertDropped(P, f4, calls, before);
  assert.equal(P.hp, 0);
  assert.deepEqual(calls.playerDie, [['hp']]);
  assert.ok(Object.keys(calls).indexOf('f4LogsDirty') < Object.keys(calls).indexOf('playerDie'));
});

check('I: damage rounded to zero preserves transport', () => {
  const { P, f4, calls, hit, armorDamage } = setup({ carry: 'k', push: true, cut: 0.96 });
  const before = structuredClone(f4);
  const hp = P.hp;
  assert.equal(armorDamage(), 0);
  assert.equal(hit(), true);
  assert.equal(P.hp, hp);
  assert.deepEqual(f4, before);
  assert.equal(calls.toast, undefined);
});

if (failures.length) process.exitCode = 1;
else console.log('PASS: hurtPlayer transport drops, early returns, lethal damage, and zero damage');
