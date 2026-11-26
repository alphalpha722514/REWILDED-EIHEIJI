#!/usr/bin/env node
// v0.88（P3-E の E-2）の検収用の試遊版 previews/p3e2-forest/ の確認（画面のない Chromium。Node の Playwright。10分ほど）。docs/p3e2-forest-preview.md
// - 本編の保存キー・設定のキーを読まない・書かない（前もって入れておいた本編の値が最後まで同じ）。試遊版のキーに保存する
// - 読み込むファイル（data・assets・vendor）が previews/p3e2-forest/ から ../../ で読める（読めなかったのは、先に試す同じフォルダの方だけ）
// - 「テスト：上志比の森で始める」→ 上志比の広葉樹の林・KEI truck（直した・救急箱）がそば・鉄の斧
// - 試遊メニュー：苗木と薬草と素材を足す・広葉樹を切る→苗木を植える→40分進める→育つ・山の薬草を摘む→20分進める→また摘める・竹林・
//   KEI truck の救急箱に薬草・光明寺のかまどで薬草粥・上志比へ戻る・朝9時・描く細かさ
// - iPhone の大きさ・タッチ（tap）でも、始める・メニューを開く・ボタンを押せる。メニューが画面からはみ出さない
// 使い方：THREE_JS=…/three.min.js node tests/p3e2-forest-preview.cjs   （PREVIEW_SHOTS=フォルダ で画面を撮る）
const fs = require('fs'), path = require('path');
const { chromium, devices } = require('playwright');
const ROOT = path.dirname(__dirname);
const THREE = fs.readFileSync(process.env.THREE_JS || '/home/claude/v010/node_modules/three/build/three.min.js', 'utf8');
const PAGE = 'previews/p3e2-forest/index.html';
const HTML = fs.readFileSync(path.join(ROOT, PAGE), 'utf8').replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){');
const SHOTS = process.env.PREVIEW_SHOTS;
const MAIN_KEYS = ['eiheiji_vs_beasts_v010', 'REWILDED_EIHEIJI_SETTINGS', 'eiheiji_weatherEffects', 'eiheiji_shadow', 'eiheiji_perf', 'eiheiji_aimMode', 'eiheiji_detail', 'eiheiji_camPitch'];
let ok = true;
const check = (c, msg) => { console.log((c ? 'ok   ' : 'FAIL ') + msg); ok = ok && !!c; };

async function run(mobile) {
  const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const ctx = await b.newContext(mobile ? { ...devices['iPhone 13'] } : { viewport: { width: 1280, height: 720 } });
  const pg = await ctx.newPage();
  const errs = [], miss = [], got = new Set();
  pg.on('pageerror', e => errs.push(String(e)));
  await ctx.route('**/*', async r => {
    const u = r.request().url();
    if (u.includes('three.min.js') || u.includes('three.js/r128')) return r.fulfill({ body: THREE, contentType: 'application/javascript' });
    if (!u.startsWith('http://game.local/')) return r.abort();
    const p = decodeURIComponent(u.slice('http://game.local/'.length).split('?')[0]);
    if (p === 'seed.html') return r.fulfill({ body: '<!doctype html><title>seed</title>', contentType: 'text/html' });
    if (p === PAGE || p === 'previews/p3e2-forest/') return r.fulfill({ body: HTML, contentType: 'text/html; charset=utf-8' });
    const fp = path.join(ROOT, p);
    if (fp.startsWith(ROOT) && fs.existsSync(fp) && fs.statSync(fp).isFile()) { got.add(p); return r.fulfill({ body: fs.readFileSync(fp) }); }
    miss.push(p); return r.fulfill({ status: 404, body: '' });
  });
  const E = c => pg.evaluate(c => window.__ev(c), c);
  const until = async (js, ms = 60000) => { for (let t = 0; t < ms; t += 250) { if (await E(js)) return true; await pg.waitForTimeout(250); } return false; };
  const press = async sel => { if (mobile) await pg.tap(sel); else await pg.click(sel); };
  const menu = async k => { if (await E("document.getElementById('ftPanel').hidden")) await press('#ftToggle'); await press(`button[data-ft="${k}"]`); await pg.waitForTimeout(300); };
  const tag = mobile ? '［iPhone］' : '［PC］';

  // 本編のキーに前もって値を入れておく（同じ場所＝同じオリジン）
  await pg.goto('http://game.local/seed.html');
  await pg.evaluate(K => { for (const k of K) localStorage.setItem(k, 'MAIN:' + k); }, MAIN_KEYS);
  await pg.goto('http://game.local/previews/p3e2-forest/', { waitUntil: 'load', timeout: 300000 });
  await pg.waitForFunction("typeof window.__ev==='function'", null, { timeout: 300000 });
  const head = await E("[document.querySelector('.tver').textContent, SAVE_KEY, localStorage.getItem('eiheiji_vs_beasts_v010'), (localStorage.setItem('eiheiji_detail','x'), 1)]");
  check(/^v0\.(?:8[89]|9[0-9])(?:\.[0-9]+)? 上志比の森林 検収用の試遊版/.test(head[0]) && head[1] === 'eiheiji_vs_beasts_p3e2forest' && head[2] === null, `${tag}版の表示・試遊版の保存キー・本編のキーは読めない ${JSON.stringify(head.slice(0, 3))}`);
  if (SHOTS && mobile) { fs.mkdirSync(SHOTS, { recursive: true }); await pg.screenshot({ path: path.join(SHOTS, 'iphone-title.png') }); }

  await press('#btnFTStart');
  check(await until("REG.cur==='kamishihi'&&!REG.busy&&!FT.busy&&!!E2.grid", 300000), `${tag}「テスト：上志比の森で始める」で上志比へ`);
  await pg.waitForTimeout(1500);
  let r = await E(`(()=>{ const d=e2Density(), t=trk(); return [d.kona, d.sugi, d.take, P.weapon, t.repaired&&t.fueled, t.region, !!(t.fac&&t.fac.aid), Math.round(dist(P.x,P.z,TRUCK.x,TRUCK.z)), !!(TRUCK.m&&TRUCK.m.visible), prog.kama.built, kamiReach(P.x,P.z)]; })()`);
  check(r[0] >= 5 && r[3] === 'axeIron' && r[4] && r[5] === 'kamishihi' && r[6] && r[7] <= 10 && r[8] && r[9] === 1 && r[10], `${tag}広葉樹の林の中（まわり28mに 広葉樹${r[0]}・杉${r[1]}・竹${r[2]}）・鉄の斧・KEI truck（直した・救急箱）が ${r[7]}m・かまど建設済み ${JSON.stringify(r)}`);
  if (SHOTS) { await pg.waitForTimeout(1500); await pg.screenshot({ path: path.join(SHOTS, (mobile ? 'iphone' : 'pc') + '-forest.png') }); }

  // メニュー：素材を足す
  await menu('items');
  r = await E("[inv.naegi, inv.mherb, inv.rice, inv.wood>=10, !document.getElementById('ftPanel').hidden, document.getElementById('ftStat').textContent.includes('苗木 3')]");
  check(r[0] === 3 && r[1] === 3 && r[2] >= 3 && r[3] && r[4] && r[5], `${tag}メニュー「苗木・山の薬草・米・木材を足す」${JSON.stringify(r)}`);
  if (SHOTS) await pg.screenshot({ path: path.join(SHOTS, (mobile ? 'iphone' : 'pc') + '-menu.png') });
  const box = await pg.evaluate(() => { const e = document.getElementById('ftPanel').getBoundingClientRect(); return [e.left, e.top, e.right, e.bottom, innerWidth, innerHeight]; });
  check(box[0] >= 0 && box[1] >= 0 && box[2] <= box[4] && box[3] <= box[5], `${tag}メニューが画面に収まる ${JSON.stringify(box.map(Math.round))}`);

  if (!mobile) {
    // 広葉樹を切る → 苗木 → 植える → 40分 → 育つ
    r = await E(`(()=>{ const kt=[...REG.live.ktrees.values()].filter(t=>t.ty==='kona'&&!t.felled).sort((a,b)=>dist(P.x,P.z,a.x,a.z)-dist(P.x,P.z,b.x,b.z))[0]; const n0=inv.naegi;
      f4Fell(kamiTreeRec(kt),0.3); window.__kt=kt; return [prog.kami.fb.includes(kt.key), inv.naegi-n0, Math.round(dist(P.x,P.z,kt.x,kt.z))]; })()`);
    check(r[0] && r[1] === 1, `${tag}近くの広葉樹（${r[2]}m）を切る：生えてこない記録・苗木+1 ${JSON.stringify(r)}`);
    r = await E(`(()=>{ const kt=__kt; P.x=kt.x+1.0; P.z=kt.z; e2Tick(REG.live); const L=[]; REG.live.inter(L); const a=L.find(o=>o.label.startsWith('広葉樹の切り株に苗木を植える')); if(a) a.act(); return [!!a, prog.kami.pl[kt.key]!=null]; })()`);
    check(r[0] && r[1], `${tag}切り株に苗木を植える ${JSON.stringify(r)}`);
    await menu('t40');
    check(await until("__kt.felled===false&&__kt.col.active&&prog.kami.pl[__kt.key]==null", 20000), `${tag}「40分進める」で苗木が広葉樹に育つ（また切れる）`);
    // 山の薬草
    await menu('herb');
    r = await E(`(()=>{ const L=[]; REG.live.inter(L); const a=L.find(o=>o.label.includes('山の薬草を摘む')); const m0=inv.mherb; if(a) a.act(); const L2=[]; REG.live.inter(L2); return [!!a, inv.mherb-m0, L2.some(o=>o.label.startsWith('山の薬草：もう摘んだ'))]; })()`);
    check(r[0] && r[1] >= 1 && r[2], `${tag}「山の薬草のそばへ」→ 摘む・待ち時間 ${JSON.stringify(r)}`);
    if (SHOTS) { await pg.waitForTimeout(1200); await pg.screenshot({ path: path.join(SHOTS, 'pc-herb.png') }); }
    await menu('t20');
    r = await E(`(()=>{ const L=[]; REG.live.inter(L); return L.some(o=>o.label.includes('山の薬草を摘む')); })()`);
    check(r, `${tag}「20分進める」で山の薬草がまた摘める`);
    // 竹林
    await menu('take');
    r = await E(`(()=>{ const L=[]; REG.live.inter(L); const a=L.find(o=>o.label==='竹林の竹を切る（竹+2）'); const b0=inv.bamboo||0; if(a) a.act(); return [!!a, (inv.bamboo||0)-b0]; })()`);
    check(r[0] && r[1] === 2, `${tag}「竹林へ」→ 竹林の竹を切る（鉄の斧で）竹+2 ${JSON.stringify(r)}`);
    if (SHOTS) { await pg.waitForTimeout(1200); await pg.screenshot({ path: path.join(SHOTS, 'pc-take.png') }); }
    for (const k of ['sugi', 'view']) {
      await menu(k);
      r = await E("(()=>{ const d=e2Density(); return [d.kona,d.sugi,d.take,kamiReach(P.x,P.z)]; })()");
      check(r[3] && (k !== 'sugi' || r[1] >= 5), `${tag}「${k === 'sugi' ? '杉林へ' : '森の奥の高い所へ'}」（まわり28mに 広葉樹${r[0]}・杉${r[1]}・竹${r[2]}・歩ける所）`);
      if (SHOTS) { await pg.waitForTimeout(1500); await pg.screenshot({ path: path.join(SHOTS, `pc-${k}.png`) }); }
    }
    // KEI truck の救急箱
    await menu('truck');
    r = await E(`(()=>{ const t=trk(); TRUCK.sync=false; truckPos(); P.x=TRUCK.x+2; P.z=TRUCK.z; P.lastHurt=-999; const L=[]; truckInteractables(L); const a=L.find(o=>o.label.startsWith('荷台の救急箱に山の薬草を入れる')); const m0=inv.mherb; if(a) a.act();
      return [t.region, !!a, m0-inv.mherb, stats.time<(TRUCK.herbT||0), !!(TRUCK.m&&TRUCK.m.visible)]; })()`);
    check(r[0] === 'kamishihi' && r[1] && r[2] === 1 && r[3] && r[4], `${tag}「KEI truck をそばに呼ぶ」→ 荷台の救急箱に山の薬草を入れる ${JSON.stringify(r)}`);
    // 光明寺のかまど
    await menu('kamado');
    check(await until("REG.cur==='komyoji'&&!REG.busy&&!FT.busy", 300000), `${tag}「光明寺のかまどの前へ」で光明寺へ`);
    r = await E(`(()=>{ prog.kama.q=[]; const L=[]; facInteractables(L); const a=L.find(o=>/かまど/.test(o.label)); if(a) a.act(); const bt=[...document.querySelectorAll('#defenseChoice button')].find(b=>b.textContent.startsWith('山の薬草で薬草粥を炊く')); const m0=inv.mherb; if(bt) bt.click();
      const d=document.getElementById('defenseChoice'); if(d) d.remove(); S.mode='playing'; return [Math.round(facDist('kama')*10)/10, !!a, !!bt, prog.kama.q.includes('herbPorridge'), m0-inv.mherb]; })()`);
    check(r[0] <= 1.5 && r[1] && r[2] && r[3] && r[4] === 1, `${tag}かまど：山の薬草で薬草粥を炊く ${JSON.stringify(r)}`);
    await menu('back');
    check(await until("REG.cur==='kamishihi'&&!REG.busy&&!FT.busy&&!!E2.grid", 300000), `${tag}「上志比の森へ戻る」`);
    await menu('noon');
    check(await E("p3dBand()==='day'&&f10Phase()==='day'"), `${tag}「朝9時にする」で昼`);
    await menu('detail');
    r = await E("[GFX.detail, localStorage.getItem('eiheiji_p3e2f_detail')]");
    await menu('detail');
    check(r[0] === 'lite' && r[1] === 'lite', `${tag}「描く細かさを切り替える」（試遊版のキーに保存）${JSON.stringify(r)}`);
    r = await E("(saveGame(), (()=>{ const d=JSON.parse(localStorage.getItem(SAVE_KEY)); return [d.v, d.inv.naegi>=0, (d.kami&&Array.isArray(d.kami.fb)), readSave()!==null]; })())");
    check(r[0] === 1 && r[1] && r[2] && r[3], `${tag}試遊版のキーに保存して読める ${JSON.stringify(r)}`);
  } else {
    await menu('t5');
    r = await E("[Math.round(stats.time), document.getElementById('ftPanel').hidden]");
    check(r[0] >= 300, `${tag}タッチで「5分進める」${JSON.stringify(r)}`);
    await menu('close');
    check(await E("document.getElementById('ftPanel').hidden&&!document.getElementById('ftToggle').hidden"), `${tag}タッチで「メニューを閉じる」`);
    // 試遊メニューのボタンが、ほかの画面の部品と重ならないか
    if (SHOTS) await pg.screenshot({ path: path.join(SHOTS, 'iphone-play.png') });
  }
  // 試遊メニューのボタンが、ほかの画面の部品（体力・目標の帯・持ち物の数・地図・手持ちバー・スマホのボタン）と重ならないか
  await pg.waitForTimeout(700);
  const ov = await pg.evaluate(() => { const a = document.getElementById('ftToggle').getBoundingClientRect(), out = [], big = innerWidth * innerHeight * 0.5;
    for (const el of document.querySelectorAll('#hud *, #touch *, #items, #objective')) { const b = el.getBoundingClientRect(); if (b.width < 4 || b.height < 4 || b.width * b.height > big) continue;
      if (getComputedStyle(el).visibility === 'hidden' || getComputedStyle(el).opacity === '0') continue;
      if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) out.push((el.id || String(el.className) || el.tagName)); } return [Math.round(a.left), Math.round(a.top), Math.round(a.right), Math.round(a.bottom), out.slice(0, 6)]; });
  check(!ov[4].length, `${tag}試遊メニューのボタン ${JSON.stringify(ov.slice(0, 4))} がほかの画面の部品と重ならない ${JSON.stringify(ov[4])}`);

  // 本編のキーは最後まで同じ
  await pg.goto('http://game.local/seed.html');
  const main = await pg.evaluate(K => K.map(k => localStorage.getItem(k) === 'MAIN:' + k), MAIN_KEYS);
  const mine = await pg.evaluate(() => Object.keys(localStorage).filter(k => !String(localStorage.getItem(k)).startsWith('MAIN:')).sort());
  check(main.every(Boolean), `${tag}本編のキー7つは変わっていない ${JSON.stringify(main)}`);
  check(mine.includes('eiheiji_vs_beasts_p3e2forest') || mobile, `${tag}試遊版が使ったキー ${JSON.stringify(mine)}`);
  // 読めなかったファイル：同じフォルダ（previews/p3e2-forest/）を先に試して、../../ で読めたものだけならよい
  const bad = miss.filter(p => !(p.startsWith('previews/p3e2-forest/') && got.has(p.slice('previews/p3e2-forest/'.length))));
  const used = [...got].filter(p => /^(assets|data|vendor)\//.test(p));
  check(!bad.length && used.some(p => p.startsWith('data/kamishihi/')) && used.some(p => p.includes('kei_truck')), `${tag}読み込み：${used.length}ファイルを ../../ で読めた（地図・KEI truck の GLB を含む）・読めないもの ${JSON.stringify(bad.slice(0, 5))}`);
  check(!errs.length, `${tag}エラーなし ${JSON.stringify(errs.slice(0, 3))}`);
  await b.close();
}

(async () => {
  await run(false);
  await run(true);
  console.log(ok ? 'PASS: 検収用の試遊版（previews/p3e2-forest）' : 'FAILED');
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
