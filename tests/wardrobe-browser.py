#!/usr/bin/env python3
"""v0.60 着替えの確認（画面のない Chromium で実行。数分かかる）。

- 初期の服の主人公の三角形の並びが、v0.59.1 の主人公と同じ（見た目を変えていない）こと
- 脱ぐと下着が出る／帽子で髪をしまう／3組の服と組み合わせが作れる／エラーがないこと

使い方：THREE_JS=…/three.min.js python3 tests/wardrobe-browser.py
"""
import asyncio
import hashlib
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
HTML = SRC.replace('function updateNPCs(dt){', 'window.__w={makeHuman,F60_GARMENTS};\nfunction updateNPCs(dt){', 1)
# v0.59.1（main c4784db）の主人公：三角形 25,586・並びの SHA-1
BASE_TRIS = 76758 // 3
BASE_SHA1 = os.environ.get('WARDROBE_BASE_SHA1', '41e093ee1071b1bf9219e30cc49570779b625824')

JS = """() => { const W = window.__w, m = W.makeHuman({player47: true}), g = m.skin.geometry, out = {};
  const ix = () => Array.from(g.index.array.slice(0, g.drawRange.count));
  out.base = ix(); out.stat = m.stat;
  m.setWear({chest: 'none', legs: 'none', feet: 'none'}); out.naked = g.drawRange.count; out.under = m.stat;
  m.setWear({head: 'tracker_head'}); m.wardrobe.ensure('tracker_head', 'head', W.F60_GARMENTS.tracker.head); m.setWear({head: 'tracker_head'});
  out.hatOn = m.wardrobe.W.gar.tracker_head.grp.visible;
  for (const set of ['basic', 'forest', 'tracker']) for (const slot of ['head', 'chest', 'legs', 'feet']) m.wardrobe.ensure(set + '_' + slot, slot, W.F60_GARMENTS[set][slot]);
  m.setWear({chest: 'forest_chest', legs: 'tracker_legs', feet: 'basic_feet', head: 'none'});
  out.mix = Object.entries(m.wardrobe.W.gar).filter(([k, v]) => v.grp.visible).map(([k]) => k).sort();
  m.setWear({}); out.back = ix().length; return out; }"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context()).new_page()
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
        await pg.wait_for_function('window.__w', timeout=300000)
        r = await pg.evaluate(JS)
        await b.close()
    sha = hashlib.sha1(json.dumps(r['base']).encode()).hexdigest()
    ok = True
    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg)
        ok = ok and c
    check(len(r['base']) // 3 == BASE_TRIS and sha == BASE_SHA1, f'初期の服の主人公が v0.59.1 と同じ（三角形 {len(r["base"])//3}、{sha[:10]}）')
    check(r['naked'] > len(r['base']), '脱ぐと下着の面が増える')
    check(r['hatOn'], '帽子をかぶれる')
    check(r['mix'] == ['basic_feet', 'forest_chest', 'tracker_legs'], f'組み合わせ：{r["mix"]}')
    check(r['back'] == len(r['base']), '全部初期の服に戻すと元どおり')
    check(not errs, f'エラーなし {errs[:2]}')
    print('PASS: wardrobe' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
