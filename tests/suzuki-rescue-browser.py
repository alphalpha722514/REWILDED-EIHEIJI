#!/usr/bin/env python3
"""v0.72（P2 作業E 第3段階）スズキが倒れる・助け起こす・回復・主人公が倒れたときの確認（画面のない Chromium。数分）。

助け起こす長押しは、本物のキー（E）とタッチの行動ボタン（pointerdown／pointerup）で押し、ゲームの時間は決まった刻みで進める
（画面のない Chromium は描画が遅く、実時間では進まないため。F11.hold で描画のコマからは進めない）。
- 倒れたスズキは時間がたっても起きず、動かず、敵に狙われず、回復もしない
- 2.5m 以内で「スズキを助け起こす」が出る（3m では出ない）
- E を3秒長押しすると起き、体力90。途中で離すと止まり、はじめから。攻撃を受けると止まり、はじめから。助け起こしている間は動けない
- タッチの行動ボタンでも同じ（押している間・指を離す・取り消し）。ゲージと「スズキを助け起こす」が出る
- ふつうの短押し（スズキへの指示・作業台）はこれまでどおり
- 戦いの後は毎秒3回復し、戦いの間は回復しない
- 主人公が倒れて起きると、ついて来ているスズキは近くへ来る（体力はそのまま）。倒れているスズキはその場に残る
- エラーなし

使い方：THREE_JS=…/three.min.js python3 tests/suzuki-rescue-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SZ_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
HOOK = ("window.__w={get REG(){return REG},get P(){return P},get S(){return S},get prog(){return prog},get enemies(){return enemies},get SZ(){return SZ},get SZR(){return SZR},get SZF(){return SZF},"
        "get held(){return held},get keys(){return keys},get curInter(){return curInter},get F11(){return F11},updatePlayer:dt=>updatePlayer(dt),updateSuzuki:dt=>updateSuzuki(dt),updateEnemies:dt=>updateEnemies(dt),szJoin:()=>szJoin(),"
        "interactables:()=>interactables(),hurtPlayer:(...a)=>hurtPlayer(...a),szFree:(...a)=>szFree(...a),playerDie:r=>playerDie(r),setState:(e,s)=>setState(e,s)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)


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
        await pg.wait_for_timeout(1000)
        # 獣は遠くへ。拠点の中の開けた所で試す
        # 開けた所（まわり8m に当たり判定がない所）
        spot = await pg.evaluate("""() => { const W = window.__w; for (const e of W.enemies) { e.x += 3000; if (e.home) e.home = {x: e.x, z: e.z}; }
          for (let z = -60; z > -300; z -= 6) for (let x = 60; x < 300; x += 6) { let okk = true; for (let a = 0; a < 8 && okk; a++) for (const r of [0, 3, 6, 8]) if (!W.szFree(x + Math.sin(a) * r, z + Math.cos(a) * r, 0.8)) { okk = false; break; } if (okk) return [x, z]; } return null; }""")
        check(spot is not None, f'試す所 {spot}')
        await pg.evaluate("""([x, z]) => { const W = window.__w; W.P.maxHp = 9999; W.P.hp = 9999; W.P.x = x; W.P.z = z - 2; W.P.facing = 0; W.szJoin(); W.SZ.x = x; W.SZ.z = z; W.SZ.order = 'wait'; W.SZ.wx = x; W.SZ.wz = z; }""", spot)

        # ---- 倒れる：起きない・動かない・回復しない ----
        r0 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ; W.S.mode = 'paused'; SZ.hp = 5; SZ.hurt(10, {x: SZ.x + 1, z: SZ.z, mode: 'field'}); const x = SZ.x, z = SZ.z;
          for (let i = 0; i < 1800; i++) { W.S.time += 1 / 30; W.updateSuzuki(1 / 30); if (i % 120 === 0) await new Promise(r => setTimeout(r, 0)); }
          return {down: SZ.down, hp: SZ.hp, moved: Math.hypot(SZ.x - x, SZ.z - z)}; }""")
        check(r0['down'] and r0['hp'] == 0 and r0['moved'] < 0.01, f'倒れたスズキは、60秒たっても起きず・動かず・回復しない {r0}')
        r1 = await pg.evaluate("""() => { const W = window.__w, SZ = W.SZ, P = W.P; P.x = SZ.x; P.z = SZ.z - 2.2; const a = W.interactables(); P.z = SZ.z - 3.0; const b = W.interactables(); P.z = SZ.z - 1.8; return {near: a && a.label, far: b && b.label}; }""")
        check(r1['near'] and 'スズキを助け起こす' in r1['near'] and not (r1['far'] and 'スズキ' in r1['far']), f'2.5m 以内で「スズキを助け起こす」が出る（3m では出ない）{r1}')

        # ---- E の長押し（実時間）----
        STEPS = """async ([sec]) => { const W = window.__w, dt = 1 / 30, n = Math.round(sec / dt); for (let i = 0; i < n; i++) { W.S.time += dt; W.updatePlayer(dt); W.updateSuzuki(dt); if (i % 30 === 0) await new Promise(r => setTimeout(r, 0)); } }"""
        await pg.evaluate("() => { const W = window.__w; W.F11.hold = true; W.S.mode = 'playing'; }")

        async def ready_inter(want):
            for _ in range(60):
                lab = await pg.evaluate("() => window.__w.curInter && window.__w.curInter.label")
                if lab and want in lab:
                    return lab
                await pg.wait_for_timeout(250)
            return None

        async def press_e(sec, extra=None, after=None):
            await pg.evaluate("() => { const W = window.__w; W.S.mode = 'playing'; document.querySelector('canvas').focus(); }")
            await ready_inter('スズキを助け起こす')
            await pg.keyboard.down('e')
            if extra:
                await extra()
            await pg.evaluate(STEPS, [sec])
            if after:
                await after()
            st = await pg.evaluate("() => { const W = window.__w, el = document.getElementById('szRescue'); return {on: W.SZR.on, t: Math.round(W.SZR.t * 100) / 100, down: W.SZ.down, hp: W.SZ.hp, ui: !!el && el.style.display === 'block', bar: el ? el.lastChild.firstChild.style.width : null}; }")
            await pg.keyboard.up('e')
            await pg.evaluate(STEPS, [0.1])
            st2 = await pg.evaluate("() => { const W = window.__w; return {on: W.SZR.on, t: W.SZR.t, down: W.SZ.down}; }")
            return st, st2
        a, a2 = await press_e(1.2)
        check(a['on'] and a['ui'] and a['t'] > 0.4 and a['down'] and not a2['on'] and a2['t'] == 0 and a2['down'], f'E を長押しすると進み（ゲージが出る）、途中で離すと止まり、はじめからになる {a} {a2}')
        # 攻撃を受けると止まる
        async def hit():
            await pg.evaluate("() => { const W = window.__w; W.P.iframe = false; W.hurtPlayer(5, W.P.x + 1, W.P.z, 0, null); W.P.stagger = 0; }")
        h, h2 = await press_e(1.0, None, hit)
        check(not h['on'] and h['t'] == 0 and h['down'], f'助け起こしている途中で攻撃を受けると止まり、はじめからになる {h}')
        # 動けない
        await pg.evaluate("() => { const W = window.__w; W.P.lvx48 = 0; W.P.lvz48 = 0; }")
        p0 = await pg.evaluate("() => [window.__w.P.x, window.__w.P.z]")
        pos = {}
        async def walk():
            await pg.keyboard.down('w')
        async def rec():
            pos['p1'] = await pg.evaluate("() => [window.__w.P.x, window.__w.P.z]")
        m, m2 = await press_e(1.0, walk, rec)
        await pg.keyboard.up('w')
        await pg.evaluate(STEPS, [0.3])
        p1 = pos['p1']
        check(m['on'] and abs(p1[0] - p0[0]) + abs(p1[1] - p0[1]) < 0.05, f'助け起こしている間は、W を押しても動かない {p0} → {p1}')
        await pg.evaluate("() => { const W = window.__w, SZ = W.SZ, P = W.P; P.x = SZ.x; P.z = SZ.z - 1.8; }")
        f, f2 = await press_e(3.6)
        r2 = await pg.evaluate("() => { const W = window.__w; return {down: W.SZ.down, hp: Math.round(W.SZ.hp), upT: W.SZ.upT}; }")
        check(not r2['down'] and 88 <= r2['hp'] <= 100, f'E を3秒長押しすると起き上がり、体力90で戻る {r2} {f}')

        # ---- タッチの行動ボタン ----
        TOUCH = """async ([sec, how]) => { const W = window.__w, b = document.getElementById('tbAct'), dt = 1 / 30; W.S.mode = 'playing';
          const step = async s => { for (let i = 0; i < Math.round(s / dt); i++) { W.S.time += dt; W.updatePlayer(dt); W.updateSuzuki(dt); if (i % 30 === 0) await new Promise(r => setTimeout(r, 0)); } };
          b.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, pointerId: 7, pointerType: 'touch'})); await step(sec);
          const mid = {on: W.SZR.on, t: Math.round(W.SZR.t * 100) / 100, held: W.held.act};
          b.dispatchEvent(new PointerEvent(how, {bubbles: true, pointerId: 7, pointerType: 'touch'})); await step(0.1);
          return {mid, after: {on: W.SZR.on, t: W.SZR.t, held: W.held.act, down: W.SZ.down, hp: Math.round(W.SZ.hp)}}; }"""
        await pg.evaluate("() => { const W = window.__w, SZ = W.SZ, P = W.P; SZ.upT = 0; SZ.hp = 1; SZ.hurt(10, {x: SZ.x + 1, z: SZ.z, mode: 'field'}); SZ.downT = 1; P.x = SZ.x; P.z = SZ.z - 1.8; W.S.mode = 'playing'; }")
        await ready_inter('スズキを助け起こす')
        t1 = await pg.evaluate(TOUCH, [1.2, 'pointerup'])
        check(t1['mid']['on'] and t1['mid']['held'] and t1['mid']['t'] > 0.4 and not t1['after']['on'] and t1['after']['t'] == 0 and t1['after']['down'], f'行動ボタンを押している間だけ進み、指を離すと止まる {t1}')
        t2 = await pg.evaluate(TOUCH, [0.9, 'pointercancel'])
        check(t2['mid']['on'] and not t2['after']['on'] and t2['after']['down'], f'タッチが取り消されると止まる {t2}')
        t3 = await pg.evaluate(TOUCH, [3.2, 'pointerup'])
        check(not t3['after']['down'] and 88 <= t3['after']['hp'] <= 100, f'行動ボタンを3秒長押しすると起き上がる {t3}')
        # ---- ふつうの短押しはこれまでどおり ----
        await pg.evaluate("() => { const W = window.__w, SZ = W.SZ, P = W.P; SZ.upT = 0; P.x = SZ.x; P.z = SZ.z - 1.6; W.S.mode = 'playing'; }")
        r3 = await ready_inter('スズキに指示する')
        await pg.keyboard.press('e')
        await pg.wait_for_timeout(300)
        r4 = await pg.evaluate("() => { const btn = [...document.querySelectorAll('#defenseChoice button')].map(b => b.textContent); const back = [...document.querySelectorAll('#defenseChoice button')].find(b => b.textContent === '戻る'); if (back) back.click(); return btn; }")
        check(r3 == 'スズキに指示する' and 'ここで待て（いまの指示）' in r4, f'倒れていないスズキには、E の短押しでこれまでどおり指示できる {r3} {r4}')
        await pg.evaluate("() => { const W = window.__w; W.P.x = 157.5; W.P.z = 62.3; W.SZ.x = 150; W.SZ.z = 40; W.SZ.wx = 150; W.SZ.wz = 40; W.S.mode = 'playing'; }")
        lab = await ready_inter('作業台')
        await pg.keyboard.press('e')
        await pg.wait_for_timeout(400)
        craft = await pg.evaluate("() => { const el = document.getElementById('craft'); const v = !!el && !el.hidden; if (v) document.getElementById('btnCraftClose').click(); return v; }")
        check(craft, f'作業台も、E の短押しでこれまでどおり開く（{lab}）')
        await pg.evaluate("() => { const W = window.__w; W.S.mode = 'paused'; W.F11.hold = false; }")

        # ---- 戦いの後の回復 ----
        r5 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ; SZ.upT = 0; SZ.hp = 100; SZ.fight = true; SZ.calmT = 0; const out = {};
          for (let i = 0; i < 60; i++) { W.S.time += 1 / 30; W.updateSuzuki(1 / 30); } out.during = Math.round(SZ.hp);
          for (let i = 0; i < 240; i++) { W.S.time += 1 / 30; W.updateSuzuki(1 / 30); } out.fightEnded = !SZ.fight; const h = SZ.hp;
          for (let i = 0; i < 60; i++) { W.S.time += 1 / 30; W.updateSuzuki(1 / 30); } out.perSec = Math.round((SZ.hp - h) / 2 * 10) / 10; return out; }""")
        check(r5['fightEnded'] and abs(r5['perSec'] - 3) < 0.2, f'戦いが終わる（敵がいない状態が8秒）と、毎秒3回復する {r5}')
        r6 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ, e = W.enemies.find(o => !o.removed && o.state !== 'dead' && o.type === 'boar'); if (!e) return null; SZ.order = 'follow'; W.P.x = SZ.x - 1; W.P.z = SZ.z - 2;
          e.x = SZ.x + 6; e.z = SZ.z; e.home = {x: e.x, z: e.z}; W.setState(e, 'chase'); e.hitP = W.S.time; SZ.hp = 100; const h = SZ.hp; let minHp = h, maxHp = h;
          for (let i = 0; i < 60; i++) { W.S.time += 1 / 30; W.updateSuzuki(1 / 30); if (SZ.hp > maxHp) maxHp = SZ.hp; } const out = {fight: SZ.fight, gained: Math.round((maxHp - h) * 10) / 10}; e.x += 3000; e.home = {x: e.x, z: e.z}; W.setState(e, 'idle'); return out; }""")
        check(r6 is not None and r6['fight'] and r6['gained'] == 0, f'戦いの間は回復しない {r6}')

        # ---- 主人公が倒れて起きたとき ----
        r7 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ, P = W.P; SZ.order = 'follow'; SZ.down = false; SZ.upT = 0; SZ.hp = 123; SZ.x = 100; SZ.z = 0; P.x = 98; P.z = 2; W.S.mode = 'playing';
          W.playerDie('hp'); await new Promise(r => setTimeout(r, 200)); document.getElementById('btnRetry').click(); await new Promise(r => setTimeout(r, 400));
          return {d: Math.round(Math.hypot(SZ.x - P.x, SZ.z - P.z) * 10) / 10, hp: Math.round(SZ.hp), mode: W.S.mode}; }""")
        check(r7['d'] < 6 and 123 <= r7['hp'] <= 128, # 起きた後の数コマ（戦いの外なので毎秒3回復）で少し増えることがある
               f'主人公が倒れて起きると、ついて来ているスズキは近くへ来る。体力はそのまま {r7}')
        r8 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ, P = W.P; W.S.mode = 'paused'; SZ.hp = 1; SZ.hurt(10, {x: SZ.x + 1, z: SZ.z, mode: 'field'}); SZ.x = 120; SZ.z = 10; const x = SZ.x, z = SZ.z; W.S.mode = 'playing';
          W.playerDie('hp'); await new Promise(r => setTimeout(r, 200)); document.getElementById('btnRetry').click(); await new Promise(r => setTimeout(r, 400));
          return {down: SZ.down, moved: Math.hypot(SZ.x - x, SZ.z - z), hp: SZ.hp}; }""")
        check(r8['down'] and r8['moved'] < 0.01 and r8['hp'] == 0, f'倒れているスズキは、主人公が起きても勝手に起きず、その場に残る {r8}')

        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: suzuki rescue (stage 3)' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
