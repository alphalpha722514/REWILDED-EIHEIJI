#!/usr/bin/env python3
"""v0.74（P2 作業E 第5段階）光明寺の防衛戦とスズキの確認（画面のない Chromium。数分）。

2026-11-15 ユーザー決定「A」：防衛戦が始まると、光明寺にいるスズキは（倒れていなければ）どの指示でも主人公のそばへ来て一緒に戦い、
終わると元の指示に戻る。上志比で待たせているスズキは加わらない。
- 「拠点で過ごせ」のスズキは、防衛戦が始まると主人公のそばへ来る（指示そのものは「拠点で過ごせ」のまま。保存も）
- 防衛戦の獣は、主人公から8m 以内なら相手にし、それより遠ければ相手にしない
- 防衛戦が終わると、元の指示に戻って拠点へ帰る
- 上志比で待たせているスズキは、防衛戦に加わらない
- エラーなし
（勝ちやすさの比べ方は tools/defense-sim.cjs --suzuki 1）

使い方：THREE_JS=…/three.min.js python3 tests/suzuki-defense-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SZ_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
HOOK = ("window.__w={get REG(){return REG},get P(){return P},get S(){return S},get prog(){return prog},get enemies(){return enemies},get SZ(){return SZ},get ev(){return ev},get npcGen(){return npcGen},"
        "updateSuzuki:dt=>updateSuzuki(dt),szJoin:()=>szJoin(),szOrder:k=>szOrder(k),szOrd:()=>szOrd(),szIsThreat:(e,a)=>szIsThreat(e,a),szAnchor:()=>szAnchor(),szSave:()=>szSave(),"
        "inBase:(...a)=>inBase(...a),startChapter2Defense:()=>startChapter2Defense(),setState:(e,s)=>setState(e,s)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
STEP = """async ([n]) => { const W = window.__w, dt = 1 / 30; for (let i = 0; i < n; i++) { W.S.time += dt; W.updateSuzuki(dt); if (i % 60 === 0) await new Promise(r => setTimeout(r, 0)); } }"""


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
        await pg.wait_for_timeout(800)
        await pg.evaluate("""() => { const W = window.__w; W.prog.bossDefeated = true; W.prog.stage = 'cleared'; W.prog.chapter2.unlocked = true; W.prog.chapter2.progress.defenseComplete = true;
          W.S.mode = 'paused'; for (const e of W.enemies) { e.x += 3000; e.home = {x: e.x, z: e.z}; } const g = W.npcGen; W.P.x = g.x + 1.2; W.P.z = g.z + 1.2; W.szJoin(); W.SZ.x = 150; W.SZ.z = 55; W.szOrder('base'); }""")
        await pg.evaluate(STEP, [300])
        r0 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; return {ord: W.szOrd(), inBase: W.inBase(SZ.x, SZ.z, 0), d: Math.round(Math.hypot(SZ.x - W.P.x, SZ.z - W.P.z))}; }")
        check(r0['ord'] == 'base' and r0['inBase'], f'ふだんは拠点で過ごす {r0}')

        # ---- 防衛戦が始まる ----
        r1 = await pg.evaluate("() => { const W = window.__w; W.S.mode = 'playing'; const ok = W.startChapter2Defense(); W.S.mode = 'paused'; return {ok, kind: W.ev.kind, ord: W.szOrd(), order: W.SZ.order}; }")
        check(r1['kind'] == 'chapter2' and r1['ord'] == 'follow' and r1['order'] == 'base', f'防衛戦が始まると、拠点で過ごすスズキもついて来る（指示そのものは「拠点で過ごせ」のまま）{r1}')
        await pg.evaluate(STEP, [450])
        r2 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; return {d: Math.round(Math.hypot(SZ.x - W.P.x, SZ.z - W.P.z) * 10) / 10, save: W.szSave().order}; }")
        check(r2['d'] < 8 and r2['save'] == 'base', f'主人公のそばへ来る。保存する指示は「拠点で過ごせ」のまま {r2}')
        r3 = await pg.evaluate("""() => { const W = window.__w, P = W.P, L = W.enemies.filter(e => !e.removed && e.state !== 'dead' && e.type !== 'boss').slice(0, 2); if (L.length < 2) return null;
          const keep = L.map(e => [e.x, e.z, e.mode, e.state]); const A = W.szAnchor();
          L[0].mode = 'raid'; L[0].x = P.x + 6; L[0].z = P.z; W.setState(L[0], 'raid'); L[1].mode = 'raid'; L[1].x = P.x + 15; L[1].z = P.z; W.setState(L[1], 'raid');
          const near = W.szIsThreat(L[0], A), far = W.szIsThreat(L[1], A);
          L.forEach((e, i) => { e.x = keep[i][0]; e.z = keep[i][1]; e.mode = keep[i][2]; W.setState(e, keep[i][3]); }); return {near, far}; }""")
        check(r3 is not None and r3['near'] and not r3['far'], f'防衛戦の獣は、主人公から8m 以内なら相手にし、15m 先は相手にしない {r3}')

        # ---- 終わると元の指示へ ----
        await pg.evaluate("() => { const W = window.__w; W.ev.kind = null; W.ev.phase = null; }")
        r4 = await pg.evaluate("() => window.__w.szOrd()")
        await pg.evaluate(STEP, [1500])
        r5 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; return W.inBase(SZ.x, SZ.z, 0); }")
        check(r4 == 'base' and r5, f'防衛戦が終わると、元の指示（拠点で過ごせ）に戻り、拠点へ帰る {r4} {r5}')

        # ---- 上志比で待たせているスズキは加わらない ----
        r6 = await pg.evaluate("() => { const W = window.__w, SZ = W.SZ; SZ.region = 'kamishihi'; SZ.order = 'wait'; W.S.mode = 'playing'; W.startChapter2Defense(); W.S.mode = 'paused'; const o = W.szOrd(); return {ord: o, kind: W.ev.kind}; }")
        check(r6['kind'] == 'chapter2' and r6['ord'] == 'wait', f'上志比で待たせているスズキは、防衛戦に加わらない {r6}')

        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: suzuki defense (stage 5)' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
