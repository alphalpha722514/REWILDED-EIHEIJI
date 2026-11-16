#!/usr/bin/env python3
"""鱗の防具（v0.76 作り直し）の確認画像。部位ごと（頭・胸・脚・靴）に、正面・横・背面を寄って撮る。docs/scale-armor-v2.md

  python3 tools/scale-armor-studio2.py 出力.png [blue|raw|none] [fx|nofx|dark] [pose]
    fx   … 光・ゆらぎ・光の筋を出す（既定）。nofx … 光と演出を切る（形と色だけで違いが分かるかを見る）。dark … 暗い背景で光を見る
    pose … ゲームの中（光明寺）で、立つ・走る・通常攻撃・強攻撃・回避（飛び込み・受け身）を前と横から撮る（体へのめり込み・追従を見る）
環境変数：STUDIO_HTML（別の index.html）、THREE_JS
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
SRC = open(os.environ.get('STUDIO_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
HTML = SRC.replace('function updateNPCs(dt){', 'window.__p={get pm(){return pm},get prog(){return prog},get S(){return S},get P(){return P},get F11(){return F11},get enemies(){return enemies},get SA(){return typeof SA!=="undefined"?SA:null},f47ApplyVisual:()=>f47ApplyVisual(),animatePlayer:(a,b)=>animatePlayer(a,b),updatePlayer:dt=>updatePlayer(dt),startAttack:k=>startAttack(k),tryDodge:f=>tryDodge(f),groundH:(x,z)=>groundH(x,z),scaleFxUpdate:dt=>scaleFxUpdate(dt),renderer,scene,THREE};\nfunction updateNPCs(dt){', 1)
OUT = sys.argv[1]
SET = sys.argv[2] if len(sys.argv) > 2 else 'raw'
FXA = sys.argv[3] if len(sys.argv) > 3 else 'fx'
FX = 'dark' if FXA == 'dark' else FXA == 'fx'
POSE = len(sys.argv) > 4 and sys.argv[4] == 'pose'
POSEJS = r"""([set, W, H]) => { const T = window.__p, X = T.THREE, P = T.P, pm = T.pm, r = T.renderer; r.setSize(W, H);
  T.S.mode = 'paused'; T.F11.hold = true; for (const e of T.enemies) { e.x += 3000; e.z += 3000; } P.x = 150; P.z = 58; P.facing = 0;
  const g = T.prog.gear; for (const s of ['head', 'chest', 'legs', 'feet']) { const id = set + '_' + s; if (!g.owned.includes(id)) g.owned.push(id); g.equip[s] = id; } T.f47ApplyVisual();
  const out = [], wp = new X.Vector3();
  // 体（pm.g）の今の位置から撮る。主人公の正面は facing の向き（sin, cos）。ly：見る高さ
  const shoot = (nm, ly = 0.9) => { T.scaleFxUpdate(0.016); pm.g.updateMatrixWorld(true); pm.g.getWorldPosition(wp); for (const [vn, yaw] of [['前', 0], ['横', -Math.PI / 2]]) { const cam = new X.PerspectiveCamera(30, W / H, 0.05, 200), f = P.facing + yaw;
      cam.position.set(wp.x + Math.sin(f) * 3.2, wp.y + ly + 0.4, wp.z + Math.cos(f) * 3.2); cam.lookAt(wp.x, wp.y + ly, wp.z); r.render(T.scene, cam); out.push([nm + '・' + vn, r.domElement.toDataURL('image/png')]); } };
  for (let i = 0; i < 20; i++) T.updatePlayer(1 / 60); shoot('立つ');
  for (let i = 0; i < 9; i++) T.animatePlayer(1 / 60, 6.5); shoot('走る');
  for (const kind of ['light', 'heavy']) { P.atk = null; P.st = 999; for (let i = 0; i < 20; i++) T.updatePlayer(1 / 60); if (T.startAttack(kind) && P.atk) { const a = P.atk, hit = (a.a0 + a.a1) / 2; let k = 0; while (P.atk === a && a.t < hit && k++ < 400) T.updatePlayer(1 / 120); shoot(kind === 'light' ? '通常攻撃' : '強攻撃'); } while (P.atk) T.updatePlayer(1 / 60); }
  P.st = 999; for (let i = 0; i < 20; i++) T.updatePlayer(1 / 60); T.tryDodge(true); let fr = 0; for (const [nm, n] of [['回避・飛び込み', 7], ['回避・受け身', 15]]) { while (fr < n) { T.updatePlayer(1 / 60); fr++; } shoot(nm, 0.45); }
  return out; }"""
JS = r"""([set, fx, pose, W, H]) => { const T = window.__p, X = T.THREE, pm = T.pm, r = T.renderer; r.setSize(W, H);
  const g = T.prog.gear; for (const s of ['head', 'chest', 'legs', 'feet']) { const id = set ? set + '_' + s : null; if (id && !g.owned.includes(id)) g.owned.push(id); g.equip[s] = id || (s === 'head' ? null : 'work_' + s); } T.f47ApplyVisual();
  const SA = T.SA; if (SA) { SA.time.value = 1.3; for (const k of ['raw', 'blue', 'rawGlow', 'blueGlow']) SA[k].value = fx ? (k === 'raw' ? 0.75 : k === 'rawGlow' ? 0.75 : k === 'blueGlow' ? 0.4 : 1) : 0; }
  if (pose) { const P = T.P; P.atk = null; T.animatePlayer(0.016, 6); }
  const sc = new X.Scene(); sc.background = new X.Color(fx === 'dark' ? 0x26282c : 0xdcd6c8); sc.add(new X.HemisphereLight(0xfff4e0, 0x8a7f6a, 0.75)); const dl = new X.DirectionalLight(0xfff0dc, 0.72); dl.position.set(2, 4, 3); sc.add(dl);
  const par = pm.g.parent, p0 = pm.g.position.clone(), r0 = pm.g.rotation.y; sc.add(pm.g); pm.g.position.set(0, 0, 0); pm.g.updateMatrixWorld(true);
  const out = []; const cam = new X.PerspectiveCamera(24, W / H, 0.05, 50);
  // 部位ごとの見る高さと距離
  for (const [nm, y, d] of [['頭', 1.74, 1.75], ['胸', 1.16, 1.75], ['脚', 0.44, 1.5], ['靴', 0.12, 1.0]]) for (const [vn, a] of [['正面', 0], ['横', Math.PI / 2], ['背面', Math.PI], ['斜め前', 0.6]]) {
    pm.g.rotation.y = a; pm.g.updateMatrixWorld(true); cam.position.set(0, y + d * 0.12, d * 1.0); cam.lookAt(0, y, 0); r.render(sc, cam); out.push([nm + '・' + vn, r.domElement.toDataURL('image/png')]); }
  par.add(pm.g); pm.g.position.copy(p0); pm.g.rotation.y = r0; return out; }"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context()).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(rq):
            u = rq.request.url
            if 'three' in u: await rq.fulfill(body=THREE, content_type='application/javascript')
            elif u.startswith('http://game.local'): await rq.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            else: await rq.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__p&&window.__p.pm', timeout=300000)
        W, H = 380, 380
        if POSE:
            await pg.click('#btnNew')
            await pg.wait_for_timeout(500)
            for _ in range(15):
                if await pg.evaluate("document.getElementById('dialog').hidden"):
                    break
                await pg.click('#dialog')
                await pg.wait_for_timeout(200)
            await pg.evaluate("() => { document.getElementById('hud').hidden = true; }")
            ims = await pg.evaluate(POSEJS, [SET, W, H])
        else:
            ims = await pg.evaluate(JS, [SET if SET != 'none' else None, FX, POSE, W, H])
        await b.close()
    font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 18)
    cols = 4
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGB', (W * cols, (H + 4) * rows + 34), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    d.text((8, 6), {'raw': '変異した鱗', 'blue': '蒼鱗', 'none': '防具なし'}.get(SET, SET) + ('（光・演出あり・暗い背景）' if FX == 'dark' else '（光・演出あり）' if FX else '（光・演出なし）') + ('・ゲームの中の姿勢（立つ・走る・攻撃・回避）' if POSE else ''), fill=(0, 0, 0), font=font)
    for i, (n, u) in enumerate(ims):
        im = Image.open(io.BytesIO(base64.b64decode(u.split(',')[1]))).convert('RGB')
        x, y = (i % cols) * W, 34 + (i // cols) * (H + 4)
        sheet.paste(im, (x, y)); d.text((x + 6, y + 4), n, fill=(60, 50, 40), font=font)
    sheet.save(OUT)
    print('wrote', OUT, 'errors:', errs[:3])


asyncio.run(main())
