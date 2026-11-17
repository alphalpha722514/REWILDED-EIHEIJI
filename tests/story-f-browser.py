#!/usr/bin/env python3
"""v0.77 作業F（救援無線 → 相談 → KEI truck を直す → 見送り → 運転して上志比へ → 山王で初遭遇 → 仲間に）の確認。
画面のない Chromium・SwiftShader（15分ほど）。docs/p2-story-f.md（2026-11-17 ユーザー確定の5項目と KEI truck の修理ゲート）

 ① 防衛戦の勝利 → 報酬の表示が終わってから、救援無線が自動で1回（主人公は無線室の前・3人が集まる）→ 相談 → もう鳴らない
 ② 直す前は、歩いても初めて上志比へは行けない
 ③ 部品と燃料は光明寺で手に入る（上志比へ行かなくても）。素材が足りないと要る物を出す
 ④ 直す・燃料 → 直した報告と見送り → 乗った状態に。運転して東の出口へ → 上志比の西端に車ごと着く → 降りる・乗る → 運転して西の出口から光明寺へ
 ⑤ 旧セーブ（防衛戦は済み・作業F の記録なし）：歩いて上志比へ行ける権利が残る。無線は光明寺で1回
 ⑥ 山王に近づくと短いカット → 戦い（スズキは退いて見守る・サルは主人公と戦う）→ 傷230で逃げ去る（鱗1枚）
 ⑦ 初遭遇の途中で倒れる → 上志比の西端で起きる → 山王でカットからやり直す（スズキは仲間でない・記録も鱗もなし）
 ⑧ 仲間になる・初遭遇の記録は会話を終えたときに同時。そのあと二度と起きない。初遭遇の途中は保存しない（鱗の二重取りを防ぐ）
 ⑨ mutantMet で上志比の群れに変異したサルが加わる
 ⑩ セーブ→続きから：KEI truck（直した・燃料・地域・場所）と各段階が戻る
 ・台詞：すべて承認済み（2026-11-17）なので「草案（未承認）」の札は出ない
 ・初遭遇の途中で光明寺へ移ると、始まる前に戻す ・エラーなし
環境変数：STORY_SHOTS=フォルダ（場面の画面を撮る）、THREE_JS
"""
import asyncio
import os
import sys
import time

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('STORY_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
SHOTS = os.environ.get('STORY_SHOTS')
HOOK = ("window.__s={get curInter(){return curInter},get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get SZ(){return SZ},get STF(){return STF},get TRUCK(){return TRUCK},get enemies(){return enemies},"
        "get REG(){return REG},get ev(){return ev},get cam(){return cam},get npcs(){return [npcTome,npcGen,npcEshin]},get KOMYOJI_EAST(){return KOMYOJI_EAST},get KOMYOJI_EAST_ARRIVE(){return KOMYOJI_EAST_ARRIVE},get bannerT(){return bannerT},"
        "winEvent:()=>winEvent(),regionTravel,stfAnchor:()=>stfAnchor(),stfStage:()=>stfStage(),stfMeetStage:()=>stfMeetStage(),stfTravelOK:()=>stfTravelOK(),truckTravelOK:()=>truckTravelOK(),stfRoom:()=>stfRoom(),"
        "trk:()=>trk(),truckSpots:()=>truckSpots(),truckPos:()=>truckPos(),objective:()=>objective(),interactables:()=>interactables(),stfNoSave:()=>stfNoSave(),"
        "damageEnemy:(e,d,k,a)=>damageEnemy(e,d,k,a),saveGame:()=>saveGame(),retryFromBase:()=>retryFromBase(),kamiMutantOK:()=>kamiMutantOK(),szWalkable:(x,z)=>szWalkable(x,z),szFree:(x,z,r)=>szFree(x,z,r),szSave:()=>szSave(),"
        "get TRUCK_CFG(){return TRUCK_CFG},setCam:a=>setCam(a),setState:(e,s)=>setState(e,s),stfCutOn:()=>stfCutOn(),chapter2State:(a,b)=>chapter2State(a,b),f31MaxHp:l=>f31MaxHp(l),get XP(){return XP},get WEAPONS(){return WEAPONS}};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
DLG = "() => { const d = document.getElementById('dialog'); return d.hidden ? null : {name: document.getElementById('dlgName').textContent, text: document.getElementById('dlgText').textContent, draft: !document.getElementById('dlgTag').hidden}; }"
BASE = """(kind) => { const T = window.__s, prog = T.prog, P = T.P; prog.bossDefeated = true; prog.stage = 'cleared'; prog.unlockTrap = true; prog.unlockBoss = true; prog.introSeen = true;
  prog.chapter2 = T.chapter2State(null, true); prog.chapter2.progress.openingStarted = true;
  prog.level = 4; prog.exp = T.XP.lv[3] || 0; P.maxHp = T.f31MaxHp(4); P.hp = P.maxHp; P.weapon = 'spear'; P.dur = T.WEAPONS.spear.maxDur; prog.arms.spear = P.dur;
  if (kind === 'win') { T.ev.kind = 'chapter2'; T.ev.ended = false; T.winEvent(); } }"""
NEAR_SANNO = """(R) => { const T = window.__s, a = T.stfAnchor(), P = T.P, ar = T.REG.live.arrival, L = Math.hypot(ar.x - a.x, ar.z - a.z);
  for (const r of [R, R - 4, R + 4, R - 8]) for (let k = 0; k < 24; k++) { const ang = Math.atan2((ar.x - a.x) / L, (ar.z - a.z) / L) + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * 0.12, x = a.x + Math.sin(ang) * r, z = a.z + Math.cos(ang) * r;
    if (T.szWalkable(x, z) && T.szFree(x, z, 0.6)) { P.x = x; P.z = z; P.facing = Math.atan2(a.x - x, a.z - z); return true; } } return false; }"""
LEG = """() => { const k = Object.keys(localStorage).find(k => k === 'eiheiji_vs_beasts_v010'); const d = JSON.parse(localStorage.getItem(k)); const p = d.chapter2.progress;
  for (const x of ['radioHeard', 'departureDecision', 'departureComplete', 'mutantMet', 'truck', 'legacyKamishihiAccess']) delete p[x]; d.chapter2.currentRegion = 'komyoji'; d.suzuki = {v: 1, joined: false};
  localStorage.setItem(k, JSON.stringify(d)); return true; }"""


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg, flush=True)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport={'width': 960, 'height': 600})
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(r):
            u = r.request.url
            if 'three' in u and u.endswith('.js'): return await r.fulfill(body=THREE, content_type='application/javascript')
            if u.startswith('http://game.local'):
                path = u.split('http://game.local/', 1)[1].split('?')[0]
                if path in ('', 'index.html'): return await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
                fp = os.path.join(ROOT, path)
                if os.path.isfile(fp): return await r.fulfill(body=open(fp, 'rb').read())
                return await r.fulfill(status=404, body='')
            await r.abort()
        await ctx.route('**/*', route)

        async def shot(name):
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                try:
                    await pg.screenshot(path=os.path.join(SHOTS, name + '.png'), timeout=180000)
                except Exception as e:
                    print('  （画面を撮れなかった：', name, str(e)[:60], '）')

        async def ev(js, arg=None):
            return await (pg.evaluate(js, arg) if arg is not None else pg.evaluate(js))

        async def until(js, timeout=90, arg=None):
            t0 = time.time()
            while time.time() - t0 < timeout:
                v = await ev(js, arg)
                if v:
                    return v
                await pg.wait_for_timeout(300)
            return None

        async def read_all(quiet=3.0, timeout=120):
            """会話を最後まで読む（場面の暗転の間も待つ）。会話も場面も無い状態が quiet 秒続いたら終わり"""
            got, t0, idle = [], time.time(), None
            while time.time() - t0 < timeout:
                d = await ev(DLG)
                if d:
                    got.append(d)
                    idle = None
                    await pg.click('#dialog')
                    await pg.wait_for_timeout(240)
                    continue
                busy = await ev("() => window.__s.STF.busy || window.__s.S.mode !== 'playing'")
                if busy:
                    idle = None
                elif idle is None:
                    idle = time.time()
                elif time.time() - idle > quiet:
                    break
                await pg.wait_for_timeout(250)
            return got

        async def boot(cont=False, before=None):
            await pg.goto('http://game.local/', wait_until='load', timeout=300000)
            await pg.wait_for_function('window.__s', timeout=300000)
            if before:
                await ev(before)
            await pg.click('#btnContinue' if cont else '#btnNew', timeout=240000)
            await pg.wait_for_timeout(500)
            for _ in range(15):
                if await ev("document.getElementById('dialog').hidden"):
                    break
                await pg.click('#dialog')
                await pg.wait_for_timeout(200)

        async def press_e(label_part=None):
            """行動の帯（画面の表示＝curInter）が label_part を含むまで待ってから E。この環境はコマ送りが遅く、場所を飛ばした直後は前の帯のことがある。
            前に押したときと同じ帯（作り直されていない＝古い）では押さない"""
            js = "(w) => { const i = window.__s.curInter; if (!i || i === window.__pi || (w && !i.label.includes(w))) return null; window.__pi = i; return i.label; }"
            t0, lab = time.time(), None
            while time.time() - t0 < 20:
                lab = await ev(js, label_part or '')
                if lab:
                    break
                await pg.wait_for_timeout(250)
            if not lab:
                return await ev("() => { const i = window.__s.interactables(); return i && i.label; }")
            await pg.keyboard.press('e')
            await pg.wait_for_timeout(500)
            return lab

        # ================= 1) 防衛戦のあと → 救援無線 → 相談 =================
        await boot()
        npc0 = await ev("() => window.__s.npcs.map(n => [n.x, n.z])")
        r0 = await ev("() => window.__s.stfRoom()")
        await ev(BASE, 'win')
        st = await ev("() => { const T = window.__s, p = T.prog.chapter2.progress; return {r: p.radioHeard, d: p.departureDecision, c: p.departureComplete, stage: T.stfStage(), walk: T.stfTravelOK()}; }")
        check(st['r'] is False and st['d'] is False and st['c'] is False and st['stage'] == 'radio' and st['walk'] is False, f'防衛戦に勝つと作業F の記録が付き、上志比へはまだ行けない {st}')
        pre = await ev("() => { const I = window.__s.TRUCK.items || {}; return Object.fromEntries(['p1', 'p2', 'fuel'].map(k => [k, !!(I[k] && I[k].visible)])); }")
        check(not any(pre.values()), f'相談の前は、部品・燃料の形は出ない {pre}')
        win = await read_all(quiet=0.6, timeout=30)
        radio = await until(DLG, 300)
        bn = await ev("() => window.__s.bannerT")
        check(bool(radio) and radio['name'] == '無線' and not radio['draft'] and bn <= 0, f'勝利の会話（{len(win)}行）と報酬の表示のあと、救援無線が自動で鳴る（承認済みの台詞・札なし）{radio}')
        pos = await ev("() => { const T = window.__s, r = T.stfRoom(); return {d: Math.hypot(T.P.x - r.x, T.P.z - r.z), npc: T.npcs.map(n => +Math.hypot(n.x - r.x, n.z - r.z).toFixed(1)), cam: !!T.cam.override}; }")
        check(pos['d'] < 0.5 and all(d < 4 for d in pos['npc']) and pos['cam'], f'主人公は無線室の前・トミオ／源さん／慧心が集まる・場面のカメラ {pos}')
        await shot('1_radio')
        lines = await read_all()
        names = [d['name'] for d in lines]
        check(len(lines) == 3 + 12 and names[:3] == ['無線'] * 3 and '無線' not in names[3:] and not any(d['draft'] for d in lines) and '区長 トミオ' in names and '見張りの源さん' in names and '修行僧 慧心' in names,
              f'無線の3行と相談の12行（承認済み・札なし）{len(lines)}行')
        a1 = await ev("""() => { const T = window.__s, p = T.prog.chapter2.progress, r = T.stfRoom(); return {r: p.radioHeard, d: p.departureDecision, stage: T.stfStage(), obj: T.objective()[0],
            npc: T.npcs.map(n => +Math.hypot(n.x - r.x, n.z - r.z).toFixed(1)), home: T.npcs.map(n => n.home ? +Math.hypot(n.home.x - r.x, n.home.z - r.z).toFixed(1) : null), kept: !!T.STF.npc,
            cam: !!T.cam.override, fade: getComputedStyle(document.getElementById('stfFade')).opacity, walk: T.stfTravelOK()}; }""")
        n0 = [round(((x - r0['x']) ** 2 + (z - r0['z']) ** 2) ** 0.5, 1) for x, z in npc0]
        back = not a1['kept'] and all(d > 4 for d in a1['npc'])
        check(a1['r'] is True and a1['d'] is True and a1['stage'] == 'truck' and '軽トラック' in a1['obj'] and back and not a1['cam'] and a1['fade'] == '0' and a1['walk'] is False,
              f'相談のあと：記録・目標「{a1["obj"]}」・町民は元の場所へ（無線室から {a1["npc"]}m、前は {n0}m）・カメラと暗転は戻る・まだ歩いて行けない {dict((k, a1[k]) for k in ("cam", "fade", "walk", "home"))}')
        await pg.wait_for_timeout(6000)
        again = await ev(DLG)
        check(again is None, '無線は1回だけ（もう鳴らない）')

        # ================= 2) 直す前は上志比へ行けない =================
        gate = """async () => { const T = window.__s, A = T.KOMYOJI_EAST_ARRIVE, E = T.KOMYOJI_EAST, w = ms => new Promise(r => setTimeout(r, ms)); // コマ送りが遅いので長めに待つ
            T.P.x = A.x; T.P.z = A.z; await w(2500); T.P.x = E.x - 2; T.P.z = E.z;
            for (let i = 0; i < 40 && T.REG.cur === 'komyoji' && !T.REG.busy; i++) await w(300);
            for (let i = 0; i < 300 && T.REG.busy; i++) await w(300); return T.REG.cur; }"""
        cur = await ev(gate)
        check(cur == 'komyoji', f'KEI truck を直す前は、歩いて東の出口へ行っても上志比へ移らない（{cur}）')

        # ================= 3) KEI truck を見つける・部品・燃料・直す =================
        MATS = await ev("() => window.__s.TRUCK_CFG.mats")
        tp = await ev("() => window.__s.truckPos()")
        await ev("(tp) => { const T = window.__s; T.P.x = tp.x - 2.6; T.P.z = tp.z + 0.3; }", tp)
        await pg.wait_for_timeout(1200)
        lab = await press_e('軽トラックを調べる')
        found = await read_all(quiet=1.0, timeout=20)
        check(lab == '軽トラックを調べる' and len(found) == 2 and not found[0]['draft'] and found[1]['name'] == 'KEI truck' and '木材' in found[1]['text'], f'軽トラックを調べる → 発見の台詞と直すのに要る物 {[d["text"][:30] for d in found]}')
        await shot('2_truck_found')
        await ev("() => { const T = window.__s; for (const k in T.TRUCK_CFG.mats) T.inv[k] = 0; }")
        lab = await press_e('KEI truck を直す')
        info = await read_all(quiet=1.0, timeout=10)
        rp = await ev("() => window.__s.trk().repaired")
        check(rp is False and len(info) == 1 and all(f' 0/{v}' in info[0]['text'] for v in MATS.values()), f'素材・部品が足りないと直せず、要る物を出す {info and info[0]["text"]}')
        sp = await ev("() => window.__s.truckSpots()")
        vis = await ev("() => { const I = window.__s.TRUCK.items || {}; return Object.fromEntries(['p1', 'p2', 'fuel'].map(k => [k, !!(I[k] && I[k].visible)])); }")
        check(all(vis.values()), f'相談のあと、部品（木箱）2つと燃料（赤い携行缶）の仮の形が地面に見える {vis}')
        await ev("(q) => { const T = window.__s; T.P.x = q.x + 3.2; T.P.z = q.z + 3.0; T.P.facing = Math.atan2(q.x - T.P.x, q.z - T.P.z); T.setCam(T.P.facing); }", sp['parts'][0])
        await pg.wait_for_timeout(2500)
        await shot('2b_items')
        await pg.keyboard.press('g')  # 大きい地図：部品・燃料・KEI truck の印
        mo = await until("() => !document.getElementById('mapOv').hidden ? true : null", 30)
        await pg.wait_for_timeout(1500)
        await shot('2c_map')
        await pg.keyboard.press('g')
        mc = await until("() => document.getElementById('mapOv').hidden && window.__s.S.mode === 'playing' ? true : null", 30)
        check(bool(mo) and bool(mc) and not errs, f'地図を開いて閉じられる（部品・燃料・車の印を描いてもエラーなし）{errs[:2]}')
        for q in sp['parts']:
            await ev("(q) => { const T = window.__s; T.P.x = q.x + 0.7; T.P.z = q.z; }", q)
            await pg.wait_for_timeout(700)
            await press_e('部品を拾う')
        await ev("(q) => { const T = window.__s; T.P.x = q.x + 0.7; T.P.z = q.z; }", sp['fuel'])
        await pg.wait_for_timeout(700)
        await press_e('を受け取る')
        got = await ev("() => { const T = window.__s, t = T.trk(); return {parts: t.parts.length, fuel: t.fuel, reg: T.REG.cur}; }")
        check(got['parts'] == 2 and got['fuel'] == 1 and got['reg'] == 'komyoji', f'部品と燃料は光明寺で手に入る（上志比へ行かずに）{got}')
        await until("() => { const I = window.__s.TRUCK.items || {}; return Object.values(I).every(m => !m.visible) ? true : null; }", 20)  # 次のコマで消える
        hid = await ev("() => { const I = window.__s.TRUCK.items || {}; return Object.fromEntries(['p1', 'p2', 'fuel'].map(k => [k, !!(I[k] && I[k].visible)])); }")
        check(not any(hid.values()), f'拾うと木箱・携行缶の形は消える {hid}')
        await ev("(tp) => { const T = window.__s; for (const k in T.TRUCK_CFG.mats) T.inv[k] = T.TRUCK_CFG.mats[k]; T.P.x = tp.x - 2.6; T.P.z = tp.z + 0.3; }", tp)
        await pg.wait_for_timeout(800)
        await press_e('KEI truck を直す')
        r1 = await ev("() => { const T = window.__s; return {rep: T.trk().repaired, left: Object.keys(T.TRUCK_CFG.mats).map(k => T.inv[k]), fueled: T.trk().fueled}; }")
        check(r1['rep'] and not any(r1['left']) and not r1['fueled'], f'素材（暫定 {MATS}）と部品2で直す・素材が減る {r1}')
        await pg.wait_for_timeout(500)
        await press_e('燃料を入れる')
        await until(DLG, 30)
        await shot('3_sendoff')
        so = await read_all()
        sn = [d['name'] for d in so]
        dr = await ev("() => { const T = window.__s, p = T.prog.chapter2.progress; return {c: p.departureComplete, drive: T.TRUCK.drive, stage: T.stfStage(), obj: T.objective()[0], fueled: T.trk().fueled, ok: T.truckTravelOK(), walk: T.stfTravelOK()}; }")
        check(len(so) == 7 and not any(d['draft'] for d in so) and sn[0] == '主人公' and '区長 トミオ' in sn and '見張りの源さん' in sn, f'燃料を入れると、直した報告と見送り（7行）{sn}')
        check(dr['c'] is True and dr['drive'] and dr['fueled'] and dr['ok'] and dr['walk'] is False and '上志比へ向かおう' in dr['obj'], f'見送りのあと KEI truck に乗った状態・まだ歩いては行けない・目標「{dr["obj"]}」')

        # ================= 4) 運転して上志比へ・戻る =================
        x0 = await ev("() => [window.__s.TRUCK.x, window.__s.TRUCK.z]")
        await pg.keyboard.down('w')  # この環境はコマ送りが遅い（ゲームの時間が実時間より遅れる）ので、5m 進むまで（最大30秒）押し続ける
        t0 = time.time()
        while time.time() - t0 < 30:
            await pg.wait_for_timeout(500)
            if await ev("(a) => Math.hypot(window.__s.TRUCK.x - a[0], window.__s.TRUCK.z - a[1]) > 6", x0):
                break
        await pg.keyboard.up('w')
        await pg.wait_for_timeout(300)
        x1 = await ev("() => [window.__s.TRUCK.x, window.__s.TRUCK.z, window.__s.P.x, window.__s.P.z, window.__s.pm ? 1 : 0]")
        moved = ((x1[0] - x0[0]) ** 2 + (x1[1] - x0[1]) ** 2) ** 0.5
        check(moved > 5 and abs(x1[2] - x1[0]) < 0.01, f'W で前へ走る（{moved:.1f}m・主人公は車といっしょ）')
        await shot('4_driving')
        await ev("""() => { const T = window.__s, E = T.KOMYOJI_EAST; T.TRUCK.x = E.x - 26; T.TRUCK.z = E.z; T.TRUCK.a = Math.PI / 2; T.TRUCK.v = 0; T.P.x = T.TRUCK.x; T.P.z = T.TRUCK.z; }""")
        await pg.wait_for_timeout(1800)
        await ev("""() => { const T = window.__s, E = T.KOMYOJI_EAST; T.TRUCK.x = E.x - 3; T.P.x = T.TRUCK.x; }""")
        k1 = await until("() => window.__s.REG.cur === 'kamishihi' && !window.__s.REG.busy ? true : null", 120)
        await pg.wait_for_timeout(800)
        k2 = await ev("() => { const T = window.__s, t = T.trk(), ar = T.REG.live.arrival; return {reg: T.REG.cur, drive: T.TRUCK.drive, treg: t.region, trips: t.trips, d: Math.hypot(T.TRUCK.x - ar.x, T.TRUCK.z - ar.z), walk: T.stfTravelOK()}; }")
        check(bool(k1) and k2['drive'] and k2['treg'] == 'kamishihi' and k2['trips'] == 1 and k2['d'] < 3 and k2['walk'], f'修理した KEI truck で東の出口へ → 上志比の西端に車ごと着く（運転したまま）・以後は歩いても行ける {k2}')
        await shot('5_kami_arrive')
        await press_e('KEI truck を降りる')
        e1 = await ev("() => { const T = window.__s; return {drive: T.TRUCK.drive, d: Math.hypot(T.P.x - T.TRUCK.x, T.P.z - T.TRUCK.z), col: !!T.TRUCK.col, vis: T.TRUCK.m.visible}; }")
        check(not e1['drive'] and 1.5 < e1['d'] < 4 and e1['col'] and e1['vis'], f'降りる（車のそばへ・車は置いたまま・当たりあり）{e1}')
        await pg.wait_for_timeout(500)
        lab = await press_e('KEI truck に乗る')
        e2 = await ev("() => window.__s.TRUCK.drive")
        check(lab == 'KEI truck に乗る' and e2, f'もう一度乗る（{lab}）')
        back = await ev("""async () => { const T = window.__s, ex = T.REG.live.D ? T.REG.live.D.exitWest : window.KAMISHIHI_MAP.exitWest; T.TRUCK.x = ex.x + ex.r + 12; T.TRUCK.z = ex.z; T.P.x = T.TRUCK.x; T.P.z = T.TRUCK.z;
            await new Promise(r => setTimeout(r, 1800)); T.TRUCK.x = ex.x; T.TRUCK.z = ex.z; T.P.x = ex.x; T.P.z = ex.z; return true; }""")
        k3 = await until("() => window.__s.REG.cur === 'komyoji' && !window.__s.REG.busy ? true : null", 120)
        await pg.wait_for_timeout(800)
        k4 = await ev("() => { const T = window.__s, t = T.trk(), A = T.KOMYOJI_EAST_ARRIVE; return {drive: T.TRUCK.drive, treg: t.region, d: Math.hypot(T.TRUCK.x - A.x, T.TRUCK.z - A.z), trips: t.trips}; }")
        check(bool(k3) and k4['drive'] and k4['treg'] == 'komyoji' and k4['d'] < 3, f'運転したまま西の出口へ → 光明寺の東の端へ車ごと戻る {k4}')
        await press_e('KEI truck を降りる')

        # ================= 5) セーブ → 続きから（KEI truck と段階） =================
        await ev("() => window.__s.saveGame()")
        tsave = await ev("() => { const t = window.__s.trk(); return {x: t.x, z: t.z, region: t.region}; }")
        await boot(cont=True)
        await pg.wait_for_timeout(2500)
        l1 = await ev("() => { const T = window.__s, t = T.trk(); return {rep: t.repaired, fu: t.fueled, reg: t.region, x: t.x, z: t.z, trips: t.trips, stage: T.stfStage(), meet: T.stfMeetStage(), dlg: !document.getElementById('dialog').hidden, vis: !!(T.TRUCK.m && T.TRUCK.m.visible)}; }")
        check(l1['rep'] and l1['fu'] and l1['reg'] == tsave['region'] and abs(l1['x'] - tsave['x']) < 0.1 and l1['trips'] == 1 and l1['stage'] == 'away' and l1['meet'] == 'meet' and not l1['dlg'] and l1['vis'],
              f'続きから：KEI truck（直した・燃料・地域・場所）と段階が戻る・会話は起きない {l1}')

        # ================= 6) 山王で初遭遇 → 逃げ去る → 仲間に =================
        await ev("async () => { await window.__s.regionTravel('kamishihi', null, {force: true}); }")
        # スズキの掛け声（吹き出し）を記録する：文が入るたびに、そのときの状態といっしょに
        await ev("""() => { window.__cries = []; new MutationObserver(ms => { for (const m of ms) { const t = m.target; if (!t.classList || !t.classList.contains('bark') || !t.textContent.includes('Reddish')) continue;
            const T = window.__s; window.__cries.push({joined: T.SZ.joined, enc: !!T.STF.enc, text: t.textContent}); } }).observe(document.body, {subtree: true, childList: true}); return true; }""")
        await ev(NEAR_SANNO, 52)
        await until("() => window.MUTANT_MONKEY_MODEL ? true : null", 120)
        await ev(NEAR_SANNO, 26)
        cut = await until("() => { const T = window.__s; return T.STF.enc && T.STF.cut ? {matte: document.body.classList.contains('cinema52')} : null; }", 60)
        check(bool(cut) and cut['matte'], '山王に近づくと短いカット（黒い帯・操作を止める）')
        await pg.wait_for_timeout(1500)
        await shot('6_cut')
        held = await ev("() => { const T = window.__s, a = T.stfAnchor(); return T.enemies.filter(e => !e.removed && e.state !== 'dead' && !e.stfF && !e.stfHold && Math.hypot(e.x - a.x, e.z - a.z) < 60).length; }")
        check(held == 0, f'山王のまわりのほかの獣は遠ざけて止める（近くに動ける獣 {held}）')
        f1 = await until("() => { const T = window.__s, E = T.STF.enc; return E && E.phase === 'fight' && !T.STF.cut ? {sz: T.STF.sz && T.STF.sz.mode, cam: !!T.cam.override} : null; }", 90)
        check(bool(f1) and f1['sz'] == 'watch' and not f1['cam'], f'カットのあと戦い（スズキは退いて見守る）{f1}')
        await pg.wait_for_timeout(4000)
        w = await ev("() => { const T = window.__s, e = T.STF.enc.e; return {tgt: e.tgt, dP: +Math.hypot(T.SZ.x - T.P.x, T.SZ.z - T.P.z).toFixed(1), dE: +Math.hypot(T.SZ.x - e.x, T.SZ.z - e.z).toFixed(1), joined: T.SZ.joined, nosave: T.stfNoSave()}; }")
        check(w['tgt'] is None and w['dP'] > 6 and not w['joined'], f'サルは主人公と戦い、スズキは離れている（主人公から {w["dP"]}m・サルから {w["dE"]}m）')
        s0 = await ev("() => localStorage.getItem('eiheiji_vs_beasts_v010')")
        await ev("() => { window.__s.inv.wood += 7; window.__s.saveGame(); }")
        s1 = await ev("() => localStorage.getItem('eiheiji_vs_beasts_v010')")
        check(w['nosave'] and s0 == s1, '初遭遇の途中は保存しない')
        cry0 = await ev("() => window.__cries.length")
        check(cry0 == 0, f'初遭遇のカットと戦いでは、スズキは「Reddish…」と言わない（{cry0}回）')
        await shot('7_fight')
        fl = await until("""() => { const T = window.__s, E = T.STF.enc; if (!E) return 'gone'; if (E.phase !== 'fight') return {phase: E.phase, drop: !!E.e.scaleDropped, met: T.prog.chapter2.progress.mutantMet};
            const e = E.e, P = T.P; T.damageEnemy(e, 120, 'heavy', Math.atan2(e.x - P.x, e.z - P.z)); return null; }""", 60)
        check(isinstance(fl, dict) and fl['drop'] and fl['met'] is not True, f'傷を負わせると逃げ去り、鱗を1枚落とす（記録はまだ）{fl}')
        talk = await until(DLG, 40)
        await shot('8_talk')
        lines = await read_all(quiet=2.0)
        L3 = [(d['name'], d['text'], d['draft']) for d in lines[:3]]
        want = [('スズキ', 'ありが、、、、、、　マンゴスチーーン！！', False), ('主人公', '色々聞きたいことはあるけど、、、とりあえず名前は？あと、こんなところで何してたんだ？', False),
                ('スズキ', 'おれはスズキ！探してる人がいるんだ。だから俺はここに残ったってかんじかな。', False)]
        check(L3 == want, f'スズキの初登場の確定の3行 {L3}')
        check(len(lines) == 10 and not any(d['draft'] for d in lines[3:]), f'そのあとの7行（承認済み・札なし）{len(lines) - 3}行')
        j = await ev("""() => { const T = window.__s, p = T.prog.chapter2.progress, sv = JSON.parse(localStorage.getItem('eiheiji_vs_beasts_v010'));
            return {joined: T.SZ.joined, order: T.SZ.order, met: p.mutantMet, enc: !!T.STF.enc, held: T.enemies.filter(e => e.stfHold).length, meet: T.stfMeetStage(), ok: T.kamiMutantOK(),
              saved: {met: sv.chapter2.progress.mutantMet, joined: sv.suzuki.joined}, obj: T.objective()[0]}; }""")
        check(j['joined'] and j['order'] == 'follow' and j['met'] is True and not j['enc'] and j['held'] == 0 and j['meet'] == 'done' and j['ok'] and j['saved'] == {'met': True, 'joined': True},
              f'会話を終えると仲間（ついて来る）と初遭遇の記録が同時に付いて保存・止めた獣は動き出す・群れに変異したサル {j}')
        await pg.wait_for_timeout(5000)
        again = await ev("() => ({enc: !!window.__s.STF.enc, dlg: !document.getElementById('dialog').hidden})")
        check(not again['enc'] and not again['dlg'], '山王にいても、初遭遇は二度と起きない')
        # 仲間になったあと：まわりの獣と戦い始めたら言う。20秒たっても戦いが始まらなければ、近くに獣を置く
        cry = await until("() => { const c = window.__cries.filter(c => c.joined && !c.enc); return c.length ? c[0] : null; }", 20)
        how = '止めた獣が動き出して戦いになった'
        if not cry:
            how = '近くに獣を置いた'
            await ev("""() => { const T = window.__s; let e = null;
                for (const o of T.enemies) { if (o.removed || o.state === 'dead' || o.type === 'boss' || o.stfF) continue; if (!e || Math.hypot(o.x - T.SZ.x, o.z - T.SZ.z) < Math.hypot(e.x - T.SZ.x, e.z - T.SZ.z)) e = o; }
                if (!e) return false; e.x = T.SZ.x + 5; e.z = T.SZ.z + 2; e.home = {x: e.x, z: e.z}; e.hp = e.maxHp; T.SZ.fight = false; T.SZ.calmT = 0; T.setState(e, 'chase'); return true; }""")
            cry = await until("() => { const c = window.__cries.filter(c => c.joined && !c.enc); return c.length ? c[0] : null; }", 40)
        n = await ev("() => window.__cries.length")
        check(isinstance(cry, dict) and cry['text'] == 'Reddishにしてやろうかああぁぁあ！？' and n == 1, f'仲間になったあと、戦いが始まるとスズキが「Reddishにしてやろうかああぁぁあ！？」と言う（{how}・{n}回）{cry}')
        await shot('9_joined')

        # ================= 7) 旧セーブ：移動権を残す・無線は1回 =================
        await ev(LEG)
        await boot(cont=True)
        g1 = await ev("() => { const T = window.__s, p = T.prog.chapter2.progress; return {r: p.radioHeard, leg: p.legacyKamishihiAccess, stage: T.stfStage(), walk: T.stfTravelOK(), meet: T.stfMeetStage()}; }")
        check(g1['r'] is False and g1['leg'] is True and g1['stage'] == 'radio' and g1['walk'] and g1['meet'] == 'meet', f'旧セーブ：上志比へ歩いて行ける権利を残し、光明寺で無線を待つ・山王で初遭遇できる {g1}')
        rd = await until(DLG, 90)
        check(bool(rd) and rd['name'] == '無線', '旧セーブでも光明寺で無線が1回鳴る')
        await read_all()
        cur = await ev(gate)
        check(cur == 'kamishihi', f'旧セーブは KEI truck を直していなくても歩いて上志比へ行ける（{cur}）')

        # ================= 8) 初遭遇の途中で倒れる → 西端 → カットからやり直す =================
        await ev(NEAR_SANNO, 52)
        await until("() => window.MUTANT_MONKEY_MODEL ? true : null", 120)
        await ev(NEAR_SANNO, 26)
        c2 = await until("() => window.__s.STF.enc && window.__s.STF.enc.phase === 'fight' ? true : null", 120)
        check(bool(c2), '（旧セーブ）山王で初遭遇が始まる')
        await ev("() => { const T = window.__s; T.P.hp = 0; T.P.dead = true; T.S.mode = 'dead'; T.retryFromBase(); }")
        await pg.wait_for_timeout(800)
        d1 = await ev("""() => { const T = window.__s, p = T.prog.chapter2.progress, ar = T.REG.live.respawn || T.REG.live.arrival;
            return {reg: T.REG.cur, west: +Math.hypot(T.P.x - ar.x, T.P.z - ar.z).toFixed(1), enc: !!T.STF.enc, mut: T.enemies.filter(e => e.stfF && !e.removed).length, held: T.enemies.filter(e => e.stfHold).length,
              met: p.mutantMet, joined: T.SZ.joined, vis: !!(T.SZ.m && T.SZ.m.g.visible)}; }""")
        check(d1['reg'] == 'kamishihi' and d1['west'] < 3 and not d1['enc'] and d1['mut'] == 0 and d1['held'] == 0 and d1['met'] is not True and not d1['joined'] and not d1['vis'],
              f'途中で倒れると上志比の西端で起き、始まる前に戻る（サルは消え、記録も仲間もなし）{d1}')
        await ev("() => { window.__s.P.hp = window.__s.P.maxHp; }")
        await ev(NEAR_SANNO, 26)
        c3 = await until("() => window.__s.STF.cut ? true : null", 120)
        check(bool(c3), 'もう一度山王へ行くと、カットからやり直す')
        await until("() => window.__s.STF.enc && window.__s.STF.enc.phase === 'fight' ? true : null", 60)

        # ================= 9) 初遭遇の途中で光明寺へ移る =================
        await ev("async () => { await window.__s.regionTravel('komyoji', null, {force: true}); }")
        await pg.wait_for_timeout(600)
        t4 = await ev("() => { const T = window.__s; return {enc: !!T.STF.enc, sz: !!T.STF.sz, cut: !!T.STF.cut, matte: document.body.classList.contains('cinema52'), cam: !!T.cam.override, reg: T.REG.cur, meet: T.stfMeetStage(), nosave: T.stfNoSave()}; }")
        check(not t4['enc'] and not t4['sz'] and not t4['cut'] and not t4['matte'] and not t4['cam'] and t4['reg'] == 'komyoji' and t4['meet'] == 'meet' and not t4['nosave'], f'初遭遇の途中で光明寺へ移ると、始まる前に戻す {t4}')

        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: story F' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
