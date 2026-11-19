#!/usr/bin/env python3
"""v0.83（P3-C の C-3）復興依頼とレベルアップの確認（画面のない Chromium。8分ほど）。docs/p3c-c3.md

- 住民が2人そろうと、澄江が依頼をまとめる（案内）。依頼のタブ：受けられる／条件がまだ（半鐘は基本防衛のあと）／段階がまだ（Lv2 の依頼）
- 必須の依頼「侵入経路と獣の痕跡の調査」：受ける（澄江の台詞）→ 目的の表示と光る印 → 足跡・柵・ふんを調べる → 素材が無いと柵をふさげない → ふさぐ（板が直る）→ 報告（報酬）
- 物置の資材回収（屋根を4回どかす→当たりが消える→資材を運び出す）・農業倉庫（土砂→工具箱→耕うん機）・火の見やぐらの半鐘（はしご→半鐘→報告で見張り台に付く）
- 復興 Lv2：条件3つがそろうまで上げられない → 上げる（本部の2階の閉じた部屋が「共同住居3」になる）
- Lv2 の依頼：避難住民（立て札→祠→蔵の戸を3回→住民 3/4）・用水路（水門の部品・種）・整備工場跡の屋内（棚→油圧ジャッキ）・南西の道の倒木（当たりが消える）→巻き上げ機の部品
- Lv2 の施設：農園・車両整備場・収集運搬施設を建てる → 住民の仕事（農園の世話・町の素材集め）で野菜と素材がたまる → 収穫箱で受け取る
- 車両整備場：KEI truck を屋根の下に止めると、車両基地の画面が開く・本部の倉庫の素材を使える
- Lv2→Lv3 の条件（住民 4人はまだ）・保存して「つづきから」で残る・古いセーブ・エラーなし

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
        await E("(()=>{ window.__away=()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; }; __away(); stfP().mutantMet=true; szJoin(); szOrder('wait'); prog.f10.tod=150; const p=p3bState(); p.hq.sv=[1,1,1]; p.hq.talk=1; p.hq.plan=1; p.hq.beasts=1; p.rep.storage=[1,1,1]; p.rep.workshop=[1,1,1]; const c=p3cState(); c.hint=1; c.sumie={met:1,hits:3,done:1}; c.rio={met:1,shelf:1,talk:1,parts:[1,1],fixed:1,done:1}; for(const k of P3B.carry.mats) inv[k]=0; return 1; })()")

        async def dlg(n=12):  # 会話を最後まで進め、出た台詞を返す
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

        async def go(id_, i, dx=1.2):  # 依頼の手順の所へ行く
            await E(f"(()=>{{ const sp=p3cSpot(P3C_REQ_BY.{id_}.steps[{i}]); P.x=sp.x+{dx}; P.z=sp.z; return 1; }})()")
            await pg.wait_for_timeout(250)

        async def step(id_, i, n=1):  # 手順を n 回する
            r = None
            for _ in range(n):
                await go(id_, i)
                r = await act(await E(f"P3C_REQ_BY.{id_}.steps[{i}].label.replace(/[()（）]/g,'.')"))
                await pg.wait_for_timeout(150)
            return r

        async def mg(tab):
            await E(f"(p3cOpenMgmt(), MG.tab='{tab}', p3cRenderMgmt(), 1)")
            return await E("[...document.querySelectorAll('#mgmtList .wkCard')].map(e=>e.id.replace('mgmtCard_','')+'|'+e.textContent.replace(/\\s+/g,''))")

        # ---- 案内と依頼のタブ ----
        await until("p3cState().hint2===1", 30000)
        h2 = await E("p3cState().hint2")
        cards = await mg('req')
        st = await E("P3C_REQ.map(q=>q.id+':'+p3cReqState(q)).join(' ')")
        check(h2 == 1 and st == 'trace:open salvage:open tools:open bell:wait evac:lock water:lock lift:lock road:lock' and any(c.startswith('q_trace|') and '【必須】' in c and '受けられる' in c for c in cards),
              f'住民が2人：澄江の依頼の案内・依頼のタブ（受けられる／条件がまだ／段階がまだ）{st} 案内{h2} {[c[:30] for c in cards[:2]]}')
        lv = await mg('lv')
        check(any(c.startswith('lvup|') and '条件がまだ' in c for c in lv) and not await E("!!document.getElementById('mgmt_lvup')"), f'復興 Lv2 に上げるボタンは、条件がそろうまで出ない {[c for c in lv if c.startswith("lvup")]}')
        await E("closeOverlay()")

        # ---- 必須の依頼：侵入経路と獣の痕跡の調査 ----
        await E("(p3cOpenMgmt(), MG.tab='req', p3cRenderMgmt(), document.getElementById('mgmt_q_trace').click(), 1)")
        lines = await dlg()
        ob = await E("p3bObjective()")
        check(lines == ['澄江｜ちょっと聞いてくれるか。夜になると、本部のまわりで獣の気配がするんや。', '澄江｜どこから入ってきよるんか、調べてきてくれんか。本部の裏と、畑の柵と、西の小川のあたりが怪しいわ。'] and await E("$('mgmtOv').hidden"),
              f'受ける：管理画面が閉じて澄江の台詞 {lines}')
        check(ob[0].startswith('上志比の依頼：本部の裏の足跡を調べる（侵入経路と獣の痕跡の調査 0/4）') and ob[1] is not None, f'目的に次の手順と場所 {ob}')
        mk = await E("P3C.mks.filter(k=>k.q.id==='trace'&&k.m.visible).map(k=>k.i).join(',')")
        check(mk == '0,1,2', f'今できる手順の所に光る印（足跡・柵・ふん。ふさぐのは柵を調べてから）{mk}')
        r0 = await step('trace', 0)
        r1 = await step('trace', 1)
        r2 = await step('trace', 2)
        await go('trace', 3)
        deny = await act('柵の穴をふさぐ')
        s3 = await E("p3cReq('trace').s[3]")
        await E("(inv.wood=6, inv.rope=3, 1)")
        r3 = await step('trace', 3)
        fx = await E("[P3C.rq.trace[3].pre[0].visible, P3C.rq.trace[3].post[0].visible, inv.wood, inv.rope]")
        check(r0 and r1 and r2 and s3 == 0 and fx == [False, True, 2, 1], f'足跡・柵・ふんを調べる → 素材が無いとふさげない → ふさぐ（倒れた板が直る・木材4と縄2を使う）{fx}')
        ob = await E("p3bObjective()[0]")
        check('拠点の管理で報告しよう' in ob, f'すべて済むと「報告しよう」 {ob}')
        await E("(p3cOpenMgmt(), MG.tab='req', p3cRenderMgmt(), document.getElementById('mgmt_q_trace').click(), 1)")
        lines = await dlg()
        rw = await E("[p3cReqDone('trace'), inv.hide, inv.iron, $('banner').textContent]")
        check(lines[0] == '澄江｜やっぱりな……。小川の方から来て、柵を倒して入っとったんやね。' and rw[0] and rw[1] == 3 and rw[2] == 2 and '依頼を達成' in rw[3], f'報告：澄江の台詞・報酬（獣素材3・屑鉄2）{rw}')

        # ---- 物置の資材回収・農業倉庫 ----
        await E("(p3cReqAccept('salvage'), 1)")
        await dlg()
        col0 = await E("P3C.rq.salvage[0].cols[0].active")
        await step('salvage', 0, 3)
        mid = await E("[p3cReq('salvage').h[0], p3cReq('salvage').s[0]]")
        await step('salvage', 0, 1)
        col1 = await E("[P3C.rq.salvage[0].cols[0].active, P3C.rq.salvage[0].pre[0].visible]")
        await step('salvage', 1)
        got = await E("[inv.wood, inv.iron, inv.oldParts]")
        check(col0 and mid == [3, 0] and col1 == [False, False] and got == [10, 5, 1], f'物置：屋根を4回どかす（当たりと屋根が消える）→ 資材を運び出す（木材8・屑鉄3・古い機械部品1）{mid} {col1} {got}')
        await E("(p3cReqAccept('tools'), 1)")
        await dlg()
        lk = await E("p3cStepOpen(P3C_REQ_BY.tools,p3cReq('tools'),2)")
        await step('tools', 0, 4)
        await step('tools', 1)
        await step('tools', 2, 3)
        tl = await E("[JSON.stringify(p3cReq('tools').s), inv.oldParts, P3C.rq.tools[0].post[0].visible]")
        check(lk is False and tl == ['[1,1,1]', 6, True], f'農業倉庫：耕うん機は入口を掘り出してから・土砂→工具箱→耕うん機（古い機械部品 +5）・シャッターが上がる {tl}')
        await E("(p3cReqReport('salvage'), 1)")
        await dlg()
        await E("(p3cReqReport('tools'), 1)")
        rl = await dlg()
        check(rl == ['リオ｜いいね、ちゃんと手入れされてた工具だ。部品もまだ使える。これで作業場でできることが増えるよ。'] and await E("p3cReqDone('salvage')&&p3cReqDone('tools')&&inv.rope===5&&inv.straw===6"), f'報告：リオの依頼はリオが話す・物置の報酬（縄4・藁6）{rl}')

        # ---- 基本防衛のあと：火の見やぐらの半鐘 ----
        await E("(()=>{ for(const id of ['housing','defense']){ const s=p3cFac()[id]; s.done=1; s.h=P3C_FAC[id].hours; s.dl=Object.assign({},P3C_FAC[id].cost); } p3cDefenseVis(); return 1; })()")
        st = await E("p3cReqState(P3C_REQ_BY.bell)")
        await E("(p3cReqAccept('bell'), 1)")
        await dlg()
        await step('bell', 0)
        await step('bell', 1)
        await step('bell', 2)
        b1 = await E("[inv.bell, P3C.rq.bell[1].post[0].visible, P3C.rq.bell[2].pre[0].visible, P3C.defG.bell.visible]")
        await E("(p3cReqReport('bell'), 1)")
        bl = await dlg()
        b2 = await E("[inv.bell, P3C.defG.bell.visible, inv.stone]")
        check(st == 'open' and b1 == [1, True, False, False] and b2 == [0, True, 6] and bl[0] == '｜見張り台に半鐘を吊るした。', f'半鐘：基本防衛のあとで受けられる・はしごを直す・半鐘を外す → 報告で見張り台に付く {b1} {b2}')

        # ---- 復興 Lv2 ----
        lv = await mg('lv')
        ok = await E("p3cLvReady()")
        await E("document.getElementById('mgmt_lvup').click()")
        ll = await dlg()
        lvs = await E("[p3cLevel(), P3C.cap[p3cLevel()], $('banner').textContent]")
        check(ok and any('指定の復興依頼達成' in c for c in lv) and lvs[0] == 2 and lvs[1] == 4 and '上志比の復興 Lv2' in lvs[2] and ll[0].startswith('澄江｜建物も人も'), f'条件がそろうと Lv2 に上げられる（住める人 4）{lvs}')
        st = await E("P3C_REQ.map(q=>q.id+':'+p3cReqState(q)).join(' ')")
        check(st == 'trace:done salvage:done tools:done bell:done evac:open water:open lift:open road:open', f'Lv2 の依頼が受けられる {st}')
        hq = await E("(()=>{ const d=P3A.doors.find(d=>d.id==='hq'); return [d.x,d.z]; })()")
        await E(f"(P.x={hq[0]},P.z={hq[1]},1)")
        await pg.wait_for_timeout(300)
        await act('拠点本部に入る')
        await until("P3A.inside&&P3A.inId==='hq'&&!P3A.busy&&S.mode==='playing'")
        rooms = await E("P3A.interior.rooms.map(r=>r.name).join(',')")
        check('共同住居3' in rooms and rooms.count('閉じた部屋') == 1, f'本部の2階：閉じた部屋の一つが「共同住居3」に {rooms}')
        await act('外へ出る')
        await until("!P3A.inside&&!P3A.busy&&S.mode==='playing'")

        # ---- 避難住民 ----
        for q in ['evac', 'water', 'lift', 'road']:
            await E(f"(p3cReqAccept('{q}'), 1)")
            await dlg()
        await step('evac', 0)
        await step('evac', 1)
        n0 = await E("p3cResidents().length")
        await step('evac', 2, 3)
        el = await dlg()
        ev = await E("(()=>{ p3cResVis(); return [p3cResidents().join(','), !!(P3CM.evac&&P3CM.evac.m.g.visible), P3C.rq.evac[2].pre[0].visible]; })()")
        check(n0 == 2 and ev == ['sumie,rio,evac', True, False] and el[0] == '｜蔵の中に、男の人がひとり隠れていた。', f'書き置き2つ → 蔵の戸の前を3回どかす → 避難住民が住民に（蔵の前に出てくる）{ev} {el[:1]}')
        # ---- 用水路・倒木・整備工場跡の屋内 ----
        await step('water', 0, 4)
        await step('water', 1)
        await step('water', 2)
        rcol = await E("P3C.rq.road[0].cols[0].active")
        await step('road', 0, 6)
        await step('road', 1)
        wr = await E("[inv.gatePart, inv.seed, inv.winchPart, P3C.rq.road[0].cols[0].active, P3C.rq.road[0].post[0].visible]")
        check(wr == [1, 4, 1, False, True] and rcol, f'水門の部品・大根の種4・倒木を6回で片付ける（道が通る）・巻き上げ機の部品 {wr}')
        fd = await E("(()=>{ const d=P3A.doors.find(d=>d.id==='factory'); return [d.x,d.z]; })()")
        ob = await E("(p3cState().trk='lift', p3bObjective())")
        check(ob[1] is not None and abs(ob[1]['x'] - fd[0]) < 0.1, f'屋内の手順は、外では整備工場跡の入口を指す {ob}')
        await E(f"(P.x={fd[0]},P.z={fd[1]},1)")
        await pg.wait_for_timeout(300)
        await act('整備工場跡に入る')
        await until("P3A.inside&&P3A.inId==='factory'&&!P3A.busy&&S.mode==='playing'")
        for i, n in [(0, 3), (1, 1)]:
            for _ in range(n):
                await E(f"(()=>{{ const m=P3A.interior.marks.find(k=>k.req&&k.req[1]==={i}); if(m){{ P.x=m.x; P.z=m.z; }} return 1; }})()")
                await pg.wait_for_timeout(200)
                await act('倒れた棚|油圧ジャッキ')
                await pg.wait_for_timeout(250)
            await until("!P3A.busy", 5000)
            await pg.wait_for_timeout(400)
        lf = await E("[JSON.stringify(p3cReq('lift').s), inv.liftJack]")
        check(lf == ['[1,1]', 1], f'整備工場跡の部品庫：倒れた棚を3回で起こす → 油圧ジャッキ（整備工場の特殊部品）{lf}')
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.exit); P.x=m.x+0.4; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        await act('外へ出る')
        await until("!P3A.inside&&!P3A.busy&&S.mode==='playing'")
        check(await E("!P3A.inside"), '整備工場跡から外へ出る')
        for q in ['evac', 'water', 'lift', 'road']:
            await E(f"(p3cReqReport('{q}'), 1)")
            await dlg()
        check(await E("['evac','water','lift','road'].every(p3cReqDone)"), 'Lv2 の依頼4つを報告')

        # ---- Lv2 の施設と住民の仕事 ----
        await E("(()=>{ Object.assign(inv,{wood:80,stone:40,iron:30,rope:30,bamboo:20,oldParts:8}); prog.stash.kami={}; for(const id of ['farm','garage','haul']) p3cDeliver(id); return 1; })()")
        stk = await E("['farm','garage','haul'].map(p3cStocked)")
        await E("(prog.f10.tod=100, p3cSetJob('sumie','b:farm'), p3cSetJob('rio','b:garage'), p3cSetJob('evac','b:haul'), p3bAdvance(4), 1)")
        dn = await E("[['farm','garage','haul'].map(p3cDone), P3C.f2.farm.done.visible, P3C.f2.garage.done.visible, P3C.f2.haul.done.visible, P3C.f2.garage.cols[0].active, JSON.stringify(p3cState().job)]")
        check(stk == [True, True, True] and dn == [[True, True, True], True, True, True, True, '{"sumie":"","rio":"","evac":""}'], f'農園（水門の部品・種）・車両整備場（特殊部品）・収集運搬施設（巻き上げ機の部品）を建てる {stk} {dn}')
        await E("(prog.f10.tod=100, p3cSetJob('sumie','w:farm'), p3cSetJob('evac','w:haul'), p3bAdvance(9), 1)")
        wk = await E("[p3cState().out.veg, JSON.stringify(prog.stash.kami), p3cJobState('sumie')]")
        check(wk[0] == 3 and '"wood":5' in wk[1] and '"stone":3' in wk[1] and '"iron":2' in wk[1], f'勤務の9時間：農園の世話で野菜3・町の素材集めで木材5・石3・屑鉄2…（本部の倉庫へ）{wk}')
        await E("(()=>{ const b=p3cHQLocal(P3C_SITE.farm.a+11,P3C_SITE.farm.d-6.5); P.x=b.x+0.8; P.z=b.z; inv.veg=0; return 1; })()")
        await pg.wait_for_timeout(250)
        hv = await act('農園の収穫を受け取る')
        check(hv.startswith('農園の収穫を受け取る') and await E("inv.veg===3&&p3cState().out.veg===0"), f'収穫箱で野菜を受け取る {hv}')
        cards = await mg('res')
        check(any(c.startswith('r_evac|') and '町の素材集め' in c for c in cards), f'住民のタブに避難住民と仕事 {[c[:40] for c in cards]}')
        await E("closeOverlay()")
        # ---- 車両整備場 ----
        await E("(()=>{ const t=trk(); t.region='kamishihi'; t.repaired=true; t.hp=40; const g=p3cHQLocal(P3C_SITE.garage.a,P3C_SITE.garage.d); TRUCK.x=g.x; TRUCK.z=g.z; TRUCK.drive=false; P.x=g.x+1.5; P.z=g.z+3.6; prog.stash.kami.wood=50; return 1; })()")
        await pg.wait_for_timeout(300)
        ga = await act('車両整備場')
        await until("!$('depotOv').hidden", 5000)
        gd = await E("[p3cGarageParked(), !$('depotOv').hidden, (stashHere()||{}).wood, $('depotOv').querySelector('h2').textContent]")
        check(ga.startswith('車両整備場（直す') and gd[0] and gd[1] and gd[2] >= 50 and gd[3] == '車両整備場（上志比）', f'車両整備場：KEI truck を止めると車両基地の画面が開く・本部の倉庫の素材を使える {ga} {gd}')
        await E("closeOverlay()")
        c3 = await E("p3cLvConds().map(q=>q.name+q.v+(q.ok?'○':'×')).join(' ')")
        check(c3 == 'Lv2 の施設を建てる3/3○ 正式に住む住民3/4× 指定の復興依頼達成○' and not await E("p3cLvReady()"), f'Lv2→Lv3 の条件：住民 4人はまだ（宗一は釣りの段階）{c3}')

        # ---- つづきから ----
        await E("saveGame()")
        await boot()
        await pg.click('#btnContinue')
        await pg.wait_for_timeout(1500)
        await until("REG.cur==='kamishihi'&&!REG.busy&&S.mode==='playing'", 60000)
        await pg.wait_for_timeout(1000)
        lp = await E("[p3cLevel(), P3C_REQ.filter(q=>p3cReqDone(q.id)).length, p3cResidents().join(','), JSON.stringify(p3cState().job), ['farm','garage','haul'].map(p3cDone).join(','), P3C.rq.road[0].cols[0].active, P3C.defG.bell.visible]")
        check(lp == [2, 8, 'sumie,rio,evac', '{"sumie":"w:farm","rio":"","evac":"w:haul"}', 'true,true,true', False, True], f'つづきから：段階・依頼・避難住民・仕事・施設・道・半鐘が残る {lp}')
        # 古いセーブ（v0.82 の p3c）：Lv1・依頼なし
        old = await E("(()=>{ const q=p3cLoad({v:1,sumie:{done:1},rio:{done:1},fac:{housing:{done:1}},job:{sumie:'b:defense'}}); return [q.lv, JSON.stringify(q.req), q.ev.res, JSON.stringify(q.job)]; })()")
        check(old == [1, '{}', 0, '{"sumie":"b:defense","rio":"","evac":""}'], f'古いセーブ：Lv1・依頼なし・避難住民なし {old}')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: P3-C 復興依頼とレベルアップ' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
