#!/usr/bin/env python3
"""v0.82（P3-C の C-1）住民と救助の確認（画面のない Chromium。数分）。docs/p3c-c1.md

- 拠点設立の会話の前は、澄江の家・整備工場跡の入口が出ない
- 会話のあと：目的が「逃げ遅れた人を探そう（住民 0/2）」で、近い方を指す
- 澄江（スズキがそばにいる）：戸を調べる → 指示書 §9 の台詞そのまま（スズキの台詞あり）→ がれきを3回どかす → 地の文 → 澄江の台詞 → 住民 1/2。がれきの形と当たりが消える
- リオ（スズキがいない）：整備工場跡に入る → 指示書 §10 の台詞（スズキの台詞は出ない・代わりの地の文）→ 工具棚を動かす → 部品2つ（足りないと直せない）→ コンプレッサーを直す（時間が30分進む）→ 住民 2/2
- 本部の中：昼は1階（澄江は入口ホール・リオは作業場）、夜は2階。話しかけられる
- スズキの「上志比の拠点で過ごせ」（拠点設立のあと）・保存して読み込んでも上志比の拠点のまま
- 保存して「つづきから」：住民・がれき・工具棚の状態が残る。古いセーブ（p3c が無い）は誰もいない
- エラーなし
使い方：THREE_JS=…/three.min.js python3 tests/p3c-residents-browser.py
"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
HTML = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read().replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){', 1)
# 指示書 v1.1 §9・§10 の正式採用台詞（そのまま比べる）
SUMIE1 = ['主人公：誰かいるんですか？', '澄江：おるよ！ こっちは大丈夫やけど、戸が開かんのや。', 'スズキ：よし、これをどかせば……って、結構重いな！']
SUMIE2 = ['：主人公が障害物を取り除き、扉が開く。', '澄江：助かったわ。私は山下澄江。この辺の人たちがどうなったか、ずっと気になっとったんや。',
          '主人公：俺たちは、近くの建物を拠点として直し始めたところです。', '澄江：そうか……。なら、私にも手伝わせてくれんか。あの人らが戻れる場所を作りたいんや。']
RIO1_NOSZ = ['リオ：いるよ。そこの工具棚、少し動かしてもらえる？']
RIO2_NOSZ = ['：主人公が棚を動かす。', 'リオ：ありがとう。南部リオ。ここに残って使える機械を調べてたんだ。', 'リオ：まだ直せるのに、捨てておくのがもったいなくて。',
             '主人公：上志比に拠点を作っている。整備ができる人を探しているんだ。', 'リオ：……拠点？ 作業場所もあるの？', '：主人公はうなずいた。', 'リオ：それなら話は早い。設備を見せてもらっていい？']
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

        async def lines(n=20):
            out = []
            await until("!$('dialog').hidden", 8000)
            for _ in range(n):
                if await pg.evaluate("document.getElementById('dialog').hidden"):
                    break
                out.append(await pg.evaluate("document.getElementById('dlgName').textContent+'：'+document.getElementById('dlgText').textContent"))
                await E("advanceDialog()")
                await pg.wait_for_timeout(220)
            return out

        async def go(x, z, wait=400):
            await E(f"(P.x={x},P.z={z},1)")
            await pg.wait_for_timeout(wait)

        away = "(()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; return 1; })()"
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
        await E(away)
        await E("(stfP().mutantMet=true, szJoin(), prog.f10.tod=200, 1)")

        # ---- 拠点設立の前 ----
        sd = await E("(()=>{ const d=p3cSumieDoor(); return [d.ox,d.oz]; })()")
        fd = await E("(()=>{ const d=p3cFactoryDoor(); return [d.x,d.z]; })()")
        await go(sd[0], sd[1])
        r1 = await act('家の戸')
        await go(fd[0], fd[1])
        r2 = await act('整備工場跡')
        check(r1.startswith('none') and r2.startswith('none'), f'拠点設立の会話の前は、澄江の家・整備工場跡に何も出ない（{r1}／{r2}）')

        # ---- 拠点設立のあと ----
        await E("(()=>{ const p=p3bState(); p.hq.sv=[1,1,1]; p.hq.talk=1; p.hq.plan=1; p.hq.beasts=1; p.rep.storage=[1,1,1]; p.rep.workshop=[1,1,1]; return 1; })()")
        await go(sd[0] + 60, sd[1] + 60, 300)
        ob = await E("(()=>{ const o=objective(); return [o[0], o[1]&&Math.round(o[1].x), o[1]&&Math.round(o[1].z)]; })()")
        check('逃げ遅れた人を探そう（住民 0/2）' in ob[0] and ob[1] is not None, f'目的：逃げ遅れた人を探そう（住民 0/2）・場所を指す {ob}')
        await until("p3cState().hint===1", 8000)
        check(await E("p3cState().hint") == 1, '本部の修理が済んでいると、最初に案内が出る')

        # ---- 澄江（スズキがそば）----
        await go(sd[0], sd[1], 300)
        await E("(SZ.x=P.x+1.2,SZ.z=P.z+1.2,szOrder('follow'),1)")
        await pg.wait_for_timeout(300)
        r = await act('家の戸を調べる')
        L1 = await lines()
        check(L1 == SUMIE1, f'澄江：指示書 §9 の台詞（スズキがいるのでスズキの台詞も）{L1}')
        pile0 = await E("[P3C.pile.filter(m=>m.visible).length, P3C.pileCol.active]")
        for i in range(3):
            await E("(SZ.x=P.x+1.2,SZ.z=P.z+1.2,1)")
            rr = await act('がれきをどかす')
            await pg.wait_for_timeout(250)
        L2 = await lines()
        check(L2 == SUMIE2, f'がれきを3回どかすと、地の文と澄江の台詞（§9 のまま）{L2}')
        st = await E("[JSON.stringify(p3cState().sumie), p3cResidents().join(','), P3C.pile.filter(m=>m.visible).length, P3C.pileCol.active]")
        check(pile0 == [3, True] and st == ['{"met":1,"hits":3,"done":1}', 'sumie', 0, False], f'澄江が住民になる。がれきの形と当たりが消える（前 {pile0}・後 {st}）')
        await until("$('banner').textContent.includes('山下澄江')", 6000)
        check('山下澄江が仲間になった' in await E("$('banner').textContent"), '「山下澄江が仲間になった」と出る')

        # ---- リオ（スズキはいない）----
        await E("(SZ.x=P.x+80,SZ.z=P.z+80,szOrder('wait'),SZ.wx=SZ.x,SZ.wz=SZ.z,1)")
        await go(fd[0], fd[1], 300)
        r = await act('整備工場跡に入る')
        await until("P3A.inside&&P3A.inId==='factory'&&!P3A.busy&&S.mode==='playing'")
        check(await E("P3A.inside&&P3A.inId==='factory'"), f'整備工場跡に入れる（{r}）')
        await E("(()=>{ const o=P3IN.factory.o; P.x=o.x+18.0; P.z=o.z+4.8; return 1; })()")
        R1 = await lines()
        check(R1 == RIO1_NOSZ, f'リオ：近づくと声がする（スズキがいないのでスズキの台詞は出ない）{R1}')
        await until("P3A.interior.marks.some(k=>k.shelf)")
        await E("(()=>{ const o=P3IN.factory.o; P.x=o.x+18.0; P.z=o.z+3.6; return 1; })()")
        await pg.wait_for_timeout(300)
        r = await act('工具棚を動かす')
        R2 = await lines()
        check(R2[:len(RIO2_NOSZ)] == RIO2_NOSZ and len(R2) == len(RIO2_NOSZ) + 2, f'工具棚を動かす → 地の文とリオの台詞（§10 のまま・スズキの台詞の代わりに地の文）{R2}')
        await until("P3A.interior.marks.some(k=>k.fix)")
        await E("(()=>{ const o=P3IN.factory.o; P.x=o.x+14.4; P.z=o.z+10.7; return 1; })()")
        await pg.wait_for_timeout(300)
        r = await act('コンプレッサー')
        check(await E("p3cState().rio.fixed") == 0, f'部品が足りないと直せない（{r}）')
        await E("(()=>{ const o=P3IN.factory.o; P.x=o.x+27.2; P.z=o.z+2.6; return 1; })()")
        await pg.wait_for_timeout(300)
        await act('部品庫の棚')
        await until("!P3A.interior.marks.some(k=>k.part===0)")
        await E("(()=>{ const o=P3IN.factory.o; P.x=o.x+25.5; P.z=o.z+9.8; return 1; })()")
        await pg.wait_for_timeout(300)
        await act('事務所の机')
        await until("!P3A.interior.marks.some(k=>k.part===1)")
        check(await E("p3cState().rio.parts.join('')") == '11', '部品を2つ見つける（部品庫の棚・事務所の机）')
        await E("(()=>{ const o=P3IN.factory.o; P.x=o.x+14.4; P.z=o.z+10.7; return 1; })()")
        await pg.wait_for_timeout(300)
        tod0 = await E("prog.f10.tod")
        await act('コンプレッサー')
        R3 = await lines()
        adv = (await E("prog.f10.tod") - tod0) % 1200
        check(len(R3) == 3 and R3[0].startswith('：リオと一緒に') and 24 <= adv <= 40, f'リオとコンプレッサーを直す（時間が約30分＝25秒進む：{round(adv,1)}秒）{R3}')
        await until("p3cState().rio.done===1", 6000)
        st = await E("[JSON.stringify(p3cState().rio), p3cResidents().join(',')]")
        check(st == ['{"met":1,"shelf":1,"talk":1,"parts":[1,1],"fixed":1,"done":1}', 'sumie,rio'], f'リオが住民になる（住民 2/2）{st}')

        # ---- 本部の中の住民 ----
        await E("(async()=>{ await p3aExit(); })()")
        await until("!P3A.inside&&!P3A.busy&&S.mode==='playing'")
        hq = await E("(()=>{ const d=P3A.doors.find(d=>d.id==='hq'); return [d.x,d.z]; })()")
        await go(hq[0], hq[1], 300)
        await act('拠点本部に入る')
        await until("P3A.inside&&P3A.inId==='hq'&&!P3A.busy&&S.mode==='playing'")
        await E("(prog.f10.tod=200,1)")
        await pg.wait_for_timeout(1200)
        pos = await E("(()=>{ p3cResVis(); const f=k=>[Math.round(P3CM[k].x-P3A_IN.x),Math.round(P3CM[k].z-P3A_IN.z),P3CM[k].m.g.visible]; return [f('sumie'),f('rio')]; })()")
        check(pos == [[6, 4, True], [18, 14, True]], f'昼：澄江は入口ホール・リオは作業場 {pos}')
        await E("(()=>{ P.x=P3CM.sumie.x+1.2; P.z=P3CM.sumie.z; return 1; })()")
        await pg.wait_for_timeout(400)
        r = await act('澄江と話す')
        T = await lines(3)
        check(r == '澄江と話す' and len(T) == 1 and T[0].startswith('澄江：'), f'澄江と話せる {T}')
        await E("(prog.f10.tod=700,1)")
        await pg.wait_for_timeout(1200)
        pos = await E("(()=>{ p3cResVis(); const f=k=>[Math.round(P3CM[k].x-P3A_IN.x),Math.round(P3CM[k].z-P3A_IN.z)]; return [f('sumie'),f('rio'),p3cDay()]; })()")
        check(pos == [[49, 9], [59, 9], False], f'夜：2階の共同住居の部屋 {pos}')
        await E("(prog.f10.tod=200,1)")
        await E("(async()=>{ await p3aExit(); })()")
        await until("!P3A.inside&&!P3A.busy&&S.mode==='playing'")
        vis = await E("[P3CM.sumie.m.g.visible, P3CM.rio.m.g.visible]")
        check(vis == [False, False], f'外に出ると、本部の中の住民は見えない {vis}')

        # ---- スズキ：上志比の拠点で過ごす ----
        await E("(SZ.x=P.x+1.5,SZ.z=P.z+1.5,szOrder('follow'),1)")
        await pg.wait_for_timeout(300)
        lab = await E("(()=>{ szTalk(); const w=document.getElementById('defenseChoice'); const t=w?w.textContent:''; if(w) w.remove(); S.mode='playing'; return t; })()")
        check('上志比の拠点で過ごせ' in lab, f'拠点設立のあと、スズキに「上志比の拠点で過ごせ」と言える（{lab[:60]}）')
        await E("szOrder('base')")
        await pg.wait_for_timeout(2500)
        sz = await E("(()=>{ const B=szKamiBase(); return [SZ.order, SZ.region, Math.round(dist(SZ.x,SZ.z,B.x,B.z))]; })()")
        check(sz[0] == 'base' and sz[1] == 'kamishihi', f'スズキは上志比の拠点で過ごす {sz}')

        # ---- 保存して、つづきから ----
        await E("saveGame()")
        await boot()
        await pg.click('#btnContinue')
        await pg.wait_for_timeout(1500)
        await until("REG.cur==='kamishihi'&&!REG.busy&&S.mode==='playing'", 60000)
        await pg.wait_for_timeout(1500)
        lp = await E("[REG.cur, JSON.stringify(p3cState().sumie), p3cState().rio.done, p3cResidents().join(','), SZ.order, SZ.region, P3C.pile&&P3C.pile.filter(m=>m.visible).length, P3C.pileCol&&P3C.pileCol.active]")
        check(lp == ['kamishihi', '{"met":1,"hits":3,"done":1}', 1, 'sumie,rio', 'base', 'kamishihi', 0, False], f'つづきから：住民・がれき・スズキ（上志比の拠点）が残る {lp}')

        # ---- 古いセーブ（p3c が無い）----
        await E("(()=>{ const d=JSON.parse(localStorage.getItem(SAVE_KEY)); delete d.p3c; localStorage.setItem(SAVE_KEY,JSON.stringify(d)); return 1; })()")
        await boot()
        await pg.click('#btnContinue')
        await pg.wait_for_timeout(1500)
        await until("!REG.busy&&S.mode==='playing'", 60000)
        old = await E("[p3cResidents().length, JSON.stringify(p3cState().rio)]")
        check(old == [0, '{"met":0,"shelf":0,"talk":0,"parts":[0,0],"fixed":0,"done":0}'], f'古いセーブ（p3c が無い）は、まだ誰もいない {old}')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: P3-C 住民と救助' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
