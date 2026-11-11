#!/usr/bin/env node
// 第2章 光明寺防衛戦の勝率を測る道具（P1 用）。ゲーム本体（index.html）は変更しない。
//
// しくみ
// - index.html を読み、テスト用の差し込み（内部への参照・ボットの入力・描画の停止）を加えた
//   コピーを、画面のない Chromium で開く。差し込みはこの道具の中だけで、リポジトリのファイルは変えない。
// - 実時間ではなく、ゲームの更新（f11Sim）を 0.05 秒ずつ直接進める。描画はしない。
// - 条件（武器・防具・柵・罠・回復食・木材・レベル）を整え、源さんから防衛戦を始め、ボットが戦う。
// - 乱数（Math.random）は実行ごとに固定の種で置き換えるので、同じ種なら同じ結果になる。
// - --override で C2_DEFENSE の値を一時的に差し替えて試せる（ゲームのファイルは変えない）。
//
// 注意
// - ボットの勝率は「人が遊んだときの勝率」ではない。条件どうしの差と、値を変えたときの増減を見る目安。
// - 条件（PRESETS）は 2026-11-11 の P1 実装指示（A／B／C）を、現行コードにある装備・設備で具体化したもの。
//
// 使い方
//   THREE_JS=/path/to/three.min.js node tools/defense-sim.cjs [--runs 30] [--cond A,B,C] [--seed 1]
//        [--override '{"coreHp":400}'] [--json out.json]
//   THREE_JS は three.js r128 の three.min.js（CDN に出られない環境のため、ローカルのファイルを渡す）。
//   SIM_TRACE=1 で1秒ごとの様子を表示する。playwright（Chromium 付き）が必要。

const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

// ---- 条件（P1 実装指示の A／B／C を、現行コードで具体化） ----
// 柵の枠は南門・東口・沢口の3つだけ。罠の枠は門の前に6つ（0,1=南門 2,3=東口 4,5=沢口）。
// ヌシ討伐で経験値150が入るため、第2章に挑める最低レベルは2。
const PRESETS = {
  A: {
    label: 'A 準備なし', level: 2, weapon: 'nata1', armor: {},
    gates: [null, null, null], traps: [], food: { onigiri: 0, bento: 0 }, wood: 0,
  },
  B: {
    label: 'B 一部準備', level: 3, weapon: 'nata2',
    armor: { head: 'basic_head', chest: 'basic_chest' },
    gates: ['wood', 'stake', null], traps: [[0, 'pit'], [2, 'snare']], food: { onigiri: 3, bento: 0 }, wood: 4,
  },
  C: {
    label: 'C 十分な準備', level: 4, weapon: 'spear',
    armor: { head: 'forest_head', chest: 'forest_chest', legs: 'forest_legs', feet: 'forest_feet' },
    gates: ['stake', 'stake', 'wood'], traps: [[0, 'pit'], [1, 'snare'], [2, 'pit'], [4, 'pit']],
    food: { onigiri: 3, bento: 2 }, wood: 10,
  },
};

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i >= 0 ? process.argv[i + 1] : def;
}

function instrument(html) {
  const rep = (s, a, b) => {
    const n = s.split(a).length - 1;
    if (n !== 1) throw new Error(`差し込み位置が ${n} か所見つかった（1か所のはず）: ${a.slice(0, 50)}`);
    return s.replace(a, b);
  };
  html = rep(html, 'function inputWorld(){', 'function inputWorld(){ if(window.__bot) return window.__bot.input();');
  html = rep(html, 'function frame(now){\n  requestAnimationFrame(frame);',
    'function frame(now){\n  requestAnimationFrame(frame); if(window.__noRender){ last=now; return; }');
  const hook = 'window.__g={get P(){return P},get prog(){return prog},get inv(){return inv},get ev(){return ev},' +
    'get enemies(){return enemies},get GAPS(){return GAPS},get traps(){return traps},get npcGen(){return npcGen},' +
    'get CORE(){return CORE},get S(){return S},get WEAPONS(){return WEAPONS},get XP(){return XP},get stats(){return stats},' +
    'get C2(){return C2_DEFENSE},' +
    'freshState:()=>freshState(),resetWorld:x=>resetWorld(x),hideAllOv:()=>hideAllOv(),setFence:(g,t,h)=>setFence(g,t,h),' +
    'setTrap:(t,s,k)=>setTrap(t,s,k),startChapter2Defense:()=>startChapter2Defense(),chapter2State:(a,b)=>chapter2State(a,b),' +
    'f11Sim:d=>f11Sim(d),tryAttack:(k,a)=>tryAttack(k,a),tryDodge:()=>tryDodge(),eat:k=>eat(k),f31MaxHp:l=>f31MaxHp(l),' +
    'f47ApplyVisual:()=>f47ApplyVisual(),raidAlive:()=>raidAlive(),' +
    'repairFence:(g,c,f)=>repairFence(g,c,f),rearmTrap:t=>rearmTrap(t)};\n';
  html = rep(html, '// ================= NPC =================', hook + '// ================= NPC =================');
  // 試験用の書き換え（SIM_PATCH=JSON ファイル：[[元の文字列, 新しい文字列], ...]）。ゲームのファイルは変えない
  if (process.env.SIM_PATCH) for (const [a, b] of JSON.parse(fs.readFileSync(process.env.SIM_PATCH, 'utf8'))) html = rep(html, a, b);
  return html;
}

// ページ内で動く：条件の準備・ボット・1回の戦闘
const PAGE_CODE = String.raw`
window.__seedRandom = function(seed){
  let a = seed >>> 0;
  Math.random = function(){ a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
};
const LEASH = 16;
const WIND = new Set(['wind','chargeWind','goreWind','stompWind','tusk','paw','strike']);
const RECOVER = new Set(['stun','trapped','recover','chargeRec','goreRec','tuskRec','hurt']);
const GATE = ['南門','東口','沢口'];
window.__bot = { mv:{x:0,z:0,mag:0}, input(){ return this.mv; } };
const B = {};
function setup(c){
  const g = __g;
  g.freshState(); g.resetWorld(null); g.hideAllOv(); g.S.mode = 'playing';
  const prog = g.prog, P = g.P, inv = g.inv;
  prog.bossDefeated = true; prog.stage = 'cleared'; prog.unlockTrap = true; prog.unlockBoss = true;
  prog.chapter2 = g.chapter2State(null, true);
  prog.level = c.level; prog.exp = g.XP.lv[c.level - 1] || 0; P.maxHp = g.f31MaxHp(c.level); P.hp = P.maxHp;
  P.weapon = c.weapon; P.dur = g.WEAPONS[c.weapon].maxDur; prog.arms[c.weapon] = P.dur;
  for (const [slot, id] of Object.entries(c.armor)) { if (!prog.gear.owned.includes(id)) prog.gear.owned.push(id); prog.gear.equip[slot] = id; }
  g.f47ApplyVisual();
  inv.onigiri = c.food.onigiri; inv.bento = c.food.bento; inv.wood = c.wood;
  g.GAPS.forEach((gp, i) => g.setFence(gp, c.gates[i] || null));
  for (const [i, kind] of c.traps) g.setTrap(g.traps[i], 'armed', kind);
  P.x = g.npcGen.x + 1.2; P.z = g.npcGen.z + 1.2;
  return g.startChapter2Defense();
}
// 波の間や手が空いたときの補修（人が「調べる」で行う操作を、近くまで歩いてから呼ぶ）
function maintenanceTarget(){
  const g = __g;
  let best = null, bd = 1e9;
  g.GAPS.forEach((gp, i) => {
    const f = gp.fence; if (!f.type) return;
    let need = 0;
    if (f.broken && g.inv.wood >= 2) need = 2; else if (!f.broken && f.hp < f.max * 0.6 && g.inv.wood >= 1) need = 1;
    if (!need) return;
    const d = Math.hypot(gp.in.x - g.P.x, gp.in.z - g.P.z);
    if (d < bd) { bd = d; best = {kind:'fence', i, x:gp.in.x, z:gp.in.z, gp, full: f.broken}; }
  });
  for (let i = 0; i < 6; i++) {
    const t = g.traps[i]; if (t.state !== 'sprung') continue;
    const cost = t.type === 'pit' ? 2 : 1; if (g.inv.wood < cost + 1) continue; // 柵の再建ぶんを少し残す
    const d = Math.hypot(t.x - g.P.x, t.z - g.P.z);
    if (d < bd) { bd = d; best = {kind:'trap', t, x:t.x, z:t.z}; }
  }
  return best;
}
function think(){
  const g = __g, P = g.P, bot = __bot;
  bot.mv = {x:0, z:0, mag:0}; B.tgt = null;
  if (P.dead) return;
  if (P.hp < P.maxHp * 0.45 && !P.atk && !P.dodge) {
    if (g.inv.bento > 0) { g.eat('bento'); B.ate++; } else if (g.inv.onigiri > 0) { g.eat('onigiri'); B.ate++; }
  }
  const foes = g.enemies.filter(e => e.mode === 'raid' && e.state !== 'dead' && e.hp > 0);
  for (const e of foes) {
    const d = Math.hypot(e.x - P.x, e.z - P.z);
    // 猪・熊の大技だけ避ける（猿の小技まで避けるとスタミナが尽きて反撃できない）
    const big = e.type === 'boar' || e.type === 'bear';
    if (d < e.r + 3.2 && WIND.has(e.state) && big && P.st >= 25) {
      const side = (e.id % 2 ? 1 : -1);
      const a = Math.atan2(P.x - e.x, P.z - e.z) + side * Math.PI / 2;
      bot.mv = {x:Math.sin(a), z:Math.cos(a), mag:1}; g.tryDodge(); return;
    }
  }
  const C = g.CORE;
  const go = (tx, tz) => {
    let a = Math.atan2(tx - P.x, tz - P.z);
    if (B.unstuckT > 0) a += B.unstuckSide * Math.PI / 2;  // 引っかかったら横へずれる
    bot.mv = {x:Math.sin(a), z:Math.cos(a), mag:1};
  };
  // やぐらから LEASH m 以内の獣だけを狙う（外へ追いかけると、その間に猿がやぐらを叩く）
  let best = null, bs = 1e9;
  for (const e of foes) {
    const d = Math.hypot(e.x - P.x, e.z - P.z);
    const dc = Math.hypot(e.x - C.x, e.z - C.z);
    // 門の柵で止まっている獣は、内側から攻撃しに行く（止めたまま放っておくと、慧心の修理と押し合いになり終わらない）
    const atGate = g.GAPS.some(gp => Math.hypot(e.x - gp.c.x, e.z - gp.c.z) < 8);
    if (dc > LEASH && !atGate) continue;
    let s = d;
    if (e.type === 'monkey' && dc < 6) s -= 25;       // やぐらを叩く猿を最優先
    if (RECOVER.has(e.state)) s -= 6;                // 止まっている獣を狙う
    if (s < bs) { bs = s; best = e; }
  }
  if (!best) {
    const m = maintenanceTarget();
    if (m) {
      const d = Math.hypot(m.x - P.x, m.z - P.z);
      if (d > 1.5) { go(m.x, m.z); return; }
      if (m.kind === 'fence') { g.repairFence(m.gp, m.full ? 2 : 1, m.full); B.repairs++; }
      else { g.rearmTrap(m.t); B.rearms++; }
      return;
    }
    const d = Math.hypot(C.x + 3 - P.x, C.z + 3 - P.z);
    if (d > 2) go(C.x + 3, C.z + 3);
    return;
  }
  const w = g.WEAPONS[P.weapon] || {range:2};
  const d = Math.hypot(best.x - P.x, best.z - P.z);
  const a = Math.atan2(best.x - P.x, best.z - P.z);
  B.tgt = best;
  if (d > w.range + best.r + 0.6) { go(best.x, best.z); return; }  // 軽攻撃の踏み込みぶん、少し遠くから振る
  P.facing = a;
  if (!P.atk && !P.dodge) g.tryAttack(RECOVER.has(best.state) ? 'heavy' : 'light', a);
}
window.__runOne = async function(c, seed, maxT, override){
  __seedRandom(seed);
  Object.assign(B, {ate:0, repairs:0, rearms:0, trace: window.__wantTrace ? [] : null, tgt:null, unstuckT:0, unstuckSide:1, lastX:0, lastZ:0, chkT:0});
  const g = __g;
  if (!window.__c2orig) window.__c2orig = JSON.parse(JSON.stringify(g.C2));
  Object.assign(g.C2, JSON.parse(JSON.stringify(window.__c2orig)), override || {});
  const ok = setup(c);
  if (!ok) return {result:'setup-failed'};
  let t = 0, dmgTaken = 0, lastHp = g.P.hp, maxWave = 0, maxAlive = 0;
  const killsBefore = g.stats.kills;
  const fenceHp = g.GAPS.map(gp => gp.fence.hp), fenceBroke = [0,0,0], eshin = [0,0,0];
  const trapArmed = g.traps.slice(0, 6).map(tr => tr.state === 'armed'); let trapFired = 0;
  const coreBy = [0,0,0], coreByType = {}; let lastCore = g.ev.coreHp; const waveClearT = [];
  while (t < maxT) {
    for (let k = 0; k < 200 && t < maxT; k++) {
      const repBefore = B.repairs;
      think(); g.f11Sim(0.05); t += 0.05;
      B.unstuckT = Math.max(0, B.unstuckT - 0.05); B.chkT += 0.05;
      if (B.chkT >= 0.6) { const moved = Math.hypot(g.P.x - B.lastX, g.P.z - B.lastZ); if (__bot.mv.mag > 0 && moved < 0.4 && !g.P.atk && !g.P.dodge) { B.unstuckT = 0.7; B.unstuckSide = -B.unstuckSide; } B.lastX = g.P.x; B.lastZ = g.P.z; B.chkT = 0; }
      if (g.P.hp < lastHp) dmgTaken += lastHp - g.P.hp; lastHp = g.P.hp;
      const alive = g.raidAlive(); maxAlive = Math.max(maxAlive, alive);
      if (g.ev.kind === 'chapter2' && g.ev.phase === 'fight') {
        if (g.ev.waveIdx + 1 > maxWave) { if (maxWave > 0) waveClearT.push(+t.toFixed(0)); maxWave = g.ev.waveIdx + 1; }
      }
      g.GAPS.forEach((gp, i) => {
        const f = gp.fence; const h = f.type ? f.hp : 0;
        if (f.type && f.broken && fenceHp[i] > 0) fenceBroke[i]++;
        if (h > fenceHp[i] && B.repairs === repBefore) eshin[i] += h - fenceHp[i];
        fenceHp[i] = f.broken ? 0 : h;
      });
      g.traps.slice(0, 6).forEach((tr, i) => { const armed = tr.state === 'armed'; if (trapArmed[i] && tr.state === 'sprung') trapFired++; trapArmed[i] = armed; });
      if (g.ev.kind === 'chapter2' && g.ev.coreHp < lastCore) {
        const hitters = g.enemies.filter(e => e.mode === 'raid' && e.c2CoreT > 0 && e.state !== 'dead');
        for (const e of hitters) { const gi = (e.gap ?? e.opt?.gap ?? -1); if (gi >= 0) coreBy[gi] += (lastCore - g.ev.coreHp) / hitters.length; coreByType[e.type] = (coreByType[e.type] || 0) + (lastCore - g.ev.coreHp) / hitters.length; }
      }
      if (g.ev.kind === 'chapter2') lastCore = g.ev.coreHp;
      if (B.trace && k % 20 === 0) { const e = B.tgt; B.trace.push([+t.toFixed(1), +g.P.x.toFixed(1), +g.P.z.toFixed(1), e ? e.type + ':' + e.state + ':' + Math.round(e.hp) : '-', Math.round(g.P.hp), Math.round(g.P.st), g.ev.phase, Math.round(g.ev.coreHp || 0), alive, g.GAPS.map(gp => gp.fence.type ? Math.round(gp.fence.hp) : '-').join('/')]); }
      const won = !g.ev.kind && g.prog.chapter2 && g.prog.chapter2.progress && g.prog.chapter2.progress.defenseComplete;
      if (won || g.S.mode === 'dead') {
        let killer = null;
        if (!won && (g.ev.coreHp || 0) > 0) { let bd = 1e9; for (const e of g.enemies) { if (e.mode !== 'raid' || e.state === 'dead') continue; const d = Math.hypot(e.x - g.P.x, e.z - g.P.z); if (d < bd) { bd = d; killer = e.type + '@' + (GATE[e.gap ?? -1] || '?'); } } }
        return {result: won ? 'win' : 'lose', reason: won ? null : ((g.ev.coreHp || 0) <= 0 ? 'core' : 'player'),
          time: +t.toFixed(1), wave: maxWave, waveClearT, hp: Math.round(g.P.hp), maxHp: g.P.maxHp,
          coreHp: Math.round(won ? lastCore : (g.ev.coreHp || 0)), dmgTaken: Math.round(dmgTaken), ate: B.ate,
          repairs: B.repairs, rearms: B.rearms, trapFired, fenceBroke, eshin: eshin.map(Math.round),
          coreBy: coreBy.map(Math.round), coreByType: Object.fromEntries(Object.entries(coreByType).map(([k, v]) => [k, Math.round(v)])),
          killer, maxAlive, kills: g.stats.kills - killsBefore, trace: B.trace,
          after: {wood: g.inv.wood, straw: g.inv.straw, onigiri: g.inv.onigiri, rewarded: !!(g.prog.chapter2.progress || {}).defenseRewarded}};
      }
    }
    await new Promise(r => setTimeout(r, 0));
  }
  return {result:'timeout', time: +t.toFixed(1), wave: maxWave, hp: Math.round(g.P.hp), coreHp: Math.round(g.ev.coreHp || 0),
    dmgTaken: Math.round(dmgTaken), ate: B.ate, repairs: B.repairs, rearms: B.rearms, trapFired, fenceBroke,
    eshin: eshin.map(Math.round), coreBy: coreBy.map(Math.round), maxAlive, kills: g.stats.kills - killsBefore};
};
`;

async function main() {
  const repo = path.join(__dirname, '..');
  const runs = +arg('runs', 30);
  const conds = arg('cond', 'A,B,C').split(',');
  const seed0 = +arg('seed', 1);
  const maxT = +arg('maxT', 900);
  const override = JSON.parse(arg('override', '{}'));
  const out = arg('json', null);
  const threePath = process.env.THREE_JS;
  if (!threePath || !fs.existsSync(threePath)) throw new Error('THREE_JS に three.js r128 の three.min.js のパスを指定してください');
  const html = instrument(fs.readFileSync(process.env.SIM_HTML || path.join(repo, 'index.html'), 'utf8')); // SIM_HTML で試遊版なども測れる
  const three = fs.readFileSync(threePath, 'utf8');

  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 320, height: 240 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.route('**/*', r => {
    const u = r.request().url();
    if (u.includes('three')) return r.fulfill({ body: three, contentType: 'application/javascript' });
    if (u.startsWith('http://game.local')) return r.fulfill({ body: html, contentType: 'text/html; charset=utf-8' });
    return r.abort();
  });
  await page.addInitScript('window.__noRender = true;' + (process.env.SIM_TRACE ? 'window.__wantTrace = true;' : ''));
  await page.goto('http://game.local/', { waitUntil: 'load', timeout: 240000 });
  await page.waitForFunction(() => window.__g && window.__g.S, null, { timeout: 120000 });
  await page.evaluate(PAGE_CODE);

  const results = {};
  for (const c of conds) {
    const preset = PRESETS[c];
    if (!preset) throw new Error('条件がない: ' + c);
    results[c] = [];
    for (let i = 0; i < runs; i++) {
      const r = await page.evaluate(([p, s, m, o]) => window.__runOne(p, s, m, o), [preset, seed0 + i, maxT, override]);
      if (r.trace) { for (const row of r.trace) console.log('  ', JSON.stringify(row)); delete r.trace; }
      results[c].push(r);
      if (process.env.SIM_VERBOSE) console.log(c, i + 1, JSON.stringify(r));
    }
  }
  await browser.close();

  const pct = (n, d) => Math.round(n / d * 100) + '%';
  const med = a => { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : 0; };
  console.log('上書き:', JSON.stringify(override));
  console.log('条件           勝率  体力切れ やぐら破壊 時間切れ  第1/2/3波に到達  勝ち時の残り体力/やぐら  食事 補修 罠作動 柵破壊(南/東/沢) 慧心の修理(南/東/沢) やぐらの被害(南/東/沢) 最大同時');
  for (const c of conds) {
    const rs = results[c], n = rs.length, win = rs.filter(r => r.result === 'win');
    const reach = [1, 2, 3].map(w => pct(rs.filter(r => r.wave >= w).length, n)).join('/');
    const sum3 = k => [0, 1, 2].map(i => Math.round(rs.reduce((a, r) => a + (r[k] ? r[k][i] : 0), 0) / n)).join('/');
    console.log(`${PRESETS[c].label.padEnd(10)} ${pct(win.length, n).padStart(4)}  ${String(rs.filter(r => r.reason === 'player').length).padStart(6)}  ${String(rs.filter(r => r.reason === 'core').length).padStart(8)}  ${String(rs.filter(r => r.result === 'timeout').length).padStart(6)}   ${reach.padEnd(15)}  ${win.length ? med(win.map(r => r.hp)) + '/' + med(win.map(r => r.coreHp)) : '-'}`.padEnd(100) +
      `  ${med(rs.map(r => r.ate))}  ${med(rs.map(r => r.repairs))}  ${med(rs.map(r => r.trapFired))}  ${sum3('fenceBroke')}  ${sum3('eshin')}  ${sum3('coreBy')}  ${Math.max(...rs.map(r => r.maxAlive))}`);
    const killers = {}; rs.filter(r => r.killer).forEach(r => { killers[r.killer] = (killers[r.killer] || 0) + 1; });
    if (Object.keys(killers).length) console.log('   体力切れのとき一番近かった獣:', JSON.stringify(killers));
  }
  if (errors.length) console.log('\nページエラー:', errors.slice(0, 5));
  if (out) fs.writeFileSync(out, JSON.stringify({ presets: PRESETS, runs, seed0, maxT, override, results, errors }, null, 2));
}

main().catch(e => { console.error(e); process.exit(1); });
