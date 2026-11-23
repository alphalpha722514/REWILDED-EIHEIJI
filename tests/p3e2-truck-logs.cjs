#!/usr/bin/env node
// KEI truck の丸太の印・旧版とのセーブ互換。THREE_JS=…/three.min.js node tests/p3e2-truck-logs.cjs
// OLD_HTML=旧本編のファイル。TRUCK_PAGE=試遊版のファイル、OLD_PAGE=旧試遊版のファイル。
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const ROOT = path.dirname(__dirname);
const ORIGIN = 'http://game.local';
const PREVIEW = !!process.env.TRUCK_PAGE;
const SOURCE = process.env.TRUCK_PAGE || 'index.html';
const PAGE = '/' + path.relative(ROOT, path.resolve(ROOT, SOURCE)).split(path.sep).join('/');
const OLD_URL = path.posix.join(path.posix.dirname(PAGE), '__old_truck_test.html');
const SAVE_KEY = PREVIEW ? 'eiheiji_vs_beasts_p3e2forest' : 'eiheiji_vs_beasts_v010';
const MAIN_KEYS = ['eiheiji_vs_beasts_v010', 'REWILDED_EIHEIJI_SETTINGS', 'eiheiji_weatherEffects',
  'eiheiji_shadow', 'eiheiji_perf', 'eiheiji_aimMode', 'eiheiji_detail'];
const THREE = fs.readFileSync(process.env.THREE_JS || '/home/claude/v010/node_modules/three/build/three.min.js');
const oldFile = PREVIEW ? process.env.OLD_PAGE : process.env.OLD_HTML;
const oldGitPath = PREVIEW ? 'previews/p3e2-forest/index.html' : 'index.html';
const OLD_HTML = oldFile ? fs.readFileSync(oldFile, 'utf8') : execFileSync('git',
  ['show', 'origin/main:' + oldGitPath], { cwd: ROOT, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });

function exposeGame(html) {
  const marker = 'function updateNPCs(dt){';
  assert(html.includes(marker), 'ゲームに検証用の入口が必要');
  return html.replace(marker, 'window.__truckTest=source=>eval(source);\n' + marker);
}

const BASE = "(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;" +
  " prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true;" +
  " p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.mutantMet=true; prog.chapter2.currentChapter=2;" +
  " p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],trips:1,region:'komyoji'}; TRUCK.sync=false; trk();" +
  " P.weapon='axeIron'; prog.arms.axeIron=WEAPONS.axeIron.maxDur; P.dur=prog.arms.axeIron; refreshWeaponMesh(); saveGame(); })()";
const FACING_TRUCK = 'Object.assign(P,{x:TRUCK.x,z:TRUCK.z-3.6,facing:0})';

async function main() {
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  try {
    const context = await browser.newContext({ viewport: { width: 1000, height: 650 } });
    const pages = new Map([[PAGE, exposeGame(fs.readFileSync(path.resolve(ROOT, SOURCE), 'utf8'))],
      [OLD_URL, exposeGame(OLD_HTML)]]);
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await context.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.pathname.endsWith('/three.min.js')) return route.fulfill({ body: THREE, contentType: 'application/javascript' });
      if (url.origin !== ORIGIN) return route.abort();
      if (pages.has(url.pathname)) return route.fulfill({ body: pages.get(url.pathname), contentType: 'text/html; charset=utf-8' });
      if (url.pathname === '/__truck_seed.html') return route.fulfill({ body: '<!doctype html>', contentType: 'text/html' });
      const file = path.resolve(ROOT, '.' + decodeURIComponent(url.pathname));
      if (file.startsWith(ROOT + path.sep) && fs.existsSync(file) && fs.statSync(file).isFile()) return route.fulfill({ path: file });
      return route.fulfill({ status: 404, body: '' });
    });
    const E = code => page.evaluate(source => window.__truckTest(source), code);
    const atRegion = region => page.waitForFunction(id => window.__truckTest(
      "REG.cur===" + JSON.stringify(id) + "&&!REG.busy&&S.mode==='playing'"), region, { timeout: 120000 });
    const getSave = () => E('readSave()');
    const raw = () => page.evaluate(key => localStorage.getItem(key), SAVE_KEY);
    const putSave = data => page.evaluate(([key, value]) => localStorage.setItem(key, JSON.stringify(value)), [SAVE_KEY, data]);
    const open = async url => {
      await page.goto(ORIGIN + url, { waitUntil: 'load', timeout: 120000 });
      await page.waitForFunction("typeof window.__truckTest==='function'", null, { timeout: 60000 });
    };
    const resume = async (url = PAGE, region = 'komyoji') => {
      await open(url);
      await page.locator('#btnContinue').click();
      await atRegion(region);
    };
    const bed = () => E("({logs:trk().bed.logs.slice(),a:bedLogAttrs(trk()).slice()})");
    const checkBed = async (logs, a) => assert.deepEqual(await bed(), { logs, a });
    const select = name => page.locator('#defenseChoice').getByRole('button', { name }).click();
    const menu = async name => { await E('bedMenu()'); await select(name); };
    const truckAt = (x, z) => E("(()=>{ const t=trk(); Object.assign(t,{region:REG.cur,x:" + x + ",z:" + z +
      ",a:0}); TRUCK.sync=false; truckPos(); " + FACING_TRUCK + "; })()");
    const placeLog = (code, attrs, x = 'TRUCK.x', z = 'TRUCK.z-3.6') => E("(()=>{ const l=[" + x + "," + z +
      ",0," + JSON.stringify(code) + "]; if(" + attrs + "&1) l[5]=1; if(" + attrs + "&2) l[6]=1; regionLogs().push(l); regionLogsDirty(); })()");
    const clearGround = () => E('regionLogs().length=0; regionLogsDirty()');
    const drop = async () => {
      await menu('丸太を1本下ろす');
      return E('(()=>{ const l=regionLogs().at(-1); return [l[3],logAttr(l)]; })()');
    };
    const moveToLastLog = () => E("(()=>{ const l=regionLogs().at(-1); P.x=l[0]+0.85; P.z=l[1]; P.facing=-Math.PI/2; setCam(P.facing); })()");
    const usePrompt = async label => {
      await page.waitForFunction(re => window.__truckTest('curInter?.label')?.match(new RegExp(re)), label, { timeout: 15000 });
      await page.keyboard.press('e');
    };
    const splitLast = async () => {
      await moveToLastLog();
      const original = await E('window.__log=regionLogs().at(-1); [inv.hardwood||0,inv.wood||0]');
      await E("P.hp=P.maxHp; P.stamina=100; for(const e of enemies) if(dist(e.x,e.z,P.x,P.z)<100) e.x+=3000; cv.focus()");
      for (let i = 0; i < 15 && await E('regionLogs().includes(__log)'); i++) {
        await page.keyboard.press('j');
        await page.waitForFunction("window.__truckTest('!P.atk&&!P.stagger')", null, { timeout: 10000 });
      }
      assert.equal(await E('regionLogs().includes(__log)'), false, 'J で丸太を割る');
      const after = await E('[inv.hardwood||0,inv.wood||0]');
      return after.map((n, i) => n - original[i]);
    };

    if (PREVIEW) {
      await page.goto(ORIGIN + '/__truck_seed.html');
      await page.evaluate(keys => keys.forEach(key => localStorage.setItem(key, 'MAIN:' + key)), MAIN_KEYS);
    }
    await open(PAGE);
    assert.equal(await E('SAVE_KEY'), SAVE_KEY);
    await page.locator('#btnNew').click();
    for (let i = 0; i < 15 && !(await page.locator('#dialog').isHidden()); i++) await E('advanceDialog()');
    await E(BASE);
    const base = await getSave();

    // 1. Actual legacy payload read by Continue, then unloaded and resaved.
    const legacy = structuredClone(base);
    delete legacy.logAttr;
    delete legacy.f4.logA;
    delete legacy.f4.carryA;
    legacy.chapter2.progress.truck.bed.logs = ['m', 'k', 't'];
    await putSave(legacy);
    await resume();
    await checkBed(['m', 'k', 't'], [0, 0, 0]);
    await truckAt('PSPAWN.x+8', 'PSPAWN.z+8');
    assert.deepEqual(await drop(), ['t', 0]);
    assert.deepEqual((await getSave()).logAttr.bed, { a: [0, 0], s: 'mk' });
    console.log('ok 1 旧セーブの丸太・荷下ろし・再保存');

    // 2. Invalid inputs are paired before filtering and capacity truncation.
    const cases = [
      [['m', 'k', 't'], { a: [3], s: 'mkt' }, ['m', 'k', 't'], [0, 0, 0]],
      [['m', 'k', 't'], { a: [3, 2, 1], s: 'tmk' }, ['m', 'k', 't'], [0, 0, 0]],
      [['m', 'k'], { a: null, s: 'mk' }, ['m', 'k'], [0, 0]],
      [['m', { toString: 0 }, 'k'], { a: [3, 1, 2], s: 'mk' }, ['m', 'k'], [0, 0]],
      [['m', 'k', 't', 'm', 'k'], { a: ['3', -1, 4, null, 2], s: 'mktmk' }, ['m', 'k', 't', 'm', 'k'], [0, 0, 0, 0, 2]],
      [['m', 'x', 'k', 't', 'm', 'm', 'm', 'k'], { a: [3, 2, 1, 0, 2, 3, 1, 2], s: 'mxktmmmk' },
        ['m', 'k', 't', 'm', 'm', 'm'], [3, 1, 0, 2, 3, 1]],
    ];
    for (const [rawLogs, meta, logs, a] of cases) {
      const actual = await E('(()=>{ const t={bed:{logs:' + JSON.stringify(rawLogs) + '}}; trkSys(t,' +
        JSON.stringify(meta) + '); return [t.bed.logs,bedLogAttrs(t)]; })()');
      assert.deepEqual(actual, [logs, a]);
    }
    assert.deepEqual(await E("(()=>{ const f=f4Load({logs:[[1,2,0,'m'],[0,0,0,'x'],[3,4,0,'k']],logA:[3,1,2]," +
      "carry:'m',carryA:'3',cart:{x:0,z:0,logs:['k','x','t'],logA:[2,3,1]}}); " +
      "return [f.logs.map(logAttr),f.carryA,f.cart.logs,f.cart.logA]; })()"), [[3, 2], 0, ['k', 't'], [2, 1]]);
    console.log('ok 2 不正な印・署名・太さの正規化と添字');

    // 3. Logs from real trees, with positions arranged so the bed menu takes one at a time.
    await E("bedLogClear(trk()); regionLogs().length=0; regionLogsDirty()");
    assert.equal(await E("regionTravel('kamishihi',null,{force:true})"), true);
    await atRegion('kamishihi');
    assert.deepEqual(await E("(()=>{ const trees=[...REG.live.ktrees.values()]; " +
      "const broad=trees.find(t=>t.ty==='kona'&&t.s<1.3&&!t.felled&&kamiReach(t.x,t.z)); " +
      "const cedar=trees.find(t=>t.ty==='sugi'&&t.s<1.3&&!t.felled&&kamiReach(t.x,t.z)); " +
      "for(const tree of [broad,cedar]){ const rec=kamiTreeRec(tree); f4Fell(rec,0); f4Buck(F4.trunks.find(t=>t.rec===rec)); }" +
      "const logs=regionLogs(); logs.splice(4); window.__rows=logs.splice(0); " +
      "return __rows.map(l=>[l[3],logAttr(l)]); })()"), [['m', 3], ['m', 3], ['m', 2], ['m', 0]]);
    await truckAt('P.x+8', 'P.z+5');
    for (let i = 0; i < 4; i++) {
      await E("(()=>{ const l=__rows.shift(); l[0]=TRUCK.x; l[1]=TRUCK.z-3.6; regionLogs().push(l); regionLogsDirty(); })()");
      await menu(/近くの丸太を積む/);
    }
    await checkBed(['m', 'm', 'm', 'm'], [3, 3, 2, 0]);
    const mixed = await getSave();
    await resume(PAGE, 'kamishihi');
    await checkBed(['m', 'm', 'm', 'm'], [3, 3, 2, 0]);
    await truckAt('trk().x', 'trk().z');
    for (const a of [0, 2, 3, 3]) {
      assert.deepEqual(await drop(), ['m', a]);
      assert.deepEqual(await splitLast(), [a & 1, 2]);
    }
    await checkBed([], []);
    console.log('ok 3 上志比の広葉樹・杉の混載、再開、LIFO、J で硬木は2個だけ');

    // 4. Repeated load/unload and replacing an identically sized log.
    await placeLog('m', 3);
    await menu(/近くの丸太を積む/);
    for (let i = 0; i < 3; i++) {
      assert.deepEqual(await drop(), ['m', 3]);
      await menu(/近くの丸太を積む/);
      await checkBed(['m'], [3]);
    }
    assert.deepEqual(await drop(), ['m', 3]);
    await E('regionLogs().at(-1)[0]+=20; regionLogsDirty()');
    await placeLog('m', 0);
    await menu(/近くの丸太を積む/);
    await checkBed(['m'], [0]);
    console.log('ok 4 積み直しと同じ太さの杉への入れ替え');

    // 5. Move the loaded truck through the actual region transition.
    await putSave(mixed);
    await E('regionResetHome(); applySave(readSave())');
    await E("regionTravel('kamishihi',null,{force:true})");
    await E("TRUCK.drive=true");
    assert.equal(await E("regionTravel('komyoji',null,{force:true})"), true);
    await E('truckExit(true)');
    await checkBed(['m', 'm', 'm', 'm'], [3, 3, 2, 0]);
    assert.equal(await E('trk().region'), 'komyoji');
    await truckAt('PSPAWN.x+8', 'PSPAWN.z+8');
    for (const a of [0, 2, 3]) {
      assert.deepEqual(await drop(), ['m', a]);
      if (a!==3) await E('regionLogs().at(-1)[0]+=12; regionLogsDirty()');
    }
    await E('saveGame()');
    await resume();
    assert.equal(await E('logAttr(regionLogs().at(-1))'), 3);
    await moveToLastLog();
    assert.match(await E("(()=>{ const L=[]; f4Interactables(L); return L.find(v=>v.label.includes('担ぐ'))?.label; })()"),
      /広葉樹の丸太.*山地の硬木\+1/);
    assert.deepEqual(await splitLast(), [1, 2]);
    console.log('ok 5 トラックで地域移動、光明寺の地面で再開、案内と J の硬木報酬');

    // 6. Carry through E and load by the truck's menu, then use the cart menu.
    await clearGround();
    await truckAt('PSPAWN.x+19', 'PSPAWN.z+19');
    await placeLog('k', 3, 'PSPAWN.x+7', 'PSPAWN.z+7');
    await moveToLastLog();
    await usePrompt('太い広葉樹の丸太.+担ぐ');
    await E('saveGame()');
    await resume();
    assert.deepEqual(await E('[prog.f4.carry,prog.f4.carryA]'), ['k', 3]);
    await truckAt('PSPAWN.x+19', 'PSPAWN.z+19');
    await menu(/担いでいる丸太を積む/);
    await checkBed(['m', 'k'], [3, 3]);
    assert.deepEqual(await E('[prog.f4.carry,prog.f4.carryA]'), [0, 0]);

    await E("RECIPES.find(r=>r.id==='cart').give(); const c=prog.f4.cart; Object.assign(c,{x:PSPAWN.x+8,z:PSPAWN.z+8}); Object.assign(P,{x:c.x+1,z:c.z})");
    const cartPrompt = starts => E("(()=>{ const L=[]; f4Interactables(L); L.find(v=>v.label.startsWith(" +
      JSON.stringify(starts) + ")).act(); })()");
    await cartPrompt('一輪車を押す');
    await placeLog('k', 3, 'P.x+1', 'P.z');
    await cartPrompt('丸太を一輪車に積む');
    await E('saveGame()');
    await resume();
    assert.deepEqual(await E('[prog.f4.cart.logs,prog.f4.cart.logA]'), [['k'], [3]]);
    await E('Object.assign(P,{x:prog.f4.cart.x+1,z:prog.f4.cart.z})');
    await cartPrompt('一輪車を押す');
    await cartPrompt('一輪車を置く・丸太を下ろす');
    await select('一輪車の丸太を1本下ろす');
    assert.deepEqual(await E('[logAttr(regionLogs().at(-1)),prog.f4.cart.logs,prog.f4.cart.logA]'), [3, [], []]);
    console.log('ok 6 担ぐ・荷台・一輪車・各再開と荷下ろし');

    // 7. Delivery routes still pay only the original amount of wood.
    const inventory = '([inv.wood||0,inv.hardwood||0])';
    let before = await E(inventory);
    await truckAt('F4.yard.x-8', 'F4.yard.z');
    await menu(/荷台の丸太を丸太置き場に納める/);
    await checkBed([], []);
    assert.deepEqual(await E(inventory), [before[0]+7, before[1]]);
    await E("Object.assign(P,{x:F4.yard.x,z:F4.yard.z}); f4CarrySet(prog.f4,'k',3)");
    await cartPrompt('丸太を納める');
    assert.deepEqual(await E(inventory), [before[0]+11, before[1]]);
    await E("(()=>{const c=prog.f4.cart; c.push=true; cartLogPush(c,'m',3);})()");
    await cartPrompt('一輪車の丸太を納める');
    assert.deepEqual(await E(inventory), [before[0]+14, before[1]]);
    assert.deepEqual(await E('[prog.f4.cart.logs,prog.f4.cart.logA]'), [[], []]);

    before = await E(inventory);
    await E("(()=>{ const t=trk(); bedLogPush(t,'t',0); bedLogPush(t,'k',3); haulStart(); })()");
    for (const [remaining, code, a, paid] of [[1, 'k', 3, 4], [0, 't', 0, 6]]) {
      assert.deepEqual(await E("(()=>{ HAUL.t=.1; haulUpdate(.2); const t=trk(); return [t.bed.logs.length,bedLogAttrs(t).length,HAUL.load.log,HAUL.load.a]; })()"),
        [remaining, remaining, code, a]);
      await E('HAUL.t=.1; haulUpdate(.2)');
      assert.deepEqual(await E(inventory), [before[0]+paid, before[1]]);
    }
    await E("haulStop(true); closeOverlay(); for(let i=0;i<15&&!$('dialog').hidden;i++) advanceDialog()");
    console.log('ok 7 荷台・担ぎ・一輪車・源さんの納入量と印の同期');

    // 8. A seventh nearby log cannot be loaded.
    await E(FACING_TRUCK);
    await clearGround();
    for (let i = 0; i < 6; i++) {
      await placeLog('m', i%4);
      await menu(/近くの丸太を積む/);
    }
    await placeLog('k', 3);
    await E('bedMenu()');
    assert.equal(await page.locator('#defenseChoice').getByRole('button', { name: /近くの丸太を積む/ }).count(), 0);
    await select('戻る');
    await checkBed(Array(6).fill('m'), [0, 1, 2, 3, 0, 1]);
    assert.equal(await E('bedUnits(trk())'), 60);
    assert.equal(await E('regionLogs().length'), 1);
    console.log('ok 8 丸太6本・広さ60・7本目は積めない');

    // 9. Save in the new game and load the real old page on the same origin.
    await E("(()=>{ const t=trk(), f=prog.f4; bedLogClear(t); bedLogPush(t,'m',0); bedLogPush(t,'k',0); bedLogPush(t,'m',3);" +
      " f.logs=[logAttrSet([PSPAWN.x+45,PSPAWN.z+45,0,'m'],3)]; f4CarrySet(f,'t',2);" +
      " cartLogClear(f.cart); cartLogPush(f.cart,'k',3); saveGame(); })()");
    const compat = await getSave();
    assert.equal(compat.v, 1);
    assert.equal(await E('SAVE_KEY'), SAVE_KEY);
    assert.deepEqual(compat.logAttr, { v: 1, bed: { a: [0, 0, 3], s: 'mkm' } });
    assert.deepEqual(Object.keys(compat.chapter2.progress.truck.bed).sort(), ['foods', 'logs', 'mats']);
    assert.equal(compat.f4.logs[0].length, 4);
    assert.deepEqual([compat.f4.logA, compat.f4.carryA, compat.f4.cart.logA], [[3], 2, [3]]);
    console.log('ok 9a SAVE_KEY・v:1・最上位 logAttr、truck.bed と f4 の既存値の形');

    await resume(OLD_URL);
    assert.deepEqual(await E('trk().bed.logs'), ['m', 'k', 'm']);
    assert.deepEqual(await E("[prog.f4.logs[0][3],prog.f4.carry,prog.f4.cart.logs[0]]"), ['m', 't', 'k']);
    await truckAt('PSPAWN.x+14', 'PSPAWN.z+14');
    await menu('丸太を1本下ろす');
    await E('regionLogs().at(-1)[0]+=20; regionLogsDirty()');
    await placeLog('m', 0);
    await menu(/近くの丸太を積む/);
    const rewritten = await getSave();
    assert.deepEqual(rewritten.chapter2.progress.truck.bed.logs, ['m', 'k', 'm']);
    assert.equal(Object.hasOwn(rewritten, 'logAttr'), false);
    await resume();
    await checkBed(['m', 'k', 'm'], [0, 0, 0]);
    console.log('ok 9b 旧版で同じ太さの丸太を入れ替えて保存、誤った印は付かない');

    await putSave(compat);
    const beforeRead = await raw();
    await open(OLD_URL);
    // Use the old game's real reader without entering play, which can auto-save.
    assert.deepEqual(await E("applySave(readSave()); trk().bed.logs"), ['m', 'k', 'm']);
    await open(PAGE);
    assert.equal(await raw(), beforeRead);
    await page.locator('#btnContinue').click();
    await atRegion('komyoji');
    await checkBed(['m', 'k', 'm'], [0, 0, 3]);
    console.log('ok 9c 旧版で読むだけなら印は残る');

    await putSave(compat);
    await resume(OLD_URL);
    await E('saveGame()');
    const touchedNothing = await getSave();
    assert.equal(Object.hasOwn(touchedNothing, 'logAttr'), false);
    assert.equal(Object.hasOwn(touchedNothing.f4, 'logA'), false);
    assert.equal(Object.hasOwn(touchedNothing.f4, 'carryA'), false);
    assert.equal(Object.hasOwn(touchedNothing.f4.cart, 'logA'), false);
    assert.deepEqual(touchedNothing.f4.logs, compat.f4.logs);
    assert.equal(touchedNothing.f4.carry, compat.f4.carry);
    assert.deepEqual(touchedNothing.f4.cart.logs, compat.f4.cart.logs);
    await resume();
    await checkBed(['m', 'k', 'm'], [0, 0, 0]);
    assert.deepEqual(await E('[prog.f4.logs.map(logAttr),prog.f4.carryA,prog.f4.cart.logA]'), [[0], 0, [0]]);
    console.log('ok 9d 旧版で丸太に触れず再保存しても印だけ消える');

    if (PREVIEW) {
      await page.goto(ORIGIN + '/__truck_seed.html');
      assert.deepEqual(await page.evaluate(keys => keys.map(key => localStorage.getItem(key)), MAIN_KEYS),
        MAIN_KEYS.map(key => 'MAIN:' + key));
      console.log('ok 試遊版 本編の保存・設定キー7つを保持');
    }
    assert.deepEqual(errors, []);
    console.log('PASS: KEI truck の丸太（種類・輸送・セーブ・旧版互換）');
  } finally { await browser.close(); }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
