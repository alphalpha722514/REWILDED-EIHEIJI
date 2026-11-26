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
  'function updateNPCs(dt){', 'window.__ev=code=>eval(code);\nfunction updateNPCs(dt){');
const MAIN_KEYS = ['eiheiji_vs_beasts_v010', 'REWILDED_EIHEIJI_SETTINGS', 'eiheiji_weatherEffects',
  'eiheiji_shadow', 'eiheiji_perf', 'eiheiji_aimMode', 'eiheiji_detail'];
const SAVE_KEY = 'eiheiji_vs_beasts_p3e3farm';
const DETAIL_KEY = 'eiheiji_p3e3f_detail';
const PLAYING = "S.mode==='playing'&&!REG.busy&&!P3A.busy&&!FARM_PREVIEW.busy";
const ENTRY = "curInter?.label==='古い農家に入る'&&!$('prompt').hidden";

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
  const menu = async name => {
    if (!(await page.locator('#farmPanel').isVisible())) await press('#farmToggle');
    await press(`[data-farm="${name}"]`);
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
      /^v0\.88\.1 古い農家（E3-1） 検収用の試遊版（本編とは別に保存）　第二章・/);
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
    await wait(`${PLAYING}&&!P3A.inside`);
    await wait(ENTRY);
    await act();
    await wait(`${PLAYING}&&P3A.inside&&P3A.inId==='farm'`);

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

    assert.deepEqual(await page.evaluate(() => window.mainKeyAccess), []);
    assert.deepEqual(blocked, []);
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
    console.log(`合格：${mobile ? 'iPhone 390×844（タップ）' : 'PC 1280×720（E キー）'}。入退室・試遊メニュー・保存の分離・ページエラーなし`);
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
