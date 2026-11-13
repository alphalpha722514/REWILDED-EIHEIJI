const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
for (const [,attrs,code] of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
  if (!/\bsrc\s*=|type=["']application\/json/.test(attrs)) new vm.Script(code);
}
const foundation = html.slice(html.indexOf('function chapter2State('), html.indexOf('function freshState(){'));
const save = html.slice(html.indexOf('function saveGame(){'), html.indexOf('function saveTrap('));
const ctx = vm.createContext({});
vm.runInContext(foundation, ctx);
function state(saved, cleared) { return JSON.parse(JSON.stringify(ctx.chapter2State(saved, cleared))); }
for (const malformed of [undefined, null, false, [], 'old', 42]) {
  assert.equal(state(malformed, false).unlocked, false);
  assert.equal(state(malformed, true).regions.kamishihi.unlocked, true);
}
assert.equal(state({unlocked:true}, false).unlocked, false);
assert.equal(state({currentChapter:2,currentRegion:'kamishihi'}, true).currentRegion, 'komyoji');
assert.deepEqual(state({progress:{quest:'saved'}}, true).progress, {quest:'saved'});
// v0.60: a saved region is restored only when that region exists (playable) and chapter 2 is unlocked
vm.runInContext("var REG={defs:{kamishihi:{name:'上志比'}}};", ctx);
assert.equal(state({currentRegion:'kamishihi'}, true).currentRegion, 'kamishihi', 'playable region restored');
assert.equal(state({currentRegion:'kamishihi'}, false).currentRegion, 'komyoji', 'locked: back to Komyoji');
assert.equal(state({currentRegion:'nowhere'}, true).currentRegion, 'komyoji', 'unknown region: Komyoji');
assert.equal(state({currentRegion:42}, true).currentRegion, 'komyoji');
vm.runInContext('REG.defs={};', ctx);
vm.runInContext(`
const SAVE_KEY='eiheiji_vs_beasts_v010'; let storageOK=true;
let stored;
const localStorage={setItem:(key,value)=>{stored={key,value};}};
let prog={bossDefeated:false,arms:{nata1:120},stage:'talk'};
const P={weapon:'nata1',dur:83,full:75};
const inv={wood:9},stats={kills:3},GAPS=[],traps=[],NODES=[];
const checkpointStage=()=>prog.stage; const saveTrap=x=>x;
const f31SaveProg=()=>({level:2});
const f5Save=()=>({}),f4Save=f5Save,f7Save=f5Save,f8Save=f5Save,f9Save=f5Save,f10Save=f5Save,facSave=id=>({v:1,built:0,id}),kamaSave=()=>({v:1,built:0,q:[],t:0,out:{}}); // v0.63：変換炉・v0.64：かまど（v0.66 で形を変えた）
${save}
saveGame();
`,ctx);
let saved=JSON.parse(vm.runInContext('stored.value',ctx));
assert.equal(vm.runInContext('stored.key',ctx),'eiheiji_vs_beasts_v010');
assert.equal(saved.v,1);
assert.equal(saved.inv.wood,9);
assert.deepEqual(saved.conv,{v:1,built:0,id:'conv'}); assert.deepEqual(saved.kama,{v:1,built:0,q:[],t:0,out:{}}); // v0.63：変換炉 conv・v0.64：かまど kama は新しいキー
assert.equal(saved.arms.nata1,83);
assert.equal(saved.chapter2.unlocked,false);
vm.runInContext("prog.bossDefeated=true;prog.stage='cleared';saveGame();",ctx);
saved=JSON.parse(vm.runInContext('stored.value',ctx));
assert.equal(saved.chapter2.unlocked,true);
assert.equal(saved.prog.stage,'cleared');
assert.deepEqual(state(saved.chapter2,saved.prog.bossDefeated),saved.chapter2);
assert.match(html,/prog\.chapter2=chapter2State\(d\.chapter2,prog\.bossDefeated\)/);
assert.match(html,/prog\.chapter2=chapter2State\(null,false\)/);
console.log('PASS: inline script syntax; legacy/malformed defaults; boss unlock; save round trip; existing key, version, inventory and durability');
