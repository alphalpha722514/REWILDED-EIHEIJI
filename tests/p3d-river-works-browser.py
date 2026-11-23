#!/usr/bin/env python3
"""v0.85（P3-D の D-3・P3-C の C-4）九頭竜川の改修と総合加工設備の確認（画面のない Chromium。10分ほど）。docs/p3d-d3.md・docs/p3c-c4.md

D-3（川の改修）
- 本流の全部が新しい水面（区画ごと）・浅い所に川底・近くの河原（区画ごとに作る・離れると捨てる・当たり判定も外す）
- 支流と水路の流れる水面（支流の水面の高さで浮きが浮く）・水路のコンクリートの壁
- 川の音：本流のそばで大きく・光明寺では鳴らない
- 川底の鉱石：7か所・つるはしで割ると川底の鉱石（1か所3つ）・割り切ると戻るまで割れない
- 特別な観察地点3か所：観察する → 図鑑の「観察」のタブ・横からのカメラ・夜は見えない
C-4（総合加工設備）
- 林道の広葉樹（33本）は切れる → 丸太を割ると山地の硬木（1本の木で2）・切った木は戻らない（つづきからでも）
- Lv3 の依頼「加工機の主軸を探す」：鉄工所の跡をのぞく → 鉄骨を4回どかす（屑鉄4）→ 主軸 → 報告（古い機械部品3）
- 総合加工設備：Lv3 で素材を納める → 住民が工期8時間で建てる → 「総合加工設備を使う」で画面（素材・武器の鍛え直し・防具の補強・車両）
- 鋼材を作る・鉈を鍛え直す（威力 +15%・耐久が長もち）・防具の補強（被ダメージ -2%）・KEI truck の高度加工3つ
- 本部の倉庫の素材も使える・保存して「つづきから」で残る（車の数値も付け直す）・新しく始めると元の数値・エラーなし

使い方：THREE_JS=…/three.min.js python3 tests/p3d-river-works-browser.py
"""
import asyncio
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
        print(('ok   ' if c else 'FAIL ') + msg, flush=True)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'])
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

        async def dlg(n=12):
            got = []
            for _ in range(n * 4):
                if await E("$('dialog').hidden"):
                    if got:
                        break
                    await pg.wait_for_timeout(150)
                    continue
                got.append(await E("$('dlgName').textContent+'｜'+$('dlgText').textContent"))
                await E("(dlgLock=0, advanceDialog(), 1)")
                await pg.wait_for_timeout(120)
            return got

        await boot()
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await E(BASE)
        base0 = await E("[TRUCK_SYS.gas.perKm, TRUCK_SYS.bed.cap, TRUCK_SYS.bed.maxLogs, TRUCK_SYS.hp.max[0], TRUCK_SYS.hp.beast]")
        await E("(audioInit&&audioInit(), 1)")
        await E("(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()")
        await until("REG.cur==='kamishihi'&&!REG.busy", 90000)
        await pg.wait_for_timeout(800)
        await E("(()=>{ window.__away=()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; }; __away(); stfP().mutantMet=true; prog.f10.tod=150; const p=p3bState(); p.hq.sv=[1,1,1]; p.hq.talk=1; p.hq.plan=1; p.hq.beasts=1; p.rep.storage=[1,1,1]; p.rep.workshop=[1,1,1]; const c=p3cState(); c.hint=1; c.hint2=1; c.sumie={met:1,hits:3,done:1}; c.rio={met:1,shelf:1,talk:1,parts:[1,1],fixed:1,done:1}; for(const k of P3B.carry.mats) inv[k]=0; return 1; })()")

        # ================= D-3 =================
        w = await E("[RIV.nChunks, RIV.tiles.length, REG.live.group.children.filter(m=>m.material&&m.material.customProgramCacheKey&&m.material.customProgramCacheKey()==='p3aWater').length, REG.live.group.children.filter(m=>m.material&&m.material.customProgramCacheKey&&m.material.customProgramCacheKey()==='rivStream').length]")
        check(w[0][0] >= 3 and w[0][1] >= 3 and w[1] > 20 and w[2] == w[0][0] and w[3] >= 2, f'本流の水面（区画ごと）・浅い所の川底・近くの河原の区画・支流と水路の水面 {w}')
        await E("(P.x=6900, P.z=935, 1)")
        await until("RIV.tiles.some(t=>t.o)", 30000)
        await pg.wait_for_timeout(1500)
        near = await E("(()=>{ const L=RIV.tiles.filter(t=>t.o); return [L.length, L.reduce((a,t)=>a+t.o.cols.length,0), L.reduce((a,t)=>a+t.o.meshes.length,0)]; })()")
        await E("(P.x=6366, P.z=1250, 1)")
        await until("!RIV.tiles.some(t=>t.o&&Math.hypot(t.cx-6900,t.cz-935)<150)", 30000)
        gone = await E("[RIV.tiles.filter(t=>t.o&&Math.hypot(t.cx-6900,t.cz-935)<150).length, circles.filter(c=>c.tag==='rock'&&dist(c.x,c.z,6900,935)<120&&!c.ktree).length]")
        check(near[0] >= 1 and near[2] >= 2 and gone[0] == 0, f'近くの河原：近づくと作る（区画 {near[0]}・形 {near[2]}・当たり {near[1]}）・離れると捨てる {gone}')
        st = await E("(()=>{ const s=KAMI.D.streams.find(s=>s.n==='河内川'); const p=s.p[Math.floor(s.p.length/2)]; const wv=p3dWater(p[0],p[1]); return [!!wv, wv&&wv.main, wv&&+(wv.y-kamiH(p[0],p[1])).toFixed(2)]; })()")
        check(st == [True, 0, 0.02], f'支流の水面の高さ（浮きの高さ）は地面 +0.02m {st}')
        # 音
        await dlg()
        await E("(P.x=6493, P.z=468, 1)")
        await until("S.mode==='playing'&&RIVSND&&RIVSND.dm<10", 15000)
        await until("RIVSND.main.gain.value>0.03", 40000)  # 音量はなめらかに上がる（画面のない Chromium はコマが少ないので時間がかかる）
        snd = await E("[typeof RIVSND!=='undefined'&&!!RIVSND, RIVSND&&+RIVSND.main.gain.value.toFixed(3), RIVSND&&Math.round(RIVSND.dm), S.mode]")
        check(snd[0] and snd[1] > 0.03 and snd[2] < 10, f'川の音：本流のそば（{snd[2]}m）で大きい {snd}')
        # 川底の鉱石
        ore = await E("(()=>{ const L=REG.live.kw.nodes.filter(n=>n.ore); const n=L[1]; prog.f5.tools={pickIron:100}; inv.ore=0; P.x=n.x+1.2; P.z=n.z; const r=[]; for(let i=0;i<5;i++){ kamiQuarry(n); r.push(inv.ore); } return [L.length, r, kamiRockLeft(n), prog.kami.r[n.key], !!prog.kami.n[n.key]]; })()")
        check(ore[0] == 7 and ore[1][-1] == 3 and ore[2] == 0 and ore[4], f'川底の鉱石：7か所・つるはしで割ると3つ・割り切ると戻るまで割れない {ore}')
        # 観察地点
        obs = []
        for oid in ['oSagi', 'oKawasemi', 'oAyu']:
            await E(f"(()=>{{ cam.override=null; RIV.camT=0; const R=RIV.obs.find(r=>r.o.id==='{oid}'); P.x=R.s.sx; P.z=R.s.sz; return 1; }})()")
            await pg.wait_for_timeout(500)
            obs.append(await act('観察する'))
            obs.append(await E("!!cam.override"))
        rec = await E("JSON.stringify(Object.keys(p3dState().obs))")
        await E("(()=>{ cam.override=null; RIV.camT=0; prog.f10.tod=1100; const R=RIV.obs[0]; P.x=R.s.sx; P.z=R.s.sz; return 1; })()")
        await pg.wait_for_timeout(500)
        await act('観察する')
        night = await E("[$('toasts').textContent.includes('暗くて'), p3dState().obs.oAyu.n]")
        await E("(prog.f10.tod=150, 1)")
        check(all(isinstance(x, str) and x.startswith('観察する') for x in obs[0::2]) and all(obs[1::2]) and rec == '["oSagi","oKawasemi","oAyu"]' and night == [True, 1],
              f'観察地点3か所：観察する → 図鑑に記録・横からのカメラ・夜は見えない {obs[0::2]} {rec} {night}')
        await E("(cam.override=null, RIV.camT=0, BOOK.tab='obs', BOOK.sel='oSagi', p3dOpenBook(), 1)")
        await E("(BOOK.tab='obs', BOOK.sel='oSagi', p3dRenderBook(), 1)")
        bk = await E("[document.querySelectorAll('#bookTabs .wkTab').length, $('bookSub').textContent, document.querySelectorAll('#bookList .wkCard:not(.lock)').length, $('bookDet').textContent.includes('首を伸ばし')]")
        await E("closeOverlay()")
        check(bk == [3, '観察 3/3', 3, True], f'図鑑の「観察」のタブ {bk}')

        # ================= C-4 =================
        kp = await E("(()=>{ const L=[...REG.live.ktrees.values()].filter(k=>k.kona&&k.key.startsWith('kp')); return [L.length, L.every(k=>k.col&&k.col.active)]; })()")  # v0.88（E-2）：広葉樹は全域にある。林道の試作の33本（kp）を数える
        hw = await E("(()=>{ const kt=[...REG.live.ktrees.values()].find(k=>k.kona&&!k.felled&&k.key.startsWith('kp')); P.x=kt.x+3; P.z=kt.z+3; const rec=kamiTreeRec(kt); f4Fell(rec,0.7); const tr=F4.trunks[F4.trunks.length-1]; tr.fall=-1; f4Buck(tr); const logs=REG.live.kw.logs.filter(l=>dist(l[0],l[1],kt.x,kt.z)<9); inv.hardwood=0; const w0=inv.wood; for(const l of logs.slice()) kamiSplitLog(l,99); return [kt.key, logs.length, logs.filter(l=>l[5]).length, inv.hardwood, inv.wood-w0, prog.kami.f.includes(kt.key)||(prog.kami.fb||[]).includes(kt.key), kt.felled]; })()")  # v0.88（E-2）：切った広葉樹は生えてこない記録（fb）へ
        check(kp[0] == 33 and kp[1] and hw[3] == 2 and hw[2] == 2 and hw[5] and hw[6], f'林道の広葉樹33本は切れる → 丸太を割ると山地の硬木2・切った木の記録 {kp} {hw}')
        # Lv3 と主軸の依頼
        await E("(()=>{ const c=p3cState(); c.lv=3; c.ev.res=1; c.soichi.found=1; c.soichi.coop=1; c.soichi.resident=1; return 1; })()")
        rs = await E("p3cReqState(P3C_REQ_BY.spindle)")
        await E("p3cReqAccept('spindle')")
        offer = await dlg()
        steps = []
        for i, n in [(0, 1), (1, 4), (2, 1)]:
            for _ in range(n):
                await E(f"(()=>{{ const sp=p3cSpot(P3C_REQ_BY.spindle.steps[{i}]); P.x=sp.x+1.0; P.z=sp.z; return 1; }})()")
                await pg.wait_for_timeout(200)
                steps.append(await act(await E(f"P3C_REQ_BY.spindle.steps[{i}].label.replace(/[()（）]/g,'.')")))
        got = await E("[inv.spindle, inv.iron, p3cReqState(P3C_REQ_BY.spindle)]")
        op0 = await E("inv.oldParts||0")
        await E("p3cReqReport('spindle')")
        done = await dlg()
        rep = await E("[p3cReqDone('spindle'), (inv.oldParts||0)]")
        check(rs == 'open' and len(offer) == 2 and offer[0].startswith('リオ｜総合加工設備を作るなら') and all(isinstance(x, str) and not x.startswith('none') for x in steps) and got == [1, 4, 'ready'] and rep == [True, op0 + 3] and len(done) == 2,
              f'Lv3 の依頼「加工機の主軸を探す」：のぞく → 鉄骨を4回どかす（屑鉄4）→ 主軸 → 報告（古い機械部品3）{got} {rep}')
        # 総合加工設備を建てる
        await E("(()=>{ Object.assign(inv,{wood:30,stone:20,iron:16,hardwood:6,oldParts:10,ore:8}); prog.stash.kami.hardwood=2; return 1; })()")
        dl = await E("(()=>{ p3cDeliver('works'); const s=p3cFac().works; return [JSON.stringify(s.dl), p3cStocked('works'), prog.stash.kami.hardwood||0, inv.spindle||0]; })()")
        await E("(()=>{ const c=p3cState(); c.job.sumie='b:works'; c.job.rio='b:works'; prog.f10.tod=150; return 1; })()")
        await E("(()=>{ for(let i=0;i<40;i++) p3cWorkTick(P3B.hour*0.25); return 1; })()")
        bd = await E("[p3cDone('works'), Math.round(p3cFac().works.h), P3C.f2.works.done.visible, P3C.f2.works.wip.visible, p3cState().job.sumie]")
        check('"spindle":1' in dl[0] and '"hardwood":8' in dl[0] and dl[1] and dl[2] == 0 and bd[0] and bd[2] and not bd[3] and bd[4] == '',
              f'総合加工設備：素材を納める（倉庫の硬木も）→ 2人で工期8時間 → 完成・担当は待機へ {dl} {bd}')
        # 使う
        await E("(()=>{ const S=P3C_SITE.works, p=p3cHQLocal(S.a-5,S.d); P.x=p.x; P.z=p.z; return 1; })()")
        await pg.wait_for_timeout(300)
        use = await act('総合加工設備を使う')
        await pg.wait_for_timeout(500)
        ui = await E("[$('craftTitle').textContent, [...document.querySelectorAll('#craftTabs .wkTab')].map(b=>b.id.replace('craftTab_','')).join(','), stashHere()===prog.stash.kami]")
        await E("(()=>{ Object.assign(inv,{ore:4,charcoal:4,steel:0}); craft('wk_steel'); craft('wk_steel'); return 1; })()")
        stl = await E("[inv.steel, inv.ore, inv.charcoal]")
        f1 = await E("(()=>{ P.weapon='nata1'; P.dur=50; prog.arms.nata1=50; const d0=weaponDmg('light'); Object.assign(inv,{steel:1,hardwood:1,iron:2}); craft('wf_nata1'); const d1=weaponDmg('light'); const dur=P.dur; P.wearAcc=0; let w=0; for(let i=0;i<4;i++) w+=p3cWear('nata1'); return [d0, +d1.toFixed(2), dur, w, p3cForgeW('nata1')]; })()")
        ar = await E("(()=>{ const c0=f47Stats().cut; Object.assign(inv,{steel:1,hide:2}); craft('af_work_chest'); return [+c0.toFixed(3), +f47Stats().cut.toFixed(3), p3cForgeA('work_chest')]; })()")
        vh = await E("(()=>{ Object.assign(inv,{steel:9,iron:10,oldParts:5,hardwood:4,rope:4}); craft('vu_plate'); craft('vu_tank'); craft('vu_frame'); return [TRUCK_SYS.hp.max[0], TRUCK_SYS.hp.beast, TRUCK_SYS.gas.perKm, TRUCK_SYS.bed.cap, TRUCK_SYS.bed.maxLogs, JSON.stringify(p3cState().vup)]; })()")
        cards = await E("(()=>{ CRAFT.tab='mat'; renderCraft(); const n=[...document.querySelectorAll('#craftList .wkCard')].length; return n; })()")
        await pg.wait_for_timeout(1500)
        await E("closeOverlay()")
        check(use.startswith('総合加工設備を使う') and ui[0] == '総合加工設備（拠点本部）' and ui[1] == 'mat,wforge,aforge,veh' and ui[2], f'「総合加工設備を使う」→ 画面（素材・武器・防具・車両）・本部の倉庫の素材も使える {ui}')
        check(stl == [2, 0, 0], f'鋼材を作る（川底の鉱石2・木炭2 → 鋼材1）{stl}')
        check(f1[0] == 10 and f1[1] == 11.5 and f1[2] == 120 and f1[3] == 3 and f1[4] == 1, f'鉈を鍛え直す：威力 10→11.5・耐久が満タン・4回で3しか減らない {f1}')
        check(ar[1] == round(ar[0] + 0.02, 3) and ar[2], f'作業着を補強：被ダメージ -2% {ar}')
        check(vh[:5] == [base0[3] + 40, 0.45, 9, 80, 8], f'KEI truck の高度加工：外装・燃料タンク・荷台の枠 {vh}')
        # つづきから
        await E("saveGame()")
        await boot()
        await pg.click('#btnContinue')
        await pg.wait_for_timeout(1500)
        await until("REG.cur==='kamishihi'&&!REG.busy&&S.mode==='playing'", 90000)
        await pg.wait_for_timeout(800)
        lp = await E("[p3cDone('works'), p3cForgeW('nata1'), p3cForgeA('work_chest'), TRUCK_SYS.gas.perKm, TRUCK_SYS.bed.maxLogs, inv.spindle, Object.keys(p3dState().obs).length, (()=>{ const kt=[...REG.live.ktrees.values()].find(k=>k.key===%s); return kt&&kt.felled; })(), prog.kami.r.q1]" % repr(hw[0]))
        check(lp == [True, 1, True, 9, 8, 0, 3, True, 0], f'つづきから：総合加工設備・鍛え直し・補強・車の数値・観察・切った広葉樹・割った鉱石が残る {lp}')
        await E("(()=>{ freshState(); return 1; })()")
        nw = await E("[TRUCK_SYS.gas.perKm, TRUCK_SYS.bed.cap, TRUCK_SYS.bed.maxLogs, TRUCK_SYS.hp.max[0], TRUCK_SYS.hp.beast]")
        check(nw == base0, f'新しく始めると、車の数値は元に戻る {nw}')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: P3-D の川の改修と総合加工設備' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
