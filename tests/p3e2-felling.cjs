#!/usr/bin/env node
// 上志比の伐採（v0.88 伐採の修正）の確認（画面のない Chromium。Node の Playwright。10分ほど）。docs/p3e2-felling-fix.md
// 実際の操作に近い形で確かめる：PC は J（攻撃）と E（調べる）を押す。iPhone の再現は「攻撃」「調べる」ボタンをタップする
//  1 杉だけの所で杉を切る（f・苗木なし・案内は「杉」）  2 広葉樹だけの所で広葉樹を切る（fb・苗木+1・案内は「広葉樹」）
//  3 杉と広葉樹が近い所で、それぞれを切る（案内に出ている木を切る）  4 案内の木と攻撃で切る木が同じ（たくさんの立ち位置で数える）
//  5・6 苗木（広葉樹は+1・杉は0）  7 広葉樹の丸太（名前・はじめの2本は割ると山地の硬木）  8 植林と成長
//  9 セーブして読み込み直す（つづきから）  10 iPhone の再現（タップ）
// 使い方：THREE_JS=…/three.min.js node tests/p3e2-felling.cjs   （FELL_HTML=別の index.html で、直す前の版と比べる）
// 試遊版そのものを確かめる：FELL_PAGE=previews/p3e2-forest/index.html（その置き場所から開く。新しい形の案内・詳しい説明を開いても切らない・試遊版の保存キー・本編のキーに触れない、も確かめる）
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
const STAND = `(kt,dd)=>{ for(let k=0;k<16;k++){ const a=k/16*TAU+hash2(kt.x,kt.z), x=kt.x+Math.sin(a)*(kt.col.r+dd), z=kt.z+Math.cos(a)*(kt.col.r+dd); if(!kamiReach(x,z)||!f4Free(x,z,0.4)) continue; P.x=x; P.z=z; P.facing=Math.atan2(kt.x-x,kt.z-z); setCam(P.facing); return true; } return false; }`;
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
  const until = async (js, ms = 60000) => { for (let t = 0; t < ms; t += 250) { if (await E(js)) return true; await pg.waitForTimeout(250); } return false; };
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
  await until("REG.cur==='kamishihi'&&!REG.busy", 240000); await pg.waitForTimeout(800); await E(CALM);
}
// 押す操作で木を切る：倒れた木の番号を返す（倒れなければ null）
async function chopWith(S, press, watchKey) {
  const { pg, E } = S;
  const before = await E(`[...REG.live.ktrees.values()].filter(t=>t.felled).map(t=>t.key)`);
  for (let i = 0; i < 40; i++) {
    for (let k = 0; k < 6 && !(await pg.evaluate("document.getElementById('dialog').hidden")); k++) { await E('(advanceDialog(),1)'); await pg.waitForTimeout(120); }
    if (await E(`!!REG.live.ktrees.get('${watchKey}').felled`)) break;
    await E(CALM); await press(); await pg.waitForTimeout(650);
  }
  await pg.waitForTimeout(300);
  return E(`(()=>{ const b=new Set(${JSON.stringify(before)}); return [...REG.live.ktrees.values()].filter(t=>t.felled&&!b.has(t.key)).map(t=>t.key); })()`);
}

// 試遊版：新しい形の案内に「広葉樹を切る」と出る・案内を押しても木を切り始めない・詳しい説明を開いても（切り株の）操作は起きない
// 木の案内「広葉樹を切る［鉄の斧・約4回］…」は全角の角括弧なので、新しい形でも短くならず「詳しく」も付かない（案内を小さくする決まりは全角の丸括弧だけを省く）
async function previewUI(S, touch, stumpKey) {
  const { pg, E } = S; const tag = touch ? '［iPhone の再現］' : '［PC］';
  const press = async () => { if (touch) await pg.tap('#prompt'); else await pg.click('#prompt'); };
  const k = await E(`(()=>{ const ST=${STAND}; for(const t of REG.live.ktrees.values()){ if(t.ty!=='kona'||t.felled||!kamiReach(t.x,t.z)) continue; if(ST(t,0.9)){ window.__u=t; return t.key; } } return null; })()`);
  await E(CALM); await pg.waitForTimeout(700);
  const a = await E("[PUI.on, $('prompt').className, $('prompt').textContent, curInter&&curInter.chop&&curInter.chop.rec.key, Math.round($('prompt').getBoundingClientRect().height)]");
  check(a[0] && a[1].includes('cmp') && /^(E)?(太い)?広葉樹を切る［鉄の斧・約\d+回］/.test(a[2]) && a[3] === k && a[4] <= 30, `P1 ${tag}新しい形（小さな1行・高さ ${a[4]}px）の案内に「${a[2]}」・案内の木＝目の前の広葉樹`);
  const c0 = await E(`[F4.chop.size, inv.naegi||0]`);
  await press(); await pg.waitForTimeout(700);
  const b = await E(`[F4.chop.size, !!P.atk, __u.felled, F4.chop.has(__u.key), $('prompt').classList.contains('open')]`);
  check(b[0] === c0[0] && !b[1] && !b[2] && !b[3], `P2 ${tag}木の案内を押しても切り始めない（切りかけ ${c0[0]}→${b[0]}・攻撃 ${b[1]}・倒れた ${b[2]}）`);
  // 詳しい説明が開ける切り株の案内（「広葉樹の切り株に苗木を植える（苗木 N）」）で開いて閉じる：植える操作は起きない
  const st = await E(`(()=>{ const kt=REG.live.ktrees.get('${stumpKey}'); if(!kt) return null; for(const rr of [1.0,1.2,0.8,1.4]) for(let i=0;i<24;i++){ const ang=i/24*TAU; P.x=kt.x+Math.cos(ang)*rr; P.z=kt.z+Math.sin(ang)*rr; const c=interactables(); if(c&&c.label.startsWith('広葉樹の切り株に苗木を植える')){ P.facing=Math.atan2(kt.x-P.x,kt.z-P.z); window.__sp=[P.x,P.z]; return c.label; } } return null; })()`);
  await E(CALM); await pg.waitForTimeout(700);
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

(async () => {
  // ================= PC =================
  const S = await setup({ viewport: { width: 1100, height: 680 } });
  const { pg, E, until } = S;
  await start(S, false);
  const J = async () => { await E('(cv.focus(),1)'); await pg.keyboard.press('j'); };
  const Ek = async () => { await E('(cv.focus(),1)'); await pg.keyboard.press('e'); };

  // 1 杉だけの所
  let kt = await E(`(()=>{ const ST=${STAND}, NR=${NEAR}; for(const t of REG.live.ktrees.values()){ if(t.ty!=='sugi'||t.felled||!kamiReach(t.x,t.z)) continue; const c=NR(t,5); if(c.kona||c.take||!c.sugi) continue; if(ST(t,0.8)){ window.__t=t; window.__s={n:inv.naegi||0}; return [t.key,interactables().label]; } } return null; })()`);
  let felled = await chopWith(S, J, kt[0]);
  let r = await E(`[prog.kami.f.includes('${kt[0]}'), prog.kami.fb.includes('${kt[0]}'), (inv.naegi||0)-__s.n]`);
  check(/^(太い)?杉を切る［/.test(kt[1]) && felled.length === 1 && felled[0] === kt[0] && r[0] && !r[1] && r[2] === 0, `1 杉だけの所で杉を切る（J）：案内「${kt[1].replace(/［.*/, '')}」・倒れた ${JSON.stringify(felled)}・f ${r[0]}・fb ${r[1]}・苗木 +${r[2]}`);
  const sugiKey = kt[0];
  // 2 広葉樹だけの所
  kt = await E(`(()=>{ const ST=${STAND}, NR=${NEAR}; for(const t of REG.live.ktrees.values()){ if(t.ty!=='kona'||t.felled||!kamiReach(t.x,t.z)) continue; const c=NR(t,5); if(c.sugi||c.take||!c.kona) continue; if(ST(t,0.8)){ window.__t=t; window.__s={n:inv.naegi||0,hw:inv.hardwood||0}; return [t.key,interactables().label]; } } return null; })()`);
  felled = await chopWith(S, J, kt[0]);
  r = await E(`[prog.kami.fb.includes('${kt[0]}'), prog.kami.f.includes('${kt[0]}'), (inv.naegi||0)-__s.n, [...document.querySelectorAll('#toasts > *')].some(t=>t.textContent.includes('広葉樹を切った'))]`);
  check(/^(太い)?広葉樹を切る［/.test(kt[1]) && felled.length === 1 && felled[0] === kt[0] && r[0] && !r[1] && r[2] === 1 && r[3], `2 広葉樹だけの所で広葉樹を切る（J）：案内「${kt[1].replace(/［.*/, '')}」・倒れた ${JSON.stringify(felled)}・fb ${r[0]}・f ${r[1]}・苗木 +${r[2]}・通知 ${r[3]}`);
  const konaKey = kt[0];
  if (PAGE) await previewUI(S, false, konaKey);
  // 7 広葉樹の丸太：枝を払う（J）→ 丸太の名前 → 割る（J）→ 山地の硬木
  await pg.waitForTimeout(2200);
  const tr = await E(`(()=>{ const tr=F4.trunks.find(t=>t.rec&&t.rec.key==='${konaKey}'); if(!tr) return null; const [ax,az,bx,bz]=trunkSeg(tr); const mx=(ax+bx)/2, mz=(az+bz)/2, nx=-(bz-az), nz=(bx-ax), L=Math.hypot(nx,nz)||1;
    for(const s of [1,-1]) for(const d of [0.9,1.2]){ const x=mx+nx/L*d*s, z=mz+nz/L*d*s; if(kamiReach(x,z)){ P.x=x; P.z=z; P.facing=Math.atan2(mx-x,mz-z); setCam(P.facing); window.__n0=REG.live.kw.logs.length; return interactables().label; } } return null; })()`);
  for (let i = 0; i < 30 && (await E(`F4.trunks.some(t=>t.rec&&t.rec.key==='${konaKey}')`)); i++) { await E(CALM); await J(); await pg.waitForTimeout(650); }
  const logs = await E(`REG.live.kw.logs.slice(__n0).map(l=>[l[3],l[5]?1:0,l[6]?1:0])`);
  const lab = await E(`(()=>{ const l=REG.live.kw.logs.slice(__n0).find(l=>l[5]); if(!l) return null; P.x=l[0]+Math.cos(l[2])*0.7; P.z=l[1]-Math.sin(l[2])*0.7; P.facing=Math.atan2(l[0]-P.x,l[1]-P.z); setCam(P.facing); window.__lg=l; const c=interactables(); return c&&c.label; })()`);
  for (let k = 0; k < 2; k++) {
    for (let i = 0; i < 20 && (await E(`REG.live.kw.logs.includes(__lg)`)); i++) { await E(CALM); await J(); await pg.waitForTimeout(650); }
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
    const m = await E(`(()=>{ const ST=${STAND}; const L=[...REG.live.ktrees.values()].filter(t=>t.ty&&!t.felled&&kamiReach(t.x,t.z));
      for(const a of L){ if(a.ty!=='${want}') continue; const b=L.find(t=>t!==a&&t.ty!==a.ty&&dist(t.x,t.z,a.x,a.z)<2.6); if(!b) continue;
        for(let k=0;k<16;k++){ const ang=k/16*TAU, x=a.x+Math.sin(ang)*(a.col.r+0.9), z=a.z+Math.cos(ang)*(a.col.r+0.9); if(!kamiReach(x,z)||!f4Free(x,z,0.4)) continue; if(dist(x,z,b.x,b.z)-b.col.r>1.6) continue;
          P.x=x; P.z=z; P.facing=Math.atan2(a.x-x,a.z-z)+0.35; setCam(P.facing); curInter=interactables(); const tg=curInter&&curInter.chop; if(!tg||tg.rec.key!==a.key) continue;
          window.__s={n:inv.naegi||0}; return [a.key,a.ty,b.ty,curInter.label]; } } return null; })()`);
    if (!m) { mixed.push(null); continue; }
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
  kt = await E(`(()=>{ const ST=${STAND}; for(const t of REG.live.ktrees.values()){ if(t.ty!=='kona'||t.felled||!kamiReach(t.x,t.z)) continue; if(ST(t,1.1)){ window.__s={n:inv.naegi||0}; const c=interactables(); return [t.key,c&&c.chop&&c.chop.rec.key,c&&c.label]; } } return null; })()`);
  felled = await chopWith(S, Ek, kt[0]);
  r = await E(`(inv.naegi||0)-__s.n`);
  check(kt[1] === kt[0] && felled.length === 1 && felled[0] === kt[0] && r === 1, `4 「調べる」（E）で案内の広葉樹を切る：倒れた ${JSON.stringify(felled)}・苗木 +${r}`);
  const kona2 = kt[0];
  // 8 植林と成長（切り株で E → 時間がたつ → 育って、また「広葉樹を切る」）
  const pl = await E(`(()=>{ const kt=REG.live.ktrees.get('${konaKey}'); for(let k=0;k<24;k++){ const a=k/24*TAU; P.x=kt.x+Math.cos(a)*1.0; P.z=kt.z+Math.sin(a)*1.0; const c=interactables(); if(c&&c.label.startsWith('広葉樹の切り株に苗木を植える')){ P.facing=Math.atan2(kt.x-P.x,kt.z-P.z); return c.label; } } return null; })()`);
  await Ek(); await pg.waitForTimeout(400);
  const planted = await E(`[prog.kami.pl['${konaKey}']!=null, REG.live.ktrees.get('${konaKey}').felled]`);
  await E(`(()=>{ stats.time+=E2.grow+5; E2.t=0; return 1; })()`);
  const grew = await until(`!REG.live.ktrees.get('${konaKey}').felled&&prog.kami.pl['${konaKey}']==null&&!prog.kami.fb.includes('${konaKey}')`, 15000);
  const relab = await E(`(()=>{ const kt=REG.live.ktrees.get('${konaKey}'); const ST=${STAND}; if(!ST(kt,0.8)) return null; const c=interactables(); return c&&c.label; })()`);
  check(pl && planted[0] && planted[1] && grew && /^(太い)?広葉樹を切る［/.test(relab || ''), `8 切り株に苗木を植える（E）→ 時間がたつと広葉樹に育つ → 案内「${(relab || '').replace(/［.*/, '')}」`);
  // 9 セーブ → 読み込み直す（つづきから）
  await E(`(()=>{ const kt=REG.live.ktrees.get('${kona2}'); inv.naegi=(inv.naegi||0)+1; for(let k=0;k<24;k++){ const a=k/24*TAU; P.x=kt.x+Math.cos(a)*1.0; P.z=kt.z+Math.sin(a)*1.0; const c=interactables(); if(c&&c.label.startsWith('広葉樹の切り株に苗木を植える')){ c.act(); break; } } saveGame(); return 1; })()`);
  const pre = await E(`({naegi:inv.naegi, hw:inv.hardwood||0, f:prog.kami.f.length, fb:prog.kami.fb.length, pl:Object.keys(prog.kami.pl).length})`);
  await pg.goto('http://game.local/' + DIR, { waitUntil: 'load', timeout: 300000 });
  await pg.waitForFunction("typeof window.__ev==='function'", null, { timeout: 300000 });
  await pg.click('#btnContinue'); await until("REG.cur==='kamishihi'&&!REG.busy&&!!REG.live&&!!REG.live.ktrees", 240000); await pg.waitForTimeout(1500);
  const post = await E(`({naegi:inv.naegi, hw:inv.hardwood||0, f:prog.kami.f.length, fb:prog.kami.fb.length, pl:Object.keys(prog.kami.pl).length,
    sugi:[REG.live.ktrees.get('${sugiKey}').felled, prog.kami.f.includes('${sugiKey}')], grown:[REG.live.ktrees.get('${konaKey}').felled, prog.kami.fb.includes('${konaKey}')],
    kona2:[REG.live.ktrees.get('${kona2}').felled, prog.kami.fb.includes('${kona2}'), prog.kami.pl['${kona2}']!=null], ty:[REG.live.ktrees.get('${konaKey}').ty, REG.live.ktrees.get('${sugiKey}').ty]})`);
  check(post.naegi === pre.naegi && post.hw === pre.hw && post.f === pre.f && post.fb === pre.fb && post.pl === pre.pl && post.sugi[0] && post.sugi[1] && !post.grown[0] && !post.grown[1] && post.kona2.every(Boolean) && post.ty[0] === 'kona' && post.ty[1] === 'sugi',
    `9 セーブして読み込み直す（つづきから）：${JSON.stringify(pre)} → ${JSON.stringify(post)}`);
  const SK = PAGE ? 'eiheiji_vs_beasts_p3e2forest' : 'eiheiji_vs_beasts_v010';
  check(await E('SAVE_KEY') === SK && await E("JSON.parse(localStorage.getItem(SAVE_KEY)).v") === 1, `9 セーブの形は同じ（SAVE_KEY「${SK}」・v:1）`);
  if (PAGE) await mainKeysKept(S, 'PC');
  check(!S.errs.length, `PC：エラーなし ${JSON.stringify(S.errs.slice(0, 3))}`);
  await S.b.close();

  // ================= 10 iPhone の再現（タップ）=================
  const T = await setup({ ...devices['iPhone 13'] });
  await start(T, true);
  let lastKona = null;
  for (const [btn, name] of [['#tbAtk', '攻撃'], ['#tbAct', '調べる']]) {
    const k2 = await T.E(`(()=>{ const ST=${STAND}; for(const t of REG.live.ktrees.values()){ if(t.ty!=='kona'||t.felled||!kamiReach(t.x,t.z)) continue; if(ST(t,0.9)){ curInter=interactables(); window.__s={n:inv.naegi||0}; return [t.key,curInter&&curInter.label]; } } return null; })()`);
    await T.pg.waitForTimeout(300);
    const f3 = await chopWith(T, async () => { await T.pg.tap(btn); }, k2[0]);
    const g = await T.E(`[(inv.naegi||0)-__s.n, prog.kami.fb.includes('${k2[0]}'), touchMode]`);
    lastKona = k2[0];
    check(/^(太い)?広葉樹を切る［/.test(k2[1] || '') && f3.length === 1 && f3[0] === k2[0] && g[0] === 1 && g[1] && g[2], `10 iPhone の再現：「${name}」ボタンのタップで広葉樹を切る（案内「${(k2[1] || '').replace(/［.*/, '')}」・倒れた ${JSON.stringify(f3)}・苗木 +${g[0]}）`);
  }
  if (PAGE) { await previewUI(T, true, lastKona); await mainKeysKept(T, 'iPhone'); }
  check(!T.errs.length, `iPhone：エラーなし ${JSON.stringify(T.errs.slice(0, 3))}`);
  await T.b.close();
  console.log(ok ? 'PASS: 上志比の伐採（樹種・案内・切る木・苗木・硬木・植林・セーブ）' : 'FAILED');
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
