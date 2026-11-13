#!/usr/bin/env python3
"""鱗の防具の確認画像（v0.64）。防具なし・蒼鱗・変異した鱗を、正面・横・背中で並べる。
python3 tools/scale-armor-studio.py 出力.png   （STUDIO_HTML で別の index.html。THREE_DIR で three の場所）
main の古い体の主人公に、本編の f47ApplyVisual で一式を着せて、無地の背景で撮る（光の粒・もやは写らない。ゲーム内の様子は tests/scale-gear-browser.py の SCALE_SHOTS）。
"""
import asyncio, base64, io, os, sys
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE=open(os.environ.get('THREE_DIR','/home/claude/v010/node_modules/three')+'/build/three.min.js').read()
SRC=open(os.environ.get('STUDIO_HTML',os.path.join(ROOT,'index.html')),encoding='utf8').read()
HTML=SRC.replace('function updateNPCs(dt){','window.__p={get pm(){return pm},get prog(){return prog},f47ApplyVisual:()=>f47ApplyVisual(),renderer};\nfunction updateNPCs(dt){',1)
OUT=sys.argv[1]
JS=r"""(set) => { const T=window.__p, pm=T.pm, W=420, H=560; const r=T.renderer; r.setSize(W,H);
  const g=T.prog.gear; for(const s of ['head','chest','legs','feet']){ const id=set?set+'_'+s:null; if(id&&!g.owned.includes(id)) g.owned.push(id); g.equip[s]=id||(s==='head'?null:'work_'+s); } T.f47ApplyVisual();
  const sc=new THREE.Scene(); sc.background=new THREE.Color(0xe8e3d8); sc.add(new THREE.HemisphereLight(0xfff4e0,0x8a7f6a,0.75)); const dl=new THREE.DirectionalLight(0xfff0dc,0.7); dl.position.set(2,4,3); sc.add(dl);
  const par=pm.g.parent; const p0=pm.g.position.clone(), r0=pm.g.rotation.y; sc.add(pm.g); pm.g.position.set(0,0,0);
  const out=[]; const cam=new THREE.PerspectiveCamera(26,W/H,0.1,50);
  for(const a of [0,Math.PI/2,Math.PI]){ pm.g.rotation.y=a; pm.g.updateMatrixWorld(true); cam.position.set(0,1.05,5.0); cam.lookAt(0,0.95,0); r.render(sc,cam); out.push(r.domElement.toDataURL('image/png')); }
  par.add(pm.g); pm.g.position.copy(p0); pm.g.rotation.y=r0; return out; }"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        pg=await (await b.new_context()).new_page()
        async def route(rq):
            u=rq.request.url
            if 'three' in u: await rq.fulfill(body=THREE,content_type='application/javascript')
            elif u.startswith('http://game.local'): await rq.fulfill(body=HTML,content_type='text/html; charset=utf-8')
            else: await rq.abort()
        await pg.route('**/*',route); await pg.goto('http://game.local/',wait_until='load',timeout=300000); await pg.wait_for_function('window.__p&&window.__p.pm',timeout=300000)
        rows=[]
        for set_,lab in [(None,'防具なし（いまの主人公）'),('blue','蒼鱗（加工した鱗）'),('raw','変異した鱗（鱗をそのまま）')]:
            ims=await pg.evaluate(JS,set_); rows.append((lab,[Image.open(io.BytesIO(base64.b64decode(u.split(',')[1]))).convert('RGB') for u in ims]))
        await b.close()
    font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc',26); small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc',18)
    sheet=Image.new('RGB',(420*3,(560+44)*3),(232,227,216)); d=ImageDraw.Draw(sheet)
    for i,(lab,ims) in enumerate(rows):
        y=i*(560+44); d.text((12,y+8),lab,fill=(40,30,20),font=font)
        for j,(im,v) in enumerate(zip(ims,['正面','横','背中'])):
            sheet.paste(im,(j*420,y+44)); d.text((j*420+12,y+52),v,fill=(90,80,70),font=small)
    sheet.save(OUT); print('wrote',OUT)
asyncio.run(main())
