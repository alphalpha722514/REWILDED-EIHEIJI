#!/usr/bin/env python3
"""画面の配置（手持ちバー・操作表・ボタン）の確認。画面のない Chromium・SwiftShader（数分）。

PC：操作表（#help）が手持ちバー（#items）・調べる帯（#prompt）・時計回りの通知（#toasts）に重ならない。手持ちバーは画面の下。
スマホ（タッチ・横向き／縦向き）：手持ちバーは画面の下。スティックの範囲・戦いのボタン・調べる帯に重ならない。画面からはみ出さない。
環境変数：HUD_SHOTS=フォルダ（大きさごとの画面）、HUD_HTML=別の index.html、THREE_JS
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('HUD_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
SHOTS = os.environ.get('HUD_SHOTS')
HOOK = "window.__h={enableTouch:()=>enableTouch(),get S(){return S},get touchMode(){return touchMode},toast:m=>toast(m)};\n"
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
PC = [(1024, 768), (1280, 720), (1366, 768), (1440, 900), (1536, 864), (1920, 1080), (900, 600), (780, 560), (1180, 700)]
TOUCH = [('iPhone 13 横', 844, 390), ('iPhone SE 横', 667, 375), ('iPhone Pro Max 横', 932, 430), ('iPhone 13 縦', 390, 844), ('iPhone SE 縦', 375, 667), ('iPad 横', 1180, 820), ('iPad 縦', 820, 1180)]
# 調べる帯を長めの文で出す・持ち替え／衝撃波のボタンも出す（いちばん混む形で比べる）
FILL = """() => { const pr = document.getElementById('prompt'); pr.hidden = false; pr.innerHTML = '<span class="k">E</span>KEI truck を直す（木材 0/10・屑鉄 0/6・縄 0/4・石 0/6・竹 0/3・部品 0/2・燃料 0/1）';
  for (const id of ['tbSwap', 'tbWave', 'bossBar', 'coreBar']) document.getElementById(id).hidden = false;
  const t = document.getElementById('toasts'); if (!t.children.length) window.__h.toast('素材が足りない：木材 0/10・屑鉄 0/6・縄 0/4（試しの通知）'); }"""
UNFILL = """() => { for (const id of ['bossBar', 'coreBar', 'tbWave']) document.getElementById(id).hidden = true; for (const x of [...document.getElementById('toasts').children]) x.remove(); }"""
RECTS = """() => { (""" + FILL + """)(); const r = id => { const e = document.getElementById(id); if (!e) return null; const cs = getComputedStyle(e); if (e.hidden || cs.display === 'none' || cs.visibility === 'hidden') return null;
    let b = e.getBoundingClientRect(); if (id === 'items') { const s = [...e.children].map(c => c.getBoundingClientRect()).filter(q => q.width > 0); if (s.length) b = {left: Math.min(...s.map(q => q.left)), top: Math.min(...s.map(q => q.top)), right: Math.max(...s.map(q => q.right)), bottom: Math.max(...s.map(q => q.bottom))}; }
    return b.right - b.left > 0 ? {l: Math.round(b.left), t: Math.round(b.top), r: Math.round(b.right), b: Math.round(b.bottom)} : null; };
  const ids = ['items', 'help', 'prompt', 'toasts', 'bossBar', 'coreBar', 'stats', 'res', 'mini', 'objective', 'tbAtk', 'tbHeavy', 'tbSwap', 'tbDodge', 'tbWave', 'tbAct', 'tbMap', 'tbPause'];
  return {W: innerWidth, H: innerHeight, touch: document.body.classList.contains('touchmode'), slots: document.getElementById('items').children.length, ...Object.fromEntries(ids.map(i => [i, r(i)]))}; }"""


def hit(a, b, pad=0):
    return a and b and a['l'] < b['r'] + pad and b['l'] < a['r'] + pad and a['t'] < b['b'] + pad and b['t'] < a['b'] + pad


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg, flush=True)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(r):
            u = r.request.url
            if 'three.min.js' in u or 'three.js/r128' in u: return await r.fulfill(body=THREE, content_type='application/javascript')
            if u.startswith('http://game.local'):
                path = u.split('http://game.local/', 1)[1].split('?')[0]
                if path in ('', 'index.html'): return await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
                fp = os.path.join(ROOT, path)
                if os.path.isfile(fp): return await r.fulfill(body=open(fp, 'rb').read())
                return await r.fulfill(status=404, body='')
            await r.abort()
        await ctx.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__h', timeout=300000)
        await pg.click('#btnNew', timeout=240000)
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await pg.wait_for_function("window.__h.S.mode === 'playing'", timeout=120000)

        async def measure(name, w, h):
            await pg.set_viewport_size({'width': w, 'height': h})
            await pg.wait_for_function("document.getElementById('items').children.length >= 10", timeout=60000)
            await pg.wait_for_timeout(900)
            if SHOTS:  # 画面はふだんの姿（測るために出す帯・ボタンは出さない）
                os.makedirs(SHOTS, exist_ok=True)
                try:
                    await pg.screenshot(path=os.path.join(SHOTS, f'{name}_{w}x{h}.png'.replace(' ', '_')), timeout=180000)
                except Exception as e:
                    print('  （画面を撮れなかった）', str(e)[:60])
            R = await pg.evaluate(RECTS)
            await pg.evaluate(UNFILL)
            return R

        # ---- PC ----
        for (w, h) in PC:
            R = await measure('PC', w, h)
            it, hp = R['items'], R['help']
            print(f'   PC {w}x{h}: 手持ち {it} 操作表 {hp} 帯 {R["prompt"]}')
            check(it and h - it['b'] < 40 and it['l'] >= 0 and it['r'] <= w, f'PC {w}×{h}：手持ちバーは画面の下・画面の中')
            check(not hit(hp, it, 6), f'PC {w}×{h}：操作表が手持ちバーに重ならない')
            check(not hit(hp, R['prompt'], 4) and not hit(it, R['prompt'], 4), f'PC {w}×{h}：操作表・手持ちバーが調べる帯に重ならない')
            check(not hit(hp, R['bossBar'], 4) and not hit(it, R['bossBar'], 4) and not hit(R['prompt'], R['bossBar'], 2), f'PC {w}×{h}：操作表・手持ちバー・調べる帯が強敵の体力に重ならない')
            check(not hit(hp, R['toasts'], 4) and not hit(it, R['toasts'], 4), f'PC {w}×{h}：操作表・手持ちバーが通知に重ならない {R["toasts"]}')
            check(not hit(hp, R['stats'], 4) and not hit(hp, R['coreBar'], 4) and not hit(hp, R['res'], 4) and not hit(hp, R['mini'], 4), f'PC {w}×{h}：操作表が体力・防衛の耐久・素材・地図に重ならない {[k for k in ("stats", "coreBar", "res", "mini") if hit(hp, R[k], 4)]} {R["coreBar"]}')
            check(not hp or (hp['l'] >= 0 and hp['t'] >= 0 and hp['b'] <= h), f'PC {w}×{h}：操作表が画面の中')
        # ---- スマホ（タッチ）----
        await pg.evaluate("window.__h.enableTouch()")
        await pg.wait_for_function("!document.getElementById('touch').hidden", timeout=30000)
        for (name, w, h) in TOUCH:
            R = await measure('touch_' + name, w, h)
            it = R['items']
            tbs = [k for k in ('tbAtk', 'tbHeavy', 'tbSwap', 'tbDodge', 'tbWave', 'tbAct', 'tbMap', 'tbPause') if R[k]]
            over = [k for k in tbs if hit(it, R[k], 4)]
            print(f'   {name} {w}x{h}: 手持ち {it} 帯 {R["prompt"]} ボタン {[(k, R[k]) for k in ("tbHeavy", "tbSwap", "tbAtk")]}')
            check(R['touch'] and it and h - it['b'] < 60 and it['t'] > h * 0.55, f'{name} {w}×{h}：手持ちバーは画面の下（下の端から {h - it["b"] if it else "?"}px）')
            check(it and it['l'] >= 0 and it['r'] <= w, f'{name} {w}×{h}：手持ちバーが画面からはみ出さない')
            check(not over, f'{name} {w}×{h}：手持ちバーがボタンに重ならない {over}')
            check(not hit(it, R['prompt'], 4) and not hit(it, R['bossBar'], 4) and not hit(it, R['toasts'], 4), f'{name} {w}×{h}：手持ちバーが調べる帯・強敵の体力・通知に重ならない')
            check(not [k for k in tbs if hit(R['prompt'], R[k], 0)], f'{name} {w}×{h}：調べる帯がボタンに重ならない {[k for k in tbs if hit(R["prompt"], R[k], 0)]}')
            sw = (it['r'] - it['l']) / max(1, R['slots']) if it else 0
            check(sw >= 28, f'{name} {w}×{h}：手持ちの枠は指で押せる大きさ（1つ 約{sw:.0f}px）')
        # ---- 指で手持ちの枠：触れて動かした（スティックのつもり）では選ばない・動かさずに離すと選ぶ ----
        await pg.set_viewport_size({'width': 844, 'height': 390})
        await pg.wait_for_timeout(800)
        await pg.evaluate("() => { document.getElementById('prompt').hidden = true; for (const t of [...document.getElementById('toasts').children]) t.remove(); }")
        c = await pg.evaluate("() => { const b = document.getElementById('items').children[9].getBoundingClientRect(); return [b.left + b.width / 2, b.top + b.height / 2]; }")
        cdp = await ctx.new_cdp_session(pg)
        async def touch(kind, x, y):
            await cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [] if kind == 'touchEnd' else [{'x': x, 'y': y, 'id': 1}]})
        await touch('touchStart', c[0], c[1])
        for k in range(1, 6):
            await touch('touchMove', c[0] - 12 * k, c[1] - 6 * k)
            await pg.wait_for_timeout(40)
        await touch('touchEnd', 0, 0)
        await pg.wait_for_timeout(500)
        m1 = await pg.evaluate("window.__h.S.mode")
        await touch('touchStart', c[0], c[1])
        await pg.wait_for_timeout(80)
        await touch('touchEnd', 0, 0)
        await pg.wait_for_timeout(800)
        m2 = await pg.evaluate("window.__h.S.mode")
        check(m1 == 'playing' and m2 == 'menu', f'指で手持ちの枠（10番目＝持ち物）：触れて動かすと選ばない（{m1}）・動かさずに離すと開く（{m2}）')
        check(not errs, f'エラーなし {errs[:2]}')
        await b.close()
    print('PASS: 画面の配置' if ok else 'FAIL', flush=True)
    sys.exit(0 if ok else 1)

asyncio.run(main())
