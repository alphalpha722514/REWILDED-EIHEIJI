#!/usr/bin/env python3
"""v0.86.1 料理の絵（ChatGPT で作った絵 19枚）の確認（画面のない Chromium。2分ほど）。docs/food-image-request.md

- 19枚の絵（assets/food/<料理ID>.webp）をすべて読み、手持ちバー・持ち物の絵がその絵になる（256×256）
- 生の食材（食料・肉・野菜・米）と魚・カニは今までの絵のまま
- 絵が読めないとき（ファイルが無い）は今までの立体の絵のまま・エラーなし
- 試遊版（previews/…/index.html）からも読める（../../assets/food/）
- FOOD_SHOTS=フォルダ で手持ちバーと持ち物の画面を撮る

使い方：THREE_JS=…/three.min.js python3 tests/food-art-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
INJ = lambda s: s.replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){', 1)
HTML = INJ(open(os.path.join(ROOT, 'index.html'), encoding='utf8').read())
SHOTS = os.environ.get('FOOD_SHOTS')
DISHES = ['onigiri', 'bento', 'grilledVeg', 'herbPorridge', 'gomadofu', 'koroni', 'kushi', 'katsudon', 'botan', 'ayuShio', 'keiShio', 'ayuMeshi', 'koikoku', 'funaKanro', 'kawaKushi', 'zakoTen', 'kawaZosui', 'zuganiJiru', 'nigoiTsumire']


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])

        async def session(page_path='', no_food=False):
            ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
            pg = await ctx.new_page()
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            got = []

            async def route(r):
                u = r.request.url
                if 'three.min.js' in u or 'three.js/r128' in u:
                    return await r.fulfill(body=THREE, content_type='application/javascript')
                if u.startswith('http://game.local'):
                    path = u.split('http://game.local/', 1)[1].split('?')[0]
                    if path in ('', 'index.html'):
                        return await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
                    if path == page_path:
                        return await r.fulfill(body=INJ(open(os.path.join(ROOT, path), encoding='utf8').read()), content_type='text/html; charset=utf-8')
                    if '/food/' in path and path.endswith('.webp'):
                        got.append(path)
                        if no_food:
                            return await r.fulfill(status=404, body='')
                    fp = os.path.join(ROOT, path)
                    if os.path.isfile(fp):
                        return await r.fulfill(body=open(fp, 'rb').read(), content_type='image/webp' if path.endswith('.webp') else None)
                    return await r.fulfill(status=404, body='')
                await r.abort()
            await ctx.route('**/*', route)
            await pg.goto('http://game.local/' + page_path, wait_until='load', timeout=300000)
            await pg.wait_for_function("typeof window.__ev==='function'", timeout=300000)
            return ctx, pg, errs, got

        # ---- 本編 ----
        ctx, pg, errs, got = await session()
        E = lambda c: pg.evaluate('(c)=>window.__ev(c)', c)
        for _ in range(100):
            if await E("Object.keys(FOOD_ART_OK).length") >= 19:
                break
            await pg.wait_for_timeout(200)
        r = await E("""(()=>{ const L=FOOD_ART.map(id=>[id, ICONS[id]===FOOD_ART_OK[id]&&FOOD_ART_OK[id]==='assets/food/'+id+'.webp']);
          return [FOOD_ART.length, L.filter(x=>x[1]).length, JSON.stringify(FOOD_ART.slice().sort())===JSON.stringify(COOKED.concat(Object.keys(FISH_DISH)).sort())]; })()""")
        check(r == [19, 19, True], f'19枚（かまどの料理9品・魚料理10品）をすべて読み、絵がその絵になる {r}')
        sz = await pg.evaluate("""async (ids) => { const out=[]; for(const id of ids){ const im=new Image(); im.src='assets/food/'+id+'.webp'; await im.decode(); out.push(im.naturalWidth+'x'+im.naturalHeight); } return [...new Set(out)]; }""", DISHES)
        check(sz == ['256x256'], f'絵の大きさ 256×256 {sz}')
        raw = await E("['food','meat','veg','rice','fAyu','zugani'].map(id=>(iconOf(id)||'').startsWith('data:image/png'))")
        check(all(raw), f'生の食材・魚・カニは今までの絵のまま {raw}')
        # 手持ちバーと持ち物
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await E("(()=>{ for(const k of ['onigiri','bento','katsudon','botan','ayuShio','zuganiJiru','koroni']) foodAdd(k,2); hbBuild(); hbRefresh(); return 1; })()")
        await pg.wait_for_timeout(800)
        hb = await E("[...document.querySelectorAll('#items img')].map(i=>i.getAttribute('src')||'').filter(s=>s.startsWith('assets/food/')).map(s=>s.slice(12))")
        if not hb:
            print('  debug', await E("[$('items')&&$('items').innerHTML.slice(0,400), ICONS.onigiri&&ICONS.onigiri.slice(0,40)]"))
        check(len(hb) >= 6 and 'onigiri.webp' in hb and 'katsudon.webp' in hb, f'手持ちバー：料理の絵 {hb}')
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            await pg.screenshot(path=os.path.join(SHOTS, 'hotbar.png'), timeout=300000)
        await E("(openInv(), 1)")
        await pg.wait_for_timeout(800)
        iv = await E("[...document.querySelectorAll('#invGrid img.fic')].map(i=>i.getAttribute('src').slice(12))")
        check(len(iv) == 7 and 'onigiri.webp' in iv and 'zuganiJiru.webp' in iv, f'持ち物の画面：料理の行に絵（おにぎり・精進弁当と「食べる」の行）{iv}')
        if SHOTS:
            await pg.screenshot(path=os.path.join(SHOTS, 'inventory.png'), timeout=300000)
        await E("(closeOverlay(), 1)")
        st = await E("(()=>{ renderStore(); return [...document.querySelectorAll('#storeList img.fic')].length; })()")
        check(st == 19, f'食料庫の画面：料理19品の行に絵 {st}')
        check(not errs, f'エラーなし（本編）{errs[:3]}')
        await ctx.close()

        # ---- 絵が読めないとき ----
        ctx, pg, errs, got = await session(no_food=True)
        E = lambda c: pg.evaluate('(c)=>window.__ev(c)', c)
        await pg.wait_for_timeout(3000)
        nf = await E("[Object.keys(FOOD_ART_OK).length, (iconOf('onigiri')||'').startsWith('data:image/png'), (iconOf('katsudon')||'').startsWith('data:image/png')]")
        check(nf == [0, True, True] and len(got) >= 19, f'絵が読めないときは今までの立体の絵のまま（{len(got)}回 試した）{nf}')
        check(not errs, f'エラーなし（絵が無いとき）{errs[:3]}')
        await ctx.close()

        # ---- 試遊版 ----
        pv = 'previews/p2-story/index.html'
        if os.path.isfile(os.path.join(ROOT, pv)) and 'foodArtLoad' in open(os.path.join(ROOT, pv), encoding='utf8').read():
            ctx, pg, errs, got = await session(pv)
            E = lambda c: pg.evaluate('(c)=>window.__ev(c)', c)
            for _ in range(100):
                if await E("Object.keys(FOOD_ART_OK).length") >= 19:
                    break
                await pg.wait_for_timeout(200)
            pr = await E("[Object.keys(FOOD_ART_OK).length, FOOD_ART_OK.onigiri]")
            check(pr == [19, '../../assets/food/onigiri.webp'], f'試遊版からも読める（../../assets/food/）{pr}')
            check(not errs, f'エラーなし（試遊版）{errs[:3]}')
            await ctx.close()
        else:
            print('skip 試遊版（まだ作り直していない）')
        await b.close()
    print('PASS: 料理の絵' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
