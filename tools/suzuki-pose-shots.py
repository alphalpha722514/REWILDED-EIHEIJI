#!/usr/bin/env python3
"""スズキの動きの確認画像を撮る（ゲームの中で、本物のカメラ・光で描く）。画面のない Chromium・SwiftShader。

撮るもの（姿勢の名前をつなげて並べた1枚の画像にする）：
  wait  … ここで待て（腕を組んで待つ）
  walk  … 歩く（ついて来る）
  run   … 走る（遅れて追いつく）
  look  … 止まった主人公のまわりで立ち止まり、あたりを見る
第2段階以降で蹴り・倒れる・助け起こすを足す。

使い方：THREE_JS=…/three.min.js python3 tools/suzuki-pose-shots.py 出力.png [姿勢 …]
"""
import asyncio
import base64
import io
import os
import sys

from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SZ_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
HOOK = ("window.__w={get SZ(){return SZ},get SZP(){return SZP},get P(){return P},get S(){return S},get cam(){return cam},get prog(){return prog},get enemies(){return enemies},camera,renderer,scene,"
        "szJoin:()=>szJoin(),szFree:(...a)=>szFree(...a),szWalkable:(...a)=>szWalkable(...a),szAnimate:dt=>szAnimate(dt),animatePlayer:(a,b)=>animatePlayer(a,b),updateCamera:dt=>updateCamera(dt),groundH:(x,z)=>groundH(x,z),THREE};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
NAMES = {'wait': '待つ（腕を組む）', 'walk': '歩く', 'run': '走る', 'look': '立ち止まって見回す'}

SHOT = """([pose, view]) => { const W = window.__w, SZ = W.SZ, P = W.P, T = W.THREE;
  if (!window.__spot) { for (let zz = 60; zz < 200 && !window.__spot; zz += 4) for (let xx = 120; xx < 220; xx += 4) if (W.szFree(xx, zz, 7) && W.szWalkable(xx, zz)) { window.__spot = [xx, zz]; break; } }
  const [x, z] = window.__spot || [150, 60]; if (view === 'side') { P.x = x; P.z = z - 1.9; P.facing = 0; } else { P.x = x - 1.6; P.z = z; P.facing = 0; } SZ.x = x; SZ.z = z; SZ.rot = 0;
  SZ.pose = pose === 'wait' ? 'wait' : null; SZ.look = 0;
  const v = pose === 'walk' ? 2.2 : pose === 'run' ? 7.5 : 0; SZ.spd = v; SZ.phase = pose === 'walk' ? 1.3 : pose === 'run' ? 1.2 : 0;
  for (let k = 0; k < 40; k++) { if (pose === 'look') SZ.look = 0.55; W.szAnimate(0); }
  SZ.spd = v; W.szAnimate(0); W.animatePlayer(0, 0);
  const gy = W.groundH(x, z); const c = W.camera; const yaw = view === 'side' ? Math.PI / 2 + 0.12 : 0.25;
  W.cam.override = {p: new T.Vector3(x + Math.sin(yaw) * 4.2, gy + 1.5, z + Math.cos(yaw) * 4.2), l: new T.Vector3(x - 0.5, gy + 0.85, z), fov: 40};
  W.updateCamera(0.016); c.position.copy(W.cam.override.p); c.lookAt(W.cam.override.l); c.fov = 40; c.updateProjectionMatrix();
  W.renderer.render(W.scene, c); return W.renderer.domElement.toDataURL('image/png'); }"""


async def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'suzuki-poses.png'
    poses = sys.argv[2:] or ['wait', 'walk', 'run', 'look']
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 640, 'height': 720})).new_page()
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
        await pg.evaluate("() => { const W = window.__w; W.S.mode = 'paused'; for (const e of W.enemies) e.x += 3000; W.P.x = 148; W.P.z = 60; W.szJoin(); W.SZ.order = 'wait'; document.getElementById('hud').hidden = true; }")
        await pg.wait_for_timeout(1500)
        tiles = []
        for pose in poses:
            for view in ('front', 'side'):
                url = await pg.evaluate(SHOT, [pose, view])
                await pg.wait_for_timeout(100)
                url = await pg.evaluate(SHOT, [pose, view])
                im = Image.open(io.BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGB')
                tiles.append((pose, view, im))
        if errs:
            print('page errors:', errs[:3])
        await b.close()
    w, h = tiles[0][2].size
    tw, th = w // 2, h // 2
    sheet = Image.new('RGB', (tw * 2, (th + 34) * len(poses)), (232, 226, 214))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 22)
    except Exception:
        f = ImageFont.load_default()
    for i, (pose, view, im) in enumerate(tiles):
        r, c = i // 2, i % 2
        sheet.paste(im.resize((tw, th)), (c * tw, r * (th + 34) + 34))
        if c == 0:
            d.text((10, r * (th + 34) + 5), NAMES.get(pose, pose) + '（左：前から・右：横から）', fill=(40, 40, 40), font=f)
    sheet.save(out)
    print('wrote', out)


asyncio.run(main())
