#!/usr/bin/env node
// v0.88（P3-E の E-2）森の音と地域の往復を画面のない Chromium で確認する。
// 使い方：THREE_JS=…/three.min.js node tests/p3e2-forest-sound.cjs
const fs = require('node:fs');
const path = require('node:path');
const { inspect } = require('node:util');
const { chromium } = require('playwright');

const ROOT = path.dirname(__dirname);
const THREE = fs.readFileSync(process.env.THREE_JS || '/home/claude/v010/node_modules/three/build/three.min.js', 'utf8');
const HTML = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){');
const BASE = `(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; prog.arms.axeStone=WEAPONS.axeStone.maxDur; return 1; })()`;

const SPOTS = `(() => {
  const best = {};
  for (const trees of E2.grid.values()) {
    const x = trees[0][0] + 1.5, z = trees[0][1] + 1.5;
    if (!kamiReach(x, z) || kamiCls(x, z) === 2) continue;
    const count = { kona: 0, sugi: 0, take: 0 };
    for (const [, , type] of trees) count[type]++;
    // 環境音を切る確認には、葉と梢が両方鳴る区画を使う。
    count.mixed = Math.min(count.kona + count.take, count.sugi);
    for (const [type, n] of Object.entries(count)) {
      if (n > (best[type]?.count || 0)) best[type] = { count: n, x, z };
    }
  }
  return best;
})()`;
const ZERO_COUNTS = '{ bird: 0, drum: 0, knock: 0, creak: 0 }';
const COUNT_SOUNDS = `(() => {
  window.__cnt = ${ZERO_COUNTS};
  const wrap = (original, name) => function() {
    __cnt[name]++;
    return original.apply(this, arguments);
  };
  e2Bird = wrap(e2Bird, 'bird');
  e2Drum = wrap(e2Drum, 'drum');
  e2Knock = wrap(e2Knock, 'knock');
  e2Creak = wrap(e2Creak, 'creak');
})()`;
const FOREST = '({ leaf: E2SND.leaf.gain.value, needle: E2SND.needle.gain.value })';
const quiet = ({ leaf, needle }) => leaf < 0.0001 && needle < 0.0001;
const noCalls = counts => Object.values(counts).every(n => n === 0);
const show = value => inspect(value, { breakLength: Infinity, compact: true });

async function run() {
  let ok = true;
  const check = (condition, message) => {
    console.log((condition ? 'ok   ' : 'FAIL ') + message);
    ok = ok && !!condition;
  };
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'] });
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
    async function until(js, timeout = 20000) {
      await pg.waitForFunction(code => window.__ev(code), js, { timeout, polling: 200 });
    }
    // 描画が遅くても、音が変わるまでゲーム内の時間で待つ。
    async function gwait(seconds) {
      const start = await E('stats.time');
      await until(`stats.time >= ${start} + ${seconds}`, 900000);
    }
    async function travel(to) {
      const arrived = await E(`regionTravel('${to}', null, { force: true })`);
      if (!arrived) throw new Error(`地域の移動に失敗した（${to}）`);
      await until(`REG.cur === '${to}' && !REG.busy`, 120000);
      if (to === 'kamishihi') {
        await E(`(() => {
          for (const e of enemies) if (!e.removed && e.x > 4000) e.x += 3000;
          prog.f10.tod = 150;
          f10LightNow();
          weather.state = 'clear';
        })()`);
      }
    }
    async function move({ x, z }) {
      await E(`(() => {
        P.x = ${x};
        P.z = ${z};
        P.y = kamiH(P.x, P.z);
        E2SND.t = 0;
      })()`);
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
    await until("S.mode === 'playing' && AU.ok && !!AC && !!noiseBuf", 120000);
    check(true, '音の準備ができた');
    await E(COUNT_SOUNDS);

    await travel('kamishihi');
    await until('!!E2SND', 120000);
    const spots = await E(SPOTS);
    if (!spots.kona || !spots.sugi || !spots.take || !spots.mixed) {
      throw new Error(`歩ける範囲に確認用の林が見つからない ${show(spots)}`);
    }

    await move(spots.kona);
    await gwait(4);
    let forest = await E(FOREST);
    check(forest.leaf > 0.005, `昼の広葉樹林で葉がざわめく ${show(forest)}`);

    await travel('komyoji');
    forest = await E(FOREST);
    check(quiet(forest), `広葉樹林から光明寺に着いた直後に葉と梢が静まる ${show(forest)}`);
    await E(`(window.__cnt = ${ZERO_COUNTS}, true)`);
    await gwait(20);
    forest = await E(FOREST);
    let counts = await E('({...__cnt})');
    check(quiet(forest) && noCalls(counts), `光明寺に20秒いても森の音が再開しない ${show(forest)} ${show(counts)}`);

    await travel('kamishihi');
    await move(spots.sugi);
    await gwait(4);
    forest = await E(FOREST);
    check(forest.needle > 0.005, `上志比に戻ると杉林で梢の風が鳴る ${show(forest)}`);
    await travel('komyoji');
    forest = await E(FOREST);
    check(quiet(forest), `杉林から光明寺に着いた直後に葉と梢が静まる ${show(forest)}`);

    await travel('kamishihi');
    await move(spots.kona);
    const birdStart = await E(`(window.__cnt = ${ZERO_COUNTS}, stats.time)`);
    await gwait(12);
    forest = await E(FOREST);
    check(forest.leaf > 0.005, `再び上志比に戻ると広葉樹林で葉がざわめく ${show(forest)}`);
    await until(`__cnt.bird + __cnt.drum > 0 || stats.time >= ${birdStart} + 60`, 900000);
    counts = await E('({...__cnt})');
    check(counts.bird + counts.drum > 0, `昼の森で鳥か木をたたく音が鳴る ${show(counts)}`);

    await move(spots.take);
    const knockStart = await E(`(window.__cnt = ${ZERO_COUNTS}, stats.time)`);
    await until(`__cnt.knock > 0 || stats.time >= ${knockStart} + 30`, 900000);
    counts = await E('({...__cnt})');
    check(counts.knock > 0, `竹林で竹が打ち合う音が鳴る ${show(counts)}`);

    await move({ x: 6493, z: 468 });
    await gwait(4);
    let river = await E('RIVSND.main.gain.value');
    check(river > 0.03, `本流のそばで川の音が大きくなる（${river}）`);
    await travel('komyoji');
    river = await E('RIVSND.main.gain.value');
    check(river === 0, `光明寺に着くと川の音が止まる（${river}）`);

    await travel('kamishihi');
    await move(spots.mixed);
    await gwait(4);
    const before = await E(`(() => {
      const gains = ${FOREST};
      SND.amb = false;
      window.__cnt = ${ZERO_COUNTS};
      return gains;
    })()`);
    await gwait(8);
    forest = await E(FOREST);
    counts = await E('({...__cnt})');
    let ambient = await E('AU.amb.gain.value');
    check(ambient < 0.01 && noCalls(counts) && forest.leaf < before.leaf && forest.needle < before.needle,
      `環境音を切って8秒後に葉と梢が静まり、鳥や竹が鳴らない（環境音 ${ambient}） ${show(before)} → ${show(forest)} ${show(counts)}`);
    await E('(SND.amb = true)');
    await gwait(4);
    ambient = await E('AU.amb.gain.value');
    check(ambient >= 0.4, `環境音を入れると音量が戻る（${ambient}）`);

    check(errs.length === 0, `ページのエラーなし ${show(errs)}`);
  } finally {
    await browser.close();
  }
  console.log(ok ? 'PASS: 上志比の森の音（E-2）' : 'FAILED');
  process.exitCode = ok ? 0 : 1;
}

run().catch(error => {
  console.error('FAIL 上志比の森の音（E-2）', error);
  process.exitCode = 1;
});
