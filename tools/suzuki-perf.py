#!/usr/bin/env python3
"""スズキを連れたときの重さの目安を測る（画面のない Chromium・SwiftShader。実機の速さではない。差を見る）。

- 上志比のサルの要塞の前（守りのサルが出ている所）で、敵とスズキの更新を決まった刻みで 600 回まわし、1回あたりの時間をくらべる
  （スズキなし／スズキあり・ついて来る／スズキあり・戦っている）
- 描く回数（draw calls）と三角形の数：スズキを出したときと出さないとき。臭いの煙を最大に出したとき
使い方：THREE_JS=…/three.min.js python3 tools/suzuki-perf.py
"""
import asyncio
import json
import os

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SZ_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
KDATA = open(os.path.join(ROOT, 'data', 'kamishihi', 'kamishihi-map.js'), encoding='utf8').read()
MDATA = open(os.path.join(ROOT, 'data', 'models', 'mutant-monkey.js'), encoding='utf8').read()
HOOK = ("window.__w={get REG(){return REG},get P(){return P},get S(){return S},get prog(){return prog},get stats(){return stats},get enemies(){return enemies},get SZ(){return SZ},get F11(){return F11},"
        "regionTravel,renderer,scene,camera,updateSuzuki:dt=>updateSuzuki(dt),updateEnemies:dt=>updateEnemies(dt),updateCamera:dt=>updateCamera(dt),szJoin:()=>szJoin(),"
        "kfGarrisonTick:(c,t)=>kfGarrisonTick(c,t),kfQueueTick:c=>kfQueueTick(c),setState:(e,s)=>setState(e,s)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
RUN = """async ([n, withSz]) => { const W = window.__w, dt = 1 / 30; let tot = 0, fight = 0, kicks = 0, last = null;
  for (let i = 0; i < n; i++) { const t0 = performance.now(); W.S.time += dt; W.stats.time += dt; if (withSz) W.updateSuzuki(dt); W.updateEnemies(dt); tot += performance.now() - t0;
    if (i % 8 === 0) { W.kfGarrisonTick(W.REG.live, W.stats.time); W.kfQueueTick(W.REG.live); } W.P.hp = W.P.maxHp; W.P.dead = false; if (W.SZ.joined) { W.SZ.hp = W.SZ.maxHp; W.SZ.down = false; }
    if (W.SZ.fight) fight++; if (W.SZ.kick && W.SZ.kick !== last) kicks++; last = W.SZ.kick;
    if (i % 60 === 0) await new Promise(r => setTimeout(r, 0)); }
  const alive = W.enemies.filter(e => !e.removed && e.state !== 'dead').length; return {msPerStep: Math.round(tot / n * 1000) / 1000, alive, fightPct: Math.round(fight / n * 100), kicks}; }"""
DRAW = """() => { const W = window.__w, r = W.renderer; W.updateCamera(0.016); r.info.autoReset = true; const m = W.SZ.m, out = {};
  if (m) { m.g.visible = false; r.render(W.scene, W.camera); out.hidden = {calls: r.info.render.calls, tris: r.info.render.triangles}; m.g.visible = true; }
  r.render(W.scene, W.camera); out.shown = {calls: r.info.render.calls, tris: r.info.render.triangles}; return out; }"""


async def main():
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
        await pg.evaluate("""async () => { const W = window.__w; W.prog.bossDefeated = true; W.prog.stage = 'cleared'; W.prog.chapter2.unlocked = true; W.prog.chapter2.progress.defenseComplete = true; W.prog.chapter2.progress.mutantMet = true;
          await W.regionTravel('kamishihi', null, {force: true}); W.F11.hold = true; W.S.mode = 'paused'; W.P.x = 7200; W.P.z = 1060; W.P.maxHp = 9999; W.P.hp = 9999;
          for (let i = 0; i < 30; i++) { W.S.time += 1 / 30; W.stats.time += 1 / 30; W.updateEnemies(1 / 30); W.kfGarrisonTick(W.REG.live, W.stats.time); } }""")
        await pg.wait_for_timeout(2000)
        out = {}
        out['no_suzuki'] = await pg.evaluate(RUN, [600, False])
        d0 = await pg.evaluate(DRAW)
        await pg.evaluate("() => { const W = window.__w; W.szJoin(); }")
        out['suzuki_follow'] = await pg.evaluate(RUN, [600, True])
        d1 = await pg.evaluate(DRAW)
        # 戦わせる：要塞の中へ近づける（守りのサルが気づいて集まる）
        await pg.evaluate("() => { const W = window.__w; W.P.x = 7262; W.P.z = 1072; W.SZ.x = 7260; W.SZ.z = 1070; let n = 0; for (const e of W.enemies) { if (e.removed || e.state === 'dead' || e.kfY > 1) continue; if (n < 4) { e.x = W.P.x + 3 + n; e.z = W.P.z + 2; e.home = {x: e.x, z: e.z}; e.hitP = W.S.time; W.setState(e, e.type === 'monkey' || e.type === 'mutant' ? 'kite' : 'chase'); n++; } } }")
        out['suzuki_fight'] = await pg.evaluate(RUN, [600, True])
        out['fight_state'] = await pg.evaluate("() => { const W = window.__w; return {fight: W.SZ.fight, smelly: W.enemies.filter(e => e.smellT > 0).length}; }")
        d1b = await pg.evaluate(DRAW)
        # 臭いの煙を最大に
        d2 = await pg.evaluate("() => { const W = window.__w; let n = 0; for (const e of W.enemies) { if (e.removed || e.state === 'dead') continue; e.x = W.P.x + 2 + n * 1.2; e.z = W.P.z + 4; e.smellT = 10; e.smellAcc = -99; if (++n >= 4) break; } for (let i = 0; i < 20; i++) W.updateSuzuki(0.05); const r = W.renderer; W.updateCamera(0.016); r.render(W.scene, W.camera); return {calls: r.info.render.calls, tris: r.info.render.triangles}; }")
        out['draw'] = {'no_suzuki': d0, 'with_suzuki': d1, 'fight_no_smoke': d1b, 'fight_smoke_max': d2}
        out['errors'] = errs[:3]
        print(json.dumps(out, ensure_ascii=False, indent=1))
        await b.close()


asyncio.run(main())
