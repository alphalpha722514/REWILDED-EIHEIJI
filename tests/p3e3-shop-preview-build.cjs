// 検収版の生成、保存の分離、開始と操作をブラウザーなしで確認する。
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'e3-shop-preview-test-'));

function testStorage(guard, html) {
  const data = new Map();
  class Storage {
    getItem(key) { return data.get(key) ?? null; }
    setItem(key, value) { data.set(key, String(value)); }
    removeItem(key) { data.delete(key); }
    clear() { data.clear(); }
  }
  const storage = new Storage();
  const settings = ['weatherEffects', 'shadow', 'perf', 'aimMode', 'detail', 'camPitch'];
  const protectedKeys = [
    'eiheiji_vs_beasts_v010', 'REWILDED_EIHEIJI_SETTINGS', '__t', ...settings.map(key => `eiheiji_${key}`),
    'eiheiji_vs_beasts_p3e3farm', 'REWILDED_EIHEIJI_SETTINGS_p3e3farm', ...settings.map(key => `eiheiji_p3e3f_${key}`),
  ];
  for (const [i, key] of protectedKeys.entries()) storage.setItem(key, `original-${i}`);
  const original = new Map(data);
  const context = vm.createContext({Storage, localStorage: storage});
  vm.runInContext(guard, context);
  for (const key of protectedKeys) {
    assert.equal(storage.getItem(key), null);
    storage.setItem(key, 'changed');
    storage.removeItem(key);
  }
  storage.clear();
  assert.deepEqual(data, original);

  const [saveKey] = html.match(/const SAVE_KEY='eiheiji_p3e3shop_save';/) ?? [];
  const [, readSave] = html.match(/(function readSave\(\)\{[\s\S]*?\n\})/) ?? [];
  assert(saveKey && readSave);
  vm.runInContext(saveKey + readSave, context);
  const previewSave = 'eiheiji_p3e3shop_save';
  assert.equal(vm.runInContext('readSave()', context), null);
  storage.setItem(previewSave, '{"v":1,"inv":{},"p3":{"e3":{"map":1}}}');
  assert.equal(vm.runInContext('readSave().p3.e3.map', context), 1);
  storage.removeItem(previewSave);
  assert.equal(vm.runInContext('readSave()', context), null);
  for (const key of ['sound', ...settings, 'probe']) {
    const name = `eiheiji_p3e3shop_${key}`;
    storage.setItem(name, name);
    assert.equal(storage.getItem(name), name);
    storage.removeItem(name);
  }
  assert.deepEqual(data, original);
}

async function testRuntime(html) {
  const start = html.indexOf('const SHOP_PREVIEW =');
  const end = html.indexOf('// タイトル\nconst hasSave', start);
  assert(start >= 0 && end > start);
  const mapSource = fs.readFileSync(path.join(root, 'data/kamishihi/kamishihi-map.js'), 'utf8');
  const map = JSON.parse(mapSource.slice(mapSource.indexOf('=') + 1).trim().replace(/;$/, ''));
  const reach = Buffer.from(map.reach, 'base64');
  const context = vm.createContext({assert, map, reach});
  const atDoor = html.slice(html.indexOf('function p3eShopAtDoor('), html.indexOf('function p3eShopFloorAt('));
  const phase = html.slice(html.indexOf('function f10Phase('), html.indexOf('function f10Story('));
  vm.runInContext(`
    const P = {r:0.5}, SZ = {}, REG = {}, TRUCK = {}, P3A = {doors:[], on:true}, S = {mode:'title'};
    const elements = {}, cv={focus(){}}, $=id=>elements[id]??(elements[id]={});
    const P3B={hour:50}, F10C={dusk:780,night:900,dawn:1140};
    const noop=()=>{}, audioInit=noop, regionResetHome=noop, resetWorld=noop, hideAllOv=noop;
    const dist=(x,z,a,b)=>Math.hypot(x-a,z-b);
    const toast=noop, resetWeather=noop, setCam=noop;
    const prog={}, store={}, truck={};
    const freshState=()=>{ prog.f10={tod:0}; prog.p3={hq:{},e3:{s:Array(8).fill(0)}}; };
    const p3bState=()=>prog.p3, chapter2State=()=>({progress:{}}), trk=()=>truck;
    const szJoin=()=>Object.assign(SZ,{joined:true,order:'follow'});
    const szHere=()=>SZ.joined&&!SZ.away, szOrder=order=>{SZ.order=order;};
    let lighting, holds=0, releases=0, followed=false;
    const stfHoldBeasts=()=>{holds++;}, stfRelease=()=>{releases++;};
    const p3aSzFollow=()=>{followed=true;}, f10LightNow=()=>{lighting=f10Phase();};
    const saveGame=()=>{store.save=JSON.parse(JSON.stringify({prog, SZ}));};
    function szWalkable(x,z) {
      const grid=map.grid, i=Math.round((x-grid.x0)/grid.step), j=Math.round((z-grid.z0)/grid.step);
      if(i<0||i>=grid.nx||j<0||j>=grid.ny) return false;
      const n=j*grid.nx+i;
      return Boolean(reach[n>>3]&(1<<(n&7)));
    }
    function f4Free(x,z,r) {
      return !map.bld.some(([bx,bz,l,w,angle],i)=>{
        const dx=x-bx,dz=z-bz, c=Math.cos(angle),s=Math.sin(angle);
        const length=i===110?Math.max(5,l)+0.3:l, width=i===110?Math.max(4,w)+0.3:w;
        return Math.abs(dx*c+dz*s)<length/2+r&&Math.abs(-dx*s+dz*c)<width/2+r;
      });
    }
    const [bx,bz,,bw,angle]=map.bld[110], outward=Math.max(4,bw)/2+1.2;
    const door={id:'house110',inId:'shop',facing:-angle,x:bx-outward*Math.sin(angle),z:bz+outward*Math.cos(angle)};
    async function regionTravel(region) { REG.cur=region; P3A.doors=[door]; return true; }
  ` + atDoor + phase + html.slice(start, end), context);
  await vm.runInContext(`(async()=>{
    await shopPreviewStart();
    assert(p3eShopAtDoor(door)&&szWalkable(P.x,P.z)&&f4Free(P.x,P.z,P.r+0.1));
    assert(P.x===P._px&&P.z===P._pz&&dist(P.x,P.z,door.x,door.z)<2.6);
    assert(store.save.prog.p3.hq.plan===1&&store.save.prog.p3.e3.map===1&&store.save.prog.p3.e3.s[7]===1);
    assert(followed&&holds===1&&SZ.order==='follow'&&lighting==='day');
    S.mode='paused';
    $('shopPreviewSuzuki').onclick(); assert(SZ.order==='wait'&&store.save.SZ.order==='wait');
    SZ.away=true; shopPreviewRefresh(); assert($('shopPreviewSuzuki').disabled);
    $('shopPreviewSuzuki').onclick(); assert(SZ.order==='wait');
    SZ.away=false; $('shopPreviewSuzuki').onclick(); assert(SZ.order==='follow');
    for(const expected of ['dusk','night','day']) {
      $('shopPreviewTime').onclick(); assert(lighting===expected&&store.save.prog.f10.tod===prog.f10.tod);
    }
    P.x+=100; shopPreviewShelter(); assert(releases===1);
  })()`, context);
}

async function main() {
  const builder = path.join(root, 'tools/build-p3e3-shop-preview.py');
  const outputs = ['first.html', 'second.html'].map(name => path.join(temp, name));
  for (const out of outputs) execFileSync('python3', [builder, '--out', out], {stdio: 'inherit'});
  const bytes = fs.readFileSync(outputs[0]);
  assert(bytes.equals(fs.readFileSync(outputs[1])), '生成結果が同一');
  const html = bytes.toString('utf8');
  const scripts = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
    .filter(([, attrs]) => !/\b(?:src|type)\s*=/.test(attrs));
  for (const [, , source] of scripts) new vm.Script(source);
  assert(scripts[0][2].includes('Storage.prototype'));
  assert(html.includes("$('btnNew').onclick=shopPreviewStart;") && html.includes('continueGame(); };'));
  for (const id of ['btnDetail', 'btnPerf', 'btnSave', 'btnContinue']) assert(html.includes(`id="${id}"`));
  for (const file of ['data/kamishihi/kamishihi-map.js', 'data/models/mutant-monkey.js', 'vendor/three-r128/GLTFLoader.js']) {
    assert(fs.existsSync(path.join(root, file)) && html.includes(file), file);
  }
  testStorage(scripts[0][2], html);
  await testRuntime(html);
  console.log('PASS: 再生成バイト一致・JavaScript構文・保存分離・地図データ上の入口・スズキ・時刻切替');
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
}).finally(() => fs.rmSync(temp, {recursive: true, force: true}));
