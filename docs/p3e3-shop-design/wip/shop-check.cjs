const fs=require('fs'), vm=require('vm'), assert=require('assert/strict');
const html=fs.readFileSync('index.html','utf8');
const ctx=vm.createContext({assert,console});
const run=s=>vm.runInContext(s,ctx), source=(a,b)=>{
  const i=html.indexOf(a),j=html.indexOf(b,i+1); assert(i>=0&&j>i,a); return html.slice(i,j);
};
run(`
const P={r:0.5,x:6405,z:864,facing:0}, SZ={r:0.42,x:6407,z:864,region:'kamishihi',joined:true,order:'follow',stk:{},crumbs:[]};
const BOUNDS={minX:5000,maxX:8000,minZ:0,maxZ:2000},P3A_IN={x:21000,z:21000},REGION_X0=4000;
const REG={cur:'kamishihi',busy:false,hfn:()=>3,live:{group:{visible:true}}},S={mode:'playing'};
const door={id:'house110',inId:'shop',x:6405,z:864,facing:1.22},P3A={on:true,inside:false,busy:false,doors:[door]};
const state={hq:{plan:0},e3:{map:0},got:{}}, p3bState=()=>state,prog={p3:state};
const no=()=>{},p3cOutdoor=no,p3cOutside=no,p3cResInteractables=no,p3cReqOutside=no,p3dOutside=no;
const p3eFarmProps=no,p3eFarmMarks=no,p3eFarmEntered=no,p3eFarmInteract=no,p3cHqPlan=no,p3bHqProps=no,p3bMarks=no,p3bOpen=no,p3bHqEntered=no,p3bInteract=no,p3cFactoryProps=no,p3cFactoryMarks=no,p3cFactoryEntered=no,p3cFactoryInteract=no;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),lerp=(a,b,t)=>a+(b-a)*t,dist=(x,z,a,b)=>Math.hypot(x-a,z-b);
const isWater=()=>false,KAMI=null,SZA={r:0.42},enemies=[],groundH=(x,z)=>REG.hfn(x,z),camera={position:{}};
class Attr{constructor(a,s){this.a=a;this.s=s;this.count=a.length/s}getX(i){return this.a[i*this.s]}getY(i){return this.a[i*this.s+1]}getZ(i){return this.a[i*this.s+2]}}
class Geo{constructor(){this.attributes={};this.userData={}}setAttribute(k,v){this.attributes[k]=v}setIndex(v){this.index=v}computeBoundingSphere(){this.boundingSphere={clone(){return this}}}dispose(){}}
class Obj{constructor(){this.children=[];this.scale={set:no};this.position={set:no};this.rotation={set:no}}add(o){this.children.push(o)}remove(o){this.children.splice(this.children.indexOf(o),1)}traverse(fn){fn(this);for(const c of this.children)c.traverse(fn)}}
class Mesh extends Obj{constructor(g,m){super();this.geometry=g;this.material=m}}
class Mat{dispose(){}}
const THREE={BufferGeometry:Geo,Float32BufferAttribute:Attr,Uint16BufferAttribute:Attr,Uint32BufferAttribute:Attr,BufferAttribute:Attr,Group:Obj,Mesh,MeshBasicMaterial:Mat,MeshLambertMaterial:Mat,Color:class{constructor(){this.r=this.g=this.b=1}}};
const scene=new Obj(),vcMat={},inkMat={},G={box:{index:{count:36}}};
let now=0,msg='',gates=[],curInter=null;const performance={now:()=>now},keys=new Set(),cz={},cam={},setCam=no;
const szSmellTick=no,STF={},szRescueCancel=no,szCombatReset=no,p3cResVis=no,clearCamPitchInput=no,clearCinemaInput52=no,sfx=no,toast=t=>msg=t;
const stfFadeEl=()=>({classList:{add:no,remove:no}}),stfFade=()=>new Promise(f=>gates.push(f)),stfWait=stfFade;
const held={},P3D={},bossCinema52=()=>false;
`);
run([
 ['function inkGeo(', 'function inkFor('],['class GB{','// ---- 地面の絵'],['function hash3(', '\nfunction '],
 ['const boxes=[];', 'function pointBoxDist'],['function gridRemove(', '// 地域が作った物'],['const P3IN=', 'function p3inDef('],
 ['function p3cOn(){','\nfunction '],['function p3inLightMesh(', 'function p3eFarmSoil('],['function p3eShopFloor(', '// 古い農家の母屋'],
 ['function p3aInteriorBuild(', '// 引き戸と、手前'],['let p3ShopFading=', 'function p3bHqEntered(){'],['async function p3aExit(){','function p3aMove('],
 ['function p3inDispose(){','function p3aDispose('],['function p3bOutside(L)', 'function p3bOutsideTick'],['function p3aInteractables(L)','// ---- v0.85 P3-D'],
 ['const SZ_ORDERS=', '// 読み込む：ついて来ているスズキと'],['function szHere(){','function szModel(){'],['function szFree(', '// 戦っているか：'],['function szPut(', '// 主人公のすぐ後ろに出す'],
 ['function szPlaceTick(){','// ---- 第3段階：倒れる'],['function updateSuzuki(dt)', '// ================= v0.77'],['function interact(){','function gatherNode(']
].map(([a,b])=>source(a,b)).join('\n'));
const ev=s=>run(s);
const phase=async()=>{ev('gates.shift()()');await new Promise(r=>setImmediate(r))};
async function transit(call,mid){
  const p=ev(call);assert(ev("P3A.busy&&p3ShopFading"));
  ev('curInter={act(){throw Error("暗転中に入力")}}; interact()');
  await phase();mid();await phase();ev('interact()');await phase();await p;
  ev('interact();now+=221;assert(!p3eShopBlocksAction())');
}
function floor(level){
  assert(ev(`P3A.interior.level===${level}&&p3eShopFloorAt(P.x,P.z)===${level}&&szWalkable(P.x,P.z)&&P3A.floors.every(f=>f.g.visible===(f.level===${level})&&f.cols.every(c=>c.active===f.g.visible))`));
  ev('constBefore=[P.x,P.z];resolve(P,false);assert.deepEqual([P.x,P.z],constBefore)');
}
function step(){ev("m=P3A.interior.marks.find(k=>k.to);P.x=m.x;P.z=m.z")}
(async()=>{
  for(const plan of [0,1])for(const map of [0,1]){
    ev(`state.hq.plan=${plan};state.e3.map=${map};L=[];p3bOutside(L)`);
    assert.equal(ev('L[0]?.label'),!plan?undefined:map?'よろず屋に入る':'入口を調べる');
  }
  ev('state.e3.map=0;L[0].act();assert(!P3A.busy);assert.equal(msg,"ここから入る手がかりがない");state.e3.map=1');
  ev('P.x=door.x+2.61;L=[];p3bOutside(L);assert(!L.length);P.x=door.x');
  await transit('p3aEnter(door)',()=>floor(1));
  const triangles=ev('P3A.floors.map(f=>{let n=0;f.g.traverse(o=>{if(o.geometry)n+=o.geometry.index.count/3});return n})');
  console.log('両階の生成三角形（描画器を使わない形状集計）',triangles);
  assert(triangles.every(n=>n>0&&n<=10000)&&triangles.reduce((a,b)=>a+b)<15000);
  ev('assert(szHere());const o=P3A.interior.def.o;assert(!szFree(o.x+2.6,o.z+2.2,.42));assert(szLine(o.x+6.3,o.z+8.7,o.x+11,o.z+8.7));szPut(o.x+2.6,o.z+2.2,0);resolve(SZ,false);assert(szFree(SZ.x,SZ.z,.419))');
  step();await transit('p3eShopInteract(m)',()=>floor(2));
  ev("assert(szHere());assert(p3eShopFloorAt(SZ.x,SZ.z)===2);p3bRebuild();SZ.order='wait';SZ.wx=SZ.x;SZ.wz=SZ.z;SZ.m={g:{visible:true}};saved=[SZ.x,SZ.z,SZ.wx,SZ.wz];");floor(2);
  step();await transit('p3eShopInteract(m)',()=>floor(1));
  ev('SZ.place=true;updateSuzuki(.05);assert(!szHere());assert(!SZ.m.g.visible);assert.deepEqual([SZ.x,SZ.z,SZ.wx,SZ.wz],saved);SZ.place=false;');
  step();await transit('p3eShopInteract(m)',()=>floor(2));ev("assert(szHere());assert.deepEqual([SZ.x,SZ.z,SZ.wx,SZ.wz],saved);SZ.down=true;SZ.hp=0;");
  step();await transit('p3eShopInteract(m)',()=>floor(1));
  ev("q=szSave();assert(q.down&&q.order==='wait'&&q.hp===0&&q.x===q.wx&&q.z===q.wz&&dist(q.x,q.z,door.x,door.z)<6);assert.deepEqual([SZ.x,SZ.z,SZ.wx,SZ.wz],saved);");
  await transit('p3aExit()',()=>ev('assert(!P3A.inside&&!REG.inB);assert(SZ.down&&SZ.hp===0&&SZ.x===SZ.wx&&SZ.z===SZ.wz);assert(dist(SZ.x,SZ.z,door.x,door.z)<6)'));
  await transit('p3aEnter(door)',()=>floor(1));ev('assert(!szHere());p3inDispose();assert(!boxes.length&&!cgrid.size);');
  console.log('入店4条件・実行時再判定・3遷移の入力・解放・階別当たり・再構築・同行・別階待機・転倒退出・再入店・破棄 OK');
})().catch(e=>{console.error(e);process.exitCode=1});
