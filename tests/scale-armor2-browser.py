#!/usr/bin/env python3
"""v0.76 鱗の防具（作り直し）の確認。画面のない Chromium・SwiftShader（数分）。docs/scale-armor-v2.md

- 8種類（蒼鱗・変異した鱗 × 頭・胸・脚・靴）を1つずつ着られ、その部位の形だけが見える（ほかの部位・ほかの系統は見えない）
- 着替えると古い形・演出（ゆらぎ・光の筋・火の粉の吹き出し口）が残らない。脱ぐと何も見えない
- 形は初めて着たときに1回だけ作る（同じ部位を何度着替えても増えない）
- 防御力・最大体力・移動など（f47Stats・f31MaxHp）は v0.75 と同じ値
- 走る・攻撃・回避の間、防具は体と同じ骨で動く（体の骨の行列を使う skinning。骨に付いたまま離れない）
- 光・ゆらぎ：変異はゆっくり脈打ち、戦闘中は少し強い。蒼鱗は光る。どちらも防具を着ているときだけ動く
- セーブ→読み直し→続きから：着ていた防具が戻り、形が出る（保存の形式は変えない）
- 描く回数・三角形（一式を着たとき）を出す
- エラーなし
"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SA_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
HOOK = ("window.__t={get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get pm(){return pm},get SA(){return SA},get SCALE_FX(){return SCALE_FX},get G47(){return G47},get F11(){return F11},get enemies(){return enemies},"
        "renderer,scene,camera,f47Equip:(s,i)=>f47Equip(s,i),f47Stats:()=>f47Stats(),f31MaxHp:l=>f31MaxHp(l),scaleFxUpdate:dt=>scaleFxUpdate(dt),updatePlayer:dt=>updatePlayer(dt),startAttack:k=>startAttack(k),tryDodge:f=>tryDodge(f),"
        "saveGame:()=>saveGame(),updateCamera:dt=>updateCamera(dt)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
VIS = """() => { const T = window.__t, L = T.pm.layers, out = {}; for (const k in L) out[k] = L[k].filter(g => g.name && g.name.startsWith('scaleArmor') && g.visible).map(g => g.name.replace('scaleArmor_', ''));
  out.built = Object.values(L).flat().filter(g => g.name && g.name.startsWith('scaleArmor')).length;
  out.emitVis = ['blue', 'raw'].map(s => T.SCALE_FX.emit[s].filter(o => o.userData.layer.visible).length); return out; }"""


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

        async def boot(cont=False):
            await pg.goto('http://game.local/', wait_until='load', timeout=300000)
            await pg.wait_for_function('window.__t', timeout=300000)
            await pg.click('#btnContinue' if cont else '#btnNew')
            await pg.wait_for_timeout(500)
            for _ in range(15):
                if await pg.evaluate("document.getElementById('dialog').hidden"):
                    break
                await pg.click('#dialog')
                await pg.wait_for_timeout(200)
            await pg.evaluate("() => { const T = window.__t; T.F11.hold = true; T.S.mode = 'paused'; for (const e of T.enemies) { e.x += 3000; e.z += 3000; } }")

        await boot()
        r0 = await pg.evaluate("() => { const T = window.__t; return {built: Object.values(T.pm.layers).flat().filter(g => g.name && g.name.startsWith('scaleArmor')).length, lazy: !!T.pm.saLazy}; }")
        check(r0['built'] == 0 and r0['lazy'], f'始めは鱗の防具の形を作らない（着たときに作る）{r0}')
        await pg.evaluate("() => { const T = window.__t, g = T.prog.gear; for (const id of Object.keys(T.G47)) if (/^(blue|raw)_/.test(id) && !g.owned.includes(id)) g.owned.push(id); }")

        # 動いて向きを変えてから初めて着る（作るときの位置に関係なく、体に付いていること）
        await pg.evaluate("() => { const T = window.__t, P = T.P; P.x += 23; P.z -= 17; P.facing = 2.1; for (let i = 0; i < 10; i++) T.updatePlayer(1 / 60); }")
        ON = """() => { const T = window.__t, pm = T.pm, X = THREE, out = {}; pm.g.updateMatrixWorld(true); pm.skin.skeleton.update();
          const BN = {head: 'head', chest: 'chest', legs: 'shinL', feet: 'footL'}, bw = new X.Vector3(), v = new X.Vector3();
          for (const slot in BN) for (const grp of pm.layers[slot]) { if (!grp.name || !grp.name.startsWith('scaleArmor')) continue; const s = grp.children[0]; s.skeleton.update();
            const bi = s.skeleton.bones.findIndex(b => b.name === BN[slot]); let n = 0, cx = 0, cy = 0, cz = 0, far = 0; const P = s.geometry.attributes.position, SI = s.geometry.attributes.skinIndex.array;
            bw.setFromMatrixPosition(s.skeleton.bones[bi].matrixWorld);
            for (let i = 0; i < P.count; i += 7) { s.boneTransform(i, v); v.applyMatrix4(s.matrixWorld); if (SI[i * 4] === bi) { far = Math.max(far, v.distanceTo(bw)); } cx += v.x; cy += v.y; cz += v.z; n++; }
            out[grp.name.replace('scaleArmor_', '')] = {far: +far.toFixed(2), dxz: +Math.hypot(cx / n - pm.g.position.x, cz / n - pm.g.position.z).toFixed(2)}; }
          return out; }"""

        # ---- 8種類を1つずつ ----
        rows = {}
        for set_ in ['blue', 'raw']:
            for slot in ['head', 'chest', 'legs', 'feet']:
                await pg.evaluate("([s, id]) => { const T = window.__t; for (const k of ['head','chest','legs','feet']) T.f47Equip(k, k === 'head' ? null : 'work_' + k); T.f47Equip(s, id); }", [slot, set_ + '_' + slot])
                v = await pg.evaluate(VIS)
                rows[set_ + '_' + slot] = v
        bad = {k: v for k, v in rows.items() if [x for s in ['head', 'chest', 'legs', 'feet'] for x in v[s]] != [k]}
        check(not bad, f'8種類を1つずつ着ると、その部位の形だけが見える {bad or "（すべて）"}')
        on = await pg.evaluate(ON)
        check(len(on) == 8 and all(v['far'] < 0.8 and v['dxz'] < 0.3 for v in on.values()), f'歩いて向きを変えた後に初めて着ても、防具は体に付いている（骨から 0.8m 以内・体の中心から横に 0.3m 以内）{on}')
        emit = {k: v['emitVis'] for k, v in rows.items()}
        check(all((e[0] > 0) == k.startswith('blue') and (e[1] > 0) == k.startswith('raw') for k, e in emit.items()), f'光の粒の吹き出し口は、着ている部位のぶんだけ使う {emit}')

        # ---- 着替え・脱ぐ・作る回数 ----
        await pg.evaluate("() => { window.__vis = " + VIS + "; }")
        sw = await pg.evaluate("""() => { const T = window.__t; for (const k of ['head','legs','feet']) T.f47Equip(k, k === 'head' ? null : 'work_' + k); for (let i = 0; i < 3; i++) { T.f47Equip('chest', 'blue_chest'); T.f47Equip('chest', 'raw_chest'); }
            const a = window.__vis(); T.f47Equip('chest', null); T.f47Equip('chest', 'work_chest'); const b = window.__vis(); return {a, b}; }""")
        check(sw['a']['chest'] == ['raw_chest'] and sw['a']['built'] == 8 and sw['b']['chest'] == [] and sum(sw['b']['emitVis']) == 0, f'着替えても古い形は残らず、脱ぐと何も見えない。形は8つだけ（作り直さない）{sw}')

        # ---- 防御力などは同じ ----
        st = await pg.evaluate("""() => { const T = window.__t, out = {}; for (const k of ['head','chest','legs','feet']) T.f47Equip(k, k === 'head' ? null : 'work_' + k); const base0 = T.P.maxHp; for (const set of ['blue', 'raw']) { for (const k of ['head','chest','legs','feet']) T.f47Equip(k, set + '_' + k); const s = T.f47Stats(); out[set] = {cut: Math.round(s.cut * 1000) / 1000, speed: Math.round(s.speed * 100) / 100, dodge: Math.round(s.dodge * 1000) / 1000, set: s.set, max: T.P.maxHp, base: base0}; } return out; }""")
        check(st['blue']['cut'] == 0.3 and st['blue']['set'] == 'blue' and st['blue']['max'] == st['blue']['base'] and st['raw']['cut'] == 0.12 and st['raw']['speed'] == 0.3 and st['raw']['dodge'] == 0.3 and st['raw']['max'] == round(st['raw']['base'] * 0.7), f'防御力・移動・最大体力は前と同じ（v0.75 と同じ値）{st}')

        # ---- 一式を着て、走る・攻撃・回避（骨と一緒に動く）・光 ----
        mv = await pg.evaluate("""async () => { const T = window.__t, P = T.P, pm = T.pm, out = {};
            for (const k of ['head','chest','legs','feet']) T.f47Equip(k, 'raw_' + k);
            const grp = pm.layers.chest.find(g => g.name === 'scaleArmor_raw_chest'), sk = grp.children[0].skeleton, body = pm.skin.skeleton;
            out.sameSkeletonBones = sk.bones.every((b, i) => b === body.bones[i]);
            // 攻撃・回避の途中で、胸当ての付いた骨（chest）の動きが体と同じ
            P.st = 999; T.startAttack('light'); for (let i = 0; i < 8; i++) T.updatePlayer(1 / 60); pm.g.updateMatrixWorld(true);
            out.atk = !!P.atk;
            for (let i = 0; i < 60; i++) T.updatePlayer(1 / 60);
            T.S.mode = 'playing'; T.S.time = 1; T.scaleFxUpdate(0.016); const calm = T.SA.raw.value; P.atk = {t: 0}; T.scaleFxUpdate(0.016); for (let i = 0; i < 80; i++) T.scaleFxUpdate(0.016); const fight = T.SA.raw.value; P.atk = null; T.S.mode = 'paused';
            out.glow = {calm: +calm.toFixed(3), fight: +fight.toFixed(3), time: T.SA.time.value};
            return out; }""")
        check(mv['sameSkeletonBones'], '防具は体と同じ骨で動く（同じ骨の組を使う）')
        check(mv['glow']['fight'] > mv['glow']['calm'], f'変異のゆらぎは戦闘中に少し強くなる {mv["glow"]}')

        # ---- 描く回数・三角形 ----
        perf = await pg.evaluate("""() => { const T = window.__t, r = T.renderer, out = {}; r.info.autoReset = true; T.updateCamera(0.016);
            const meas = () => { r.render(T.scene, T.camera); return {calls: r.info.render.calls, tris: r.info.render.triangles}; };
            for (const k of ['head','chest','legs','feet']) T.f47Equip(k, k === 'head' ? null : 'work_' + k); out.none = meas();
            for (const set of ['blue', 'raw']) { for (const k of ['head','chest','legs','feet']) T.f47Equip(k, set + '_' + k); out[set] = meas(); }
            let ms = T.pm.saMs; out.buildMs = ms; return out; }""")
        print('重さ：', json.dumps(perf, ensure_ascii=False))
        check(perf['blue']['calls'] - perf['none']['calls'] <= 16 and perf['raw']['calls'] - perf['none']['calls'] <= 16, f'一式を着たときの描く回数の増え（蒼鱗 +{perf["blue"]["calls"] - perf["none"]["calls"]}・変異 +{perf["raw"]["calls"] - perf["none"]["calls"]}、16以下）')

        # ---- セーブ→読み直し ----
        await pg.evaluate("() => { const T = window.__t; for (const k of ['head','chest','legs','feet']) T.f47Equip(k, 'raw_' + k); T.f47Equip('head', 'blue_head'); T.saveGame(); }")
        await boot(cont=True)
        v2 = await pg.evaluate(VIS)
        check(v2['head'] == ['blue_head'] and v2['chest'] == ['raw_chest'] and v2['legs'] == ['raw_legs'] and v2['feet'] == ['raw_feet'], f'セーブ→読み直し：着ていた防具が戻り、形が出る {v2}')

        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: scale armor v2' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
