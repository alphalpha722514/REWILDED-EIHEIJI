#!/usr/bin/env python3
"""v0.61 変異したサルの確認（画面のない Chromium。数分）。

本編のコードで変異したサルを呼び、敵の更新を一定の刻みで直接回して（描画は時々だけ）、次を確かめる。
- 形のデータを読んで呼び出せる（骨21本・三角形・テクスチャ）
- 主人公に向かって戦う：凶暴化した猿と同じ攻撃（突進・噛みつき）と固有の攻撃（前腕のひっかき・飛びかかり）を使い、当たると主人公の体力が減る
- 初遭遇（fleeOnly）：体力が45%以下になると逃げ去り、倒れない。逃げ切ると消える
- 通常：体力が0になると倒れて消える
- 呼んで消すのを繰り返しても、形・テクスチャ・場面の物が増え続けない
- 上志比で呼んだものは、光明寺へ戻ると消える
- エラーなし
使い方：THREE_JS=…/three.min.js python3 tests/mutant-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
MDATA = open(os.path.join(ROOT, 'data', 'models', 'mutant-monkey.js'), encoding='utf8').read()
KDATA = open(os.path.join(ROOT, 'data', 'kamishihi', 'kamishihi-map.js'), encoding='utf8').read()
HOOK = ("window.__t={get enemies(){return enemies},get P(){return P},get S(){return S},get prog(){return prog},renderer,scene,camera,"
        "spawnMutant:(...a)=>spawnMutant(...a),updateEnemies:(dt)=>updateEnemies(dt),damageEnemy:(...a)=>damageEnemy(...a),regionTravel:(...a)=>regionTravel(...a),"
        "get REG(){return REG},get MUTANT(){return MUTANT}};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

# 敵の更新を n 回まわす（主人公は止まったまま。倒れないよう体力を戻す）。訪れた状態と主人公が受けた回数を数える
RUN = """async ([n, dt]) => { const T = window.__t, P = T.P; const seen = {}; let hits = 0, lastHp = P.hp;
  for (let i = 0; i < n; i++) { T.S.time += dt; T.updateEnemies(dt);
    for (const e of T.enemies) if (e.type === 'mutant') seen[e.state] = (seen[e.state] || 0) + 1;
    if (P.hp < lastHp) hits++; P.hp = P.maxHp; lastHp = P.hp; P.iframe = 0; P.dead = false;
    if (i % 60 === 0) { T.renderer.render(T.scene, T.camera); await new Promise(r => setTimeout(r, 0)); } }
  return {seen, hits}; }"""
MEM = "() => { const T = window.__t; return {geo: T.renderer.info.memory.geometries, tex: T.renderer.info.memory.textures, kids: T.scene.children.length, n: T.enemies.length}; }"


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 800, 'height': 500})).new_page()
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
        await pg.wait_for_function('window.__t', timeout=300000)
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(2000)
        # 主人公を開けた所に置く（光明寺の始まりの所）。サルを 9 先に
        info = await pg.evaluate("""async () => { const T = window.__t, P = T.P; P.maxHp = 9999; P.hp = 9999;
          const e = await T.spawnMutant(P.x + 7, P.z + 6, {fleeOnly: true}); T.renderer.render(T.scene, T.camera);
          return {ok: !!e, bones: e.m.skin.skeleton.bones.length, tris: e.m.skin.geometry.index.count / 3, tex: !!(T.MUTANT.tex.image && T.MUTANT.tex.image.width), hp: e.hp}; }""")
        print('呼び出し：', info)
        check(info['ok'] and info['bones'] == 21 and info['tris'] > 5000 and info['tex'], '形のデータを読んで呼び出せる（骨21本・テクスチャ）')
        base = await pg.evaluate(MEM)
        r = await pg.evaluate(RUN, [2400, 1 / 30])
        print('80秒の戦い：', r)
        sn = r['seen']
        check(r['hits'] >= 3, f'主人公に当てる（{r["hits"]} 回）')
        check(('dash' in sn) and ('wind' in sn), '凶暴化した猿と同じ攻撃（突進・噛みつき）を使う')
        check(('scratchWind' in sn) and ('pounceWind' in sn) and ('pounce' in sn), '固有の攻撃（前腕のひっかき・飛びかかり）を使う')
        # 初遭遇：体力を減らすと逃げ去る
        fl = await pg.evaluate("""async () => { const T = window.__t; const e = T.enemies.find(e => e.type === 'mutant');
          for (let i = 0; i < 30 && e.state !== 'flee'; i++) T.damageEnemy(e, 12, 'light', 0);
          const st = e.state, hp = e.hp, max = e.maxHp; for (let i = 0; i < 10; i++) T.damageEnemy(e, 30, 'heavy', 0);
          return {st, hp, max, hpAfter: e.hp, dead: e.state === 'dead'}; }""")
        print('初遭遇：', fl)
        check(fl['st'] == 'flee' and fl['hp'] <= fl['max'] * 0.45 and fl['hpAfter'] >= 1 and not fl['dead'], '初遭遇は体力45%以下で逃げ去り、さらに叩いても倒れない')
        await pg.evaluate(RUN, [240, 1 / 30])
        gone = await pg.evaluate("() => !window.__t.enemies.some(e => e.type === 'mutant')")
        check(gone, '逃げ切ると消える')
        # 通常：倒れる
        dd = await pg.evaluate("""async () => { const T = window.__t, P = T.P; const e = await T.spawnMutant(P.x + 5, P.z + 5, {fleeOnly: false});
          for (let i = 0; i < 40 && e.state !== 'dead'; i++) T.damageEnemy(e, 15, 'light', 0); return e.state; }""")
        await pg.evaluate(RUN, [120, 1 / 30])
        gone2 = await pg.evaluate("() => !window.__t.enemies.some(e => e.type === 'mutant')")
        check(dd == 'dead' and gone2, '通常は体力0で倒れ、少しして消える')
        # 繰り返し
        mems = []
        for i in range(4):
            # 倒すと毛皮などが落ちて場面の物が増えるので、ここは逃げ去る方で数える
            await pg.evaluate("""async () => { const T = window.__t, P = T.P; const e = await T.spawnMutant(P.x + 6, P.z + 6, {fleeOnly: true});
              T.renderer.render(T.scene, T.camera); for (let i = 0; i < 40 && e.state !== 'flee'; i++) T.damageEnemy(e, 20, 'light', 0); }""")
            await pg.evaluate(RUN, [240, 1 / 30])
            await pg.evaluate("() => window.__t.renderer.render(window.__t.scene, window.__t.camera)")
            mems.append(await pg.evaluate(MEM))
        print('繰り返し：', mems)
        check(len({(m['geo'], m['tex'], m['kids']) for m in mems[1:]}) == 1, '呼んで消すのを繰り返しても、形・テクスチャ・場面の物が増え続けない')
        # 上志比で呼んで光明寺へ戻る
        kk = await pg.evaluate("""async () => { const T = window.__t, P = T.P; T.prog.bossDefeated = true; T.prog.chapter2.unlocked = true; T.prog.chapter2.progress.defenseComplete = true;
          await T.regionTravel('kamishihi', null, {force: true}); const e = await T.spawnMutant(P.x + 8, P.z, {fleeOnly: true});
          const inRegion = T.REG.live.enemies.includes(e); await T.regionTravel('komyoji', null, {force: true});
          return {inRegion, left: T.enemies.includes(e), removed: e.removed}; }""")
        print('上志比：', kk)
        check(kk['inRegion'] and not kk['left'] and kk['removed'], '上志比で呼んだものは、光明寺へ戻ると消える')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: mutant monkey' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
