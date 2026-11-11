// v0.58: 攻撃の向き（移動入力があればその方向へ。±40°以内・届く獣へ狙いを合わせる）と当たりの広さ
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname, '../index.html'), 'utf8');
const grab = name => { const i = html.indexOf(`function ${name}(`); assert.ok(i >= 0, name); return html.slice(i, html.indexOf('\n}', i) + 2); };
const ctx = vm.createContext({ Math });
vm.runInContext(`
const P={x:0,z:0,facing:0}, AIM={mode:'cursor'}, mouse={active:false};
let input={x:0,z:0,mag:0}, enemies=[], cursorAim=-1, autoA=null;
const inputWorld=()=>input, equippedWeapon=()=>({range:3.3}), dist=(a,b,c,d)=>Math.hypot(a-c,b-d);
const angDiff=(a,b)=>{ let d=b-a; while(d>Math.PI)d-=2*Math.PI; while(d<-Math.PI)d+=2*Math.PI; return d; };
const aimAngle=()=>AIM.mode==='cursor'&&mouse.active?cursorAim:(autoA??P.facing);
${grab('assistAim')}
${grab('attackAimNow')}
`, ctx);
const run = s => vm.runInContext(s, ctx);
const near = (a, b) => Math.abs(a - b) < 1e-6;
// 移動入力が東なら、押した瞬間の向き（北）より入力を優先
run('input={x:1,z:0,mag:1}');
assert.ok(near(run('attackAimNow(0)'), Math.PI / 2), 'movement input wins over the click-time aim');
// カーソル操作中でも、移動入力があれば入力の方向
run('mouse.active=true');
assert.ok(near(run('attackAimNow(0)'), Math.PI / 2), 'movement input wins over the cursor');
// 入力の向きから 30° ずれた所に届く獣がいれば、その獣へ合わせる
run("enemies=[{x:Math.sin(Math.PI/2+0.5)*2.5,z:Math.cos(Math.PI/2+0.5)*2.5,r:0.45,state:'idle'}]");
assert.ok(near(run('attackAimNow(0)'), Math.PI / 2 + 0.5), 'assist snaps to a beast within ±40°');
// 60° ずれた獣には合わせない
run("enemies=[{x:Math.sin(Math.PI/2+1.05)*2.5,z:Math.cos(Math.PI/2+1.05)*2.5,r:0.45,state:'idle'}]");
assert.ok(near(run('attackAimNow(0)'), Math.PI / 2), 'no assist beyond ±40°');
// 移動入力がなければ、カーソル操作中は「技が出る瞬間」のカーソル
run('input={x:0,z:0,mag:0}; enemies=[]; cursorAim=2.2');
assert.ok(near(run('attackAimNow(0)'), 2.2), 'live cursor when not moving');
// 移動入力もカーソルもなければ、押した瞬間の向き
run('mouse.active=false');
assert.ok(near(run('attackAimNow(0.7)'), 0.7), 'click-time aim otherwise');
// 当たりの広さ（v0.58）
assert.match(html, /const SHAPE_T=\{slash:0\.32,blunt:0\.4,thrust:0\.36,low:0\.36,spin:0\.3\}/);
assert.match(html, /bx\+=\(tx-bx\)\*0\.3;/, 'spear uses the tip-side 70% of the shaft');
console.log('PASS: attack aim follows movement input, ±40° assist, live cursor, click-time fallback; wider hit shapes');
