#!/usr/bin/env node
// 「調べる」の案内（#prompt）を小さくした形の確認（試遊版 previews/p3e2-forest。画面のない Chromium。Node の Playwright。10分ほど）。docs/prompt-ui.md
// - PC（1280×720）・iPhone 縦（iPhone 13 の再現）・iPhone 横（844×390・タッチ）で、今までの形と新しい形を撮って比べる
// - 新しい形：名前だけの1行・小さい・主人公／手持ちバー／スマホのボタン／体力などの表示と重ならない・押すと詳しく（全文）・別の物に近づくと閉じる
// - 調べる操作は今までどおり（PC は E、スマホは「調べる」ボタン）。「長押し」の操作の説明は残す
// - 大きな案内（banner）・通知（toast）は今までどおり出る。今までの形に戻すと v0.88 と同じ表示
// 使い方：THREE_JS=…/three.min.js node tests/p3e2-prompt-ui.cjs   （PUI_SHOTS=フォルダ で改善前後の画面を撮る）
const fs = require('fs'), path = require('path');
const { chromium, devices } = require('playwright');
const ROOT = path.dirname(__dirname);
const THREE = fs.readFileSync(process.env.THREE_JS || '/home/claude/v010/node_modules/three/build/three.min.js', 'utf8');
const PAGE = 'previews/p3e2-forest/index.html';
const HTML = fs.readFileSync(path.join(ROOT, PAGE), 'utf8').replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){');
const SHOTS = process.env.PUI_SHOTS;
let ok = true;
const check = (c, msg) => { console.log((c ? 'ok   ' : 'FAIL ') + msg); ok = ok && !!c; };
const VIEWS = [
  { tag: 'pc', name: 'PC 1280×720', ctx: { viewport: { width: 1280, height: 720 } } },
  { tag: 'iphone', name: 'iPhone 縦（iPhone 13 の再現）', ctx: { ...devices['iPhone 13'] } },
  { tag: 'iphone-land', name: 'iPhone 横（844×390・タッチ）', ctx: { viewport: { width: 844, height: 390 }, deviceScaleFactor: 3, isMobile: true, hasTouch: true } },
];
// 画面の部品の位置と重なり
const MEASURE = `(()=>{ const R=el=>{ const b=el.getBoundingClientRect(); return [b.left,b.top,b.right,b.bottom]; }, hit=(a,b)=>a[0]<b[2]&&b[0]<a[2]&&a[1]<b[3]&&b[1]<a[3];
  const pr=$('prompt'), p=R(pr), cs=getComputedStyle(pr);
  // 主人公の画面の上の範囲（足元から頭まで・幅 0.9m）
  const y0=groundH(P.x,P.z), pts=[], rt=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0); for(const h of [0,0.9,1.85]) for(const s of [-0.45,0.45]){ const v=new THREE.Vector3(P.x+rt.x*s,y0+h,P.z+rt.z*s).project(camera); pts.push([(v.x+1)/2*innerWidth,(1-v.y)/2*innerHeight]); }
  const pl=[Math.min(...pts.map(q=>q[0])),Math.min(...pts.map(q=>q[1])),Math.max(...pts.map(q=>q[0])),Math.max(...pts.map(q=>q[1]))];
  const over=[]; if(hit(p,pl)) over.push('主人公');
  for(const id of ['items','stats','objective','res','notice','coreBar','bossBar','mini','help','ftToggle','tbAct','tbAtk','tbDodge','tbHeavy','tbMap','tbPause','tbSwap','tbWave']){ const el=document.getElementById(id); if(!el) continue; const b=el.getBoundingClientRect(), c=getComputedStyle(el);
    if(b.width<4||b.height<4||c.visibility==='hidden'||c.display==='none'||c.opacity==='0'||el.closest('[hidden]')) continue; if(hit(p,R(el))) over.push(id); }
  return {lab:curInter&&curInter.label, hidden:pr.hidden, rect:p.map(Math.round), w:Math.round(p[2]-p[0]), h:Math.round(p[3]-p[1]), font:cs.fontSize, text:pr.textContent, cls:pr.className, over, player:pl.map(Math.round), vw:innerWidth, vh:innerHeight,
    inView:p[0]>=0&&p[1]>=0&&p[2]<=innerWidth&&p[3]<=innerHeight}; })()`;

async function run(V) {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext(V.ctx);
  const pg = await ctx.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push(String(e)));
  await ctx.route('**/*', async r => {
    const u = r.request().url();
    if (u.includes('three.min.js') || u.includes('three.js/r128')) return r.fulfill({ body: THREE, contentType: 'application/javascript' });
    if (!u.startsWith('http://game.local/')) return r.abort();
    const p = decodeURIComponent(u.slice('http://game.local/'.length).split('?')[0]);
    if (p === PAGE || p === 'previews/p3e2-forest/') return r.fulfill({ body: HTML, contentType: 'text/html; charset=utf-8' });
    const fp = path.join(ROOT, p);
    if (fp.startsWith(ROOT) && fs.existsSync(fp) && fs.statSync(fp).isFile()) return r.fulfill({ body: fs.readFileSync(fp) });
    return r.fulfill({ status: 404, body: '' });
  });
  const E = c => pg.evaluate(c => window.__ev(c), c);
  const until = async (js, ms = 60000) => { for (let t = 0; t < ms; t += 250) { if (await E(js)) return true; await pg.waitForTimeout(250); } return false; };
  const touch = !!V.ctx.hasTouch;
  const press = async sel => { if (touch) await pg.tap(sel); else await pg.click(sel); };
  const shot = async name => { if (SHOTS) { fs.mkdirSync(SHOTS, { recursive: true }); await pg.screenshot({ path: path.join(SHOTS, `${V.tag}-${name}.png`) }); } };
  const T = `［${V.name}］`;

  await pg.goto('http://game.local/previews/p3e2-forest/', { waitUntil: 'load', timeout: 300000 });
  await pg.waitForFunction("typeof window.__ev==='function'", null, { timeout: 300000 });
  await press('#btnFTStart');
  check(await until("REG.cur==='kamishihi'&&!REG.busy&&!FT.busy&&!!E2.grid", 300000), `${T}上志比の森で始める`);
  check(await E('touchMode') === touch, `${T}操作の種類（タッチ ${touch}）`);
  // 落ち着かせる：獣を遠ざける・昼・大きな案内を消す
  await E("(()=>{ for(const e of enemies) if(!e.removed) e.x+=3000; prog.f10.tod=150; f10LightNow(); $('banner').classList.remove('show'); bannerT=0; for(const t of [...document.querySelectorAll('#toasts > *')]) t.remove(); return 1; })()");
  // 長い案内が出る所：近くの広葉樹を切って、苗木を持たずに切り株のそばへ（「広葉樹の切り株：苗木を植えると、また育つ（苗木は…）」）
  await E("(()=>{ const t=trk(); t.region='komyoji'; delete t.x; delete t.z; TRUCK.sync=false; return 1; })()"); // KEI truck の案内が入れ替わらないように光明寺へ
  const lab = await E(`(()=>{ const kt=[...REG.live.ktrees.values()].filter(t=>t.ty==='kona'&&!t.felled).sort((a,b)=>dist(P.x,P.z,a.x,a.z)-dist(P.x,P.z,b.x,b.z))[0]; f4Fell(kamiTreeRec(kt),0.3);
    inv.naegi=0; window.__kt=kt; e2Tick(REG.live); return 1; })()`);
  await pg.waitForTimeout(4000); // 幹が倒れきるのを待つ（倒れたあとの幹の「枝を払う」の案内が近くなることがあるため）
  const spot = await E(`(()=>{ const kt=__kt; // 切り株の案内がいちばん近くなる所を探す
    for(let k=0;k<48;k++){ const a=k/24*TAU, rr=k<24?1.0:1.3; P.x=kt.x+Math.cos(a)*rr; P.z=kt.z+Math.sin(a)*rr; const c=interactables(); if(c&&c.label.startsWith('広葉樹の切り株：')){ P.facing=Math.atan2(kt.x-P.x,kt.z-P.z); setCam(P.facing); window.__spot=[P.x,P.z,P.facing]; return k; } } return -1; })()`);
  // 測る直前に、切り株のそばへ立たせ直す（ぶつかって少しずれると、倒れた幹の案内に入れ替わるため）
  const reset = () => E("(()=>{ const s=__spot; P.x=s[0]; P.z=s[1]; P.facing=s[2]; if(P.vx!=null){ P.vx=0; P.vz=0; } return 1; })()");
  await pg.waitForTimeout(1200);
  await E("(()=>{ for(const t of [...document.querySelectorAll('#toasts > *')]) t.remove(); return 1; })()");
  const label = await E('curInter&&curInter.label');
  check(label && label.startsWith('広葉樹の切り株：苗木を植えると、また育つ（'), `${T}長い案内の所に立つ：「${label}」`);

  // ---- 今までの形 ----
  await E('(puiSet(false), 1)'); await reset(); await pg.waitForTimeout(400); await reset(); await pg.waitForTimeout(200);
  const old = await E(MEASURE);
  await shot('before');
  check(!old.hidden && old.lab === label && old.text === (touch ? '調べる' : 'E') + label && !old.cls.includes('cmp'), `${T}今までの形（v0.88 のまま）：${old.w}×${old.h}px・文字 ${old.font}・重なる ${JSON.stringify(old.over)}`);

  // ---- 新しい形 ----
  await E('(puiSet(true), 1)'); await reset(); await pg.waitForTimeout(700); await reset(); await pg.waitForTimeout(200);
  const nw = await E(MEASURE);
  await shot('after');
  check(!nw.hidden && nw.lab === label && nw.cls.includes('cmp') && nw.text === (touch ? '' : 'E') + '広葉樹の切り株：苗木を植えると、また育つ詳しく',
    `${T}新しい形：名前だけ「${nw.text}」`);
  check(nw.h <= 30 && nw.font === '12px', `${T}新しい形は1行・小さい（${nw.w}×${nw.h}px・文字 ${nw.font}。今まで ${old.w}×${old.h}px）面積 ${Math.round(nw.w * nw.h / (old.w * old.h) * 100)}%`);
  check(nw.inView && !nw.over.length, `${T}新しい形は画面の中・主人公／手持ちバー／ボタン／体力などの表示と重ならない ${JSON.stringify(nw.rect)} 重なる ${JSON.stringify(nw.over)}（主人公 ${JSON.stringify(nw.player)}）`);
  // 押すと詳しく・もう一度で閉じる
  await reset(); await press('#prompt'); await pg.waitForTimeout(400); await reset(); await pg.waitForTimeout(200);
  const op = await E(MEASURE);
  await shot('open');
  check(op.lab === label && op.cls.includes('open') && op.text === (touch ? '' : 'E') + label + '閉じる' && op.inView && !op.over.length, `${T}押すと詳しい説明（全文）：${op.w}×${op.h}px・重なる ${JSON.stringify(op.over)}`);
  await press('#prompt'); await pg.waitForTimeout(400);
  check(!(await E("$('prompt').classList.contains('open')")), `${T}もう一度押すと閉じる`);
  check(await E("REG.cur==='kamishihi'&&!P.dead&&S.mode==='playing'"), `${T}案内を押しても、攻撃・移動・ほかの操作は起きない（遊んでいる状態のまま）`);
  // 開いたまま別の物に近づくと閉じる：竹林へ
  await press('#prompt'); await pg.waitForTimeout(300);
  await E("(()=>{ const c=E2.take.slice().sort((a,b)=>dist(P.x,P.z,a.x,a.z)-dist(P.x,P.z,b.x,b.z))[0]; const r=1.0*c.s*E2GS.take+0.6; P.x=c.x+r; P.z=c.z; return 1; })()");
  await pg.waitForTimeout(600);
  const bt = await E(MEASURE);
  check(!bt.cls.includes('open') && bt.text.includes('竹林の竹を切る') && !bt.text.includes('竹+2'), `${T}別の物に近づくと詳しい説明は閉じる：「${bt.text}」`);
  // 調べる操作は今までどおり
  const b0 = await E('inv.bamboo||0');
  if (touch) await pg.tap('#tbAct'); else { await E('(cv.focus(), 1)'); await pg.keyboard.press('e'); }
  await pg.waitForTimeout(500);
  const b1 = await E('inv.bamboo||0');
  check(b1 - b0 === 2, `${T}調べる操作は今までどおり（${touch ? '「調べる」ボタン' : 'E キー'}で竹+2：${b0}→${b1}）`);
  // 「長押し」の操作の説明は残す
  const lp = await E("[puiShort('スズキを助け起こす（行動ボタンを長押し）'), puiShort('スズキを助け起こす（E を長押し）')]");
  check(lp[0].includes('長押し') && lp[1].includes('長押し'), `${T}「長押し」の操作の説明は残す ${JSON.stringify(lp)}`);
  // 大きな案内・通知は今までどおり
  await E("(banner('確かめ','大きな案内は今までどおり',3), toast('通知は今までどおり'), 1)"); await pg.waitForTimeout(500);
  const bn = await E("[ $('banner').classList.contains('show'), [...document.querySelectorAll('#toasts > *')].some(t=>t.textContent.includes('通知は今までどおり')) ]");
  check(bn[0] && bn[1], `${T}大きな案内（banner）と通知（toast）は今までどおり出る ${JSON.stringify(bn)}`);
  // 今までの形に戻すと v0.88 と同じ表示
  await E("($('banner').classList.remove('show'), bannerT=0, puiSet(false), 1)"); await pg.waitForTimeout(500);
  const back = await E("[ $('prompt').className, $('prompt').querySelector('.k')&&$('prompt').querySelector('.k').textContent, $('prompt').textContent, curInter&&curInter.label ]");
  check(!back[0].includes('cmp') && back[1] === (touch ? '調べる' : 'E') && back[2] === back[1] + back[3], `${T}今までの形に戻すと v0.88 と同じ（札「${back[1]}」＋「${back[3]}」）`);
  check(!errs.length, `${T}エラーなし ${JSON.stringify(errs.slice(0, 3))}`);
  await b.close();
  return { old, nw, op };
}

(async () => {
  const res = {};
  for (const V of VIEWS) res[V.tag] = await run(V);
  if (SHOTS) fs.writeFileSync(path.join(SHOTS, 'measure.json'), JSON.stringify(res, null, 1));
  console.log(ok ? 'PASS: 「調べる」の案内を小さく（試遊版）' : 'FAILED');
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
