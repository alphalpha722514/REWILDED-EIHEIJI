"""正投影で撮って座標の目盛りを描く（部位の位置を読むため）。python3 ortho.py モデル.glb 出力.png view[,view] [x0,x1,y0,y1]
view: pz（+Z から：横顔。横軸 X、縦軸 Y）／px（+X から：正面。横軸 -Z→Z）／nx（-X から：背面）／py（上から。横軸 X、縦軸 Z）"""
import asyncio, base64, os, sys
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont
import io
T = os.environ.get('THREE_DIR', '/home/claude/v010/node_modules/three')
THREE = open(f'{T}/build/three.min.js').read(); GLTF = open(f'{T}/examples/js/loaders/GLTFLoader.js').read(); MO = open(f'{T}/examples/js/libs/meshopt_decoder.js').read()
src, out, views = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
rng = [float(v) for v in sys.argv[4].split(',')] if len(sys.argv) > 4 else [-0.55, 0.55, -0.55, 0.55]
mode = sys.argv[5] if len(sys.argv) > 5 else 'clay'
B64 = base64.b64encode(open(src, 'rb').read()).decode()
S = 900
JS = r"""async ([b64, views, rng, S, mode]) => { const T = THREE;
  const r = new T.WebGLRenderer({antialias: true, preserveDrawingBuffer: true}); r.setSize(S, S); r.setPixelRatio(1);
  const sc = new T.Scene(); sc.background = new T.Color(0xf4f1ea); sc.add(new T.HemisphereLight(0xffffff, 0x777766, 0.8)); const dl = new T.DirectionalLight(0xffffff, 0.7); dl.position.set(2, 3, 4); sc.add(dl);
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer; const L = new T.GLTFLoader(); L.setMeshoptDecoder(MeshoptDecoder);
  const g = await new Promise((res, rej) => L.parse(bin, '', res, rej)); sc.add(g.scene);
  if (mode === 'clay') g.scene.traverse(o => { if (o.isMesh) o.material = new T.MeshLambertMaterial({color: 0xcfc6b4, side: T.DoubleSide}); });
  else g.scene.traverse(o => { if (o.isMesh && o.material.map) o.material.map.encoding = T.LinearEncoding; });
  const [x0, x1, y0, y1] = rng, out = [];
  for (const v of views) {
    const cam = new T.OrthographicCamera(x0, x1, y1, y0, 0.01, 10);
    if (v === 'pz') { cam.position.set(0, 0, 3); cam.up.set(0, 1, 0); cam.lookAt(0, 0, 0); }
    if (v === 'px') { cam.position.set(3, 0, 0); cam.up.set(0, 1, 0); cam.lookAt(0, 0, 0); }
    if (v === 'nx') { cam.position.set(-3, 0, 0); cam.up.set(0, 1, 0); cam.lookAt(0, 0, 0); }
    if (v === 'py') { cam.position.set(0, 3, 0); cam.up.set(0, 0, -1); cam.lookAt(0, 0, 0); }
    cam.updateProjectionMatrix(); r.render(sc, cam); out.push(r.domElement.toDataURL('image/png')); }
  return out; }"""
LAB = {'pz': ('X', 'Y'), 'px': ('-Z→+Z (画面右=+Z の反対)', 'Y'), 'nx': ('Z', 'Y'), 'py': ('X', 'Z')}
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context()).new_page(); await pg.set_content('<html></html>')
        for s in (THREE, GLTF, MO): await pg.add_script_tag(content=s)
        imgs = await pg.evaluate(JS, [B64, views, rng, S, mode]); await b.close()
    font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc', 14)
    tiles = []
    for v, u in zip(views, imgs):
        im = Image.open(io.BytesIO(base64.b64decode(u.split(',')[1]))).convert('RGB'); d = ImageDraw.Draw(im)
        x0, x1, y0, y1 = rng
        def gx(val, flip=False): return (val - x0) / (x1 - x0) * S if not flip else (x1 - val) / (x1 - x0) * S
        step = 0.05
        k = round(x0 / step)
        while k * step <= x1 + 1e-9:
            val = k * step; px = (val - x0) / (x1 - x0) * S
            d.line([(px, 0), (px, S)], fill=(255, 0, 0) if abs(val) < 1e-9 else (190, 190, 230) if k % 2 else (120, 120, 200), width=1)
            if k % 2 == 0: d.text((px + 2, 2), f'{val:.1f}' if v not in ('px',) else f'{val:.1f}', fill=(40, 40, 160), font=font)
            k += 1
        k = round(y0 / step)
        while k * step <= y1 + 1e-9:
            val = k * step; py = (y1 - val) / (y1 - y0) * S
            d.line([(0, py), (S, py)], fill=(255, 0, 0) if abs(val) < 1e-9 else (190, 230, 190) if k % 2 else (90, 160, 90), width=1)
            if k % 2 == 0: d.text((2, py + 1), f'{val:.1f}', fill=(30, 110, 30), font=font)
            k += 1
        d.text((S - 260, S - 22), f'{v}: 横={LAB[v][0]} 縦={LAB[v][1]}', fill=(0, 0, 0), font=font)
        tiles.append(im)
    o = Image.new('RGB', (S * len(tiles), S), 'white')
    for i, t in enumerate(tiles): o.paste(t, (i * S, 0))
    o.save(out); print('wrote', out)
asyncio.run(main())
