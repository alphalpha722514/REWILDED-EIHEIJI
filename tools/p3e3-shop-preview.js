// 生成された検収用HTMLだけで使う。
const SHOP_PREVIEW = {busy: false, active: false, shelter: false};
const SHOP_PREVIEW_TIMES = [
  {phase: 'day', label: '昼', tod: () => 6 * P3B.hour},
  {phase: 'dusk', label: '夕方', tod: () => F10C.dusk + 1},
  {phase: 'night', label: '夜', tod: () => F10C.night + 1},
];

function shopPreviewDoor() {
  return P3A.doors.find(door => door.id === 'house110' && door.inId === 'shop');
}

function shopPreviewEntrance(door) {
  // 正面に立つ候補だけを試す。候補は本編の入口判定にも通る距離に収める。
  const forwardX = Math.sin(door.facing), forwardZ = Math.cos(door.facing);
  for (const forward of [1.65, 2.15, 1.35, 1, 2.35]) {
    for (const side of [0, 0.65, -0.65, 1, -1]) {
      const x = door.x + forward * forwardX + side * forwardZ;
      const z = door.z + forward * forwardZ - side * forwardX;
      if (szWalkable(x, z) && f4Free(x, z, P.r + 0.1)) return {x, z};
    }
  }
  return null;
}

function shopPreviewClock(time) {
  prog.f10.tod = time.tod();
  f10LightNow();
}

function shopPreviewShelter() {
  if (!SHOP_PREVIEW.active || REG.cur !== 'kamishihi') return;
  const door = shopPreviewDoor();
  const near = door && (P3A.inside ? P3A.inId === 'shop' : dist(P.x, P.z, door.x, door.z) < 35);
  if (near) {
    stfHoldBeasts(door);
    SHOP_PREVIEW.shelter = true;
  } else if (SHOP_PREVIEW.shelter) {
    stfRelease();
    SHOP_PREVIEW.shelter = false;
  }
}

async function shopPreviewStart() {
  if (SHOP_PREVIEW.busy || REG.busy || P3A.busy) return;
  SHOP_PREVIEW.busy = true;
  try {
    audioInit(); regionResetHome(); freshState(); resetWorld(null); hideAllOv();
    $('hud').hidden = false; S.mode = 'playing'; cv.focus();
    Object.assign(prog, {bossDefeated: true, stage: 'cleared', unlockTrap: true, unlockBoss: true, introSeen: true});
    prog.chapter2 = chapter2State(null, true);
    prog.chapter2.currentChapter = 2;
    Object.assign(prog.chapter2.progress, {
      openingStarted: true, defenseComplete: true, defenseRewarded: true, radioHeard: true,
      departureDecision: true, departureComplete: true, mutantMet: true,
    });
    Object.assign(trk(), {found: true, repaired: true, fueled: true, parts: ['p1', 'p2'],
      trips: 1, region: 'komyoji', lv: 4, gas: 100});
    TRUCK.sync = false;
    const {hq, e3} = p3bState();
    Object.assign(hq, {sv: [1, 1, 1], talk: 1, plan: 1, visited: 1, beasts: 1});
    e3.farm = e3.map = e3.s[7] = 1;
    szJoin();
    SHOP_PREVIEW.active = true;
    SHOP_PREVIEW.shelter = false;
    if (!(await regionTravel('kamishihi', null, {force: true}))) return;
    const door = shopPreviewDoor(), point = door && shopPreviewEntrance(door);
    if (!point) {
      toast('よろず屋の入口前に立てる場所が見つかりませんでした', true);
      return;
    }
    P.x = P._px = point.x; P.z = P._pz = point.z; P.lvx48 = P.lvz48 = 0;
    P.facing = Math.atan2(door.x - point.x, door.z - point.z);
    setCam(P.facing);
    shopPreviewShelter(); p3aSzFollow();
    resetWeather(); shopPreviewClock(SHOP_PREVIEW_TIMES[0]);
    saveGame();
    toast('古い地図を取得済みです。「調べる」でよろず屋に入れます');
  } finally {
    SHOP_PREVIEW.busy = false;
  }
}

function shopPreviewCanOrder() {
  return SHOP_PREVIEW.active && S.mode === 'paused' && szHere() && !SZ.down && !SZ.upT;
}

function shopPreviewRefresh() {
  const order = $('shopPreviewSuzuki');
  order.disabled = !shopPreviewCanOrder();
  order.textContent = !szHere() ? 'スズキ：別の場所' : SZ.down ? 'スズキ：転倒中' :
    SZ.order === 'follow' ? 'スズキ：ここで待つ' : 'スズキ：ついて来る';
  const phase = SHOP_PREVIEW_TIMES.find(time => time.phase === f10Phase());
  $('shopPreviewTime').textContent = '時刻：' + (phase?.label ?? '明け方');
}

$('shopPreviewSuzuki').onclick = () => {
  if (!shopPreviewCanOrder()) return;
  szOrder(SZ.order === 'follow' ? 'wait' : 'follow');
  saveGame();
  shopPreviewRefresh();
};
$('shopPreviewTime').onclick = () => {
  if (!SHOP_PREVIEW.active || S.mode !== 'paused') return;
  const current = SHOP_PREVIEW_TIMES.findIndex(time => time.phase === f10Phase());
  shopPreviewClock(SHOP_PREVIEW_TIMES[(current + 1) % SHOP_PREVIEW_TIMES.length]);
  saveGame();
  shopPreviewRefresh();
};
