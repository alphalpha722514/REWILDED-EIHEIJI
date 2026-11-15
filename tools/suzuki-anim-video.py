#!/usr/bin/env python3
"""スズキの動きの確認動画を作る（ゲームの中の光とカメラで1コマずつ描いて、動画にする）。画面のない Chromium・SwiftShader と ffmpeg。

順に：待つ（腕を組む）→ 歩く → 走る → 戦いの間の腿上げ → ローキック → 後ろ回し蹴り → 飛び蹴り → 倒れる → 起き上がる
使い方：THREE_JS=…/three.min.js python3 tools/suzuki-anim-video.py 出力.mp4
"""
import asyncio
import base64
import io
import os
import shutil
import subprocess
import sys
import tempfile

from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SZ_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
HOOK = ("window.__w={get SZ(){return SZ},get SZK(){return SZK},get SZF(){return SZF},get P(){return P},get S(){return S},get cam(){return cam},get enemies(){return enemies},camera,renderer,scene,THREE,"
        "szJoin:()=>szJoin(),szFree:(...a)=>szFree(...a),szAnimate:dt=>szAnimate(dt),animatePlayer:(a,b)=>animatePlayer(a,b),updateCamera:dt=>updateCamera(dt),groundH:(x,z)=>groundH(x,z)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
FPS = 15
# [名前, 長さ（秒）, 種類]
SEGS = [('待つ（腕を組む）', 1.6, 'wait'), ('歩く', 1.6, 'walk'), ('走る', 1.6, 'run'), ('戦いの間の腿上げ', 2.0, 'knee'),
        ('ローキック', 0.9, 'low'), ('後ろ回し蹴り', 1.0, 'spin'), ('飛び蹴り', 1.3, 'jump'), ('倒れる', 1.6, 'down'), ('起き上がる', 1.0, 'up')]

FRAME = """([kind, t, dt]) => { const W = window.__w, SZ = W.SZ, T = W.THREE; const [x, z] = window.__spot;
  SZ.x = x; SZ.z = z; SZ.rot = 0; SZ.pose = null; SZ.fight = false; SZ.kick = null; SZ.down = false; SZ.upT = 0; SZ.stagger = 0; SZ.spd = 0;
  if (kind === 'wait') SZ.pose = 'wait';
  if (kind === 'walk') SZ.spd = 2.2;
  if (kind === 'run') SZ.spd = 7.5;
  if (kind === 'knee') SZ.fight = true;
  if (kind === 'low') SZ.kick = {id: 'low', K: W.SZK.low, t: t % W.SZK.low.dur, atk: {}};
  if (kind === 'spin' || kind === 'jump') SZ.kick = {id: kind, K: W.SZK[kind], t: Math.min(t, W.SZK[kind].dur - 0.001), atk: {}};
  if (kind === 'down') { SZ.down = true; SZ.downT = t; }
  if (kind === 'up') { SZ.upT = Math.max(0.0001, W.SZF.upT - t); }
  W.szAnimate(dt);
  const gy = W.groundH(x, z), c = W.camera, yaw = 0.7;
  W.cam.override = {p: new T.Vector3(x + Math.sin(yaw) * 4.6, gy + 1.9, z + Math.cos(yaw) * 4.6), l: new T.Vector3(x, gy + 0.75, z + 0.5), fov: 42};
  W.updateCamera(0.016); c.position.copy(W.cam.override.p); c.lookAt(W.cam.override.l); c.fov = 42; c.updateProjectionMatrix();
  W.renderer.render(W.scene, c); return W.renderer.domElement.toDataURL('image/jpeg', 0.9); }"""


async def main():
    out = sys.argv[1] if len(sys.argv) > 1 else 'suzuki-anim.mp4'
    tmp = tempfile.mkdtemp(prefix='szvid_')
    try:
        f = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 26)
    except Exception:
        f = ImageFont.load_default()
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 640, 'height': 480})).new_page()

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
        await pg.evaluate("""() => { const W = window.__w; W.S.mode = 'paused'; for (const e of W.enemies) e.x += 3000; document.getElementById('hud').hidden = true;
          let sp = null; for (let zz = 60; zz < 200 && !sp; zz += 4) for (let xx = 120; xx < 220; xx += 4) if (W.szFree(xx, zz, 7)) { sp = [xx, zz]; break; } window.__spot = sp;
          W.P.x = sp[0] - 2.2; W.P.z = sp[1] - 1.0; W.P.facing = 0.6; W.szJoin(); W.animatePlayer(0, 0); }""")
        n = 0
        dt = 1 / FPS
        for name, sec, kind in SEGS:
            for i in range(int(sec * FPS)):
                url = await pg.evaluate(FRAME, [kind, i * dt, dt])
                im = Image.open(io.BytesIO(base64.b64decode(url.split(',')[1]))).convert('RGB')
                d = ImageDraw.Draw(im)
                d.rectangle([0, 0, im.width, 40], fill=(30, 30, 30))
                d.text((12, 4), name, fill=(245, 239, 223), font=f)
                im.save(os.path.join(tmp, f'f{n:04d}.jpg'), quality=92)
                n += 1
        await b.close()
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.jpg'), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', out], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print('wrote', out, n, 'frames')


asyncio.run(main())
