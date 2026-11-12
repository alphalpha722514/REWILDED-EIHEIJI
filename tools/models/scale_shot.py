"""主人公・通常の猿・変異したサル（暫定の大きさ）を並べて撮る。
python3 tools/models/scale_shot.py サル.glb 出力.png 高さ倍率（通常の猿の高さに対して）
"""
import asyncio, base64, os, sys
from playwright.async_api import async_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); T3 = os.environ.get('THREE_DIR', '/home/claude/v010/node_modules/three')
THREE = open(f'{T3}/build/three.min.js').read(); GLTF = open(f'{T3}/examples/js/loaders/GLTFLoader.js').read(); MESHOPT = open(f'{T3}/examples/js/libs/meshopt_decoder.js').read()
SRC = open(f'{ROOT}/index.html', encoding='utf8').read()
HOOK = "window.__s={makeHuman,makeMonkey};\n"
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
B64 = base64.b64encode(open(sys.argv[1], 'rb').read()).decode()
OUT, K = sys.argv[2], float(sys.argv[3])
JS = r"""async ([b64, K]) => { const T = THREE, S = window.__s, W = 1200, H = 520;
  const r = new T.WebGLRenderer({antialias: true, preserveDrawingBuffer: true}); r.setSize(W, H); r.setPixelRatio(1);
  const sc = new T.Scene(); sc.background = new T.Color(0xe9e4d8); sc.add(new T.HemisphereLight(0xfff2dc, 0x6f6450, 0.6));
  const dl = new T.DirectionalLight(0xfff0d8, 0.7); dl.position.set(3, 6, 8); sc.add(dl);
  const gr = new T.Mesh(new T.PlaneGeometry(40, 40), new T.MeshBasicMaterial({color: 0xd6cfbf})); gr.rotation.x = -Math.PI / 2; sc.add(gr);
  const pl = S.makeHuman({player47: true}).g, mk = S.makeMonkey().g;
  const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer; const L = new T.GLTFLoader(); L.setMeshoptDecoder(MeshoptDecoder);
  const gl = await new Promise((res, rej) => L.parse(bin, '', res, rej)); const mu = new T.Group(); const inner = gl.scene; mu.add(inner);
  inner.rotation.y = -Math.PI / 2; inner.updateMatrixWorld(true);
  inner.traverse(o => { if (o.isMesh && o.material.map) { o.material.map.encoding = T.LinearEncoding; o.material.needsUpdate = true; } }); // ゲームの色の扱い（Linear）に合わせる
  let bb = new T.Box3().setFromObject(inner); const feetY = -0.443; // 足の裏（手の先はこれより 0.048 下）
  const sz = bb.getSize(new T.Vector3());
  const info = {};
  for (const [n, g] of [['player', pl], ['monkey', mk]]) { g.updateMatrixWorld(true); const b = new T.Box3().setFromObject(g); info[n] = [b.min.y.toFixed(2), b.max.y.toFixed(2), (b.max.z - b.min.z).toFixed(2)]; }
  const monkeyH = +info.monkey[1], scale = monkeyH * K / (bb.max.y - feetY); inner.scale.setScalar(scale); inner.position.y = -feetY * scale; mu.updateMatrixWorld(true);
  bb = new T.Box3().setFromObject(mu); info.mutant = [bb.min.y.toFixed(2), bb.max.y.toFixed(2), (bb.max.z - bb.min.z).toFixed(2), 'scale ' + scale.toFixed(2)];
  const out = [];
  for (const [rot, dist] of [[0, 1], [Math.PI / 2, 1]]) {
    [[pl, -1.6], [mk, 0], [mu, 1.7]].forEach(([g, x]) => { if (!g.parent) sc.add(g); g.position.x = x; g.rotation.y = rot; g.updateMatrixWorld(true); });
    const cam = new T.PerspectiveCamera(26, W / H, 0.1, 100); cam.position.set(0, 1.0, 9.5); cam.lookAt(0, 0.85, 0); r.render(sc, cam); out.push(r.domElement.toDataURL('image/png')); }
  return {out, info}; }"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 900, 'height': 500})).new_page()
        async def route(rq):
            u = rq.request.url
            if 'three' in u: await rq.fulfill(body=THREE, content_type='application/javascript')
            elif u.startswith('http://game.local'): await rq.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            else: await rq.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__s', timeout=300000)
        await pg.add_script_tag(content=GLTF); await pg.add_script_tag(content=MESHOPT)
        res = await pg.evaluate(JS, [B64, K]); print(res['info'])
        html = '<body style="margin:0">' + ''.join(f'<img src="{u}" style="display:block;width:1200px">' for u in res['out']) + '</body>'
        p2 = await (await b.new_context(viewport={'width': 1200, 'height': 400})).new_page(); await p2.set_content(html)
        await p2.screenshot(path=OUT, full_page=True, timeout=240000); await b.close()
asyncio.run(main())
