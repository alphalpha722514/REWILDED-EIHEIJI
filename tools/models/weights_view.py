"""重みの確認：頂点を「一番重い骨」の色で点として描く。python3 weights_view.py 重み.json 出力.png"""
import asyncio, json, os, sys
from playwright.async_api import async_playwright
T = os.environ.get('THREE_DIR', '/home/claude/v010/node_modules/three')
THREE = open(f'{T}/build/three.min.js').read()
D = open(sys.argv[1]).read(); OUT = sys.argv[2]
JS = r"""async (d) => { const T = THREE, W = 520, H = 560; const r = new T.WebGLRenderer({antialias: true, preserveDrawingBuffer: true}); r.setSize(W, H); r.setPixelRatio(1);
  const sc = new T.Scene(); sc.background = new T.Color(0x202020);
  const pal = [0xffffff, 0xff4040, 0xffa040, 0xffff40, 0x40ff40, 0x40ffff, 0xff40ff, 0xc080ff, 0x8080ff, 0xff8080, 0xffc0a0, 0x40a0ff, 0xa0ff40, 0xffd040, 0x00c080, 0xff0080, 0x80c0ff, 0xc0ff80, 0xff8040, 0x60ffd0, 0xd0d0ff];
  const pos = new Float32Array(d.P.flat()), col = new Float32Array(d.P.length * 3);
  d.main.forEach((b, i) => { const c = new T.Color(pal[b % pal.length]); col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; });
  const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(pos, 3)); g.setAttribute('color', new T.BufferAttribute(col, 3));
  sc.add(new T.Points(g, new T.PointsMaterial({size: 3, sizeAttenuation: false, vertexColors: true})));
  const out = []; for (const [cx, cy, cz] of [[0, 1.0, 6], [6, 1.0, 0], [0, 1.0, -6], [4, 3, 4]]) { const cam = new T.PerspectiveCamera(24, W / H, 0.1, 50); cam.position.set(cx, cy, cz); cam.lookAt(0, 0.95, 0); r.render(sc, cam); out.push(r.domElement.toDataURL()); }
  return {out, legend: d.names.map((n, i) => [n, '#' + new T.Color(pal[i % pal.length]).getHexString()])}; }"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context()).new_page(); await pg.set_content('<html></html>'); await pg.add_script_tag(content=THREE)
        res = await pg.evaluate(JS, json.loads(D))
        leg = ''.join(f'<span style="color:{c};margin-right:12px">■{n}</span>' for n, c in res['legend'])
        html = f'<body style="margin:0;background:#202020;font:15px sans-serif;color:#fff"><div style="padding:6px">{leg}</div>' + ''.join(f'<img src="{u}" style="width:520px">' for u in res['out']) + '</body>'
        p2 = await (await b.new_context(viewport={'width': 2080, 'height': 300})).new_page(); await p2.set_content(html)
        await p2.screenshot(path=OUT, full_page=True); await b.close()
asyncio.run(main())
