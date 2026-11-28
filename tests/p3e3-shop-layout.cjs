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
  const clamp=(n,lo,hi)=>Math.min(hi,Math.max(lo,n));
  const window={innerWidth:390,innerHeight:844}, renderer={setSize(){}};
  const CAM_PITCH_SENS={std:{gain:1}}, camPitchSettings={sens:'std',inv:false};
  const S={mode:'playing',shake:0}, TRUCK={}, keys=new Set();
  const bossE=null, enemies=[], torches=[], NPCS=[], fadeables=[];
  const bossCinema52=()=>false, fadeForest=()=>{}, vibrate52=()=>{};
  let ground=0;
  const groundH=()=>ground;
  const szHere=()=>false;
  const p3cHqPlan=()=>{}, p3bHqProps=()=>{}, p3bMarks=()=>{}, p3bOpen=()=>{}, p3bHqEntered=()=>{}, p3bInteract=()=>{};
  const p3cFactoryProps=()=>{}, p3cFactoryMarks=()=>{}, p3cOn=()=>{}, p3cFactoryEntered=()=>{}, p3cFactoryInteract=()=>{};
`, context);

const parts = [
  ['const CAM={dist:', "window.addEventListener('resize',onResize);"],
  ['function hash3(', '\nfunction '],
  ['function smooth01(', '\n'],
  ['const boxes=[];', '// 円形の実体'],
  ['function pointBoxDist(', '// ================= 遮蔽フェード'],
  ['const INKC=', 'function inkFor('],
  ['class GB{', '// ---- 地面の絵'],
  ['function p3aRng(', '\nfunction '],
  ['const P3IN=', 'function p3inDef('],
  ['function p3eShopFloor(', 'function p3bHqProps('],
  ['function p3inBuildFloor(', 'function p3bRebuild('],
  ['function p3bInteriorTick(', '// 店の暗転'],
  ['function szFree(', 'function szWalkable('],
  ['const cam={yaw:', '// カメラと主人公の間にある森の杉'],
  ['function updateCamera(dt){', '// ================= ループ'],
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

  function borderSweep(floor, px, pz, pitch, blocked, clear){
    P3A.floors=[floor]; p3inActivate(1); P3A.inside=true;
    P.x=floor.def.o.x+px; P.z=floor.def.o.z+pz;
    assert(szFree(P.x,P.z,0.5));
    const anchor=new THREE.Vector3(P.x,1.3,P.z);
    for(const [dt, maxStep] of [[1/60,0.5],[1/30,0.95],[0.05,1.5]]){
      setCam(clear); cam.curDist=0.94; cam.pitch.in=pitch;
      for(let i=0;i<100;i++) updateCamera(dt);
      let peak=0, settled=0;
      // 壁の角をまたぐ小さな左右ドラッグを連続で送る。
      for(let i=0;i<90;i++){
        const next=i%2?clear:blocked, previous=camera.position.clone();
        cam.dragDX=(cam.yaw-next)/0.0065;
        updateCamera(dt); p3bInteriorTick(dt);
        const step=previous.distanceTo(camera.position);
        peak=Math.max(peak,step);
        if(i>=60) settled=Math.max(settled,step);
        const {x,y,z}=camera.position;
        assert(!floor.cols.some(b=>x>b.minX&&x<b.maxX&&z>b.minZ&&z<b.maxZ&&y<b.h), 'レンズが壁や家具の中に入らない');
        assert(camera.position.distanceTo(anchor)>2, floor.id+' のカメラが主人公の近くに飛ばない');
      }
      assert(peak<maxStep&&settled<0.2, floor.id+' の1フレーム移動 '+peak+' m、収束後 '+settled+' m');
      cam.yaw=blocked;
      for(let i=0;i<100;i++) updateCamera(dt);
      assert(cam.curDist<0.35, '障害物でカメラ距離が縮む');
      cam.yaw=clear;
      for(let i=0;i<160;i++) updateCamera(dt);
      assert(cam.curDist>0.93, '障害物を外れるとカメラ距離が戻る');
      console.log(floor.id+' '+window.innerWidth+'×'+window.innerHeight+' '+Math.round(1/dt)+' fps相当: '+peak.toFixed(3)+' m/フレーム、収束後 '+settled.toFixed(3)+' m');
    }
    for(const c of floor.cols) c.active=false;
  }
  onResize();
  borderSweep(first,7.15,1.87,0.08,0.544,0.592);
  borderSweep(farm,15.07,20.35,-0.08,6.24,6.288);
  window.innerWidth=1280; window.innerHeight=720; onResize();
  borderSweep(first,7.15,1.87,0.14,0.336,0.384);
  borderSweep(farm,15.07,20.35,-0.08,6.144,6.192);

  // 屋外では従来の注視線と地面の高さを使う。屋内の当たりが残っていても高さ補正の対象外。
  P3A.inside=false; ground=-7; P.x=-12; P.z=3;
  addBox(P.x-CAM.shoulder,P.z-CAM.dist,0.2,0.2,'wall',{h:15,p3a:1,active:false});
  setCam(0); cam.pitch.out=0; cam.curDist=0.94;
  updateCamera(1/60);
  assert(Math.abs(camera.position.y-(ground+1.3+(CAM.h-1.3)*0.94))<1e-9);
  console.log('PASS: 屋内のカメラ補正、屋外の既定構図');
`, context);
