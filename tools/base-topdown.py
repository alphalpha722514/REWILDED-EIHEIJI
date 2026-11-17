"""拠点（光明寺）を真上から撮り、施設の位置に印と名前を付ける（docs/base-layout-plan.md）。
使い方：python3 tools/base-topdown.py 出力.png [中心x 中心z 幅m] [index.html]
環境変数：LAYOUT_FOV（画角。広く撮るときは50）、LAYOUT_LABELS（[[名前,x,z,種類],…] の JSON。無いと拠点の施設）、LAYOUT_SETUP（撮る前にゲームの中で実行する式）、THREE_JS"""
import asyncio, os, sys, json, math
from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE=open(os.environ.get('THREE_JS','/home/claude/v010/node_modules/three/build/three.min.js')).read()
OUT=sys.argv[1]; CX=float(sys.argv[2]) if len(sys.argv)>2 else 150; CZ=float(sys.argv[3]) if len(sys.argv)>3 else 56; SPAN=float(sys.argv[4]) if len(sys.argv)>4 else 62
HTMLP=sys.argv[5] if len(sys.argv)>5 else os.path.join(ROOT,'index.html')
LABELS=json.loads(os.environ.get('LAYOUT_LABELS','null') or 'null')
SRC=open(HTMLP,encoding='utf8').read()
HTML=SRC.replace('function updateNPCs(dt){',"window.__ev=s=>eval(s);\n"+'function updateNPCs(dt){',1)
SETUP=os.environ.get('LAYOUT_SETUP','')
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        ctx=await b.new_context(viewport={'width':1000,'height':1000}); pg=await ctx.new_page()
        pg.on('pageerror',lambda e:print('ERR',e))
        async def route(r):
            u=r.request.url
            if 'three.min.js' in u or 'three.js/r128' in u: return await r.fulfill(body=THREE,content_type='application/javascript')
            if u.startswith('http://game.local'):
                path=u.split('http://game.local/',1)[1].split('?')[0]
                if path in ('','index.html'): return await r.fulfill(body=HTML,content_type='text/html; charset=utf-8')
                fp=os.path.join(ROOT,path)
                if os.path.isfile(fp): return await r.fulfill(body=open(fp,'rb').read())
                return await r.fulfill(status=404,body='')
            await r.abort()
        await ctx.route('**/*',route)
        G=lambda c: pg.evaluate('(c)=>window.__ev(c)',c)
        await pg.goto('http://game.local/',wait_until='load',timeout=300000)
        await pg.wait_for_function("typeof window.__ev==='function'",timeout=300000)
        await pg.click('#btnNew',timeout=240000); await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"): break
            await pg.click('#dialog'); await pg.wait_for_timeout(200)
        await G("""(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  for(const id of ['kama','conv']){ prog[id]=prog[id]||facFresh(); prog[id].built=1; } facApply(); depotS().built=1; depotApply(); dlgQueue.length=0; document.getElementById('dialog').hidden=true; S.mode='playing'; return 1; })()""")
        if SETUP: print('setup',await G(SETUP))
        await pg.wait_for_timeout(3000)
        FOV=float(os.environ.get('LAYOUT_FOV','20')); H=SPAN/2/math.tan(math.radians(FOV/2)); STEP=10 if SPAN<100 else 20
        await G(f"""(()=>{{ P.x={CX}; P.z={CZ}+40; cam.override={{p:new THREE.Vector3({CX},{H},{CZ}+0.001),l:new THREE.Vector3({CX},0,{CZ}),fov:{FOV}}}; camera.far=5000; camera.updateProjectionMatrix();
          const cv=document.querySelector('canvas'); document.querySelectorAll('body *').forEach(el=>{{ if(el!==cv&&!el.contains(cv)) el.style.visibility='hidden'; }}); return 1; }})()""")
        await pg.wait_for_timeout(6000)
        await pg.screenshot(path=OUT,timeout=300000)
        labs=LABELS or await G("""(()=>{ const L=[], add=(n,x,z,k)=>L.push([n,x,z,k||'f']);
          add('集会所',150,37.5,'b'); { const [sx,sz]=M(STOREHOUSE[0],STOREHOUSE[1]); add('資材倉庫',sx,sz,'b'); } add('救護テント',165,42,'b'); add('無線室',135,66,'b'); add('食料庫',STORE.x,41,'b'); add('作業台',BENCH.x,BENCH.z,'f'); add('田んぼ（米がとれる）',(PADDY.x0+PADDY.x1)/2,(PADDY.z0+PADDY.z1)/2,'f');
          add('見張り台（源さん）',156,73,'b'); add('見張り台',144,73,'b'); add('見張り台',169,37,'b'); add('火の見やぐら',CORE.x,CORE.z,'b'); add('井戸',159.5,49,'f'); add('共同菜園',F8PLOTS[1].x,F8PLOTS[1].z,'f');
          add('かまど',FAC.kama.pos.x,FAC.kama.pos.z,'f'); add('変換炉',FAC.conv.pos.x,FAC.conv.pos.z,'f'); add('丸太置き場',F4.yard.x,F4.yard.z,'f'); add('物見やぐら（建てる）',SCOUT.x,SCOUT.z,'f'); add('車両基地',TRUCK_SYS.depot.x,TRUCK_SYS.depot.z,'t');
          for(const g of GAPS) add(g.name,g.c.x,g.c.z,'g'); add('裏の木戸',150,34,'g'); add('出発点',PSPAWN.x,PSPAWN.z,'p');
          for(const n of NPCS) if(n.home&&inBase(n.home.x,n.home.z,2)) add(n.name.replace(/^.* /,''),n.home.x,n.home.z,'n');
          return L; })()""")
        pts=await G("(()=>{ const L="+json.dumps(labs)+"; return L.map(([n,x,z,k])=>{ const v=new THREE.Vector3(x,groundH(x,z),z).project(camera); return [n,(v.x+1)/2*innerWidth,(1-v.y)/2*innerHeight,k]; }); })()")
        grid=await G(f"(()=>{{ const R=[]; for(let x=Math.ceil(({CX}-{SPAN})/{STEP})*{STEP};x<={CX}+{SPAN};x+={STEP}) for(let z=Math.ceil(({CZ}-{SPAN})/{STEP})*{STEP};z<={CZ}+{SPAN};z+={STEP}){{ const v=new THREE.Vector3(x,groundH(x,z),z).project(camera); R.push([x,z,(v.x+1)/2*innerWidth,(1-v.y)/2*innerHeight]); }} return R; }})()")
        await b.close()
    im=Image.open(OUT).convert('RGB'); d=ImageDraw.Draw(im); f=ImageFont.truetype(FONT,17); fs=ImageFont.truetype(FONT,12)
    for x,z,px,py in grid:
        if 0<=px<im.width and 0<=py<im.height: d.text((px+2,py+1),f'{x},{z}',font=fs,fill=(255,255,255),stroke_width=2,stroke_fill=(0,0,0)); d.line([px-4,py,px+4,py],fill=(255,255,255)); d.line([px,py-4,px,py+4],fill=(255,255,255))
    col={'b':(255,235,120),'f':(140,230,255),'t':(255,140,90),'g':(255,90,90),'p':(200,255,160),'n':(255,170,230),'x':(255,255,255)}
    for n,px,py,k in pts:
        c=col.get(k,(255,255,255)); d.ellipse([px-5,py-5,px+5,py+5],fill=c,outline=(0,0,0),width=2)
        d.text((px+8,py-11),n,font=f,fill=c,stroke_width=3,stroke_fill=(0,0,0))
    im.save(OUT); print('wrote',OUT)
asyncio.run(main())
