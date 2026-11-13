#!/usr/bin/env python3
"""v0.63 鱗の装備の確認（画面のない Chromium。数分）。

本編のコードで次を確かめる（docs/mutant-scale-uses.md）。
- 変換炉：変異した鱗があると作業台に出て、組み立てられる。拠点の南東の隅に現れ、当たり判定がほかの物と重ならない
- 変換炉：鱗と燃料（木材）を入れると、1つずつ時間をかけて加工した鱗になる（遊んでいる間だけ進む）。取り出せる
- 鱗の武器：元の武器（鉈Lv3・鉄の斧・棍棒・牙槍）を、加工した鱗で上位に作り替えられる。持てて、形を作れる
- 青鱗の防具：4部位で被ダメージ -30%（4部位の上限が15%→30%）
- 変異鱗の防具：4部位で最大体力0.7倍・移動+30%。外すと戻る。力がたまると衝撃波で獣を押し出す（ダメージなし）
- 保存：変換炉・加工した鱗・鱗の武器・防具が保存され、変換炉の項目がない旧セーブは未建設で読める
- エラーなし
使い方：THREE_JS=…/three.min.js python3 tests/scale-gear-browser.py   （SCALE_SHOTS=フォルダ で画面を撮る）
"""
import asyncio
import base64
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SCALE_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
SHOTS = os.environ.get('SCALE_SHOTS')
HOOK = ("window.__t={get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get enemies(){return enemies},renderer,scene,camera,"
        "WEAPONS,CONV,CONVM,SCALE_WAVE,SCALE_FX,G47,"
        "craft:id=>craft(id),convPut:n=>convPut(n),convTake:()=>convTake(),convUpdate:dt=>convUpdate(dt),interactables:()=>interactables(),"
        "scaleFxUpdate:dt=>scaleFxUpdate(dt),updateEnemies:dt=>updateEnemies(dt),f47Equip:(a,b)=>f47Equip(a,b),f47Stats:()=>f47Stats(),f31MaxHp:l=>f31MaxHp(l),"
        "equipArm:id=>equipArm(id),armGain:(a,b)=>armGain(a,b),saveGame:()=>saveGame(),applySave:d=>applySave(d),spawnEnemy:(...a)=>spawnEnemy(...a),removeEnemy:e=>removeEnemy(e),"
        "gridQuery:(...a)=>gridQuery(...a).slice(),resolve:(a,b)=>resolve(a,b),groundH:(x,z)=>groundH(x,z)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

GIVE = "() => { const I = window.__t.inv; Object.assign(I, {mutScale: 30, procScale: 0, wood: 99, iron: 40, stone: 40, hide: 60, rope: 40, straw: 20}); }"


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        pg = await (await b.new_context(viewport={'width': 960, 'height': 600})).new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(r):
            u = r.request.url
            if 'three' in u: await r.fulfill(body=THREE, content_type='application/javascript')
            elif u.startswith('http://game.local'): await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            else: await r.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__t', timeout=300000)
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(1500)

        async def shot(name, js_cam):
            if not SHOTS:
                return
            os.makedirs(SHOTS, exist_ok=True)
            u = await pg.evaluate("(c) => { const T = window.__t; const cam = new THREE.PerspectiveCamera(42, 960/600, 0.1, 400); const f = new Function('cam', 'T', c); f(cam, T); T.renderer.setSize(960, 600); T.renderer.render(T.scene, cam); return T.renderer.domElement.toDataURL('image/png'); }", js_cam)
            open(os.path.join(SHOTS, name + '.png'), 'wb').write(base64.b64decode(u.split(',')[1]))

        # 変換炉
        hid = await pg.evaluate("() => { const T = window.__t; const before = document.querySelectorAll('#craft_convBuild').length; return {built: T.prog.conv.built}; }")
        await pg.evaluate(GIVE)
        cb = await pg.evaluate("""() => { const T = window.__t, I = T.inv; const w0 = I.wood, s0 = I.mutScale; T.craft('convBuild');
          const c = T.CONV, col = T.CONVM.col; const hw = c.W / 2, hd = c.D / 2;
          const others = T.gridQuery(c.pos.x - hw, c.pos.x + hw, c.pos.z - hd, c.pos.z + hd).filter(o => o !== col && o.active !== false && o.tag !== 'ground' &&
            (o.k === 'c' ? Math.abs(o.x - c.pos.x) < hw + o.r && Math.abs(o.z - c.pos.z) < hd + o.r : o.maxX > c.pos.x - hw && o.minX < c.pos.x + hw && o.maxZ > c.pos.z - hd && o.minZ < c.pos.z + hd));
          const P = T.P; const px = P.x, pz = P.z; P.x = c.pos.x; P.z = c.pos.z; T.resolve(P, false); const pushed = Math.hypot(P.x - c.pos.x, P.z - c.pos.z); P.x = c.pos.x; P.z = c.pos.z - c.D / 2 - 0.8;
          return {built: T.prog.conv.built, visible: T.CONVM.g.visible, colActive: col.active, overlap: others.map(o => o.tag + '@' + Math.round(o.x ?? o.minX) + ',' + Math.round(o.z ?? o.minZ)),
            usedWood: w0 - I.wood, usedScale: s0 - I.mutScale, pushed, label: (T.interactables() || {}).label }; }""")
        print('変換炉：', cb)
        check(hid['built'] == 0 and cb['built'] == 1 and cb['visible'] and cb['colActive'], '作業台で変換炉を組み立てると、拠点に現れて当たり判定が付く')
        check(not cb['overlap'], f'変換炉の場所がほかの物と重ならない {cb["overlap"]}')
        check(cb['usedScale'] == 2 and cb['usedWood'] == 10, '組み立てに変異した鱗2・木材10（ほか）を使う')
        check(cb['pushed'] > 0.9, '変換炉の中には入れない')
        check(str(cb['label']).startswith('変換炉'), f'近くで「変換炉」を調べられる（{cb["label"]}）')
        cv = await pg.evaluate("""() => { const T = window.__t, I = T.inv, C = T.prog.conv; const s0 = I.mutScale, w0 = I.wood; T.convPut(3);
          const after = {q: C.q, usedScale: s0 - I.mutScale, usedWood: w0 - I.wood};
          for (let i = 0; i < 89 * 10; i++) T.convUpdate(0.1); const at89 = C.out;
          for (let i = 0; i < 2 * 10 + 1; i++) T.convUpdate(0.1); const at91 = C.out;
          for (let i = 0; i < 181 * 10; i++) T.convUpdate(0.1); const all = {q: C.q, out: C.out};
          const p0 = I.procScale; T.convTake(); return {after, at89, at91, all, took: I.procScale - p0, outAfter: C.out}; }""")
        print('加工：', cv)
        check(cv['after'] == {'q': 3, 'usedScale': 3, 'usedWood': 6}, '鱗3つと燃料（木材6）を入れられる')
        check(cv['at89'] == 0 and cv['at91'] == 1, '1つ目は90秒でできる（すぐにはできない）')
        check(cv['all'] == {'q': 0, 'out': 3} and cv['took'] == 3 and cv['outAfter'] == 0, '3つとも加工した鱗になり、取り出せる')
        await pg.evaluate("() => { const T = window.__t; T.convPut(2); }")
        await shot('1_conv', "const c = T.CONV.pos; cam.position.set(c.x - 5.2, 3.0, c.z - 2.6); cam.lookAt(c.x, 1.1, c.z); T.convUpdate(0.5);")

        # 鱗の武器
        await pg.evaluate("() => { const T = window.__t; T.inv.procScale = 40; for (const id of ['nata3', 'axeIron', 'club', 'spear']) T.armGain(id, false); }")
        wp = await pg.evaluate("""() => { const T = window.__t; const res = {};
          for (const [id, base] of [['scNata', 'nata3'], ['scAxe', 'axeIron'], ['scClub', 'club'], ['scSpear', 'spear']]) { T.craft(id); res[id] = {have: id in T.prog.arms, baseGone: !(base in T.prog.arms)}; T.equipArm(id); T.renderer.render(T.scene, T.camera); res[id].held = T.P.weapon === id; }
          return {res, dmg: ['scNata', 'scAxe', 'scClub', 'scSpear'].map(id => [T.WEAPONS[id].light, T.WEAPONS[id].heavy]), used: 40 - T.inv.procScale}; }""")
        print('武器：', wp)
        check(all(v['have'] and v['baseGone'] and v['held'] for v in wp['res'].values()), '4つの武器を鱗の武器に作り替えて持てる')
        check(wp['used'] == 13, f'加工した鱗を使う（合計 {wp["used"]}）')
        if SHOTS:
            await pg.evaluate("() => { const P = window.__t.P; P.x = 163; P.z = 52.5; P.facing = 0.6; }")
            await pg.wait_for_timeout(700)
        await shot('2_spear', "const P = T.P; const gy = T.groundH(P.x, P.z); for (let i = 0; i < 20; i++) T.scaleFxUpdate(1 / 30); cam.position.set(P.x + 2.2, gy + 1.8, P.z + 2.8); cam.lookAt(P.x, gy + 1.1, P.z);")

        # 青鱗の防具
        bl = await pg.evaluate("""() => { const T = window.__t; T.inv.procScale = 40; for (const s of ['head', 'chest', 'legs', 'feet']) { T.craft('gear_blue_' + s); T.f47Equip(s, 'blue_' + s); }
          const st = T.f47Stats(); for (let i = 0; i < 60; i++) T.scaleFxUpdate(1 / 30);
          return {cut: Math.round(st.cut * 1000) / 1000, set: st.set, motes: T.SCALE_FX.pool.filter(s => s.visible).length}; }""")
        print('青鱗：', bl)
        check(bl['cut'] == 0.3 and bl['set'] == 'blue', '青鱗の4部位で被ダメージ -30%（上限が30%に上がる）')
        check(bl['motes'] > 0, '青い光の粒が出る')
        await shot('3_blue', "const P = T.P, gy = T.groundH(P.x, P.z); for (let i = 0; i < 30; i++) T.scaleFxUpdate(1 / 30); cam.position.set(P.x + 2.4, gy + 1.7, P.z + 2.6); cam.lookAt(P.x, gy + 0.95, P.z);")

        # 変異鱗の防具
        rw = await pg.evaluate("""() => { const T = window.__t, P = T.P; const base = T.prog.level; for (const s of ['head', 'chest', 'legs', 'feet']) T.craft('gear_raw_' + s);
          const before = P.maxHp; for (const s of ['head', 'chest', 'legs', 'feet']) T.f47Equip(s, 'raw_' + s);
          const full = {max: P.maxHp, hp: P.hp, speed: Math.round(T.f47Stats().speed * 100) / 100, dodge: Math.round(T.f47Stats().dodge * 100) / 100};
          T.f47Equip('head', null); const three = P.maxHp; T.f47Equip('head', 'raw_head');
          return {before, full, three, usedScale: 30 - 2 - 3 - 2 - T.inv.mutScale}; }""")
        print('変異鱗：', rw)
        check(rw['full']['max'] == round(rw['before'] * 0.7) and rw['full']['hp'] <= rw['full']['max'], '変異鱗の4部位で最大体力0.7倍（体力も上限に合わせる）')
        check(rw['three'] == round(rw['before'] * 0.775), '1部位外すと最大体力が戻る（1部位 -7.5%）')
        check(rw['full']['speed'] == 0.3 and rw['full']['dodge'] == 0.3, '変異鱗の4部位で移動 +30%・回避消費 -30%')
        sw = await pg.evaluate("""async () => { const T = window.__t, P = T.P; for (const e of [...T.enemies]) T.removeEnemy(e); P.maxHp = 9999; P.hp = 9999;
          const e = T.spawnEnemy('monkey', P.x + 2.2, P.z + 0.4, 'field', {aggro: true}); const hp0 = e.hp; T.SCALE_FX.charge = 0; let fired = -1, dmax = 0;
          for (let i = 0; i < 12 * 30; i++) { T.S.time += 1 / 30; T.scaleFxUpdate(1 / 30); T.updateEnemies(1 / 30); P.hp = 9999; P.iframe = 0;
            if (fired < 0 && T.SCALE_FX.charge === 0 && i > 30) fired = i / 30; if (fired >= 0) dmax = Math.max(dmax, Math.hypot(e.x - P.x, e.z - P.z)); if (fired >= 0 && i / 30 > fired + 0.6) break; }
          const out = {fired, dmax, hp0, hp: e.hp, ring: !!T.SCALE_FX.ring}; T.removeEnemy(e); return out; }""")
        print('衝撃波：', sw)
        check(9.5 < sw['fired'] < 11, f'力が10秒でたまり、近くに獣がいると放つ（{sw["fired"]}秒）')
        check(sw['dmax'] > 5.0 and sw['hp'] == sw['hp0'], f'衝撃波で獣を押し出し、ダメージはない（{sw["dmax"]:.1f}m）')
        await pg.evaluate("() => { const T = window.__t; T.SCALE_FX.charge = T.SCALE_WAVE.charge - 0.01; }")
        await shot('4_raw', "const P = T.P, gy = T.groundH(P.x, P.z); for (let i = 0; i < 25; i++) T.scaleFxUpdate(1 / 30); cam.position.set(P.x + 2.4, gy + 1.7, P.z + 2.6); cam.lookAt(P.x, gy + 0.95, P.z);")

        # 保存
        sv = await pg.evaluate("""() => { const T = window.__t; T.prog.conv.q = 2; T.prog.conv.t = 33.3; T.prog.conv.out = 1; T.saveGame(); const d = JSON.parse(localStorage.getItem('eiheiji_vs_beasts_v010'));
          T.applySave(JSON.parse(JSON.stringify(d))); const c = T.prog.conv; const back = {built: c.built, q: c.q, t: c.t, out: c.out, proc: T.inv.procScale, spear: 'scSpear' in T.prog.arms, raw: T.prog.gear.equip.chest, max: T.P.maxHp};
          const old = JSON.parse(JSON.stringify(d)); delete old.conv; delete old.inv.procScale; T.applySave(old); const o = {built: T.prog.conv.built, q: T.prog.conv.q, proc: T.inv.procScale};
          return {v: d.v, saved: d.conv, back, old: o}; }""")
        print('保存：', sv)
        check(sv['v'] == 1 and sv['saved'] == {'v': 1, 'built': 1, 'q': 2, 't': 33.3, 'out': 1}, '変換炉の状態を保存する（v:1 のまま）')
        check(sv['back']['built'] == 1 and sv['back']['q'] == 2 and abs(sv['back']['t'] - 33.3) < 0.01 and sv['back']['out'] == 1 and sv['back']['spear'] and sv['back']['raw'] == 'raw_chest', '読み込むと変換炉・鱗の武器・防具が戻る')
        check(sv['back']['max'] == round(sv['back']['max']) and sv['back']['max'] < 100, f'変異鱗を着たまま読み込むと最大体力も0.7倍（{sv["back"]["max"]}）')
        check(sv['old'] == {'built': 0, 'q': 0, 'proc': 0}, '変換炉・加工した鱗の項目がない旧セーブは、未建設・0で読める')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: scale gear' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
