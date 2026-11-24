#!/usr/bin/env node
// 上志比の伐採（v0.88 伐採の修正）の確認（画面のない Chromium。Node の Playwright。10分ほど）。docs/p3e2-felling-fix.md
// 実際の操作に近い形で確かめる：PC は J（攻撃）と E（調べる）を押す。iPhone の再現は「攻撃」「調べる」ボタンをタップする
//  1 杉だけの所で杉を切る（f・苗木なし・案内は「杉」）  2 広葉樹だけの所で広葉樹を切る（fb・苗木+1・案内は「広葉樹」）
//  3 杉と広葉樹が近い所で、それぞれを切る（案内に出ている木を切る）  4 案内の木と攻撃で切る木が同じ（たくさんの立ち位置で数える）
//  5・6 苗木（広葉樹は+1・杉は0）  7 広葉樹の丸太（名前・はじめの2本は割ると山地の硬木）  8 植林と成長
//  9 セーブして読み込み直す（つづきから）  10 iPhone の再現（タップ）
// 使い方：THREE_JS=…/three.min.js node tests/p3e2-felling.cjs   （FELL_HTML=別の index.html で、直す前の版と比べる）
// 試遊版そのものを確かめる：FELL_PAGE=previews/p3e2-forest/index.html（その置き場所から開く。新しい形の案内・案内を押しても切らない・試遊版の保存キー・本編のキーに触れない、も確かめる）
// 2026-11-24：Codex の改善版（p3e2-felling-test-fix の 8cc8e5d）に、試遊版の確かめ（p3e2-integrated-preview の FELL_PAGE・P1〜P3）を移した
const assert = require('node:assert/strict');
const fs = require('fs'), path = require('path');
const { chromium, devices } = require('playwright');
const ROOT = path.dirname(__dirname);
const THREE = fs.readFileSync(process.env.THREE_JS || '/home/claude/v010/node_modules/three/build/three.min.js', 'utf8');
const PAGE = process.env.FELL_PAGE || ''; // 例：previews/p3e2-forest/index.html
const DIR = PAGE ? path.posix.dirname(PAGE) + '/' : '';
const MAIN_KEYS = ['eiheiji_vs_beasts_v010', 'REWILDED_EIHEIJI_SETTINGS', 'eiheiji_weatherEffects', 'eiheiji_shadow', 'eiheiji_perf', 'eiheiji_aimMode', 'eiheiji_detail'];
const HTML = fs.readFileSync(PAGE ? path.join(ROOT, PAGE) : (process.env.FELL_HTML || path.join(ROOT, 'index.html')), 'utf8').replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){');
let ok = true;
const check = (c, msg) => { console.log((c ? 'ok   ' : 'FAIL ') + msg); ok = ok && !!c; };
const BASE = `(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.mutantMet=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; prog.arms.axeIron=WEAPONS.axeIron.maxDur; P.weapon='axeIron'; P.dur=prog.arms.axeIron; refreshWeaponMesh(); prog.f4.hint=1; return 1; })()`;
const CALM = "(()=>{ for(const e of enemies) if(!e.removed&&e.x>4000&&dist(e.x,e.z,P.x,P.z)<200) e.x+=3000; prog.f10.tod=150; f10LightNow(); P.hp=P.maxHp; return 1; })()";
// 立つ所：木 kt から r+dd の所で、歩けて何も無い所。木の方を向く
const WALKABLE = `(x,z)=>f4Free(x,z,0.55)&&[[0,0],[-0.5,0],[0.5,0],[0,-0.5],[0,0.5]]
  .every(([dx,dz])=>kamiReach(x+dx,z+dz))`;
const STAND = `async (kt,dd)=>{
  const safe=${WALKABLE};
  for(let k=0;k<16;k++){
    const a=k/16*TAU+hash2(kt.x,kt.z), r=kt.col.r+dd, x=kt.x+Math.sin(a)*r, z=kt.z+Math.cos(a)*r;
    if(!safe(x,z)) continue;
    P.x=x; P.z=z; P.facing=Math.atan2(kt.x-x,kt.z-z); setCam(P.facing);
    const t=f4FindTarget(1.6), c=interactables();
    if(!c||t?.type!=='tree'||t.rec.key!==kt.key) continue;
    for(let i=0;i<2;i++) await new Promise(resolve=>requestAnimationFrame(resolve));
    if(dist(P.x,P.z,x,z)<0.1&&curInter?.label===c.label&&curInter?.d===c.d) return true;
  }
  return false;
}`;
// まわり r m の木の種類
const NEAR = `(kt,r)=>{ const c={sugi:0,kona:0}; for(const t of REG.live.ktrees.values()){ if(t===kt||t.felled||!t.ty) continue; if(dist(t.x,t.z,kt.x,kt.z)<r) c[t.ty]=(c[t.ty]||0)+1; } for(const t of E2.take||[]) if(dist(t.x,t.z,kt.x,kt.z)<r) c.take=(c.take||0)+1; return c; }`;

async function setup(ctxOpt) {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext(ctxOpt);
  const pg = await ctx.newPage(); const errs = []; pg.on('pageerror', e => errs.push(String(e)));
  await ctx.route('**/*', async r => { const u = r.request().url();
    if (u.includes('three.min.js') || u.includes('three.js/r128')) return r.fulfill({ body: THREE, contentType: 'application/javascript' });
    if (!u.startsWith('http://game.local/')) return r.abort();
    const p = decodeURIComponent(u.slice(18).split('?')[0]); if (p === 'seed.html') return r.fulfill({ body: '<!doctype html><title>seed</title>', contentType: 'text/html' });
    if (p === DIR || p === DIR + 'index.html') return r.fulfill({ body: HTML, contentType: 'text/html; charset=utf-8' });
    const fp = path.join(ROOT, p); if (fs.existsSync(fp) && fs.statSync(fp).isFile()) return r.fulfill({ body: fs.readFileSync(fp) }); return r.fulfill({ status: 404, body: '' }); });
  const E = c => pg.evaluate(c => window.__ev(c), c);
  const until = async (js, ms = 60000) => { for (const deadline = performance.now() + ms; performance.now() < deadline;) { if (await E(js)) return true; await pg.waitForTimeout(250); } return false; };
  return { b, ctx, pg, errs, E, until };
}
async function start(S, touch) {
  const { pg, E, until } = S;
  if (PAGE) { await pg.goto('http://game.local/seed.html'); await pg.evaluate(K => { for (const k of K) localStorage.setItem(k, 'MAIN:' + k); }, MAIN_KEYS); } // 本編のキーに前もって値を入れておく
  await pg.goto('http://game.local/' + DIR, { waitUntil: 'load', timeout: 300000 });
  await pg.waitForFunction("typeof window.__ev==='function'", null, { timeout: 300000 });
  if (touch) await pg.tap('#btnNew'); else await pg.click('#btnNew');
  await pg.waitForTimeout(500);
  for (let i = 0; i < 15; i++) { if (await pg.evaluate("document.getElementById('dialog').hidden")) break; await E("(advanceDialog(),1)"); await pg.waitForTimeout(150); }
  await E(BASE);
  await E("(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()");
  assert(await until(READY, 240000), '上志比の開始状態を読み込めない');
  await pg.waitForTimeout(800); await E(CALM);
}
const PC = { viewport: { width: 1100, height: 680 } };
const READY = "REG.cur==='kamishihi'&&!REG.busy&&!!REG.live?.ktrees&&S.mode==='playing'";
const PLANT = '広葉樹の切り株に苗木を植える';
const BROADLEAF = /^(太い)?広葉樹を切る［/;
const STUMPS = `(x,z)=>prog.kami.fb.filter(key=>{
  const t=REG.live.ktrees.get(key);
  return t?.kona&&t.felled&&prog.kami.pl[key]==null&&dist(t.x,t.z,x,z)<=2.5;
})`;
const SHOWN = `(()=>{
  const c=curInter, fresh=interactables();
  const same=!!c&&c.label===fresh?.label&&c.d===fresh?.d;
  const stumps=(${STUMPS})(P.x,P.z);
  let key=c?.chop?.rec?.key??null, source=key?'chop':null;
  if(same&&c.label.startsWith(${JSON.stringify(PLANT)})&&stumps.length===1){
    key=stumps[0]; source='isolated-stump';
  }
  // 比較用の伐採修正前HTMLには chop がない。旧版の案内を照合し、既存の判定で差を検出する。
  if(same&&typeof f4ShownTarget==='undefined'&&/^(細い木|(太い)?(杉|広葉樹))(を切る［|：)/.test(c.label)){
    const t=f4FindTarget(1.6);
    if(t?.type==='tree'){ key=t.rec.key; source='legacy-prompt'; }
  }
  return {key,source,label:c?.label??null,freshLabel:fresh?.label??null,same,stumps};
})()`;
const ISOLATED = `(x,z)=>{
  for(const t of REG.live.ktrees.values()) if(t.felled&&dist(x,z,t.x,t.z)<8) return false;
  for(const tr of F4.trunks) if(segDist(x,z,...trunkSeg(tr))<8) return false;
  for(const l of REG.live.kw.logs){
    const dx=Math.sin(l[2])*LOG_LEN/2, dz=Math.cos(l[2])*LOG_LEN/2;
    if(segDist(x,z,l[0]-dx,l[1]-dz,l[0]+dx,l[1]+dz)<8) return false;
  }
  return true;
}`;

async function nextFrames(pg, n = 2) {
  await pg.evaluate(async count => {
    for (let i = 0; i < count; i++) await new Promise(resolve => requestAnimationFrame(resolve));
  }, n);
}

async function waitShown(S, pred, ms = 15000, trace = '操作対象', expected = null, complete = 'false') {
  await nextFrames(S.pg);
  const deadline = performance.now() + ms;
  const read = `(()=>{ const shown=${SHOWN}; return {shown,ready:!!(${pred}),complete:!!(${complete})}; })()`;
  let state;
  do {
    state = await S.E(read);
    if (state.complete) return null;
    if (state.ready) return state.shown;
    await S.pg.waitForTimeout(100);
  } while (performance.now() < deadline);
  const game = await S.E('({mode:S.mode,dead:P.dead,x:P.x,z:P.z,attacking:!!P.atk,region:REG.cur})');
  throw new Error(`${trace} 狙い=${JSON.stringify(expected)} 実際=${JSON.stringify(state.shown)} 状態=${JSON.stringify(game)}`);
}

async function runCase(label, fn) {
  try { await fn(); } catch (error) { check(false, `${label} ${error.stack || error}`); }
}

async function withGame(options, touch, fn) {
  const S = await setup(options);
  try {
    await start(S, touch);
    await fn(S);
    if (PAGE) await mainKeysKept(S, touch ? 'iPhone' : 'PC');
  } finally {
    check(!S.errs.length, `${touch?'iPhone':'PC'}：エラーなし ${JSON.stringify(S.errs.slice(0, 3))}`);
    await S.b.close();
  }
}

const keyPress = (S, key) => () => S.pg.keyboard.press(key);
const treeState = (S, key) => S.E(`REG.live.ktrees.get(${JSON.stringify(key)})?.felled===true`);

async function isolatedTree(S, species, exclude = []) {
  const ret = await S.E(`(()=>{
    const safe=${ISOLATED}, walkable=${WALKABLE}, excluded=${JSON.stringify(exclude)};
    for(const t of REG.live.ktrees.values()){
      if(t.ty!==${JSON.stringify(species)}||t.felled||excluded.includes(t.key)||!kamiReach(t.x,t.z)||!safe(t.x,t.z)) continue;
      for(let k=0;k<16;k++){
        const a=k/16*TAU+hash2(t.x,t.z), r=t.col.r+0.9, x=t.x+Math.sin(a)*r, z=t.z+Math.cos(a)*r;
        if(!walkable(x,z)||!safe(x,z)) continue;
        P.x=x; P.z=z; P.facing=Math.atan2(t.x-x,t.z-z); setCam(P.facing);
        const c=interactables(), aim=f4FindTarget(1.3);
        if(c?.chop?.rec?.key===t.key || (typeof f4ShownTarget==='undefined'&&aim?.type==='tree'&&aim.rec.key===t.key&&/^(太い)?(杉|広葉樹)を切る［/.test(c?.label||''))) return [t.key,c.label];
      }
    }
    return null;
  })()`);
  assert(ret, `${species} の孤立した伐採対象が見つからない（除外 ${JSON.stringify(exclude)}、倒木・幹・丸太から8m以上）`);
  return ret;
}

async function plantAt(S, key, trace) {
  const id = JSON.stringify(key);
  const pl = await S.E(`(()=>{
    const t=REG.live.ktrees.get(${id}), stumps=${STUMPS};
    if(!t?.felled) return null;
    for(let k=0;k<24;k++){
      const a=k/24*TAU, x=t.x+Math.cos(a), z=t.z+Math.sin(a);
      if(!kamiReach(x,z)||!f4Free(x,z,0.4)) continue;
      const keys=stumps(x,z);
      if(keys.length!==1||keys[0]!==t.key) continue;
      P.x=x; P.z=z; P.facing=Math.atan2(t.x-x,t.z-z); setCam(P.facing);
      const c=interactables();
      if(c?.label.startsWith(${JSON.stringify(PLANT)})) return c.label;
    }
    return null;
  })()`);
  if (!pl) throw new Error(`${trace} 狙い=${key} 実際=${JSON.stringify(await S.E(SHOWN))}。対象のみが2.5m以内にある植林位置を確保できない`);
  await S.E('(cv.focus(),1)');
  const read = () => S.E(`({keys:Object.keys(prog.kami.pl),seeds:inv.naegi||0,
    felled:REG.live.ktrees.get(${id}).felled,planted:prog.kami.pl[${id}]!=null})`);
  const before = await read();
  assert(before.felled && !before.planted && before.seeds > 0, `${trace} 狙い=${key} 植林前=${JSON.stringify(before)}`);
  const shown = await waitShown(S, `shown.same&&shown.source==='isolated-stump'&&shown.key===${id}`, 15000, trace, key);
  console.log(`   ${trace} E直前 狙い=${key} curInter=${JSON.stringify(shown)} 前=${JSON.stringify(before)}`);
  await S.pg.keyboard.press('e');
  await S.until(`Object.keys(prog.kami.pl).length!==${before.keys.length}||inv.naegi!==${before.seeds}`, 10000);
  const after = await read();
  const added = after.keys.filter(k => !before.keys.includes(k));
  const removed = before.keys.filter(k => !after.keys.includes(k));
  console.log(`   ${trace} E後 狙い=${key} 実際の追加=${JSON.stringify(added)} 後=${JSON.stringify(after)}`);
  assert(added.length === 1 && added[0] === key && !removed.length && after.seeds === before.seeds - 1 && after.felled && after.planted,
    `${trace} 狙い=${key} curInter=${JSON.stringify(shown)} 追加=${JSON.stringify(added)} 消失=${JSON.stringify(removed)} 前=${JSON.stringify(before)} 後=${JSON.stringify(after)}`);
  return { pl, planted: [after.planted, after.felled] };
}

async function growAt(S, key) {
  await S.E('(()=>{ stats.time+=E2.grow+5; E2.t=0; return 1; })()');
  return S.until(`!REG.live.ktrees.get('${key}').felled&&prog.kami.pl['${key}']==null&&!prog.kami.fb.includes('${key}')`, 60000);
}

// 新しく倒れた木の番号をすべて返す。
async function chopWith(S, press, watchKey, trace = '') {
  const { pg, E } = S;
  const before = await E(`[...REG.live.ktrees.values()].filter(t=>t.felled).map(t=>t.key)`);
  for (let i = 0; i < 40; i++) {
    for (let k = 0; k < 6 && !(await pg.evaluate("document.getElementById('dialog').hidden")); k++) { await E('(advanceDialog(),1)'); await pg.waitForTimeout(120); }
    if (await E(`!!REG.live.ktrees.get('${watchKey}').felled`)) break;
    await E(CALM);
    if (!(await E('touchMode'))) await E('(cv.focus(),1)');
    const id = JSON.stringify(watchKey);
    const actual = await waitShown(S, `shown.same&&shown.key===${id}&&(shown.source==='chop'||shown.source==='legacy-prompt')`,
      15000, trace || '伐採の操作対象', watchKey, `REG.live.ktrees.get(${id})?.felled===true`);
    if (!actual) break;
    if (trace) console.log(`   ${trace} 入力${i+1} 狙い=${watchKey} curInter=${JSON.stringify(actual)}`);
    await press(); await pg.waitForTimeout(650);
    assert(await S.until('!P.atk&&P.stagger<=0', 15000), `${trace || '伐採'} 狙い=${watchKey} の入力後に攻撃動作が終わらない`);
  }
  await pg.waitForTimeout(300);
  if (await treeState(S, watchKey)) {
    const settled = `P.stagger<=0&&F4.trunks.every(t=>t.rec?.key!==${JSON.stringify(watchKey)}||(t.fall<0&&!(t.roll>0)))`;
    assert(await S.until(settled, 30000), `${trace || '伐採'} 狙い=${watchKey} の倒木と主人公が静止しない`);
  }
  return E(`(()=>{ const b=new Set(${JSON.stringify(before)}); return [...REG.live.ktrees.values()].filter(t=>t.felled&&!b.has(t.key)).map(t=>t.key); })()`);
}

async function fellingAndPlanting(S, rememberGrowthKey) {
  const { pg, E, until } = S;
  const J = keyPress(S, 'j');
  const Ek = keyPress(S, 'e');

  // 1 杉だけの所
  let kt = await E(`(async()=>{ const ST=${STAND}, NR=${NEAR}; for(const t of REG.live.ktrees.values()){ if(t.ty!=='sugi'||t.felled||!kamiReach(t.x,t.z)) continue; const c=NR(t,5); if(c.kona||c.take||!c.sugi) continue; if(await ST(t,0.8)){ window.__t=t; window.__s={n:inv.naegi||0}; return [t.key,interactables().label]; } } return null; })()`);
  assert(kt?.[1], '1 杉の伐採位置と案内が見つからない');
  let felled = await chopWith(S, J, kt[0]);
  let r = await E(`[prog.kami.f.includes('${kt[0]}'), prog.kami.fb.includes('${kt[0]}'), (inv.naegi||0)-__s.n]`);
  check(/^(太い)?杉を切る［/.test(kt[1]) && felled.length === 1 && felled[0] === kt[0] && r[0] && !r[1] && r[2] === 0, `1 杉だけの所で杉を切る（J）：案内「${kt[1].replace(/［.*/, '')}」・倒れた ${JSON.stringify(felled)}・f ${r[0]}・fb ${r[1]}・苗木 +${r[2]}`);
  const sugiKey = kt[0];
  // 2 広葉樹だけの所
  kt = await E(`(async()=>{ const ST=${STAND}, NR=${NEAR}; for(const t of REG.live.ktrees.values()){ if(t.ty!=='kona'||t.felled||!kamiReach(t.x,t.z)) continue; const c=NR(t,5); if(c.sugi||c.take||!c.kona) continue; if(await ST(t,0.8)){ window.__t=t; window.__s={n:inv.naegi||0,hw:inv.hardwood||0}; return [t.key,interactables().label]; } } return null; })()`);
  assert(kt?.[1], '2 広葉樹の伐採位置と案内が見つからない');
  rememberGrowthKey(kt[0]);
  felled = await chopWith(S, J, kt[0]);
  r = await E(`[prog.kami.fb.includes('${kt[0]}'), prog.kami.f.includes('${kt[0]}'), (inv.naegi||0)-__s.n, [...document.querySelectorAll('#toasts > *')].some(t=>t.textContent.includes('広葉樹を切った'))]`);
  check(/^(太い)?広葉樹を切る［/.test(kt[1]) && felled.length === 1 && felled[0] === kt[0] && r[0] && !r[1] && r[2] === 1 && r[3], `2 広葉樹だけの所で広葉樹を切る（J）：案内「${kt[1].replace(/［.*/, '')}」・倒れた ${JSON.stringify(felled)}・fb ${r[0]}・f ${r[1]}・苗木 +${r[2]}・通知 ${r[3]}`);
  const konaKey = kt[0];
  if (PAGE) await runCase('P1・P2 PC', () => previewUI(S, false, konaKey));
  // 7 広葉樹の丸太：枝を払う（J）→ 丸太の名前 → 割る（J）→ 山地の硬木
  assert(await until(`F4.trunks.some(t=>t.rec?.key==='${konaKey}'&&t.fall<0&&!(t.roll>0))`),
    `7 狙い=${konaKey} の幹が倒れ終わらない`);
  const tr = await E(`(()=>{ const tr=F4.trunks.find(t=>t.rec&&t.rec.key==='${konaKey}'); if(!tr) return null; const [ax,az,bx,bz]=trunkSeg(tr); const mx=(ax+bx)/2, mz=(az+bz)/2, nx=-(bz-az), nz=(bx-ax), L=Math.hypot(nx,nz)||1;
    for(const s of [1,-1]) for(const d of [0.9,1.2]){ const x=mx+nx/L*d*s, z=mz+nz/L*d*s; if(kamiReach(x,z)){ P.x=x; P.z=z; P.facing=Math.atan2(mx-x,mz-z); setCam(P.facing); const target=f4FindTarget(1.3), c=interactables();
      if(target?.tr!==tr||!c?.label.startsWith('枝を払う')) continue; window.__n0=REG.live.kw.logs.length; return c.label; } } return null; })()`);
  assert(tr, `7 狙い=${konaKey} の枝払い位置が見つからない`);
  for (let i = 0; i < 30 && await E(`F4.trunks.some(t=>t.rec?.key==='${konaKey}')`); i++) {
    await E(CALM);
    await waitShown(S, `shown.same&&shown.label?.startsWith('枝を払う')&&f4FindTarget(1.3)?.tr?.rec?.key==='${konaKey}'`,
      15000, '7 枝払い', konaKey);
    await J(); await pg.waitForTimeout(650);
  }
  assert(await E(`!F4.trunks.some(t=>t.rec?.key==='${konaKey}')`), `7 狙い=${konaKey} を丸太にできない`);
  const logs = await E(`REG.live.kw.logs.slice(__n0).map(l=>[l[3],l[5]?1:0,l[6]?1:0])`);
  const lab = await E(`(()=>{ const l=REG.live.kw.logs.slice(__n0).find(l=>l[5]); if(!l) return null; P.x=l[0]+Math.cos(l[2])*0.7; P.z=l[1]-Math.sin(l[2])*0.7; P.facing=Math.atan2(l[0]-P.x,l[1]-P.z); setCam(P.facing); window.__lg=l; const c=interactables(); return c&&c.label; })()`);
  for (let k = 0; k < 2; k++) {
    assert(await E("typeof __lg!=='undefined'&&REG.live.kw.logs.includes(__lg)"), `7 硬木の丸太${k+1}本目が見つからない`);
    for (let i = 0; i < 20 && await E('REG.live.kw.logs.includes(__lg)'); i++) {
      await E(CALM);
      await waitShown(S, "shown.same&&shown.label?.includes('の丸太')&&f4FindTarget(1.3)?.l===__lg",
        15000, '7 丸太を割る', `${k+1}本目`);
      await J(); await pg.waitForTimeout(650);
    }
    if (k === 0) await E(`(()=>{ const l=REG.live.kw.logs.slice(__n0).find(l=>l[5]); if(!l) return 0; P.x=l[0]+Math.cos(l[2])*0.7; P.z=l[1]-Math.sin(l[2])*0.7; P.facing=Math.atan2(l[0]-P.x,l[1]-P.z); setCam(P.facing); window.__lg=l; return 1; })()`);
  }
  r = await E(`[(inv.hardwood||0)-__s.hw]`);
  check(tr && logs.length >= 3 && logs.every(l => l[2] === 1) && logs.filter(l => l[1]).length === 2 && lab && /^(太い)?広葉樹の丸太（ここからは運べない）　割る：木材\+\d・山地の硬木\+1［/.test(lab) && r[0] === 2,
    `7 広葉樹の丸太：枝を払う（J）→ 丸太 ${JSON.stringify(logs)}・案内「${lab}」→ 割る（J）で山地の硬木 +${r[0]}`);
  // 杉の丸太は「杉の丸太」・硬木の印なし
  const sl = await E(`(()=>{ const tr=F4.trunks.find(t=>t.rec&&t.rec.key==='${sugiKey}'); return tr?tr.size:'(もう丸太)'; })()`);
  // 3・4 杉と広葉樹が近い所：案内に出ている木を、攻撃（J）でも切る
  const mixed = [];
  for (const want of ['kona', 'sugi', 'kona', 'sugi']) {
    const m = await E(`(()=>{ const walkable=${WALKABLE}; const L=[...REG.live.ktrees.values()].filter(t=>t.ty&&!t.felled&&kamiReach(t.x,t.z));
      for(const a of L){ if(a.ty!=='${want}') continue; const b=L.find(t=>t!==a&&t.ty!==a.ty&&dist(t.x,t.z,a.x,a.z)<2.6); if(!b) continue;
        for(let k=0;k<16;k++){ const ang=k/16*TAU, x=a.x+Math.sin(ang)*(a.col.r+0.9), z=a.z+Math.cos(ang)*(a.col.r+0.9); if(!walkable(x,z)) continue; if(dist(x,z,b.x,b.z)-b.col.r>1.6) continue;
          P.x=x; P.z=z; P.facing=Math.atan2(a.x-x,a.z-z)+0.35; setCam(P.facing); const c=interactables(), tg=c?.chop; if(!tg||tg.rec.key!==a.key) continue;
          window.__s={n:inv.naegi||0}; return [a.key,a.ty,b.ty,c.label]; } } return null; })()`);
    if (!m) {
      check(false, `3 ${want} の混在位置で対象キー付きの伐採案内が見つからない`);
      mixed.push(null); continue;
    }
    const f2 = await chopWith(S, J, m[0]);
    const g = await E(`[(inv.naegi||0)-__s.n, prog.kami.fb.includes('${m[0]}'), prog.kami.f.includes('${m[0]}')]`);
    mixed.push({ key: m[0], ty: m[1], near: m[2], label: m[3].replace(/［.*/, ''), felled: f2, naegi: g[0], fb: g[1], f: g[2] });
  }
  const mixOk = mixed.every(m => m && m.felled.length === 1 && m.felled[0] === m.key && (m.ty === 'kona' ? m.naegi === 1 && m.fb && !m.f && /広葉樹を切る/.test(m.label) : m.naegi === 0 && m.f && !m.fb && /杉を切る/.test(m.label)));
  check(mixOk, `3 杉と広葉樹が近い所で、案内に出ている木を攻撃（J）で切る ${JSON.stringify(mixed.map(m => m && [m.ty, m.label, m.felled.length === 1 && m.felled[0] === m.key, m.naegi]))}`);
  // 4 たくさんの立ち位置で、案内の木と攻撃で切る木が同じか（攻撃の向きは少しずらす）
  const st = await E(`(()=>{ const L=[...REG.live.ktrees.values()].filter(t=>t.ty&&!t.felled&&kamiReach(t.x,t.z)); let n=0, same=0, diff=0, miss=0;
    for(let i=0;i<L.length&&n<3000;i+=3){ const kt=L[i]; for(const dd of [0.5,0.9,1.2,1.45]){ const a=hash2(kt.x*1.3+dd,kt.z)*TAU, x=kt.x+Math.sin(a)*(kt.col.r+dd), z=kt.z+Math.cos(a)*(kt.col.r+dd); if(!kamiReach(x,z)||!f4Free(x,z,0.35)) continue;
      P.x=x; P.z=z; P.facing=Math.atan2(kt.x-x,kt.z-z)+(hash2(x,z)-0.5)*0.8; curInter=interactables(); const shown=curInter&&curInter.chop; if(!shown||shown.type!=='tree') continue; n++;
      const atk=(typeof f4ShownTarget==='function'&&f4ShownTarget())||f4FindTarget(1.3); if(!atk) miss++; else if(atk.type==='tree'&&atk.rec.key===shown.rec.key) same++; else diff++; } }
    return {n,same,diff,miss}; })()`);
  check(st.n > 1000 && st.same === st.n, `4 案内の木と攻撃で切る木が同じ：${JSON.stringify(st)}`);
  // 4b 「調べる」（E）でも同じ木を切る
  kt = await E(`(async()=>{ const ST=${STAND}; for(const t of REG.live.ktrees.values()){ if(t.ty!=='kona'||t.felled||!kamiReach(t.x,t.z)) continue; if(await ST(t,1.1)){ window.__s={n:inv.naegi||0}; const c=interactables(); return [t.key,c&&c.chop&&c.chop.rec.key,c&&c.label]; } } return null; })()`);
  assert(kt?.[2], '4b 広葉樹を調べる位置と案内が見つからない');
  felled = await chopWith(S, Ek, kt[0]);
  r = await E(`(inv.naegi||0)-__s.n`);
  check(kt[1] === kt[0] && felled.length === 1 && felled[0] === kt[0] && r === 1, `4 「調べる」（E）で案内の広葉樹を切る：倒れた ${JSON.stringify(felled)}・苗木 +${r}`);
  await runCase('8 植林と成長', async () => {
    const { pl, planted } = await plantAt(S, konaKey, '8 植林');
    const grew = await growAt(S, konaKey);
    const relab = await E(`(async()=>{ const kt=REG.live.ktrees.get('${konaKey}'); const ST=${STAND}; if(!(await ST(kt,0.8))) return null; const c=interactables(); return c&&c.label; })()`);
    check(pl && planted[0] && planted[1] && grew && BROADLEAF.test(relab || ''),
      `8 切り株に苗木を植える（E）→ 時間がたつと広葉樹に育つ → 案内「${(relab || '').replace(/［.*/, '')}」`);
  });
}

async function saveAndResume(S, growthKey) {
  const { pg, E, until } = S;
  const J = keyPress(S, 'j');
  const [sugiKey] = await isolatedTree(S, 'sugi');
  assert.deepEqual(await chopWith(S, J, sugiKey, '9 杉の準備'), [sugiKey], '9 杉1本の伐採');
  const [konaKey] = await isolatedTree(S, 'kona', [sugiKey]);
  assert.deepEqual(await chopWith(S, J, konaKey, '9 成長用広葉樹の準備'), [konaKey], '9 成長用広葉樹1本の伐採');
  await plantAt(S, konaKey, '9 成長用の植林');
  assert(await growAt(S, konaKey), `9 成長用広葉樹 ${konaKey} が育たない`);

  // 独立したセーブで既存の硬木2個も復元検証の対象にする。
  await E('inv.hardwood=2');
  const [kona2] = await isolatedTree(S, 'kona', [sugiKey, konaKey, growthKey]);
  assert.deepEqual(await chopWith(S, J, kona2, '9 保存用広葉樹の伐採'), [kona2], '9 保存用広葉樹1本の伐採');
  await E('inv.naegi=(inv.naegi||0)+1');
  await plantAt(S, kona2, '9 保存用の植林');
  const stored = await E(`(()=>{ saveGame(); const d=JSON.parse(localStorage.getItem(SAVE_KEY)); return {
    time:d?.kami?.pl?.['${kona2}']??null, liveTime:Math.floor(prog.kami.pl['${kona2}']),
    felled:d?.kami?.fb?.includes('${kona2}')??false
  }; })()`);
  assert(stored.felled && Number.isFinite(stored.time) && stored.time === stored.liveTime,
    `9 保存前 狙い=${kona2} の植林・伐採記録 ${JSON.stringify(stored)}`);
  console.log(`   9 保存前 狙い=${kona2} JSON=${JSON.stringify(stored)}`);

  const pre = await E(`({naegi:inv.naegi, hw:inv.hardwood||0, f:prog.kami.f.length, fb:prog.kami.fb.length, pl:Object.keys(prog.kami.pl).length})`);
  await pg.reload({ waitUntil: 'load', timeout: 300000 });
  await pg.waitForFunction("typeof window.__ev==='function'", null, { timeout: 300000 });
  await pg.click('#btnContinue');
  assert(await until(READY, 240000), '9 つづきからの上志比の読み込みが完了しない');
  await nextFrames(pg);
  const post = await E(`({naegi:inv.naegi, hw:inv.hardwood||0, f:prog.kami.f.length, fb:prog.kami.fb.length, pl:Object.keys(prog.kami.pl).length,
    sugi:[REG.live.ktrees.get('${sugiKey}').felled, prog.kami.f.includes('${sugiKey}')], grown:[REG.live.ktrees.get('${konaKey}').felled, prog.kami.fb.includes('${konaKey}')],
    kona2:[REG.live.ktrees.get('${kona2}').felled, prog.kami.fb.includes('${kona2}'), prog.kami.pl['${kona2}']!=null], ty:[REG.live.ktrees.get('${konaKey}').ty, REG.live.ktrees.get('${sugiKey}').ty]})`);
  check(post.naegi === pre.naegi && post.hw === pre.hw && post.f === pre.f && post.fb === pre.fb && post.pl === pre.pl && post.sugi[0] && post.sugi[1] && !post.grown[0] && !post.grown[1] && post.kona2.every(Boolean) && post.ty[0] === 'kona' && post.ty[1] === 'sugi',
    `9 セーブして読み込み直す（つづきから）：${JSON.stringify(pre)} → ${JSON.stringify(post)}`);
  const SK = PAGE ? 'eiheiji_vs_beasts_p3e2forest' : 'eiheiji_vs_beasts_v010';
  check(await E('SAVE_KEY') === SK && await E("JSON.parse(localStorage.getItem(SAVE_KEY)).v") === 1, `9 セーブの形は同じ（SAVE_KEY「${SK}」・v:1）`);
}

// 試遊版：新しい形の案内に「広葉樹を切る」と出る・案内を押しても木を切り始めない・詳しい説明を開いても（切り株の）操作は起きない
// 木の案内「広葉樹を切る［鉄の斧・約4回］…」は全角の角括弧なので、新しい形でも短くならず「詳しく」も付かない（案内を小さくする決まりは全角の丸括弧だけを省く）
async function previewUI(S, touch, stumpKey) {
  const { pg, E } = S; const tag = touch ? '［iPhone の再現］' : '［PC］';
  const press = async () => { if (touch) await pg.tap('#prompt'); else await pg.click('#prompt'); };
  const k = await E(`(async()=>{ const ST=${STAND}; for(const t of REG.live.ktrees.values()){ if(t.ty!=='kona'||t.felled||!kamiReach(t.x,t.z)) continue; if(await ST(t,0.9)){ window.__u=t; return t.key; } } return null; })()`);
  assert(k, `P1 ${tag}広葉樹の前に立てない`);
  await E(CALM); await pg.waitForTimeout(700); await nextFrames(pg);
  const a = await E("[PUI.on, $('prompt').className, $('prompt').textContent, curInter&&curInter.chop&&curInter.chop.rec.key, Math.round($('prompt').getBoundingClientRect().height)]");
  check(a[0] && a[1].includes('cmp') && /^(E)?(太い)?広葉樹を切る［鉄の斧・約\d+回］/.test(a[2]) && a[3] === k && a[4] <= 30, `P1 ${tag}新しい形（小さな1行・高さ ${a[4]}px）の案内に「${a[2]}」・案内の木＝目の前の広葉樹`);
  const c0 = await E(`[F4.chop.size, inv.naegi||0]`);
  await press(); await pg.waitForTimeout(700);
  const b = await E(`[F4.chop.size, !!P.atk, __u.felled, F4.chop.has(__u.key), $('prompt').classList.contains('open')]`);
  check(b[0] === c0[0] && !b[1] && !b[2] && !b[3], `P2 ${tag}木の案内を押しても切り始めない（切りかけ ${c0[0]}→${b[0]}・攻撃 ${b[1]}・倒れた ${b[2]}）`);
  // 詳しい説明が開ける切り株の案内（「広葉樹の切り株に苗木を植える（苗木 N）」）で開いて閉じる：植える操作は起きない
  const st = await E(`(()=>{ const kt=REG.live.ktrees.get('${stumpKey}'); if(!kt) return null; for(const rr of [1.0,1.2,0.8,1.4]) for(let i=0;i<24;i++){ const ang=i/24*TAU; P.x=kt.x+Math.cos(ang)*rr; P.z=kt.z+Math.sin(ang)*rr; const c=interactables(); if(c&&c.label.startsWith('広葉樹の切り株に苗木を植える')){ P.facing=Math.atan2(kt.x-P.x,kt.z-P.z); window.__sp=[P.x,P.z]; return c.label; } } return null; })()`);
  await E(CALM); await pg.waitForTimeout(700); await nextFrames(pg);
  const n0 = await E(`[inv.naegi||0, prog.kami.pl['${stumpKey}']!=null, $('prompt').textContent]`);
  await E('(P.x=__sp[0],P.z=__sp[1],1)'); await press(); await pg.waitForTimeout(700);
  const o = await E(`[$('prompt').classList.contains('open'), $('prompt').textContent, inv.naegi||0, prog.kami.pl['${stumpKey}']!=null, !!P.atk]`);
  await E('(P.x=__sp[0],P.z=__sp[1],1)'); await press(); await pg.waitForTimeout(500);
  const cl = await E(`[$('prompt').classList.contains('open'), inv.naegi||0, prog.kami.pl['${stumpKey}']!=null]`);
  const bd = touch ? '' : 'E'; // PC は「E」の札が付く
  check(st && n0[2] === bd + '広葉樹の切り株に苗木を植える詳しく' && o[0] && o[1] === bd + st + '閉じる' && o[2] === n0[0] && !o[3] && !o[4] && !cl[0] && cl[1] === n0[0] && !cl[2],
    `P2 ${tag}切り株の詳しい説明を開く（「${o[1]}」）→ 閉じる：苗木 ${n0[0]}→${o[2]}→${cl[1]}・植えていない ${!cl[2]}・攻撃 ${o[4]}`);
}
// 試遊版：本編のキー7つ（前もって入れた値）が変わっていない
async function mainKeysKept(S, tag) {
  const { pg } = S; await pg.goto('http://game.local/seed.html');
  const r = await pg.evaluate(K => K.map(k => localStorage.getItem(k) === 'MAIN:' + k), MAIN_KEYS);
  const mine = await pg.evaluate(() => Object.keys(localStorage).filter(k => !String(localStorage.getItem(k)).startsWith('MAIN:')).sort());
  check(r.every(Boolean) && mine.includes('eiheiji_vs_beasts_p3e2forest'), `P3 ［${tag}］本編のキー7つは変わっていない ${JSON.stringify(r)}・試遊版が使ったキー ${JSON.stringify(mine)}`);
}

async function phoneFelling(T) {
  let lastKona = null; // 試遊版の確かめ（P2 の切り株）に使う
  for (const [btn, name] of [['#tbAtk', '攻撃'], ['#tbAct', '調べる']]) {
    await runCase(`10 iPhone ${name}`, async () => {
      const k2 = await isolatedTree(T, 'kona');
      lastKona = k2[0];
      const before = await T.E('inv.naegi||0');
      const f3 = await chopWith(T, () => T.pg.tap(btn), k2[0], `10 iPhone ${name}`);
      const g = await T.E(`[(inv.naegi||0)-${before}, prog.kami.fb.includes('${k2[0]}'), touchMode]`);
      check(BROADLEAF.test(k2[1] || '') && f3.length === 1 && f3[0] === k2[0] && g[0] === 1 && g[1] && g[2], `10 iPhone の再現：「${name}」ボタンのタップで広葉樹を切る（狙い=${k2[0]}・案内「${(k2[1] || '').replace(/［.*/, '')}」・倒れた ${JSON.stringify(f3)}・苗木 +${g[0]}）`);
    });
  }
  if (PAGE) await runCase('P1・P2 iPhone', async () => { assert(lastKona, 'P2 iPhone の切り株が無い'); await previewUI(T, true, lastKona); });
}

(async () => {
  // 共有するのは項目8の対象IDだけ。項目9のゲームと保存領域は初期状態から用意する。
  let growthKey = null;
  await runCase('1〜8 PC', () => withGame(PC, false, S => fellingAndPlanting(S, key => { growthKey = key; })));
  await runCase('9 独立したPCブラウザー', () => withGame(PC, false, S => saveAndResume(S, growthKey)));
  await runCase('10 iPhone', () => withGame({ ...devices['iPhone 13'] }, true, phoneFelling));
  console.log(ok ? 'PASS: 上志比の伐採（樹種・案内・切る木・苗木・硬木・植林・セーブ）' : 'FAILED');
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
