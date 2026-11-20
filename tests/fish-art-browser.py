#!/usr/bin/env python3
"""v0.86 魚と水生生物の形の確認（画面のない Chromium。5分ほど）。docs/fish-art.md

- 図鑑の絵：魚11種・アラレガコ・水生生物7種が、新しい形（体の断面・ひれ・模様の絵／立体を組んだ形）で描ける
- 持ち物・手持ちバーの生の魚とモクズガニが、椀の絵ではなく魚・カニの絵になる（料理の椀の絵は今までどおり）
- 形と絵は種類ごとに1つ作って使い回す（重さ：三角形の数）
- 上志比：釣れた魚を少しのあいだ主人公の前に見せる → 消える・次に投げると消える／アラレガコの近景が新しい形・くねる・川へ戻すと消える
- 石の下で見つけた生き物を水際に少しのあいだ見せる（ヨシノボリは魚の形）
- 観察地点「瀬のアユの群れ」の影がアユの形
- 上志比を出ると、見せている魚と生き物は消える・エラーなし

使い方：THREE_JS=…/three.min.js python3 tests/fish-art-browser.py
"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
HTML = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read().replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){', 1)
BASE = """(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; return 1; })()"""
ACT = """(re)=>{ const L=[]; p3aInteractables(L); const o=L.find(o=>new RegExp(re).test(o.label)); if(!o) return 'none:'+L.map(o=>o.label).join('|'); o.act(); return o.label; }"""


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport={'width': 1100, 'height': 680})
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(r):
            u = r.request.url
            if 'three.min.js' in u or 'three.js/r128' in u:
                return await r.fulfill(body=THREE, content_type='application/javascript')
            if u.startswith('http://game.local'):
                path = u.split('http://game.local/', 1)[1].split('?')[0]
                if path in ('', 'index.html'):
                    return await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
                fp = os.path.join(ROOT, path)
                if os.path.isfile(fp):
                    return await r.fulfill(body=open(fp, 'rb').read())
                return await r.fulfill(status=404, body='')
            await r.abort()
        await ctx.route('**/*', route)
        E = lambda c: pg.evaluate('(c)=>window.__ev(c)', c)

        async def act(re_):
            return await pg.evaluate(f"(re)=>window.__ev(`({ACT})`)(re)", re_)

        async def until(js, ms=20000):
            for _ in range(ms // 150):
                if await E(js):
                    return True
                await pg.wait_for_timeout(150)
            return False

        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function("typeof window.__ev==='function'", timeout=300000)
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await E(BASE)
        await pg.wait_for_timeout(500)

        # ---- 図鑑の絵 ----
        ic = await E("""(()=>{ const ids=FISH.map(f=>f.id).concat(['ara']), aq=AQUA.map(a=>a.id), out={fish:[],aqua:[],bad:[]};
          for(const id of ids){ const o=makeIconObj('p3d_'+id); let tex=0, n=0; o.traverse(m=>{ if(m.isMesh){ n++; if(m.material.map) tex++; } }); out.fish.push([id,n,tex]); if(!(n===1&&tex===1)) out.bad.push(id); delete ICONS['p3d_'+id]; if(!iconOf('p3d_'+id)) out.bad.push('img:'+id); }
          for(const id of aq){ const o=makeIconObj('p3d_'+id); let vc=0, n=0; o.traverse(m=>{ if(m.isMesh){ n++; if(m.material.vertexColors||m.material.map) vc++; } }); out.aqua.push([id,n,vc]); if(!(n===1&&vc===1)) out.bad.push(id); delete ICONS['p3d_'+id]; if(!iconOf('p3d_'+id)) out.bad.push('img:'+id); }
          return out; })()""")
        check(not ic['bad'] and len(ic['fish']) == 12 and len(ic['aqua']) == 7, f"図鑑の絵：魚11種・アラレガコ（模様の絵つきの形）・水生生物7種（色を塗った形）が描ける {ic['bad']}")
        raw = await E("""(()=>{ const f=makeIconObj('fAyu'), z=makeIconObj('zugani'), d=makeIconObj('ayuShio'), k=makeIconObj('koikoku'); const geo=o=>{ let g=null; o.traverse(m=>{ if(m.isMesh&&!g) g=m.geometry; }); return g; };
          return [geo(f)===fishGeo('fAyu',1), geo(z)===aquaGeo('aMokuzu'), geo(d)!==fishGeo('fAyu',1), k.children.length>=2]; })()""")
        check(raw == [True, True, True, True], f'持ち物の生の魚・モクズガニは魚とカニの絵（前は椀の絵）。料理の絵は今までどおり {raw}')
        sz = await E("""(()=>{ const tri=g=>(g.index?g.index.count:g.attributes.position.count)/3; const f=FISH.map(x=>x.id).concat(['ara','aYoshinobori']).map(id=>tri(fishGeo(id,1))), a=AQUA.filter(a=>a.id!=='aYoshinobori').map(x=>Math.round(tri(aquaGeo(x.id))));
          return [Math.max(...f), Math.min(...f), Math.max(...a), tri(fishGeo('fAyu',0,false)), fishGeo('fKoi',1)===fishGeo('fKoi',1), fishTex('fKoi')===fishTex('fKoi'), fishTex('fKoi').image.width, Object.keys(FISHTEX).length]; })()""")
        check(sz[0] < 3500 and sz[2] < 25000 and sz[3] < 400 and sz[4] and sz[5] and sz[6] == 256, f'形と絵は種類ごとに1つ（使い回す）。三角形：魚 {sz[1]}〜{sz[0]}・水生生物 最大 {sz[2]}・群れのアユ {sz[3]}・模様の絵 256×256 {sz}')

        # ---- 上志比：釣れた魚を見せる ----
        await E("(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()")
        await until("REG.cur==='kamishihi'&&!REG.busy", 60000)
        await pg.wait_for_timeout(800)
        await E("(()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; stfP().mutantMet=true; prog.f10.tod=150; const p=p3bState(); p.hq.sv=[1,1,1]; p.hq.talk=1; p.hq.plan=1; p.hq.beasts=1; p3dState().rod.basic=1; p3cState().soichi.found=1; return 1; })()")  # 宗一の出会い（はじめて投げたとき）で釣りが止まらないように
        sp = await E("(()=>{ for(let r=3;r<8;r+=0.5) for(let a=0;a<16;a++){ const x=6292+Math.cos(a*Math.PI/8)*r, z=822+Math.sin(a*Math.PI/8)*r; if(kamiReach(x,z)&&!p3dWater(x,z)){ P.x=x; P.z=z; if(p3dShore()) return [x,z]; } } return null; })()")
        await E("(cam.override={p:new THREE.Vector3(P.x,groundH(P.x,P.z)+3,P.z), l:new THREE.Vector3(P.x+0.01,groundH(P.x,P.z)+60,P.z), fov:50}, 1)")
        await pg.wait_for_timeout(300)

        async def cast(pick):
            await act('釣りをする')
            await E("p3dPress()")
            await until("P3D.fish&&P3D.fish.t>0.3", 60000)
            await E("p3dRelease()")
            if await E("P3D.fish&&P3D.fish.st==='fly'"):
                await E(f"(P3D.fish.fishPick={pick}, P3D.fish.t=0.6, P3D.fish.wait=0.05, 1)")
                await until("P3D.fish&&P3D.fish.st==='bite'", 60000)
            return await E("P3D.fish&&P3D.fish.st")

        st = await cast('FISH_BY.fYamame')
        n0 = await E("inv.fYamame||0")
        await E("p3dPress()")
        await until("P3D.fish&&P3D.fish.st==='ready'", 60000)
        sh = await E("[inv.fYamame, !!P3D.fm&&P3D.fm.visible, P3D.fm&&P3D.fm.geometry===fishGeo('fYamame',1), P3D.fm&&P3D.fm.material===fishMat('fYamame',true), P3D.fmT>0, P3D.fm&&+(P3D.fm.position.y-groundH(P.x,P.z)).toFixed(2)]")
        check(st == 'bite' and sh[0] == n0 + 1 and sh[1] and sh[2] and sh[3] and sh[4] and 0.9 < sh[5] < 1.4, f'釣れた魚（ヤマメ）を主人公の前に吊るして見せる（持ち物にも入る）{sh}')
        r0 = await E("P3D.fm.rotation.y")
        await pg.wait_for_timeout(500)
        r1 = await E("P3D.fm.rotation.y")
        await until("!P3D.fm.visible", 40000)
        gone = await E("[P3D.fm.visible, P3D.fmT]")
        check(r0 != r1 and gone == [False, 0], f'少し揺れて、2秒ほどで消える {gone}')
        # 見せている間に次を投げると消える
        st = await cast('FISH_BY.fAyu')
        await E("p3dPress()")
        await until("P3D.fish&&P3D.fish.st==='ready'", 60000)
        v1 = await E("[P3D.fm.visible, P3D.fm.geometry===fishGeo('fAyu',1)]")
        await act('釣りをする')
        await E("p3dPress()")
        await pg.wait_for_timeout(300)
        v2 = await E("[P3D.fish&&P3D.fish.st, P3D.fm.visible]")
        await E("p3dStop()")
        check(v1 == [True, True] and v2 == ['aim', False], f'見せている間に次を投げ始めると消える {v1} {v2}')

        # ---- アラレガコの近景 ----
        await E("(()=>{ const f=P3A.fishSpots[2]; P.x=f.x; P.z=f.z; return 1; })()")
        await pg.wait_for_timeout(300)
        st = await cast('ARAGAKO')
        await E("p3dPress()")
        await until("P3D.fish&&P3D.fish.st==='ara'", 60000)
        await pg.wait_for_timeout(300)
        a0 = await E("[P3D.fm.visible, P3D.fm.geometry===fishGeo('ara',1), P3D.fm.material.map===fishTex('ara'), P3D.fm.rotation.y]")
        await pg.wait_for_timeout(400)
        a1 = await E("P3D.fm.rotation.y")
        await until("P3D.fish&&P3D.fish.st==='ready'", 90000)
        a2 = await E("[P3D.fm.visible, !!cam.override, inv.ara||0]")
        check(st == 'bite' and a0[:3] == [True, True, True] and a0[3] != a1 and a2[0] is False and a2[2] == 0, f'アラレガコ：近景は新しい形（大きな胸びれ・石のような模様）・ゆっくりくねる・川へ戻すと消える {a0[:3]} {a2}')
        await E("(cam.override={p:new THREE.Vector3(P.x,groundH(P.x,P.z)+3,P.z), l:new THREE.Vector3(P.x+0.01,groundH(P.x,P.z)+60,P.z), fov:50}, 1)")

        # ---- 石の下の生き物 ----
        await E("(p3dStop(), 1)")  # 釣りの最中は「石の下を調べる」が出ない
        await E(sp and f"(P.x={sp[0]}, P.z={sp[1]}, 1)" or "1")
        await pg.wait_for_timeout(300)
        aq = []
        for a in ['aMokuzu', 'aYoshinobori', 'aKawanina']:
            await E(f"(P3D.srch=0, P3D.forceAqua='{a}', 1)")
            await act('水辺の石の下を調べる')
            aq.append(await E(f"[P3D.am.visible, P3D.am.geometry==={'fishGeo' if a == 'aYoshinobori' else 'aquaGeo'}('{a}'{',1' if a == 'aYoshinobori' else ''}), +(P3D.am.position.y-groundH(P3D.am.position.x,P3D.am.position.z)).toFixed(2), dist(P3D.am.position.x,P3D.am.position.z,P.x,P.z)<3]"))
        await E("(P3D.forceAqua=null, 1)")
        await until("!P3D.am.visible", 40000)
        ag = await E("[P3D.am.visible, P3D.amT]")
        check(all(x[0] and x[1] and -0.01 <= x[2] < 0.6 and x[3] for x in aq) and ag == [False, 0], f'石の下で見つけた生き物を水際に見せる（モクズガニ・ヨシノボリは魚の形・カワニナ）→ 3秒ほどで消える {aq} {ag}')

        # ---- 観察地点のアユの群れ ----
        ay = await E("(()=>{ const R=RIV.obs.find(r=>r.o.id==='oAyu'); if(!R||!R.fish) return null; const g=R.fish.geometry; return [g.attributes.position.count, !!g.attributes.uv, g!==fishGeo('fAyu',0), R.fish.count]; })()")
        check(ay is not None and ay[0] > 100 and ay[1] and ay[2] and ay[3] == 11, f'観察地点「瀬のアユの群れ」の影はアユの形（地域の後片付けで捨てる使い捨ての形）{ay}')

        # ---- 上志比を出ると消える ----
        await act('釣りをする')
        await E("p3dPress()")
        await pg.wait_for_timeout(200)
        await E("p3dStop()")
        await E("(P3D.srch=0, P3D.forceAqua='aSawagani', 1)")
        await act('水辺の石の下を調べる')
        await E("(P3D.forceAqua=null, p3dShowCatch(FISH_BY.fKoi,50), 1)")
        b4 = await E("[P3D.fm.visible, P3D.am.visible]")
        await E("(async()=>{ await regionTravel('komyoji',null,{force:true}); })()")
        await until("REG.cur==='komyoji'&&!REG.busy", 60000)
        await pg.wait_for_timeout(500)
        af = await E("[P3D.fm.visible, P3D.am.visible, P3D.fmT, P3D.amT]")
        check(b4 == [True, True] and af == [False, False, 0, 0], f'上志比を出ると、見せている魚と生き物は消える {b4} {af}')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: 魚と水生生物の形' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
