#!/usr/bin/env python3
"""v0.77 作業F を iPhone の操作（指でさわる）で確かめる。画面のない Chromium（iPhone の画面の大きさ・タッチ・横向き）。5分ほど。

 ・行動ボタン（調べる）で燃料を入れる → 会話は画面をタップして進む → KEI truck に乗った状態
 ・スティックを上へ倒すと前へ走る／右へ倒すと右へ曲がる（角度が減る）／下へ倒すと止まって下がる
 ・行動ボタンで降りる・もう一度乗る
 ・山王のカットの間は、スティック・行動ボタンが効かない（主人公は動かない）→ 戦いになると動ける
 ・初遭遇の会話もタップで進み、スズキが仲間になる
本物の iPhone（Safari）での確認ではない（画面のない Chromium のタッチの再現）。
環境変数：STORY_SHOTS=フォルダ（画面を撮る）、THREE_JS
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
HOOK = ("window.__s={get curInter(){return curInter},get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get SZ(){return SZ},get STF(){return STF},get TRUCK(){return TRUCK},get REG(){return REG},get joy(){return joy},"
        "get touchMode(){return touchMode},stfAnchor:()=>stfAnchor(),trk:()=>trk(),truckPos:()=>truckPos(),interactables:()=>interactables(),regionTravel,damageEnemy:(e,d,k,a)=>damageEnemy(e,d,k,a),"
        "szWalkable:(x,z)=>szWalkable(x,z),szFree:(x,z,r)=>szFree(x,z,r),chapter2State:(a,b)=>chapter2State(a,b),saveGame:()=>saveGame()};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
DLG = "() => document.getElementById('dialog').hidden ? null : document.getElementById('dlgText').textContent"


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg, flush=True)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        dev = dict(p.devices['iPhone 13 landscape'])
        dev['device_scale_factor'] = 1
        dev.pop('default_browser_type', None)
        ctx = await b.new_context(**dev)
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
        cdp = await ctx.new_cdp_session(pg)

        async def shot(name):
            if SHOTS:
                os.makedirs(SHOTS, exist_ok=True)
                try:
                    await pg.screenshot(path=os.path.join(SHOTS, name + '.png'), timeout=180000)
                except Exception as e:
                    print('  （画面を撮れなかった：', name, str(e)[:60], '）')

        async def ev(js, arg=None):
            return await (pg.evaluate(js, arg) if arg is not None else pg.evaluate(js))

        async def until(js, timeout=90):
            t0 = time.time()
            while time.time() - t0 < timeout:
                v = await ev(js)
                if v:
                    return v
                await pg.wait_for_timeout(300)
            return None

        async def center(sel):
            bb = await pg.locator(sel).bounding_box()
            return bb['x'] + bb['width'] / 2, bb['y'] + bb['height'] / 2

        async def tap(sel):
            x, y = await center(sel)
            await pg.touchscreen.tap(x, y)
            await pg.wait_for_timeout(350)

        async def act(part):
            """行動の帯が part を含むまで待ってから、行動ボタンをタップ"""
            t0, lab = time.time(), None
            while time.time() - t0 < 20:
                lab = await ev("(w) => { const i = window.__s.curInter; if (!i || i === window.__pi || !i.label.includes(w)) return null; window.__pi = i; return i.label; }", part)
                if lab:
                    break
                await pg.wait_for_timeout(250)
            await tap('#tbAct')
            return lab

        async def touch(kind, x, y, tid=1):
            pts = [] if kind == 'touchEnd' else [{'x': x, 'y': y, 'id': tid, 'radiusX': 4, 'radiusY': 4, 'force': 1}]
            await cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': pts})

        async def stick(dx, dy, ms, until_js=None, arg=None):
            """左の下の方を指で押して、(dx,dy) へずらしたまま ms ミリ秒（until_js があれば、それが真になるまで。最大 ms）。
            この環境はコマ送りが遅く、ゲームの時間が実時間より遅れるため"""
            bb = await pg.locator('#joyZone').bounding_box()
            x0, y0 = bb['x'] + bb['width'] * 0.35, bb['y'] + bb['height'] * 0.6
            await touch('touchStart', x0, y0)
            for k in range(1, 6):
                await touch('touchMove', x0 + dx * k / 5, y0 + dy * k / 5)
                await pg.wait_for_timeout(30)
            t0 = time.time()
            while (time.time() - t0) * 1000 < ms:
                await touch('touchMove', x0 + dx, y0 + dy)
                await pg.wait_for_timeout(120)
                if until_js and await ev(until_js, arg):
                    break
            j = await ev("() => ({x: window.__s.joy.x, y: window.__s.joy.y, id: window.__s.joy.id})")
            await touch('touchEnd', 0, 0)
            await pg.wait_for_timeout(200)
            return j

        async def read_taps(timeout=120, quiet=2.5):
            n, t0, idle = 0, time.time(), None
            while time.time() - t0 < timeout:
                if await ev(DLG):
                    n += 1
                    idle = None
                    await tap('#dialog')
                    continue
                busy = await ev("() => window.__s.STF.busy || window.__s.S.mode !== 'playing'")
                if busy:
                    idle = None
                elif idle is None:
                    idle = time.time()
                elif time.time() - idle > quiet:
                    break
                await pg.wait_for_timeout(250)
            return n

        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__s', timeout=300000)
        await tap('#btnNew')
        await pg.wait_for_timeout(800)
        while await ev(DLG):
            await tap('#dialog')
        await until("() => { const r = document.getElementById('joyZone').getBoundingClientRect(); return r.width > 0 && !document.getElementById('touch').hidden ? true : null; }", 30)
        tm = await ev("() => { const r = document.getElementById('joyZone').getBoundingClientRect(); return {t: window.__s.touchMode, cls: document.body.classList.contains('touchmode'), joy: r.width > 0 && !document.getElementById('touch').hidden}; }")
        check(tm['t'] and tm['cls'] and tm['joy'], f'タッチの操作になる（スティックが出る）{tm}')

        # KEI truck を直したところ（燃料はまだ）から
        await ev("""() => { const T = window.__s, prog = T.prog; prog.bossDefeated = true; prog.stage = 'cleared'; prog.introSeen = true; prog.chapter2 = T.chapter2State(null, true);
            Object.assign(prog.chapter2.progress, {openingStarted: true, defenseComplete: true, defenseRewarded: true, radioHeard: true, departureDecision: true, departureComplete: false});
            const t = T.trk(); Object.assign(t, {found: true, repaired: true, parts: ['p1', 'p2'], fuel: 1, fueled: false}); T.TRUCK.sync = false; }""")
        await pg.wait_for_timeout(600)
        await ev("() => { const T = window.__s, tp = T.truckPos(); T.P.x = tp.x - 2.6; T.P.z = tp.z + 0.3; }")
        await pg.wait_for_timeout(1200)
        await until("() => window.__s.curInter && window.__s.curInter.label.includes('燃料を入れる') ? true : null", 30)
        vis = await ev("() => !!document.getElementById('tbAct').offsetParent")
        check(vis, 'KEI truck のそばでは行動ボタンが見える')
        lab = await act('燃料を入れる')
        n = await read_taps()
        st = await ev("() => ({drive: window.__s.TRUCK.drive, done: window.__s.prog.chapter2.progress.departureComplete})")
        check(lab and '燃料' in lab and n == 7 and st['drive'] and st['done'], f'行動ボタン「{lab}」→ 見送りの会話（{n}行）をタップで進める → KEI truck に乗った {st}')
        await shot('t1_drive')

        a0 = await ev("() => [window.__s.TRUCK.x, window.__s.TRUCK.z, window.__s.TRUCK.a]")
        j = await stick(0, -60, 30000, "(a) => Math.hypot(window.__s.TRUCK.x - a[0], window.__s.TRUCK.z - a[1]) > 6", a0)
        a1 = await ev("() => [window.__s.TRUCK.x, window.__s.TRUCK.z, window.__s.TRUCK.a, window.__s.TRUCK.v]")
        mv = ((a1[0] - a0[0]) ** 2 + (a1[1] - a0[1]) ** 2) ** 0.5
        check(j['y'] < -0.8 and mv > 4, f'スティックを上へ倒すと前へ走る（{mv:.1f}m・スティック {j}）')
        j = await stick(55, -40, 20000, "(a) => window.__s.TRUCK.a < a - 0.35", a1[2])
        a2 = await ev("() => [window.__s.TRUCK.x, window.__s.TRUCK.z, window.__s.TRUCK.a]")
        check(j['x'] > 0.6 and a2[2] < a1[2] - 0.2, f'右へ倒すと右へ曲がる（向き {a1[2]:.2f} → {a2[2]:.2f}）')
        await shot('t2_turn')
        j = await stick(0, 60, 25000, "() => window.__s.TRUCK.v < -1")
        v = await ev("() => window.__s.TRUCK.v")
        check(v < 0, f'下へ倒すと止まって下がる（速さ {v:.1f}）')
        await pg.wait_for_timeout(1500)
        lab = await act('KEI truck を降りる')
        e1 = await ev("() => window.__s.TRUCK.drive")
        lab2 = await act('KEI truck に乗る')
        e2 = await ev("() => window.__s.TRUCK.drive")
        check(lab == 'KEI truck を降りる' and e1 is False and lab2 == 'KEI truck に乗る' and e2 is True, f'行動ボタンで降りる（{lab}）・乗る（{lab2}）')
        await act('KEI truck を降りる')

        # 山王：カットの間はさわっても動かない
        await ev("async () => { await window.__s.regionTravel('kamishihi', null, {force: true}); }")
        near = """(R) => { const T = window.__s, a = T.stfAnchor(), P = T.P, ar = T.REG.live.arrival, L = Math.hypot(ar.x - a.x, ar.z - a.z);
          for (const r of [R, R - 4, R + 4, R - 8]) for (let k = 0; k < 24; k++) { const ang = Math.atan2((ar.x - a.x) / L, (ar.z - a.z) / L) + (k % 2 ? 1 : -1) * Math.ceil(k / 2) * 0.12, x = a.x + Math.sin(ang) * r, z = a.z + Math.cos(ang) * r;
            if (T.szWalkable(x, z) && T.szFree(x, z, 0.6)) { P.x = x; P.z = z; return true; } } return false; }"""
        await ev(near, 52)
        await until("() => window.MUTANT_MONKEY_MODEL ? true : null", 120)
        await ev(near, 26)
        c = await until("() => window.__s.STF.cut ? true : null", 60)
        p0 = await ev("() => [window.__s.P.x, window.__s.P.z]")
        j = await stick(0, -60, 2500)
        await tap('#tbAct')
        p1 = await ev("() => [window.__s.P.x, window.__s.P.z, !!window.__s.STF.cut]")
        d = ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2) ** 0.5
        check(bool(c) and j['id'] is None and d < 0.05, f'カットの間はスティック・行動ボタンが効かない（動いた {d:.2f}m・スティック {j}）')
        await shot('t3_cut')
        f = await until("() => window.__s.STF.enc && window.__s.STF.enc.phase === 'fight' && !window.__s.STF.cut ? true : null", 90)
        p2 = await ev("() => [window.__s.P.x, window.__s.P.z]")
        await stick(0, -60, 20000, "(a) => Math.hypot(window.__s.P.x - a[0], window.__s.P.z - a[1]) > 1.5", p2)
        p3 = await ev("() => [window.__s.P.x, window.__s.P.z]")
        d = ((p3[0] - p2[0]) ** 2 + (p3[1] - p2[1]) ** 2) ** 0.5
        check(bool(f) and d > 1, f'戦いになるとスティックで動ける（{d:.1f}m）')
        await until("""() => { const T = window.__s, E = T.STF.enc; if (!E || E.phase !== 'fight') return true; const e = E.e; T.damageEnemy(e, 120, 'heavy', Math.atan2(e.x - T.P.x, e.z - T.P.z)); return null; }""", 60)
        await until(DLG, 40)
        n = await read_taps()
        jn = await ev("() => ({joined: window.__s.SZ.joined, met: window.__s.prog.chapter2.progress.mutantMet})")
        check(n == 10 and jn['joined'] and jn['met'] is True, f'初遭遇の会話（{n}行）をタップで進めると仲間になる {jn}')
        await shot('t4_joined')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: story F touch' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
