#!/usr/bin/env python3
"""変異したサルの動きの確認（本編のコード mutantLoad・makeMutant・mutantPose をそのまま使う）。
python3 tools/models/mutant_anim_preview.py 出力フォルダ [動き,…]
出力：動きごとの連続画像（contact_*.png）、全部をつないだ動画（mutant_anims.mp4）、曲げた姿勢の画像（bend.png）
"""
import asyncio, base64, os, subprocess, sys
from playwright.async_api import async_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
T3 = os.environ.get('THREE_DIR', '/home/claude/v010/node_modules/three')
THREE = open(f'{T3}/build/three.min.js').read()
SRC = open(os.path.join(ROOT, os.environ.get('PREVIEW_HTML', 'index.html')), encoding='utf8').read()
DATA = open(os.path.join(ROOT, 'data/models/mutant-monkey.js'), encoding='utf8').read()
HOOK = "window.__m={mutantLoad,makeMutant,mutantPose,makeHuman,makeMonkey};\n"
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
ANIMS = (sys.argv[2].split(',') if len(sys.argv) > 2 else ['idle', 'walk', 'run', 'pounce', 'scratch', 'flinch', 'fall'])
LABEL = {'combo': 'ひっかきの二連撃（v0.62）', 'scratchL': '左の返し', 'idle': '待機', 'walk': '歩く', 'run': '四つ足で走る', 'pounce': '飛びかかり', 'scratch': 'ひっかき', 'flinch': 'ひるみ', 'fall': '倒れる'}
DUR = {'combo': 2.2, 'scratchL': 1.0, 'idle': 4.0, 'walk': 2.0, 'run': 1.4, 'pounce': 1.3, 'scratch': 1.0, 'flinch': 0.6, 'fall': 1.6}  # 撮る長さ（秒）。一度きりの動きは ph を 0→1
FPS = 24
JS = r"""async ([anims, dur, fps]) => { const T = THREE, M = window.__m, W = 720, H = 540;
  await M.mutantLoad(); await new Promise(r => setTimeout(r, 300));
  const r = new T.WebGLRenderer({antialias: true, preserveDrawingBuffer: true}); r.setSize(W, H); r.setPixelRatio(1);
  const sc = new T.Scene(); sc.background = new T.Color(0xe6e0d2); sc.add(new T.HemisphereLight(0xfff2dc, 0x6f6450, 0.6));
  const dl = new T.DirectionalLight(0xfff0d8, 0.75); dl.position.set(3, 6, 5); sc.add(dl);
  const gr = new T.Mesh(new T.PlaneGeometry(40, 40), new T.MeshBasicMaterial({color: 0xd2cab8})); gr.rotation.x = -Math.PI / 2; sc.add(gr);
  const grid = new T.GridHelper(40, 40, 0xb8ae98, 0xc4bba7); grid.position.y = 0.002; sc.add(grid);
  const m = M.makeMutant(); sc.add(m.g);
  const cam = new T.PerspectiveCamera(30, W / H, 0.1, 100);
  const frames = {};
  for (const a of anims) { const n = Math.round(dur[a] * fps), fr = [];
    for (let i = 0; i < n; i++) { const t = i / fps, ph = i / (n - 1);
      // 二連撃：右のひっかき（予備0.55秒＋振り0.12秒）→ 左の返し（予備0.32秒＋振り0.14秒）→ 戻り0.6秒。ゲームの状態の長さと同じ
      if (a === 'combo') { const T1 = 0.67, T2 = T1 + 0.46; if (t < T1) M.mutantPose(m, 'scratch', t, t < 0.55 ? 0.4 * t / 0.55 : 0.4 + 0.15 * (t - 0.55) / 0.12);
        else if (t < T2) { const u = t - T1; M.mutantPose(m, 'scratchL', t, u < 0.32 ? 0.4 * u / 0.32 : 0.4 + 0.15 * (u - 0.32) / 0.14); }
        else M.mutantPose(m, 'scratchL', t, Math.min(1, 0.55 + 0.45 * (t - T2) / 0.6)); }
      else M.mutantPose(m, a, t, ph);
      // 跳ぶ動きは、AI が体を動かす代わりに、ここで前と上へ動かす（見るため）
      let z = 0, y = 0; if (a === 'pounce') { const k = Math.max(0, Math.min(1, (ph - 0.38) / 0.4)); z = 2.6 * (k * k * (3 - 2 * k)); y = 1.0 * Math.sin(Math.PI * k); }
      if (a === 'walk') z = 2.4 * t; if (a === 'run') z = 6.0 * t;
      m.g.position.set(0, y, z - (a === 'walk' ? 2.4 : a === 'run' ? 4.2 : a === 'pounce' ? 1.3 : 0));
      m.g.updateMatrixWorld(true);
      const gp = m.g.position, ty = 0.85 + gp.y * 0.9; cam.position.set(gp.x + 5.2, ty + 1.35, gp.z + 3.4); cam.lookAt(gp.x, ty, gp.z); r.render(sc, cam); fr.push(r.domElement.toDataURL('image/jpeg', 0.9)); }
    frames[a] = fr; }
  // 曲げた姿勢（重みの確認）
  const bends = [['腕を上げる', b => { b.upperArmL.rotation.x = -2.2; b.upperArmR.rotation.x = -1.2; b.foreArmR.rotation.x = 1.2; }],
    ['脚を曲げる', b => { b.thighL.rotation.x = -1.0; b.shinL.rotation.x = 1.4; b.thighR.rotation.x = 0.6; b.shinR.rotation.x = 0.4; }],
    ['首を回す・頭を上げる', b => { b.neck.rotation.y = 0.6; b.head.rotation.y = 0.4; b.head.rotation.x = -0.5; }],
    ['尾を上げる・振る', b => { b.tail1.rotation.x = -0.7; b.tail2.rotation.x = -0.4; b.tail1.rotation.y = 0.5; b.tail3.rotation.y = 0.6; }],
    ['背を丸める・ひねる', b => { b.spine.rotation.x = 0.4; b.chest.rotation.x = 0.3; b.chest.rotation.y = 0.5; }],
    ['前腕を振り下ろす', b => { b.upperArmR.rotation.x = -0.9; b.upperArmR.rotation.z = -0.6; b.foreArmR.rotation.x = -0.5; b.handR.rotation.x = -0.6; }]];
  const bend = [];
  for (const [lab, f] of bends) { M.mutantPose(m, 'idle', 0, 0); for (const k in m.B) m.B[k].rotation.set(0, 0, 0); f(m.B); m.g.position.set(0, 0, 0); m.g.updateMatrixWorld(true);
    const out = []; for (const [cx, cz] of [[4.5, 3.4], [-4.0, 3.8]]) { cam.position.set(cx, 2.2, cz); cam.lookAt(0, 0.9, 0); r.render(sc, cam); out.push(r.domElement.toDataURL('image/jpeg', 0.9)); }
    bend.push([lab, out]); }
  return {frames, bend}; }"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 900, 'height': 500})).new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        async def route(rq):
            u = rq.request.url
            if 'three' in u: await rq.fulfill(body=THREE, content_type='application/javascript')
            elif 'mutant-monkey.js' in u: await rq.fulfill(body=DATA, content_type='application/javascript')
            elif u.startswith('http://game.local'): await rq.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            else: await rq.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__m', timeout=300000)
        res = await pg.evaluate(JS, [ANIMS, DUR, FPS])
        await b.close()
    if errs: print('page errors:', errs[:3])
    from PIL import Image, ImageDraw, ImageFont
    import io
    font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc', 28)
    fdir = os.path.join(OUT, 'frames'); os.makedirs(fdir, exist_ok=True); k = 0
    for a in ANIMS:
        imgs = [Image.open(io.BytesIO(base64.b64decode(u.split(',')[1]))).convert('RGB') for u in res['frames'][a]]
        for im in imgs:
            d = ImageDraw.Draw(im); d.text((14, 10), LABEL[a], fill=(40, 30, 20), font=font); im.save(os.path.join(fdir, f'{k:05d}.jpg'), quality=90); k += 1
        for im in imgs[-1:] * 8:  # 区切り
            im.save(os.path.join(fdir, f'{k:05d}.jpg'), quality=90); k += 1
        sel = [imgs[int(i * (len(imgs) - 1) / 5)] for i in range(6)]
        sheet = Image.new('RGB', (360 * 6, 270), 'white')
        for i, im in enumerate(sel): sheet.paste(im.resize((360, 270)), (i * 360, 0))
        sheet.save(os.path.join(OUT, f'contact_{a}.png'))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(fdir, '%05d.jpg'), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p', os.path.join(OUT, 'mutant_anims.mp4')], check=True)
    rows = []
    for lab, outs in res['bend']:
        ims = [Image.open(io.BytesIO(base64.b64decode(u.split(',')[1]))).convert('RGB').resize((480, 360)) for u in outs]
        row = Image.new('RGB', (960, 400), (233, 228, 216)); ImageDraw.Draw(row).text((10, 4), lab, fill=(40, 30, 20), font=font)
        for i, im in enumerate(ims): row.paste(im, (i * 480, 40))
        rows.append(row)
    sheet = Image.new('RGB', (1920, 400 * ((len(rows) + 1) // 2)), (233, 228, 216))
    for i, row in enumerate(rows): sheet.paste(row, ((i % 2) * 960, (i // 2) * 400))
    sheet.save(os.path.join(OUT, 'bend.png'))
    print('wrote', OUT, k, 'frames')

asyncio.run(main())
