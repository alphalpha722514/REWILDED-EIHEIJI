#!/usr/bin/env python3
"""GLB を three.js r128 で撮る（確認用）。
python3 render.py モデル.glb 出力.png [mode] [views]
mode: tex（テクスチャ）／wire（線）／normal（裏面を赤）／clay（白い粘土）／uv（UV の図）
views: front,side,back,top,q34,… を , でつなぐ。zoom=x,y,z,r（その点を中心に半径 r で撮る）
"""
import asyncio
import base64
import os
import sys

from playwright.async_api import async_playwright

T = os.environ.get('THREE_DIR', '/home/claude/v010/node_modules/three')  # three.js r128（npm の three@0.128）
THREE = open(f'{T}/build/three.min.js').read()
GLTF = open(f'{T}/examples/js/loaders/GLTFLoader.js').read()
MESHOPT = open(f'{T}/examples/js/libs/meshopt_decoder.js').read()
src, out = sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else 'tex'
views = (sys.argv[4] if len(sys.argv) > 4 else 'front,side,back,q34').split(';' if ';' in (sys.argv[4] if len(sys.argv) > 4 else '') else ',')
B64 = base64.b64encode(open(src, 'rb').read()).decode()
SIZE = int(os.environ.get('RSIZE', '640'))

JS = r"""
async ([b64, mode, views, size]) => {
  const T = THREE, W = size, H = size;
  const r = new T.WebGLRenderer({antialias: true, preserveDrawingBuffer: true}); r.setSize(W, H); r.setPixelRatio(1);
  r.outputEncoding = T.sRGBEncoding;
  const sc = new T.Scene(); sc.background = new T.Color(mode === 'normal' ? 0x222222 : 0xe6e1d6);
  sc.add(new T.HemisphereLight(0xffffff, 0x666655, 0.75)); const dl = new T.DirectionalLight(0xffffff, 0.85); dl.position.set(2, 4, 3); sc.add(dl);
  const dl2 = new T.DirectionalLight(0xffffff, 0.3); dl2.position.set(-3, 1, -2); sc.add(dl2);
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer;
  const L = new T.GLTFLoader(); if (window.MeshoptDecoder) L.setMeshoptDecoder(MeshoptDecoder);
  const g = await new Promise((res, rej) => L.parse(bin, '', res, rej));
  const root = g.scene; sc.add(root); root.updateMatrixWorld(true);
  let meshes = []; root.traverse(o => { if (o.isMesh) meshes.push(o); });
  const box = new T.Box3().setFromObject(root), ctr = box.getCenter(new T.Vector3()), sz = box.getSize(new T.Vector3());
  for (const m of meshes) {
    if (mode === 'wire') m.material = new T.MeshBasicMaterial({color: 0x202020, wireframe: true});
    else if (mode === 'clay') m.material = new T.MeshStandardMaterial({color: 0xd8d2c4, roughness: 0.9, metalness: 0});
    else if (mode === 'normal') { const front = new T.MeshLambertMaterial({color: 0x9ab8d8, side: T.FrontSide});
      const back = new T.MeshBasicMaterial({color: 0xff2020, side: T.BackSide}); const b = new T.Mesh(m.geometry, back); m.add(b); m.material = front; }
  }
  if (mode === 'wireover') for (const m of meshes) { const w = new T.Mesh(m.geometry, new T.MeshBasicMaterial({color: 0x000000, wireframe: true, transparent: true, opacity: 0.25})); m.add(w); }
  const cam = new T.PerspectiveCamera(30, W / H, 0.01, 100), out = [];
  const R = Math.max(sz.x, sz.y, sz.z) * 1.95;
  for (const v of views) {
    let tgt = ctr.clone(), dir, rad = R;
    const d = {front: [0, 0, 1], back: [0, 0, -1], side: [1, 0, 0], left: [-1, 0, 0], top: [0, 1, 0.001], bottom: [0, -1, 0.001], q34: [0.8, 0.35, 1], q34b: [-0.8, 0.35, -1]};
    if (v.startsWith('zoom=')) { const a = v.slice(5).split(',').map(Number); tgt = new T.Vector3(a[0], a[1], a[2]); rad = a[3]; dir = a.length > 4 ? [a[4], a[5], a[6]] : [0.7, 0.3, 1]; }
    else dir = d[v];
    const dv = new T.Vector3(...dir).normalize(); cam.position.copy(tgt).addScaledVector(dv, rad); cam.lookAt(tgt); cam.updateMatrixWorld();
    r.render(sc, cam); out.push(r.domElement.toDataURL('image/png'));
  }
  return {imgs: out, box: [box.min.toArray(), box.max.toArray()], tris: meshes.reduce((s, m) => s + (m.geometry.index ? m.geometry.index.count / 3 : m.geometry.attributes.position.count / 3), 0)};
}
"""


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 800, 'height': 600})).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.set_content('<html><body></body></html>')
        await pg.add_script_tag(content=THREE)
        await pg.add_script_tag(content=GLTF)
        await pg.add_script_tag(content=MESHOPT)
        res = await pg.evaluate(JS, [B64, mode, views, SIZE])
        print('box', res['box'], 'tris', res['tris'])
        html = '<body style="margin:0;background:#ccc;display:flex;flex-wrap:wrap">' + ''.join(
            f'<div style="font:16px sans-serif"><div style="padding:2px 6px">{v}</div><img src="{u}" style="display:block;width:{SIZE}px"></div>' for v, u in zip(views, res['imgs'])) + '</body>'
        p2 = await (await b.new_context(viewport={'width': SIZE * min(len(views), 4), 'height': 300})).new_page()
        await p2.set_content(html)
        await p2.screenshot(path=out, full_page=True, timeout=240000)
        if errs:
            print('errors', errs[:3])
        await b.close()

asyncio.run(main())
