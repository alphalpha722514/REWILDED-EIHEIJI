// WebGLを使わず、本編の屋内生成・壁表示・当たりをThree.js r128で調べる。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const THREE = process.env.THREE_JS ? require(path.resolve(process.env.THREE_JS)) : require('three');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const context = vm.createContext({THREE, assert, console});

function source(start, end) {
  const first = html.indexOf(start);
  const last = html.indexOf(end, first + start.length);
  assert(first >= 0 && last > first, `本編の抽出範囲: ${start}`);
  return html.slice(first, last);
}

vm.runInContext(`
  const scene=new THREE.Scene(), camera=new THREE.PerspectiveCamera();
  const P={}, P3A={}, REG={}, P3A_IN={x:21000,z:21000}, TAU=Math.PI*2;
  const G={box:new THREE.BoxGeometry()}, vcMat=new THREE.MeshLambertMaterial({vertexColors:true});
  const dist=(x,z,a,b)=>Math.hypot(x-a,z-b), lerp=(a,b,t)=>a+(b-a)*t;
  const szHere=()=>false;
  const p3cHqPlan=()=>{}, p3bHqProps=()=>{}, p3bMarks=()=>{}, p3bOpen=()=>{}, p3bHqEntered=()=>{}, p3bInteract=()=>{};
  const p3cFactoryProps=()=>{}, p3cFactoryMarks=()=>{}, p3cOn=()=>{}, p3cFactoryEntered=()=>{}, p3cFactoryInteract=()=>{};
`, context);

const parts = [
  ['function hash3(', '\nfunction '],
  ['const boxes=[];', '// 円形の実体'],
  ['const INKC=', 'function inkFor('],
  ['class GB{', '// ---- 地面の絵'],
  ['function p3aRng(', '\nfunction '],
  ['const P3IN=', 'function p3inDef('],
  ['function p3eShopFloor(', 'function p3bHqProps('],
  ['function p3inBuildFloor(', 'function p3bRebuild('],
  ['function p3bInteriorTick(', '// 店の暗転'],
  ['function szFree(', 'function szWalkable('],
];
vm.runInContext(parts.map(([start, end]) => source(start, end)).join('\n'), context);

vm.runInContext(`
  P3A.floors=P3IN.shop.floors.map((def,i)=>p3inBuildFloor('shop',def,i+1));
  const [first,second]=P3A.floors, farm=p3inBuildFloor('farm',P3IN.farm,1);
  const totals=[first,second,farm].map((floor,i)=>{
    let meshes=0,triangles=0;
    floor.g.traverse(mesh=>{
      if(!mesh.isMesh) return;
      meshes++;
      triangles+=(mesh.geometry.index?.count??mesh.geometry.attributes.position.count)/3;
    });
    console.log((i===2?'古い農家':(i+1)+'階')+' '+triangles+'三角形 '+meshes+'メッシュ');
    return {meshes,triangles};
  });
  assert(totals.slice(0,2).every(s=>s.meshes<=50&&s.triangles<=10000));
  assert(totals[0].triangles+totals[1].triangles<15000);
  assert(first.windowSun.isMeshLambertMaterial&&second.windowSun.isMeshLambertMaterial);
  assert(first.mk.length===1&&second.mk.length===0);

  p3inActivate(2);
  const {x,z}=second.def.o;
  const bases=second.uppers.filter(u=>u.base);
  assert(bases.length===3&&first.uppers.every(u=>!u.base)&&farm.uppers.every(u=>!u.base));
  const bedWall=bases.find(u=>u.x0===u.x1), closetWall=bases.find(u=>u.z0===u.z1&&u.x0===x+8);
  function view(aspect,px,pz,cx,cz){
    camera.aspect=aspect; P.x=x+px; P.z=z+pz; camera.position.set(x+cx,7,z+cz);
    p3bInteriorTick(0);
  }
  view(390/844,10.6,9.7,5,9.7);
  assert(!bedWall.m.visible&&!bedWall.base.visible&&closetWall.base.visible);
  assert(!szFree(x+8,z+9.7,0.42));
  view(1280/720,10.6,9.7,5,9.7);
  assert(!bedWall.m.visible&&bedWall.base.visible);
  view(390/844,10.6,9.7,14,9.7);
  assert(bedWall.m.visible&&bedWall.base.visible);
  view(390/844,8.9,10.5,8.9,14);
  assert(!closetWall.m.visible&&!closetWall.base.visible);
  assert(!szFree(x+8.9,z+11.6,0.42));
  view(390/844,10.2,10.5,10.2,14);
  assert(closetWall.m.visible&&closetWall.base.visible);
  view(390/844,5,9.7,11,9.7);
  assert(!bedWall.m.visible&&bedWall.base.visible);
  p3inActivate(1);
  assert(first.cols.every(c=>c.active)&&second.cols.every(c=>!c.active));
  console.log('PASS: 台所の縦画面、横画面、視点の反転、収納戸口、別室、階別の当たりと窓材質');
`, context);
