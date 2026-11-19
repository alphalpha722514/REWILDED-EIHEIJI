#!/usr/bin/env python3
"""v0.82（P3-C の C-2）拠点の管理画面と工事の確認（画面のない Chromium。数分）。docs/p3c-c2.md

- 本部の中の掲示板（1階）と机（2階）で管理画面が開く。4つのタブ（復興段階・施設・住民・依頼）
- 復興段階：Lv1 の施設 n/4・正式に住む住民 n/2・指定の復興依頼
- 施設：分けて納める（持ち物 → 本部の倉庫 → 本部のそばの KEI truck の荷台）。素材は費用より多くは取らない
- 止まっている理由：素材が足りない・担当がいない・勤務時間外
- 住民の担当：1人 1.0倍・2人 1.5倍。勤務時間外は進まない。光明寺にいても進む
- 完成：「〇〇ができた」・担当は待機に戻る・共同住居は2階の見た目と「布団で休む」・基本防衛は前庭の柵と見張り台
- 布団で休む：朝 6:00 まで・体力が全快
- 住民は勤務時間に担当の工事の所にいる（共同住居は2階・基本防衛は前庭）
- 保存して「つづきから」：納めた素材・進み・担当が残る
- エラーなし
使い方：THREE_JS=…/three.min.js python3 tests/p3c-manage-browser.py
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
        await E("(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()")
        await until("REG.cur==='kamishihi'&&!REG.busy")
        await pg.wait_for_timeout(800)
        await E("(()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; stfP().mutantMet=true; szJoin(); szOrder('wait'); prog.f10.tod=150; const p=p3bState(); p.hq.sv=[1,1,1]; p.hq.talk=1; p.hq.plan=1; p.hq.beasts=1; p.rep.storage=[1,1,1]; p.rep.workshop=[1,1,1]; const c=p3cState(); c.hint=1; c.sumie={met:1,hits:3,done:1}; c.rio={met:1,shelf:1,talk:1,parts:[1,1],fixed:1,done:1}; return 1; })()")
        ob = await E("objective()[0]")
        check('拠点の管理で、共同住居と基本防衛設備の工事を進めよう' in ob, f'住民が2人そろうと、目的が工事になる（{ob}）')

        # ---- 本部に入って管理画面 ----
        hq = await E("(()=>{ const d=P3A.doors.find(d=>d.id==='hq'); return [d.x,d.z]; })()")
        await E(f"(P.x={hq[0]},P.z={hq[1]},1)")
        await pg.wait_for_timeout(300)
        await act('拠点本部に入る')
        await until("P3A.inside&&P3A.inId==='hq'&&!P3A.busy&&S.mode==='playing'")
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.id==='mgmt'); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(300)
        r = await act('拠点の管理（掲示板）')
        await until("!$('mgmtOv').hidden")
        tabs = await E("[...document.querySelectorAll('#mgmtTabs .wkTab')].map(b=>b.textContent)")
        conds = await E("[...document.querySelectorAll('#mgmtList .wkCard')].map(e=>e.textContent.replace(/\\s+/g,''))")
        check(r == '拠点の管理（掲示板）' and tabs == ['復興段階', '施設', '住民', '依頼'], f'1階の掲示板で管理画面が開く・4つのタブ {tabs}')
        check(any('Lv1の施設を直す2/4' in c for c in conds) and any('正式に住む住民2/2' in c for c in conds) and any('指定の復興依頼' in c for c in conds), f'復興段階：Lv1 の施設 2/4・住民 2/2・指定の依頼 {conds}')
        await E("closeOverlay()")
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.id==='mgmt2'); return m?1:0; })()")
        check(await E("P3A.interior.marks.some(k=>k.id==='mgmt2')"), '2階の拠点管理の部屋の机でも開ける')

        # ---- 納める：持ち物・本部の倉庫・本部のそばの荷台 ----
        await E("(()=>{ for(const k of P3B.carry.mats) inv[k]=0; inv.wood=10; inv.straw=12; prog.stash.kami={wood:8,rope:6}; const t=trk(); t.region='kamishihi'; t.repaired=true; t.bed.mats={wood:20,iron:4}; const d=P3A.doors.find(d=>d.id==='hq'); TRUCK.x=d.x+8; TRUCK.z=d.z+8; return 1; })()")
        near = await E("p3cTruckNearHQ()")
        await E("p3cDeliver('housing')")
        st = await E("[JSON.stringify(p3cFac().housing.dl), inv.wood, inv.straw, JSON.stringify(prog.stash.kami), JSON.stringify(trk().bed.mats)]")
        check(near and st == ['{"wood":24,"straw":12,"rope":6,"iron":4}', 0, 0, '{}', '{"wood":14}'], f'共同住居に納める：持ち物→本部の倉庫→本部のそばの荷台の順、費用より多く取らない {st}')
        await E("(()=>{ inv.wood=5; return 1; })()")
        await E("p3cDeliver('defense')")
        dd = await E("[JSON.stringify(p3cFac().defense.dl), p3cWhy('defense'), p3cWhy('housing')]")
        check(dd[0] == '{"wood":19}' and dd[1] == '素材が足りない' and dd[2] == '担当の住民がいない', f'分けて納める（基本防衛は木材だけ）・止まっている理由 {dd}')

        # ---- 担当と進み ----
        await E("(prog.f10.tod=150, p3cSetJob('sumie','b:housing'), 1)")
        h0 = await E("p3cFac().housing.h")
        await E("p3bAdvance(1)")
        h1 = await E("p3cFac().housing.h")
        await E("p3cSetJob('rio','b:housing')")
        await E("p3bAdvance(1)")
        h2 = await E("p3cFac().housing.h")
        check(abs(h1 - h0 - 1.0) < 0.02 and abs(h2 - h1 - 1.5) < 0.02, f'1人で1時間＝1.0時間分、2人で1時間＝1.5時間分進む（{round(h0,2)}→{round(h1,2)}→{round(h2,2)}）')
        await E("(prog.f10.tod=600,1)")
        why = await E("p3cWhy('housing')")
        await E("p3bAdvance(1)")
        h3 = await E("p3cFac().housing.h")
        check(abs(h3 - h2) < 0.01 and '勤務時間外' in why, f'勤務時間外（17:00 より後）は進まない（{why}）')
        # 勤務時間に担当の工事の所にいる（共同住居は2階）
        await E("(prog.f10.tod=150,1)")
        await pg.wait_for_timeout(900)
        sp = await E("(()=>{ p3cResVis(); return [Math.round(P3CM.sumie.x-P3A_IN.x), Math.round(P3CM.rio.x-P3A_IN.x)]; })()")
        check(sp == [50, 60], f'勤務時間：担当の住民は2階の共同住居の工事の所にいる {sp}')

        # ---- 光明寺にいても進む ----
        await E("(async()=>{ await p3aExit(); })()")
        await until("!P3A.inside&&!P3A.busy&&S.mode==='playing'")
        await E("(async()=>{ await regionTravel('komyoji',null,{force:true}); })()")
        await until("REG.cur==='komyoji'&&!REG.busy")
        h4 = await E("p3cFac().housing.h")
        await E("(prog.f10.tod=150, f10Clock(25), 1)")
        h5 = await E("p3cFac().housing.h")
        check(h5 - h4 > 0.7, f'光明寺にいても、時計が進むと上志比の工事が進む（{round(h4,2)}→{round(h5,2)}）')
        await E("p3bAdvance(2)")
        dn = await E("[p3cFac().housing.done, JSON.stringify(p3cState().job)]")
        check(dn == [1, '{"sumie":"","rio":"","evac":""}'], f'完成すると担当は待機に戻る {dn}')
        await until("$('banner').textContent.includes('共同住居ができた')", 5000)
        check('共同住居ができた' in await E("$('banner').textContent"), '「共同住居ができた」と出る')

        # ---- 上志比に戻る：布団・基本防衛 ----
        await E("(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()")
        await until("REG.cur==='kamishihi'&&!REG.busy")
        await pg.wait_for_timeout(600)
        await E("(()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; return 1; })()")
        dv = await E("[P3C.defG.done.visible, P3C.defG.wip.visible]")
        check(dv == [False, True], f'基本防衛：納めた素材の山が前庭に見える（まだ完成していない）{dv}')
        await E("(()=>{ inv.wood=1; inv.stone=10; inv.bamboo=10; inv.rope=6; inv.hide=4; p3cDeliver('defense'); p3cSetJob('rio','b:defense'); prog.f10.tod=150; return 1; })()")
        await pg.wait_for_timeout(900)
        out = await E("(()=>{ p3cResVis(); const B=szKamiBase(), d=P3A.doors.find(d=>d.id==='hq'); return [P3CM.rio.m.g.visible, Math.round(dist(P3CM.rio.x,P3CM.rio.z,d.x,d.z))]; })()")
        check(out[0] and 6 <= out[1] <= 14, f'基本防衛の担当は、勤務時間に前庭にいる {out}')
        await E("p3bAdvance(3.2)")
        dv = await E("[p3cFac().defense.done, P3C.defG.done.visible, P3C.defG.wip.visible]")
        check(dv == [1, True, False], f'基本防衛ができると、前庭に柵と見張り台 {dv}')
        await E(f"(P.x={hq[0]},P.z={hq[1]},1)")
        await pg.wait_for_timeout(300)
        await act('拠点本部に入る')
        await until("P3A.inside&&P3A.inId==='hq'&&!P3A.busy&&S.mode==='playing'")
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.rest); P.x=m.x; P.z=m.z; P.hp=5; prog.f10.tod=700; return 1; })()")
        await pg.wait_for_timeout(300)
        r = await act('布団で休む')
        await until("!P3A.busy&&S.mode==='playing'&&P.hp>5")
        rs = await E("[Math.round(P.hp)===P.maxHp, p3bClockText()]")
        check(r.startswith('布団で休む') and rs[0] and rs[1].startswith('6:0'), f'共同住居の布団で休む：朝 6:00 まで・体力が全快 {rs}')
        conds = await E("(()=>{ MG.tab='lv'; p3cOpenMgmt(); const t=[...document.querySelectorAll('#mgmtList .wkCard')].map(e=>e.textContent.replace(/\\s+/g,'')); closeOverlay(); return t; })()")
        check(any('Lv1の施設を直す4/4' in c for c in conds), f'Lv1 の施設 4/4 {conds}')

        # ---- 保存して、つづきから ----
        await E("saveGame()")
        await boot()
        await pg.click('#btnContinue')
        await pg.wait_for_timeout(1500)
        await until("REG.cur==='kamishihi'&&!REG.busy&&S.mode==='playing'", 60000)
        lp = await E("[p3cFac().housing.done, p3cFac().defense.done, JSON.stringify(p3cState().job)]")
        check(lp == [1, 1, '{"sumie":"","rio":"","evac":""}'], f'つづきから：施設の完成と担当が残る {lp}')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: P3-C 拠点の管理と工事' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
