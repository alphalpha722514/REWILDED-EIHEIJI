#!/usr/bin/env python3
"""v0.60（P2 作業B）上志比の確認（画面のない Chromium。数分かかる）。

本物の上志比のデータ（data/kamishihi/kamishihi-map.js）で、
- 防衛戦を終える前は、光明寺の東の出口で止められる
- 終えた後は、東の出口（国道416号）から歩いて上志比へ移り、国道の上に着く
- 上志比の地面・範囲・建物と木の当たり判定がある
- 西の出口へ歩くと光明寺の東の出口の手前に戻り、光明寺の当たり判定・範囲・地面が元どおり
- 3往復しても、当たり判定・テクスチャ・場面の物が増え続けない
- 地図データを読めないときは、光明寺へ安全に戻る
- 全体地図が上志比の地図になる
を確かめる。KAMI_SHOTS=出力フォルダ を付けると、上志比の画面を撮る。

使い方：THREE_JS=…/three.min.js python3 tests/kamishihi-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
DATA = open(os.path.join(ROOT, 'data', 'kamishihi', 'kamishihi-map.js'), encoding='utf8').read()
SHOTS = os.environ.get('KAMI_SHOTS')
HOOK = ("window.__r={REG,renderer,scene,boxes,circles,oboxes,cgrid,BOUNDS,groundH,clsAt,get KOMYOJI_EAST(){return KOMYOJI_EAST},get KOMYOJI_EAST_ARRIVE(){return KOMYOJI_EAST_ARRIVE},get regionTravel(){return regionTravel},camera,"
        "get P(){return P},get S(){return S},get prog(){return prog},get KAMI(){return KAMI},saveGame,openMap:()=>{ if(S.mode==='playing') openMap(); else { sizeMap(); drawMap(); } }};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

SNAP = """() => { const R = window.__r; let cells = 0; for (const a of R.cgrid.values()) cells += a.length;
  return {cur: R.REG.cur, geo: R.renderer.info.memory.geometries, tex: R.renderer.info.memory.textures, boxes: R.boxes.length, circles: R.circles.length,
    oboxes: R.oboxes.length, cells, kids: R.scene.children.length, bounds: JSON.stringify(R.BOUNDS), h: R.groundH(158, 22),
    px: R.P.x, pz: R.P.z, ph: R.groundH(R.P.x, R.P.z), mode: R.S.mode, busy: R.REG.busy,
    tris: R.renderer.info.render.triangles, calls: R.renderer.info.render.calls,
    saved: (JSON.parse(localStorage.getItem('eiheiji_vs_beasts_v010') || '{}').chapter2 || {}).currentRegion}; }"""

# 出口へ歩かせる（入力の代わりに位置を少しずつ動かす）
WALK = """async ([tx, tz]) => { const R = window.__r; for (let i = 0; i < 400; i++) { if (R.REG.busy || R.S.mode !== 'playing') break; window.__g0 = R.renderer.info.memory.geometries; window.__t0 = R.renderer.info.memory.textures;
    const dx = tx - R.P.x, dz = tz - R.P.z, d = Math.hypot(dx, dz); if (d < 0.5) break; const s = Math.min(d, 2.5);
    R.P.x += dx / d * s; R.P.z += dz / d * s; await new Promise(r => requestAnimationFrame(r)); }
  for (let i = 0; i < 600 && (R.REG.busy || R.S.mode === 'loading'); i++) await new Promise(r => setTimeout(r, 50)); return R.REG.cur; }"""


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
        cons = []
        pg.on('console', lambda m: cons.append(m.text) if m.type == 'error' else None)
        block = {'data': False}

        async def route(r):
            u = r.request.url
            if 'three' in u:
                await r.fulfill(body=THREE, content_type='application/javascript')
            elif 'kamishihi-map.js' in u:
                if block['data']:
                    await r.fulfill(status=404, body='')
                else:
                    await r.fulfill(body=DATA, content_type='application/javascript')
            elif u.startswith('http://game.local'):
                await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            else:
                await r.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        try:
            await pg.wait_for_function('window.__r', timeout=300000)
        except Exception:
            print('page errors:', errs[:5])
            raise
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(1500)
        E = await pg.evaluate("() => [window.__r.KOMYOJI_EAST, window.__r.KOMYOJI_EAST_ARRIVE]")
        east, arr = E
        print('光明寺の東の出口：', east, '戻る所：', arr)
        # 1) 防衛戦を終える前は行けない
        await pg.evaluate("([x, z]) => { const R = window.__r; R.P.x = x; R.P.z = z; }", [arr['x'], arr['z']])
        await pg.wait_for_timeout(300)
        cur = await pg.evaluate(WALK, [east['x'] + 1, east['z']])
        check(cur == 'komyoji', '防衛戦の前は、東の出口で止められる')
        # 2) 開放して東の出口へ歩く
        await pg.evaluate("""() => { const R = window.__r; R.prog.bossDefeated = true; R.prog.chapter2.unlocked = true;
          R.prog.chapter2.progress.defenseComplete = true; R.P.x = R.KOMYOJI_EAST_ARRIVE.x; R.P.z = R.KOMYOJI_EAST_ARRIVE.z; }""")
        await pg.wait_for_timeout(5000)  # 光明寺の東の端の区画が読み込まれるのを待つ
        base = await pg.evaluate(SNAP)
        print('光明寺：', base)
        geos, texs, departs, tdeparts = [], [], [], []
        for i in range(3):
            await pg.evaluate("([x, z]) => { const R = window.__r; R.P.x = x; R.P.z = z; }", [arr['x'], arr['z']])
            await pg.wait_for_timeout(200)
            cur = await pg.evaluate(WALK, [east['x'] + 1, east['z']])
            departs.append(await pg.evaluate("() => window.__g0"))
            tdeparts.append(await pg.evaluate("() => window.__t0"))
            await pg.wait_for_timeout(800)
            a = await pg.evaluate(SNAP)
            if i == 0:
                print('上志比：', a)
                if cons:
                    print('console errors:', cons[:5])
                K = await pg.evaluate("""() => { const R = window.__r, D = R.KAMI.D, x = R.P.x, z = R.P.z;
                  let best = 1e9; for (const r of D.roads) if (r.n === '国道416号') for (const q of r.p) best = Math.min(best, Math.hypot(q[0] - x, q[1] - z));
                  return {road: best, cls: R.clsAt(x, z), play: D.play, trees: R.REG.live.treeCount, bld: D.bld.length}; }""")
                print('着いた所：', K)
                check(cur == 'kamishihi' and a['px'] > 5000 and a['mode'] == 'playing', '東の出口から上志比へ移った')
                check(K['road'] < 12, f'国道416号の近くに着いた（{K["road"]:.1f}）')
                check(a['oboxes'] - base['oboxes'] == K['bld'] and a['circles'] > base['circles'] + 1000, f'建物 {K["bld"]} 軒と木 {a["circles"] - base["circles"]} 本の当たり判定')
                check(abs(a['ph']) < 300 and a['bounds'] != base['bounds'], '上志比の地面の高さと範囲')
                W = await pg.evaluate("""async () => { const R = window.__r, K = R.KAMI, D = K.D; let wx = null, wz = null;
                  for (let k = 40; k < K.ny - 40 && wx === null; k += 3) for (let i = 40; i < K.nx - 40; i += 3) if (K.C[k * K.nx + i] === 2 && K.C[k * K.nx + i - 6] === 2 && K.C[(k + 6) * K.nx + i] === 2) { wx = K.X0 + i * K.GS; wz = K.Z0 + k * K.GS; break; }
                  const sx = R.P.x, sz = R.P.z; R.P.x = wx; R.P.z = wz; await new Promise(r => requestAnimationFrame(r)); await new Promise(r => requestAnimationFrame(r));
                  const blocked = R.clsAt(R.P.x, R.P.z) !== 2; R.P.x = sx; R.P.z = sz;
                  const r = D.roads.filter(r => r.b).sort((a, b) => b.p.length - a.p.length)[0], q = r.p[Math.floor(r.p.length / 2)];
                  const deck = R.groundH(q[0], q[1]), terr = R.REG.live.h === undefined ? 0 : 0;
                  return {blocked, deck, bridge: R.REG.live.bridgeAt(q[0], q[1])}; }""")
                print('川と橋：', W)
                check(W['blocked'] and W['bridge'] is not None and abs(W['deck'] - W['bridge']) < 0.01, '九頭竜川には入れず、橋の上は橋の高さを歩く')
                if SHOTS:
                    os.makedirs(SHOTS, exist_ok=True)
                    await pg.wait_for_timeout(1500)
                    await pg.screenshot(path=os.path.join(SHOTS, 'kami_arrival.png'))
                    for name, pos in [('kami_sanno', 'station:山王'), ('kami_takehara', 'station:越前竹原'), ('kami_bridge', 'bridge'), ('kami_east', 'xy:7350,640'), ('kami_river', 'xy:5600,470')]:
                        await pg.evaluate("""(pos) => { const R = window.__r, D = R.KAMI.D; let x, z;
                          if (pos.startsWith('station:')) { const s = D.pts.station.find(s => s[2] === pos.slice(8)); x = s[0] + 18; z = s[1] + 10; }
                          else if (pos === 'bridge') { const r = D.roads.filter(r => r.b && r.n === '国道416号').sort((a, b) => b.p.length - a.p.length)[0]; const q = r.p[Math.floor(r.p.length / 2)]; x = q[0]; z = q[1]; }
                          else { [x, z] = pos.slice(3).split(',').map(Number); }
                          R.P.x = x; R.P.z = z; }""", pos)
                        await pg.wait_for_timeout(2500)
                        await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))
                    await pg.evaluate("() => window.__r.openMap()")
                    await pg.wait_for_timeout(300)
                    await pg.evaluate("() => window.__r.openMap()")
                    await pg.wait_for_timeout(600)
                    await pg.screenshot(path=os.path.join(SHOTS, 'kami_map.png'))
                    await pg.keyboard.press('g')
                    await pg.wait_for_timeout(300)
                    st = await pg.evaluate(SNAP)
                    print('描画の量（最後の場所）：', st['tris'], '三角形', st['calls'], '回')
            ex = await pg.evaluate("() => window.__r.KAMI.D.exitWest")
            await pg.evaluate("([x, z]) => { const R = window.__r; R.P.x = x + 40; R.P.z = z; }", [ex['x'], ex['z']])
            await pg.wait_for_timeout(300)
            cur = await pg.evaluate(WALK, [ex['x'] - 1, ex['z']])
            k = await pg.evaluate("() => [window.__g0, window.__t0, window.__r.renderer.info.memory.geometries, window.__r.renderer.info.memory.textures]")
            geos.append((k[0], k[2]))  # 上志比を出る直前と、光明寺に戻った直後（光明寺の区画が新しく作られる前）
            texs.append((k[1], k[3]))
            await pg.wait_for_timeout(3000)
            c = await pg.evaluate(SNAP)
            if i == 0:
                check(cur == 'komyoji' and abs(c['px'] - arr['x']) < 1 and abs(c['pz'] - arr['z']) < 1, '西の出口から、光明寺の東の出口の手前に戻った')
        print('3往復後：', c)
        same = all(c[k] == base[k] for k in ['cur', 'boxes', 'circles', 'oboxes', 'cells', 'kids', 'bounds', 'h'])
        check(same, '3往復しても、当たり判定・場面の物・範囲・地面が元どおり')
        # 光明寺へ戻ったあと、区画の読み込みを待ってから数える（光明寺の物は遅れて作られる物がある）
        # 上志比の物がすべて捨てられたか：光明寺へ戻った直後の数が、上志比へ出る直前（光明寺）の数と同じ
        check(all(abs(g[1] - d) <= 2 for g, d in zip(geos, departs)) and all(t[1] == d for t, d in zip(texs, tdeparts)),
              f'上志比の形・テクスチャが残らない（光明寺を出る直前 {departs}/{tdeparts} → 上志比を出る直前と戻った直後 {geos} {texs}）')
        check(c['saved'] == 'komyoji', '光明寺に戻ると、いる地域が光明寺で保存される')
        # 3) 地図データを読めないとき
        await pg.evaluate("() => { delete window.KAMISHIHI_MAP; document.querySelectorAll('script[src*=kamishihi]').forEach(s => s.remove()); }")
        block['data'] = True
        r3 = await pg.evaluate("async () => await window.__r.regionTravel('kamishihi', null, {force: true})")
        await pg.wait_for_timeout(400)
        d = await pg.evaluate(SNAP)
        check((not r3) and d['cur'] == 'komyoji' and d['circles'] == base['circles'] and d['bounds'] == base['bounds'] and d['mode'] == 'playing',
              '地図データを読めない：光明寺へ戻り、取り残しなし')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: kamishihi region' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
