#!/usr/bin/env python3
"""武器の GLB の確認画像（v0.75）。画面のない Chromium・SwiftShader。docs/p2-weapon-glb.md

  python3 tools/weapon-studio.py 出力.png lineup 武器ID …   いまのコードの形（左）と GLB の形（右）を、武器の向きで並べる
        （刃の面・刃の側・背・斜め。赤い点＝当たりの根元、緑の点＝当たりの先端（WTIP）、黄の点＝握る所）
  python3 tools/weapon-studio.py 出力.png hand 武器ID …     ゲームの中で主人公が持つ姿（立つ／通常攻撃の当たる瞬間／強攻撃の当たる瞬間。前と横から）
  python3 tools/weapon-studio.py 出力.png holster 武器ID …  腰・背中に収めた姿（その武器を持っていて、ほかの武器を手に持つ）

環境変数：STUDIO_HTML（別の index.html）、THREE_JS（three.js r128）、WS_NOGLB=1（GLB を読まない＝フォールバックの確認）
"""
import asyncio
import base64
import io
import mimetypes
import os
import sys

from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('STUDIO_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
HOOK = ("window.__w={get P(){return P},get S(){return S},get prog(){return prog},get WG(){return WG},get WGLB(){return WGLB},get WTIP(){return WTIP},get enemies(){return enemies},get F11(){return F11},get pm(){return pm},get HOL(){return HOL},"
        "get weaponMesh(){return weaponMesh},get BOOM(){return BOOM},THREE,renderer,scene,camera,makeWeapon:(i,o)=>makeWeapon(i,o),makeWeaponCode:i=>makeWeaponCode(i),f47WeaponScale:i=>f47WeaponScale(i),armGain:(i,e)=>armGain(i,e),"
        "refreshWeaponMesh:()=>refreshWeaponMesh(),updatePlayer:dt=>updatePlayer(dt),startAttack:k=>startAttack(k),weaponWorld:()=>weaponWorld(),wglbFile:f=>wglbFile(f),groundH:(x,z)=>groundH(x,z),"
        "boomerMesh:()=>boomerMesh(),equipArm:i=>equipArm(i)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'

LINEUP = r"""async ([id, W, H]) => { const T = window.__w, X = T.THREE;
  const d = T.WGLB[id]; if (d) { await T.wglbFile(d.f); }
  const r = T.renderer; r.setSize(W, H);
  const sc = new X.Scene(); sc.background = new X.Color(0xe8e3d8); sc.add(new X.HemisphereLight(0xfff4e0, 0x8a7f6a, 0.8)); const dl = new X.DirectionalLight(0xfff0dc, 0.75); dl.position.set(3, 4, 5); sc.add(dl);
  const s = T.f47WeaponScale(id), a = T.makeWeaponCode(id), b = T.makeWeapon(id, {noSwap: true}); a.scale.setScalar(s); b.scale.setScalar(s);
  const pairs = [[a, 0.42], [b, -0.42]]; const dot = (c, p, par) => { const m = new X.Mesh(new X.SphereGeometry(0.03, 10, 8), new X.MeshBasicMaterial({color: c, depthTest: false})); m.position.set(...p); m.renderOrder = 9; par.add(m); };
  const wt = T.WTIP[id] || T.WTIP.nata1;
  const holders = pairs.map(([g, x]) => { const h = new X.Group(); h.position.set(0, 0, 0); h.add(g); sc.add(h); const k = new X.Group(); k.scale.setScalar(s); h.add(k); dot(0xd02020, wt[0], k); dot(0x20a030, wt[1], k); dot(0xe0c020, [0, 0, 0], k); return [h, x]; });
  const box = new X.Box3(); holders.forEach(([h]) => box.expandByObject(h)); const cy = (box.min.y + box.max.y) / 2, ext = Math.max(box.max.y - box.min.y, 1.2);
  const out = [];
  for (const [nm, dir] of [['刃の面（+x から）', [1, 0, 0]], ['刃の側（+z から）', [0, 0, 1]], ['背（-x から）', [-1, 0, 0]], ['斜め', [0.8, 0.35, 0.6]]]) {
    const cam = new X.OrthographicCamera(-ext * W / H * 0.62, ext * W / H * 0.62, ext * 0.62, -ext * 0.62, 0.01, 50);
    // 左右に並べる：カメラの右方向にずらす
    const v = new X.Vector3(...dir).normalize(), up = new X.Vector3(0, 1, 0), right = new X.Vector3().crossVectors(up, v).normalize().multiplyScalar(-1);
    holders.forEach(([h, x]) => h.position.copy(right.clone().multiplyScalar(x * ext * 0.62 * W / H)));
    cam.position.set(v.x * 6, cy + v.y * 6, v.z * 6); cam.up.set(0, 1, 0); cam.lookAt(0, cy, 0); r.render(sc, cam); out.push([nm, r.domElement.toDataURL('image/png')]); }
  return out; }"""

HAND = r"""async ([id, W, H]) => { const T = window.__w, X = T.THREE, P = T.P;
  const d = T.WGLB[id]; if (d) await T.wglbFile(d.f);
  T.S.mode = 'paused'; T.F11.hold = true; for (const e of T.enemies) { e.x += 3000; e.z += 3000; }
  P.x = 150; P.z = 58; P.facing = 0; P.hp = P.maxHp; P.st = 999; if (!(id in T.prog.arms)) T.armGain(id, true); else T.equipArm(id); T.refreshWeaponMesh();
  for (let i = 0; i < 30; i++) T.updatePlayer(1 / 60);
  const r = T.renderer; r.setSize(W, H);
  const shots = [];
  const shoot = (nm) => { T.pm.g.updateMatrixWorld(true); let mk = [];
    if (T.weaponMesh && T.weaponMesh.visible) { const [b, t] = T.weaponWorld(); for (const [c, p] of [[0xd02020, b], [0x20a030, t]]) { const m = new X.Mesh(new X.SphereGeometry(0.035, 10, 8), new X.MeshBasicMaterial({color: c, depthTest: false})); m.renderOrder = 9; m.position.copy(p); T.scene.add(m); mk.push(m); } }
    const gy = T.groundH(P.x, P.z);
    for (const [vn, yaw] of [['前', 0], ['横', -Math.PI / 2]]) { const cam = new X.PerspectiveCamera(34, W / H, 0.05, 200), f = P.facing + yaw;
      cam.position.set(P.x + Math.sin(f) * 3.4, gy + 1.35, P.z + Math.cos(f) * 3.4); cam.lookAt(P.x, gy + 0.95, P.z); r.render(T.scene, cam); shots.push([nm + '・' + vn, r.domElement.toDataURL('image/png')]); }
    mk.forEach(m => { T.scene.remove(m); m.geometry.dispose(); }); };
  shoot('立つ');
  for (const kind of ['light', 'heavy']) { P.atk = null; P.st = 999; for (let i = 0; i < 20; i++) T.updatePlayer(1 / 60);
    if (!T.startAttack(kind) || !P.atk) { continue; } const a = P.atk, hit = (a.a0 + a.a1) / 2; let g = 0; while (P.atk === a && a.t < hit && g++ < 400) T.updatePlayer(1 / 120);
    shoot(kind === 'light' ? '通常攻撃' : '強攻撃'); while (P.atk && g++ < 900) T.updatePlayer(1 / 60); }
  return shots; }"""

HOLSTER = r"""async ([id, W, H]) => { const T = window.__w, X = T.THREE, P = T.P;
  const d = T.WGLB[id]; if (d) await T.wglbFile(d.f);
  T.S.mode = 'paused'; T.F11.hold = true; for (const e of T.enemies) { e.x += 3000; e.z += 3000; }
  P.x = 150; P.z = 58; P.facing = 0; if (!(id in T.prog.arms)) T.armGain(id, false); const other = id === 'club' ? 'bamboo' : 'club'; if (!(other in T.prog.arms)) T.armGain(other, true); else T.equipArm(other); T.refreshWeaponMesh();
  await new Promise(r => setTimeout(r, 50)); for (let i = 0; i < 30; i++) T.updatePlayer(1 / 60);
  const r = T.renderer; r.setSize(W, H); const shots = []; T.pm.g.updateMatrixWorld(true); const gy = T.groundH(P.x, P.z);
  const f0 = T.pm.g.rotation.y; // 体の向き（モデルの前）
  for (const [vn, yaw, dd, ly, fov] of [['前', 0, 3.6, 0.85, 36], ['鞘の側', -Math.PI / 2, 3.6, 0.85, 36], ['後ろ', Math.PI, 3.6, 0.85, 36], ['鞘の近く（横）', -Math.PI / 2, 1.4, 0.75, 40], ['鞘の近く（前寄り）', -0.6, 1.4, 0.75, 40]]) { const cam = new X.PerspectiveCamera(fov, W / H, 0.05, 200), f = f0 + yaw;
    cam.position.set(P.x + Math.sin(f) * dd, gy + 1.15, P.z + Math.cos(f) * dd); cam.lookAt(P.x, gy + ly, P.z); r.render(T.scene, cam); shots.push(['腰・背中・' + vn, r.domElement.toDataURL('image/png')]); }
  return shots; }"""


async def main():
    out, mode, ids = sys.argv[1], sys.argv[2], sys.argv[3:]
    font = ImageFont.truetype(FONT, 18)
    rows = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 960, 'height': 600})).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append(m.text) if m.type in ('error', 'warning') and '武器' in m.text else None)

        async def route(r):
            u = r.request.url
            if 'three.min.js' in u or 'three.js/r128' in u: return await r.fulfill(body=THREE, content_type='application/javascript')
            if u.startswith('http://game.local'):
                path = u.split('http://game.local/', 1)[1].split('?')[0]
                if path in ('', 'index.html'): return await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
                if os.environ.get('WS_NOGLB') and path.endswith('.glb'): return await r.fulfill(status=404, body='')
                fp = os.path.join(ROOT, path)
                if os.path.isfile(fp): return await r.fulfill(body=open(fp, 'rb').read(), content_type=mimetypes.guess_type(fp)[0] or 'application/octet-stream')
                return await r.fulfill(status=404, body='')
            await r.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__w', timeout=300000)
        if mode in ('hand', 'holster'):
            await pg.click('#btnNew')
            await pg.wait_for_timeout(500)
            for _ in range(15):
                if await pg.evaluate("document.getElementById('dialog').hidden"):
                    break
                await pg.click('#dialog')
                await pg.wait_for_timeout(200)
            await pg.evaluate("() => { document.getElementById('hud').hidden = true; }")
        if mode == 'perf':
            print(await pg.evaluate("""async (ids) => { const T = window.__w, out = {}; const cnt = o => { let n = 0, t = 0; o.traverse(c => { if (c.isMesh && c.visible) { n++; const g = c.geometry; t += (g.index ? g.index.count : g.attributes.position.count) / 3; } }); return [n, Math.round(t)]; };
              for (const id of ids) { const d = T.WGLB[id]; const t0 = performance.now(); if (d) await T.wglbFile(d.f); const ms = Math.round(performance.now() - t0); out[id] = {code: cnt(T.makeWeaponCode(id)), glb: cnt(T.makeWeapon(id, {noSwap: true})), loadMs: ms}; }
              return JSON.stringify(out); }""", ids))
            await b.close(); return
        if mode == 'info':
            print(await pg.evaluate(HOLSTER.replace('const r = T.renderer;', 'const loc = o => { const bx = new X.Box3(); const inv = new X.Matrix4().copy(T.HOL.hip.matrixWorld).invert(); T.HOL.hip.updateMatrixWorld(true); o.updateMatrixWorld(true); o.traverse(c => { if (c.isMesh) { c.geometry.computeBoundingBox(); const b = c.geometry.boundingBox.clone().applyMatrix4(new X.Matrix4().multiplyMatrices(inv, c.matrixWorld)); bx.union(b); } }); return [bx.min.toArray().map(v => +v.toFixed(3)), bx.max.toArray().map(v => +v.toFixed(3))]; }; return JSON.stringify({sheathBox: loc(T.HOL.sheath), nataBox: loc(T.HOL.mesh.nata1), nataPar: T.HOL.mesh.nata1.parent === T.HOL.hip, nataVis: T.HOL.mesh.nata1.visible, nataWg: T.HOL.mesh.nata1.userData.wglb, hip: T.HOL.hip && T.HOL.hip.visible, sheath: T.HOL.sheath && T.HOL.sheath.visible, box: T.HOL.hipBox && T.HOL.hipBox.visible, ch: T.HOL.hip.children.map(c => [c.type, c.visible, c.children.length]), wp: T.HOL.hip.getWorldPosition(new X.Vector3()).toArray().map(v => +v.toFixed(2)), P: [P.x, P.z], arms: Object.keys(T.prog.arms), weapon: P.weapon, root: T.pm.g.position.toArray(), rootVis: T.pm.g.visible}); const r = T.renderer;'), [ids[0], 10, 10]))
            await b.close(); return
        W, H = (360, 420) if mode == 'lineup' else (340, 420)
        for wid in ids:
            js = LINEUP if mode == 'lineup' else HAND if mode == 'hand' else HOLSTER
            ims = await pg.evaluate(js, [wid, W, H])
            rows.append((wid, [(n, Image.open(io.BytesIO(base64.b64decode(u.split(',')[1]))).convert('RGB')) for n, u in ims]))
        st = await pg.evaluate("() => Object.fromEntries(Object.entries(window.__w.WG.files).map(([k, v]) => [k, v.st]))")
        await b.close()
    cols = max(len(r[1]) for r in rows)
    sheet = Image.new('RGB', (W * cols, (H + 30) * len(rows)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, (wid, ims) in enumerate(rows):
        y = i * (H + 30)
        d.text((6, y + 4), wid + ('　左：いまのコードの形／右：GLB' if mode == 'lineup' else ''), fill=(0, 0, 0), font=font)
        for j, (n, im) in enumerate(ims):
            sheet.paste(im, (j * W, y + 30)); d.text((j * W + 6, y + 32), n, fill=(60, 50, 40), font=font)
    sheet.save(out)
    print('wrote', out, 'glb:', st, 'errors:', errs[:5])


asyncio.run(main())
