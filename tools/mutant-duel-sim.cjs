#!/usr/bin/env node
// 変異したサルとの1対1を測る道具（v0.61〜）。ゲーム本体（index.html）は変更しない。
//
// しくみ（tools/defense-sim.cjs と同じ）
// - index.html にテスト用の差し込み（内部への参照・ボットの入力・描画の停止）を加えたコピーを、画面のない Chromium で開く。
// - ゲームの更新（f11Sim）を 0.05 秒ずつ直接進める。乱数は種で固定する。
// - 光明寺の開けた所で、主人公（ボット）と変異したサル1体だけを戦わせる（ほかの獣は消し続ける）。
// - ボットは近づいて叩き、サルが隙（攻撃の後・ひるみ・崩れ）なら強攻撃。体力が4割を切ると回復食を食べる。
//   サルの予備動作（噛みつき・ひっかき・飛びかかり）を見て、dodge の割合で横へ回避する（人のうまさの目安）。
// 注意：ボットの結果は「人が遊んだとき」ではない。強さを変えたときの増減を見る目安。
//
// 使い方
//   THREE_JS=/path/to/three.min.js node tools/mutant-duel-sim.cjs [--runs 20] [--cond B,C] [--dodge 0.3,0.8] [--mode flee|kill] [--seed 1]
//        [--override '{"bite":16}']（MUT の値を一時的に差し替え） [--et '{"hp":300}']（ET.mutant を差し替え）
//        [--enemy bear]（比べるための相手：bear・boar・monkey。倒すまで） [--at 142,236]（戦う場所。安全地帯の外）

const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const PRESETS = {
  B: { label: 'B 一部準備', level: 3, weapon: 'nata2', armor: { head: 'basic_head', chest: 'basic_chest' }, food: { onigiri: 3, bento: 0 } },
  C: { label: 'C 十分な準備', level: 4, weapon: 'spear', armor: { head: 'forest_head', chest: 'forest_chest', legs: 'forest_legs', feet: 'forest_feet' }, food: { onigiri: 3, bento: 2 } },
  D: { label: 'D 青鱗＋鱗の槍', level: 5, weapon: 'scSpear', armor: { head: 'blue_head', chest: 'blue_chest', legs: 'blue_legs', feet: 'blue_feet' }, food: { onigiri: 3, bento: 2 } }, // v0.63
  E: { label: 'E 変異鱗＋鱗の槍', level: 5, weapon: 'scSpear', armor: { head: 'raw_head', chest: 'raw_chest', legs: 'raw_legs', feet: 'raw_feet' }, food: { onigiri: 3, bento: 2 } }, // v0.63
};
function arg(name, def) { const i = process.argv.indexOf('--' + name); return i >= 0 ? process.argv[i + 1] : def; }

function instrument(html) {
  const rep = (s, a, b) => { const n = s.split(a).length - 1; if (n !== 1) throw new Error(`差し込み位置が ${n} か所: ${a.slice(0, 50)}`); return s.replace(a, b); };
  html = rep(html, 'function inputWorld(){', 'function inputWorld(){ if(window.__bot) return window.__bot.input();');
  html = rep(html, 'function frame(now){\n  requestAnimationFrame(frame);', 'function frame(now){\n  requestAnimationFrame(frame); if(window.__noRender){ last=now; return; }');
  const hook = 'window.__g={get P(){return P},get prog(){return prog},get inv(){return inv},get enemies(){return enemies},get S(){return S},' +
    'get WEAPONS(){return WEAPONS},get XP(){return XP},get MUT(){return MUT},get ET(){return ET},get PSPAWN(){return PSPAWN},' +
    'freshState:()=>freshState(),resetWorld:x=>resetWorld(x),hideAllOv:()=>hideAllOv(),chapter2State:(a,b)=>chapter2State(a,b),' +
    'f11Sim:d=>f11Sim(d),tryAttack:(k,a)=>tryAttack(k,a),tryDodge:()=>tryDodge(),eat:k=>eat(k),f31MaxHp:l=>f31MaxHp(l),' +
    'f47ApplyVisual:()=>f47ApplyVisual(),foodAdd:(k,n)=>foodAdd(k,n),f7Flush:()=>f7Flush(),removeEnemy:e=>removeEnemy(e),spawnEnemy:(...a)=>spawnEnemy(...a),spawnMutant:(x,z,o)=>spawnMutant(x,z,o),mutantLoad:()=>mutantLoad()};\n';
  return rep(html, '// ================= NPC =================', hook + '// ================= NPC =================');
}

const PAGE_CODE = String.raw`
window.__seedRandom = function(seed){ let a = seed >>> 0;
  Math.random = function(){ a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; };
window.__bot = { mv:{x:0,z:0,mag:0}, input(){ return this.mv; } };
const OPEN = new Set(['recover','hurt','stun','broken','trapped','scratch','scratch2']);
const WINDS = {wind:0.4, scratchWind:0.55, scratch2Wind:0.32, pounceWind:0.5};
const B = {};
async function setup(c, mode, foe, at){
  const g = __g; g.freshState(); g.resetWorld(null); g.hideAllOv(); g.S.mode = 'playing';
  const prog = g.prog, P = g.P, inv = g.inv;
  prog.bossDefeated = true; prog.stage = 'cleared'; prog.unlockTrap = true; prog.unlockBoss = true; prog.chapter2 = g.chapter2State(null, true);
  prog.level = c.level; prog.exp = g.XP.lv[c.level - 1] || 0; P.maxHp = g.f31MaxHp(c.level); P.hp = P.maxHp;
  P.weapon = c.weapon; P.dur = g.WEAPONS[c.weapon].maxDur; prog.arms[c.weapon] = P.dur;
  for (const [slot, id] of Object.entries(c.armor)) { if (!prog.gear.owned.includes(id)) prog.gear.owned.push(id); prog.gear.equip[slot] = id; }
  P.maxHp = g.f31MaxHp(c.level); P.hp = P.maxHp; // v0.63：防具で最大体力が変わる（変異鱗）
  g.f47ApplyVisual(); g.f7Flush(); inv.onigiri = 0; inv.bento = 0; if (c.food.onigiri) g.foodAdd('onigiri', c.food.onigiri); if (c.food.bento) g.foodAdd('bento', c.food.bento);
  P.x = at[0]; P.z = at[1]; P.facing = 0;
  for (const e of [...g.enemies]) g.removeEnemy(e);
  const e = foe === 'mutant' ? await g.spawnMutant(P.x + 7, P.z + 7, {fleeOnly: mode === 'flee', aggro: true}) : g.spawnEnemy(foe, P.x + 7, P.z + 7, foe === 'boss' ? 'boss' : 'field', {aggro: true});
  return e; }
function think(e, dodgeP){
  const g = __g, P = g.P, bot = __bot; bot.mv = {x:0, z:0, mag:0}; if (P.dead) return;
  if (P.hp < P.maxHp * 0.4 && !P.atk && !P.dodge) { if (g.inv.bento > 0) { g.eat('bento'); B.ate++; } else if (g.inv.onigiri > 0) { g.eat('onigiri'); B.ate++; } }
  const d = Math.hypot(e.x - P.x, e.z - P.z), a = Math.atan2(e.x - P.x, e.z - P.z);
  // 予備動作の終わりぎわに、決めた割合で横へ回避（同じ攻撃につき1回だけ判定）
  const wd = WINDS[e.state], tele = (e.sector && e.sector.visible) || (e.ind && e.ind.visible) || (e.ringM && e.ringM.visible);
  if ((e.type === 'mutant' ? (wd && e.st > wd - 0.18) : (tele && e.st > 0.25)) && B.judged !== e.sn) { B.judged = e.sn;
    const reach = e.type !== 'mutant' ? 9 : e.state === 'pounceWind' ? 11 : (e.state === 'scratchWind' || e.state === 'scratch2Wind') ? 4.2 : 3.2;
    if (d < reach && P.st >= 25 && Math.random() < dodgeP) { const s = (B.flip = -B.flip || 1); const da = a + s * Math.PI / 2; bot.mv = {x:Math.sin(da), z:Math.cos(da), mag:1}; g.tryDodge(); B.dodges++; return; } }
  const w = g.WEAPONS[P.weapon] || {range:2};
  if (e.state === 'flee' || e.state === 'dead') return;
  if (d > w.range + e.r + 0.5) { bot.mv = {x:Math.sin(a), z:Math.cos(a), mag:1}; return; }
  P.facing = a;
  if (!P.atk && !P.dodge) { const heavy = OPEN.has(e.state); g.tryAttack(heavy ? 'heavy' : 'light', a); if (heavy) B.heavy++; else B.light++; }
}
window.__duel = async function(c, seed, mode, dodgeP, maxT, mut, et, foe, at){
  const g = __g; await g.mutantLoad();
  if (!window.__mutOrig) window.__mutOrig = {mut: JSON.parse(JSON.stringify(g.MUT)), et: JSON.parse(JSON.stringify(g.ET.mutant))};
  Object.assign(g.MUT, window.__mutOrig.mut, mut || {}); Object.assign(g.ET.mutant, window.__mutOrig.et, et || {});
  __seedRandom(seed); Object.assign(B, {ate:0, dodges:0, heavy:0, light:0, judged:-1, flip:1});
  const e = await setup(c, mode, foe, at); let t = 0, dmg = 0, lastHp = g.P.hp, hits = 0, lastSn = -1; const ent = {};
  while (t < maxT) {
    for (let k = 0; k < 200 && t < maxT; k++) {
      if (!e.removed) think(e, dodgeP); g.f11Sim(0.05); t += 0.05;
      for (const o of [...g.enemies]) if (o !== e) g.removeEnemy(o);
      if (g.P.hp < lastHp) { dmg += lastHp - g.P.hp; hits++; } lastHp = g.P.hp;
      if (e.sn !== lastSn) { lastSn = e.sn; ent[e.state] = (ent[e.state] || 0) + 1; }
      const done = mode === 'flee' ? (e.state === 'flee' || e.removed) : (e.state === 'dead');
      if (done || g.S.mode === 'dead' || g.P.dead) {
        const win = done && !(g.S.mode === 'dead' || g.P.dead);
        return {result: win ? (mode === 'flee' ? 'repel' : 'kill') : 'lose', time: +t.toFixed(1), dmg: Math.round(dmg), hits, hp: Math.round(g.P.hp), maxHp: g.P.maxHp,
          ate: B.ate, dodges: B.dodges, heavy: B.heavy, light: B.light, mutHp: Math.round(e.hp), ent}; } }
    await new Promise(r => setTimeout(r, 0)); }
  return {result: 'timeout', time: +t.toFixed(1), dmg: Math.round(dmg), hits, hp: Math.round(g.P.hp), maxHp: g.P.maxHp, ate: B.ate, dodges: B.dodges, mutHp: Math.round(e.hp)};
};`;

async function main() {
  const repo = path.join(__dirname, '..');
  const runs = +arg('runs', 20), conds = arg('cond', 'B,C').split(','), dodges = arg('dodge', '0.3,0.8').split(',').map(Number);
  const foe = arg('enemy', 'mutant'), at = arg('at', '142,236').split(',').map(Number);
  const mode = foe === 'mutant' ? arg('mode', 'flee') : 'kill', seed0 = +arg('seed', 1), maxT = +arg('maxT', 240);
  const mut = JSON.parse(arg('override', '{}')), et = JSON.parse(arg('et', '{}'));
  const three = fs.readFileSync(process.env.THREE_JS, 'utf8');
  const html = instrument(fs.readFileSync(process.env.SIM_HTML || path.join(repo, 'index.html'), 'utf8'));
  const mdata = fs.readFileSync(path.join(repo, 'data/models/mutant-monkey.js'), 'utf8');
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 320, height: 240 } });
  const errors = []; page.on('pageerror', e => errors.push(String(e)));
  await page.route('**/*', r => { const u = r.request().url();
    if (u.includes('three')) return r.fulfill({ body: three, contentType: 'application/javascript' });
    if (u.includes('mutant-monkey.js')) return r.fulfill({ body: mdata, contentType: 'application/javascript' });
    if (u.startsWith('http://game.local')) return r.fulfill({ body: html, contentType: 'text/html; charset=utf-8' });
    return r.abort(); });
  await page.addInitScript('window.__noRender = true;');
  await page.goto('http://game.local/', { waitUntil: 'load', timeout: 240000 });
  await page.waitForFunction(() => window.__g && window.__g.S, null, { timeout: 120000 });
  await page.evaluate(PAGE_CODE);
  const med = a => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : 0; };
  console.log(`相手：${foe}  場所：${at}  `);
  console.log(`モード：${mode === 'flee' ? '初遭遇（撃退）' : '通常（倒す）'}  上書き MUT=${JSON.stringify(mut)} ET=${JSON.stringify(et)}`);
  console.log('条件           回避   勝ち  負け  時間切れ  時間(中央)  受けた(中央)  被弾回数  残り体力  食事  回避回数');
  for (const c of conds) for (const dp of dodges) {
    const rs = [];
    for (let i = 0; i < runs; i++) rs.push(await page.evaluate(([p, s, m, d, t, a, b, f, x]) => window.__duel(p, s, m, d, t, a, b, f, x), [PRESETS[c], seed0 + i, mode, dp, maxT, mut, et, foe, at]));
    const win = rs.filter(r => r.result === 'repel' || r.result === 'kill');
    console.log(`${PRESETS[c].label.padEnd(10)} ${String(dp).padStart(4)}  ${String(Math.round(win.length / rs.length * 100) + '%').padStart(4)}  ${String(rs.filter(r => r.result === 'lose').length).padStart(4)}  ${String(rs.filter(r => r.result === 'timeout').length).padStart(6)}    ${String(med(win.map(r => r.time))).padStart(6)}s     ${String(med(rs.map(r => r.dmg))).padStart(6)}      ${String(med(rs.map(r => r.hits))).padStart(4)}    ${win.length ? med(win.map(r => r.hp)) + '/' + rs[0].maxHp : '-'}   ${med(rs.map(r => r.ate))}    ${med(rs.map(r => r.dodges))}`);
    if (process.env.DUEL_DETAIL) { const sum = {}; for (const r of rs) for (const [k, v] of Object.entries(r.ent || {})) sum[k] = (sum[k] || 0) + v;
      console.log('    状態に入った回数（1戦あたり）:', Object.entries(sum).map(([k, v]) => `${k} ${(v / rs.length).toFixed(1)}`).join('  '), `  強攻撃 ${med(rs.map(r => r.heavy))}・通常 ${med(rs.map(r => r.light))}`); }
  }
  await browser.close();
  if (errors.length) console.log('ページエラー:', errors.slice(0, 3));
}
main().catch(e => { console.error(e); process.exit(1); });
