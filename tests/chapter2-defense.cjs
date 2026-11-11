const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
function extract(name){const start=html.indexOf('function '+name+'(');assert(start>=0);const end=html.indexOf('\nfunction ',start+1);return html.slice(start,end);}
const foundation=html.slice(html.indexOf('function chapter2State('),html.indexOf('function freshState(){'));
const ctx=vm.createContext({console});
vm.runInContext(`
let prog={bossDefeated:false,chapter2:null,stage:'cleared'},P={x:0,z:0,dead:false},S={},bossActive=false;
const npcGen={x:0,z:0},CORE={x:10,z:10},ev={kind:null,ids:new Set()},enemies=[],keys={clear(){}},cv={focus(){}};
let saves=0,damaged=0,sector=0,dialogs=0;
const inv={wood:0,straw:0},food={onigiri:0},foodAdd=(k,n)=>{food[k]=(food[k]||0)+n},queueDialog=()=>{dialogs++},say=()=>{},npcTome={},npcEshin={},npcYone={};
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
assert.equal(run('ev.kind'),'chapter2');assert.equal(run('ev.waves.flat().length'),30);
assert.deepEqual(JSON.parse(run('JSON.stringify(ev.waves.map(w=>w.length))')),[8,10,12]);
assert.equal(run("ev.waves.every(w=>['boar','bear','monkey'].every(t=>w.some(e=>e[0]===t)))"),true);
assert.equal(run("ev.waves.every(w=>[0,1,2].every(g=>w.some(e=>e[1]===g)))"),true);
assert.equal(run('startChapter2Defense()'),false,'no duplicate');
run('updateEvent(30)');assert.equal(run('ev.phase'),'fight');
run('updateEvent(20);alive=1;updateEvent(60)');assert.equal(run('ev.waveIdx'),0,'no next wave while monkeys remain');
run('alive=0;updateEvent(18)');assert.equal(run('ev.waveIdx'),1);
for(let i=0;i<12&&run('ev.kind');i++)run('alive=0;updateEvent(18)');
assert.equal(run('ev.kind'),null);assert.equal(run('chapter2Opening().defenseComplete'),true);
assert.equal(run('prog.stage'),'cleared','chapter 1 completion intact');
// v0.55: first-clear reward once, with the short villager dialogue
assert.deepEqual(JSON.parse(run('JSON.stringify([inv.wood,inv.straw,food.onigiri,dialogs])')),[6,6,2,1],'first clear reward');
assert.equal(run('chapter2Opening().defenseRewarded'),true);
assert.equal(run('syncChapter2().currentChapter'),2);
assert.equal(run('startChapter2Defense()'),true,'completed save can replay');
assert.equal(run('chapter2Opening().defenseComplete'),true,'replay keeps completion');
run('updateEvent(30)');for(let i=0;i<12&&run('ev.kind');i++)run('alive=0;updateEvent(18)');
assert.equal(run('ev.kind'),null,'replay can be won');
assert.deepEqual(JSON.parse(run('JSON.stringify([inv.wood,inv.straw,food.onigiri,dialogs])')),[6,6,2,1],'no reward on replay');
// a save that cleared before rewards existed gets the reward once
run('delete prog.chapter2.progress.defenseRewarded;ev.kind=null;ev.phase=null;ev.queue=[]');assert.equal(run('startChapter2Defense()'),true);
run('updateEvent(30)');for(let i=0;i<12&&run('ev.kind');i++)run('alive=0;updateEvent(18)');
assert.deepEqual(JSON.parse(run('JSON.stringify([inv.wood,inv.straw,food.onigiri])')),[12,12,4],'legacy clear rewarded once');
run('prog.chapter2.progress.defenseComplete=false;ev.kind=null');assert.equal(run('startChapter2Defense()'),true);
run('ev.kind=null;ev.phase=null;ev.queue=[]');assert.equal(run('startChapter2Defense()'),true,'retry from prepared state');
assert.match(html,/if\(kind==='chapter2'\)[\s\S]*?saveGame\(\);return;/);
console.log('PASS: unlock, proximity, duplicate start, 30 mixed attackers / 3 waves, rest, completion, chapter persistence, retry');
vm.runInContext(`
${extract('targetOf')}
${extract('tDist')}
${extract('updateMonkey')}
const STORE={x:20,z:20},ET={monkey:{speed:6}},faceTo=()=>{},showSector=()=>{sector++},hideSector=()=>{},steer=()=>{},floatText=()=>{};
const damageCore=d=>{ev.coreHp-=d;damaged+=d};
CORE.r=2;P.r=.5;P.x=100;P.z=100;
const attacker={x:13,z:10,r:1,mode:'raid',type:'monkey',gap:0,rphase:'core',state:'raid',home:{x:0,z:0},aggro:false};
`,ctx);
assert.equal(run('targetOf(attacker).kind'),'core');
run('updateMonkey(attacker,1)');assert.equal(run('damaged'),0,'windup before damage');
run('updateMonkey(attacker,1)');assert.equal(run('damaged'),14,'attacks core');
run("ev.kind='invasion'");assert.equal(run('targetOf(attacker).kind'),'store','chapter 1 monkey behavior unchanged');
// v0.55: monkeys stop to climb an intact fence in chapter 2 only
run("ev.kind='chapter2';Object.assign(GAPS[0],{out:{x:50,z:50},in:{x:60,z:60},fence:{type:'wood',broken:false}})");
vm.runInContext("var climber={x:50,z:50.5,r:1,mode:'raid',type:'monkey',gap:0,rphase:'approach',state:'raid',home:{x:0,z:0},aggro:false};",ctx);
run('targetOf(climber)');assert.equal(run('climber.climbT'),4,'climb starts at intact fence');
run('updateMonkey(climber,1)');assert.equal(run('climber.climbT'),3);assert.equal(run('climber.x'),50,'stays while climbing');
run("GAPS[0].fence.broken=true;climber.rphase='approach';climber.climbT=0;targetOf(climber)");assert.equal(run('climber.climbT'),0,'broken fence: no climb');
run("ev.kind='invasion';GAPS[0].fence.broken=false;climber.rphase='approach';targetOf(climber)");assert.equal(run('climber.climbT'),0,'chapter 1: no climb');
console.log('PASS: chapter 2 core target/windup/damage; chapter 1 store target; chapter 2 fence climb');

vm.runInContext(`${extract('f11InvHp')}${extract('f11InvDmg')}`,ctx);
run("ev.kind='chapter2'");
assert.equal(run('f11InvHp(29)'),58);
assert.equal(run("f11InvDmg(38,{mode:'raid'})"),53);
assert.equal(run("f11InvDmg(38,{mode:'field'})"),38,'field enemies unchanged');
run("F11B.hpMul=1.6;F11B.dmgMul=1.1;ev.kind='invasion'");
assert.equal(run('f11InvHp(29)'),46);
assert.equal(run("f11InvDmg(38,{mode:'raid'})"),42);
run("ev.kind='raid'");assert.equal(run('f11InvHp(29)'),29);
assert.equal(run("f11InvDmg(38,{mode:'raid'})"),38);
// Preparation acts through real target selection and trap effects, not an inventory gate.
run("ev.kind='chapter2';GAPS[0].fence={type:'stake',broken:false};GAPS[0].c={x:0,z:0};");
assert.equal(run("targetOf({type:'bear',mode:'raid',gap:0,rphase:'gate',x:0,z:0}).kind"),'fence');
vm.runInContext(`
${extract('triggerTrap')}
const setTrap=(t,s)=>{t.state=s},f10Noise=()=>{},damageEnemy=(e,d)=>{e.hp-=d};
const trap={type:'pit',state:'armed',x:0,z:0},bear={type:'bear',hp:358,state:'chase',ind:{}};
`,ctx);
run('triggerTrap(trap,bear)');
assert.equal(run('bear.hp'),330);assert.equal(run('bear.stunT'),5);
assert.equal(run('trap.state'),'sprung');
console.log('PASS: chapter-only HP/damage, unchanged chapter 1/field enemies, stake blocks bear, pit damages/stuns bear');
