const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
function extract(name){const start=html.indexOf('function '+name+'(');assert(start>=0);const end=html.indexOf('\nfunction ',start+1);return html.slice(start,end);}
const foundation=html.slice(html.indexOf('function chapter2State('),html.indexOf('function freshState(){'));
const ctx=vm.createContext({console});
vm.runInContext(`
let prog={bossDefeated:false,chapter2:null,stage:'cleared'},P={x:0,z:0,dead:false},S={},bossActive=false;
const npcGen={x:0,z:0},CORE={x:10,z:10},ev={kind:null,ids:new Set()},enemies=[],keys={clear(){}},cv={focus(){}};
let saves=0,damaged=0,sector=0;
const hideAllOv=()=>{},saveGame=()=>{saves++},banner=()=>{},sfx=()=>{},setState=(e,s)=>{e.state=s},inBase=()=>false;
const dist=(x,z,a,b)=>Math.hypot(x-a,z-b);
${foundation}
${extract('startEvent')}
${extract('queueWave')}
${extract('updateEvent')}
${extract('winEvent')}
${extract('f11Rest')}
let alive=0;
const raidAlive=()=>alive,toast=()=>{},bellObj=null,F11B={rest:10};
const GAPS=[{name:'南門',spawn:[{x:0,z:0}]},{name:'東口',spawn:[{x:1,z:0}]},{name:'沢口',spawn:[{x:2,z:0}]}];
let nextId=0;
const rr=()=>0,spawnEnemy=(type,x,z,mode)=>{alive++;return {id:++nextId,type,x,z,mode}};
`,ctx);
function run(s){return vm.runInContext(s,ctx)}
assert.equal(run('startChapter2Defense()'),false,'locked before boss');
run('prog.bossDefeated=true;P.x=100');
assert.equal(run('startChapter2Defense()'),false,'requires presence at lookout');
run('P.x=0');assert.equal(run('startChapter2Defense()'),true);
assert.equal(run('ev.kind'),'chapter2');assert.equal(run('ev.waves.flat().length'),18);
assert.equal(run("ev.waves.flat().every(w=>w[0]==='monkey')"),true);
assert.equal(run('startChapter2Defense()'),false,'no duplicate');
run('updateEvent(20)');assert.equal(run('ev.phase'),'fight');
run('updateEvent(20);alive=1;updateEvent(60)');assert.equal(run('ev.waveIdx'),0,'no next wave while monkeys remain');
run('alive=0;updateEvent(6)');assert.equal(run('ev.waveIdx'),1);
run('updateEvent(20);alive=0;updateEvent(6);updateEvent(20);alive=0;updateEvent(6)');
assert.equal(run('ev.kind'),null);assert.equal(run('chapter2Opening().defenseComplete'),true);
assert.equal(run('prog.stage'),'cleared','chapter 1 completion intact');
assert.equal(run('syncChapter2().currentChapter'),2);
assert.equal(run('startChapter2Defense()'),false,'completed cannot replay');
run('prog.chapter2.progress.defenseComplete=false;ev.kind=null');assert.equal(run('startChapter2Defense()'),true);
run('ev.kind=null;ev.phase=null;ev.queue=[]');assert.equal(run('startChapter2Defense()'),true,'retry from prepared state');
assert.match(html,/if\(kind==='chapter2'\)[\s\S]*?saveGame\(\);return;/);
console.log('PASS: unlock, proximity, duplicate start, 18 monkeys / 3 waves, rest, completion, chapter persistence, retry');
vm.runInContext(`
${extract('targetOf')}
${extract('tDist')}
${extract('updateMonkey')}
const STORE={x:20,z:20},ET={monkey:{speed:6}},faceTo=()=>{},showSector=()=>{sector++},hideSector=()=>{},steer=()=>{};
const damageCore=d=>{ev.coreHp-=d;damaged+=d};
CORE.r=2;P.r=.5;P.x=100;P.z=100;
const attacker={x:13,z:10,r:1,mode:'raid',type:'monkey',gap:0,rphase:'core',state:'raid',home:{x:0,z:0},aggro:false};
`,ctx);
assert.equal(run('targetOf(attacker).kind'),'core');
run('updateMonkey(attacker,1)');assert.equal(run('damaged'),0,'windup before damage');
run('updateMonkey(attacker,1.4)');assert.equal(run('damaged'),8,'attacks core');
run("ev.kind='invasion'");assert.equal(run('targetOf(attacker).kind'),'store','chapter 1 monkey behavior unchanged');
console.log('PASS: chapter 2 core target/windup/damage; chapter 1 store target');
