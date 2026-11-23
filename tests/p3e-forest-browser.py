#!/usr/bin/env python3
"""v0.88（P3-E の E-2）上志比の森林の確認（画面のない Chromium。10分ほど）。docs/p3e-e2.md

- 木の位置・数・番号は今までのまま、杉・広葉樹・竹に分ける（約6割・3割・1割）。何度作っても同じ分け方
- 広葉樹はどこでも切れて、丸太を割ると山地の硬木。切った広葉樹は生えてこない（fb）・苗木が1本取れる
- 切り株に苗木を植えると、時間がたつと育って、また切れる（pl）。杉は今までどおり（f）
- 古いセーブ（fb が無い）で、前に切った広葉樹は生えてこない方の記録へ移る
- 竹林の竹を切る（竹+2・待ち時間）。山の薬草（森の奥・摘む・待ち時間）。かまどで薬草粥・荷台の救急箱に入れると戻りが2倍
- 近くの林床（下草・木漏れ日・苔の岩・倒木）を区画ごとに作る・捨てる（当たり判定も外す）
- 「描く細かさ：軽量」で遠くの木を減らす・戻す。セーブの読み書き。光明寺へ戻ると何も残らない。エラーなし
- FOREST_SHOTS=フォルダ で森の画面を撮る

使い方：THREE_JS=…/three.min.js python3 tests/p3e-forest-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
HTML = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read().replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){', 1)
SHOTS = os.environ.get('FOREST_SHOTS')
BASE = """(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; prog.arms.axeStone=WEAPONS.axeStone.maxDur; return 1; })()"""
TRAVEL = "(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()"
CALM = "(()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; prog.f10.tod=150; f10LightNow(); weather.state='clear'; return 1; })()"
HASH = "(()=>{ let h=0; E2.all.forEach((o,i)=>{ h=(h*31+(o.ty==='sugi'?1:o.ty==='kona'?2:3)*(i%97+1))%1000000007; }); return [E2.all.length,h]; })()"


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg, flush=True)
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

        async def until(js, ms=20000):
            for _ in range(ms // 200):
                if await E(js):
                    return True
                await pg.wait_for_timeout(200)
            return False

        async def travel(to):
            await E(TRAVEL if to == 'kamishihi' else "(async()=>{ await regionTravel('komyoji',null,{force:true}); })()")
            await until(f"REG.cur==='{to}'&&!REG.busy", 120000)
            await pg.wait_for_timeout(500)

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
        await E("(()=>{ try{ localStorage.removeItem('eiheiji_detail'); }catch(e){} GFX.detail='std'; E1.off=true; return 1; })()")
        home = await E("[circles.length, oboxes.length, boxes.length]")
        await travel('kamishihi')
        await E(CALM)

        # ---- 分け方 ----
        st = await E("""(()=>{ const c=E2.count, n=c.sugi+c.kona+c.take, kt=[...REG.live.ktrees.values()]; const ty={}; for(const t of kt) ty[t.ty||'kp']=(ty[t.ty||'kp']||0)+1;
          const keyOK=kt.every(t=>/^(k\\d+_\\d+_\\d+|kp\\d+)$/.test(t.key)), konaFlag=kt.filter(t=>t.ty==='kona').every(t=>t.kona===1), sugiG=kt.filter(t=>t.ty==='sugi').every(t=>t.gs===E2GS.sugi);
          const p3a=E2.all.filter(o=>o.tr[4]).length; return {n, c, total:REG.live.treeCount, ty, keyOK, konaFlag, sugiG, take:E2.take.length, p3a,
            share:[c.sugi,c.kona,c.take].map(v=>Math.round(v/(n-p3a)*1000)/10)}; })()""")
        sh = st['share']
        check(st['n'] == st['total'] and st['keyOK'] and st['konaFlag'] and st['sugiG'], f"木の数は今までのまま {st['n']}本（番号の形も同じ）・広葉樹に印・杉は P3-A の杉の大きさ")
        check(55 <= sh[0] <= 65 and 27 <= sh[1] <= 33 and 8 <= sh[2] <= 12, f"杉・広葉樹・竹の割合（%）{sh}（約6割・3割・1割）・{st['c']}・竹林 {st['take']}か所")
        h1 = await E(HASH)

        # ---- 広葉樹を切る・苗木・植える・育つ ----
        r = await E("""(()=>{ const kt=[...REG.live.ktrees.values()].find(t=>t.ty==='kona'&&!t.felled&&dist(t.x,t.z,6200,900)<2500); inv.naegi=0; inv.hardwood=0; const k=prog.kami;
          const rec=kamiTreeRec(kt); f4Fell(rec,0.3); const tr=F4.trunks.find(t=>t.key===kt.key); const L=REG.live.kw.logs, n0=L.length; f4Buck(tr); const hw=L.slice(n0).filter(l=>l[5]).length;
          window.__kt=kt; return [k.fb.includes(kt.key), k.f.includes(kt.key), inv.naegi, kt.felled, hw, kt.col.active]; })()""")
        check(r == [True, False, 1, True, 2, False], f"広葉樹を切る：生えてこない記録（fb）へ・苗木+1・硬木の丸太2本 {r}")
        await E("(()=>{ e2Tick(REG.live); return 1; })()")
        r = await E("""(()=>{ const kt=__kt; P.x=kt.x+1.0; P.z=kt.z; const L=[]; REG.live.inter(L); const a=L.find(o=>o.label.startsWith('広葉樹の切り株に苗木を植える')); const st=E2.stumpIM?E2.stumpIM.count:0;
          if(a) a.act(); e2Tick(REG.live); return [!!a, st, inv.naegi, prog.kami.pl[kt.key]!=null, E2.sapIM?E2.sapIM.count:0]; })()""")
        check(r[0] and r[1] >= 1 and r[2] == 0 and r[3] and r[4] >= 1, f"切り株が見える・苗木を植える（調べる）・苗木の形が出る {r}")
        r = await E("""(()=>{ const kt=__kt, k=prog.kami; k.pl[kt.key]=stats.time-E2.grow-1; E2.t=0; e2Tick(REG.live); return [kt.felled, kt.col.active, k.fb.includes(kt.key), k.pl[kt.key]==null]; })()""")
        check(r == [False, True, False, True], f"植えてから時間がたつと育つ（また切れる・当たり判定も戻る）{r}")
        r = await E("""(()=>{ const kt=[...REG.live.ktrees.values()].find(t=>t.ty==='sugi'&&!t.felled&&dist(t.x,t.z,6200,900)<2500); const k=prog.kami, n0=inv.naegi; f4Fell(kamiTreeRec(kt),0.2);
          const tr=F4.trunks.find(t=>t.key===kt.key); const L=REG.live.kw.logs, n1=L.length; f4Buck(tr); return [k.f.includes(kt.key), k.fb.includes(kt.key), inv.naegi-n0, L.slice(n1).filter(l=>l[5]).length]; })()""")
        check(r == [True, False, 0, 0], f"杉は今までどおり（f・硬木にならない・苗木なし）{r}")

        # ---- 竹林・山の薬草 ----
        r = await E("""(()=>{ const c=E2.take.find(c=>dist(c.x,c.z,6200,900)<2500); P.x=c.x+1.0*c.s*E2GS.take+0.6; P.z=c.z; const L=[]; REG.live.inter(L); const a=L.find(o=>o.label==='竹林の竹を切る（竹+2）'); const b0=inv.bamboo||0;
          if(a) a.act(); const L2=[]; REG.live.inter(L2); return [!!a, (inv.bamboo||0)-b0, prog.kami.n['t'+c.i]!=null, L2.some(o=>o.label.startsWith('竹林：切った竹が伸びるのを待つ'))]; })()""")
        check(r == [True, 2, True, True], f"竹林の竹を切る：竹+2・待ち時間（t の記録）{r}")
        r = await E("""(()=>{ const H=REG.live.kw.nodes.filter(n=>n.k==='herb'), D=KAMI.D; let mb=1e9, mr=1e9; for(const n of H){ for(const b of D.bld) mb=Math.min(mb,dist(n.x,n.z,b[0],b[1])); for(const r of D.roads){ if(r.b) continue; for(let i=0;i<r.p.length-1;i++) mr=Math.min(mr,segDist(n.x,n.z,r.p[i][0],r.p[i][1],r.p[i+1][0],r.p[i+1][1])); } }
          const n=H[0]; P.x=n.x+0.8; P.z=n.z; const L=[]; REG.live.inter(L); const a=L.find(o=>o.label.includes('山の薬草を摘む')); inv.mherb=0; if(a) a.act(); const L2=[]; REG.live.inter(L2);
          return [H.length, Math.round(mb), Math.round(mr), !!a, inv.mherb>=1, prog.kami.n[n.key]!=null, L2.some(o=>o.label.startsWith('山の薬草：もう摘んだ'))]; })()""")
        check(r[0] >= 18 and r[1] >= 70 and r[2] >= 25 and r[3:] == [True, True, True, True], f"山の薬草：{r[0]}か所（家から {r[1]}m・道から {r[2]}m 以上）・摘む・待ち時間 {r[3:]}")
        r = await E("""(()=>{ const sv=JSON.parse(JSON.stringify(kamiSave())), k2=kamiLoad(sv); return [JSON.stringify(k2.fb)===JSON.stringify(prog.kami.fb), Object.keys(k2.pl).length===Object.keys(prog.kami.pl).length,
          Object.keys(k2.n).filter(a=>/^[th]/.test(a)).length===Object.keys(prog.kami.n).filter(a=>/^[th]/.test(a)).length, k2.f.length===prog.kami.f.length]; })()""")
        check(r == [True, True, True, True], f"セーブの読み書き（fb・pl・竹林と薬草の待ち時間・f）{r}")
        # かまど・荷台の救急箱
        r = await E("""(()=>{ if(!prog.kama.built){ prog.kama.built=1; } prog.kama.q=[]; foodAdd('rice',2); inv.mherb=2; inv.wood=20; const L=[]; kamaInteract(L,1); L[0].act();
          const bt=[...document.querySelectorAll('#defenseChoice button')].find(b=>b.textContent.startsWith('山の薬草で薬草粥を炊く')); const hasImg=!!(bt&&bt.querySelector('img')); if(bt) bt.click(); const d=document.getElementById('defenseChoice'); if(d) d.remove(); S.mode='playing';
          return [!!bt, prog.kama.q.includes('herbPorridge'), inv.mherb]; })()""")
        check(r == [True, True, 1], f"かまど：山の薬草で薬草粥を炊く（米1・山の薬草1）{r}")
        r = await E("""(()=>{ const t=trk(); t.region=REG.cur; t.fac=t.fac||{}; t.fac.aid=1; TRUCK.x=P.x+2; TRUCK.z=P.z; TRUCK.drive=false; P.lastHurt=-999; inv.mherb=1;
          const L=[]; truckInteractables(L); const a=L.find(o=>o.label.startsWith('荷台の救急箱に山の薬草を入れる')); if(a) a.act();
          P.hp=P.maxHp-50; const h0=P.hp; truckAidUpdate(1); const d1=P.hp-h0; TRUCK.herbT=0; P.hp=P.maxHp-50; truckAidUpdate(1); const d0=P.hp-(P.maxHp-50); P.hp=P.maxHp; return [!!a, inv.mherb, Math.round(d1/d0*10)/10]; })()""")
        check(r == [True, 0, 2.0], f"荷台の救急箱に山の薬草：体力の戻りが2倍 {r}")

        # ---- 林床（近くの区画）----
        await E("(()=>{ E1.off=false; return 1; })()")
        sp = await E("""(()=>{ let best=null; for(const [gk,a] of E2.grid){ const c={sugi:0,kona:0,take:0}; for(const t of a) c[t[2]]++; const sc=Math.min(c.kona,15)+Math.min(c.take,8)*2+Math.min(c.sugi,15); if(!best||sc>best.sc) best={sc,x:a[0][0],z:a[0][1]}; } return [best.x,best.z]; })()""")
        x, z = sp
        await E(f"(()=>{{ P.x=6200; P.z=900; cam.override={{p:new THREE.Vector3({x}+3,groundH({x}+3,{z}+6)+1.7,{z}+6), l:new THREE.Vector3({x}-10,groundH({x}-10,{z}-12)+2.5,{z}-12), fov:62}}; return 1; }})()")
        done = await until(f"!E1.busy&&[...E1.cells.values()].every(c=>c.o||e1RectD(c,{x}+3,{z}+6)>=gfxRad().in)", 240000)
        fl = await E("""(()=>{ let fern=0, sun=0, cols=0, rock=0, log=0; window.__fc=[]; for(const c of E1.cells.values()) if(c.o){ if(c.o.fern) fern+=c.o.fern.count; if(c.o.sun) sun++; cols+=c.o.cols.length; for(const k of c.o.cols){ __fc.push(k); if(k.tag==='rock') rock++; if(k.tag==='log') log++; } } return [fern, sun, rock, log]; })()""")
        check(done and fl[0] > 100 and fl[1] >= 1 and fl[2] + fl[3] >= 1, f"近くの林床：下草 {fl[0]}・木漏れ日の区画 {fl[1]}・苔の岩 {fl[2]}・倒木 {fl[3]}")
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            await E("($('hud').hidden=true, 1)")
            await pg.wait_for_timeout(1500)
            await pg.screenshot(path=os.path.join(SHOTS, 'inside.png'), timeout=300000)
            await E(f"(()=>{{ cam.override={{p:new THREE.Vector3({x}-40,groundH({x}-40,{z}+40)+28,{z}+40), l:new THREE.Vector3({x},groundH({x},{z}),{z}), fov:55}}; return 1; }})()")
            await until(f"!E1.busy&&[...E1.cells.values()].every(c=>c.o||e1RectD(c,{x}-40,{z}+40)>=gfxRad().in)", 240000)
            await pg.wait_for_timeout(1500)
            await pg.screenshot(path=os.path.join(SHOTS, 'above.png'), timeout=300000)
            await E("($('hud').hidden=false, 1)")
        # 軽量：遠くの木を減らす
        r = await E("""(()=>{ applyDetail('lite'); const a=E2.lo.every(e=>e.lo.count===e.keep), red=E2.lo.reduce((s,e)=>s+e.n-e.keep,0), all=E2.lo.reduce((s,e)=>s+e.n,0); applyDetail('std'); const b=E2.lo.every(e=>e.lo.count===e.n); return [a, b, Math.round(red/all*100)]; })()""")
        check(r[0] and r[1] and 30 <= r[2] <= 50, f"「描く細かさ：軽量」で遠くの木を {r[2]}% 減らす・標準で戻す {r[:2]}")
        await E("(()=>{ P.x=6500; P.z=470; cam.override={p:new THREE.Vector3(6500,groundH(6500,470)+30,470), l:new THREE.Vector3(6520,groundH(6520,430),430), fov:55}; return 1; })()")
        await until("!E1.busy&&[...E1.cells.values()].every(c=>!c.o||e1RectD(c,6500,470)<=gfxRad().out)", 120000)
        r = await E("""(()=>{ const live=new Set(); for(const c of E1.cells.values()) if(c.o) for(const k of c.o.cols) live.add(k); const C=new Set(circles), O=new Set(oboxes); return __fc.filter(k=>!live.has(k)&&(C.has(k)||O.has(k))).length; })()""")
        check(r == 0, f"離れると林床の当たり判定も外れる（残り {r}）")

        # ---- 古いセーブ：前に切った広葉樹（f の中）は生えてこない方へ ----
        await E("(cam.override=null, 1)")
        old = await E("""(()=>{ const kt=[...REG.live.ktrees.values()].find(t=>t.ty==='kona'&&!t.felled&&t.key[1]!=='p'); const sv=kamiSave(); delete sv.fb; delete sv.pl; sv.f=sv.f.concat([kt.key]); window.__old=kt.key; prog.kami=kamiLoad(sv); return kt.key; })()""")
        await travel('komyoji')
        back = await E("[E1.cells===null, E2.all===null, circles.length, oboxes.length, boxes.length]")
        check(back[0] and back[1] and back[2:] == home, f"光明寺へ戻ると捨てる・当たり判定が残らない {back} / {home}")
        await travel('kamishihi')
        r = await E(f"""(()=>{{ const k=prog.kami, kt=REG.live.ktrees.get('{old}'); return [k.f.includes('{old}'), k.fb.includes('{old}'), !!(kt&&kt.felled)]; }})()""")
        check(r == [False, True, True], f"古いセーブ：前に切った広葉樹は生えてこない記録へ移る {r}")
        h2 = await E(HASH)
        check(h1 == h2, f"作り直しても同じ分け方 {h1} / {h2}")
        sv = await E("(saveGame(), (()=>{ const d=JSON.parse(localStorage.getItem(SAVE_KEY)); return [d.v, typeof d.inv.naegi, typeof d.inv.mherb, SAVE_KEY]; })())")
        check(sv == [1, 'number', 'number', 'eiheiji_vs_beasts_v010'], f"セーブ：v:1・保存キーは同じ・苗木と山の薬草を持ち物に {sv}")
        check(not errs, f"エラーなし {errs[:3]}")
        await b.close()
    print('PASS: 上志比の森林（E-2）' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
