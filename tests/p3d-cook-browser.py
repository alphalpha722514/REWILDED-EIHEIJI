#!/usr/bin/env python3
"""v0.84（P3-D の D-2）魚料理と水生生物の確認（画面のない Chromium。5分ほど）。docs/p3d-d2.md

- 光明寺のかまど：魚を持っていると「魚を料理する」→ 10品の一覧（素材が足りない料理は印つき）→ 素材と薪を使って火にかける → できる
- 「どの川魚でも」「小さい川魚」「ヤマメかイワナ」の料理は、多く持っている魚から使う。アラレガコは料理に使えない（持ち物に入らない）
- 魚料理を食べる：体力・満腹・攻撃・移動・30秒で体力・採集の量+1（雑魚の天ぷら）・近くの採集物と依頼の場所が地図に出る（ずがに汁）
- 上志比の水際で「水辺の石の下を調べる」：川虫（釣りの餌）・モクズガニ（食材）・観察だけの生き物 → 水生生物の図鑑
- 川虫を持っていると釣りで自動で付ける（珍しい魚が出やすく・待ちが短く）
- 保存して「つづきから」・エラーなし

使い方：THREE_JS=…/three.min.js python3 tests/p3d-cook-browser.py
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

        async def boot():
            await pg.goto('http://game.local/', wait_until='load', timeout=300000)
            await pg.wait_for_function("typeof window.__ev==='function'", timeout=300000)

        async def act(re_):
            return await pg.evaluate(f"(re)=>window.__ev(`({ACT})`)(re)", re_)

        async def until(js, ms=20000):
            for _ in range(ms // 150):
                if await E(js):
                    return True
                await pg.wait_for_timeout(150)
            return False

        await boot()
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await E(BASE)
        await pg.wait_for_timeout(500)
        # ---- 光明寺のかまど ----
        await E("(()=>{ if(!prog.kama.built){ prog.kama.built=1; facApply(); } for(const k of ['fAyu','fKoi','fFuna','fNigoi','fYamame','fOikawa','fAbura','zugani','rice','veg']) foodAdd(k,3); inv.wood=40; P.x=FAC.kama.pos.x+1.6; P.z=FAC.kama.pos.z; return 1; })()")
        await pg.wait_for_timeout(400)
        lb = await E("(()=>{ const L=[]; kamaInteract(L,1); L[0].act(); return [...document.querySelectorAll('#defenseChoice button')].map(b=>b.textContent); })()")
        await E("[...document.querySelectorAll('#defenseChoice button')].find(b=>b.textContent.startsWith('魚を料理する')).click()")
        ls = await E("[...document.querySelectorAll('#defenseChoice button')].map(b=>b.textContent)")
        await E("(()=>{ const d=document.getElementById('defenseChoice'); if(d) d.remove(); return 1; })()")
        check(any(x.startswith('魚を料理する') for x in lb) and len(ls) == 11 and ls[10] == '戻る' and ls[0].startswith('鮎の塩焼き：アユ1') and all('素材が足りない' not in x for x in ls[:10]),
              f'かまど：魚を持っていると「魚を料理する」→ 10品の一覧（どれも作れる）{ls[:3]}')
        # 料理を作る（かまどの待ち行列は6まで。順に作って取り出す）
        made = {}
        for grp in [['ayuShio', 'keiShio', 'ayuMeshi', 'koikoku', 'funaKanro', 'kawaKushi'], ['zakoTen', 'kawaZosui', 'zuganiJiru', 'nigoiTsumire']]:
            r = await E(f"(()=>{{ const out=[]; for(const id of {grp}) out.push(p3dDishCook(id)); prog.kama.t=999; for(let i=0;i<8;i++) kamaUpdate(999); kamaTake(); return out; }})()")
            for x in r:
                made[x] = 1
        inv = await E("Object.fromEntries(Object.keys(FISH_DISH).map(k=>[k,inv[k]]))")
        check(len(made) == 10 and all(v == 1 for v in inv.values()), f'10品をかまどで作る（素材と薪を使う）{inv}')
        left = await E("[inv.fAyu, inv.fKoi, inv.fYamame, inv.fOikawa+inv.fAbura, inv.zugani, inv.rice, inv.veg]")
        check(left == [1, 2, 2, 3, 2, 1, 0], f'素材の使い方：アユ2（塩焼き・鮎めし）・ヤマメ1（渓魚）・小さい魚3（天ぷら2・どの魚でも…）など {left}')
        none = await E("(()=>{ for(const k of FISH.map(f=>f.id).concat(['zugani'])) foodTake(k,99); return [p3dHasFish(), p3dDishPlan('kawaKushi'), (p3dDishCook('kawaKushi'), $('toasts').textContent.includes('素材が足りない'))]; })()")
        check(none == [False, None, True], f'魚が無いと作れない（アラレガコも料理には使えない：持ち物に入らない）{none}')
        # ---- 食べる ----
        await E("(P.hp=50, P.full=20, P.st=100, 1)")
        ef = await E("(()=>{ const n0=(p3dScoutPts()||'none'); eat('zakoTen'); const a=[P.gatherT, P.full]; eat('zuganiJiru'); const b=P.scoutT, pts=p3dScoutPts(); eat('keiShio'); return [a[0], a[1], b, n0, pts.length>0&&pts.every(p=>!p.req&&dist(p.x,p.z,P.x,P.z)<=80), P.buffT]; })()")
        check(ef[0] == 60 and ef[1] == 55 and ef[2] == 90 and ef[3] == 'none' and ef[4] and ef[5] >= 15, f'食べる：雑魚の天ぷら（採集+1 60秒）・ずがに汁（90秒 近くの採集物が地図に出る）・渓魚の塩焼き（攻撃 15秒）{ef}')
        g = await E("(()=>{ const n=NODES.find(n=>n.avail&&n.k==='wood'); if(!n) return null; const w=inv.wood; gatherNode(n); const s=F5.straw.find(n=>!(nodeLeft(n)>0)); const st=inv.straw||0; if(s) f5Gather(s); return [inv.wood-w, s?(inv.straw||0)-st:null, STRAW_GOT]; })()")
        check(g[0] == 3 and g[2] is not None and g[1] == g[2] + 1, f'採集の量 +1（木材 2→3・藁 STRAW_GOT+1）{g}')
        hb = await E("(()=>{ hbBuild&&hbBuild(); return [...document.querySelectorAll('#hotbar .hb')].map(e=>e.dataset.id||'').join(','); })()")

        # ---- 上志比：水辺の石の下 ----
        await E("(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()")
        await until("REG.cur==='kamishihi'&&!REG.busy", 60000)
        await pg.wait_for_timeout(800)
        await E("(()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; stfP().mutantMet=true; prog.f10.tod=150; const p=p3bState(); p.hq.sv=[1,1,1]; p.hq.talk=1; p.hq.plan=1; p.hq.beasts=1; return 1; })()")
        sc = await E("(()=>{ const q=P3C_REQ.find(q=>!q.direct), R=p3cState().req||(p3cState().req={}); R[q.id]={a:1,s:q.steps.map(()=>0),h:q.steps.map(()=>0),r:0}; P.scoutT=90; const pts=p3dScoutPts(); const out=[pts.filter(p=>!p.req).length, pts.filter(p=>p.req).length]; P.scoutT=0; out.push(p3dScoutPts()); delete R[q.id]; return out; })()")
        check(sc[0] > 0 and sc[1] >= 1 and sc[2] is None, f'上志比：ずがに汁の間は、近くの採集物と受けた依頼の場所が地図に出る・切れると消える {sc}')
        sp = await E("(()=>{ for(let r=3;r<8;r+=0.5) for(let a=0;a<16;a++){ const x=6292+Math.cos(a*Math.PI/8)*r, z=822+Math.sin(a*Math.PI/8)*r; if(kamiReach(x,z)&&!p3dWater(x,z)){ P.x=x; P.z=z; if(p3dShore()) return [x,z]; } } return null; })()")
        await pg.wait_for_timeout(300)
        res = []
        for a in ['aKawagera', 'aMokuzu', 'aYago']:
            await E(f"(P3D.srch=0, P3D.forceAqua='{a}', 1)")
            res.append(await act('水辺の石の下を調べる'))
        await E("(P3D.forceAqua=null, 1)")
        aq = await E("[inv.kawamushi, inv.zugani, JSON.stringify(Object.keys(p3dState().book2)), p3dState().book2.aYago.where]")
        await E("(P3D.srch=5, 1)")
        cd = await act('水辺の石の下を調べる')
        cdt = await E("$('toasts').textContent.includes('さっき調べたばかり')")
        check(sp is not None and res[0] == '水辺の石の下を調べる（水生生物）' and aq[0] in (1, 2) and aq[1] == 1 and aq[2] == '["aKawagera","aMokuzu","aYago"]' and aq[3] == '河内川（支流）' and cdt,
              f'水辺の石の下を調べる：川虫（釣りの餌）・モクズガニ（食材）・ヤゴ（観察だけ）→ 図鑑・続けては調べられない {aq}')
        # ---- 川虫を付けて釣る ----
        await E("(p3dState().rod.basic=1, 1)")
        await act('釣りをする')
        await E("p3dPress()")
        await until("P3D.fish&&P3D.fish.t>0.3", 60000)
        b0 = await E("inv.kawamushi")
        await E("p3dRelease()")
        bt = await E("[P3D.fish.st, P3D.fish.bait, inv.kawamushi, $('fishRod').textContent]")
        await E("p3dStop()")
        check(bt[0] == 'fly' and bt[1] == 1 and bt[2] == b0 - 1 and '川虫' in bt[3], f'川虫を持っていると、投げるときに自動で付ける {bt}')
        # ---- 図鑑の水生生物 ----
        await E("(BOOK.tab='aqua', BOOK.sel='aMokuzu', p3dOpenBook(), 1)")
        await E("(BOOK.tab='aqua', BOOK.sel='aMokuzu', p3dRenderBook(), 1)")
        bk = await E("[document.querySelectorAll('#bookList .wkCard').length, document.querySelectorAll('#bookList .wkCard.lock').length, $('bookSub').textContent, $('bookDet').textContent, document.querySelectorAll('#bookTabs .wkTab').length]")
        await E("closeOverlay()")
        check(bk[0] == 7 and bk[1] == 4 and '水生生物 3/7' in bk[2] and 'モクズガニ' in bk[3] and '食材' in bk[3] and bk[4] == 3, f"図鑑：水生生物のタブ（7種・見つけた3つ。タブは魚類・水生生物・観察）{bk}")
        # ---- つづきから ----
        await E("saveGame()")
        await boot()
        await pg.click('#btnContinue')
        await pg.wait_for_timeout(1500)
        await until("REG.cur==='kamishihi'&&!REG.busy&&S.mode==='playing'", 60000)
        await pg.wait_for_timeout(800)
        lp = await E("[Object.keys(p3dState().book2).length, inv.zugani, inv.koikoku, inv.funaKanro]")
        check(lp == [3, 1, 1, 1], f'つづきから：水生生物の図鑑・モクズガニ・魚料理が残る {lp}')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: P3-D 魚料理と水生生物' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
