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
console.log(ok ? 'PASS: truck physics' : 'FAILED');
process.exit(ok ? 0 : 1);
