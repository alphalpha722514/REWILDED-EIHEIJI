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
      phase: TRSND.phase, rpm: TRSND.rpm, gear: TRSND.gear, level: TRSND.level, bass: TRSND.bass,
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
    await E(`(() => {
      const probe = window.__truckAudioProbe = { oscillator: 0, wave: 0, shaper: 0, frames: [] };
      let updating = false;
      // BGM や森の音の発音を除き、車音の更新中に作ったノードだけを数える。
      for (const [name, key] of [
        ['createOscillator', 'oscillator'], ['createPeriodicWave', 'wave'], ['createWaveShaper', 'shaper']
      ]) {
        const create = AC[name].bind(AC);
        AC[name] = (...args) => {
          if (updating) probe[key]++;
          return create(...args);
        };
      }
      const update = truckSoundUpdate;
      truckSoundUpdate = (...args) => {
        updating = true;
        try { update(...args); } finally { updating = false; }
        if (probe.record && stats.time !== probe.frames.at(-1)?.time) {
          probe.frames.push({
            time: stats.time, rpm: TRSND.rpm, gear: TRSND.gear,
            shift: TRSND.shift?.phase ?? null, level: TRSND.level
          });
        }
      };
      // 変速の短い間を記録できるよう、描画が遅いときの1コマの進みを抑える。
      const rawMax = F11D.rawMax;
      F11D.rawMax = 0.05;
      const drive = truckDrive, walk = truckWalk, collide = resolve;
      // 加減速は本編の処理を使い、試験中だけ平坦で障害物のない直線を走らせる。
      truckDrive = dt => {
        const { x, z } = TRUCK;
        TRUCK.gf = TRUCK.gr = 1;
        truckWalk = () => true;
        resolve = () => {};
        try { drive(dt); } finally { truckWalk = walk; resolve = collide; }
        TRUCK.x = P.x = x;
        TRUCK.z = P.z = z;
      };
      probe.finish = () => { truckDrive = drive; F11D.rawMax = rawMax; };
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
    check(idle.phase === 'running' && idle.engine > 0.05 && idle.roll === 0 &&
      idle.rpm >= 750 && idle.rpm <= 1000 && idle.gear === 1, '停車中は1速でアイドリングが鳴る');

    const nodes = await E('(({ oscillator, wave, shaper }) => ({ oscillator, wave, shaper }))(__truckAudioProbe)');
    check(nodes.wave === 1 && nodes.oscillator > 0 && nodes.shaper === 2,
      '初回乗車で波形、発振器、歪みと整流の WaveShaper を作る');
    check(await E(`(() => {
      const { jitter, timingDepth, strengthDepth, rectifier } = TRSND.nodes;
      return jitter?.type === 'lowpass' && jitter.frequency.value >= 10 && jitter.frequency.value <= 20 &&
        timingDepth?.gain.value > 0 && strengthDepth?.gain.value > 0 &&
        rectifier instanceof WaveShaperNode && rectifier.curve[0] > 0 &&
        rectifier.curve.at(-1) > 0 && rectifier.curve[(rectifier.curve.length - 1) / 2] === 0;
    })()`), '燃焼の間隔と強さを揺らすローパスと、燃焼の脈を整流する WaveShaper がある');
    await E('__truckAudioProbe.record = true; __truckInput.iz = 1');
    await gwait(10);
    const moving = await read();
    const full = await E('__truckAudioProbe.record = false; __truckAudioProbe.frames');
    const cutIndex = full.findIndex(frame => frame.shift === 'cut');
    const before = full[cutIndex - 1];
    const cut = full[cutIndex];
    const engaged = full.findIndex((frame, i) => i > cutIndex && !frame.shift);
    const after = full[engaged];
    const shifting = cut && after ? full.slice(cutIndex, engaged) : [];
    check(moving.shiftUp >= 2 && moving.gear >= 3 &&
      full.some(frame => frame.gear === 2) && full.some(frame => frame.gear === 3), '全開加速で1速から順に3速以上へ上がる');
    check(before && after && shifting.some(frame => frame.rpm <= before.rpm - 1200) &&
      shifting.some(frame => frame.level < before.level * 0.5) &&
      after.level >= before.level * 0.5 && after.time - cut.time <= 0.4,
    '変速中に回転が1200rpm以上落ち、排気が半分未満にしぼんで0.4秒以内に戻る');
    const rising = full.find(frame => frame.rpm >= 5000 && frame.gear === 1 && !frame.shift);
    check(rising && before && before.rpm > rising.rpm && before.level > rising.level &&
      moving.engine > idle.engine && moving.roll > 0, '加速で回転と排気音量が上がり、タイヤが転がる');
    check(await E(`__truckAudioProbe.oscillator === ${nodes.oscillator} &&
      __truckAudioProbe.wave === ${nodes.wave} && __truckAudioProbe.shaper === ${nodes.shaper}`),
      '10ゲーム秒走っても車音の波形、発振器、WaveShaper を作り足さない');

    await until('TRSND.gear === 5 && !TRSND.shift && Math.hypot(TRUCK.vx, TRUCK.vz) >= truckPerf().speed - 0.01');
    const atTop = await read();
    await gwait(3);
    const held = await read();
    check(held.gear === 5 && held.limiter === atTop.limiter &&
      atTop.rpm >= 5500 && atTop.rpm <= 6500 && held.rpm >= 5500 && held.rpm <= 6500,
    '5速の最高速で全開を3ゲーム秒続けても燃料カットが入らず、回転数は5500〜6500rpm');

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

    await gwait(13);
    const coast = await read();
    check(coast.shiftDown > moving.shiftDown, 'アクセルを戻して減速するとシフトダウンする');
    check(coast.rpm >= 750 && coast.rpm <= 1000 && coast.gear === 1 && coast.roll === 0,
      '停車すると1速のアイドリングへ戻る');

    await E('__truckAudioProbe.frames = []; __truckAudioProbe.record = true; __truckInput.iz = 0.4');
    await gwait(3);
    const light = await E(`__truckAudioProbe.record = false; __truckInput.iz = 0;
      __truckAudioProbe.finish(); __truckAudioProbe.frames.find(frame => frame.shift === 'cut')`);
    check(light && cut && light.rpm < cut.rpm - 1200, '軽く踏むと全開より低い回転数でシフトアップする');

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
    check(Math.abs(upgraded.rpm - idle.rpm) < 100 && upgraded.bass > idle.bass && upgraded.level > idle.level, '改修すると低い音が太く、少し大きくなる');

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
    await until('AU.car.gain.value > 0.95 && TRSND.nodes.engine.gain.value > 0.05');

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
