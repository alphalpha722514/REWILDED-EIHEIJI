// v0.77 KEI truck の運転の物理（2026-11-17 ユーザー指示「慣性や遠心力で、こんなに俊敏には曲がれないはず」）を、
// index.html の truckDrive をそのまま取り出して確かめる（衝突・地形なし。1/60 秒ずつ）。node tests/truck-physics.cjs
'use strict';
const fs = require('fs'), path = require('path');
const src = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const cut = (a, b) => { const i = src.indexOf(a); if (i < 0) throw new Error('見つからない: ' + a); const j = src.indexOf(b, i); if (j < 0) throw new Error('見つからない: ' + b); return src.slice(i, j); };
const cfgSrc = cut('const TRUCK_CFG=', '\nfunction ');
const driveSrc = cut('function truckStop(){', '\n// 地域を移った');
let input = {ix: 0, iz: 0};
const sandbox = new Function('getInput', `
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)), dist=(a,b,c,d)=>Math.hypot(a-c,b-d), angDiff=(a,b)=>{ let d=b-a; while(d>Math.PI) d-=2*Math.PI; while(d<-Math.PI) d+=2*Math.PI; return d; };
  const TRUCK={m:null,wheels:[{rotation:{}},{rotation:{}},{rotation:{}},{rotation:{}}],v:0,vx:0,vz:0,yr:0,steer:0,roll:0,pitch:0,slide:0,x:0,z:0,a:0};
  const P={}, pm={g:{}}, cam={yaw:0}, REG={cur:'komyoji'}, SAVE={};
  const trk=()=>SAVE, truckWalk=()=>true, resolve=()=>{}, groundH=()=>0, spawnParticles=()=>{};
  const truckInput=()=>getInput();
  const TRUCK_SYS={gas:{perKm:12},hp:{bump:{v:4.5,k:4,cd:0.6}}}, S={time:0}, sfx=()=>{}, truckDamage=()=>{}, truckBurn=()=>{}, truckTipCheck=()=>false; // v0.78：燃料・傷み・横転はこのテストでは見ない（tests/kei-truck-systems-browser.py）
  const truckPerf=()=>({speed:TRUCK_CFG.speed,acc:TRUCK_CFG.acc});
  ${cfgSrc}
  ${driveSrc.replace(/function truckInput\(\)[\s\S]*?\n(?=function truckWalk)/, '').replace(/function truckWalk\([\s\S]*?\n(?=function truckDrive)/, '')}
  return {TRUCK, TRUCK_CFG, truckDrive, truckStop};`)(() => input);
const {TRUCK, TRUCK_CFG: C, truckDrive, truckStop} = sandbox;
const dt = 1 / 60;
function reset(speed) { truckStop(); Object.assign(TRUCK, {a: 0, x: 0, z: 0, vx: 0, vz: speed, v: speed, roll: 0, pitch: 0}); }
function drive(ix, iz, secs, each) { input = {ix, iz}; for (let k = 0; k < Math.round(secs / dt); k++) { truckDrive(dt); if (each) each(k); } }
const radius = () => Math.hypot(TRUCK.vx, TRUCK.vz) / Math.max(1e-6, Math.abs(TRUCK.yr));
let ok = true;
const check = (c, m) => { console.log((c ? 'ok   ' : 'FAIL ') + m); ok = ok && c; };

// 1) 止まっているとハンドルを切っても向きは変わらない
reset(0); drive(1, 0, 1); check(Math.abs(TRUCK.a) < 1e-6, `止まっているとハンドルを切っても向きは変わらない（${TRUCK.a.toFixed(4)}）`);
// 2) 速いときは大回り（遠心力の限界）。前の仕組みは 14m/秒で半径 7.4m・横の加速度 26.6m/秒²
reset(14); let maxLat = 0; drive(1, 0.5, 1, () => { maxLat = Math.max(maxLat, Math.abs(TRUCK.v * TRUCK.yr)); });
const r14 = radius();
check(r14 > 15, `14m/秒（約50km/時）で右いっぱい：1秒後の回る半径 ${r14.toFixed(1)}m（15m より大きい）`);
check(maxLat <= C.grip * C.yawSlip + 0.1, `横の加速度は最大 ${maxLat.toFixed(1)}m/秒²（タイヤの限界 ${C.grip}×${C.yawSlip} まで）`);
check(TRUCK.a < 0, '右へ切ると右へ曲がる（向きの角度が減る）');
// 3) 向きを変えても速さはすぐについて来ない（横滑り）。大きく滑ると速さが落ちる
reset(14); let maxW = 0; drive(1, 0.5, 3, () => { maxW = Math.max(maxW, TRUCK.slide); });
check(maxW > 0.5 && TRUCK.v < 12, `速いまま切り続けると外へ滑り（最大 ${maxW.toFixed(1)}m/秒）、速さが落ちる（3秒後 ${TRUCK.v.toFixed(1)}m/秒）`);
// 4) ゆっくりなら小回りできる（最小の回る半径 約3.6m）
reset(3); drive(1, 0.2, 1.5); const r3 = radius();
check(r3 < 4.5, `3m/秒で右いっぱい：回る半径 ${r3.toFixed(1)}m（小回りできる）`);
// 5) 少し切ったときは滑らない
reset(14); let sl = 0; drive(0.4, 0.5, 3, () => { sl = Math.max(sl, TRUCK.slide); });
check(sl === 0 && TRUCK.v > 13, `14m/秒で少し切るだけなら滑らない（速さ ${TRUCK.v.toFixed(1)}m/秒）`);
// 6) ハンドルは少しずつ切れる（いきなりは曲がらない）
reset(8); drive(1, 0.5, 0.1); const s01 = Math.abs(TRUCK.steer);
check(s01 < C.steerMax * 0.5, `ハンドルは少しずつ切れる（0.1秒で ${s01.toFixed(2)}rad）`);
// 7) 加速とブレーキ
reset(0); drive(0, 1, 2); const v2 = TRUCK.v; check(v2 > 4 && v2 < 9, `0から2秒アクセル：${v2.toFixed(1)}m/秒（急には速くならない）`);
reset(14); let tStop = 0; drive(0, -1, 3, k => { if (!tStop && TRUCK.v <= 0.05) tStop = (k + 1) * dt; });
check(tStop > 1.2 && tStop < 2.5, `14m/秒からブレーキで止まるまで ${tStop.toFixed(2)}秒`);
// 8) 後ろへ下がりながら右へ切ると、車の前は左へ振れる（向きの角度が増える）
reset(0); drive(0, -1, 1.5); drive(1, -1, 1.5); check(TRUCK.v < 0 && TRUCK.a > 0.05, `後退しながら右へ切ると前は左へ振れる（向き ${TRUCK.a.toFixed(2)}）`);
// 9) 車体は曲がる外側へ傾き、ブレーキで前へ沈む
reset(10); drive(1, 0.5, 1); check(TRUCK.roll < -0.02, `右へ曲がると車体は外（左）へ傾く（${TRUCK.roll.toFixed(3)}rad）`);
reset(12); drive(0, -1, 0.5); check(TRUCK.pitch > 0.01, `ブレーキで前へ沈む（${TRUCK.pitch.toFixed(3)}rad）`);
// 10) 浮いている（前の車輪が地面にない）間はハンドルを切っても向きは変わらない
reset(10); TRUCK.gf = 0; TRUCK.gr = 0; drive(1, 1, 0.5); const a10 = TRUCK.a; TRUCK.gf = 1; TRUCK.gr = 1;
check(Math.abs(a10) < 1e-6, `宙に浮いている間はハンドルもアクセルも効かない（向き ${a10.toFixed(4)}・速さ ${TRUCK.v.toFixed(1)}m/秒）`);

// ---- ばね（段差で跳ね上がる・少し浮く）。truckSusp をそのまま動かす ----
const suspSrc = cut('const TRUCK_WHEELS=', '\nfunction truckSegIdx') + '\n' + cut('function truckSusp(dt){', '// 乗る・降りる');
let ground = () => 0;
const SU = new Function('getGround', `
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)), dist=(a,b,c,d)=>Math.hypot(a-c,b-d), angDiff=(a,b)=>{ let d=b-a; while(d>Math.PI) d-=2*Math.PI; while(d<-Math.PI) d+=2*Math.PI; return d; }; const S={shake:0}; const sfx=()=>{}, spawnParticles=()=>{}, truckBumpH=()=>0; const TRUCK_SYS={hp:{land:{min:0.55,k:20}}}; let landDmg=0; const truckDamage=n=>{ landDmg+=n; }; // v0.78：高く跳んだ着地の傷み
  const groundH=(x,z)=>getGround()(x,z);
  const TRUCK={x:0,z:0,a:0,drive:true,susp:null};
  ${cfgSrc}
  ${suspSrc}
  return {TRUCK, truckSusp};`)(() => ground);
function ride(groundFn, speed, secs, z0 = 0) { ground = groundFn; Object.assign(SU.TRUCK, {x: 0, z: z0, a: 0, susp: null});
  const r = {maxUp: 0, air: 0, maxAir: 0, gfMin: 1, end: null}; let airT = 0;
  for (let k = 0; k < Math.round(secs / dt); k++) { SU.TRUCK.z += speed * dt; const B = SU.truckSusp(dt); const U = SU.TRUCK.susp;
    const gAvg = [-1.05, 1.05].reduce((a, lz) => a + ground(0, SU.TRUCK.z + lz), 0) / 2; r.maxUp = Math.max(r.maxUp, U.vY); r.lift = Math.max(r.lift || 0, B.Y - gAvg);
    if (U.air > 0) { airT += dt; r.maxAir = Math.max(r.maxAir, U.air); } r.gfMin = Math.min(r.gfMin, SU.TRUCK.gf); r.end = {vY: U.vY, Y: B.Y, g: gAvg, p: B.p}; }
  r.air = airT; return r; }
// 11) 平らな所に止めておくと、動かない
let r = ride(() => 0, 0, 3); check(Math.abs(r.end.Y) < 0.003 && Math.abs(r.end.vY) < 0.01 && r.air === 0, `平らな所では車体は沈みも浮きもしない（高さ ${r.end.Y.toFixed(4)}）`);
// 12) 15cm の段差を 36km/時で上る：跳ね上がって少し浮き、すぐ収まる
r = ride((x, z) => z > 5 ? 0.15 : 0, 10, 3);
check(r.maxUp > 0.5 && r.lift > 0.05, `15cm の段差を 36km/時で上ると跳ね上がる（上向きの速さ 最大 ${r.maxUp.toFixed(2)}m/秒・地面より ${(r.lift * 100).toFixed(0)}cm 上がる）`);
check(r.maxAir > 0.02, `そのとき少し浮く（最長 ${r.maxAir.toFixed(2)}秒）`);
check(Math.abs(r.end.vY) < 0.05 && Math.abs(r.end.Y - 0.15) < 0.02, `2秒ほどで揺れが収まる（高さ ${r.end.Y.toFixed(3)}m）`);
// 13) ゆっくり（7km/時）なら同じ段差でも浮かない
r = ride((x, z) => z > 3 ? 0.15 : 0, 2, 4);
check(r.air === 0, `ゆっくりなら同じ段差でも浮かない（浮いた時間 ${r.air.toFixed(2)}秒）`);
// 14) 坂（30%）を上りきった頂上を 50km/時で越えると浮く（坂の頂上で地面が下がっていくため）
r = ride((x, z) => z < 2 ? 0 : z < 8 ? (z - 2) * 0.3 : 1.8, 14, 3);
check(r.maxAir > 0.1, `坂（30%）の頂上を 50km/時で越えると浮く（最長 ${r.maxAir.toFixed(2)}秒・地面より ${(r.lift * 100).toFixed(0)}cm）`);
// 14b) 細い畦（幅0.5m・高さ12cm）を 50km/時で越える：1コマが長くても（0.05秒＝0.7m）見落とさずに跳ねる
{ ground = (x, z) => (z > 6 && z < 6.5) ? 0.12 : 0; Object.assign(SU.TRUCK, {x: 0, z: 0, a: 0, susp: null}); let up = 0;
  for (let k = 0; k < 40; k++) { SU.TRUCK.z += 14 * 0.05; SU.truckSusp(0.05); up = Math.max(up, SU.TRUCK.susp.vY); }
  check(up > 0.3, `細い畦を 50km/時で越えると、コマが粗くても跳ねる（上向きの速さ 最大 ${up.toFixed(2)}m/秒）`); }
// 15) 20cm 下がる段差：前の車輪が一瞬地面から離れる
r = ride((x, z) => z > 5 ? -0.2 : 0, 8, 2);
check(r.gfMin < 1, `20cm 下がる段差で前の車輪が一瞬浮く（前の車輪の接地 最小 ${r.gfMin}）`);
console.log(ok ? 'PASS: truck physics' : 'FAILED');
process.exit(ok ? 0 : 1);
