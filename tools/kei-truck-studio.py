#!/usr/bin/env python3
"""KEI truck のゲーム用 GLB（assets/models/kei-truck/game/）の確認画像。docs/kei-truck-glb.md
python3 tools/kei-truck-studio.py 出力.png [broken|repaired|both] [mode]
mode:
  views（既定）：正面・背面・左・右・斜め前45°・斜め後ろ45°・上（ゲームの見た目に近いトゥーン）
  parts：車体だけ（車輪を外す）・車輪だけ（色分け）— 車輪を切り分けた所の確認
  spin：車輪を60°回し、前の車輪を切った姿（ゲームで回したとき）
  person：主人公くらいの高さ（1.7m）の棒と並べる（大きさの確認）
  open：ドア2枚を開き（60°）、あおりを下ろした姿（v0.78。斜め前・右・左の後ろ・後ろ）と、ドア・あおりだけ（色分け）
"""
import asyncio, base64, os, sys
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.environ.get('THREE_DIR', '/home/claude/v010/node_modules/three')
THREE = open(f'{T}/build/three.min.js').read()
GLTF = open(os.path.join(ROOT, 'vendor/three-r128/GLTFLoader.js')).read()
out = sys.argv[1]
which = sys.argv[2] if len(sys.argv) > 2 else 'both'
mode = sys.argv[3] if len(sys.argv) > 3 else 'views'
files = {'broken': 'assets/models/kei-truck/game/kei_truck_broken.glb', 'repaired': 'assets/models/kei-truck/game/kei_truck_repaired.glb'}
ids = ['broken', 'repaired'] if which == 'both' else [which]
B64 = {i: base64.b64encode(open(os.path.join(ROOT, files[i]), 'rb').read()).decode() for i in ids}
SIZE = int(os.environ.get('RSIZE', '420'))
JS = r"""async ([b64s, mode, S]) => { const T = THREE;
  const r = new T.WebGLRenderer({antialias: true, preserveDrawingBuffer: true}); r.setSize(S, S); r.setPixelRatio(1);
  const grad = new T.DataTexture(new Uint8Array([90, 90, 90, 255, 180, 180, 180, 255, 255, 255, 255, 255]), 3, 1, T.RGBAFormat); grad.minFilter = grad.magFilter = T.NearestFilter; grad.needsUpdate = true;
  const rows = [];
  for (const b64 of b64s) {
    const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer;
    const g = await new Promise((res, rej) => new T.GLTFLoader().parse(bin, '', res, rej));
    const sc = new T.Scene(); sc.background = new T.Color(0xe8e4da); sc.add(new T.HemisphereLight(0xffffff, 0x8a8470, 0.55)); const dl = new T.DirectionalLight(0xffffff, 0.75); dl.position.set(3, 6, 4); sc.add(dl);
    const ground = new T.Mesh(new T.CircleGeometry(4, 40), new T.MeshLambertMaterial({color: 0xb8b2a0})); ground.rotation.x = -Math.PI / 2; ground.position.y = -0.002; sc.add(ground);
    const root = g.scene; sc.add(root); const wheels = [];
    root.traverse(o => { if (o.isMesh) { const m0 = o.material; if (m0.transparent || m0.opacity < 1) o.material = new T.MeshPhongMaterial({color: m0.color, transparent: true, opacity: m0.opacity, side: T.DoubleSide, shininess: 80, depthWrite: false});
      else { if (m0.map) m0.map.encoding = T.LinearEncoding; o.material = new T.MeshToonMaterial({color: 0xffffff, map: m0.map, gradientMap: grad}); } }
      if (/^wheel_/.test(o.name)) wheels.push(o); });
    if (mode === 'parts') { const body = root.getObjectByName('body'); }
    const imgs = [];
    const shot = (pos, tgt, fov = 30) => { const cam = new T.PerspectiveCamera(fov, 1, 0.05, 100); cam.position.set(...pos); cam.lookAt(...tgt); r.render(sc, cam); imgs.push(r.domElement.toDataURL('image/png')); };
    const H = 1.05, D = 8.2;
    if (mode === 'views' || mode === 'person') {
      if (mode === 'person') { const p = new T.Mesh(new T.CylinderGeometry(0.18, 0.18, 1.7, 12), new T.MeshLambertMaterial({color: 0x3a6ea8})); p.position.set(1.45, 0.85, 0.4); sc.add(p); const hd = new T.Mesh(new T.SphereGeometry(0.13, 12, 8), new T.MeshLambertMaterial({color: 0xe8c8a8})); hd.position.set(1.45, 1.72, 0.4); sc.add(hd); }
      shot([0, H, D], [0, H, 0]); shot([0, H, -D], [0, H, 0]); shot([D, H, 0], [0, H, 0]); shot([-D, H, 0], [0, H, 0]);
      shot([D * 0.72, H + 1.8, D * 0.72], [0, 0.9, 0]); shot([-D * 0.72, H + 1.8, -D * 0.72], [0, 0.9, 0]); shot([0, 11, 0.01], [0, 0, 0], 28); }
    if (mode === 'parts') {
      for (const w of wheels) w.visible = false; shot([D * 0.72, H + 1.2, D * 0.72], [0, 0.9, 0]); shot([-D * 0.72, H + 0.6, D * 0.5], [0, 0.6, 0]);
      for (const w of wheels) w.visible = true; root.getObjectByName('body').visible = false; const ws = root.getObjectByName('windshield'); if (ws) ws.visible = false;
      const cols = [0xd04040, 0x40a040, 0x4060d0, 0xd0a020]; wheels.forEach((w, i) => w.traverse(o => { if (o.isMesh) o.material = new T.MeshLambertMaterial({color: cols[i]}); }));
      shot([D * 0.72, H + 1.2, D * 0.72], [0, 0.5, 0]); shot([-D * 0.72, H + 0.6, D * 0.5], [0, 0.4, 0]); }
    if (mode === 'open') { const dr = root.getObjectByName('door_r'), dl = root.getObjectByName('door_l'), tg = root.getObjectByName('tailgate');
      if (dr) dr.rotation.y = 1.05; if (dl) dl.rotation.y = -1.05; if (tg) tg.rotation.x = -1.5;
      shot([-D * 0.72, H + 1.2, D * 0.62], [0, 1.0, 0.3]); shot([-D * 0.9, H + 0.4, 1.2], [0, 1.1, 0.6], 24); shot([D * 0.55, H + 1.6, -D * 0.75], [0, 1.0, -0.6]); shot([0, H + 1.4, -D], [0, 1.0, -1.0], 26);
      const cols = {door_r: 0xd04040, door_l: 0x40a040, tailgate: 0x4060d0}; for (const n in cols) { const o = root.getObjectByName(n); if (o) o.traverse(q => { if (q.isMesh) q.material = new T.MeshLambertMaterial({color: cols[n], side: T.DoubleSide}); }); }
      shot([-D * 0.72, H + 1.2, D * 0.62], [0, 1.0, 0.3]); shot([D * 0.55, H + 1.6, -D * 0.75], [0, 1.0, -0.6]); }
    if (mode === 'spin') { for (const w of wheels) { w.rotation.order = 'YXZ'; w.rotation.x = Math.PI / 3; if (/^wheel_f/.test(w.name)) w.rotation.y = 0.4; }
      shot([D * 0.72, H + 1.2, D * 0.72], [0, 0.8, 0]); shot([D * 0.55, 0.6, D * 0.2], [0, 0.4, 0.8], 24); shot([0, 2.5, 6], [0, 0.4, 0.9], 30); shot([-D * 0.6, 0.7, D * 0.1], [0, 0.4, -0.85], 24); }
    rows.push(imgs);
  }
  return rows; }"""
LAB = {'views': ['正面', '背面', '左', '右', '斜め前45°', '斜め後ろ45°', '上'], 'person': ['正面', '背面', '左', '右', '斜め前45°', '斜め後ろ45°', '上'],
       'parts': ['車体だけ（斜め前）', '車体だけ（右の下）', '車輪だけ（斜め前）', '車輪だけ（右の下）'], 'spin': ['車輪を60°回し前を切る', '右前の近く', '前から', '左後ろの近く'], 'open': ['ドアとあおりを開く（斜め前）', '右のドアの近く', '左後ろから', '後ろから', '開いた部分を色分け（斜め前）', '開いた部分を色分け（左後ろ）']}


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await b.new_page()
        await pg.set_content('<html><body></body></html>')
        await pg.add_script_tag(content=THREE)
        await pg.add_script_tag(content=GLTF)
        rows = await pg.evaluate(JS, [[B64[i] for i in ids], mode, SIZE])
        names = {'broken': '修理前', 'repaired': '修理後'}
        html = '<html><body style="margin:0;background:#ccc;font:15px sans-serif">' + ''.join(
            f'<div style="display:flex;flex-wrap:wrap">' + ''.join(f'<div><div style="padding:2px 6px;background:#333;color:#fff">{names[i]}：{lab}</div><img src="{u}" style="display:block;width:{SIZE}px"></div>' for lab, u in zip(LAB[mode], row)) + '</div>'
            for i, row in zip(ids, rows)) + '</body></html>'
        n = len(rows[0])
        p2 = await (await b.new_context(viewport={'width': SIZE * min(n, 4), 'height': 300})).new_page()
        await p2.set_content(html)
        await p2.wait_for_timeout(300)
        await p2.screenshot(path=out, full_page=True)
        await b.close()
    print('wrote', out)

asyncio.run(main())
