"""主人公・通常の猿・変異したサルの各版を、ゲームの中で並べて撮る（ゲームの色の扱い・輪郭線）。
python3 lineup.py 出力.png "名前=GLB[:ol]" ...   （:ol で輪郭線をつける）
"""
import asyncio, base64, os, sys
from playwright.async_api import async_playwright
ROOT = '/home/claude/rewilded-eiheiji'; T3 = os.environ.get('THREE_DIR', '/home/claude/v010/node_modules/three')
THREE = open(f'{T3}/build/three.min.js').read(); GLTF = open(f'{T3}/examples/js/loaders/GLTFLoader.js').read(); MO = open(f'{T3}/examples/js/libs/meshopt_decoder.js').read()
SRC = open(f'{ROOT}/index.html', encoding='utf8').read()
HOOK = "window.__s={makeHuman,makeMonkey,outlineMatT};\n"
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
OUT = sys.argv[1]
ITEMS = []
for a in sys.argv[2:]:
    name, rest = a.split('=', 1); ol = rest.endswith(':ol'); path = rest[:-3] if ol else rest
    ITEMS.append([name, base64.b64encode(open(path, 'rb').read()).decode(), ol])
JS = r"""async (items) => { const T = THREE, S = window.__s, W = 1500, H = 560;
  // 輪郭線用の形：同じ位置の頂点をまとめ、少しならして（毛先のとげを体に収める）なめらかな法線をつける。ゲームでも読み込み時に作る予定
  const hullGeo = (geo, iters = 10) => { const pa = geo.attributes.position, nv = pa.count, I = geo.index.array, P = new Float32Array(nv * 3); // 交互配置（interleaved）でも読めるように取り出す
    for (let v = 0; v < nv; v++) { P[v * 3] = pa.getX(v); P[v * 3 + 1] = pa.getY(v); P[v * 3 + 2] = pa.getZ(v); }
    const key = new Map(), wid = new Int32Array(nv); let n = 0;
    for (let v = 0; v < nv; v++) { const k = Math.round(P[v * 3] * 1e5) + ',' + Math.round(P[v * 3 + 1] * 1e5) + ',' + Math.round(P[v * 3 + 2] * 1e5); let w = key.get(k); if (w === undefined) { w = n++; key.set(k, w); } wid[v] = w; }
    const X = new Float64Array(n * 3); for (let v = 0; v < nv; v++) for (let j = 0; j < 3; j++) X[wid[v] * 3 + j] = P[v * 3 + j];
    const nb = Array.from({length: n}, () => new Set());
    for (let f = 0; f < I.length; f += 3) { const a = wid[I[f]], b = wid[I[f + 1]], c = wid[I[f + 2]]; nb[a].add(b).add(c); nb[b].add(a).add(c); nb[c].add(a).add(b); }
    const nbs = nb.map(s => Array.from(s));
    const step = lam => { const Y = new Float64Array(X); for (let w = 0; w < n; w++) { const L = nbs[w]; if (!L.length) continue; for (let j = 0; j < 3; j++) { let m = 0; for (const u of L) m += X[u * 3 + j]; m /= L.length; Y[w * 3 + j] = X[w * 3 + j] + lam * (m - X[w * 3 + j]); } } X.set(Y); };
    for (let i = 0; i < iters; i++) { step(0.6); step(-0.62); }
    const N = new Float64Array(n * 3);
    for (let f = 0; f < I.length; f += 3) { const a = wid[I[f]], b = wid[I[f + 1]], c = wid[I[f + 2]];
      const ux = X[b * 3] - X[a * 3], uy = X[b * 3 + 1] - X[a * 3 + 1], uz = X[b * 3 + 2] - X[a * 3 + 2], vx = X[c * 3] - X[a * 3], vy = X[c * 3 + 1] - X[a * 3 + 1], vz = X[c * 3 + 2] - X[a * 3 + 2];
      const nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx; for (const w of [a, b, c]) { N[w * 3] += nx; N[w * 3 + 1] += ny; N[w * 3 + 2] += nz; } }
    const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3);
    for (let v = 0; v < nv; v++) { const w = wid[v], l = Math.hypot(N[w * 3], N[w * 3 + 1], N[w * 3 + 2]) || 1; for (let j = 0; j < 3; j++) { pos[v * 3 + j] = X[w * 3 + j]; nor[v * 3 + j] = N[w * 3 + j] / l; } }
    const g = new T.BufferGeometry(); g.setAttribute('position', new T.BufferAttribute(pos, 3)); g.setAttribute('normal', new T.BufferAttribute(nor, 3)); g.setIndex(geo.index); return g; };
  const r = new T.WebGLRenderer({antialias: true, preserveDrawingBuffer: true}); r.setSize(W, H); r.setPixelRatio(1);
  const sc = new T.Scene(); sc.background = new T.Color(0xe9e4d8); sc.add(new T.HemisphereLight(0xfff2dc, 0x6f6450, 0.6));
  const dl = new T.DirectionalLight(0xfff0d8, 0.7); dl.position.set(3, 6, 8); sc.add(dl);
  const gr = new T.Mesh(new T.PlaneGeometry(60, 60), new T.MeshBasicMaterial({color: 0xd6cfbf})); gr.rotation.x = -Math.PI / 2; sc.add(gr);
  const objs = [["主人公", S.makeHuman({player47: true}).g], ["通常の猿", S.makeMonkey().g]];
  for (const [name, b64, ol] of items) {
    const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0)).buffer; const L = new T.GLTFLoader(); L.setMeshoptDecoder(MeshoptDecoder);
    const gl = await new Promise((res, rej) => L.parse(bin, '', res, rej)); const g = new T.Group(); g.add(gl.scene);
    const ms = []; gl.scene.traverse(o => { if (o.isMesh) ms.push(o); });
    for (const o of ms) { if (o.material.map) { o.material.map.encoding = T.LinearEncoding; o.material.needsUpdate = true; }
      if (ol) o.add(new T.Mesh(hullGeo(o.geometry), window.__DBG ? new T.MeshBasicMaterial({color: 0xff0000, wireframe: true}) : S.outlineMatT(+(window.__OL||0.022)))); }
    objs.push([name, g]); }
  const gap = 1.75, x0 = -(objs.length - 1) * gap / 2, out = [];
  objs.forEach(([n, g], i) => { sc.add(g); g.position.set(x0 + i * gap, 0, 0); });
  const shots = [['正面', 0, [0, 1.0, 13], [0, 0.95, 0], 22], ['横', -Math.PI / 2, [0, 1.0, 13], [0, 0.95, 0], 22], ['遊ぶときの角度（後ろ斜め上から）', Math.PI * 0.8, [0, 5.2, 11.5], [0, 0.7, 0], 26]];
  for (const [label, rot, cp, tg, fov] of shots) {
    objs.forEach(([n, g]) => { g.rotation.y = rot; g.updateMatrixWorld(true); });
    const cam = new T.PerspectiveCamera(fov, W / H, 0.1, 200); cam.position.set(...cp); cam.lookAt(...tg); r.render(sc, cam); out.push([label, r.domElement.toDataURL('image/png')]); }
  // 顔の拡大（変異したサルだけ。斜め前から）
  const faces = []; const r2 = new T.WebGLRenderer({antialias: true, preserveDrawingBuffer: true}); r2.setSize(480, 420); r2.setPixelRatio(1);
  objs.forEach(([n, g]) => { g.rotation.y = 0; g.updateMatrixWorld(true); });
  for (let i = 2; i < objs.length; i++) { const g = objs[i][1], bb = new T.Box3().setFromObject(g), top = bb.max.y;
    const cam = new T.PerspectiveCamera(24, 480 / 420, 0.05, 50); const hx = g.position.x, hy = top - 0.35, hz = bb.max.z - 0.35;
    cam.position.set(hx + 1.1, hy + 0.25, hz + 2.2); cam.lookAt(hx, hy - 0.05, hz); r2.render(sc, cam); faces.push([objs[i][0], r2.domElement.toDataURL('image/png')]); }
  return {out, faces, names: objs.map(o => o[0])}; }"""
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
        await pg.add_script_tag(content=GLTF); await pg.add_script_tag(content=MO)
        if os.environ.get('DBG'): await pg.evaluate('window.__DBG=true')
        res = await pg.evaluate(JS, ITEMS)
        names = '　／　'.join(res['names'])
        html = '<body style="margin:0;background:#e9e4d8;font:22px sans-serif">' + f'<div style="padding:8px 14px">左から：{names}</div>' + ''.join(
            f'<div style="padding:4px 14px">{l}</div><img src="{u}" style="display:block;width:1500px">' for l, u in res['out']) + \
            '<div style="padding:4px 14px">顔（斜め前から）</div><div style="display:flex">' + ''.join(
            f'<div><div style="padding:2px 14px;font-size:18px">{l}</div><img src="{u}" style="display:block;width:480px;margin-right:20px"></div>' for l, u in res['faces']) + '</div></body>'
        p2 = await (await b.new_context(viewport={'width': 1500, 'height': 400})).new_page(); await p2.set_content(html)
        await p2.screenshot(path=OUT, full_page=True, timeout=240000); await b.close()
asyncio.run(main())
