#!/usr/bin/env python3
"""KEI truck の正式モデル（Tripo の GLB、2026-11-17 ユーザー採用）の確認。画面のない Chromium・SwiftShader（数分）。docs/kei-truck-glb.md

 ① 発見の場所に修理前の形（kei_truck_broken.glb）を置く。コードの仮の形は隠れる。車輪は4つ・地面に着く・大きさ（全長 約3.75m）
 ② 部品を集め始めたら（相談のあと）修理後の形を先に読んでおく
 ③ 直す（行動ボタン）→ 修理後の形（kei_truck_repaired.glb）に切り替わる・フロントガラスがある・修理前の形は外す・素材は1回だけ引く
    もう一度 truckRepair() を呼んでも素材は減らない
 ④ 燃料 → 見送り → 乗った状態。運転すると車輪が回り、前の車輪はハンドルの向きに切れる・進む
 ⑤ セーブ → 続きから：修理後の形のまま（修理前の形は読まない・未修理へ戻らない）
 ⑥ GLB を読めないとき：コードの仮の形のまま遊べる（エラーなし）
 ・描画の回数・三角形・GPU の目安（この環境は画面のない Chromium の CPU 描画。実機の値ではない）
環境変数：KT_SHOTS=フォルダ（修理前・修理後・運転中の画面を撮る）、THREE_JS
"""
import asyncio
import os
import sys
import time

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
SHOTS = os.environ.get('KT_SHOTS')
HOOK = ("window.__s={get curInter(){return curInter},get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get STF(){return STF},get TRUCK(){return TRUCK},get TRUCK_VIS(){return TRUCK_VIS},"
        "get REG(){return REG},get cam(){return cam},get renderer(){return renderer},get TRUCK_CFG(){return TRUCK_CFG},groundH:(x,z)=>groundH(x,z),interactables:()=>interactables(),"
        "trk:()=>trk(),truckPos:()=>truckPos(),truckRepair:()=>truckRepair(),truckFuel:()=>truckFuel(),saveGame:()=>saveGame(),chapter2State:(a,b)=>chapter2State(a,b),f31MaxHp:l=>f31MaxHp(l),get XP(){return XP},get WEAPONS(){return WEAPONS}};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
DLG = "() => { const d = document.getElementById('dialog'); return d.hidden ? null : {name: document.getElementById('dlgName').textContent, text: document.getElementById('dlgText').textContent}; }"
# 防衛戦は済み・救援無線の相談も済み（部品を集める段階）
BASE = """() => { const T = window.__s, prog = T.prog, P = T.P; prog.bossDefeated = true; prog.stage = 'cleared'; prog.unlockTrap = true; prog.unlockBoss = true; prog.introSeen = true;
  prog.chapter2 = T.chapter2State(null, true); const p = prog.chapter2.progress; p.openingStarted = true; p.defenseComplete = true; p.defenseRewarded = true; prog.chapter2.currentChapter = 2; p.radioHeard = true; p.departureDecision = true; p.departureComplete = false;
  prog.level = 4; prog.exp = T.XP.lv[3] || 0; P.maxHp = T.f31MaxHp(4); P.hp = P.maxHp; P.weapon = 'spear'; P.dur = T.WEAPONS.spear.maxDur; prog.arms.spear = P.dur; }"""
# 車の中の座標 → 世界の座標（+x が左・+z が前）
LOC = "(T, lx, lz) => { const a = T.TRUCK.a, sa = Math.sin(a), ca = Math.cos(a); return [T.TRUCK.x + lx * ca + lz * sa, T.TRUCK.z - lx * sa + lz * ca]; }"
INFO = """() => { const T = window.__s, TR = T.TRUCK, V = T.TRUCK_VIS, kind = TR.visKind, cur = V[kind]; const B = new THREE.Box3(), wv = new THREE.Vector3();
  let glass = null, tris = 0, meshes = 0;
  if (cur && cur.g && TR.m) { const inv = new THREE.Matrix4().copy(TR.m.matrixWorld).invert(); cur.g.traverse(o => { if (!o.isMesh) return; meshes++; const g = o.geometry; tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
      if (o.name === 'windshield' || (o.parent && o.parent.name === 'windshield')) glass = {vis: o.visible && cur.g.visible, tr: !!o.material.transparent, op: o.material.opacity};
      if (!g.boundingBox) g.computeBoundingBox(); const bb = g.boundingBox.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld)); B.union(bb); }); } // 車の中の座標で
  const wheels = (TR.wheels || []).map((w, i) => { w.getWorldPosition(wv); return {y: wv.y - TR.hub[i], g: T.groundH(wv.x, wv.z), rx: w.rotation.x, ry: w.rotation.y, name: w.name}; });
  return {kind, code: !!TR.code && TR.code.visible, root: !!TR.m && TR.m.visible, vis: Object.fromEntries(Object.entries(V).map(([k, v]) => [k, v.st + (v.g && v.g.visible ? ':見える' : '')])), glass, tris, meshes, wr: TR.wr,
    size: cur ? [B.max.x - B.min.x, B.max.y - B.min.y, B.max.z - B.min.z].map(v => +v.toFixed(2)) : null, wheels, rep: T.trk().repaired, x: TR.x, z: TR.z, drive: TR.drive}; }"""
# 描画の回数・三角形（KEI truck を見せたとき − 隠したとき）と GPU の目安（読んだ形の絵と頂点の大きさ）
PERF = """async () => { const T = window.__s, R = T.renderer, fr = n => new Promise(r => { let k = 0; const f = () => (++k >= n ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); });
  const kids = T.TRUCK.m.children.slice(), was = kids.map(o => o.visible), hide = h => kids.forEach((o, i) => { o.visible = h ? false : was[i]; }); // 毎コマ truckUpdate が root を見せるので、中の形を隠す
  const read = async () => { await fr(3); const i = R.info.render; return {calls: i.calls, tris: i.triangles}; };
  const ms = async () => { const t0 = performance.now(); let n = 0; await new Promise(r => { const f = () => { n++; if (performance.now() - t0 > 2500) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); }); return (performance.now() - t0) / n; };
  const on = await read(); hide(true); const off = await read(); const tOff = await ms(); hide(false); const tOn = await ms();
  let tex = 0, geo = 0; const seen = new Set(); for (const k in T.TRUCK_VIS) { const g = T.TRUCK_VIS[k].g; if (!g) continue; g.traverse(o => { if (!o.isMesh) return;
      for (const a of Object.values(o.geometry.attributes)) geo += a.array.byteLength; if (o.geometry.index) geo += o.geometry.index.array.byteLength;
      const m = o.material.map; if (m && !seen.has(m)) { seen.add(m); tex += m.image.width * m.image.height * 4 * 4 / 3; } }); }
  return {calls: on.calls - off.calls, tris: on.tris - off.tris, texMB: +(tex / 1048576).toFixed(1), geoMB: +(geo / 1048576).toFixed(2), msOff: +tOff.toFixed(1), msOn: +tOn.toFixed(1),
    gpuGeo: R.info.memory.geometries, gpuTex: R.info.memory.textures, heapMB: performance.memory ? +(performance.memory.usedJSHeapSize / 1048576).toFixed(0) : null}; }"""


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg, flush=True)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--enable-precise-memory-info'])

        async def open_game(noglb=False):
            ctx = await b.new_context(viewport={'width': 960, 'height': 600})
            pg = await ctx.new_page()
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))

            async def route(r):
                u = r.request.url
                if 'three.min.js' in u or 'three.js/r128' in u: return await r.fulfill(body=THREE, content_type='application/javascript')
                if u.startswith('http://game.local'):
                    path = u.split('http://game.local/', 1)[1].split('?')[0]
                    if path in ('', 'index.html'): return await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
                    if noglb and 'kei-truck' in path: return await r.fulfill(status=404, body='')
                    fp = os.path.join(ROOT, path)
                    if os.path.isfile(fp): return await r.fulfill(body=open(fp, 'rb').read())
                    return await r.fulfill(status=404, body='')
                await r.abort()
            await ctx.route('**/*', route)
            return ctx, pg, errs

        ctx, pg, errs = await open_game()

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

        async def shot(name, view=None):
            """view：[横, 高さ, 前後, 見る横, 見る高さ, 見る前後]（車の中の座標）。カメラを置いて撮る"""
            if not SHOTS:
                return
            os.makedirs(SHOTS, exist_ok=True)
            if view:
                await ev("""([v, LOC]) => { const T = window.__s, L = eval(LOC), [x, z] = L(T, v[0], v[2]), [lx, lz] = L(T, v[3], v[5]), g = T.groundH(T.TRUCK.x, T.TRUCK.z);
                    T.cam.override = {p: new THREE.Vector3(x, g + v[1], z), l: new THREE.Vector3(lx, g + v[4], lz), fov: 42}; }""", [view, LOC])
                await pg.wait_for_timeout(1500)
            try:
                await pg.screenshot(path=os.path.join(SHOTS, name + '.png'), timeout=180000)
            except Exception as e:
                print('  （画面を撮れなかった：', name, str(e)[:60], '）')
            if view:
                await ev("() => { window.__s.cam.override = null; }")

        async def boot(cont=False):
            await pg.goto('http://game.local/', wait_until='load', timeout=300000)
            await pg.wait_for_function('window.__s', timeout=300000)
            await pg.click('#btnContinue' if cont else '#btnNew', timeout=240000)
            await pg.wait_for_timeout(500)
            for _ in range(15):
                if await ev("document.getElementById('dialog').hidden"):
                    break
                await pg.click('#dialog')
                await pg.wait_for_timeout(200)

        async def read_all(quiet=3.0, timeout=120):
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

        async def press_e(label_part):
            js = "(w) => { const i = window.__s.curInter; if (!i || i === window.__pi || !i.label.includes(w)) return null; window.__pi = i; return i.label; }"
            t0, lab = time.time(), None
            while time.time() - t0 < 25:
                lab = await ev(js, label_part)
                if lab:
                    break
                await pg.wait_for_timeout(250)
            if not lab:
                return await ev("() => { const i = window.__s.interactables(); return i && i.label; }")
            await pg.keyboard.press('e')
            await pg.wait_for_timeout(500)
            return lab

        def ground_ok(info, tol=0.06):
            return all(abs(w['y'] - w['g']) < tol for w in info['wheels'])

        # ================= ① 修理前の形 =================
        await boot()
        await ev(BASE)
        tp = await ev("() => window.__s.truckPos()")
        await ev("(tp) => { const T = window.__s, a = T.TRUCK.a; T.P.x = tp.x + Math.cos(a) * 2.9; T.P.z = tp.z - Math.sin(a) * 2.9; }", tp)  # 運転席の側（右）に立つ
        got = await until("() => { const T = window.__s; return T.TRUCK.m && T.TRUCK.visKind === 'broken' && T.TRUCK.m.visible; }", 120)
        await pg.wait_for_timeout(1500)
        i1 = await ev(INFO)
        print('  ', {k: i1[k] for k in ('kind', 'vis', 'size', 'tris', 'meshes', 'wr')})
        check(bool(got) and i1['kind'] == 'broken' and not i1['code'] and i1['root'], f'発見の場所に修理前の形（GLB）が出る・コードの仮の形は隠れる {i1["vis"]}')
        check([w['name'] for w in i1['wheels']] == ['wheel_fr', 'wheel_fl', 'wheel_rr', 'wheel_rl'] and i1['glass'] is None, f'車輪は4つの別の形（右前・左前・右後ろ・左後ろ）・修理前に足したガラスは無い（元のひびのガラスのまま）')
        check(ground_ok(i1), f'4つの車輪が地面に着く（車輪の下 − 地面：{[round(w["y"] - w["g"], 3) for w in i1["wheels"]]}m）')
        sz = i1['size']
        check(sz and 1.95 < sz[0] < 2.25 and 2.3 < sz[1] < 2.65 and 4.0 < sz[2] < 4.25, f'大きさ 幅×高さ×長さ {sz}m（全長 約4.1m）')
        pre = await ev("() => { const V = window.__s.TRUCK_VIS.repaired; return V ? V.st : null; }")
        check(pre in ('load', 'ok'), f'部品を集める段階では、修理後の形を先に読んでおく（{pre}）')
        lab = await press_e('軽トラックを調べる')
        found = await read_all(quiet=1.0, timeout=30)
        check(lab == '軽トラックを調べる' and len(found) >= 1, f'運転席の側（右・車の中心から 2.9m）から調べられる（{lab}）')
        await shot('kt_1_broken_front', [-2.85, 1.85, 6.15, 0, 1.0, 0])
        await shot('kt_2_broken_side', [-6.8, 1.75, 0.65, 0, 1.0, 0])
        await shot('kt_3_broken_rear', [3.75, 2.1, -5.95, 0, 1.0, -0.35])
        pf = await ev(PERF)
        print('   修理前の重さ（画面のない Chromium の CPU 描画。実機の値ではない）', pf)
        check(pf['calls'] <= 12, f'KEI truck の描画の回数 {pf["calls"]}（影を含む。車体＋車輪4つ）・三角形 {pf["tris"]}')

        # ================= ③ 直す → 修理後の形 =================
        await ev("() => window.__s.cam.override = null")
        mats = await ev("() => window.__s.TRUCK_CFG.mats")
        await ev("() => { const T = window.__s, t = T.trk(), m = T.TRUCK_CFG.mats; for (const k in m) T.inv[k] = m[k] + 5; t.parts = ['p1', 'p2']; t.fuel = 0; }")
        inv0 = await ev("() => Object.fromEntries(Object.keys(window.__s.TRUCK_CFG.mats).map(k => [k, window.__s.inv[k]]))")
        await until("() => window.__s.TRUCK_VIS.repaired && window.__s.TRUCK_VIS.repaired.st === 'ok'", 120)
        lab = await press_e('KEI truck を直す')
        sw = await until("() => window.__s.TRUCK.visKind === 'repaired'", 60)
        await pg.wait_for_timeout(1500)
        i2 = await ev(INFO)
        inv1 = await ev("() => Object.fromEntries(Object.keys(window.__s.TRUCK_CFG.mats).map(k => [k, window.__s.inv[k]]))")
        print('  ', {k: i2[k] for k in ('kind', 'vis', 'size', 'tris', 'meshes', 'glass')})
        check(bool(sw) and i2['rep'] is True and i2['kind'] == 'repaired' and not i2['code'] and 'broken' not in i2['vis'], f'直す（{lab}）→ 修理後の形に切り替わる・修理前の形は外す {i2["vis"]}')
        check(bool(i2['glass']) and i2['glass']['vis'] and i2['glass']['tr'] and 0.2 < i2['glass']['op'] < 0.5, f'修理後はフロントガラスがある（半透明 {i2["glass"]}）')
        check(all(inv0[k] - inv1[k] == mats[k] for k in mats), f'素材は1回だけ引く {inv0} → {inv1}')
        check(ground_ok(i2), f'修理後も4つの車輪が地面に着く {[round(w["y"] - w["g"], 3) for w in i2["wheels"]]}')
        await ev("() => window.__s.truckRepair()")
        inv2 = await ev("() => Object.fromEntries(Object.keys(window.__s.TRUCK_CFG.mats).map(k => [k, window.__s.inv[k]]))")
        check(inv2 == inv1, 'もう一度「直す」を呼んでも素材は減らない（二重に引かない）')
        await shot('kt_4_repaired_front', [-2.85, 1.85, 6.15, 0, 1.0, 0])
        await shot('kt_5_repaired_side', [-6.8, 1.75, 0.65, 0, 1.0, 0])
        await shot('kt_6_repaired_rear', [3.75, 2.1, -5.95, 0, 1.0, -0.35])
        await shot('kt_7_repaired_glass', [-1.1, 1.9, 3.95, 0, 1.6, 0.65])
        pf2 = await ev(PERF)
        print('   修理後の重さ（実機の値ではない）', pf2)
        check(pf2['texMB'] < 6.5, f'直したあと GPU に残る KEI truck の絵は1枚（約{pf2["texMB"]}MB・頂点 {pf2["geoMB"]}MB）')

        # ================= ④ 燃料 → 見送り → 運転 =================
        await ev("() => { window.__s.trk().fuel = window.__s.TRUCK_CFG.fuel; }")
        lab = await press_e('燃料を入れる')
        if SHOTS and await until(DLG, 90):
            await pg.wait_for_timeout(800)
            await shot('kt_9_sendoff')
        await read_all(quiet=2.0, timeout=150)
        dr = await until("() => window.__s.TRUCK.drive", 60)
        check(bool(dr), f'燃料（{lab}）→ 見送り → 乗った状態')
        a0 = await ev(INFO)
        await pg.keyboard.down('w')
        await until("([x, z]) => Math.hypot(window.__s.TRUCK.x - x, window.__s.TRUCK.z - z) > 3", 60, [a0['x'], a0['z']])
        await pg.keyboard.down('d')
        await until("() => window.__s.TRUCK.steer < -0.15", 30)
        await pg.wait_for_timeout(300)
        a1 = await ev(INFO)
        await shot('kt_8_driving')
        await pg.keyboard.up('d')
        await pg.keyboard.up('w')
        moved = ((a1['x'] - a0['x']) ** 2 + (a1['z'] - a0['z']) ** 2) ** 0.5
        spun = all(abs(w1['rx'] - w0['rx']) > 0.5 for w0, w1 in zip(a0['wheels'], a1['wheels']))
        steer = a1['wheels'][0]['ry'] < -0.05 and a1['wheels'][1]['ry'] < -0.05 and a1['wheels'][2]['ry'] == 0
        check(moved > 3 and spun and steer, f'運転すると進み（{moved:.1f}m）、4つの車輪が回り、前の車輪だけ右へ切れる（{[round(w["ry"], 2) for w in a1["wheels"]]}）')
        await until("() => Math.hypot(window.__s.TRUCK.vx, window.__s.TRUCK.vz) < 0.2", 60)
        await pg.wait_for_timeout(800)
        a2 = await ev(INFO)
        check(ground_ok(a2, 0.08), f'止まると車輪は地面に着いている（でこぼこ込み）{[round(w["y"] - w["g"], 3) for w in a2["wheels"]]}')
        await press_e('降りる')
        await until("() => !window.__s.TRUCK.drive", 30)
        await ev("() => window.__s.saveGame()")

        # ================= ⑤ 続きから =================
        await boot(cont=True)
        got = await until("() => window.__s.TRUCK.m && window.__s.TRUCK.visKind === 'repaired' && window.__s.TRUCK.m.visible", 120)
        i5 = await ev(INFO)
        check(bool(got) and i5['rep'] is True and 'broken' not in i5['vis'] and bool(i5['glass']), f'続きから：修理後の形のまま・修理前の形は読まない {i5["vis"]}')
        check(ground_ok(i5), f'続きから：車輪が地面に着く {[round(w["y"] - w["g"], 3) for w in i5["wheels"]]}')
        check(not errs, f'エラーなし {errs[:3]}')
        await ctx.close()

        # ================= ⑥ GLB を読めないとき =================
        ctx, pg, errs = await open_game(noglb=True)
        await boot()
        await ev(BASE)
        tp = await ev("() => window.__s.truckPos()")
        await ev("(tp) => { const T = window.__s; T.P.x = tp.x + 3; T.P.z = tp.z; }", tp)
        f = await until("() => { const V = window.__s.TRUCK_VIS.broken; return V && V.st === 'fail' && window.__s.TRUCK.m && window.__s.TRUCK.m.visible; }", 120)
        i6 = await ev(INFO)
        check(bool(f) and i6['kind'] == 'code' and i6['code'], f'GLB を読めないとき：コードの仮の形のまま {i6["vis"]}')
        lab = await press_e('軽トラックを調べる')
        check(lab == '軽トラックを調べる' and not errs, f'仮の形でも調べられる・エラーなし {errs[:2]}')
        await ctx.close()
        await b.close()
    print('PASS: KEI truck の正式モデル' if ok else 'FAIL', flush=True)
    sys.exit(0 if ok else 1)

asyncio.run(main())
