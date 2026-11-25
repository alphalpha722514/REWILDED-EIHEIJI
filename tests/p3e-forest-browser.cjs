#!/usr/bin/env node
// v0.88（P3-E の E-2）上志比の森林の確認（画面のない Chromium。Node の Playwright。10分ほど）。docs/p3e-e2.md
//
// - 木の位置・数・番号は今までのまま、杉・広葉樹・竹に分ける（約6割・3割・1割）。何度作っても同じ分け方
// - 広葉樹はどこでも切れて、丸太を割ると山地の硬木。切った広葉樹は生えてこない（fb）・苗木が1本取れる
// - 切り株に苗木を植えると、時間がたつと育って、また切れる（pl）。杉は今までどおり（f）
// - 古いセーブ（fb が無い）で、前に切った広葉樹は生えてこない方の記録へ移る
// - 竹林の竹を切る（竹+2・待ち時間）。山の薬草（森の奥・摘む・待ち時間）。かまどで薬草粥・荷台の救急箱に入れると戻りが2倍
// - 近くの林床（下草・木漏れ日・苔の岩・倒木）を区画ごとに作る・捨てる（当たり判定も外す）
// - 「描く細かさ：軽量」で遠くの木を減らす・戻す。セーブの読み書き。光明寺へ戻ると何も残らない。エラーなし
// - FOREST_SHOTS=フォルダ で森の画面を撮る
//
// 使い方：THREE_JS=…/three.min.js node tests/p3e-forest-browser.cjs
const fs = require('node:fs');
const path = require('node:path');
const { inspect, isDeepStrictEqual } = require('node:util');
const { chromium } = require('playwright');

const ROOT = path.dirname(__dirname);
const THREE = fs.readFileSync(process.env.THREE_JS || '/home/claude/v010/node_modules/three/build/three.min.js', 'utf8');
const HTML = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){');
const SHOTS = process.env.FOREST_SHOTS;
const BASE = `(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; prog.arms.axeStone=WEAPONS.axeStone.maxDur; return 1; })()`;
const TRAVEL = "(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()";
const CALM = "(()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; prog.f10.tod=150; f10LightNow(); weather.state='clear'; return 1; })()";
const HASH = "(()=>{ let h=0; E2.all.forEach((o,i)=>{ h=(h*31+(o.ty==='sugi'?1:o.ty==='kona'?2:3)*(i%97+1))%1000000007; }); return [E2.all.length,h]; })()";

// Python 版と同じように、配列や集計値を1行で表示する。
const show = value => inspect(value, { breakLength: Infinity, maxArrayLength: null, compact: true });

async function run() {
  let ok = true;
  const check = (condition, message) => {
    console.log((condition ? 'ok   ' : 'FAIL ') + message);
    ok = ok && !!condition;
  };
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const ctx = await browser.newContext({ viewport: { width: 1100, height: 680 } });
    const pg = await ctx.newPage();
    const errs = [];
    pg.on('pageerror', e => errs.push(String(e)));
    await ctx.route('**/*', async route => {
      const url = route.request().url();
      if (url.includes('three.min.js') || url.includes('three.js/r128')) {
        return route.fulfill({ body: THREE, contentType: 'application/javascript' });
      }
      if (!url.startsWith('http://game.local/')) return route.abort();
      const relative = decodeURIComponent(new URL(url).pathname.slice(1));
      if (relative === '' || relative === 'index.html') {
        return route.fulfill({ body: HTML, contentType: 'text/html; charset=utf-8' });
      }
      const file = path.resolve(ROOT, relative);
      if (file.startsWith(ROOT + path.sep) && fs.existsSync(file) && fs.statSync(file).isFile()) {
        return route.fulfill({ body: fs.readFileSync(file) });
      }
      return route.fulfill({ status: 404, body: '' });
    });
    const E = code => pg.evaluate(code => window.__ev(code), code);
    async function until(js, ms = 20000) {
      for (let t = 0; t < ms; t += 200) {
        if (await E(js)) return true;
        await pg.waitForTimeout(200);
      }
      return false;
    }
    async function travel(to) {
      await E(to === 'kamishihi' ? TRAVEL : "(async()=>{ await regionTravel('komyoji',null,{force:true}); })()");
      await until(`REG.cur==='${to}'&&!REG.busy`, 120000);
      await pg.waitForTimeout(500);
    }

    await pg.goto('http://game.local/', { waitUntil: 'load', timeout: 300000 });
    await pg.waitForFunction("typeof window.__ev==='function'", null, { timeout: 300000 });
    await pg.click('#btnNew');
    await pg.waitForTimeout(500);
    for (let i = 0; i < 15; i++) {
      if (await pg.evaluate("document.getElementById('dialog').hidden")) break;
      await pg.click('#dialog');
      await pg.waitForTimeout(200);
    }
    await E(BASE);
    await E("(()=>{ try{ localStorage.removeItem('eiheiji_detail'); }catch(e){} GFX.detail='std'; E1.off=true; return 1; })()");
    // KEI truck は救急箱の確認で上志比へ移すので、往復の当たり判定の比較から除く（2026-11-25）
    const home = await E("[circles.length, oboxes.filter(o=>o.tag!=='truck').length, boxes.length]");
    await travel('kamishihi');
    await E(CALM);

    // ---- 分け方 ----
    const st = await E(`(()=>{ const c=E2.count, n=c.sugi+c.kona+c.take, kt=[...REG.live.ktrees.values()]; const ty={}; for(const t of kt) ty[t.ty||'kp']=(ty[t.ty||'kp']||0)+1;
    const keyOK=kt.every(t=>/^(k\\d+_\\d+_\\d+|kp\\d+)$/.test(t.key)), konaFlag=kt.filter(t=>t.ty==='kona').every(t=>t.kona===1), sugiG=kt.filter(t=>t.ty==='sugi').every(t=>t.gs===E2GS.sugi);
    const p3a=E2.all.filter(o=>o.tr[4]).length; return {n, c, total:REG.live.treeCount, ty, keyOK, konaFlag, sugiG, take:E2.take.length, p3a,
      share:[c.sugi,c.kona,c.take].map(v=>Math.round(v/(n-p3a)*1000)/10)}; })()`);
    const sh = st.share;
    check(st.n === st.total && st.keyOK && st.konaFlag && st.sugiG, `木の数は今までのまま ${st.n}本（番号の形も同じ）・広葉樹に印・杉は P3-A の杉の大きさ`);
    check(sh[0] >= 55 && sh[0] <= 65 && sh[1] >= 27 && sh[1] <= 33 && sh[2] >= 8 && sh[2] <= 12, `杉・広葉樹・竹の割合（%）${show(sh)}（約6割・3割・1割）・${show(st.c)}・竹林 ${st.take}か所`);
    const h1 = await E(HASH);

    // ---- 広葉樹を切る・苗木・植える・育つ ----
    let r = await E(`(()=>{ const kt=[...REG.live.ktrees.values()].find(t=>t.ty==='kona'&&!t.felled&&dist(t.x,t.z,6200,900)<2500); inv.naegi=0; inv.hardwood=0; const k=prog.kami;
    const rec=kamiTreeRec(kt); f4Fell(rec,0.3); const tr=F4.trunks.find(t=>t.key===kt.key); const L=REG.live.kw.logs, n0=L.length; f4Buck(tr); const hw=L.slice(n0).filter(l=>l[5]).length;
    window.__kt=kt; return [k.fb.includes(kt.key), k.f.includes(kt.key), inv.naegi, kt.felled, hw, kt.col.active]; })()`);
    check(isDeepStrictEqual(r, [true, false, 1, true, 2, false]), `広葉樹を切る：生えてこない記録（fb）へ・苗木+1・硬木の丸太2本 ${show(r)}`);
    await E("(()=>{ e2Tick(REG.live); return 1; })()");
    r = await E(`(()=>{ const kt=__kt; P.x=kt.x+1.0; P.z=kt.z; const L=[]; REG.live.inter(L); const a=L.find(o=>o.label.startsWith('広葉樹の切り株に苗木を植える')); const st=E2.stumpIM?E2.stumpIM.count:0;
    if(a) a.act(); e2Tick(REG.live); return [!!a, st, inv.naegi, prog.kami.pl[kt.key]!=null, E2.sapIM?E2.sapIM.count:0]; })()`);
    check(r[0] && r[1] >= 1 && r[2] === 0 && r[3] && r[4] >= 1, `切り株が見える・苗木を植える（調べる）・苗木の形が出る ${show(r)}`);
    r = await E("(()=>{ const kt=__kt, k=prog.kami; k.pl[kt.key]=stats.time-E2.grow-1; E2.t=0; e2Tick(REG.live); return [kt.felled, kt.col.active, k.fb.includes(kt.key), k.pl[kt.key]==null]; })()");
    check(isDeepStrictEqual(r, [false, true, false, true]), `植えてから時間がたつと育つ（また切れる・当たり判定も戻る）${show(r)}`);
    r = await E(`(()=>{ const kt=[...REG.live.ktrees.values()].find(t=>t.ty==='sugi'&&!t.felled&&dist(t.x,t.z,6200,900)<2500); const k=prog.kami, n0=inv.naegi; f4Fell(kamiTreeRec(kt),0.2);
    const tr=F4.trunks.find(t=>t.key===kt.key); const L=REG.live.kw.logs, n1=L.length; f4Buck(tr); return [k.f.includes(kt.key), k.fb.includes(kt.key), inv.naegi-n0, L.slice(n1).filter(l=>l[5]).length]; })()`);
    check(isDeepStrictEqual(r, [true, false, 0, 0]), `杉は今までどおり（f・硬木にならない・苗木なし）${show(r)}`);

    // ---- 竹林・山の薬草 ----
    r = await E(`(()=>{ const c=E2.take.find(c=>dist(c.x,c.z,6200,900)<2500); P.x=c.x+1.0*c.s*E2GS.take+0.6; P.z=c.z; const L=[]; REG.live.inter(L); const a=L.find(o=>o.label==='竹林の竹を切る（竹+2）'); const b0=inv.bamboo||0;
    if(a) a.act(); const L2=[]; REG.live.inter(L2); return [!!a, (inv.bamboo||0)-b0, prog.kami.n['t'+c.i]!=null, L2.some(o=>o.label.startsWith('竹林：切った竹が伸びるのを待つ'))]; })()`);
    check(isDeepStrictEqual(r, [true, 2, true, true]), `竹林の竹を切る：竹+2・待ち時間（t の記録）${show(r)}`);
    r = await E(`(()=>{ const H=REG.live.kw.nodes.filter(n=>n.k==='herb'), D=KAMI.D; let mb=1e9, mr=1e9; for(const n of H){ for(const b of D.bld) mb=Math.min(mb,dist(n.x,n.z,b[0],b[1])); for(const r of D.roads){ if(r.b) continue; for(let i=0;i<r.p.length-1;i++) mr=Math.min(mr,segDist(n.x,n.z,r.p[i][0],r.p[i][1],r.p[i+1][0],r.p[i+1][1])); } }
    const n=H[0]; P.x=n.x+0.8; P.z=n.z; const L=[]; REG.live.inter(L); const a=L.find(o=>o.label.includes('山の薬草を摘む')); inv.mherb=0; if(a) a.act(); const L2=[]; REG.live.inter(L2);
    return [H.length, Math.round(mb), Math.round(mr), !!a, inv.mherb>=1, prog.kami.n[n.key]!=null, L2.some(o=>o.label.startsWith('山の薬草：もう摘んだ')), H.every(n=>kamiReach(n.x,n.z)&&kamiCls(n.x,n.z)!==2)]; })()`);
    check(r[0] === 12 && r[1] >= 70 && r[2] >= 25 && isDeepStrictEqual(r.slice(3), [true, true, true, true, true]), `山の薬草：${r[0]}か所（家から ${r[1]}m・道から ${r[2]}m 以上・すべて歩ける所）・摘む・待ち時間 ${show(r.slice(3))}`);
    r = await E(`(()=>{ const sv=JSON.parse(JSON.stringify(kamiSave())), k2=kamiLoad(sv); return [JSON.stringify(k2.fb)===JSON.stringify(prog.kami.fb), Object.keys(k2.pl).length===Object.keys(prog.kami.pl).length,
    Object.keys(k2.n).filter(a=>/^[th]/.test(a)).length===Object.keys(prog.kami.n).filter(a=>/^[th]/.test(a)).length, k2.f.length===prog.kami.f.length]; })()`);
    check(isDeepStrictEqual(r, [true, true, true, true]), `セーブの読み書き（fb・pl・竹林と薬草の待ち時間・f）${show(r)}`);
    // かまど・荷台の救急箱
    r = await E(`(()=>{ if(!prog.kama.built){ prog.kama.built=1; } prog.kama.q=[]; foodAdd('rice',2); inv.mherb=2; inv.wood=20; const L=[]; kamaInteract(L,1); L[0].act();
    const bt=[...document.querySelectorAll('#defenseChoice button')].find(b=>b.textContent.startsWith('山の薬草で薬草粥を炊く')); const hasImg=!!(bt&&bt.querySelector('img')); if(bt) bt.click(); const d=document.getElementById('defenseChoice'); if(d) d.remove(); S.mode='playing';
    return [!!bt, prog.kama.q.includes('herbPorridge'), inv.mherb]; })()`);
    check(isDeepStrictEqual(r, [true, true, 1]), `かまど：山の薬草で薬草粥を炊く（米1・山の薬草1）${show(r)}`);
    r = await E(`(()=>{ const t=trk(); t.region=REG.cur; t.fac=t.fac||{}; t.fac.aid=1; TRUCK.x=P.x+2; TRUCK.z=P.z; TRUCK.drive=false; P.lastHurt=-999; inv.mherb=1;
    const L=[]; truckInteractables(L); const a=L.find(o=>o.label.startsWith('荷台の救急箱に山の薬草を入れる')); if(a) a.act();
    P.hp=P.maxHp-50; const h0=P.hp; truckAidUpdate(1); const d1=P.hp-h0; TRUCK.herbT=0; P.hp=P.maxHp-50; truckAidUpdate(1); const d0=P.hp-(P.maxHp-50); P.hp=P.maxHp; return [!!a, inv.mherb, Math.round(d1/d0*10)/10]; })()`);
    check(isDeepStrictEqual(r, [true, 0, 2.0]), `荷台の救急箱に山の薬草：体力の戻りが2倍 ${show(r)}`);

    // ---- 林床（近くの区画）----
    await E("(()=>{ E1.off=false; return 1; })()");
    const [x, z] = await E("(()=>{ let best=null; for(const [gk,a] of E2.grid){ const c={sugi:0,kona:0,take:0}; for(const t of a) c[t[2]]++; const sc=Math.min(c.kona,15)+Math.min(c.take,8)*2+Math.min(c.sugi,15); if(!best||sc>best.sc) best={sc,x:a[0][0],z:a[0][1]}; } return [best.x,best.z]; })()");
    await E(`(()=>{ P.x=6200; P.z=900; cam.override={p:new THREE.Vector3(${x}+3,groundH(${x}+3,${z}+6)+1.7,${z}+6), l:new THREE.Vector3(${x}-10,groundH(${x}-10,${z}-12)+2.5,${z}-12), fov:62}; return 1; })()`);
    const done = await until(`!E1.busy&&[...E1.cells.values()].every(c=>c.o||e1RectD(c,${x}+3,${z}+6)>=gfxRad().in)`, 240000);
    const fl = await E("(()=>{ let fern=0, sun=0, cols=0, rock=0, log=0; window.__fc=[]; for(const c of E1.cells.values()) if(c.o){ if(c.o.fern) fern+=c.o.fern.count; if(c.o.sun) sun++; cols+=c.o.cols.length; for(const k of c.o.cols){ __fc.push(k); if(k.tag==='rock') rock++; if(k.tag==='log') log++; } } return [fern, sun, rock, log]; })()");
    check(done && fl[0] > 100 && fl[1] >= 1 && fl[2] + fl[3] >= 1, `近くの林床：下草 ${fl[0]}・木漏れ日の区画 ${fl[1]}・苔の岩 ${fl[2]}・倒木 ${fl[3]}`);
    const q = await E(`(()=>{ let nq=0, fq=0, dup=0, miss=0; for(const e of E2.lo){ const A=e.lo.instanceMatrix.array; for(const Q of e.q){ if(!Q) continue; if(Q.near){ nq++; if(!Q.hi.visible) miss++; for(let i=Q.i0;i<Q.i0+Q.n;i++) if(A[i*16+15]!==0) dup++; } else if(Q.hi.visible) fq++; } }
    return [nq, fq, dup, miss]; })()`);
    check(q[0] >= 1 && q[1] === 0 && q[2] === 0 && q[3] === 0, `近い4分の1の区画だけ細かい形・そこの遠い形は消す（近い ${q[0]}・遠いのに細かい ${q[1]}・二重 ${q[2]}・抜け ${q[3]}）`);
    if (SHOTS) {
      fs.mkdirSync(SHOTS, { recursive: true });
      await E("($('hud').hidden=true, 1)");
      await pg.waitForTimeout(1500);
      await pg.screenshot({ path: path.join(SHOTS, 'inside.png'), timeout: 300000 });
      await E(`(()=>{ cam.override={p:new THREE.Vector3(${x}-40,groundH(${x}-40,${z}+40)+28,${z}+40), l:new THREE.Vector3(${x},groundH(${x},${z}),${z}), fov:55}; return 1; })()`);
      await until(`!E1.busy&&[...E1.cells.values()].every(c=>c.o||e1RectD(c,${x}-40,${z}+40)>=gfxRad().in)`, 240000);
      await pg.waitForTimeout(1500);
      await pg.screenshot({ path: path.join(SHOTS, 'above.png'), timeout: 300000 });
      await E("($('hud').hidden=false, 1)");
    }
    // 軽量：遠くの木を減らす
    r = await E(`(()=>{ const thinOn=()=>{ let on=0, n=0; for(const e of E2.lo){ const A=e.lo.instanceMatrix.array; for(let i=0;i<e.n;i++) if(e.thin[i]&&e.orig[i*16+15]!==0){ n++; if(A[i*16+15]!==0) on++; } } return [on,n]; };
    applyDetail('lite'); const [on1,n]=thinOn(), red=E2.lo.reduce((s,e)=>s+e.n-e.keep,0), all=E2.lo.reduce((s,e)=>s+e.n,0); applyDetail('std'); const [on2]=thinOn(); return [on1===0, on2>n*0.9, Math.round(red/all*100)]; })()`);
    check(r[0] && r[1] && r[2] >= 30 && r[2] <= 50, `「描く細かさ：軽量」で遠くの木を ${r[2]}% 減らす・標準で戻す ${show(r.slice(0, 2))}`);
    await E("(()=>{ P.x=6500; P.z=470; cam.override={p:new THREE.Vector3(6500,groundH(6500,470)+30,470), l:new THREE.Vector3(6520,groundH(6520,430),430), fov:55}; return 1; })()");
    await until("!E1.busy&&[...E1.cells.values()].every(c=>!c.o||e1RectD(c,6500,470)<=gfxRad().out)", 120000);
    r = await E("(()=>{ const live=new Set(); for(const c of E1.cells.values()) if(c.o) for(const k of c.o.cols) live.add(k); const C=new Set(circles), O=new Set(oboxes); return __fc.filter(k=>!live.has(k)&&(C.has(k)||O.has(k))).length; })()");
    check(r === 0, `離れると林床の当たり判定も外れる（残り ${show(r)}）`);

    // ---- 古いセーブ：前に切った広葉樹（f の中）は生えてこない方へ ----
    await E("(cam.override=null, 1)");
    const old = await E("(()=>{ const kt=[...REG.live.ktrees.values()].find(t=>t.ty==='kona'&&!t.felled&&t.key[1]!=='p'); const sv=kamiSave(); delete sv.fb; delete sv.pl; sv.f=sv.f.concat([kt.key]); window.__old=kt.key; prog.kami=kamiLoad(sv); return kt.key; })()");
    await travel('komyoji');
    const back = await E("[E1.cells===null, E2.all===null, circles.length, oboxes.filter(o=>o.tag!=='truck').length, boxes.length]");
    check(back[0] && back[1] && isDeepStrictEqual(back.slice(2), home), `光明寺へ戻ると捨てる・当たり判定が残らない ${show(back)} / ${show(home)}`);
    await travel('kamishihi');
    r = await E(`(()=>{ const k=prog.kami, kt=REG.live.ktrees.get('${old}'); return [k.f.includes('${old}'), k.fb.includes('${old}'), !!(kt&&kt.felled)]; })()`);
    check(isDeepStrictEqual(r, [false, true, true]), `古いセーブ：前に切った広葉樹は生えてこない記録へ移る ${show(r)}`);
    const h2 = await E(HASH);
    check(isDeepStrictEqual(h1, h2), `作り直しても同じ分け方 ${show(h1)} / ${show(h2)}`);
    const sv = await E("(saveGame(), (()=>{ const d=JSON.parse(localStorage.getItem(SAVE_KEY)); return [d.v, typeof d.inv.naegi, typeof d.inv.mherb, SAVE_KEY]; })())");
    check(isDeepStrictEqual(sv, [1, 'number', 'number', 'eiheiji_vs_beasts_v010']), `セーブ：v:1・保存キーは同じ・苗木と山の薬草を持ち物に ${show(sv)}`);
    check(errs.length === 0, `エラーなし ${show(errs.slice(0, 3))}`);
  } finally {
    await browser.close();
  }
  console.log(ok ? 'PASS: 上志比の森林（E-2）' : 'FAILED');
  process.exitCode = ok ? 0 : 1;
}

run().catch(error => {
  console.error('FAIL 上志比の森林（E-2）', error);
  process.exitCode = 1;
});
