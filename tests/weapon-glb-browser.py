#!/usr/bin/env python3
"""v0.75 武器の GLB（見た目だけの差し替え）の確認。画面のない Chromium・SwiftShader（数分）。docs/p2-weapon-glb.md

- 新しく始めると、持っている鉈（nata1）の GLB だけを読む（持っていない武器は読まない）。鞘も読む
- 鉈を Lv2・Lv3 に鍛える／木の棍棒・鉄の斧・牙槍・蒼鱗・変異鱗の武器・飛去来器を作る（作業台の craft）と、手の武器が GLB の形になる
- 当たりの点（weaponWorld）・武器の数値（WEAPONS）は、GLB でもコードの形でも同じ
- 攻撃（通常・強）は GLB の武器で出て、獣に当たる
- 飛去来器：投げる→飛ぶ姿が GLB の形→戻って手に戻る（2回）
- セーブ→読み直し→続きから：持ち物・手の武器・GLB の形が戻る。保存のキーと形式は変わらない
- 上志比へ移っても、手の武器は GLB のまま
- アイコンは GLB を読んだあと描き直される
- GLB を読めないとき（WGT_NOGLB=1 で .glb を 404 に）：コードの形のまま、エラーなしで攻撃できる
- エラーなし

使い方：THREE_JS=…/three.min.js python3 tests/weapon-glb-browser.py   （WGT_NOGLB=1 でフォールバックの確認）
"""
import asyncio
import json
import mimetypes
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('WGT_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
NOGLB = bool(os.environ.get('WGT_NOGLB'))
HOOK = ("window.__w={get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get WG(){return WG},get WGLB(){return WGLB},get WEAPONS(){return WEAPONS},get enemies(){return enemies},get F11(){return F11},"
        "get weaponMesh(){return weaponMesh},get BOOM(){return BOOM},get HOL(){return HOL},get ICONS(){return ICONS},get REG(){return REG},"
        "craft:i=>craft(i),equipArm:i=>equipArm(i),updatePlayer:dt=>updatePlayer(dt),boomerUpdate:dt=>boomerUpdate(dt),startAttack:k=>startAttack(k),weaponWorld:()=>weaponWorld().map(v=>v.toArray()),"
        "iconOf:i=>iconOf(i),saveGame:()=>saveGame(),regionTravel,makeWeaponCode:i=>makeWeaponCode(i),f47WeaponScale:i=>f47WeaponScale(i),setState:(e,s)=>setState(e,s),updHolster:()=>updHolster()};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
WAIT = """async (fs) => { const W = window.__w; for (let i = 0; i < 400; i++) { if (fs.every(f => W.WG.files[f] && W.WG.files[f].st !== 'load')) break; await new Promise(r => setTimeout(r, 50)); }
  return Object.fromEntries(Object.entries(W.WG.files).map(([k, v]) => [k, v.st])); }"""
STEP = """async ([n, dt]) => { const W = window.__w; for (let i = 0; i < n; i++) { W.S.time += dt; W.updatePlayer(dt); W.boomerUpdate(dt); if (i % 60 === 0) await new Promise(r => setTimeout(r, 0)); } }"""


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport={'width': 960, 'height': 600})
        pg = await ctx.new_page()
        errs, glbReq = [], []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(r):
            u = r.request.url
            if 'three.min.js' in u or 'three.js/r128' in u: return await r.fulfill(body=THREE, content_type='application/javascript')
            if u.startswith('http://game.local'):
                path = u.split('http://game.local/', 1)[1].split('?')[0]
                if path in ('', 'index.html'): return await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
                if path.endswith('.glb'):
                    glbReq.append(path)
                    if NOGLB: return await r.fulfill(status=404, body='')
                fp = os.path.join(ROOT, path)
                if os.path.isfile(fp): return await r.fulfill(body=open(fp, 'rb').read(), content_type=mimetypes.guess_type(fp)[0] or 'application/octet-stream')
                return await r.fulfill(status=404, body='')
            await r.abort()
        await ctx.route('**/*', route)

        async def boot(cont=False):
            await pg.goto('http://game.local/', wait_until='load', timeout=300000)
            await pg.wait_for_function('window.__w', timeout=300000)
            await pg.click('#btnContinue' if cont else '#btnNew')
            await pg.wait_for_timeout(500)
            for _ in range(15):
                if await pg.evaluate("document.getElementById('dialog').hidden"):
                    break
                await pg.click('#dialog')
                await pg.wait_for_timeout(200)
            await pg.evaluate("() => { const W = window.__w; W.F11.hold = true; W.S.mode = 'paused'; }")

        await boot()
        st = await pg.evaluate(WAIT, ['normalNata', 'sheath'])
        want = 'fail' if NOGLB else 'ok'
        check(st.get('normalNata') == want and st.get('sheath') == want and len(st) == 2, f'始めは鉈と鞘だけを読む {st} 要求 {sorted(set(glbReq))}')
        r = await pg.evaluate("() => ({w: window.__w.P.weapon, g: window.__w.weaponMesh.userData.wglb || null})")
        check(r['w'] == 'nata1' and r['g'] == (None if NOGLB else 'nata1'), f'手の鉈は {"コードの形（読めないとき）" if NOGLB else "GLB の形"} {r}')
        wj0 = await pg.evaluate("() => JSON.stringify(window.__w.WEAPONS)")

        # ---- 作業台で作る・鍛える ----
        res = await pg.evaluate("""async () => { const W = window.__w, I = W.inv; for (const k of ['wood','hide','stone','rope','iron','bamboo','fang','procScale','mutScale','straw']) I[k] = 999; W.prog.unlockBoss = true; W.prog.conv = {built: true};
          const out = {}; for (const id of ['nata2', 'nata3', 'club', 'axeStone', 'axeIron', 'spear', 'scNata', 'scAxe', 'scClub', 'scSpear', 'boomer']) { W.craft(id); out[id] = W.prog.arms[id] != null; }
          return {made: out, arms: Object.keys(W.prog.arms)}; }""")
        check(all(res['made'].values()), f'作業台で作れる・鍛えられる {res}')
        # 変異鱗の武器は蒼鱗と同じ元の武器から作るので、別の流れで確かめる
        res2 = await pg.evaluate("""async () => { const W = window.__w; const out = {}; for (const [base, id] of [['nata3','rwNata'],['axeIron','rwAxe'],['club','rwClub'],['spear','rwSpear']]) { W.prog.arms[base] = W.WEAPONS[base].maxDur; W.craft(id); out[id] = W.prog.arms[id] != null; } return out; }""")
        check(all(res2.values()), f'変異鱗の武器も作れる {res2}')
        own = await pg.evaluate("() => { const W = window.__w; return [...new Set(Object.keys(W.prog.arms).filter(k => W.WGLB[k]).map(k => W.WGLB[k].f))]; }")
        st = await pg.evaluate(WAIT, own + ['sheath'])
        check(all(st.get(f) == want for f in own), f'持っている武器の GLB を読む（{want}）持っている形 {sorted(own)} → {st}')
        ids = ['nata3', 'club', 'axeIron', 'spear', 'scNata', 'scAxe', 'scClub', 'scSpear', 'rwNata', 'rwAxe', 'rwClub', 'rwSpear', 'boomer']
        rows = await pg.evaluate("""async (ids) => { const W = window.__w, out = {}; for (const id of ids) { W.prog.arms[id] = W.prog.arms[id] ?? W.WEAPONS[id].maxDur; W.equipArm(id); const f = W.WGLB[id].f; for (let i = 0; i < 200 && W.WG.files[f] && W.WG.files[f].st === 'load'; i++) await new Promise(r => setTimeout(r, 50)); await new Promise(r => setTimeout(r, 0));
            const m = W.weaponMesh; let tris = 0; m.traverse(o => { if (o.isMesh) tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3; });
            out[id] = {g: m.userData.wglb || null, vis: m.visible, tris, sc: +m.scale.x.toFixed(3), want: +W.f47WeaponScale(id).toFixed(3)}; } return out; }""", ids)
        bad = {k: v for k, v in rows.items() if v['g'] != (None if NOGLB else k) or not v['vis'] or v['sc'] != v['want']}
        check(not bad, f'13本とも、手に持つと {"コードの形" if NOGLB else "GLB の形"}・大きさは今と同じ {bad or "（すべて）"}')

        # ---- 腰の鉈：通常・蒼鱗・変異の鉈とも、同じ GLB の鞘（2026-11-16 ユーザー）。読めないときは箱 ----
        hs = await pg.evaluate("""async () => { const W = window.__w, out = {}; W.equipArm('club'); const keep = {...W.prog.arms};
            for (const id of ['nata1', 'scNata', 'rwNata']) { for (const k of ['nata1', 'nata2', 'nata3', 'scNata', 'rwNata']) delete W.prog.arms[k]; W.prog.arms[id] = W.WEAPONS[id].maxDur; W.updHolster();
              const H = W.HOL; out[id] = {hip: H.hip.visible, sheath: H.sheath.visible, box: H.hipBox.visible, nata: !!(H.mesh[id] && H.mesh[id].visible)}; }
            Object.assign(W.prog.arms, keep); W.updHolster(); return out; }""")
        check(all(v['hip'] and v['nata'] and v['sheath'] == (not NOGLB) and v['box'] == NOGLB for v in hs.values()), f'腰の鉈は通常・蒼鱗・変異とも{"箱（GLB なし）" if NOGLB else "同じ GLB の鞘"}に収まる {hs}')

        # ---- 当たりの点はコードの形と同じ（武器の形の中の点 WTIP × 大きさ。形は関係しない） ----
        hp = await pg.evaluate("""async () => { const W = window.__w, P = W.P; W.equipArm('nata3'); for (let i = 0; i < 20; i++) W.updatePlayer(1/60);
            const a = W.weaponWorld(); const m = W.weaponMesh, keep = [...m.children]; keep.forEach(c => m.remove(c)); const code = W.makeWeaponCode('nata3'); m.add(code); const b = W.weaponWorld(); m.remove(code); keep.forEach(c => m.add(c));
            return {same: a.every((v, i) => v.every((x, k) => Math.abs(x - b[i][k]) < 1e-9)), a}; }""")
        check(hp['same'], f'当たりの点（根元・先端）は、GLB でもコードの形でも同じ {hp["a"]}')
        wj1 = await pg.evaluate("() => JSON.stringify(window.__w.WEAPONS)")
        check(wj0 == wj1, '武器の数値（威力・間合い・耐久）は変わらない')

        # ---- 攻撃が出て当たる ----
        hit = await pg.evaluate("""async () => { const W = window.__w, P = W.P, out = {}; const e = W.enemies.find(e => !e.removed && e.state !== 'dead' && e.type !== 'boss');
            for (const id of ['scClub', 'rwSpear', 'nata3']) { W.equipArm(id); for (let i = 0; i < 30; i++) W.updatePlayer(1/60); P.st = 999;
              e.x = P.x + Math.sin(P.facing) * 1.6; e.z = P.z + Math.cos(P.facing) * 1.6; e.hp = e.maxHp = 9999; W.setState(e, 'idle'); const h0 = e.hp;
              W.startAttack('light'); let g = 0; while (P.atk && g++ < 300) { W.updatePlayer(1/60); e.x = P.x + Math.sin(P.facing) * 1.6; e.z = P.z + Math.cos(P.facing) * 1.6; }
              out[id] = h0 - e.hp; } return out; }""")
        check(all(v > 0 for v in hit.values()), f'GLB の武器で通常攻撃が出て、獣に当たる（与えたダメージ）{hit}')

        # ---- 飛去来器 ----
        bm = await pg.evaluate("""async () => { const W = window.__w, P = W.P, out = []; W.equipArm('boomer'); P.dur = W.WEAPONS.boomer.maxDur;
            for (let k = 0; k < 2; k++) { for (let i = 0; i < 20; i++) W.updatePlayer(1/60); P.st = 999; const okThrow = W.startAttack('light'); let fly = null, g = 0, back = false;
              while (g++ < 600) { W.S.time += 1/60; W.updatePlayer(1/60); W.boomerUpdate(1/60); if (W.BOOM.st !== 'hand' && !fly) fly = {st: W.BOOM.st, g: W.BOOM.m.userData.wglb || null, vis: W.BOOM.m.visible, hand: W.weaponMesh.visible};
                if (fly && W.BOOM.st === 'hand') { back = true; break; } await (g % 60 ? null : new Promise(r => setTimeout(r, 0))); }
              out.push({okThrow, fly, back, handVis: W.weaponMesh.visible, flyVis: W.BOOM.m.visible}); } return out; }""")
        okb = all(x['okThrow'] and x['fly'] and x['fly']['vis'] and not x['fly']['hand'] and x['back'] and x['handVis'] and not x['flyVis'] and x['fly']['g'] == (None if NOGLB else 'boomerFly') for x in bm)
        check(okb, f'飛去来器：投げる→飛ぶ姿（{"コードの形" if NOGLB else "GLB"}）→戻って手に（2回）{bm}')

        # ---- アイコン ----
        if not NOGLB:
            ic = await pg.evaluate("""() => { const W = window.__w; const a = W.iconOf('scAxe'); return {has: !!a, len: a ? a.length : 0}; }""")
            check(ic['has'], f'アイコンは GLB を読んだあと描き直される {ic}')

        # ---- 上志比へ ----
        rg = await pg.evaluate("""async () => { const W = window.__w; W.equipArm('rwNata'); W.prog.bossDefeated = true; W.prog.stage = 'cleared'; W.prog.chapter2.unlocked = true; W.prog.chapter2.progress.defenseComplete = true;
            await W.regionTravel('kamishihi', null, {force: true}); W.F11.hold = true; W.S.mode = 'paused'; return {reg: W.REG.cur, w: W.P.weapon, g: W.weaponMesh.userData.wglb || null, vis: W.weaponMesh.visible}; }""")
        check(rg['reg'] == 'kamishihi' and rg['w'] == 'rwNata' and rg['g'] == (None if NOGLB else 'rwNata') and rg['vis'], f'上志比へ移っても手の武器はそのまま {rg}')
        await pg.evaluate("async () => { const W = window.__w; await W.regionTravel('komyoji', null, {force: true}); W.F11.hold = true; W.S.mode = 'paused'; }")

        # ---- セーブ→読み直し ----
        sv = await pg.evaluate("""() => { const W = window.__w; W.equipArm('scSpear'); W.saveGame(); const raw = localStorage.getItem('eiheiji_vs_beasts_v010'); const d = JSON.parse(raw); return {v: d.v, weapon: d.weapon, keys: Object.keys(d).length, arms: Object.keys(W.prog.arms).sort()}; }""")
        await boot(cont=True)
        st2 = await pg.evaluate(WAIT, ['azureSpear'])
        ld = await pg.evaluate("() => { const W = window.__w; return {w: W.P.weapon, g: W.weaponMesh.userData.wglb || null, arms: Object.keys(W.prog.arms).sort()}; }")
        check(sv['v'] == 1 and sv['weapon'] == 'scSpear' and ld['w'] == 'scSpear' and ld['arms'] == sv['arms'] and ld['g'] == (None if NOGLB else 'scSpear'), f'セーブ→読み直し：持ち物と手の武器が戻る（保存の版 v:{sv["v"]}）{ld} {st2}')

        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print(('PASS: weapon GLB' + (' (fallback)' if NOGLB else '')) if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
