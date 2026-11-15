#!/usr/bin/env python3
"""v0.73（P2 作業E 第4段階）スズキのセーブ・読み込み・地域をまたぐ状態の確認（画面のない Chromium。数分）。

本物の保存（localStorage）に書き、ページを読み直して「つづきから」で確かめる。
- 古いセーブ（suzuki のキーがない）・不正な値：まだ仲間でない（出ない）／直せる値は直して読む
- ついて来ている：読み込むと主人公の近くに出る。体力はそのまま
- 上志比で待たせて光明寺で保存：読み込むと上志比に残っている（光明寺には出ない）。上志比へ行くと待たせた所にいる
- 地域を移った直後の保存（上志比）：つづきから上志比の着く所で始まり、スズキは主人公の近くに出る
- 倒れている：読み込んでも倒れたまま、同じ所。助け起こせる
- 拠点で過ごす：読み込んでも拠点で過ごす
- 主人公が倒れて起きた後の保存：ついて来ているスズキは近くに出る。体力はそのまま
- 試遊版は別の保存キー（本編のセーブに混ざらない）
- エラーなし

使い方：THREE_JS=…/three.min.js python3 tests/suzuki-save-browser.py
"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SZ_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
KDATA = open(os.path.join(ROOT, 'data', 'kamishihi', 'kamishihi-map.js'), encoding='utf8').read()
MDATA = open(os.path.join(ROOT, 'data', 'models', 'mutant-monkey.js'), encoding='utf8').read()
HOOK = ("window.__w={get REG(){return REG},get P(){return P},get S(){return S},get prog(){return prog},get enemies(){return enemies},get SZ(){return SZ},get F11(){return F11},"
        "regionTravel,saveGame,updateSuzuki:dt=>updateSuzuki(dt),szJoin:()=>szJoin(),szOrder:k=>szOrder(k),szDown:()=>szDown(),interactables:()=>interactables(),"
        "szFree:(...a)=>szFree(...a),inBase:(...a)=>inBase(...a),playerDie:r=>playerDie(r),SAVE_KEY};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
# 体力は、読み込んだ後の数コマ（戦いの外なので毎秒3回復）で少し増えることがある
STATE = "() => { const W = window.__w, SZ = W.SZ, P = W.P; return {joined: SZ.joined, order: SZ.order, region: SZ.region, cur: W.REG.cur, x: Math.round(SZ.x * 100) / 100, z: Math.round(SZ.z * 100) / 100, wx: SZ.wx, wz: SZ.wz, hp: Math.round(SZ.hp), down: SZ.down, d: Math.round(Math.hypot(SZ.x - P.x, SZ.z - P.z) * 10) / 10, vis: !!(SZ.m && SZ.m.g.visible)}; }"


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

        async def boot():
            await pg.goto('http://game.local/', wait_until='load', timeout=300000)
            await pg.wait_for_function('window.__w', timeout=300000)

        async def cont(region='komyoji'):
            await boot()
            await pg.click('#btnContinue')
            await pg.wait_for_function(f"window.__w.REG.cur === '{region}' && !window.__w.REG.busy && window.__w.S.mode === 'playing'", timeout=300000)
            await pg.evaluate("() => { const W = window.__w; W.F11.hold = true; for (let i = 0; i < 3; i++) { W.S.time += 1 / 30; W.updateSuzuki(1 / 30); } }")
            return await pg.evaluate(STATE)

        await boot()
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await pg.evaluate("() => { const W = window.__w; W.prog.bossDefeated = true; W.prog.stage = 'cleared'; W.prog.chapter2.unlocked = true; W.prog.chapter2.progress.defenseComplete = true; W.saveGame(); }")

        # ---- 古いセーブ・不正な値 ----
        await pg.evaluate("() => { const W = window.__w, d = JSON.parse(localStorage.getItem(W.SAVE_KEY)); delete d.suzuki; localStorage.setItem(W.SAVE_KEY, JSON.stringify(d)); }")
        s0 = await cont()
        check(not s0['joined'] and not s0['vis'], f'古いセーブ（suzuki のキーがない）：スズキはまだ仲間でない・出ない {s0}')
        await pg.evaluate("() => { const W = window.__w, d = JSON.parse(localStorage.getItem(W.SAVE_KEY)); d.suzuki = {v: 1, joined: true, order: 'dance', region: 'mars', x: 'a', z: 1, hp: 'x'}; localStorage.setItem(W.SAVE_KEY, JSON.stringify(d)); }")
        s1 = await cont()
        check(s1['joined'] and s1['order'] == 'follow' and s1['region'] == 'komyoji' and s1['hp'] == 180 and s1['d'] < 6, f'不正な値は直して読む（ついて来る・光明寺・体力180・主人公の近く）{s1}')
        await pg.evaluate("() => { const W = window.__w, d = JSON.parse(localStorage.getItem(W.SAVE_KEY)); d.suzuki = {v: 2, joined: true}; localStorage.setItem(W.SAVE_KEY, JSON.stringify(d)); }")
        s1b = await cont()
        check(not s1b['joined'], f'形の違う値（v:2）は「まだ仲間でない」{s1b}')

        # ---- ついて来ている ----
        await pg.evaluate("() => { const W = window.__w; W.S.mode = 'playing'; W.szJoin(); W.SZ.hp = 123; W.saveGame(); }")
        s2 = await cont()
        check(s2['joined'] and s2['order'] == 'follow' and 123 <= s2['hp'] <= 126 and s2['d'] < 6 and s2['vis'], f'ついて来ている：読み込むと主人公の近くに出る。体力はそのまま {s2}')

        # ---- 上志比で待たせて、光明寺で保存 ----
        await pg.evaluate("async () => { const W = window.__w; W.F11.hold = false; await W.regionTravel('kamishihi', null, {force: true}); W.F11.hold = true; W.updateSuzuki(1 / 30); W.szOrder('wait'); W.SZ.hp = 120; W.saveGame(); await W.regionTravel('komyoji', null, {force: true}); }")
        spot = await pg.evaluate("() => [window.__w.SZ.wx, window.__w.SZ.wz]")
        s3 = await cont('komyoji')
        check(s3['joined'] and s3['order'] == 'wait' and s3['region'] == 'kamishihi' and s3['cur'] == 'komyoji' and not s3['vis'] and 120 <= s3['hp'] <= 123 and abs(s3['wx'] - spot[0]) < 0.02, f'上志比で待たせて光明寺で保存：読み込むと上志比に残っている（光明寺には出ない）{s3}')
        await pg.evaluate("async () => { const W = window.__w; await W.regionTravel('kamishihi', null, {force: true}); for (let i = 0; i < 3; i++) W.updateSuzuki(1 / 30); }")
        s3b = await pg.evaluate(STATE)
        check(s3b['region'] == 'kamishihi' and abs(s3b['x'] - spot[0]) < 0.5 and abs(s3b['z'] - spot[1]) < 0.5 and s3b['vis'] in (True, False), f'上志比へ行くと、待たせた所にいる {s3b} {spot}')

        # ---- 地域を移った直後の保存（上志比）----
        await pg.evaluate("async () => { const W = window.__w; W.szOrder('follow'); const SZ = W.SZ, P = W.P; P.x = SZ.x + 1; P.z = SZ.z; await W.regionTravel('komyoji', null, {force: true}); for (let i = 0; i < 3; i++) W.updateSuzuki(1 / 30); await W.regionTravel('kamishihi', null, {force: true}); }")
        s4 = await cont('kamishihi')
        check(s4['joined'] and s4['order'] == 'follow' and s4['region'] == 'kamishihi' and s4['cur'] == 'kamishihi' and s4['d'] < 6, f'上志比へ移った直後の保存：つづきから上志比で始まり、スズキは主人公の近くに出る {s4}')
        await pg.evaluate("async () => { const W = window.__w; W.F11.hold = false; await W.regionTravel('komyoji', null, {force: true}); W.F11.hold = true; for (let i = 0; i < 3; i++) W.updateSuzuki(1 / 30); }")

        # ---- 倒れている ----
        await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; W.szDown(); W.saveGame(); }")
        before = await pg.evaluate(STATE)
        s5 = await cont()
        near = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ, P = W.P; P.x = SZ.x; P.z = SZ.z - 1.8; const it = W.interactables(); return it && it.label; }")
        check(s5['down'] and s5['hp'] == 0 and abs(s5['x'] - before['x']) < 0.02 and abs(s5['z'] - before['z']) < 0.02 and near and 'スズキを助け起こす' in near, f'倒れている：読み込んでも倒れたまま、同じ所。助け起こせる {s5} {near}')

        # ---- 拠点で過ごす ----
        await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; SZ.down = false; SZ.hp = 150; SZ.x = 150; SZ.z = 55; W.szOrder('base'); W.saveGame(); }")
        s6 = await cont()
        inb = await pg.evaluate("() => window.__w.inBase(window.__w.SZ.x, window.__w.SZ.z, 0)")
        check(s6['order'] == 'base' and s6['region'] == 'komyoji' and inb and 150 <= s6['hp'] <= 153, f'拠点で過ごす：読み込んでも拠点で過ごす {s6}')

        # ---- 主人公が倒れて起きた後の保存 ----
        await pg.evaluate("async () => { const W = window.__w; W.szOrder('follow'); W.SZ.hp = 77; W.S.mode = 'playing'; W.playerDie('hp'); await new Promise(r => setTimeout(r, 200)); document.getElementById('btnRetry').click(); await new Promise(r => setTimeout(r, 300)); }")
        s7 = await cont()
        check(s7['order'] == 'follow' and 77 <= s7['hp'] <= 80 and s7['d'] < 6, f'主人公が倒れて起きた後の保存：ついて来ているスズキは近くに出る。体力はそのまま {s7}')

        # ---- 試遊版は別の保存キー ----
        prev = open(os.path.join(ROOT, 'previews', 'p2-suzuki', 'index.html'), encoding='utf8').read()
        check("const SAVE_KEY='eiheiji_vs_beasts_p2suzuki'" in prev and "const SAVE_KEY='eiheiji_vs_beasts_v010'" not in prev, '試遊版は別の保存キー（スズキを呼んだ状態が本編のセーブに混ざらない）')
        main_has_btn = 'btnSStartK' in SRC or 'sTestStart' in SRC
        check(not main_has_btn, '本編にはスズキを呼ぶボタンがない')

        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: suzuki save (stage 4)' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
