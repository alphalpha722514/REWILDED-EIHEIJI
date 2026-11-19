#!/usr/bin/env python3
"""v0.84（P3-D の D-1）九頭竜川の釣りと宗一の確認（画面のない Chromium。10分ほど）。docs/p3d-d1.md

- 釣り竿が無いと釣れない → 作業台の「簡易釣り竿」→ 河内川（支流）の岸で「釣りをする」
- 投げる（押して離す）→ 待つ → アタリ（通常の魚は 1.0秒）→ 合わせる → 魚が持ち物と図鑑に（場所・時間帯・大きさ）
- 早すぎる・遅すぎる・水に届かない・歩くとやめる
- 初めて釣りをすると宗一が来る（Claude の台詞）→ 加入依頼（道具箱・リール・仕掛けの箱・素材が無いと直せない）→ 宗一に報告 → 協力者（住民には数えない）
- アラレガコ（本流の瀬）：専用の場面 → すぐ川へ戻す（持ち物に入らない）→ 宗一に報告（§15 の台詞のまま）→ 川守の釣り竿（1回だけ）
- 川底をのぞく（目撃）・図鑑の画面・Lv2 で宗一が本部に住む（住民 4人）・保存して「つづきから」・古いセーブ・エラーなし

使い方：THREE_JS=…/three.min.js python3 tests/p3d-fishing-browser.py
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
        await E("(()=>{ window.__away=()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; }; __away(); stfP().mutantMet=true; szJoin(); szOrder('wait'); prog.f10.tod=150; weather.state='clear'; const p=p3bState(); p.hq.sv=[1,1,1]; p.hq.talk=1; p.hq.plan=1; p.hq.beasts=1; p.rep.storage=[1,1,1]; p.rep.workshop=[1,1,1]; const c=p3cState(); c.hint=1; c.hint2=1; c.sumie={met:1,hits:3,done:1}; c.rio={met:1,shelf:1,talk:1,parts:[1,1],fixed:1,done:1}; for(const k of P3B.carry.mats) inv[k]=0; return 1; })()")

        async def dlg(n=16):  # 会話を最後まで進め、出た台詞を返す
            got = []
            for _ in range(n * 6):
                if await E("$('dialog').hidden"):
                    if got:
                        break
                    await pg.wait_for_timeout(150)
                    continue
                got.append(await E("$('dlgName').textContent+'｜'+$('dlgText').textContent"))
                await E("(dlgLock=0, advanceDialog(), 1)")
                await pg.wait_for_timeout(120)
            return got

        async def sky():  # 河原は画面のない Chromium では重いので、計算の間は空を向けておく
            await E("(cam.override={p:new THREE.Vector3(P.x,groundH(P.x,P.z)+3,P.z), l:new THREE.Vector3(P.x+0.01,groundH(P.x,P.z)+60,P.z), fov:50}, 1)")

        async def cast(pick=None):  # 投げて、アタリまで進める（待ち時間は縮める）
            await E("p3dPress()")
            await until("P3D.fish&&P3D.fish.t>0.3", 60000)
            await E("p3dRelease()")
            if await E("P3D.fish&&P3D.fish.st==='fly'"):
                if pick:
                    await E(f"(P3D.fish.fishPick={pick}, 1)")
                await E("(P3D.fish.t=0.6, P3D.fish.wait=0.05, 1)")
                await until("P3D.fish&&P3D.fish.st==='bite'", 60000)
            return await E("P3D.fish&&P3D.fish.st")

        CREEK = "(()=>{ for(let r=3;r<8;r+=0.5) for(let a=0;a<16;a++){ const x=6292+Math.cos(a*Math.PI/8)*r, z=822+Math.sin(a*Math.PI/8)*r; if(kamiReach(x,z)&&!p3dWater(x,z)){ P.x=x; P.z=z; if(p3dShore()) return [x,z]; } } return null; })()"

        # ---- 釣り竿 ----
        sp = await E(CREEK)
        await pg.wait_for_timeout(300)
        lb = await act('釣りをする')
        no = await E("!P3D.fish")
        r1 = await E("(()=>{ const r=RECIPES.find(r=>r.id==='rod1'); const s=r.show(); r.give(); return [s, p3dRod(), RECIPES.find(r=>r.id==='rod2').lock()]; })()")
        check(sp is not None and lb.startswith('釣りをする（釣り竿が要る') and no and r1 == [True, 'basic', True], f'釣り竿が無いと釣れない → 作業台の簡易釣り竿 → 川漁師の竿は上志比の総合作業場で Lv2 から {lb} {r1}')

        # ---- 河内川で釣る ----
        await sky()
        lb = await act('釣りをする')
        st0 = await E("[P3D.fish&&P3D.fish.st, !$('fishUi').hidden, $('fishBtn').textContent]")
        st = await cast('FISH_BY.fUgui')
        info = await E("[P3D.fish.area, P3D.fish.place, P3D.fish.win, $('fishBtn').textContent]")
        await E("p3dPress()")
        await until("P3D.fish&&P3D.fish.st==='ready'", 60000)
        got = await E("[inv.fUgui, JSON.stringify(p3dState().book.fUgui||null), p3dState().casts]")
        check(lb == '釣りをする（簡易釣り竿）' and st0 == ['ready', True, '投げる'] and st == 'bite' and info[:3] == ['trib', '河内川', 1] and info[3] == '合わせる！' and got[0] == 1 and '"where":"河内川（支流）"' in got[1] and '"band":"昼"' in got[1],
              f'河内川（支流）：投げる → 待つ → アタリ（通常の魚は 1.0秒）→ 合わせる → ウグイが持ち物と図鑑に {info} {got}')
        # ---- 宗一が来る ----
        await until("!!P3D.so||!$('dialog').hidden", 60000)
        await E("(P3D.so&&(P3D.so.t=5), 1)")
        await until("!$('dialog').hidden", 90000)
        lines = await dlg()
        rq = await E("[p3cState().soichi.found, JSON.stringify(p3cReq('soichi')), p3cState().trk, p3bObjective()[0], p3cResidents().length]")
        check(lines[:2] == ['｜後ろから、長靴の足音が近づいてきた。', '宗一｜おっ、竿を出しとるんか。この川で釣りをしとる人を見るのは、久しぶりやな。'] and lines[2] == '主人公｜上志比の本部で、町を立て直しています。' and len(lines) == 7 and rq[0] == 1 and '"a":1' in rq[1] and rq[2] == 'soichi' and rq[3].startswith('上志比の依頼：流木の下の道具箱を引き出す') and rq[4] == 2,
              f'初めて釣りをすると宗一が来る → 加入依頼を受ける（目的に出る・住民の数は変わらない）{lines[:3]} {rq}')
        # ---- 早すぎる・逃げられる・届かない・歩くとやめる ----
        await sky()
        await act('釣りをする')
        await E("p3dPress()")
        await until("P3D.fish.t>0.3", 60000)
        await E("p3dRelease()")
        await E("(P3D.fish.t=0.6, P3D.fish.wait=99, 1)")
        await until("P3D.fish.st==='wait'", 60000)
        await E("p3dPress()")
        e1 = await E("[P3D.fish.st, $('toasts').textContent]")
        st = await cast()
        await E("(P3D.fish.win=0.01, 1)")
        await until("P3D.fish.st==='ready'", 60000)
        e2 = await E("$('toasts').textContent")
        await E("(P.facing+=Math.PI, 1)")
        await E("p3dPress()")
        await until("P3D.fish.t>0.3", 60000)
        await E("(P3D.fish.t=0.5, p3dRelease(), 1)")
        e3 = await E("[P3D.fish.st, $('toasts').textContent]")
        await E("keys.add('w')")
        await until("!P3D.fish", 60000)
        await E("keys.delete('w')")
        e4 = await E("!P3D.fish&&$('fishUi').hidden")
        check(e1[0] == 'ready' and '早すぎた' in e1[1] and '逃げられた' in e2 and e3[0] == 'ready' and '水に届かなかった' in e3[1] and e4, f'早すぎる・遅すぎる・水に届かない・歩くとやめる {e1} {e2} {e3}')

        # ---- 宗一の依頼（九頭竜川の河原）----
        for i, n in [(0, 2), (1, 3), (2, 1)]:
            for _ in range(n):
                await E(f"(()=>{{ const sp=p3cSpot(P3C_REQ_BY.soichi.steps[{i}]); P.x=sp.x+1.0; P.z=sp.z; return 1; }})()")
                await sky()
                await pg.wait_for_timeout(200)
                await act(await E(f"P3C_REQ_BY.soichi.steps[{i}].label"))
                await pg.wait_for_timeout(150)
        s3 = await E("JSON.stringify(p3cReq('soichi').s)")
        await E("(()=>{ const w=p3dSoichiWhere(); P.x=w.x+1.4; P.z=w.z; p3cResVis(); return 1; })()")
        await pg.wait_for_timeout(300)
        d1 = await E("(p3cTalk('soichi'), [JSON.stringify(p3cReq('soichi').s), $('toasts').textContent])")
        await E("(inv.bamboo=2, inv.rope=2, inv.oldParts=1, 1)")
        await E("p3cTalk('soichi')")
        await pg.wait_for_timeout(300)
        s4 = await E("[JSON.stringify(p3cReq('soichi').s), inv.bamboo, inv.oldParts]")
        await E("p3cTalk('soichi')")
        ll = await dlg()
        co = await E("[p3cState().soichi.coop, p3cState().soichi.joinDone, p3cReqDone('soichi'), p3cResidents().length, p3cLvConds(1)[1].v, $('banner').textContent]")
        check(s3 == '[1,1,1,0]' and d1[0] == '[1,1,1,0]' and '素材が足りない' in d1[1] and s4 == ['[1,1,1,1]', 0, 0] and ll[0] == '宗一｜おお、どれもわしのや。……よし、これで竿がまた使える。' and co[:4] == [1, 1, True, 2] and co[4] == '2/2',
              f'道具箱（2回）・リール（3回）・仕掛けの箱 → 素材が無いと直せない → 直す → 宗一に報告 → 協力者（住民には数えない）{s3} {d1} {s4} {co}')

        # ---- アラレガコ（本流の瀬）----
        await E("(()=>{ const f=P3A.fishSpots[2]; P.x=f.x; P.z=f.z; return 1; })()")
        await sky()
        await pg.wait_for_timeout(300)
        await act('釣りをする')
        st = await cast('ARAGAKO')
        ar0 = await E("[P3D.fish.area, P3D.fish.win]")
        n0 = await E("FISH.reduce((a,f)=>a+(inv[f.id]||0),0)")
        await E("p3dPress()")
        await until("P3D.fish&&P3D.fish.st==='ara'", 60000)
        ar1 = await E("[!!cam.override, $('banner').textContent, JSON.stringify(p3dState().ara)]")
        await until("P3D.fish&&P3D.fish.st==='ready'", 120000)
        n1 = await E("FISH.reduce((a,f)=>a+(inv[f.id]||0),0)")
        check(st == 'bite' and abs(ar0[1] - 0.7) < 1e-9 and ar1[0] and 'アラレガコ' in ar1[1] and '"caughtReleased":1' in ar1[2] and '"reported":0' in ar1[2] and n1 == n0,
              f'アラレガコ：猶予 0.7秒・専用のカメラ → すぐ川へ戻す（持ち物に入らない）{ar0} {ar1}')
        await E("p3dStop()")
        await E("(()=>{ const w=p3dSoichiWhere(); P.x=w.x+1.4; P.z=w.z; return 1; })()")
        await pg.wait_for_timeout(300)
        await E("p3cTalk('soichi')")
        opts = await E("[...document.querySelectorAll('#defenseChoice button')].map(b=>b.textContent)")
        await E("[...document.querySelectorAll('#defenseChoice button')].find(b=>b.textContent.includes('見慣れない魚')).click()")
        al = await dlg(14)
        want = ['主人公｜この前、川で見慣れない魚が釣れたんです。すぐに川へ戻しました。', '宗一｜どんな魚やった？', '主人公｜頭が大きくて、石みたいな模様で……。', '宗一｜……それ、アラレガコやないか。', '主人公｜アラレガコ？',
                '宗一｜昔から九頭竜川で知られとる魚や。でも、今は数が減っとる。大事にせんとな。', '主人公｜そうだったんですね。', '宗一｜川へ戻してくれたんやな。ありがとう。', '｜宗一が使い込まれた釣り竿を取り出す。',
                '宗一｜これを使ってくれ。いい竿やぞ。これからも、この川のことをよう見てやってほしい。', '主人公｜ありがとうございます。大切に使います。']
        rw = await E("[p3dRod(), JSON.stringify(p3dState().ara), $('banner').textContent]")
        await E("p3cTalk('soichi')")
        opts2 = await E("[...document.querySelectorAll('#defenseChoice button')].map(b=>b.textContent)")
        await E("(()=>{ const d=document.getElementById('defenseChoice'); if(d) d.remove(); return 1; })()")
        check(any('見慣れない魚' in o for o in opts) and al == want and rw[0] == 'guard' and '"reported":1,"rodRewardClaimed":1' in rw[1] and '川守の釣り竿' in rw[2] and not any('見慣れない魚' in o for o in opts2),
              f'宗一に報告：§15 の台詞そのまま（11行）→ 川守の釣り竿 → 2回目は出ない {rw}')
        # 川守の竿：猶予 1.3倍
        await E("(()=>{ const f=P3A.fishSpots[2]; P.x=f.x; P.z=f.z; return 1; })()")
        await act('釣りをする')
        st = await cast('FISH_BY.fAyu')
        w2 = await E("[P3D.fish.rod, P3D.fish.win]")
        await E("p3dStop()")
        check(st == 'bite' and w2[0] == 'guard' and abs(w2[1] - 1.3) < 1e-9, f'川守の釣り竿：猶予 1.3秒（暫定）{w2}')
        # ---- 川底をのぞく・図鑑 ----
        await E("(()=>{ const f=P3A.fishSpots[1]; P.x=f.x; P.z=f.z; P3D.look=0; P3D.forceSee=1; return 1; })()")
        lk = await act('川底をのぞく')
        await E("(P3D.forceSee=0, 1)")
        await E("p3dOpenBook()")
        bk = await E("[!$('bookOv').hidden, document.querySelectorAll('#bookList .wkCard').length, document.querySelectorAll('#bookList .wkCard.lock').length, $('bookSub').textContent, (BOOK.sel='ara', p3dRenderBook(), $('bookDet').textContent)]")
        await E("closeOverlay()")
        check(lk == '川底をのぞく' and bk[0] and bk[1] == 12 and bk[2] == 10 and '魚類 2/12' in bk[3] and '保護報告済み' in bk[4] and '持ち帰らない魚' in bk[4],
              f'川底をのぞく・図鑑（12種・見つけた2つ（ウグイ・アラレガコ）・アラレガコは保護報告済み）{bk[:4]}')

        # ---- Lv2 で本部に住む ----
        await E("(()=>{ const c=p3cState(); c.lv=2; c.ev.res=1; return 1; })()")
        await E("(()=>{ const w=p3dSoichiWhere(); P.x=w.x+1.4; P.z=w.z; return 1; })()")
        ob = await E("p3bObjective()[0]")
        await E("p3cTalk('soichi')")
        await E("[...document.querySelectorAll('#defenseChoice button')].find(b=>b.textContent.includes('空き部屋')).click()")
        mv = await dlg()
        rs = await E("[p3cResidents().join(','), p3cLvConds(2)[1].v, p3cLvConds(2)[1].ok]")
        check('宗一に、本部の空き部屋に住まないか聞こう' in ob and mv == ['宗一｜部屋が空いとるんか。……ほな、世話になろうかな。朝は川に通わせてもらうで。'] and rs == ['sumie,rio,evac,soichi', '4/4', True], f'復興 Lv2 の空き部屋：宗一が本部に住む（住民 4/4）{ob} {rs}')

        # ---- つづきから ----
        await E("saveGame()")
        await boot()
        await pg.click('#btnContinue')
        await pg.wait_for_timeout(1500)
        await until("REG.cur==='kamishihi'&&!REG.busy&&S.mode==='playing'", 60000)
        await pg.wait_for_timeout(1000)
        lp = await E("[p3dRod(), JSON.stringify(p3dState().ara), p3dState().book.fUgui&&p3dState().book.fUgui.n, inv.fUgui, p3cState().soichi.coop, p3cState().soichi.resident, p3cReqDone('soichi')]")
        check(lp == ['guard', '{"observed":1,"caughtReleased":1,"reported":1,"rodRewardClaimed":1}', 1, 1, 1, 1, True], f'つづきから：釣り竿・アラレガコの記録・図鑑・魚・宗一が残る {lp}')
        old = await E("JSON.stringify(p3dLoad(undefined))")
        check(old == '{"v":1,"rod":{"basic":0,"pro":0,"guard":0},"book":{},"ara":{"observed":0,"caughtReleased":0,"reported":0,"rodRewardClaimed":0},"casts":0,"catches":0}', f'古いセーブ（p3d なし）：釣り竿も記録もない {old}')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: P3-D 釣りと宗一' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
