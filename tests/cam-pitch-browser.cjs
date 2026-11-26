#!/usr/bin/env node
// THREE_JS と CAM_SHOTS は必要なときだけ指定する。
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const ROOT = path.dirname(__dirname);
const OLD_REF = 'bdc2a1e263502f2518129908e3edc77dc858ece3';
function loadOldCamera() {
  let html;
  try {
    html = process.env.OLD_HTML
      ? fs.readFileSync(path.resolve(ROOT, process.env.OLD_HTML), 'utf8')
      : execFileSync('git', ['show', `${OLD_REF}:index.html`], {
        cwd: ROOT, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024, stdio: ['ignore', 'pipe', 'pipe'],
      });
    const source = html.match(/^function updateCamera\(dt\)\{[\s\S]*?^\}/m);
    if (!source) throw new Error('updateCamera が見つかりません。');
    return source[0].replace('function updateCamera(', 'function oldUpdateCamera(');
  } catch (error) {
    console.error(`比較用の旧版 (${OLD_REF}) を読み込めませんでした。 ${error.message}`);
    console.error('固定コミットを参照できる作業コピーで実行するか、同じ版の index.html を OLD_HTML= で指定してください。');
    process.exit(1);
  }
}
const oldCamera = loadOldCamera();
const { chromium } = require('playwright');
const THREE = fs.readFileSync(process.env.THREE_JS || '/home/claude/v010/node_modules/three/build/three.min.js');
const HTML = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8')
  .replace('  const hit=playing?camObstruct', '  window.__candidate={D,Hh,bx,byy,bz};\n  const hit=playing?camObstruct')
  .replace('function updateNPCs(dt){', () => `${oldCamera}\nwindow.__ev=s=>eval(s);\nfunction updateNPCs(dt){`);
const BASE = `(() => {
  prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); prog.chapter2.currentChapter=2;
  const p=prog.chapter2.progress;
  Object.assign(p,{openingStarted:true,defenseComplete:true,defenseRewarded:true,radioHeard:true,departureDecision:true,departureComplete:true});
  p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  TRUCK.sync=false; P.atk=null;
  camFoe=()=>null;
})()`;
const SAME_CAMERA = `(() => {
  if(S.mode!=='playing'||cam.override||bossCinema52()) return false;
  const dt=1/60;
  const config={...cam,pitch:{...cam.pitch}};
  const vectors=[cam.pos,cam.look,_cv,_lv,camera.position];
  const saved=vectors.map(v=>v.clone());
  const rotation=camera.quaternion.clone(), fov=camera.fov;
  const shake=S.shake, ground52=S.ground52, air52=S.air52;
  const restore=()=>{
    Object.assign(cam,config,{pitch:{...config.pitch}});
    vectors.forEach((v,i)=>v.copy(saved[i]));
    camera.quaternion.copy(rotation);
    camera.fov=fov;
    camera.updateProjectionMatrix();
    S.shake=shake; S.ground52=ground52; S.air52=air52;
  };
  const step=update=>{
    cam.pitch[camPitchScene()]=0; cam.dragDY=0;
    S.shake=0; S.ground52=0; S.air52=0;
    update(dt);
    return [..._cv.toArray(),..._lv.toArray(),...camera.position.toArray()];
  };
  try {
    const current=step(updateCamera);
    restore();
    const old=step(oldUpdateCamera);
    return current.every((n,i)=>Math.abs(n-old[i])<=1e-6);
  } finally {
    restore();
  }
})()`;
const ROOF_VIEW = `(x,z,yaw)=> {
  Object.assign(P,{x,z});
  cam.yaw=yaw; cam.manualT=10; cam.dragDY=0;
  const keep=cam.pitch.out;
  try {
    cam.pitch.out=0;
    updateCamera(1/60);
    const standard=Math.atan2(__candidate.Hh-1.3,__candidate.D);
    const requested=60*CAM_DEG-standard;
    cam.pitch.out=requested;
    updateCamera(1/60);
    const actual=Math.atan2(__candidate.Hh-1.3,__candidate.D);
    return cam.pitch.out===requested && actual>=standard-1e-6 && actual<60*CAM_DEG-1e-6;
  } finally {
    cam.pitch.out=keep;
  }
}`;
const RANGE = { out: [-10, 60], in: [35, 80], truck: [8, 40] };
const ZERO = 'Object.values(cam.pitch).every(v=>v===0)';
const near = (a, b) => Math.abs(a - b) < 1e-6;

async function run() {
  let ok = true;
  const check = (condition, message) => {
    console.log((condition ? 'ok   ' : 'FAIL ') + message);
    ok = ok && !!condition;
  };
  const browser = await chromium.launch({
    executablePath: process.env.CHROMIUM_PATH || undefined,
    args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
  });
  const errors = [];
  const shots = process.env.CAM_SHOTS;
  if (shots) fs.mkdirSync(shots, { recursive: true });
  async function open(touch) {
    const ctx = await browser.newContext({
      viewport: touch ? { width: 390, height: 844 } : { width: 1280, height: 720 },
      hasTouch: touch, isMobile: touch,
    });
    await ctx.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.pathname.endsWith('/three.min.js')) return route.fulfill({ body: THREE, contentType: 'application/javascript' });
      if (url.origin !== 'http://game.local') return route.abort();
      if (['/', '/index.html'].includes(url.pathname)) return route.fulfill({ body: HTML, contentType: 'text/html; charset=utf-8' });
      const file = path.resolve(ROOT, '.' + decodeURIComponent(url.pathname));
      if (file.startsWith(ROOT + path.sep) && fs.existsSync(file) && fs.statSync(file).isFile()) return route.fulfill({ path: file });
      return route.fulfill({ status: 404, body: '' });
    });
    const page = await ctx.newPage();
    page.on('pageerror', error => errors.push(String(error)));
    const E = code => page.evaluate(code => window.__ev(code), code);
    const until = code => page.waitForFunction(code => window.__ev(code), code, { timeout: 180000, polling: 100 });
    const wait = async seconds => until(`stats.time>=${await E('stats.time') + seconds}`);
    const ready = async () => {
      await page.goto('http://game.local/', { timeout: 180000 });
      await until("typeof window.__ev==='function'");
    };
    const start = async () => {
      await page.click('#btnNew');
      await E('while(S.mode==="dialog"&&dlgQueue.length<10) nextDialog()');
      await until("S.mode==='playing'");
      await E(BASE);
      await wait(0.04);
    };
    const travel = async id => {
      if (!await E(`regionTravel('${id}',null,{force:true})`)) throw new Error(`地域移動に失敗（${id}）`);
      await until(`REG.cur==='${id}'&&!REG.busy&&S.mode==='playing'`);
    };
    const angle = () => E('Math.atan2(__candidate.Hh-1.3,__candidate.D)/CAM_DEG');
    const pitch = () => E('cam.pitch[camPitchScene()]');
    const reset = () => E('resetCamPitch(); cam.yaw=0; cam.manualT=10; P.atk=null; cam.atkK=0');
    return { ctx, page, E, wait, until, ready, start, travel, angle, pitch, reset, touch };
  }

  async function capture(g, spot) {
    if (!shots) return;
    for (const [name, drag] of [['standard', 0], ['up', -4000], ['down', 4000]]) {
      await g.E(`cam.pitch[camPitchScene()]=0; cam.dragDY=${drag}; cam.init=false`);
      await g.wait(0.35);
      await g.page.screenshot({ path: path.join(shots, `${g.touch ? 'iphone' : 'pc'}-${spot}-${name}.png`) });
    }
  }
  async function limits(g, scene) {
    const [min, max] = RANGE[scene];
    for (const [drag, target] of [[-4000, min], [4000, max]]) {
      const result = await g.E(`cam.dragDY=${drag}; updateCamera(1/60); Math.atan2(__candidate.Hh-1.3,__candidate.D)/CAM_DEG`);
      check(near(result, target), `${scene} の仰角が ${target}° で止まる（${result}）`);
    }
  }
  async function spots(g) {
    const { E, travel } = g;
    if (!g.touch) await E('cam.pitch.out=0.12');
    await travel('kamishihi');
    if (!g.touch) {
      check(await E('cam.pitch.out===0.12'), '地域移動で屋外の角度を保持');
      check(await E(SAME_CAMERA), '上志比の到着地点の標準構図は旧式と一致');
    }
    const farm = await E("P3A.doors.find(d=>d.inId==='farm')");
    if (!farm) throw new Error('古い農家の入口が見つからない');
    const locations = await E(`(() => {
      const candidates=[];
      for(const trees of E2.grid.values()){
        const [x,z]=trees[0];
        if(kamiReach(x+2,z+2)&&kamiCls(x+2,z+2)!==2) candidates.push({x:x+2,z:z+2});
        if(candidates.length>=200) break;
      }
      const slope=({x,z})=>Math.abs(groundH(x+4,z)-groundH(x-4,z))+Math.abs(groundH(x,z+4)-groundH(x,z-4));
      return { forest:candidates[0], slope:candidates.sort((a,b)=>slope(b)-slope(a))[0] };
    })()`);
    check(await E(`(() => {
      const door=P3A.doors.find(d=>d.id==='house26');
      const house=KAMI.D.bld[26];
      return (${ROOF_VIEW})(door.x,door.z,Math.atan2(house[0]-door.x,house[1]-door.z));
    })()`), `${g.touch ? 'スマホ' : 'PC'} の house26 の入口で見下ろしを抑え、角度差を保持`);
    locations.building = { x: farm.x, z: farm.z };
    for (const [name, { x, z }] of Object.entries(locations)) {
      await E(`P.x=${x}; P.z=${z}; setCam(0)`);
      if (!g.touch) {
        check(await E(`(() => {
          const keep=cam.pitch.out;
          for(const yaw of [0,1.5,3,4.5]){
            cam.yaw=yaw; cam.dragDY=-4000;
            for(let i=0;i<20;i++){
              updateCamera(1/60);
              if(cam.pos.y<groundH(cam.pos.x,cam.pos.z)+0.4-1e-8) return false;
            }
          }
          cam.pitch.out=keep;
          return true;
        })()`), `${name} の見上げで地面との間を保つ`);
      }
      await capture(g, name);
    }
    await E("cam.pitch.out=0.12; p3aEnter(P3A.doors.find(d=>d.inId==='farm'))");
    await g.until("S.mode==='playing'&&!P3A.busy");
    if (!g.touch) {
      check(await E("camPitchScene()==='in'&&cam.pitch.in===0") && await E(SAME_CAMERA), '古い農家の標準構図は旧式と一致');
      await limits(g, 'in');
      for (const [drag, label] of [[-4000, '見上げ'], [4000, '見下ろし']]) {
        check(await E(`(() => {
          for(const yaw of [0,1.5,3,4.5]){
            cam.yaw=yaw; cam.dragDY=${drag};
            for(let i=0;i<25;i++){
              updateCamera(1/60);
              const {x,y,z}=cam.pos;
              if(P3A.interior.cols.some(c=>c.active&&x>c.minX&&x<c.maxX&&z>c.minZ&&z<c.maxZ&&y<c.h)) return false;
            }
          }
          return true;
        })()`), `古い農家の${label}で壁の当たりに入らない`);
      }
    }
    await capture(g, 'farm');
    if (!g.touch) await E('cam.pitch.in=0.19');
    await E('p3aExit()');
    if (!g.touch) check(await E("camPitchScene()==='out'&&cam.pitch.out===0.12&&cam.pitch.in===0.19"), '屋内から出ると屋外の角度に復帰');
    if (!g.touch) {
      await E("p3aEnter(P3A.doors.find(d=>d.inId==='farm'))");
      check(await E("camPitchScene()==='in'&&cam.pitch.in===0.19"), '入り直すと屋内の角度に復帰');
      await E('p3aExit()');
    }
    await travel('komyoji');
    if (!g.touch) {
      const view = await E('[P.x,P.z,cam.yaw,cam.manualT]');
      check(await E(`(() => {
        const [x,z]=M(0,68.5);
        return (${ROOF_VIEW})(x,z+4.5/2+0.8,Math.PI);
      })()`), '光明寺の集会所の入口で見下ろしを抑え、角度差を保持');
      await E(`P.x=${view[0]}; P.z=${view[1]}; cam.yaw=${view[2]}; cam.manualT=${view[3]}; cam.init=false`);
    }
    await E('truckLoadPos(); truckBoard()');
    if (!g.touch) {
      check(await E("camPitchScene()==='truck'") && await E(SAME_CAMERA), '運転中の標準構図は旧式と一致');
      await limits(g, 'truck');
    }
    await capture(g, 'truck');
    await E('cam.pitch.truck=0.15; truckExit(true)');
    if (!g.touch) {
      check(await E("camPitchScene()==='out'&&cam.pitch.out===0.12"), '降りると屋外の角度に復帰');
      await E('truckBoard()');
      check(await E("camPitchScene()==='truck'&&cam.pitch.truck===0.15"), '乗り直すと運転中の角度に復帰');
      await E('truckExit(true)');
    }
  }

  try {
    const pc = await open(false);
    const { page, E, wait, reset, pitch } = pc;
    await pc.ready();
    check(await E("camPitchSettings.sens==='std'&&!camPitchSettings.inv"), '設定なしで標準・オフ');
    await E("localStorage.setItem(CAM_PITCH_KEY,'{broken')");
    await pc.ready();
    check(await E("camPitchSettings.sens==='std'&&!camPitchSettings.inv"), '壊れた設定で標準・オフ');
    await pc.start();
    await reset();
    async function drag(dx, dy) {
      await page.mouse.move(600, 350);
      await page.mouse.down({ button: 'middle' });
      await page.mouse.move(600 + dx, 350 + dy);
      await page.mouse.up({ button: 'middle' });
      await wait(0.05);
    }
    await drag(0, -40);
    check(near(await pitch(), -40 * 0.0065 * 0.6) && await E('cam.manualT>8'), '中ボタンを上へ動かすと見上げ、横の追従タイマーはそのまま');
    await drag(30, 0);
    check(near(await E('cam.yaw'), -30 * 0.0065), '中ボタンの横回転は従来の感度');
    check(await E(`(() => {
      window.dispatchEvent(new KeyboardEvent('keydown',{key:'c',code:'KeyC'}));
      const centered=cam.pitch[camPitchScene()]===0&&Math.abs(angDiff(cam.yaw,P.facing))<1e-6;
      window.dispatchEvent(new KeyboardEvent('keyup',{key:'c',code:'KeyC'}));
      return centered;
    })()`), 'C で背後と標準の角度へ');
    for (const [label, gain] of [['高', 1.5], ['低', 0.6], ['標準', 1]]) {
      await page.keyboard.press('Escape');
      await page.click('#camPitchSens');
      check((await page.textContent('#camPitchSens')).endsWith(label), `感度ボタンを押すと「${label}」`);
      await page.click('#btnResume');
      await reset();
      await drag(0, -40);
      check(near(await pitch(), -40 * 0.0065 * 0.6 * gain), `感度「${label}」の倍率は ${gain}`);
    }
    await page.keyboard.press('Escape');
    await page.click('#camPitchInv');
    await page.click('#btnResume');
    await reset();
    await drag(0, -40);
    check(near(await pitch(), 40 * 0.0065 * 0.6), '反転オンで中ボタンの上下が逆になる');
    for (const [key, sign] of [['x', -1], ['z', 1]]) {
      await reset();
      await page.keyboard.down(key);
      await wait(0.1);
      await page.keyboard.up(key);
      check((await pitch()) * sign > 0.06, `反転オンでも ${key.toUpperCase()} の向きは同じ`);
    }
    await page.keyboard.press('Escape');
    await page.click('#camPitchInv');
    await page.click('#btnResume');
    await limits(pc, 'out');
    check(await E(`(() => {
      keys.add('w'); cam.manualT=10;
      cam.pitch.out=0; const movement=inputWorld(), attack=attackAimNow();
      cam.pitch.out=0.4; updateCamera(1/60);
      const equal=JSON.stringify(inputWorld())===JSON.stringify(movement)&&attackAimNow()===attack;
      keys.delete('w'); return equal;
    })()`), '角度を変えても移動と移動中の攻撃方向が一致');
    check(await E(`(() => {
      AIM.mode='cursor'; mouse.active=true; cam.init=false; cam.pitch.out=0;
      updateCamera(1/60); camera.updateMatrixWorld();
      let found=false;
      for(let y=0;y<=innerHeight;y+=20) for(let x=0;x<=innerWidth;x+=60){
        mouse.x=x; mouse.y=y;
        const g=mouseGround();
        if(!g) continue;
        const dx=g.x-P.x,dz=g.z-P.z,d2=dx*dx+dz*dz;
        if(d2>0.04&&d2<6400){ found=true; if(aimAngle()!==Math.atan2(dx,dz)) return false; }
      }
      return found;
    })()`), '旧式で交点が取れるカーソル照準は一致');
    check(await E(`(() => {
      cam.dragDY=-4000; cam.init=false; updateCamera(1/60); camera.updateMatrixWorld();
      mouse.y=0; mouse.x=innerWidth/2; feetPlane.constant=-groundH(P.x,P.z);
      return mouseGroundAngle(mouseGround())===null&&mouseGroundAngle(mouseGround(feetPlane))===null&&aimAngle()===(autoAim()??P.facing);
    })()`), '見上げて交点がない場合は自動照準か向きに戻る');
    check(await E(`(() => {
      const realHeight=REG.hfn, realX=P.x;
      try{
        REG.hfn=()=>10; P.x=REGION_X0+100;
        camera.position.set(P.x,14,P.z+2);
        camera.lookAt(P.x,13.8,P.z);
        camera.updateMatrixWorld();
        mouse.x=innerWidth/2; mouse.y=innerHeight/2;
        const old=mouseGroundAngle(mouseGround());
        feetPlane.constant=-10;
        const feet=mouseGroundAngle(mouseGround(feetPlane));
        return old===null&&feet!==null&&aimAngle()===feet;
      }finally{ REG.hfn=realHeight; P.x=realX; }
    })()`), '高さ0の交点が遠い場合は足元の高さで照準を取れる');
    for (const mode of ['override', 'dialog']) {
      await reset();
      await E(mode === 'override'
        ? 'cam.override={p:cam.pos.clone(),l:cam.look.clone(),fov:64}'
        : "queueDialog([[null,'上下入力の確認']])");
      await page.keyboard.press('x');
      // 会話を閉じず、中ボタン移動のイベントだけを送る。
      await E("cv.dispatchEvent(new PointerEvent('pointermove',{pointerType:'mouse',buttons:4,movementY:-40})); updateCamera(1/60)");
      await E(mode === 'override' ? 'cam.override=null' : 'nextDialog()');
      await wait(0.08);
      check(await pitch() === 0 && await E('cam.dragDY===0'), `${mode} の上下入力を終了後に持ち越さない`);
    }
    await spots(pc);
    await E("saveGame()");
    check(await E("!/(camPitch|pitch|dragDY)/i.test(localStorage.getItem(SAVE_KEY))"), 'ゲームのセーブに上下の値が入らない');
    await page.keyboard.press('Escape');
    await page.click('#camPitchSens');
    await page.click('#camPitchInv');
    check(await E("localStorage.getItem(CAM_PITCH_KEY)==='{\"v\":1,\"sens\":\"high\",\"inv\":true}'"), '感度と反転を専用キーに保存');
    await page.click('#btnToTitle');
    check(await E(ZERO), 'タイトルへ戻ると全場面が標準');
    await pc.ready();
    check(await E("camPitchSettings.sens==='high'&&camPitchSettings.inv"), '再読み込みで設定を復元');
    await E('Object.assign(cam.pitch,{out:0.1,in:0.2,truck:0.3})');
    await page.click('#btnContinue');
    await pc.until("S.mode==='playing'");
    check(await E(ZERO), 'つづきからで全場面が標準');
    await E('cam.pitch.out=0.3; openPause()');
    await page.click('#btnToTitle');
    await E('Object.assign(cam.pitch,{out:0.1,in:0.2,truck:0.3})');
    await pc.start();
    check(await E(ZERO), '新しく始めると全場面が標準');
    await pc.ctx.close();

    const mobile = await open(true);
    await mobile.ready();
    await mobile.start();
    const touch = await mobile.ctx.newCDPSession(mobile.page);
    const send = (type, points) => touch.send('Input.dispatchTouchEvent', { type, touchPoints: points });
    const origin = { x: 260, y: 350, id: 1 };
    async function swipe(dx, dy, left = false) {
      await mobile.reset();
      const other = { x: 80, y: 590, id: 2 };
      await send('touchStart', [origin]);
      if (left) {
        await send('touchStart', [origin, other]);
        other.y -= 45;
      }
      await send('touchMove', [{ ...origin, x: origin.x + dx, y: origin.y + dy }, ...(left ? [other] : [])]);
      await mobile.wait(0.05);
      const state = await mobile.E('({pitch:cam.pitch.out,yaw:cam.yaw,moving:inputWorld().mag>0&&joy.id!==null})');
      await send('touchEnd', []);
      return state;
    }
    for (const [dx, dy, left, label] of [[0, -55, false, '縦'], [55, 0, false, '横'], [45, -45, true, '斜めと左の移動'], [45, 3, false, '最初の小さな縦ぶれ']]) {
      const state = await swipe(dx, dy, left);
      check(near(state.pitch, (dy===3?0:dy)*1.3*0.0065*0.6) && near(state.yaw, -dx*1.3*0.0065)
        && state.moving===left, `スマホの${label}（${JSON.stringify(state)}）`);
    }
    await mobile.reset();
    await send('touchStart', [origin]);
    await send('touchMove', [{ ...origin, x: 282, y: 352 }]);
    await send('touchMove', [{ ...origin, x: 302, y: 355 }]);
    await mobile.wait(0.05);
    check(near(await mobile.pitch(), 3*1.3*0.0065*0.6), '約10pxを過ぎると小さな縦移動も反映');
    await send('touchEnd', []);
    await mobile.reset();
    await mobile.page.tap('#tbAtk');
    await mobile.wait(0.05);
    check(await mobile.E('cam.pitch.out===0&&cam.yaw===0&&cz.id===null'), '攻撃ボタンはカメラの操作と競合しない');
    for (const viewport of [{ width: 390, height: 844 }, { width: 844, height: 390 }]) {
      await mobile.page.setViewportSize(viewport);
      await mobile.E('openPause()');
      const inv = await mobile.E('camPitchSettings.inv');
      await mobile.page.tap('#camPitchSens');
      await mobile.page.tap('#camPitchInv');
      check(await mobile.E(`camPitchSettings.sens!=='std'&&camPitchSettings.inv!==${inv}`), `スマホの ${viewport.width}×${viewport.height} で設定ボタンに届く`);
      await mobile.page.tap('#btnResume');
    }
    if (shots) {
      await mobile.page.setViewportSize({ width: 390, height: 844 });
      await mobile.E("camPitchSettings.inv=false");
      await spots(mobile);
    }
    check(errors.length === 0, `ページのエラーなし ${errors.join(' / ')}`);
  } finally {
    await browser.close();
  }
  console.log(ok ? 'PASS 三人称カメラの上下操作' : 'FAILED');
  process.exitCode = ok ? 0 : 1;
}

run().catch(error => {
  console.error('FAIL 三人称カメラの上下操作', error);
  process.exitCode = 1;
});
