#!/usr/bin/env node
// 古い農家の試遊版を PC と iPhone の画面・入力で確認する。通信は手元のファイルで応答する。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium, devices } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const PAGE = 'previews/p3e3-farm/index.html';
const ORIGIN = 'http://game.local';
const THREE = fs.readFileSync(process.env.THREE_JS || '/home/claude/v010/node_modules/three/build/three.min.js');
const HTML = fs.readFileSync(path.join(ROOT, PAGE), 'utf8').replace(
  'function updateNPCs(dt){', 'window.__ev=code=>eval(code);\nfunction updateNPCs(dt){').replace(
  'function interact(){', 'function interact(){ window.farmEntryTrace?.record("interact");');
const MAIN_KEYS = ['eiheiji_vs_beasts_v010', 'REWILDED_EIHEIJI_SETTINGS', 'eiheiji_weatherEffects',
  'eiheiji_shadow', 'eiheiji_perf', 'eiheiji_aimMode', 'eiheiji_detail', 'eiheiji_camPitch'];
const SAVE_KEY = 'eiheiji_vs_beasts_p3e3farm';
const DETAIL_KEY = 'eiheiji_p3e3f_detail';
const PLAYING = "S.mode==='playing'&&!REG.busy&&!P3A.busy&&!FARM_PREVIEW.busy";
const ENTRY = "curInter?.label==='古い農家に入る'&&!$('prompt').hidden";
const READY_TO_ENTER = `${PLAYING}&&!P3A.inside&&$('farmPanel').hidden&&(${ENTRY})`;
const FARM_RECORD = '[p3bState().e3.s,p3bState().e3.map,prog.chapter2.progress.e3farm]';
const SAVED_FARM_RECORD = '(()=>{ const d=readSave(); return [d.p3.e3.s,d.p3.e3.map,d.chapter2.progress.e3farm]; })()';

async function run(browser, mobile) {
  const viewport = mobile ? { width: 390, height: 844 } : { width: 1280, height: 720 };
  const ctx = await browser.newContext(mobile ? { ...devices['iPhone 13'], viewport } : { viewport });
  const page = await ctx.newPage();
  const errors = [], blocked = [];
  page.on('pageerror', error => errors.push(String(error)));
  page.on('console', msg => {
    if (msg.text().startsWith('試遊版：本編のキーには触れない')) blocked.push(msg.text());
  });
  const ev = code => page.evaluate(code => window.__ev(code), code);
  const wait = code => page.waitForFunction(code => window.__ev?.(code), code, { timeout: 120000, polling: 250 });
  const press = selector => mobile ? page.locator(selector).tap() : page.locator(selector).click();
  const act = () => mobile ? press('#tbAct') : page.keyboard.press('e');
  const enterFarm = async (step, closeMenu = false) => {
    await ev(`(() => {
      const events = [];
      window.farmEntryTrace = { events, record(type, event) {
        const door = farmPreviewDoor();
        events.push({
          type, mode: S.mode, label: curInter?.label ?? null, ready: ${READY_TO_ENTER},
          focus: document.activeElement?.id, target: event?.target?.id, repeat: event?.repeat,
          prompt: $('prompt').hidden ? null : $('prompt').textContent,
          busy: { region: REG.busy, interior: P3A.busy, preview: FARM_PREVIEW.busy },
          cut: STF.cut, bossIntro: !!bossCinema52(), fishing: !!P3D.fish, inside: P3A.inside,
          player: { x: P.x, z: P.z },
          door: door && { x: door.x, z: door.z, distance: dist(P.x,P.z,door.x,door.z) },
          suzuki: { x: SZ.x, z: SZ.z, distance: dist(P.x,P.z,SZ.x,SZ.z), order: SZ.order },
        });
      } };
    })()`);
    try {
      if (closeMenu) {
        // 閉じるクリックと入室操作の間に待ちを挟まず、入力時の状態を記録する。
        await press('#farmToggle');
      } else {
        await wait(READY_TO_ENTER);
        await ev('window.farmEntryTrace.record("before")');
      }
      await act();
      const events = await ev('window.farmEntryTrace.record("after"); window.farmEntryTrace.events');
      const input = events.find(event => event.type === 'interact');
      assert.equal(input?.label, '古い農家に入る', step);
      assert.ok(input.ready, step);
      assert.notEqual(events.at(-1).mode, 'menu', step);
      await wait(`${PLAYING}&&P3A.inside&&P3A.inId==='farm'`);
    } catch (error) {
      const events = await ev('window.farmEntryTrace.record("failure"); window.farmEntryTrace.events');
      console.error(step, JSON.stringify(events, null, 2));
      throw error;
    } finally {
      await ev('delete window.farmEntryTrace');
    }
  };
  const menu = async name => {
    if (!(await page.locator('#farmPanel').isVisible())) await press('#farmToggle');
    await press(`[data-farm="${name}"]`);
  };
  const checkMainKeys = async () => {
    assert.deepEqual(await page.evaluate(() => window.mainKeyAccess), []);
    assert.deepEqual(blocked, []);
  };
  const reloadSave = async () => {
    await checkMainKeys();
    await page.reload({ timeout: 120000 });
    await press('#btnContinue');
    await wait(`${PLAYING}&&REG.cur==='kamishihi'&&P3A.on`);
  };
  const search = async ({ x, z, label, dialog, reward }) => {
    await ev(`P.x=P3IN.farm.o.x+${x}; P.z=P3IN.farm.o.z+${z}`);
    assert.ok(await ev('szFree(P.x,P.z,P.r)'), `${label}の前に立てる`);
    const before = await ev('({...inv})');
    await wait(`curInter?.label===${JSON.stringify(label)}`);
    await act();
    if (dialog) {
      await page.locator('#dialog').waitFor({ state: 'visible' });
      assert.equal(await page.locator('#dlgName').textContent(), '');
      assert.equal(await page.locator('#dlgText').textContent(), dialog);
      await wait('performance.now()-dlgLock>=180');
      if (mobile) await press('#dialog');
      else await act();
      await page.locator('#dialog').waitFor({ state: 'hidden' });
    }
    for (const [id, amount] of Object.entries(reward ?? {})) before[id] += amount;
    assert.deepEqual(await ev('({...inv})'), before, label);
  };
  try {
    await ctx.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.pathname.endsWith('/three.min.js')) return route.fulfill({ body: THREE, contentType: 'application/javascript' });
      if (url.origin !== ORIGIN) return route.abort();
      const file = decodeURIComponent(url.pathname.slice(1));
      if (file === 'seed.html') return route.fulfill({ body: '<!doctype html><title>保存の確認</title>', contentType: 'text/html' });
      if (file === PAGE) return route.fulfill({ body: HTML, contentType: 'text/html; charset=utf-8' });
      const local = path.resolve(ROOT, file);
      if (local.startsWith(ROOT + path.sep) && fs.statSync(local, { throwIfNoEntry: false })?.isFile()) {
        return route.fulfill({ path: local });
      }
      return route.fulfill({ status: 404, body: '' });
    });

    await page.goto(ORIGIN + '/seed.html');
    await page.evaluate(keys => {
      for (const key of keys) localStorage.setItem(key, '本編:' + key);
    }, MAIN_KEYS);
    await ctx.addInitScript(keys => {
      window.mainKeyAccess = [];
      if (location.pathname.endsWith('/seed.html')) return;
      for (const type of ['keydown', 'keyup']) {
        window.addEventListener(type, event => {
          if (event.key.toLowerCase() === 'e') window.farmEntryTrace?.record(type, event);
        }, true);
      }
      for (const method of ['getItem', 'setItem', 'removeItem', 'clear']) {
        const original = Storage.prototype[method];
        Storage.prototype[method] = function (key, ...args) {
          if (method === 'clear' || keys.includes(String(key))) window.mainKeyAccess.push([method, key]);
          return Reflect.apply(original, this, [key, ...args]);
        };
      }
    }, MAIN_KEYS);

    await page.goto(ORIGIN + '/' + PAGE, { timeout: 120000 });
    await wait("typeof P3IN==='object'");
    assert.match(await page.locator('.tver').textContent(),
      /^v0\.(?:88\.1|(?:89|9[0-9])(?:\.[0-9]+)?) 古い農家（E3-1・E3-2） 検収用の試遊版（本編とは別に保存）　第二章・/);
    assert.deepEqual(await ev('[SAVE_KEY,SND_KEY,WEATHER_PREF]'),
      [SAVE_KEY, 'REWILDED_EIHEIJI_SETTINGS_p3e3farm', 'eiheiji_p3e3f_weatherEffects']);
    assert.equal(await page.locator('#btnFarmStart').textContent(), 'テスト：古い農家の前で始める');
    await press('#btnFarmStart');
    await wait(`${PLAYING}&&REG.cur==='kamishihi'`);
    await wait(ENTRY);
    const distance = await ev('dist(P.x,P.z,farmPreviewDoor().x,farmPreviewDoor().z)');
    assert.ok(distance >= 1.5 - 0.001 && distance <= 2 + 0.001, `入口まで ${distance}m`);
    assert.ok(await ev("szWalkable(P.x,P.z)&&szHere()&&SZ.order==='follow'&&p3cOn()&&trk().repaired&&stfP().mutantMet&&weather.state==='clear'&&p3bClock()[0]===9"));

    await act();
    await wait(`${PLAYING}&&P3A.inside&&P3A.inId==='farm'`);
    assert.ok(await ev('p3bSzInside()'));
    await wait("curInter?.label==='外へ出る'");
    await act();
    await enterFarm('外へ出た直後の再入室');

    await press('#farmToggle');
    for (const selector of ['#farmToggle', '#farmPanel']) {
      const box = await page.locator(selector).boundingBox();
      assert.ok(box && box.x >= 0 && box.y >= 0 && box.x + box.width <= viewport.width &&
        box.y + box.height <= viewport.height, `${selector} の位置 ${JSON.stringify(box)}`);
    }
    assert.match(await page.locator('#farmStat').textContent(), /農家の中.*9:.*ついて来る/);
    await menu('suzuki');
    assert.equal(await ev('SZ.order'), 'wait');
    assert.match(await page.locator('#farmStat').textContent(), /ここで待つ/);
    await menu('suzuki');
    assert.equal(await ev('SZ.order'), 'follow');

    for (const [hour, light, label] of [[17, 'dusk', '夕方'], [23, 'night', '夜'], [9, 'day', '朝']]) {
      await menu('time');
      assert.deepEqual(await ev('[p3bClock()[0],lightMode]'), [hour, light]);
      assert.equal(await page.locator('[data-farm=time]').textContent(), '時刻：' + label);
    }
    const detail = await ev('GFX.detail');
    await menu('detail');
    assert.equal(await ev(`localStorage.getItem(${JSON.stringify(DETAIL_KEY)})`), detail === 'std' ? 'lite' : 'std');
    await menu('detail');
    assert.equal(await ev('GFX.detail'), detail);
    await menu('go');
    await wait(`${PLAYING}&&!P3A.inside&&(${ENTRY})`);
    await press('#farmToggle');
    assert.match(await page.locator('#farmStat').textContent(), /いる所：外/);
    await enterFarm('試遊メニューを閉じた直後の入室', true);
    assert.ok(await ev('p3bSzInside()'));

    const emptyRecord = [Array(8).fill(0), 0, { s: 0, map: 0 }];
    assert.deepEqual(await ev(FARM_RECORD), emptyRecord);
    await search({ x: 2.9, z: 19.4, label: 'かまどを調べる', reward: { charcoal: 2 } });
    await search({ x: 2.9, z: 19.4, label: 'かまどを見る' });
    const altar = { x: 15.1, z: 17.6, label: '仏壇に手を合わせる', dialog: '小さく手を合わせた。' };
    await search(altar);
    await search(altar);
    await search({ x: 14.5, z: 2.2, label: '蔵の棚を調べる', reward: { oldParts: 1, iron: 2 },
      dialog: '棚の奥の木箱に、折り畳んだ紙が入っていた。広げると、この辺りを描いた古い地図だった。' });
    const banner = page.locator('#banner.show .old-map-banner-note');
    await banner.waitFor({ state: 'visible' });
    assert.match(await banner.textContent(), /スマホは「地図」ボタン/);
    await search({ x: 14.5, z: 2.2, label: '蔵の棚を見る' });

    const foundRecord = [[1, 0, 0, 0, 0, 1, 0, 1], 1, { s: 129 + 32, map: 1 }];
    assert.deepEqual(await ev(FARM_RECORD), foundRecord);
    assert.deepEqual(await ev(SAVED_FARM_RECORD), foundRecord);
    await menu('go');
    await wait(`${PLAYING}&&!P3A.inside&&(${ENTRY})`);
    if (mobile) await press('#tbMap');
    else await page.keyboard.press('g');
    await page.locator('#oldMapLegend').waitFor({ state: 'visible' });
    await press('#mapClose');
    await reloadSave();
    assert.deepEqual(await ev(FARM_RECORD), foundRecord);

    const inventory = await ev('({...inv})');
    assert.equal(await page.locator('[data-farm="resetSearch"]').textContent(), '調査記録を初期化して試す');
    await menu('resetSearch');
    await page.getByText('調査記録と地図の印を初期化しました。拾った物は残ります', { exact: true }).waitFor();
    assert.deepEqual(await ev(FARM_RECORD), emptyRecord);
    assert.deepEqual(await ev(SAVED_FARM_RECORD), emptyRecord);
    assert.deepEqual(await ev('({...inv})'), inventory);
    await reloadSave();
    assert.deepEqual(await ev(FARM_RECORD), emptyRecord);
    assert.deepEqual(await ev('({...inv})'), inventory);

    await checkMainKeys();
    // 通常の操作が終わってから、念のため早期ガードそのものを確かめる。
    assert.ok(await page.evaluate(keys => keys.every(key => {
      localStorage.setItem(key, '変更を試す');
      localStorage.removeItem(key);
      return localStorage.getItem(key) === null;
    }), MAIN_KEYS));
    assert.deepEqual(await page.evaluate(() => window.mainKeyAccess), []);
    await page.goto(ORIGIN + '/seed.html');
    const stored = await page.evaluate(keys => keys.map(key => localStorage.getItem(key)), [...MAIN_KEYS, SAVE_KEY]);
    assert.deepEqual(stored.slice(0, -1), MAIN_KEYS.map(key => '本編:' + key));
    assert.equal(JSON.parse(stored.at(-1)).v, 1);
    assert.deepEqual(errors, []);
    console.log(`合格：${mobile ? 'iPhone 390×844（タップ）' : 'PC 1280×720（E キー）'}。入退室・調査・地図・初期化・試遊メニュー・保存の分離・ページエラーなし`);
  } finally {
    await ctx.close();
  }
}

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_BIN,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  });
  try {
    await run(browser, false);
    await run(browser, true);
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
