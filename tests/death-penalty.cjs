// v0.56: 倒れた代償（2026-11-12 承認：A 野の獣の体力も戻る／B 体力半分・満腹-25・柵の無料修理なし／C 手に持っていた武器の耐久-25%）
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
const start = html.indexOf('function retryFromBase(){');
assert.ok(start >= 0, 'retryFromBase exists');
const end = html.indexOf('\n}', start) + 2;

const ctx = vm.createContext({ Math, console });
vm.runInContext(`
let saves=0, toasts=[];
const P={x:0,z:0,maxHp:120,hp:0,full:50,dead:true,weapon:'nata2',dur:80,atk:1,dodge:1,stagger:1,buffer:1,facing:1};
const WEAPONS={nata2:{maxDur:100}};
const prog={stage:'cleared',arms:{nata2:80}};
const ev={kind:'chapter2',phase:'fight',queue:[1],ended:true};
const GAPS=[{fence:{type:'wood',hp:0,max:100,broken:true},col:{active:false}},{fence:{type:'stake',hp:30,max:200,broken:false},col:{active:true}}];
const enemies=[{mode:'field',state:'chase',hp:12,maxHp:90,x:5,z:5,home:{x:50,z:50}},{mode:'field',state:'dead',hp:0,maxHp:90,x:1,z:1,home:{x:9,z:9}}];
const PSPAWN={x:100,z:100}, S={mode:'dead'}, heavyRing={visible:true};
let bossActive=false;
const f9Reset=()=>{}, clearRaidEnemies=()=>{}, setNight=()=>{}, setDusk=()=>{}, fenceVisual=()=>{}, setupBoss=()=>{}, setBarrier=()=>{},
  setCam=()=>{}, resetCombat=()=>{}, setState=(e,s)=>{e.state=s}, hideAllOv=()=>{}, toast=t=>toasts.push(t), saveGame=()=>{saves++};
const $=()=>({hidden:false});
${html.slice(start, end)}
`, ctx);
const run = s => vm.runInContext(s, ctx);
run('retryFromBase()');
assert.equal(run('P.hp'), 60, 'B: HP is half');
assert.equal(run('P.full'), 25, 'B: fullness -25');
run('P.full=20; retryFromBase()');
assert.equal(run('P.full'), 15, 'B: fullness floor 15');
run('P.full=25; P.dur=80; prog.arms.nata2=80; P.hp=1');
run('retryFromBase()');
assert.equal(run('P.dur'), 55, 'C: weapon durability -25% of max');
assert.equal(run('prog.arms.nata2'), 55, 'C: stored durability follows');
run('P.dur=10; retryFromBase()');
assert.equal(run('P.dur'), 0, 'C: durability does not go below 0');
assert.equal(run('GAPS[0].fence.broken'), true, 'B: broken fence is not repaired for free');
assert.equal(run('GAPS[1].fence.hp'), 30, 'B: worn fence is not repaired for free');
assert.equal(run('enemies[0].hp'), 90, 'A: field beast HP restored');
assert.equal(run('enemies[0].x'), 50, 'field beast returns home');
assert.equal(run('enemies[1].hp'), 0, 'dead beast untouched');
assert.equal(run('ev.kind'), null, 'event reset to preparation');
assert.ok(run('saves') > 0, 'saved');
run("P.weapon=null; P.dur=0; retryFromBase()");
assert.equal(run('P.dur'), 0, 'unarmed: nothing to wear');
assert.match(html, /体力は半分、満腹は少し減り、手に持っていた武器が傷みます/, 'death screen explains the cost');
console.log('PASS: death penalty (half HP, fullness -25 floor 15, weapon -25%, no free fence repair, field beasts heal), event reset, save');
