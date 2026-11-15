#!/usr/bin/env python3
"""v0.70（P2 作業E）スズキの仲間 AI の確認（画面のない Chromium。数分）。第1段階：ついて来る・移動・指示・地域の移動。

ゲームを一時停止にして、主人公の位置を決まった刻みで動かし、スズキの更新（updateSuzuki）を直接まわす。
- 本編では、仲間にならない限りスズキは出ない
- 仲間になると、主人公のすぐ後ろに出る
- ついて来る：歩く・走る主人公に遅れない。7m より遅れると速く走る。止まると、まわり6m を歩き回り、立ち止まる
- 家の向こうへ回り込む主人公について行ける（歩いた跡をたどる）。当たり判定の中に入らない
- 25m より離れると、主人公から見えない所へ移る（戦っている間は移らない）
- 指示：ここで待て（その場に残る）・ついて来い・拠点で過ごせ（拠点まで歩いて中を歩き回る）。「拠点で過ごせ」は光明寺だけ
- 地域を移る：ついて来ているスズキは一緒に移る。上志比で待たせると、光明寺へ戻っても上志比に残り、また行くと同じ所にいる
- エラーなし

使い方：THREE_JS=…/three.min.js python3 tests/suzuki-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SZ_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
KDATA = open(os.path.join(ROOT, 'data', 'kamishihi', 'kamishihi-map.js'), encoding='utf8').read()
MDATA = open(os.path.join(ROOT, 'data', 'models', 'mutant-monkey.js'), encoding='utf8').read()
HOOK = ("window.__w={get REG(){return REG},get P(){return P},get S(){return S},get prog(){return prog},get stats(){return stats},get enemies(){return enemies},"
        "get SZ(){return SZ},get SZA(){return SZA},get BASE(){return BASE},get PSPAWN(){return PSPAWN},oboxes,camera,"
        "regionTravel,updateSuzuki:dt=>updateSuzuki(dt),szJoin:()=>szJoin(),szOrder:k=>szOrder(k),szTalk:()=>szTalk(),szFree:(...a)=>szFree(...a),"
        "szWalkable:(...a)=>szWalkable(...a),szInView:(...a)=>szInView(...a),szFighting:()=>szFighting(),inBase:(...a)=>inBase(...a),"
        "setState:(e,s)=>setState(e,s),interactables:()=>interactables(),updateCamera:dt=>updateCamera(dt)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

# 主人公を道すじにそって speed で歩かせ、1コマごとにスズキを更新する。記録：主人公との最大の距離・当たり判定に入ったか・速さ
WALK = """async ([path, speed, tail]) => { const W = window.__w, P = W.P, SZ = W.SZ, dt = 1 / 30; let i = 0, x = path[0][0], z = path[0][1], maxD = 0, inside = 0, maxSpd = 0, n = 0, warps = 0, lastX = SZ.x, lastZ = SZ.z;
  P.x = x; P.z = z;
  const tick = (vx, vz) => { P.lvx48 = vx; P.lvz48 = vz; if (vx || vz) P.facing = Math.atan2(vx, vz); W.S.time += dt; W.updateSuzuki(dt); W.updateCamera(dt);
    const d = Math.hypot(SZ.x - P.x, SZ.z - P.z); if (d > maxD) maxD = d; if (!W.szFree(SZ.x, SZ.z, SZ.r * 0.7)) inside++; if (Math.hypot(SZ.x - lastX, SZ.z - lastZ) > 3) warps++; lastX = SZ.x; lastZ = SZ.z; if (SZ.spd > maxSpd) maxSpd = SZ.spd; n++; };
  for (let k = 1; k < path.length; k++) { const [bx, bz] = path[k]; let L = Math.hypot(bx - x, bz - z);
    while (L > 1e-6) { const s = Math.min(L, speed * dt), ux = (bx - x) / L, uz = (bz - z) / L; x += ux * s; z += uz * s; P.x = x; P.z = z; L -= s; tick(ux * speed, uz * speed); if (n % 60 === 0) await new Promise(r => setTimeout(r, 0)); } }
  for (let k = 0; k < (tail || 0); k++) { tick(0, 0); if (k % 60 === 0) await new Promise(r => setTimeout(r, 0)); }
  return {maxD: Math.round(maxD * 10) / 10, endD: Math.round(Math.hypot(SZ.x - P.x, SZ.z - P.z) * 10) / 10, inside, maxSpd: Math.round(maxSpd * 10) / 10, warps}; }"""
# 主人公は止めたまま、スズキだけ n コマ
IDLE = """async ([n]) => { const W = window.__w, P = W.P, SZ = W.SZ, dt = 1 / 30; let moved = 0, maxR = 0, still = 0, inside = 0; let lx = SZ.x, lz = SZ.z;
  for (let k = 0; k < n; k++) { P.lvx48 = 0; P.lvz48 = 0; W.S.time += dt; W.updateSuzuki(dt); W.updateCamera(dt); const m = Math.hypot(SZ.x - lx, SZ.z - lz); moved += m; if (m < 1e-4) still++; lx = SZ.x; lz = SZ.z;
    const r = Math.hypot(SZ.x - P.x, SZ.z - P.z); if (r > maxR) maxR = r; if (!W.szFree(SZ.x, SZ.z, SZ.r * 0.7)) inside++; if (k % 60 === 0) await new Promise(r => setTimeout(r, 0)); }
  return {moved: Math.round(moved * 10) / 10, maxR: Math.round(maxR * 10) / 10, still, inside, x: SZ.x, z: SZ.z}; }"""
# a から b まで歩ける道（0.5m の格子・スズキの当たり判定の調べ方）。端の点は近くの歩ける所へ寄せる
PATH = """([a, b, pad]) => { const W = window.__w; const free = (x, z) => W.szFree(x, z, 0.55) && W.szWalkable(x, z);
  const near = ([x, z]) => { if (free(x, z)) return [x, z]; for (let r = 0.5; r < 8; r += 0.5) for (let k = 0; k < 16; k++) { const a = k * Math.PI / 8, X = x + Math.sin(a) * r, Z = z + Math.cos(a) * r; if (free(X, Z)) return [X, Z]; } return null; };
  const A = near(a), B = near(b); if (!A || !B) return null; const G = 0.5, P0 = pad || 25, x0 = Math.min(A[0], B[0]) - P0, z0 = Math.min(A[1], B[1]) - P0, nx = Math.ceil((Math.abs(A[0] - B[0]) + 2 * P0) / G), nz = Math.ceil((Math.abs(A[1] - B[1]) + 2 * P0) / G);
  const key = (i, k) => k * nx + i, prev = new Int32Array(nx * nz).fill(-2); const si = Math.round((A[0] - x0) / G), sk = Math.round((A[1] - z0) / G), ti = Math.round((B[0] - x0) / G), tk = Math.round((B[1] - z0) / G);
  const q = [key(si, sk)]; prev[q[0]] = -1; let found = false;
  for (let h = 0; h < q.length && !found; h++) { const c = q[h], i = c % nx, k = (c / nx) | 0; for (const [di, dk] of [[1,0],[-1,0],[0,1],[0,-1]]) { const ni = i + di, nk = k + dk; if (ni < 0 || nk < 0 || ni >= nx || nk >= nz) continue; const n2 = key(ni, nk); if (prev[n2] !== -2) continue; if (!free(x0 + ni * G, z0 + nk * G)) continue; prev[n2] = c; if (ni === ti && nk === tk) { found = true; break; } q.push(n2); } }
  if (!found) return null; const path = []; for (let c = key(ti, tk); c !== -1; c = prev[c]) path.push([x0 + (c % nx) * G, z0 + ((c / nx) | 0) * G]); path.reverse();
  const simp = [path[0]]; for (let j = 4; j < path.length; j += 4) simp.push(path[j]); simp.push(path[path.length - 1]); return simp; }"""
# 家の両側に点をとり、家を回り込む道を 0.5m の格子で探す（スズキの当たり判定の調べ方で）
DETOUR = """() => { const W = window.__w, P = W.P; const free = (x, z) => W.szFree(x, z, 0.55) && W.szWalkable(x, z);
  for (const o of W.oboxes) { if (o.tag !== 'house' || !o.active || o.barri) continue; if (Math.hypot(o.x - W.PSPAWN.x, o.z - W.PSPAWN.z) > 220 || o.hx < 3 || o.hz < 2.5) continue;
    const ax = o.x + o.c * (o.hx + 4), az = o.z + o.s * (o.hx + 4), bx = o.x - o.c * (o.hx + 4), bz = o.z - o.s * (o.hx + 4);
    if (!free(ax, az) || !free(bx, bz)) continue;
    const G = 0.5, x0 = Math.min(ax, bx) - 30, z0 = Math.min(az, bz) - 30, nx = Math.ceil((Math.abs(ax - bx) + 60) / G), nz = Math.ceil((Math.abs(az - bz) + 60) / G);
    const key = (i, k) => k * nx + i, prev = new Int32Array(nx * nz).fill(-2); const si = Math.round((ax - x0) / G), sk = Math.round((az - z0) / G), ti = Math.round((bx - x0) / G), tk = Math.round((bz - z0) / G);
    const q = [key(si, sk)]; prev[q[0]] = -1; let found = false;
    for (let h = 0; h < q.length && !found; h++) { const c = q[h], i = c % nx, k = (c / nx) | 0; for (const [di, dk] of [[1,0],[-1,0],[0,1],[0,-1]]) { const ni = i + di, nk = k + dk; if (ni < 0 || nk < 0 || ni >= nx || nk >= nz) continue; const n2 = key(ni, nk); if (prev[n2] !== -2) continue; if (!free(x0 + ni * G, z0 + nk * G)) continue; prev[n2] = c; if (ni === ti && nk === tk) { found = true; break; } q.push(n2); } }
    if (!found) continue; const path = []; for (let c = key(ti, tk); c !== -1; c = prev[c]) path.push([x0 + (c % nx) * G, z0 + ((c / nx) | 0) * G]); path.reverse();
    const simp = [path[0]]; for (let j = 4; j < path.length; j += 4) simp.push(path[j]); simp.push(path[path.length - 1]);
    let L = 0; for (let j = 1; j < simp.length; j++) L += Math.hypot(simp[j][0] - simp[j - 1][0], simp[j][1] - simp[j - 1][1]);
    if (L < 2 * (o.hx + 4) + 6 || L > 90) continue; return {path: simp, house: [o.x, o.z], L: Math.round(L)}; }
  return null; }"""


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 960, 'height': 600})).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(r):
            u = r.request.url
            if 'three' in u: await r.fulfill(body=THREE, content_type='application/javascript')
            elif 'mutant-monkey.js' in u: await r.fulfill(body=MDATA, content_type='application/javascript')
            elif 'kamishihi-map.js' in u: await r.fulfill(body=KDATA, content_type='application/javascript')
            elif u.startswith('http://game.local'): await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            else: await r.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__w', timeout=300000)
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(1500)

        # ---- 本編では出ない ----
        R0 = await pg.evaluate("() => { const W = window.__w; return {joined: W.SZ.joined, model: !!(W.SZ.m && W.SZ.m.g.visible)}; }")
        check(not R0['joined'] and not R0['model'], f'本編では、仲間にならない限りスズキは出ない {R0}')

        # ---- 仲間になる ----
        await pg.evaluate("""() => { const W = window.__w; W.prog.bossDefeated = true; W.prog.stage = 'cleared'; W.prog.chapter2.unlocked = true; W.prog.chapter2.progress.defenseComplete = true;
          W.S.mode = 'paused'; for (const e of [...W.enemies]) { e.x += 3000; } W.P.x = 150; W.P.z = 40; W.P.facing = 0; W.szJoin(); }""")
        await pg.wait_for_timeout(300)
        R1 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ, P = W.P; return {d: Math.round(Math.hypot(SZ.x - P.x, SZ.z - P.z) * 10) / 10, front: Math.round(((SZ.x - P.x) * Math.sin(P.facing) + (SZ.z - P.z) * Math.cos(P.facing)) * 10) / 10, free: W.szFree(SZ.x, SZ.z, SZ.r)}; }")
        check(R1['d'] < 5 and R1['free'], f'仲間になると、主人公のすぐそば（後ろを優先）に出る {R1}')

        # ---- ついて来る（まっすぐ・歩き→走り）----
        P1 = await pg.evaluate(PATH, [[150, 40], [190, 75], 25])
        P2 = await pg.evaluate(PATH, [P1[-1], [150, 115], 25])
        await pg.evaluate("([x, z]) => { const W = window.__w; W.P.x = x; W.P.z = z; W.szJoin(); }", P1[0])
        W1 = await pg.evaluate(WALK, [P1, 3.0, 60])
        check(W1['maxD'] < 6.5 and W1['inside'] == 0 and W1['warps'] == 0, f'歩く主人公についていく（離れても 6.5m まで）{W1}')
        W2 = await pg.evaluate(WALK, [P2, 6.2, 90])
        check(W2['maxD'] < 9 and W2['endD'] < 5 and W2['inside'] == 0, f'走る主人公（6.2m/秒）に遅れない {W2}')
        R2 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ, P = W.P; SZ.x = P.x + 14; SZ.z = P.z; let mx = 0; for (let k = 0; k < 20; k++) { W.S.time += 1 / 30; W.updateSuzuki(1 / 30); if (SZ.spd > mx) mx = SZ.spd; } return mx; }""")
        check(R2 > 7.4, f'7m より遅れると速く走る（最大 {R2:.1f}m/秒）')
        # 止まると、まわりを歩き回る
        await pg.evaluate(IDLE, [90])  # 上で 14m 離したので、まず戻らせる
        I1 = await pg.evaluate(IDLE, [600])
        check(I1['moved'] > 3 and I1['maxR'] < 7.6 and I1['still'] > 120 and I1['inside'] == 0, f'止まると、まわり6m を歩き回り、ときどき立ち止まる（20秒）{I1}')

        # ---- 家を回り込む ----
        D = await pg.evaluate(DETOUR)
        check(D is not None, f'家を回り込む道が見つかる {None if D is None else (D["house"], D["L"])}')
        if D:
            await pg.evaluate("([x, z]) => { const W = window.__w; W.P.x = x; W.P.z = z; const SZ = W.SZ; SZ.x = x; SZ.z = z - 2.5; W.S.time += 10; }", D['path'][0])
            await pg.evaluate("([x, z]) => { const W = window.__w; W.szJoin(); }", D['path'][0])
            W3 = await pg.evaluate(WALK, [D['path'], 4.5, 150])
            check(W3['endD'] < 6 and W3['inside'] == 0 and W3['warps'] == 0, f'家の向こうへ回り込む主人公について行く（移されずに着く）{W3}')

        # ---- 25m 離れると見えない所へ移る ----
        R3 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ, P = W.P; P.x = 150; P.z = 70; P.facing = 0; for (let k = 0; k < 40; k++) W.updateCamera(1 / 30);
          SZ.x = P.x + 2; SZ.z = P.z + 40; SZ.order = 'follow'; W.S.time += 1 / 30; W.updateSuzuki(1 / 30); const d = Math.hypot(SZ.x - P.x, SZ.z - P.z);
          return {d: Math.round(d * 10) / 10, view: W.szInView(SZ.x, SZ.z), free: W.szFree(SZ.x, SZ.z, SZ.r)}; }""")
        check(R3['d'] < 17 and not R3['view'] and R3['free'], f'25m より離れると、主人公の近くの見えない所へ移る {R3}')
        R4 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ, P = W.P, e = W.enemies.find(e => !e.removed && e.state !== 'dead'); if (!e) return null; const ox = e.x, oz = e.z;
          e.x = P.x + 5; e.z = P.z; W.setState(e, 'chase'); SZ.x = P.x; SZ.z = P.z + 40; W.S.time += 1 / 30; W.updateSuzuki(1 / 30); const d = Math.hypot(SZ.x - P.x, SZ.z - P.z); e.x = ox; e.z = oz; W.setState(e, 'idle'); return {d: Math.round(d), fight: true}; }""")
        check(R4 is not None and R4['d'] > 30, f'戦っている間（近くに獣が向かってきている）は移らない {R4}')

        # ---- 指示 ----
        R5 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ, P = W.P; P.x = 150; P.z = 62; SZ.x = 150; SZ.z = 60.5; SZ.order = 'follow';
          const near = W.interactables(); const lab = near && near.label;
          W.szTalk(); const btn = [...document.querySelectorAll('#defenseChoice button')].map(b => b.textContent); const back = [...document.querySelectorAll('#defenseChoice button')].find(b => b.textContent === '戻る'); if (back) back.click();
          return {lab, btn, mode: W.S.mode}; }""")
        check(R5['lab'] == 'スズキに指示する' and R5['btn'][:3] == ['ついて来い（いまの指示）', 'ここで待て', '拠点で過ごせ'], f'近くで話しかけると、指示を選ぶ画面が出る（光明寺は3つ）{R5}')
        await pg.evaluate("() => { window.__w.S.mode = 'paused'; window.__w.szOrder('wait'); }")
        W4 = await pg.evaluate(WALK, [[[150, 70], [150, 95], [170, 95]], 5.0, 60])
        R6 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; return {d: Math.hypot(SZ.x - SZ.wx, SZ.z - SZ.wz), wx: SZ.wx, wz: SZ.wz}; }")
        check(R6['d'] < 1.0 and W4['endD'] > 20, f'ここで待て：主人公が離れても、その場に残る {R6} {W4["endD"]}')
        I2 = await pg.evaluate(IDLE, [200])
        check(I2['moved'] < 0.5, f'待っている間は歩き回らない {I2["moved"]}')
        await pg.evaluate("() => { window.__w.szOrder('follow'); }")
        I3 = await pg.evaluate(IDLE, [400])
        R7 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ, P = W.P; return Math.hypot(SZ.x - P.x, SZ.z - P.z); }")
        check(R7 < 7, f'ついて来い：主人公のそばへ戻る（{R7:.1f}m）')
        await pg.evaluate("() => { const W = window.__w; W.P.x = 150; W.P.z = 105; W.SZ.x = 150; W.SZ.z = 103; W.szOrder('base'); }")
        I4 = await pg.evaluate(IDLE, [900])
        R8 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; return {inBase: W.inBase(SZ.x, SZ.z, -3), x: SZ.x, z: SZ.z}; }")
        I5 = await pg.evaluate(IDLE, [900])
        R9 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; return W.inBase(SZ.x, SZ.z, -3); }")
        check(R8['inBase'] and R9 and I5['moved'] > 2 and I5['inside'] == 0, f'拠点で過ごせ：拠点まで歩き、中を歩き回る（30秒で {I5["moved"]}m）{R8}')

        # ---- 地域を移る ----
        await pg.evaluate("() => { const W = window.__w; W.szOrder('follow'); W.SZ.x = W.P.x + 1; W.SZ.z = W.P.z - 2; }")
        await pg.evaluate("async () => { const W = window.__w; await W.regionTravel('kamishihi', null, {force: true}); W.S.mode = 'paused'; }")
        await pg.wait_for_timeout(500)
        R10 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ, P = W.P; return {region: SZ.region, cur: W.REG.cur, d: Math.hypot(SZ.x - P.x, SZ.z - P.z), free: W.szFree(SZ.x, SZ.z, SZ.r), walk: W.szWalkable(SZ.x, SZ.z)}; }")
        check(R10['region'] == 'kamishihi' and R10['d'] < 7 and R10['free'] and R10['walk'], f'ついて来ているスズキは、上志比へ一緒に移る {R10}')
        R11 = await pg.evaluate("""() => { const W = window.__w, SZ = W.SZ, P = W.P; P.x = SZ.x + 1; P.z = SZ.z; W.szTalk(); const btn = [...document.querySelectorAll('#defenseChoice button')].map(b => b.textContent);
          const back = [...document.querySelectorAll('#defenseChoice button')].find(b => b.textContent === '戻る'); if (back) back.click(); W.S.mode = 'paused'; return btn; }""")
        check('拠点で過ごせ' not in R11 and len(R11) == 3, f'上志比では「拠点で過ごせ」を出さない {R11}')
        W5 = await pg.evaluate("async () => { const W = window.__w, P = W.P, x = P.x, z = P.z; return [[x, z], [x + 20, z], [x + 20, z + 1]]; }")
        W5r = await pg.evaluate(WALK, [W5, 4.0, 60])
        check(W5r['endD'] < 6 and W5r['inside'] == 0, f'上志比でもついて来る {W5r}')
        await pg.evaluate("() => { window.__w.szOrder('wait'); }")
        spot = await pg.evaluate("() => [window.__w.SZ.wx, window.__w.SZ.wz]")
        await pg.evaluate("async () => { const W = window.__w; await W.regionTravel('komyoji', null, {force: true}); W.S.mode = 'paused'; }")
        await pg.wait_for_timeout(500)
        R12 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; W.updateSuzuki(1 / 30); return {region: SZ.region, cur: W.REG.cur, vis: SZ.m.g.visible}; }")
        check(R12['region'] == 'kamishihi' and R12['cur'] == 'komyoji' and not R12['vis'], f'上志比で待たせると、光明寺へ戻っても上志比に残る（光明寺には出ない）{R12}')
        await pg.evaluate("async () => { const W = window.__w; await W.regionTravel('kamishihi', null, {force: true}); W.S.mode = 'paused'; }")
        await pg.wait_for_timeout(500)
        R13 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; W.updateSuzuki(1 / 30); return {region: SZ.region, x: SZ.x, z: SZ.z, vis: SZ.m.g.visible}; }")
        check(R13['region'] == 'kamishihi' and abs(R13['x'] - spot[0]) < 1 and abs(R13['z'] - spot[1]) < 1, f'また上志比へ行くと、待たせた所にいる {R13}')
        await pg.evaluate("async () => { const W = window.__w; await W.regionTravel('komyoji', null, {force: true}); }")

        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: suzuki ally stage 1' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
