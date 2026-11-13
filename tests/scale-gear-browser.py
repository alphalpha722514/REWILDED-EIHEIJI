#!/usr/bin/env python3
"""v0.63〜 鱗の装備の確認（画面のない Chromium。数分）。v0.64 でかまど・木炭・変異鱗の武器・鱗の飛去来器・衝撃波のボタン・防具の形を足した。

本編のコードで次を確かめる（docs/mutant-scale-uses.md）。
- かまど：木材を焼いて、1つ30秒で木炭を作る（燃料も木材）。変換炉の隣に築き、当たり判定がほかの物と重ならない
- 変換炉：燃料は木炭。変異した鱗と木炭を入れると、1つ90秒で加工した鱗になる。木炭がないと動かない
- 武器：蒼鱗（加工した鱗）と変異鱗（鱗をそのまま）で、4つの武器の上位を作れる。持てる
- 鱗の飛去来器：投げると飛んで戻る。当たると傷を与える。飛んでいる間にもう一度攻撃すると、周りの獣を押し出して傷を与える。
  投げるたびに耐久が1減り、0で投げられない。手入れ（加工した鱗1）で戻る。飛んでいる間は持ち替えられない
- 蒼鱗の防具：4部位で被ダメージ -30%。形（金属の板に鱗）が出て、鱗と継ぎ目から光の粒が出る
- 変異した鱗の防具：最大体力0.7倍・移動+30%。衝撃波は自動では出ず、力がたまってからボタン（F）で放つ（ダメージなし）
- 保存：変換炉・かまど・木炭・加工した鱗・武器・防具。項目がない旧セーブも読める
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
HOOK = ("window.__t={get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get enemies(){return enemies},get pm(){return pm},renderer,scene,camera,"
        "WEAPONS,FAC,FACM,SCALE_WAVE,SCALE_FX,G47,BOOM,BOOMER,"
        "craft:id=>craft(id),facPut:(a,n)=>facPut(a,n),facTake:a=>facTake(a),facUpdate:dt=>facUpdate(dt),interactables:()=>interactables(),"
        "scaleFxUpdate:dt=>scaleFxUpdate(dt),updateEnemies:dt=>updateEnemies(dt),updatePlayer:dt=>updatePlayer(dt),boomerUpdate:dt=>boomerUpdate(dt),tryAttack:(k,a)=>tryAttack(k,a),scaleWaveBtn:()=>scaleWaveBtn(),updateF6C:dt=>updateF6C(dt),"
        "f47Equip:(a,b)=>f47Equip(a,b),f47Stats:()=>f47Stats(),f31MaxHp:l=>f31MaxHp(l),armDur:id=>armDur(id),"
        "equipArm:id=>equipArm(id),armGain:(a,b)=>armGain(a,b),saveGame:()=>saveGame(),applySave:d=>applySave(d),spawnEnemy:(...a)=>spawnEnemy(...a),removeEnemy:e=>removeEnemy(e),"
        "gridQuery:(...a)=>gridQuery(...a).slice(),resolve:(a,b)=>resolve(a,b),groundH:(x,z)=>groundH(x,z)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

GIVE = "() => { const I = window.__t.inv; Object.assign(I, {mutScale: 40, procScale: 0, charcoal: 0, wood: 120, iron: 60, stone: 60, hide: 80, rope: 50, straw: 20}); }"
# ほかの当たり判定との重なり（施設の箱の中にあるもの）
OVERLAP = """(id) => { const T = window.__t, F = T.FAC[id], col = T.FACM[id].col, hw = F.W / 2, hd = F.D / 2;
  return T.gridQuery(F.pos.x - hw, F.pos.x + hw, F.pos.z - hd, F.pos.z + hd).filter(o => o !== col && o.active !== false && o.tag !== 'ground' &&
    (o.k === 'c' ? Math.abs(o.x - F.pos.x) < hw + o.r && Math.abs(o.z - F.pos.z) < hd + o.r : o.maxX > F.pos.x - hw && o.minX < F.pos.x + hw && o.maxZ > F.pos.z - hd && o.minZ < F.pos.z + hd))
    .map(o => o.tag + '@' + Math.round(o.x ?? o.minX) + ',' + Math.round(o.z ?? o.minZ)); }"""
# n フレーム、主人公・飛去来器・獣・光を進める
STEP = """(n) => { const T = window.__t; for (let i = 0; i < n; i++) { T.S.time += 1 / 60; T.updatePlayer(1 / 60); T.boomerUpdate(1 / 60); T.updateEnemies(1 / 60); T.scaleFxUpdate(1 / 60); T.P.hp = T.P.maxHp; T.P.iframe = 0; } }"""


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

        async def shot(name, js_cam, move=None):
            if not SHOTS:
                return
            if move:
                await pg.evaluate(move)
                await pg.wait_for_timeout(700)
            os.makedirs(SHOTS, exist_ok=True)
            u = await pg.evaluate("(c) => { const T = window.__t; const cam = new THREE.PerspectiveCamera(40, 960/600, 0.05, 400); const f = new Function('cam', 'T', c); f(cam, T); T.renderer.setSize(960, 600); T.renderer.render(T.scene, cam); return T.renderer.domElement.toDataURL('image/png'); }", js_cam)
            open(os.path.join(SHOTS, name + '.png'), 'wb').write(base64.b64decode(u.split(',')[1]))

        # ---- かまどと変換炉 ----
        await pg.evaluate(GIVE)
        fa = await pg.evaluate("""() => { const T = window.__t, I = T.inv; const w0 = I.wood; T.craft('kamaBuild'); const kamaWood = w0 - I.wood; const s0 = I.mutScale; T.craft('convBuild');
          const P = T.P, out = {}; for (const id of ['kama', 'conv']) { const F = T.FAC[id]; P.x = F.pos.x; P.z = F.pos.z; T.resolve(P, false); out[id] = {built: T.prog[id].built, vis: T.FACM[id].g.visible, col: T.FACM[id].col.active, pushed: Math.hypot(P.x - F.pos.x, P.z - F.pos.z) > 0.5}; }
          const k = T.FAC.kama, c = T.FAC.conv; const gap = (c.pos.x - c.W / 2) - (k.pos.x + k.W / 2);
          P.x = k.pos.x; P.z = k.pos.z - k.D / 2 - 0.7; const lab = (T.interactables() || {}).label;
          return {out, kamaWood, convScale: s0 - I.mutScale, gap, lab}; }""")
        print('施設：', fa)
        check(all(v['built'] and v['vis'] and v['col'] and v['pushed'] for v in fa['out'].values()), 'かまどと変換炉を作業台で築くと現れ、中に入れない')
        check(fa['gap'] > 0.2, f'かまどと変換炉が重ならない（すき間 {fa["gap"]:.2f}）')
        for id_ in ['kama', 'conv']:
            ov = await pg.evaluate(OVERLAP, id_)
            check(not ov, f'{id_} の場所がほかの物と重ならない {ov}')
        check(str(fa['lab']).startswith('かまど'), f'近くで「かまど」を調べられる（{fa["lab"]}）')
        ch = await pg.evaluate("""() => { const T = window.__t, I = T.inv, K = T.prog.kama, C = T.prog.conv; const w0 = I.wood; T.facPut('kama', 2); const used = w0 - I.wood;
          const deny = (T.facPut('conv', 1), C.q);
          for (let i = 0; i < 29 * 10; i++) T.facUpdate(0.1); const at29 = K.out; for (let i = 0; i < 31 * 10 + 2; i++) T.facUpdate(0.1); const at60 = K.out;
          T.facTake('kama'); const coal = I.charcoal; const s0 = I.mutScale; T.facPut('conv', 2); const cq = C.q, cUsed = {scale: s0 - I.mutScale, coal: coal - I.charcoal};
          for (let i = 0; i < 89 * 10; i++) T.facUpdate(0.1); const c89 = C.out; for (let i = 0; i < 91 * 10 + 2; i++) T.facUpdate(0.1); const c180 = C.out; T.facTake('conv');
          return {used, deny, at29, at60, coal, cq, cUsed, c89, c180, proc: I.procScale}; }""")
        print('木炭と加工：', ch)
        check(ch['used'] == 6 and ch['at29'] == 0 and ch['at60'] == 2 and ch['coal'] == 2, 'かまど：木材3（材料2・燃料1）で、1つ30秒で木炭ができる')
        check(ch['deny'] == 0, '変換炉：木炭がないと動かない')
        check(ch['cq'] == 2 and ch['cUsed'] == {'scale': 2, 'coal': 2} and ch['c89'] == 0 and ch['c180'] == 2 and ch['proc'] == 2, '変換炉：鱗1と木炭1で、1つ90秒で加工した鱗ができる')
        await shot('1_facilities', "const k = T.FAC.kama.pos; T.prog.kama.q = 2; T.prog.conv.q = 2; T.facUpdate(0.6); cam.position.set(k.x - 3.6, 2.4, k.z - 4.6); cam.lookAt(k.x + 2.2, 0.8, k.z);")
        await pg.evaluate("() => { const T = window.__t; T.prog.kama.q = 0; T.prog.conv.q = 0; T.prog.kama.t = 0; T.prog.conv.t = 0; }")

        # ---- 武器 ----
        wp = await pg.evaluate("""() => { const T = window.__t; T.inv.procScale = 60; const res = {};
          const bases = {Nata: 'nata3', Axe: 'axeIron', Club: 'club', Spear: 'spear'};
          for (const pre of ['sc', 'rw']) { for (const b of Object.values(bases)) T.armGain(b, false);
            for (const [k, base] of Object.entries(bases)) { const id = pre + k; T.craft(id); T.equipArm(id); T.renderer.render(T.scene, T.camera); res[id] = {have: id in T.prog.arms, held: T.P.weapon === id, name: T.WEAPONS[id].name, scale: T.WEAPONS[id].scale}; } }
          return res; }""")
        print('武器：', {k: v['name'] for k, v in wp.items()})
        check(all(v['have'] and v['held'] for v in wp.values()), '蒼鱗と変異鱗の武器（4つずつ）を作って持てる')
        check([wp[k]['name'] for k in ['scNata', 'rwNata']] == ['蒼鱗の鉈', '変異鱗の鉈'] and wp['rwSpear']['scale'] == 'raw', '名前：蒼鱗の鉈・変異鱗の鉈（ユーザー決定）')
        await shot('2_weapons', "const P = T.P, gy = T.groundH(P.x, P.z); cam.position.set(P.x + 1.9, gy + 1.6, P.z + 2.2); cam.lookAt(P.x, gy + 1.1, P.z);",
                   "() => { const T = window.__t, P = T.P; P.x = 163; P.z = 52.5; P.facing = 0.6; T.equipArm('rwSpear'); for (let i = 0; i < 40; i++) T.scaleFxUpdate(1 / 30); }")

        # ---- 鱗の飛去来器 ----
        bm = await pg.evaluate("""() => { const T = window.__t, P = T.P; for (const e of [...T.enemies]) T.removeEnemy(e); T.craft('boomer'); T.equipArm('boomer');
          P.x = 150; P.z = 52; P.facing = 0; P.st = 100; const dur0 = T.armDur('boomer');
          const e = T.spawnEnemy('monkey', P.x, P.z + 6, 'field', {aggro: false}); e.state = 'stun'; e.stunT = 99; const hp0 = e.hp;
          T.tryAttack('light', 0); let maxD = 0, st = [], back = false;
          for (let i = 0; i < 300; i++) { T.S.time += 1 / 60; T.updatePlayer(1 / 60); T.boomerUpdate(1 / 60); T.updateEnemies(1 / 60); e.state = 'stun'; e.stunT = 99;
            if (T.BOOM.st !== 'hand') maxD = Math.max(maxD, Math.hypot(T.BOOM.x - P.x, T.BOOM.z - P.z)); if (st[st.length - 1] !== T.BOOM.st) st.push(T.BOOM.st); if (i > 20 && T.BOOM.st === 'hand') { back = true; break; } }
          const hit = hp0 - e.hp; T.removeEnemy(e); return {held: P.weapon, dur0, dur1: T.armDur('boomer'), maxD, st, back, hit}; }""")
        print('飛去来器：', bm)
        check(bm['held'] == 'boomer' and bm['st'][:3] == ['hand', 'out', 'back'] and bm['back'], '投げると飛んで、手元に戻る')
        check(10.5 < bm['maxD'] < 13.5, f'通常の投げは約12まで飛ぶ（{bm["maxD"]:.1f}）')
        check(bm['hit'] >= 18, f'飛んでいる飛去来器が獣に当たる（{bm["hit"]}）')
        check(bm['dur0'] == 10 and bm['dur1'] == 9, '投げるたびに耐久が1減る（10回分）')
        wv = await pg.evaluate("""() => { const T = window.__t, P = T.P; P.x = 150; P.z = 52; P.facing = 0; P.st = 100;
          const e = T.spawnEnemy('boar', P.x + 1.2, P.z + 7, 'field', {aggro: false}); const hp0 = e.hp, x0 = e.x;
          T.tryAttack('light', 0); for (let i = 0; i < 20; i++) { T.S.time += 1 / 60; T.updatePlayer(1 / 60); T.boomerUpdate(1 / 60); }
          const bx = T.BOOM.x, bz = T.BOOM.z; const swapBlocked = (T.equipArm('nata1'), T.P.weapon === 'boomer'); const pre = Math.hypot(e.x - bx, e.z - bz);
          T.tryAttack('light'); const det = T.BOOM.det; for (let i = 0; i < 40; i++) { T.S.time += 1 / 60; T.boomerUpdate(1 / 60); T.updateEnemies(1 / 60); }
          const post = Math.hypot(e.x - bx, e.z - bz), dmg = hp0 - e.hp; for (let i = 0; i < 300 && T.BOOM.st !== 'hand'; i++) { T.S.time += 1 / 60; T.updatePlayer(1 / 60); T.boomerUpdate(1 / 60); }
          T.removeEnemy(e); return {det, pre, post, dmg, swapBlocked, back: T.BOOM.st}; }""")
        print('衝撃波（飛去来器）：', wv)
        check(wv['det'] and wv['post'] - wv['pre'] > 2.0 and wv['dmg'] >= 15, f'飛んでいる間にもう一度攻撃すると、周りの獣を押し出して傷を与える（{wv["post"] - wv["pre"]:.1f}m・{wv["dmg"]}）')
        check(wv['swapBlocked'] and wv['back'] == 'hand', '飛んでいる間は持ち替えられず、戻ってくる')
        dz = await pg.evaluate("""() => { const T = window.__t, P = T.P; T.prog.arms.boomer = 0; P.dur = 0; P.st = 100; T.tryAttack('light', 0); for (let i = 0; i < 30; i++) { T.S.time += 1 / 60; T.updatePlayer(1 / 60); T.boomerUpdate(1 / 60); }
          const threw = T.BOOM.st !== 'hand'; const p0 = T.inv.procScale; T.craft('boomerFix'); return {threw, fixed: T.armDur('boomer'), used: p0 - T.inv.procScale}; }""")
        print('耐久：', dz)
        check(not dz['threw'] and dz['fixed'] == 10 and dz['used'] == 1, '耐久0では投げられず、手入れ（加工した鱗1）で戻る')
        await shot('3_boomer', "const P = T.P; P.x = 163; P.z = 50; P.facing = 0; P.st = 100; T.tryAttack('light', 0); for (let i = 0; i < 26; i++) { T.S.time += 1 / 60; T.updatePlayer(1 / 60); T.boomerUpdate(1 / 60); T.scaleFxUpdate(1 / 60); } const b = T.BOOM, gy = T.groundH(b.x, b.z); cam.position.set(b.x + 1.8, gy + 1.8, b.z - 1.0); cam.lookAt(b.x, gy + 1.1, b.z);")
        await pg.evaluate("() => { const T = window.__t; for (let i = 0; i < 400 && T.BOOM.st !== 'hand'; i++) { T.updatePlayer(1 / 60); T.boomerUpdate(1 / 60); } T.equipArm('scSpear'); }")

        # ---- 蒼鱗の防具 ----
        bl = await pg.evaluate("""() => { const T = window.__t; T.inv.procScale = 60; for (const s of ['head', 'chest', 'legs', 'feet']) { T.craft('gear_blue_' + s); T.f47Equip(s, 'blue_' + s); }
          const st = T.f47Stats(); const L = T.pm.layers; const vis = Object.fromEntries(Object.entries(L).map(([k, a]) => [k, a.filter(g => g.visible).map(g => g.userData.variant)]));
          const em = T.SCALE_FX.emit.blue.filter(o => o.userData.layer.visible).length; T.SCALE_FX.pool.forEach(s => s.visible = false); for (let i = 0; i < 60; i++) T.scaleFxUpdate(1 / 30);
          return {cut: Math.round(st.cut * 1000) / 1000, set: st.set, vis, em, motes: T.SCALE_FX.pool.filter(s => s.visible).length, names: ['head', 'chest', 'legs', 'feet'].map(s => T.G47['blue_' + s].name)}; }""")
        print('蒼鱗：', bl)
        check(bl['cut'] == 0.3 and bl['set'] == 'blue', '蒼鱗の4部位で被ダメージ -30%')
        check(all(v and set(v) == {'blue'} for v in bl['vis'].values()), '蒼鱗の形（金属の板と鱗）が頭・胸・脚・足に出る')
        check(bl['em'] >= 15 and bl['motes'] > 0, f'埋め込んだ鱗と継ぎ目から光の粒が出る（吹き出し口 {bl["em"]}）')
        check(bl['names'][0] == '蒼鱗の鉢金', '名前：蒼鱗（ユーザー決定）')
        mv_front = "() => { const T = window.__t, P = T.P; P.x = 163; P.z = 52.5; P.facing = 0.35; for (let i = 0; i < 40; i++) T.scaleFxUpdate(1 / 30); }"
        await shot('4_blue_front', "const P = T.P, gy = T.groundH(P.x, P.z); for (let i = 0; i < 20; i++) T.scaleFxUpdate(1 / 30); cam.position.set(P.x + Math.sin(P.facing) * 2.9 + 0.5, gy + 1.5, P.z + Math.cos(P.facing) * 2.9); cam.lookAt(P.x, gy + 1.05, P.z);", mv_front)
        await shot('5_blue_back', "const P = T.P, gy = T.groundH(P.x, P.z); for (let i = 0; i < 20; i++) T.scaleFxUpdate(1 / 30); cam.position.set(P.x - Math.sin(P.facing) * 2.9 - 0.5, gy + 1.5, P.z - Math.cos(P.facing) * 2.9); cam.lookAt(P.x, gy + 1.05, P.z);")

        # ---- 変異した鱗の防具 ----
        rw = await pg.evaluate("""() => { const T = window.__t, P = T.P; const before = T.f31MaxHp(T.prog.level); for (const s of ['head', 'chest', 'legs', 'feet']) { T.craft('gear_raw_' + s); T.f47Equip(s, 'raw_' + s); }
          return {before, max: P.maxHp, hp: P.hp, speed: Math.round(T.f47Stats().speed * 100) / 100, name: T.G47.raw_chest.name}; }""")
        print('変異した鱗：', rw)
        check(rw['max'] == round(rw['before'] * 0.7) and rw['hp'] <= rw['max'] and rw['speed'] == 0.3, '変異した鱗の4部位で最大体力0.7倍・移動+30%')
        check(rw['name'] == '変異した鱗の胴当て', '名前：変異した鱗（ユーザー決定）')
        sw = await pg.evaluate("""() => { const T = window.__t, P = T.P; for (const e of [...T.enemies]) T.removeEnemy(e); P.x = 150; P.z = 52;
          const e = T.spawnEnemy('monkey', P.x + 2.2, P.z + 0.4, 'field', {aggro: true}); const hp0 = e.hp; T.SCALE_FX.charge = 0; T.SCALE_FX.smoke.forEach(s => s.visible = false);
          const d = () => Math.hypot(e.x - P.x, e.z - P.z); let maxAuto = 0;
          for (let i = 0; i < 12 * 30; i++) { T.S.time += 1 / 30; T.scaleFxUpdate(1 / 30); e.x = P.x + 2.2; e.z = P.z + 0.4; e.state = 'stun'; e.stunT = 9; T.updateEnemies(1 / 30); P.hp = P.maxHp; P.dead = false; maxAuto = Math.max(maxAuto, d()); }
          T.updateF6C(0); const btnReady = document.getElementById('tbWave').classList.contains('ready');
          const smoke = T.SCALE_FX.smoke.filter(s => s.visible).length; const charged = T.SCALE_FX.charge; T.scaleWaveBtn(); const fired = T.SCALE_FX.charge === 0;
          for (let i = 0; i < 40; i++) { T.S.time += 1 / 30; T.updateEnemies(1 / 30); } const after = d();
          T.updateF6C(0); const btn = document.getElementById('tbWave'); const out = {maxAuto, charged, fired, after, hp0, hp: e.hp, smoke, btnShown: !btn.hidden, btnReady}; T.removeEnemy(e);
          T.SCALE_FX.charge = 3; const s2 = T.SCALE_FX.charge; T.scaleWaveBtn(); out.early = T.SCALE_FX.charge === s2; return out; }""")
        print('衝撃波（防具）：', sw)
        check(sw['maxAuto'] < 3.0, '衝撃波は自動では出ない（ユーザー決定：ボタンで出す）')
        check(sw['charged'] >= 10 and sw['fired'] and sw['after'] > 5.0 and sw['hp'] == sw['hp0'], f'力がたまったらボタンで放ち、獣を押し出す（{sw["after"]:.1f}m・ダメージなし）')
        check(sw['early'], 'たまる前に押しても出ない')
        check(sw['smoke'] > 0, '暗い紫のもやが立ちのぼる')
        check(sw['btnShown'] and sw['btnReady'], 'スマホの「衝撃」ボタンが一式のときに出て、たまると光る')
        await shot('6_raw_front', "const P = T.P, gy = T.groundH(P.x, P.z); T.SCALE_FX.charge = 10; for (let i = 0; i < 40; i++) T.scaleFxUpdate(1 / 30); cam.position.set(P.x + Math.sin(P.facing) * 2.9 + 0.5, gy + 1.5, P.z + Math.cos(P.facing) * 2.9); cam.lookAt(P.x, gy + 1.05, P.z);", mv_front)

        # ---- 保存 ----
        sv = await pg.evaluate("""() => { const T = window.__t; T.prog.conv.q = 2; T.prog.conv.t = 33.3; T.prog.kama.out = 3; T.inv.charcoal = 4; T.saveGame(); const d = JSON.parse(localStorage.getItem('eiheiji_vs_beasts_v010'));
          T.applySave(JSON.parse(JSON.stringify(d))); const back = {conv: [T.prog.conv.built, T.prog.conv.q, T.prog.conv.t], kama: [T.prog.kama.built, T.prog.kama.out], coal: T.inv.charcoal, boomer: 'boomer' in T.prog.arms, rw: 'rwSpear' in T.prog.arms, raw: T.prog.gear.equip.chest, max: T.P.maxHp};
          const old = JSON.parse(JSON.stringify(d)); delete old.conv; delete old.kama; delete old.inv.procScale; delete old.inv.charcoal; T.applySave(old);
          return {v: d.v, saved: {conv: d.conv, kama: d.kama}, back, old: {conv: T.prog.conv.built, kama: T.prog.kama.built, proc: T.inv.procScale, coal: T.inv.charcoal}}; }""")
        print('保存：', sv)
        check(sv['v'] == 1 and sv['saved']['conv']['q'] == 2 and sv['saved']['kama']['out'] == 3, '変換炉・かまどの状態を保存する（v:1 のまま）')
        check(sv['back']['conv'][:2] == [1, 2] and abs(sv['back']['conv'][2] - 33.3) < 0.01 and sv['back']['kama'] == [1, 3] and sv['back']['coal'] == 4 and sv['back']['boomer'] and sv['back']['rw'] and sv['back']['raw'] == 'raw_chest' and sv['back']['max'] < 100,
              '読み込むと施設・木炭・飛去来器・変異鱗の武器・防具（体力0.7倍）が戻る')
        check(sv['old'] == {'conv': 0, 'kama': 0, 'proc': 0, 'coal': 0}, '施設・加工した鱗・木炭の項目がない旧セーブは、未建設・0で読める')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: scale gear' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
