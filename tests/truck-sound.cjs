#!/usr/bin/env node
// KEI truck の Web Audio と設定を画面のない Chromium で確認する。
// 使い方：THREE_JS=…/three.min.js node tests/truck-sound.cjs
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const ROOT = path.dirname(__dirname);
const THREE = fs.readFileSync(process.env.THREE_JS || '/home/claude/v010/node_modules/three/build/three.min.js', 'utf8');
const HTML = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8').replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){');
const BASE = `(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; prog.arms.axeStone=WEAPONS.axeStone.maxDur; return 1; })()`;

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
    const read = () => E(`({
      phase: TRSND.phase, hz: TRSND.hz, level: TRSND.level, bass: TRSND.bass,
      roll: TRSND.roll, skid: TRSND.skid, car: AU.car.gain.value, engine: TRSND.nodes.engine.gain.value,
      ...TRSND.counts
    })`);
    // 本編と同じページで、旧設定を読んだ場合の初期値から確かめる。
    await ctx.addInitScript(() => {
      if (!localStorage.getItem('REWILDED_EIHEIJI_SETTINGS')) {
        localStorage.setItem('REWILDED_EIHEIJI_SETTINGS', JSON.stringify({ v: 1, se: true, bgm: true, amb: true }));
      }
    });
    await pg.goto('http://game.local/', { waitUntil: 'load', timeout: 300000 });
    await pg.waitForFunction("typeof window.__ev==='function'", null, { timeout: 300000 });
    check(await E("SND.car === true && !('car' in JSON.parse(localStorage.getItem(SND_KEY)))"), '古い設定では車の音がオン');
    await pg.click('#btnNew');
    for (let i = 0; i < 15; i++) {
      if (await pg.evaluate("document.getElementById('dialog').hidden")) break;
      await pg.click('#dialog');
    }
    await E(BASE);
    await until("S.mode === 'playing' && AU.ok && AC.state === 'running' && TRUCK.m?.visible", 120000);
    await E(`(() => {
      const h = truckHome();
      Object.assign(trk(), { x: h.x, z: h.z, a: h.a + Math.PI });
      truckLoadPos();
      P.x = TRUCK.x - 2;
      P.z = TRUCK.z;
      window.__truckInput = { ix: 0, iz: 0 };
      truckInput = () => window.__truckInput;
    })()`);
    check(await E(`(() => {
      truckBoard();
      f31AudioUpdate();
      return TRUCK.drive && TRSND.phase === 'crank' && TRSND.counts.starter === 1;
    })()`), '乗るとセルが回る');
    await until('TRSND.nodes.crank.gain.value > 0.01 || TRSND.counts.start > 0');
    await until('TRSND.counts.start === 1');
    check((await read()).start === 1, 'セルのあとに始動する');
    await gwait(0.9);
    const idle = await read();
    check(idle.phase === 'running' && idle.engine > 0.07 && idle.roll === 0 && idle.hz < 50, '停車中に低いアイドリングが鳴る');

    await E('(__truckInput.iz = 1)');
    await gwait(2.2);
    const moving = await read();
    check(moving.hz > idle.hz + 25 && moving.engine > idle.engine && moving.roll > 0, '走ると排気音が高く大きくなり、タイヤが転がる');

    // 判定が起こる離し方を、乱数を固定した1コマで確かめる。
    const pops = await E(`(() => {
      __truckInput.iz = 0;
      const before = TRSND.counts.backfire;
      const rand = Math.random;
      try {
        Math.random = () => 0.1;
        truckDrive(1/60);
        f31AudioUpdate();
      } finally { Math.random = rand; }
      return TRSND.counts.backfire - before;
    })()`);
    check(pops >= 2 && pops <= 4, `アクセルを離すと短い破裂音が鳴る（${pops}回）`);

    // 速いコーナーで車体の向きと速度がずれた状態を作り、物理側で横滑りさせる。
    const skid = await E(`(() => {
      const a = TRUCK.a;
      TRUCK.vx = 11*Math.sin(a) - 2*Math.cos(a);
      TRUCK.vz = 11*Math.cos(a) + 2*Math.sin(a);
      TRUCK.gf = TRUCK.gr = 1;
      __truckInput.ix = 1;
      truckDrive(1/60);
      f31AudioUpdate();
      __truckInput.ix = 0;
      return { slide: TRUCK.slide, skid: TRSND.skid };
    })()`);
    check(skid.slide > 0.3 && skid.skid > 0.03, '高速でハンドルを切って横滑りするとタイヤがきしむ');
    const landed = await E(`(() => {
      truckStop();
      truckSusp(1/60);
      TRUCK.susp.air = 0.4;
      truckSusp(1/60);
      f31AudioUpdate();
      return TRSND.counts.land;
    })()`);
    check(landed > 0, '車輪が空中から接地すると着地音が鳴る');

    await E('truckExit()');
    await until("TRSND.phase === 'off' && TRSND.nodes.engine.gain.value < 0.001");
    check((await read()).stop > idle.stop, '降りると回転が落ちて止まる');
    const beforeEmpty = await read();
    await E('trk().gas = 0; truckBoard()');
    await until("TRSND.phase === 'empty'");
    await gwait(0.8);
    const empty = await read();
    check(empty.starter === beforeEmpty.starter + 1 && empty.start === beforeEmpty.start && empty.engine < 0.001, '燃料0ではセルだけ鳴って始動しない');

    await E('trk().gas = 100; trk().hp = 10');
    await until("TRSND.phase === 'running'");
    await gwait(4.5);
    let faults = await read();
    check(faults.cough > empty.cough && faults.starve === empty.starve, `傷んだ車はせき込む（${faults.cough}回）`);
    await E('trk().hp = 100; trk().gas = 4');
    await gwait(4);
    faults = await read();
    check(faults.starve > empty.starve, `燃料が少ない車は息つぎする（${faults.starve}回）`);
    await E('trk().gas = 0');
    await until("TRSND.phase === 'empty' && TRSND.nodes.engine.gain.value < 0.001");
    check((await read()).stop === faults.stop + 1, '燃料が尽きると回転が落ちて止まる');

    await E('trk().gas = 100; trk().lv = 5; trk().hp = trkHpMax(trk())');
    await until("TRSND.phase === 'running'");
    await gwait(0.9);
    const upgraded = await read();
    check(upgraded.hz < idle.hz && upgraded.bass > idle.bass && upgraded.level > idle.level, '改修すると低い音が太く、少し大きくなる');

    await E('openPause()');
    await until('Math.abs(AU.car.gain.value - 0.5) < 0.005 && Math.abs(AU.amb.gain.value - 0.25) < 0.005 && Math.abs(AU.bgm.gain.value - 0.2) < 0.005');
    check((await read()).car < 0.505, '一時停止中は車の音も半分');
    await pg.setViewportSize({ width: 320, height: 568 });
    check(await E(`Array.from($('sndRow').children).every(b => {
      const box = b.getBoundingClientRect();
      return box.left >= 0 && box.right <= innerWidth && box.width > 0;
    })`), '幅320pxで音の設定が横にはみ出さない');
    await pg.click('#sndSe');
    check(await E('!SND.se && SND.car && AU.car.gain.value > 0.45'), '効果音をオフにしても車の音は鳴る');
    const other = await E('[AU.amb.gain.value, AU.bgm.gain.value]');
    await pg.click('#sndCar');
    const muted = await E('({ car: AU.car.gain.value, amb: AU.amb.gain.value, bgm: AU.bgm.gain.value, saved: JSON.parse(localStorage.getItem(SND_KEY)), label: $("sndCar").textContent })');
    check(muted.car === 0 && Math.abs(muted.amb - other[0]) < 0.005 && Math.abs(muted.bgm - other[1]) < 0.005,
      '車の音をオフにすると車のバスだけが消音される');
    check(muted.saved.v === 1 && muted.saved.car === false && muted.label === '車の音：オフ', '車の音のオフが設定に保存される');
    await pg.click('#sndCar');
    await pg.click('#btnResume');
    await until('AU.car.gain.value > 0.95 && TRSND.nodes.engine.gain.value > 0.07');

    const beforeTravel = await read();
    const travel = await E(`(async () => {
      __truckInput.iz = 0;
      const arrival = regionTravel('kamishihi', null, { force: true });
      const silent = REG.busy && S.mode === 'loading' && TRSND.phase === 'off' &&
        AU.car.gain.value === 0 && TRSND.bursts.size === 0;
      return { silent, arrived: await arrival && REG.cur === 'kamishihi' && !REG.busy && TRUCK.drive };
    })()`);
    check(travel.arrived, '運転席に乗って上志比へ着く');
    check(travel.silent, '地域移動で車の音が止まる');
    await gwait(1);
    const afterTravel = await read();
    check(afterTravel.phase === 'running' && afterTravel.car > 0 && afterTravel.engine > 0 &&
      afterTravel.starter === beforeTravel.starter && afterTravel.start === beforeTravel.start,
    '到着後はアクセルを踏まずに始動音なしでアイドリングへ戻る');
    await E('openPause()');
    await pg.click('#btnToTitle');
    check(await E("S.mode === 'title' && TRSND.phase === 'off' && AU.car.gain.value === 0"), 'タイトルへ戻ると車の音が止まる');
    await E(`localStorage.setItem(SND_KEY, ${JSON.stringify(JSON.stringify(muted.saved))})`);
    await pg.reload({ waitUntil: 'load', timeout: 300000 });
    await pg.waitForFunction("typeof window.__ev==='function'", null, { timeout: 300000 });
    check(await E('SND.car === false'), '保存した車の音のオフを再読込で復元する');
    check(errs.length === 0, `ページのエラーなし ${JSON.stringify(errs)}`);
  } finally {
    await browser.close();
  }
  console.log(ok ? 'PASS: KEI truck の音' : 'FAILED');
  process.exitCode = ok ? 0 : 1;
}

run().catch(error => {
  console.error('FAIL KEI truck の音', error);
  process.exitCode = 1;
});
