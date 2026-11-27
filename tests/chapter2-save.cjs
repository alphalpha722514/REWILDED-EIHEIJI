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
const checkpointStage=()=>prog.stage; const saveTrap=x=>x; const stfNoSave=()=>false, stfNormalize=()=>{}; // v0.77：作業F（tests/story-f-browser.py で確かめる）
const f31SaveProg=()=>({level:2});
const f5Save=()=>({}),f4Save=f5Save,f7Save=f5Save,f8Save=f5Save,f9Save=f5Save,f10Save=f5Save,facSave=id=>({v:1,built:0,id}),kamaSave=()=>({v:1,built:0,q:[],t:0,out:{}}),kamiSave=()=>({v:1,n:{},r:{},sc:[],f:[],sp:{},g:{},st:{},fm:{}}),szSave=()=>({v:1,joined:false}),p3Save=()=>({v:1,hq:{sv:[0,0,0]}}),stashSave=()=>({v:1,komyoji:{},kami:{}}),p3cSave=()=>({v:1,sumie:{done:0}}),paddySave=()=>({v:1,st:2,t:300,care:0}); // v0.79：田んぼ paddy。v0.63：変換炉・v0.64：かまど（v0.66 で形を変えた）・v0.67：上志比・v0.73：スズキ
${save}
saveGame();
`,ctx);
let saved=JSON.parse(vm.runInContext('stored.value',ctx));
assert.equal(vm.runInContext('stored.key',ctx),'eiheiji_vs_beasts_v010');
assert.equal(saved.v,1);
assert.equal(saved.inv.wood,9);
assert.deepEqual(saved.conv,{v:1,built:0,id:'conv'}); assert.deepEqual(saved.kama,{v:1,built:0,q:[],t:0,out:{}}); // v0.63：変換炉 conv・v0.64：かまど kama は新しいキー
assert.deepEqual(saved.kami,{v:1,n:{},r:{},sc:[],f:[],sp:{},g:{},st:{},fm:{}}); // v0.67：上志比の採集・伐採・獣は新しいキー kami
assert.deepEqual(saved.paddy,{v:1,st:2,t:300,care:0}); // v0.79：拠点の田んぼは新しいキー paddy
assert.deepEqual(saved.suzuki,{v:1,joined:false}); // v0.73：スズキは新しいキー suzuki
assert.deepEqual(saved.p3,{v:1,hq:{sv:[0,0,0]}}); assert.deepEqual(saved.stash,{v:1,komyoji:{},kami:{}}); // v0.81：拠点本部 p3・資材置き場 stash は新しいキー
assert.deepEqual(saved.p3c,{v:1,sumie:{done:0}}); // v0.82：住民 p3c は新しいキー
assert.equal(saved.arms.nata1,83);
assert.equal(saved.chapter2.unlocked,false);
vm.runInContext("prog.bossDefeated=true;prog.stage='cleared';saveGame();",ctx);
saved=JSON.parse(vm.runInContext('stored.value',ctx));
assert.equal(saved.chapter2.unlocked,true);
assert.equal(saved.prog.stage,'cleared');
assert.deepEqual(state(saved.chapter2,saved.prog.bossDefeated),saved.chapter2);
// 同じ進行を屋外と店の両階で保存し、読み込み補正を通さず全項目を比較する。
vm.runInContext("REG.defs={kamishihi:{}};prog.chapter2.currentRegion='kamishihi';prog.chapter2.progress.openingStarted=true;const P3A={inside:false,inId:'shop'};saveGame()",ctx);
const outdoor=JSON.parse(vm.runInContext('stored.value',ctx));
assert.equal(outdoor.chapter2.currentChapter,2);
assert.equal(outdoor.chapter2.currentRegion,'kamishihi');
for(const level of [1,2]){
  vm.runInContext(`P3A.inside=true;P3A.interior={level:${level}};stored=null;saveGame()`,ctx);
  assert.equal(vm.runInContext('storageOK',ctx),true);
  const indoor=JSON.parse(vm.runInContext('stored.value',ctx));
  assert.equal(typeof indoor.chapter2.currentChapter,'number');
  assert.deepEqual(indoor,outdoor);
}
assert.match(html,/prog\.chapter2=chapter2State\(d\.chapter2,prog\.bossDefeated\)/);
assert.match(html,/prog\.chapter2=chapter2State\(null,false\)/);
// v0.67：上志比の状態 kami（古いセーブ・不正な値・往復）
{ const kc=vm.createContext({clamp:(v,a,b)=>Math.min(b,Math.max(a,v)),ROCK_MAX:8,stats:{time:1000},prog:{}});
  vm.runInContext(html.slice(html.indexOf('const KW={beasts:'),html.indexOf('// ---- 場所を決める ----')),kc);
  const L=q=>JSON.parse(JSON.stringify(vm.runInContext('kamiLoad('+JSON.stringify(q)+')',kc)));
  const fresh={v:1,n:{},r:{},sc:[],f:[],sp:{},g:{},st:{},fm:{},fb:[],pl:{}}; // v0.88：fb 切った広葉樹・pl 苗木を植えた時刻
  for(const bad of [null,42,'x',[],{v:2,n:{s0:5}}]) assert.deepEqual(L(bad),fresh,'malformed: fresh');
  assert.deepEqual(L(null),fresh,'old save: nothing taken');
  const q=L({v:1,n:{s0:1200,zz:5,b1:'x',o3:-5},r:{r1:3,r2:99,s0:1},sc:[1,2,'a',-1],f:['k1_2_3','bad','f1_1_1'],sp:{a0:1500,b:1},g:{g0:{d:[1,0,1,1],w:2000},x:{d:[1]}},st:{fort:{n:2,t:300},outB:{n:0,t:5},bad:{n:1},outA:{n:'x'}},fm:{f3:2000,a1:'x',z9:5,b2:-4}});
  assert.deepEqual(q.n,{s0:1200,o3:0}); assert.deepEqual(q.r,{r1:3,r2:8}); assert.deepEqual(q.sc,[1,2]); assert.deepEqual(q.f,['k1_2_3']); assert.deepEqual(q.sp,{a0:1500}); assert.deepEqual(q.g,{g0:{d:[1,0,1],w:2000}}); assert.deepEqual(q.st,{fort:{n:2,t:300}}); assert.deepEqual(q.fm,{f3:2000,b2:0}); // v0.68：物資置き場・v0.69：守りのサル
  { const q2=L({v:1,n:{q1:50,q:3},r:{q2:9,q3:1,r1:2},f:['kp3','kp','k1_2_3','kpx']}); assert.deepEqual(q2.n,{q1:50}); assert.deepEqual(q2.r,{q2:3,q3:1,r1:2},'v0.85: river ore (q) up to 3'); assert.deepEqual(q2.f,['kp3','k1_2_3'],'v0.85: felled broadleaf trees (kp)'); }
  vm.runInContext('prog.kami=kamiLoad('+JSON.stringify({v:1,n:{s0:1200},r:{r1:0},sc:[4],f:['k0_0_1'],sp:{a0:900,a1:1500},g:{g0:{d:[1,1,0],w:0},g1:{d:[0,0,0],w:500}},st:{outB:{n:1,t:950}},fm:{f1:1600,b0:200}})+')',kc);
  const s2=JSON.parse(JSON.stringify(vm.runInContext('kamiSave()',kc)));
  assert.deepEqual(s2,{v:1,n:{s0:1200},r:{r1:0},sc:[4],f:['k0_0_1'],sp:{a1:1500},g:{g0:{d:[1,1,0],w:0}},st:{outB:{n:1,t:950}},fm:{f1:1600},fb:[],pl:{}},'round trip keeps pending times only');
  { const q3=L({v:1,n:{t12:1300,h3:1400,x1:5},f:['k1_1_1'],fb:['k2_2_2','kp4','bad',7],pl:{k2_2_2:900,kp9:5,k3_3_3:'x'}}); assert.deepEqual(q3.n,{t12:1300,h3:1400},'v0.88: bamboo grove (t) and mountain herb (h)'); assert.deepEqual(q3.fb,['k2_2_2','kp4'],'v0.88: felled broadleaf (fb)'); assert.deepEqual(q3.pl,{k2_2_2:900},'v0.88: planted only on felled broadleaf (pl)'); } }
// v0.73：スズキの状態 suzuki（古いセーブ・不正な値は「まだ仲間でない」）
{ const sc=vm.createContext({});
  vm.runInContext('let prog=null; '+html.slice(html.indexOf('function szKamiBaseOK()'),html.indexOf('function szKamiBase()'))+html.slice(html.indexOf("const SZ_ORDERS=['follow'"),html.indexOf('// 読み込む：ついて来ているスズキと')),sc);
  const L=q=>JSON.parse(JSON.stringify(vm.runInContext('szLoadState('+JSON.stringify(q)+',180)',sc)));
  for(const bad of [undefined,null,42,'x',[],{v:2,joined:true},{v:1},{v:1,joined:false},{v:1,joined:'yes'}]) assert.equal(L(bad===undefined?null:bad).joined,false,'old/malformed save: not joined');
  const full=L({v:1,joined:true,order:'wait',region:'kamishihi',x:5070.25,z:759.5,wx:5071,wz:760,hp:120,down:false});
  assert.deepEqual(full,{joined:true,order:'wait',region:'kamishihi',x:5070.25,z:759.5,wx:5071,wz:760,hp:120,down:false},'round trip');
  assert.deepEqual(L({v:1,joined:true,order:'fly',region:'mars',x:'a',z:3,hp:999}),{joined:true,order:'follow',region:'komyoji',x:null,z:null,wx:null,wz:null,hp:180,down:false},'bad fields fall back');
  const dn=L({v:1,joined:true,order:'follow',region:'komyoji',x:120,z:10,wx:0,wz:0,hp:50,down:true}); assert.equal(dn.down,true); assert.equal(dn.hp,0,'down: hp 0');
  assert.equal(L({v:1,joined:true,order:'follow',x:1,z:1,hp:0}).hp,1,'standing Suzuki keeps at least 1 hp');
  const w=L({v:1,joined:true,order:'wait',region:'komyoji',x:7,z:8}); assert.deepEqual([w.order,w.wx,w.wz],['wait',7,8],'wait spot falls back to the position');
  assert.equal(L({v:1,joined:true,order:'wait',region:'komyoji'}).order,'follow','no position: follow');
  assert.equal(L({v:1,joined:true,order:'base',region:'kamishihi',x:5000,z:700}).order,'follow','base only in Komyoji');
  vm.runInContext('prog={p3:{hq:{plan:1}}}',sc); assert.equal(L({v:1,joined:true,order:'base',region:'kamishihi',x:5000,z:700}).order,'base','v0.82: base in Kamishihi after the founding talk');
  assert.match(html,/kami:kamiSave\(\),suzuki:szSave\(\),p3:p3Save\(\),stash:stashSave\(\),p3c:p3cSave\(\),p3d:prog\.p3d\}/); assert.match(html,/prog\.p3c=p3cLoad\(d\.p3c\)/); assert.match(html,/prog\.p3d=p3dLoad\(d\.p3d\)/); /* v0.84：釣り */ assert.match(html,/szApplyLoad\(d\.suzuki\)/); }
{ // v0.81 P3-B：拠点本部 p3・資材置き場 stash の読み込み（古いセーブ・不正な値）
  const code=html.slice(html.indexOf('function p3Fresh()'),html.indexOf('function stashHere()'));
  const c3=vm.createContext({}); vm.runInContext(`const P3B={carry:{mats:['wood','stone','iron','rope','straw','bamboo','hide','charcoal','oldParts']}}; const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)); function num(v,def,min=0,max=9999){ return (typeof v==='number'&&isFinite(v))?clamp(Math.floor(v),min,max):def; } let prog={}; let inv={};\n${code}`,c3);
  const J=x=>JSON.parse(JSON.stringify(x)), L=q=>J(c3.p3Load(q)), F=J(c3.p3Fresh());
  for(const bad of [undefined,null,42,'x',[],{v:2,hq:{plan:1}}]) assert.deepEqual(L(bad),F,'old or malformed p3: fresh');
  assert.deepEqual(L({v:1,hq:{sv:[1,'a',0],talk:0,plan:0}}).hq.sv,[1,1,0],'truthy values become 1');
  assert.deepEqual(L({v:1,hq:{plan:1}}).hq.sv,[1,1,1],'plan started: surveys and talk are done');
  assert.equal(L({v:1,hq:{plan:1}}).hq.talk,1);
  assert.deepEqual(L({v:1,hq:{sv:[1,1,1],talk:1,plan:0}}).hq,{sv:[1,1,1],talk:0,plan:0,beasts:0,visited:0},'closed during the founding talk: the talk plays again');
  assert.deepEqual(L({v:1,hq:{plan:1},rep:{storage:[1,0,0],workshop:[1,1,0]}}).rep.workshop,[0,0,0],'workshop needs storage first');
  assert.deepEqual(L({v:1,hq:{plan:1},rep:{storage:[1,1,1],workshop:[1,0,1]}}).rep.workshop,[1,0,1]);
  assert.equal(L({v:1,got:{yardHits:-5}}).got.yardHits,0);
  const S=q=>J(c3.stashLoad(q));
  for(const bad of [undefined,null,{v:2,komyoji:{wood:5}},'x']) assert.deepEqual(S(bad),{v:1,komyoji:{},kami:{}},'old or malformed stash: empty');
  assert.deepEqual(S({v:1,komyoji:{wood:12,gold:9,stone:-3,iron:'x'},kami:{rope:4.7}}),{v:1,komyoji:{wood:12},kami:{rope:4}},'only known materials, whole numbers'); }
{ // v0.82 P3-C：住民 p3c の読み込み（古いセーブ・不正な値・進み具合のつじつま）
  const code=html.slice(html.indexOf('function p3cFresh()'),html.indexOf('function p3cState()'))+html.slice(html.indexOf('const P3C_FAC='),html.indexOf('function p3cFac()'))+html.slice(html.indexOf('const P3C_REQ='),html.indexOf('function p3cReq(id)'))+html.slice(html.indexOf('function p3cForgeLoad('),html.indexOf('let TRUCK_BASE0')); /* v0.85 C-4 */ // v0.83：依頼と仕事も
  const c4=vm.createContext({}); vm.runInContext(`const WEAPONS={nata1:{},spear:{},boomer:{boomer:1}}; const G47={work_chest:{},forest_chest:{}}; const P3C={hits:3}; const P3C_LINES={}; function num(v,def,min=0,max=9999){ return (typeof v==='number'&&isFinite(v))?Math.max(min,Math.min(max,Math.floor(v))):def; } let prog={};`+code,c4);
  const J=x=>JSON.parse(JSON.stringify(x)), L=q=>J(c4.p3cLoad(q)), F=J(c4.p3cFresh());
  for(const bad of [undefined,null,42,'x',[],{v:2,sumie:{done:1}}]) assert.deepEqual(L(bad),F,'old or malformed p3c: nobody yet');
  assert.deepEqual(L({v:1,sumie:{done:1}}).sumie,{met:1,hits:3,done:1},'rescued Sumie: met and pile cleared');
  assert.deepEqual(L({v:1,sumie:{met:1,hits:9}}).sumie,{met:1,hits:3,done:0},'hits capped');
  assert.deepEqual(L({v:1,rio:{done:1}}).rio,{met:1,shelf:1,talk:1,parts:[1,1],fixed:1,done:1},'Rio joined: all steps done');
  assert.deepEqual(L({v:1,rio:{met:1,parts:[1,1]}}).rio.parts,[0,0],'parts only after the talk');
  assert.deepEqual(L({v:1,rio:{talk:1,parts:[1,'a']}}).rio,{met:1,shelf:1,talk:1,parts:[1,1],fixed:0,done:0});
  assert.deepEqual(L({v:1,soichi:{coop:1,job:5}}).soichi,{found:0,coop:1,joinDone:0,resident:0,job:''},'Soichi: separate flags (P3-D)');
  // v0.82 C-2：施設の工事（納めた素材・進み）と住民の担当
  const f=L({v:1,fac:{housing:{dl:{wood:30,straw:5,gold:9,rope:-2},h:9,done:0},defense:{dl:{wood:20},h:1.5,done:0},farm:{done:1}},job:{sumie:'b:housing',rio:'b:farm',x:'b:defense'}});
  const E={dl:{},h:0,done:0};
  assert.deepEqual(f.fac,{housing:{dl:{wood:24,straw:5},h:4,done:0},defense:{dl:{wood:20},h:1.5,done:0},farm:{dl:{},h:2,done:1},garage:E,haul:E,works:E},'delivered capped at the cost, unknown materials dropped, progress capped (v0.83: Lv2 facilities too)');
  assert.deepEqual(f.job,{sumie:'b:housing',rio:'b:farm',evac:'',soichi:''},'only buildable facilities as jobs');
  assert.deepEqual(L({v:1,fac:{housing:{done:1}}}).fac.housing,{dl:{},h:4,done:1},'done: full progress');
  assert.deepEqual(L({v:1,job:{sumie:'w:farm',rio:'w:haul',evac:'w:fish'}}).job,{sumie:'w:farm',rio:'w:haul',evac:'',soichi:''},'work jobs: farm and haul only');
  // v0.83 C-3：段階・依頼・避難住民・農園の収穫・収集の端数
  assert.equal(F.lv,1); assert.deepEqual(F.req,{}); assert.equal(F.trk,''); assert.deepEqual(F.ev,{res:0});
  for(const [v,e] of [[2,2],[3,3],[9,3],[0,1],['x',1],[2.7,2]]) assert.equal(L({v:1,lv:v}).lv,e,'level clamped 1..3');
  const q=L({v:1,req:{trace:{a:1,s:[1,1,null,0],h:[0,0,0,0]},salvage:{a:1,s:[0,0],h:[99,0]},nope:{a:1},tools:{r:1},bell:{a:0,s:[1,1,1]}},trk:'trace'});
  assert.deepEqual(q.req.trace,{a:1,s:[1,1,0,0],h:[0,0,0,0],r:0},'accepted request: steps as 0/1');
  assert.deepEqual(q.req.salvage.h,[4,0],'hits capped');
  assert.deepEqual(q.req.tools,{a:1,s:[1,1,1],h:[4,0,3],r:1},'reported: all steps done');
  assert.ok(!('nope' in q.req)&&!('bell' in q.req),'unknown or not accepted requests dropped'); assert.equal(q.trk,'trace');
  assert.equal(L({v:1,req:{tools:{r:1}},trk:'tools'}).trk,'','no tracking of a reported request'); assert.equal(L({v:1,trk:'nope'}).trk,'');
  assert.deepEqual(L({v:1,req:{evac:{a:1,s:[1,1,1]}}}).ev,{res:1},'evacuee found: resident'); assert.deepEqual(L({v:1,ev:{res:1}}).ev,{res:1});
  const o=L({v:1,out:{veg:99},acc:{farm:0.5,haul:{wood:0.4,gold:3}},got:{wood:12,gold:2}});
  assert.equal(o.out.veg,30,'harvest capped');
  // v0.85 C-4：武器の鍛え直し・防具の補強・車両の高度加工
  assert.deepEqual(F.forge,{w:{},a:{}}); assert.deepEqual(F.vup,{plate:0,tank:0,frame:0});
  const fg=L({v:1,forge:{w:{nata1:2,spear:7,boomer:1,gold:1,club:'x'},a:{work_chest:1,nope:1,forest_chest:0}},vup:{plate:1,tank:'y',wings:1}});
  assert.deepEqual(fg.forge,{w:{nata1:2,spear:2},a:{work_chest:1}},'forge levels 0..2, known weapons and armor only (not the boomerang)');
  assert.deepEqual(fg.vup,{plate:1,tank:1,frame:0},'vehicle upgrades as 0/1');
  assert.deepEqual(L({v:1,forge:'x',vup:5}).forge,{w:{},a:{}});
  { // v0.84 P3-D：釣り（p3d）
    const code=html.slice(html.indexOf('const FISH=['),html.indexOf('function p3dState()'))+html.slice(html.indexOf('const AQUA=['),html.indexOf('const AQUA_BY'));
    const c5=vm.createContext({}); vm.runInContext(`function num(v,def,min=0,max=9999){ return (typeof v==='number'&&isFinite(v))?Math.max(min,Math.min(max,Math.floor(v))):def; }`+code,c5); const L5=q=>JSON.parse(vm.runInContext(`JSON.stringify(p3dLoad(${JSON.stringify(q)}))`,c5));
    const F5=JSON.parse(vm.runInContext('JSON.stringify(p3dFresh())',c5)); assert.deepEqual(F5.rod,{basic:0,pro:0,guard:0}); assert.deepEqual(F5.ara,{observed:0,caughtReleased:0,reported:0,rodRewardClaimed:0});
    assert.deepEqual(L5(null),F5,'no p3d: fresh'); assert.deepEqual(L5({v:2,rod:{basic:1}}),F5,'other version: fresh'); assert.deepEqual(F5.obs,{}); assert.deepEqual(L5({v:1,obs:{oAyu:{n:2,band:'昼'},oSagi:{n:0},nope:{n:3},oKawasemi:{n:'x'}}}).obs,{oAyu:{n:2,band:'昼'}},'v0.85 D-3: observation records, known spots only');
    const a=L5({v:1,ara:{rodRewardClaimed:1}}); assert.deepEqual(a.ara,{observed:1,caughtReleased:1,reported:1,rodRewardClaimed:1},'later stages imply earlier ones'); assert.equal(a.rod.guard,1,'reward claimed: river-guard rod');
    const b=L5({v:1,book:{fAyu:{n:3,max:999,where:'九頭竜川（本流の瀬）',band:'昼'},nope:{n:1},ara:{seen:1}},casts:-5});
    assert.deepEqual(b.book.fAyu,{n:3,max:200,where:'九頭竜川（本流の瀬）',band:'昼',seen:1}); assert.ok(!('nope' in b.book)); assert.equal(b.book.ara.seen,1); assert.equal(b.casts,0);
    const c=L5({v:1,book2:{aMokuzu:{n:2,where:'河内川（支流）',band:'朝'},aNope:{n:1},aYago:{seen:1}}}); assert.deepEqual(c.book2.aMokuzu,{n:2,where:'河内川（支流）',band:'朝',seen:1}); assert.ok(!('aNope' in c.book2)); assert.equal(c.book2.aYago.seen,1); assert.deepEqual(F5.book2,{}); } assert.deepEqual(o.acc,{farm:0.5,haul:{wood:0.4}},'fractions kept (below 1), unknown materials dropped'); assert.deepEqual(L({v:1,acc:{farm:7,haul:{wood:-1}}}).acc,{farm:0.999,haul:{}}); assert.deepEqual(o.got,{wood:12}); }
console.log('PASS: inline script syntax; legacy/malformed defaults; boss unlock; save round trip; existing key, version, inventory and durability; v0.67 kami state; v0.73 suzuki state; v0.81 p3/stash state; v0.82 p3c residents; v0.83 p3c requests and level; v0.84 p3d fishing');
