#!/usr/bin/env python3
"""v0.71（P2 作業E 第2段階）スズキの戦いの確認（画面のない Chromium。数分）。

ゲームを一時停止にして、スズキと敵の更新を決まった刻みで直接まわす。主人公は動かさず、体力を戻し続ける。
- 敵がスズキを相手にできる（相手がスズキの敵の攻撃はスズキに当たり、主人公には当たらない）。敵が考えた後、主人公の位置・状態は元どおり
- 相手の切り替えは2秒に1回まで。倒れたスズキは相手にされない
- 同時に攻撃してくる獣は相手ごとに2体まで（主人公に2体攻撃中でも、スズキを相手にする獣は攻撃できる）
- 近くにいるだけの（主人公を見つけていない）獣とは戦わない。主人公を見つけた獣とは戦う
- 蹴り3種：ローキック（18）・後ろ回し蹴り（45）・飛び蹴り（4〜8m 先へ跳ぶ）を使い分ける。外れたら臭いは付かない
- 足の臭い：当たると2秒、当たるたびに2秒足す（最大10秒）。毎秒6。ひるませず押し返さない。ヌシには付かない
- 受けるダメージは2割減。体力54以下では敵から離れて戦う。体力0で倒れる
- 要塞の見張りは、スズキを主人公の7割（12.6m）で見つける
- エラーなし

使い方：THREE_JS=…/three.min.js python3 tests/suzuki-combat-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('SZ_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
KDATA = open(os.path.join(ROOT, 'data', 'kamishihi', 'kamishihi-map.js'), encoding='utf8').read()
MDATA = open(os.path.join(ROOT, 'data', 'models', 'mutant-monkey.js'), encoding='utf8').read()
HOOK = ("window.__w={get REG(){return REG},get P(){return P},get S(){return S},get prog(){return prog},get stats(){return stats},get enemies(){return enemies},"
        "get SZ(){return SZ},get SZK(){return SZK},get SZF(){return SZF},get TGV(){return TGV},get bossE(){return bossE},get KFA(){return KFA},"
        "regionTravel,updateSuzuki:dt=>updateSuzuki(dt),updateEnemies:dt=>updateEnemies(dt),szJoin:()=>szJoin(),szOrder:k=>szOrder(k),szPick:e=>szPick(e),"
        "szKickHit:k=>szKickHit(k),szKickStart:(i,e)=>szKickStart(i,e),tgvBegin:()=>tgvBegin(),tgvEnd:()=>tgvEnd(),kfSees:e=>kfSees(e),attackSlotFree:e=>attackSlotFree(e),"
        "setState:(e,s)=>setState(e,s),damageEnemy:(...a)=>damageEnemy(...a),szFree:(...a)=>szFree(...a),kfGarrisonTick:(c,t)=>kfGarrisonTick(c,t),kfQueueTick:c=>kfQueueTick(c)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

# n コマまわす（1/30 秒）。記録：蹴りの種類と回数・スズキと主人公の体力の減り・主人公の位置がずれたか
STEP = """async ([n, keepSz]) => { const W = window.__w, P = W.P, SZ = W.SZ, dt = 1 / 30; const kicks = {}, px = P.x, pz = P.z; let szLost = 0, pLost = 0, leak = 0, last = null;
  for (let i = 0; i < n; i++) { W.S.time += dt; W.stats.time += dt; const sh = SZ.hp, ph = P.hp; W.updateSuzuki(dt); W.updateEnemies(dt);
    if (SZ.hp < sh) szLost += sh - SZ.hp; if (P.hp < ph) pLost += ph - P.hp; if (P.x !== px || P.z !== pz || W.TGV.on) leak++;
    if (SZ.kick && SZ.kick !== last) { kicks[SZ.kick.id] = (kicks[SZ.kick.id] || 0) + 1; } last = SZ.kick;
    P.hp = P.maxHp; P.dead = false; if (keepSz) SZ.hp = SZ.maxHp;
    if (i % 60 === 0) await new Promise(r => setTimeout(r, 0)); }
  return {kicks, szLost: Math.round(szLost), pLost: Math.round(pLost), leak}; }"""
# 戦わせる獣を1体だけ近くに置き、ほかは遠くへ
PUT = """([type, x, z, st]) => { const W = window.__w; let e = null; for (const o of W.enemies) { if (o.removed || o.state === 'dead' || o.type === 'boss') continue; if (!e && o.type === type) e = o; else { o.x += 3000; o.home = {x: o.x, z: o.z}; } }
  if (!e) return null; e.x = x; e.z = z; e.home = {x, z}; e.hp = e.maxHp; e.smellT = 0; e.szT = false; e.szSw = -99; e.hitP = -99; e.hitS = -99; W.setState(e, st); window.__e = e; return {type: e.type, hp: e.hp}; }"""


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
            elif 'mutant-monkey.js' in u: await r.fulfill(body=MDATA, content_type='application/javascript')
            elif 'kamishihi-map.js' in u: await r.fulfill(body=KDATA, content_type='application/javascript')
            elif u.startswith('http://game.local'): await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            else: await r.abort()
        await pg.route('**/*', route)
        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function('window.__w', timeout=300000)
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(1000)
        # 光明寺の外の開けた所（拠点・境内の外。獣が相手を見失わない所）
        spot = await pg.evaluate("""() => { const W = window.__w; W.S.mode = 'paused'; W.P.maxHp = 9999; W.P.hp = 9999;
          for (let z = -60; z > -300; z -= 6) for (let x = 60; x < 300; x += 6) { let okk = true; for (let a = 0; a < 8 && okk; a++) for (const r of [0, 4, 8, 12]) if (!W.szFree(x + Math.sin(a) * r, z + Math.cos(a) * r, 1)) { okk = false; break; }
            if (okk) return [x, z]; } return null; }""")
        check(spot is not None, f'戦いを試す開けた所 {spot}')
        X, Z = spot
        await pg.evaluate("([x, z]) => { const W = window.__w; W.P.x = x; W.P.z = z; W.P.facing = 0; W.szJoin(); W.SZ.x = x + 3; W.SZ.z = z - 1; }", spot)

        # ---- 近くにいるだけの獣とは戦わない ----
        await pg.evaluate(PUT, ['boar', X + 6, Z + 6, 'idle'])
        await pg.evaluate("() => { const e = window.__e; e.rot = Math.atan2(e.x - window.__w.P.x, e.z - window.__w.P.z); }")  # 背を向ける
        r0 = await pg.evaluate("""async () => { const W = window.__w, e = window.__e; let tgt = 0; for (let i = 0; i < 30; i++) { W.S.time += 1 / 30; W.updateSuzuki(1 / 30); if (W.SZ.tgt) tgt++; } return {tgt, st: e.state}; }""")
        check(r0['tgt'] == 0, f'主人公を見つけていない獣とは戦わない {r0}')

        # ---- 敵がスズキを相手にする・主人公の位置が漏れない ----
        await pg.evaluate(PUT, ['boar', X + 3, Z + 9, 'chase'])
        r1 = await pg.evaluate("""() => { const W = window.__w, e = window.__e; W.SZ.x = e.x; W.SZ.z = e.z - 2.5; W.P.x = e.x - 20; W.P.z = e.z - 10; return W.szPick(e); }""")
        S1 = await pg.evaluate(STEP, [240, True])
        r2 = await pg.evaluate("() => ({szT: window.__e.szT, tgv: window.__w.TGV.on})")
        check(r1 and r2['szT'] and S1['szLost'] > 0 and S1['pLost'] == 0 and S1['leak'] == 0, f'近いスズキを相手にした獣の攻撃はスズキに当たり、主人公には当たらない。考えた後の主人公の位置は元どおり {S1} {r2}')
        check(S1['kicks'].get('low', 0) + S1['kicks'].get('spin', 0) > 0, f'スズキは襲ってきた獣を蹴る {S1["kicks"]}')
        # 2秒に1回まで
        r3 = await pg.evaluate("""() => { const W = window.__w, e = window.__e; e.szT = true; e.szSw = W.S.time; W.setState(e, 'chase'); W.P.x = e.x + 1; W.P.z = e.z; W.SZ.x = e.x + 15; W.SZ.z = e.z;
          const a = W.szPick(e); W.S.time += 2.1; const b = W.szPick(e); return {a, b}; }""")
        check(r3['a'] and not r3['b'], f'相手の切り替えは2秒に1回まで（すぐには変えず、2秒後に近い主人公へ）{r3}')

        # ---- 同時攻撃は相手ごとに2体まで ----
        r4 = await pg.evaluate("""() => { const W = window.__w, L = W.enemies.filter(o => !o.removed && o.state !== 'dead' && o.type !== 'boss').slice(0, 4); if (L.length < 3) return null;
          const keep = L.map(o => [o.state, o.szT]); W.setState(L[0], 'wind'); L[0].szT = false; W.setState(L[1], 'wind'); L[1].szT = false; L[2].szT = true; L[2].mode = 'field'; const forSz = W.attackSlotFree(L[2]); L[2].szT = false; const forP = W.attackSlotFree(L[2]);
          L.forEach((o, i) => { W.setState(o, keep[i][0]); o.szT = keep[i][1]; }); return {forSz, forP}; }""")
        check(r4 is not None and r4['forSz'] and not r4['forP'], f'主人公に2体が攻撃中でも、スズキを相手にする獣は攻撃できる（主人公には3体目は来ない）{r4}')

        # ---- 蹴り3種・使い分け（イノシシ・サル）----
        await pg.evaluate("([x, z]) => { const W = window.__w; W.P.x = x; W.P.z = z; W.SZ.x = x + 1.5; W.SZ.z = z - 1; W.SZ.cd = {low: 0, spin: 0, jump: 0}; W.SZ.hp = W.SZ.maxHp; }", spot)
        await pg.evaluate(PUT, ['boar', X + 2, Z + 7.5, 'chase'])
        await pg.evaluate("() => { const W = window.__w, e = window.__e; e.hitP = W.S.time; e.maxHp = 5000; e.hp = 5000; }")
        S2 = await pg.evaluate(STEP, [600, True])
        check(all(S2['kicks'].get(k, 0) > 0 for k in ('low', 'spin', 'jump')), f'ローキック・後ろ回し蹴り・飛び蹴りを使い分ける（20秒）{S2["kicks"]}')

        # ---- 一撃の威力・臭い ----
        r5 = await pg.evaluate("""() => { const W = window.__w, SZ = W.SZ, e = window.__e; W.setState(e, 'chase'); e.hp = 5000; e.smellT = 0; e.smellAcc = 0; SZ.x = e.x; SZ.z = e.z - e.r - SZ.r - 0.8; SZ.rot = 0; SZ.down = false;
          const h0 = e.hp, x0 = e.x, z0 = e.z; const k = {id: 'low', K: W.SZK.low, e}; const hit = W.szKickHit(k); const d1 = h0 - e.hp, s1 = e.smellT, moved = Math.hypot(e.x - x0, e.z - z0);
          const h1 = e.hp; const hit2 = W.szKickHit({id: 'spin', K: W.SZK.spin, e}); const d2 = h1 - e.hp, s2 = e.smellT;
          for (let i = 0; i < 6; i++) { SZ.x = e.x; SZ.z = e.z - e.r - SZ.r - 0.8; W.szKickHit({id: 'low', K: W.SZK.low, e}); } const s3 = e.smellT;
          return {hit, d1, s1, moved: Math.round(moved * 100) / 100, hit2, d2, s2, s3}; }""")
        check(r5['hit'] and r5['d1'] == 18 and r5['moved'] < 0.01, f'ローキック：18・押し返さない {r5}')
        check(r5['hit2'] and r5['d2'] >= 45, f'後ろ回し蹴り：45（体勢が崩れていれば多め）{r5["d2"]}')
        check(abs(r5['s1'] - 2) < 1e-6 and abs(r5['s2'] - 4) < 1e-6 and abs(r5['s3'] - 10) < 1e-6, f'臭い：初めは2秒、当たるたびに2秒足し、最大10秒 {r5["s1"]}/{r5["s2"]}/{r5["s3"]}')
        r6 = await pg.evaluate("""async () => { const W = window.__w, e = window.__e, dt = 1 / 30; W.SZ.down = true; e.smellT = 2; e.smellAcc = 0; e.hp = 5000; W.setState(e, 'stun'); e.stunT = 99; const x0 = e.x, z0 = e.z, h0 = e.hp, st0 = e.state, fl0 = e.flinchT;
          for (let i = 0; i < 75; i++) { W.S.time += dt; W.updateSuzuki(dt); } W.SZ.down = false; return {dmg: h0 - e.hp, moved: Math.round(Math.hypot(e.x - x0, e.z - z0) * 100) / 100, st: e.state, st0, flinch: e.flinchT !== fl0, left: e.smellT}; }""")
        check(r6['dmg'] == 12 and r6['moved'] < 0.01 and r6['st'] == r6['st0'] and not r6['flinch'] and r6['left'] == 0, f'臭い2秒＝毎秒6で12。ひるまず押し返さない {r6}')
        r7 = await pg.evaluate("""() => { const W = window.__w, SZ = W.SZ, e = window.__e; e.smellT = 0; SZ.x = e.x; SZ.z = e.z - e.r - SZ.r - 3.5; SZ.rot = 0; const h0 = e.hp; const hit = W.szKickHit({id: 'low', K: W.SZK.low, e}); return {hit, dmg: h0 - e.hp, smell: e.smellT}; }""")
        check(not r7['hit'] and r7['dmg'] == 0 and r7['smell'] == 0, f'外れたら傷も臭いも付かない {r7}')
        r8 = await pg.evaluate("""() => { const W = window.__w, SZ = W.SZ, b = W.bossE; if (!b) return null; const keep = {x: b.x, z: b.z, hp: b.hp, st: b.state}; SZ.x = b.x; SZ.z = b.z - b.r - SZ.r - 0.8; SZ.rot = 0; b.smellT = 0;
          const hit = W.szKickHit({id: 'low', K: W.SZK.low, e: b}); const out = {hit, smell: b.smellT || 0, dmg: keep.hp - b.hp}; b.hp = keep.hp; b.x = keep.x; b.z = keep.z; W.setState(b, keep.st); return out; }""")
        check(r8 is not None and r8['hit'] and r8['dmg'] > 0 and r8['smell'] == 0, f'ヌシ（ボス）には臭いが付かない（蹴りは当たる）{r8}')

        # ---- 受けるダメージ2割減・体力が少ないとき・倒れる ----
        r9 = await pg.evaluate("""() => { const W = window.__w, SZ = W.SZ, e = window.__e; SZ.hp = SZ.maxHp; SZ.down = false; W.tgvBegin(); const h = SZ.hp; const r = (function(){ return true; })(); W.tgvEnd();
          const h0 = SZ.hp; SZ.hurt(30, e); return {lost: h0 - SZ.hp}; }""")
        check(r9['lost'] == 24, f'受けるダメージは2割減（30→24）{r9}')
        await pg.evaluate("([x, z]) => { const W = window.__w; W.P.x = x; W.P.z = z; W.SZ.x = x + 1; W.SZ.z = z + 2; W.SZ.hp = 40; W.SZ.stagger = 0; W.SZ.kick = null; }", spot)
        await pg.evaluate(PUT, ['boar', X + 1, Z + 5, 'chase'])
        await pg.evaluate("() => { const W = window.__w, e = window.__e; e.hitP = W.S.time; e.maxHp = 5000; e.hp = 5000; }")
        r10 = await pg.evaluate("""async () => { const W = window.__w, SZ = W.SZ, e = window.__e, dt = 1 / 30; let minD = 99, jumps = 0, n = 0; for (let i = 0; i < 300; i++) { W.S.time += dt; SZ.hp = 40; W.updateSuzuki(dt); W.updateEnemies(dt); W.P.hp = W.P.maxHp;
            if (SZ.kick && SZ.kick.id === 'jump') jumps++; if (i > 60) { minD = Math.min(minD, Math.hypot(SZ.x - e.x, SZ.z - e.z) - SZ.r - e.r); n++; } if (i % 60 === 0) await new Promise(r => setTimeout(r, 0)); } return {jumps, avgFar: n}; }""")
        FAR = """async ([hp]) => { const W = window.__w, SZ = W.SZ, e = window.__e, dt = 1 / 30; let far = 0, n = 0, sum = 0; for (let i = 0; i < 300; i++) { W.S.time += dt; SZ.hp = hp; W.updateSuzuki(dt); W.updateEnemies(dt); W.P.hp = W.P.maxHp;
            const d = Math.hypot(SZ.x - e.x, SZ.z - e.z) - SZ.r - e.r; if (d > 3) far++; sum += d; n++; if (i % 60 === 0) await new Promise(r => setTimeout(r, 0)); } return {far: Math.round(far / n * 100), avg: Math.round(sum / n * 10) / 10}; }"""
        lowHp = await pg.evaluate(FAR, [40])
        normHp = await pg.evaluate(FAR, [180])
        check(r10['jumps'] == 0 and lowHp['far'] >= normHp['far'] + 25 and lowHp['avg'] > normHp['avg'] + 1.5,
              f'体力54以下：敵から離れて戦い、飛び蹴りはしない（3m より離れている時間：体力40 {lowHp}・体力180 {normHp}）{r10}')
        r11 = await pg.evaluate("""() => { const W = window.__w, SZ = W.SZ, e = window.__e; SZ.hp = 10; SZ.down = false; SZ.hurt(40, e); const down = SZ.down; e.szSw = -99; const pick = W.szPick(e); return {down, hp: SZ.hp, pick, szT: e.szT}; }""")
        check(r11['down'] and r11['hp'] == 0 and not r11['pick'], f'体力0で倒れ、倒れたスズキは相手にされない {r11}')
        await pg.evaluate("() => { const SZ = window.__w.SZ; SZ.down = false; SZ.hp = SZ.maxHp; }")

        # ---- 要塞の見張り：スズキは12.6m ----
        await pg.evaluate("""async () => { const W = window.__w; W.prog.bossDefeated = true; W.prog.stage = 'cleared'; W.prog.chapter2.unlocked = true; W.prog.chapter2.progress.defenseComplete = true; W.S.mode = 'playing';
          await W.regionTravel('kamishihi', null, {force: true}); W.S.mode = 'paused'; W.P.x = 7100; W.P.z = 1060; W.kfGarrisonTick(W.REG.live, W.stats.time); }""")
        await pg.wait_for_timeout(500)
        await pg.evaluate("async () => { const W = window.__w; for (let i = 0; i < 20; i++) { W.S.time += 1 / 30; W.updateEnemies(1 / 30); W.kfGarrisonTick(W.REG.live, W.stats.time); } }")
        r12 = await pg.evaluate("""() => { const W = window.__w, P = W.P, SZ = W.SZ, e = W.REG.live.kf.mem.get('f0'); if (!e) return null; P.x = e.x - 40; P.z = e.z; SZ.region = W.REG.cur; const at = d => { SZ.x = e.x - d; SZ.z = e.z; e.rot = -Math.PI / 2; e.kfLosAt = -9; W.tgvBegin(); const v = W.kfSees(e); W.tgvEnd(); return v; };
          const pl = d => { P.x = e.x - d; P.z = e.z; e.rot = -Math.PI / 2; e.kfLosAt = -9; const v = W.kfSees(e); P.x = e.x - 40; return v; };
          return {s12: at(12), s13: at(13.2), p17: pl(17)}; }""")
        check(r12 is not None and r12['s12'] and not r12['s13'] and r12['p17'], f'要塞の見張りは、スズキを12.6m（主人公の7割）で見つける（12m は見つけ、13.2m は見つけない。主人公は17m で見つける）{r12}')
        r13 = await pg.evaluate("""async () => { const W = window.__w, P = W.P, SZ = W.SZ, kf = W.REG.live.kf, e = kf.mem.get('f0'), dt = 1 / 30; if (!e) return null;
          P.x = e.x - 45; P.z = e.z + 30; SZ.x = e.x - 11; SZ.z = e.z; SZ.order = 'wait'; SZ.wx = SZ.x; SZ.wz = SZ.z; SZ.hp = SZ.maxHp; e.kf.look = -Math.PI / 2; e.rot = -Math.PI / 2; e.szSw = -99; let call = false, joins = 0, hitSz = 0;
          for (let i = 0; i < 240; i++) { W.S.time += dt; W.stats.time += dt; const h = SZ.hp; W.updateSuzuki(dt); W.updateEnemies(dt); if (i % 8 === 0) { W.kfGarrisonTick(W.REG.live, W.stats.time); W.kfQueueTick(W.REG.live); } P.hp = P.maxHp; SZ.hp = Math.max(SZ.hp, 100);
            if (e.state === 'kfcall') call = true; let j = 0; for (const [, o] of kf.mem) if (o.kfJoin) j++; joins = Math.max(joins, j); if (i % 60 === 0) await new Promise(r => setTimeout(r, 0)); }
          return {call, joins, alarm: (kf.run.fort || {}).alarmAt > 0, szT: e.szT}; }""")
        check(r13 is not None and r13['call'] and r13['alarm'] and r13['joins'] >= 2, f'見張りがスズキを見つけると、ふだんどおり鳴いて知らせる（通報・増援が動く）{r13}')
        await pg.evaluate("async () => { const W = window.__w; W.S.mode = 'playing'; await W.regionTravel('komyoji', null, {force: true}); }")

        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: suzuki combat (stage 2)' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
