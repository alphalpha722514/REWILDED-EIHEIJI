#!/usr/bin/env python3
"""キャラクターの確認用の画像を作る（正面・横・背面）。ゲーム本体は変えない。

index.html のコピーに、内部の作り（makeHuman・村人・主人公）を取り出す口を足し、
画面のない Chromium で、背景を消した撮影用の場面に並べて撮る。

使い方：
  python3 tools/char-studio.py 出力.png [並べる人 ...]
  並べる人：player（主人公）／suzuki（スズキ・試作）／gen／tome／eshin／yone／村人のID
  例：python3 tools/char-studio.py /tmp/suzuki.png player suzuki gen
環境変数 THREE_JS に three.js r128 の three.min.js のパスを入れる。
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.path.join(ROOT, os.environ.get('STUDIO_HTML', 'index.html')), encoding='utf8').read()
HOOK = ("window.__studio={THREE,makeHuman,get pm(){return pm},get NPCS(){return NPCS},"
        "get SUZUKI_OPTS(){return typeof SUZUKI_OPTS!=='undefined'?SUZUKI_OPTS:null},"
        "get F60_GARMENTS(){return typeof F60_GARMENTS!=='undefined'?F60_GARMENTS:null}};\n")
ANCHOR = 'function updateNPCs(dt){'
assert SRC.count(ANCHOR) == 1, 'anchor'
HTML = SRC.replace(ANCHOR, HOOK + ANCHOR)

STUDIO_JS = r"""
async (who) => {
  const S = window.__studio, T = S.THREE;
  const W = 1500, H = 640;
  const r = new T.WebGLRenderer({antialias: true, preserveDrawingBuffer: true});
  r.setSize(W, H); r.setPixelRatio(1);
  const sc = new T.Scene(); sc.background = new T.Color(0xe9e4d8);
  sc.add(new T.HemisphereLight(0xfff2dc, 0x6f6450, 0.55));
  const dl = new T.DirectionalLight(0xfff0d8, 0.62); dl.position.set(3, 6, 8); sc.add(dl);
  const ground = new T.Mesh(new T.CircleGeometry(30, 32), new T.MeshBasicMaterial({color: 0xd6cfbf}));
  ground.rotation.x = -Math.PI / 2; sc.add(ground);
  const models = [];
  for (const id of who) {
    let g = null;
    if (id === 'player') g = S.pm.g;
    else if (id.startsWith('wear:') || id.startsWith('player@')) {
      // wear:chest=none,legs=forest,feet=base,head=tracker（部位ごと。none=脱ぐ／base=初期の服／組の名前=その組の服）
      // player@forest は頭・胸・脚・靴をその組で着せる
      const m = S.makeHuman({player47: true}), w = {}, t0 = performance.now();
      const spec = id.startsWith('player@') ? ['head', 'chest', 'legs', 'feet'].map(k => k + '=' + id.slice(7)).join(',') : id.slice(5);
      for (const t of spec.split(',').filter(Boolean)) { const [slot, v] = t.split('=');
        if (v === 'none' || v === 'base') w[slot] = v;
        else { const gid = v + '_' + slot; m.wardrobe.ensure(gid, slot, S.F60_GARMENTS[v][slot]); w[slot] = gid; } }
      m.setWear(w); window.__armorMs = (window.__armorMs || []).concat([[id, Math.round(performance.now() - t0)]]);
      g = m.g; }
    else if (id === 'suzuki') g = S.makeHuman(S.SUZUKI_OPTS).g;
    else { const n = S.NPCS.find(n => n.id === id); if (n) g = n.m.g; }
    if (!g) throw new Error('unknown ' + id);
    g.parent && g.parent.remove(g); sc.add(g); models.push(g);
  }
  if (window.__pose) for (const g of models) g.traverse(b => { // 動きの確認用：踏み込み・ひざ曲げ・腕上げ
    if (!b.isBone) return; const r = {legL: [-1.0, 0, 0], shinL: [1.3, 0, 0], footL: [-0.3, 0, 0], legR: [0.55, 0, 0], shinR: [0.5, 0, 0],
      armR: [-2.2, 0, 0.2], foreR: [-0.6, 0, 0], armL: [0.6, 0, -0.3], chest: [0.25, 0.4, 0], body: [0.1, 0, 0]}[b.name];
    if (r) b.rotation.set(r[0], r[1], r[2]); });
  const gap = 1.25, x0 = -(models.length - 1) * gap / 2;
  const cam = new T.PerspectiveCamera(24, W / 3 / H, 0.1, 100);
  const out = [];
  for (const [k, rot] of [['front', 0], ['side', Math.PI / 2], ['back', Math.PI]]) {
    models.forEach((g, i) => { g.position.set(x0 + i * gap, 0, 0); g.rotation.set(0, rot, 0); g.updateMatrixWorld(true); });
    const span = models.length * gap + 0.4;
    cam.aspect = W / H; cam.updateProjectionMatrix();
    const th = Math.tan(cam.fov * Math.PI / 360), dist = Math.max(span / 2 / th / cam.aspect, 1.32 / th);
    cam.position.set(0, 1.1, dist); cam.lookAt(0, 1.02, 0);
    r.render(sc, cam); out.push(r.domElement.toDataURL('image/png'));
  }
  return out;
}
"""


async def main():
    out = sys.argv[1]
    who = sys.argv[2:] or ['player', 'suzuki', 'gen']
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 900, 'height': 500})).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(rq):
            u = rq.request.url
            if 'three' in u:
                await rq.fulfill(body=THREE, content_type='application/javascript')
            elif u.startswith('http://game.local'):
                await rq.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            else:
                await rq.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=240000)
        await pg.wait_for_function('window.__studio', timeout=240000)
        if os.environ.get('STUDIO_POSE'):
            await pg.evaluate('window.__pose=true')
        imgs = await pg.evaluate(STUDIO_JS, who)
        print('armor build ms:', await pg.evaluate('window.__armorMs||[]'))
        html = '<body style="margin:0;background:#e9e4d8">' + ''.join(
            f'<div style="font:20px sans-serif;padding:6px 12px">{t}</div><img src="{u}" style="display:block;width:1500px">'
            for t, u in zip(['正面', '横', '背面'], imgs)) + '</body>'
        p2 = await (await b.new_context(viewport={'width': 1500, 'height': 400})).new_page()
        await p2.set_content(html)
        await p2.screenshot(path=out, full_page=True, timeout=240000)
        if errs:
            print('page errors:', errs[:5])
        print('wrote', out)
        await b.close()

asyncio.run(main())
