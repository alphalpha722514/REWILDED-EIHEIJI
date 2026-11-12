#!/usr/bin/env python3
"""v0.60（P2 作業A）地域の移動の確認（画面のない Chromium。数分かかる）。

試験用の地域（平らな地面・当たり判定・物）をその場で定義し、光明寺との往復を10回くり返して、
- 往復のたびに、当たり判定・ジオメトリ・テクスチャ・場面の物の数が元に戻る（重複・取り残しがない）
- 移った先の地面の高さ・範囲・位置が正しく、光明寺に戻ると元どおり
- 読み込みに失敗する地域へ移ろうとすると、光明寺へ安全に戻る
- 最後にいた地域が保存され、「つづきから」でその地域から始まる（開放済みのとき）
を確かめる。

使い方：THREE_JS=…/three.min.js python3 tests/region-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
HOOK = ("window.__r={regionDefine,regionTravel,REG,REGION_X0,renderer,scene,boxes,circles,oboxes,cgrid,BOUNDS,groundH,continueGame,"
        "get P(){return P},get S(){return S},get prog(){return prog},saveGame};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

DEFINE = """() => { const R = window.__r, T = THREE, X = R.REGION_X0;
  R.regionDefine('testfield', {name: '試験の野原', build(ctx) {
    const g = ctx.own(new T.PlaneGeometry(300, 300, 8, 8)); g.rotateX(-Math.PI / 2); g.translate(X + 250, 2, 0);
    const m = ctx.own(new T.MeshLambertMaterial({color: 0x7a9a5a}));
    ctx.add(new T.Mesh(g, m));
    for (let i = 0; i < 30; i++) { ctx.circle(X + 150 + i * 6, 20, 1.2, 'tree');
      const tg = ctx.own(new T.CylinderGeometry(0.3, 0.4, 4, 6)); const tm = new T.Mesh(tg, m); tm.position.set(X + 150 + i * 6, 4, 20); ctx.add(tm); }
    for (let i = 0; i < 5; i++) ctx.box(X + 200 + i * 10, -30, 4, 4, 'wall');
    ctx.obox(X + 260, 40, 6, 3, 0.4, 'house'); ctx.obox(X + 280, 40, 6, 3, -0.4, 'house');
    ctx.h = (x, z) => 2; ctx.cls = () => 1;
    ctx.bounds = {minX: X + 110, maxX: X + 390, minZ: -140, maxZ: 140};
    ctx.arrival = {x: X + 200, z: 0, facing: 0};
  }});
  R.regionDefine('broken', {name: '壊れた地域', build(ctx) { ctx.circle(X + 10, 0, 1, 'tree'); throw new Error('test failure'); }});
}"""

SNAP = """() => { const R = window.__r; let cells = 0; for (const a of R.cgrid.values()) cells += a.length;
  return {cur: R.REG.cur, geo: R.renderer.info.memory.geometries, tex: R.renderer.info.memory.textures, boxes: R.boxes.length, circles: R.circles.length,
    oboxes: R.oboxes.length, cells, kids: R.scene.children.length, bounds: JSON.stringify(R.BOUNDS), h: R.groundH(158, 22),
    px: R.P.x, pz: R.P.z, ph: R.groundH(R.P.x, R.P.z), mode: R.S.mode,
    saved: (JSON.parse(localStorage.getItem('eiheiji_vs_beasts_v010') || '{}').chapter2 || {}).currentRegion}; }"""


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 640, 'height': 400})).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(r):
            u = r.request.url
            if 'three' in u:
                await r.fulfill(body=THREE, content_type='application/javascript')
            elif u.startswith('http://game.local'):
                await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            else:
                await r.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__r', timeout=300000)
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await pg.evaluate(DEFINE)
        await pg.wait_for_timeout(1500)
        base = await pg.evaluate(SNAP)
        print('光明寺：', base)
        geos = []
        for i in range(10):
            r1 = await pg.evaluate("async () => await window.__r.regionTravel('testfield', null, {force: true})")
            await pg.wait_for_timeout(400)
            a = await pg.evaluate(SNAP)
            if i == 0:
                print('試験の野原：', a)
                check(r1 and a['cur'] == 'testfield' and a['px'] > 4000 and a['ph'] == 2, '移った先：地域・位置・地面の高さ')
                check(a['circles'] == base['circles'] + 30 and a['boxes'] == base['boxes'] + 5 and a['oboxes'] == base['oboxes'] + 2, '移った先の当たり判定が足された')
                check(a['bounds'] != base['bounds'] and a['mode'] == 'playing', '範囲が変わり、操作できる')
            r2 = await pg.evaluate("async () => await window.__r.regionTravel('komyoji', null, {force: true})")
            await pg.wait_for_timeout(400)
            c = await pg.evaluate(SNAP)
            geos.append(c['geo'])
        print('10往復後：', c)
        same = all(c[k] == base[k] for k in ['cur', 'tex', 'boxes', 'circles', 'oboxes', 'cells', 'kids', 'bounds', 'h'])
        check(r2 and same, '10往復しても、当たり判定・テクスチャ・場面の物・範囲・地面が元どおり')
        # ジオメトリは、光明寺へ初めて戻ったときに遅れて作られる物（木など）があるので、2回目以降が増えないことを見る
        check(len(set(geos[1:])) == 1, f'ジオメトリの数が往復で増え続けない（{geos}）')
        r3 = await pg.evaluate("async () => await window.__r.regionTravel('broken', null, {force: true})")
        await pg.wait_for_timeout(400)
        d = await pg.evaluate(SNAP)
        check((not r3) and d['cur'] == 'komyoji' and d['circles'] == base['circles'] and d['bounds'] == base['bounds'] and d['mode'] == 'playing',
              '読み込みに失敗する地域：光明寺へ戻り、取り残しなし')
        # 最後にいた地域から再開（第2章が開放済みのとき）
        await pg.evaluate("async () => { const R = window.__r; R.prog.bossDefeated = true; await R.regionTravel('testfield', null, {force: true}); }")
        await pg.wait_for_timeout(400)
        sv = await pg.evaluate(SNAP)
        check(sv['saved'] == 'testfield', '開放済みなら、いる地域が保存される')
        await pg.evaluate("() => { window.__r.continueGame(); }")
        await pg.wait_for_timeout(3000)
        e = await pg.evaluate(SNAP)
        check(e['cur'] == 'testfield' and e['px'] > 4000, f'「つづきから」で最後にいた地域から始まる（{e["cur"]}）')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: region travel' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
