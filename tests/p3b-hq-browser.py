#!/usr/bin/env python3
"""v0.81（P3-B）上志比の拠点本部の確認（画面のない Chromium。数分）。

- スズキが仲間になる前は、本部のシャッターが開かない
- 仲間になった後：目的が本部を指す・初めて近づくと前庭にサルが2体出る（1回だけ）
- 入る（スズキも一緒）→ 3か所を調べる → 拠点設立の会話（指示書 §3.3 の台詞そのまま、10行）→「上志比復興計画を開始」
- スズキがいないときは会話を始めない（呼んでくると始まる）
- 倉庫の修理：素材が足りないと直せない・棚の金具を見つける・3か所直す・1か所ごとにゲーム内の時間が40分進む
- 倉庫の棚に預ける → 作業場の修理で倉庫の素材も使える
- 前庭の軽トラを解体（槌で6回）→ 古い機械部品・屑鉄
- 作業場の修理 → 総合作業場でクラフトの画面が開く
- 持ち物の重さ：拠点の外で素材60を超えると遅くなる・拠点本部の中と光明寺の境内では遅くならない
- 光明寺の資材置き場（丸太置き場）に預けられる
- 時刻：1日を均等に24時間（tod 0＝6:00、50秒で1時間）
- 保存して「つづきから」：拠点本部・置き場の状態が残る。古いセーブ（p3・stash のキーがない）も読める
- エラーなし
使い方：THREE_JS=…/three.min.js python3 tests/p3b-hq-browser.py
"""
import asyncio
import json
import os
import re
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
HTML = SRC.replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){', 1)
# 指示書 v1.1 §3.3 の正式採用台詞（そのまま比べる）
TALK = ['うわ、広っ！ ここなら雨の日でも走り回れるな。', '走るための建物じゃないぞ。', 'そっか。でも、屋根も壁もあるし、案外まだ使えそうじゃね？',
        '主人公は棚に残された工具や、奥へ続く階段を見渡す。', '……ここなら倉庫も作業場も作れる。上の階を直せば、住む場所にもなる。', 'ってことは、上志比の新しい基地ってことか！',
        'まだ何もできてない。でも、ここを直せば、戻ってきた人たちが暮らせる場所になる。', 'いいじゃん！ じゃあ、何から始める？', 'まずは倉庫と作業場だ。使えそうなものを探そう。',
        'おっしゃ！ ……で、掃除ってどこからやればいいんだ？']
BASE = """(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; return 1; })()"""
# 近くの「調べる」を探して実行する
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

        async def wait_playing(ms=8000):
            for _ in range(ms // 100):
                if await E("S.mode==='playing'&&!P3A.busy"):
                    return True
                await pg.wait_for_timeout(100)
            return False

        async def go(x, z):
            await E(f"(P.x={x},P.z={z},1)")
            await pg.wait_for_timeout(300)

        await boot()
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await E(BASE)

        # ---- 時刻 ----
        clk = await E("[p3bClockText(0),p3bClockText(100),p3bClockText(550),p3bClockText(1199),p3bClockText(780)]")
        check(clk == ['6:00', '8:00', '17:00', '5:58', '21:36'], f'時刻：1日を均等に24時間（tod 0＝6:00・50秒で1時間）{clk}')
        for _ in range(100):  # 画面のない Chromium は最初の数コマが遅い。時計が進むまで待つ
            if not await E("$('hudClock').hidden"):
                break
            await pg.wait_for_timeout(200)
        hc = await E("[$('hudClock').hidden,$('hudClock').textContent]")
        check(hc[0] is False and re.match(r'^\d+:\d\d$', hc[1]) is not None, f'画面に時刻が出る {hc}')

        # ---- 上志比へ。スズキが仲間になる前 ----
        await E("(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()")
        await pg.wait_for_timeout(1500)
        await E("(()=>{ for(const e of enemies) if(!e.removed&&dist(e.x,e.z,6366,815)<220) e.x+=900; return 1; })()")
        door = await E("(()=>{ const d=P3A.doors.find(d=>d.id==='hq'); return [d.x,d.z]; })()")
        await go(door[0], door[1])
        r = await act('シャッター')
        check('重くて開かない' in r and not await E("P3A.inside"), f'スズキが仲間になる前は、シャッターが開かない（{r}）')
        check(await E("p3bState().hq.beasts") == 0, '仲間になる前は、前庭のサルも出ない')

        # ---- 仲間になった後：目的・前庭のサル ----
        await go(door[0] + 120, door[1])
        await E("(stfP().mutantMet=true, szJoin(), 1)")
        await pg.wait_for_timeout(400)
        obj = await E("(()=>{ const o=objective(); return [o[0], !!o[1]]; })()")
        check('大きな建物' in obj[0] and obj[1], f'仲間になった後、目的が本部を指す {obj}')
        n0 = await E("enemies.filter(e=>!e.removed&&e.type==='monkey'&&dist(e.x,e.z,6366,815)<70).length")
        await go(door[0] + 40, door[1])
        for _ in range(100):
            if await E("p3bState().hq.beasts"):
                break
            await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(300)
        n1 = await E("enemies.filter(e=>!e.removed&&e.type==='monkey'&&dist(e.x,e.z,6366,815)<70).length")
        check(n1 - n0 == 2 and await E("p3bState().hq.beasts") == 1, f'初めて本部に近づくと、前庭にサルが2体出る（{n0}→{n1}）')
        await E("(()=>{ for(const e of enemies) if(!e.removed&&dist(e.x,e.z,6366,815)<220) e.x+=900; return 1; })()")

        # ---- 入る（スズキも）→ 3か所 → 会話 ----
        await go(door[0], door[1])
        r = await act('大きな建物に入る')
        await wait_playing()
        await pg.wait_for_timeout(600)
        st = await E("[P3A.inside, p3bSzInside(), Math.round(dist(SZ.x,SZ.z,P.x,P.z))]")
        check(st[0] and st[1], f'入るとスズキも一緒に入る {st}')
        # スズキを外に置いたまま3か所を調べる → 会話は始まらない
        await E("(()=>{ SZ.x=P3A.ret.x+3; SZ.z=P3A.ret.z; szOrder('wait'); return 1; })()")
        for i in range(3):
            await E(f"(()=>{{ const m=P3A.interior.marks.find(k=>k.sv==={i}); P.x=m.x; P.z=m.z; return 1; }})()")
            await pg.wait_for_timeout(250)
            r = await act('調べる')
            await pg.wait_for_timeout(300)
        sv = await E("[p3bState().hq.sv.join(''), p3bState().hq.talk, $('dialog').hidden]")
        check(sv[0] == '111' and sv[1] == 0 and sv[2], f'3か所を調べても、スズキがいないと会話は始まらない {sv}')
        await E("(()=>{ szOrder('follow'); SZ.x=P.x+2; SZ.z=P.z; return 1; })()")
        texts = []
        for _ in range(120):
            await pg.wait_for_timeout(150)
            if not await pg.evaluate("document.getElementById('dialog').hidden"):
                break
        for _ in range(14):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            texts.append(await pg.evaluate("[document.getElementById('dlgName').textContent, document.getElementById('dlgText').textContent]"))
            await pg.click('#dialog')
            await pg.wait_for_timeout(260)
        check([t[1] for t in texts] == TALK, f'拠点設立の会話：指示書 §3.3 の台詞そのまま10行 {len(texts)}行')
        check([t[0] for t in texts] == ['スズキ', '主人公', 'スズキ', '', '主人公', 'スズキ', '主人公', 'スズキ', '主人公', 'スズキ'], f'話す人の名前（地の文は名前なし） {[t[0] for t in texts]}')
        await pg.wait_for_timeout(300)
        bn = await E("[$('banner').textContent, p3bState().hq.plan]")
        check('上志比復興計画を開始' in bn[0] and bn[1] == 1, f'会話のあと「上志比復興計画を開始」{bn}')

        # ---- 倉庫の修理 ----
        await wait_playing()
        await E("(()=>{ for(const k of P3B.carry.mats) inv[k]=0; return 1; })()")
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.rep&&k.rep[0]==='storage'&&k.rep[1]===0); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        r = await act('倉庫：倒れた')
        await pg.wait_for_timeout(300)
        check(await E("p3bState().rep.storage[0]") == 0, '素材が足りないと直せない')
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.find==='shelfKit'); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        r = await act('奥の箱')
        await pg.wait_for_timeout(300)
        check(await E("inv.shelfKit") == 1, f'倉庫の奥の箱で「棚の金具」を見つける（{r}）')
        await E("(inv.wood=12,inv.stone=6,inv.iron=4,inv.rope=4,1)")
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.rep&&k.rep[0]==='storage'&&k.rep[1]===0); P.x=m.x; P.z=m.z; return 1; })()")
        lb = await E("(()=>{ const L=[]; p3aInteractables(L); const o=L.find(o=>/倒れた/.test(o.label)); return o?o.label:''; })()")
        check('木材6/6・屑鉄2/2・棚の金具1/1' in lb, f'直す所の表示は、近づいたときの持ち物で数え直す（{lb}）')
        tod0 = await E("prog.f10.tod")
        for i in range(3):
            await wait_playing()
            await E(f"(()=>{{ const m=P3A.interior.marks.find(k=>k.rep&&k.rep[0]==='storage'&&k.rep[1]==={i}); P.x=m.x; P.z=m.z; return 1; }})()")
            await pg.wait_for_timeout(250)
            await act('倉庫：')
            await wait_playing()
        rs = await E("[p3bState().rep.storage.join(''), inv.wood, inv.stone, inv.iron, inv.rope, inv.shelfKit]")
        tod1 = await E("prog.f10.tod")
        adv = (tod1 - tod0) % 1200
        check(rs == ['111', 0, 0, 0, 0, 0], f'倉庫を3か所直す（素材と棚の金具を使い切る）{rs}')
        check(95 <= adv <= 130, f'倉庫の修理で時間が約2時間（100秒）進む（{round(adv,1)}秒。修理中の分を含む）')

        # ---- 倉庫に預ける → 作業場の修理に使える ----
        await E("(inv.iron=6,inv.wood=16,inv.stone=8,inv.rope=4,1)")
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.stash); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        await E("stashPut('kami',P3B.carry.mats)")
        sk = await E("[JSON.stringify(prog.stash.kami), carryN()]")
        check(sk[1] == 0 and json.loads(sk[0]) == {'wood': 16, 'stone': 8, 'iron': 6, 'rope': 4}, f'倉庫の棚に預ける {sk}')
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.find==='gen'); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        await act('発電機')
        await pg.wait_for_timeout(300)
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.find==='toolSet'); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        await act('工具箱')
        await pg.wait_for_timeout(300)
        got = await E("[inv.oldParts, inv.toolSet]")
        check(got == [2, 1], f'発電機から古い機械部品2・工具箱で作業場の工具一式 {got}')
        # 古い機械部品が1つ足りない → 前庭の軽トラを解体
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.rep&&k.rep[0]==='workshop'&&k.rep[1]===1); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        await act('旋盤')
        await pg.wait_for_timeout(300)
        check(await E("p3bState().rep.workshop[1]") == 0, '古い機械部品が足りない（2/3）と旋盤と溶接機は直せない')
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.exit); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        await act('外へ出る')
        await wait_playing()
        tk = await E("[P3A.yardTruck.x, P3A.yardTruck.z]")
        await go(tk[0] + 1.6, tk[1])
        r = await act('解体')
        check('none' not in r and await E("p3bState().got.yardHits") == 0, f'道具がないと解体できない（{r}）')
        await E("(prog.f5.tools.hammerStone=40, 1)")
        for _ in range(6):
            await act('解体')
            await pg.wait_for_timeout(120)
        yt = await E("[p3bState().got.yardTruck, inv.oldParts, inv.iron, P3A.yardTruck.mesh.visible, P3A.yardTruck.pile.visible]")
        check(yt == [1, 4, 3, False, True], f'前庭の軽トラを槌で6回たたいて解体：古い機械部品+2・屑鉄+3、鉄くずの山になる {yt}')
        await go(door[0], door[1])
        await act('拠点本部に入る')
        await wait_playing()
        await pg.wait_for_timeout(400)
        for i in range(3):
            await wait_playing()
            await E(f"(()=>{{ const m=P3A.interior.marks.find(k=>k.rep&&k.rep[0]==='workshop'&&k.rep[1]==={i}); P.x=m.x; P.z=m.z; return 1; }})()")
            await pg.wait_for_timeout(250)
            await act('総合作業場：')
            await wait_playing()
        ws = await E("[p3bState().rep.workshop.join(''), JSON.stringify(prog.stash.kami), inv.oldParts, inv.toolSet, inv.iron]")
        check(ws[0] == '111' and json.loads(ws[1]) == {'iron': 3} and ws[2] == 1 and ws[3] == 0 and ws[4] == 0, f'作業場を3か所直す（手持ちの屑鉄3を先に使い、残りは倉庫から）{ws}')
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.craft); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        await act('総合作業場を使う')
        await pg.wait_for_timeout(500)
        cr = await E("[$('craft').hidden, $('craftTitle').textContent, CRAFT.at]")
        check(cr[0] is False and '総合作業場' in cr[1], f'総合作業場でクラフトの画面が開く {cr}')
        await E("(closeOverlay&&closeOverlay(), $('craft').hidden=true, S.mode='playing', 1)")

        # ---- 持ち物の重さ ----
        await E("(inv.wood=80,1)")  # 古い機械部品の残り1と合わせて81
        m_in = await E("carrySpeedMul()")
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.exit); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        await act('外へ出る')
        await wait_playing()
        m_out = await E("carrySpeedMul()")
        check(m_in == 1 and abs(m_out - 0.6) < 1e-9, f'素材80：拠点本部の中では遅くならない・外では0.6倍 {m_in} {m_out}')
        rr = await E("[$('rCarryRow').hidden, $('rCarry').textContent, $('rCarryRow').classList.contains('heavy')]")
        check(rr == [False, '81/60', True], f'画面に素材の重さ（超えると色が変わる）{rr}')

        # ---- 保存して、つづきから ----
        await E("saveGame()")
        await boot()
        await pg.click('#btnContinue')
        await pg.wait_for_timeout(1500)
        for _ in range(300):
            if await E("REG.cur==='kamishihi'&&!REG.busy&&S.mode==='playing'"):
                break
            await pg.wait_for_timeout(200)
        lp = await E("[REG.cur, p3bState().hq.plan, p3bState().rep.storage.join(''), p3bState().rep.workshop.join(''), p3bState().got.yardTruck, P3A.yardTruck&&P3A.yardTruck.pile.visible, inv.wood]")
        check(lp == ['kamishihi', 1, '111', '111', 1, True, 80], f'つづきから：拠点本部の進み具合と解体した軽トラが残る {lp}')
        await E("(()=>{ for(const e of enemies) if(!e.removed&&dist(e.x,e.z,6366,815)<220) e.x+=900; return 1; })()")
        door = await E("(()=>{ const d=P3A.doors.find(d=>d.id==='hq'); return [d.x,d.z]; })()")
        await go(door[0], door[1])
        await act('拠点本部に入る')
        await wait_playing()
        mk = await E("P3A.interior.marks.map(k=>k.id).sort().join(',')")
        check(mk == 'craft,down,exit,stair,stash', f'もう一度入ると、倉庫の棚と総合作業場が使える（直す所・調べる所は出ない）{mk}')
        await E("(()=>{ const m=P3A.interior.marks.find(k=>k.exit); P.x=m.x; P.z=m.z; return 1; })()")
        await pg.wait_for_timeout(250)
        await act('外へ出る')
        await wait_playing()

        # ---- 光明寺の資材置き場 ----
        await E("(async()=>{ await regionTravel('komyoji',null,{force:true}); })()")
        await pg.wait_for_timeout(1500)
        await E("(P.x=F4.yard.x+1.5, P.z=F4.yard.z, 1)")
        await pg.wait_for_timeout(300)
        lab = await E("(()=>{ const L=[]; f4Interactables(L); const o=L.find(o=>/資材置き場/.test(o.label)); return o?o.label:''; })()")
        check('資材置き場' in lab, f'光明寺の丸太置き場に資材置き場がある（{lab}）')
        check(await E("carrySpeedMul()") == 1, '光明寺の境内では重さで遅くならない')
        await E("stashPut('komyoji',['wood'])")
        ks = await E("[prog.stash.komyoji.wood, inv.wood]")
        check(ks == [80, 0], f'光明寺の資材置き場に預ける {ks}')
        # 光明寺の境内では、作るときに置き場の素材も使える
        aff = await E("[bedHaveAll('wood'), bedAfford({wood:50})]")
        check(aff == [80, True], f'光明寺の境内では、作るときに資材置き場の素材も数える {aff}')
        await E("bedPay({wood:5})")
        check(await E("prog.stash.komyoji.wood") == 75, '払うと資材置き場から減る')
        await E("saveGame()")

        # ---- 古いセーブ（p3・stash のキーがない）----
        await E("(()=>{ const d=JSON.parse(localStorage.getItem(SAVE_KEY)); delete d.p3; delete d.stash; delete d.inv.oldParts; localStorage.setItem(SAVE_KEY,JSON.stringify(d)); return 1; })()")
        await boot()
        await pg.click('#btnContinue')
        await pg.wait_for_timeout(2500)
        for _ in range(300):
            if await E("!REG.busy&&S.mode==='playing'"):
                break
            await pg.wait_for_timeout(200)
        old = await E("[JSON.stringify(p3bState().hq), JSON.stringify(prog.stash), inv.oldParts]")
        check(json.loads(old[0])['plan'] == 0 and json.loads(old[1]) == {'v': 1, 'komyoji': {}, 'kami': {}} and old[2] == 0, f'古いセーブ：拠点本部はまだ・置き場は空・古い機械部品0 {old}')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: P3-B 拠点本部' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
