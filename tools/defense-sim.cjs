#!/usr/bin/env node
// 第2章 光明寺防衛戦の勝率を測る道具（P1 用）。ゲーム本体（index.html）は変更しない。
//
// しくみ
// - index.html を読み、テスト用の差し込み（内部への参照・ボットの入力・描画の停止）を加えた
//   コピーを、画面のない Chromium で開く。差し込みはこの道具の中だけで、リポジトリのファイルは変えない。
// - 実時間ではなく、ゲームの更新（f11Sim）を 0.05 秒ずつ直接進める。描画はしない。
// - 条件（武器・防具・柵・罠・回復食・レベル）を整え、源さんから防衛戦を始め、ボットが戦う。
// - 乱数（Math.random）は実行ごとに固定の種で置き換えるので、同じ種なら同じ結果になる。
//
// 注意
// - ボットの勝率は「人が遊んだときの勝率」ではない。条件どうしを比べる目安として使う。
// - 条件の中身（PRESETS）は暫定。ユーザーと ChatGPT が決めた定義に差し替える。
//
// 使い方
//   THREE_JS=/path/to/three.min.js node tools/defense-sim.cjs [--runs 10] [--cond none,partial,full] [--seed 1] [--json out.json]
//   THREE_JS は three.js r128 の three.min.js（CDN に出られない環境のため、ローカルのファイルを渡す）。
//   playwright（Chromium 付き）が必要。

const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

// ---- 条件（暫定。ユーザー・ChatGPT の定義に差し替える） ----
// gates: 柵の種類（null=なし／wood／stake／spike）を南・東・西の順に。
// traps: TRAP_SLOTS の番号と種類（0,1=南口 2,3=東口 4,5=西口）。
const PRESETS = {
  none: {
    label: '準備なし（暫定）', level: 5, weapon: 'nata1', armor: {},
    gates: [null, null, null], traps: [], food: { onigiri: 1, bento: 0 },
  },
  partial: {
    label: '一部準備（暫定）', level: 5, weapon: 'nata2',
    armor: { head: 'basic_head', chest: 'basic_chest', legs: 'basic_legs', feet: 'basic_feet' },
    gates: ['wood', 'wood', 'wood'], traps: [[0, 'snare'], [2, 'snare'], [4, 'snare']], food: { onigiri: 3, bento: 0 },
  },
  full: {
    label: '十分な準備（暫定）', level: 5, weapon: 'spear',
    armor: { head: 'forest_head', chest: 'forest_chest', legs: 'forest_legs', feet: 'forest_feet' },
    gates: ['stake', 'stake', 'stake'],
    traps: [[0, 'pit'], [1, 'snare'], [2, 'pit'], [3, 'snare'], [4, 'pit'], [5, 'snare']],
    food: { onigiri: 4, bento: 2 },
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
    'freshState:()=>freshState(),resetWorld:x=>resetWorld(x),hideAllOv:()=>hideAllOv(),setFence:(g,t,h)=>setFence(g,t,h),' +
    'setTrap:(t,s,k)=>setTrap(t,s,k),startChapter2Defense:()=>startChapter2Defense(),chapter2State:(a,b)=>chapter2State(a,b),' +
    'f11Sim:d=>f11Sim(d),tryAttack:(k,a)=>tryAttack(k,a),tryDodge:()=>tryDodge(),eat:k=>eat(k),f31MaxHp:l=>f31MaxHp(l),' +
    'f47ApplyVisual:()=>f47ApplyVisual(),f31Armor:d=>f31Armor(d),raidAlive:()=>raidAlive()};\n';
  html = rep(html, '// ================= NPC =================', hook + '// ================= NPC =================');
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
window.__bot = { mv:{x:0,z:0,mag:0}, input(){ return this.mv; } };
function setup(c){
  const g = __g;
  g.freshState(); g.resetWorld(null); g.hideAllOv(); g.S.mode = 'playing';
  const prog = g.prog, P = g.P, inv = g.inv;
  prog.bossDefeated = true; prog.stage = 'cleared'; prog.chapter2 = g.chapter2State(null, true);
  prog.level = c.level; prog.exp = g.XP.lv[c.level - 1] || 0; P.maxHp = g.f31MaxHp(c.level); P.hp = P.maxHp;
  P.weapon = c.weapon; P.dur = g.WEAPONS[c.weapon].maxDur; prog.arms[c.weapon] = P.dur;
  for (const [slot, id] of Object.entries(c.armor)) { if (!prog.gear.owned.includes(id)) prog.gear.owned.push(id); prog.gear.equip[slot] = id; }
  g.f47ApplyVisual();
  inv.onigiri = c.food.onigiri; inv.bento = c.food.bento;
  g.GAPS.forEach((gp, i) => g.setFence(gp, c.gates[i] || null));
  for (const [i, kind] of c.traps) g.setTrap(g.traps[i], 'armed', kind);
  P.x = g.npcGen.x + 1.2; P.z = g.npcGen.z + 1.2;
  return g.startChapter2Defense();
}
function think(){
  const g = __g, P = g.P, bot = __bot;
  bot.mv = {x:0, z:0, mag:0};
  if (P.dead) return;
  if (P.hp < P.maxHp * 0.45 && !P.atk && !P.dodge) {
    if (g.inv.bento > 0) { g.eat('bento'); B.ate++; } else if (g.inv.onigiri > 0) { g.eat('onigiri'); B.ate++; }
  }
  const foes = g.enemies.filter(e => e.mode === 'raid' && e.state !== 'dead' && e.hp > 0);
  for (const e of foes) {
    const d = Math.hypot(e.x - P.x, e.z - P.z);
    // 猪・熊の大技だけ避ける（猿の小技まで避けるとスタミナが尽きて反撃できない）。スタミナが少ないときは避けない
    const big = e.type === 'boar' || e.type === 'bear';
    if (d < e.r + 3.2 && WIND.has(e.state) && big && P.st >= 25) {
      const side = (e.id % 2 ? 1 : -1);
      const a = Math.atan2(P.x - e.x, P.z - e.z) + side * Math.PI / 2;
      bot.mv = {x:Math.sin(a), z:Math.cos(a), mag:1}; g.tryDodge(); return;
    }
  }
  const C = g.CORE;
  // 守りの範囲（やぐらから LEASH m）の中の獣だけを狙う。外へ追いかけると、その間に猿がやぐらを叩くため
  let best = null, bs = 1e9;
  for (const e of foes) {
    const d = Math.hypot(e.x - P.x, e.z - P.z);
    const dc = Math.hypot(e.x - C.x, e.z - C.z);
    if (dc > LEASH) continue;
    let s = d;
    if (e.type === 'monkey' && dc < 6) s -= 25;       // やぐらを叩く猿を最優先
    if (RECOVER.has(e.state)) s -= 6;                // 止まっている獣を狙う
    if (s < bs) { bs = s; best = e; }
  }
  const go = (tx, tz) => {
    let a = Math.atan2(tx - P.x, tz - P.z);
    if (B.unstuckT > 0) a += B.unstuckSide * Math.PI / 2;  // 引っかかったら横へずれる
    bot.mv = {x:Math.sin(a), z:Math.cos(a), mag:1};
  };
  if (!best) { // 範囲に敵がいなければ、やぐらのそばで待つ
    const d = Math.hypot(C.x + 3 - P.x, C.z + 3 - P.z);
    if (d > 2) go(C.x + 3, C.z + 3);
    return;
  }
  const w = g.WEAPONS[P.weapon] || {range:2};
  const d = Math.hypot(best.x - P.x, best.z - P.z);
  const a = Math.atan2(best.x - P.x, best.z - P.z);
  B.tgt = best;
  if (d > w.range + best.r + 0.6) { go(best.x, best.z); return; }  // 軽攻撃の踏み込みぶん、少し遠くから振る
  B.tgt = best; P.facing = a;
  if (!P.atk && !P.dodge) g.tryAttack(RECOVER.has(best.state) ? 'heavy' : 'light', a);
}
const B = {ate:0, trace:null, tgt:null, unstuckT:0, unstuckSide:1, lastX:0, lastZ:0, chkT:0};
window.__runOne = async function(c, seed, maxT){
  __seedRandom(seed); B.ate = 0; B.trace = window.__wantTrace ? [] : null;
  const g = __g;
  const ok = setup(c);
  if (!ok) return {result:'setup-failed'};
  let t = 0, dmgTaken = 0, lastHp = g.P.hp, maxWave = 0;
  const killsBefore = g.stats.kills;
  while (t < maxT) {
    for (let k = 0; k < 200 && t < maxT; k++) {
      B.tgt = null; think(); g.f11Sim(0.05); t += 0.05;
      B.unstuckT = Math.max(0, B.unstuckT - 0.05); B.chkT += 0.05;
      if (B.chkT >= 0.6) { const moved = Math.hypot(g.P.x - B.lastX, g.P.z - B.lastZ); if (__bot.mv.mag > 0 && moved < 0.4 && !g.P.atk && !g.P.dodge) { B.unstuckT = 0.7; B.unstuckSide = -B.unstuckSide; } B.lastX = g.P.x; B.lastZ = g.P.z; B.chkT = 0; }
      if (B.trace && k % 20 === 0) { const e = B.tgt; B.trace.push([+t.toFixed(1), +g.P.x.toFixed(1), +g.P.z.toFixed(1), e ? e.type + ':' + e.state + ':' + Math.round(e.hp) : '-', e ? +Math.hypot(e.x - g.P.x, e.z - g.P.z).toFixed(1) : null, g.P.atk ? g.P.atk.kind : '', Math.round(g.P.st), g.ev.phase, Math.round(g.ev.coreHp || 0), g.raidAlive()]); }
      if (g.P.hp < lastHp) dmgTaken += lastHp - g.P.hp; lastHp = g.P.hp;
      if (g.ev.kind === 'chapter2' && g.ev.phase === 'fight') maxWave = Math.max(maxWave, g.ev.waveIdx + 1);
      const won = !g.ev.kind && g.prog.chapter2 && g.prog.chapter2.progress && g.prog.chapter2.progress.defenseComplete;
      if (won || g.S.mode === 'dead') {
        return {result: won ? 'win' : 'lose', reason: won ? null : ((g.ev.coreHp || 0) <= 0 ? 'core' : 'player'),
          time: +t.toFixed(1), wave: maxWave, hp: Math.round(g.P.hp), maxHp: g.P.maxHp,
          coreHp: Math.round(g.ev.coreHp || 0), dmgTaken: Math.round(dmgTaken), ate: B.ate,
          kills: g.stats.kills - killsBefore, trace: B.trace};
      }
    }
    await new Promise(r => setTimeout(r, 0));
  }
  return {result:'timeout', time: +t.toFixed(1), wave: maxWave, hp: Math.round(g.P.hp), coreHp: Math.round(g.ev.coreHp || 0),
    dmgTaken: Math.round(dmgTaken), ate: B.ate, kills: g.stats.kills - killsBefore};
};
`;

async function main() {
  const repo = path.join(__dirname, '..');
  const runs = +arg('runs', 10);
  const conds = arg('cond', 'none,partial,full').split(',');
  const seed0 = +arg('seed', 1);
  const maxT = +arg('maxT', 900);
  const out = arg('json', null);
  const threePath = process.env.THREE_JS;
  if (!threePath || !fs.existsSync(threePath)) throw new Error('THREE_JS に three.js r128 の three.min.js のパスを指定してください');
  const html = instrument(fs.readFileSync(path.join(repo, 'index.html'), 'utf8'));
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
      const r = await page.evaluate(([p, s, m]) => window.__runOne(p, s, m), [preset, seed0 + i, maxT]);
      results[c].push(r);
      if (r.trace) { for (const row of r.trace) console.log('  ', JSON.stringify(row)); delete r.trace; }
      process.stdout.write(`${c} #${i + 1}: ${r.result}${r.reason ? '(' + r.reason + ')' : ''} 波${r.wave} ${r.time}s 体力${r.hp} やぐら${r.coreHp} 被ダメ${r.dmgTaken} 食事${r.ate} 撃破${r.kills}\n`);
    }
  }
  await browser.close();

  console.log('\n条件              勝率   負け(体力/やぐら)  時間切れ  平均到達波  勝ち平均時間');
  for (const c of conds) {
    const rs = results[c];
    const win = rs.filter(r => r.result === 'win');
    const lp = rs.filter(r => r.reason === 'player').length, lc = rs.filter(r => r.reason === 'core').length;
    const to = rs.filter(r => r.result === 'timeout').length;
    const avgWave = (rs.reduce((a, r) => a + (r.wave || 0), 0) / rs.length).toFixed(1);
    const avgT = win.length ? (win.reduce((a, r) => a + r.time, 0) / win.length).toFixed(0) + 's' : '-';
    console.log(`${PRESETS[c].label.padEnd(14)} ${String(Math.round(win.length / rs.length * 100)).padStart(3)}%   ${lp}/${lc}               ${to}         ${avgWave}        ${avgT}`);
  }
  if (errors.length) console.log('\nページエラー:', errors.slice(0, 5));
  if (out) fs.writeFileSync(out, JSON.stringify({ presets: PRESETS, runs, seed0, maxT, results, errors }, null, 2));
}

main().catch(e => { console.error(e); process.exit(1); });
