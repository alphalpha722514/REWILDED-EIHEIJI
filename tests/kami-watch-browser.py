#!/usr/bin/env python3
"""v0.69（P2 第3段階）要塞・小拠点のサル（見張り・巡回・通報・増援・見失った後の探索）と物資の再補充の確認（画面のない Chromium。数分）。

敵の更新は、ゲームを一時停止にして、決まった刻みで直接まわす（mutant-browser.py と同じやり方）。
- 巡回の道すじ・見張り台の梯子・物資の見張りの位置が歩ける
- 近づくと守りのサルが出る：初遭遇の前は要塞7（凶暴化だけ）・見張り場2、初遭遇の記録のあとは要塞10（変異3）・見張り場3
- 見張り台の見張り：台の上にいて、攻撃は届かない。18m・正面で見つけ、19m・横・バリケードのすぐ陰・家の陰では見つけない（高い所からはバリケードの上を見通す）
- 見つけると鳴いて知らせ（台の上）、少しして飛び降りる。近くの仲間3体が1.2秒おきに順に集まる
- 見失うと、最後に見た場所のまわりを約12秒探してから戻る。見張りは台に登り直し、巡回は道すじに戻る
- 変異したサル（物資の見張り）も、見失うと探して戻り、落ち着く
- 倒された守りは、遊んだ時間で10分たち、主人公が100m 以上離れているときに戻る
- 320m 離れると片付き、近づくと覚えた位置から出る。90m 先でも形の位置は合っている
- 物資置き場：1回目は大量・すぐには取れない・60分（遊んだ時間）で少し貯まる。保存・読み込みされる
- 光明寺に戻ると何も残らない／エラーなし（KEI truck の当たりは数えない：止めてある車の当たりは、ゲームが毎コマ付け外しするので、最初に数えた時に付いていないことがある。2026-11-19）

使い方：THREE_JS=…/three.min.js python3 tests/kami-watch-browser.py
"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.environ.get('KW_HTML', os.path.join(ROOT, 'index.html')), encoding='utf8').read()
KDATA = open(os.path.join(ROOT, 'data', 'kamishihi', 'kamishihi-map.js'), encoding='utf8').read()
MDATA = open(os.path.join(ROOT, 'data', 'models', 'mutant-monkey.js'), encoding='utf8').read()
HOOK = ("window.__w={get REG(){return REG},get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get stats(){return stats},get enemies(){return enemies},"
        "get KFA(){return KFA},get KF_ROUTES(){return KF_ROUTES},get KF_GARRISON(){return KF_GARRISON},get KF_LOOT(){return KF_LOOT},circles,oboxes,cgrid,"
        "regionTravel,saveGame,readSave,applySave,updateEnemies:dt=>updateEnemies(dt),kfGarrisonTick:(c,t)=>kfGarrisonTick(c,t),kfQueueTick:c=>kfQueueTick(c),kfSees:e=>kfSees(e),"
        "kfLOS:(...a)=>kfLOS(...a),damageEnemy:(...a)=>damageEnemy(...a),setState:(e,s)=>setState(e,s),f4Free:(...a)=>f4Free(...a),groundH:(x,z)=>groundH(x,z),"
        "allInter:()=>{ const L=[]; g4Interactables(L); return L; }};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

# 敵の更新を n 回（dt 秒ずつ）。0.25秒ごとに守りの出し入れと増援の順番を進める。主人公は倒れないよう体力を戻す
STEP = """async ([n, dt]) => { const W = window.__w, P = W.P, L = W.REG.live;
  for (let i = 0; i < n; i++) { W.S.time += dt; W.stats.time += dt; W.updateEnemies(dt); window.__acc = (window.__acc || 0) + dt;
    if (window.__acc >= 0.25) { window.__acc = 0; W.kfGarrisonTick(L, W.stats.time); W.kfQueueTick(L); }
    P.hp = P.maxHp; P.dead = false; P.iframe = 0;
    if (i % 90 === 0) await new Promise(r => setTimeout(r, 0)); } }"""
MEM = """() => { const W = window.__w, kf = W.REG.live.kf, out = {};
  for (const [k, e] of kf.mem) out[k] = {type: e.type, st: e.state, x: Math.round(e.x * 10) / 10, z: Math.round(e.z * 10) / 10, y: e.kfY || 0, join: e.kfJoin || null, look: e.kfLook == null ? null : Math.round(e.kfLook * 10) / 10, aggro: !!e.aggro};
  return out; }"""


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
        await pg.wait_for_timeout(800)
        base = await pg.evaluate("() => { const W = window.__w; let cells = 0; for (const a of W.cgrid.values()) cells += a.filter(o => o.tag !== 'truck').length; return {circles: W.circles.length, oboxes: W.oboxes.filter(o => o.tag !== 'truck').length, cells}; }")
        # 遠くの所（どの拠点からも 320m 以上）に着いてから止める
        await pg.evaluate("""async () => { const W = window.__w; W.prog.bossDefeated = true; W.prog.stage = 'cleared'; W.prog.chapter2.unlocked = true; W.prog.chapter2.progress.defenseComplete = true;
          await W.regionTravel('kamishihi', null, {force: true}); W.P.x = 5600; W.P.z = 900; W.S.mode = 'paused'; W.P.maxHp = 9999; W.P.hp = 9999; }""")
        # ---- 道すじ ----
        R = await pg.evaluate("""() => { const W = window.__w, bad = [];
          for (const [id, R] of Object.entries(W.KF_ROUTES)) { const p = R.p, n = R.loop ? p.length : p.length - 1;
            for (let i = 0; i < n; i++) { const a = p[i], b = p[(i + 1) % p.length], L = Math.hypot(b[0] - a[0], b[1] - a[1]);
              for (let t = 0; t <= L; t += 0.5) { const x = a[0] + (b[0] - a[0]) * t / L, z = a[1] + (b[1] - a[1]) * t / L; if (!W.f4Free(x, z, 0.5)) { bad.push([id, i, Math.round(x * 10) / 10, Math.round(z * 10) / 10]); break; } } } }
          for (const t of W.REG.live.kf.towers) { const x = t.x - Math.cos(t.yaw) * 2.4, z = t.z - Math.sin(t.yaw) * 2.4; if (!W.f4Free(x, z, 0.5)) bad.push(['ladder', t.site, x, z]); }
          if (!W.f4Free(7331.5, 1086, 0.5)) bad.push(['guard']); return bad; }""")
        check(not R, f'巡回の道すじ・見張り台の梯子の下・物資の見張りの位置が歩ける {R[:6]}')

        # ---- 出る（初遭遇の前） ----
        await pg.evaluate("() => { const W = window.__w; W.P.x = 7100; W.P.z = 1060; }")
        await pg.evaluate(STEP, [10, 1 / 30])
        m0 = await pg.evaluate(MEM)
        fort0 = [v for k, v in m0.items() if k[0] == 'f']
        a0 = [v for k, v in m0.items() if k[0] == 'a']
        check(len(fort0) == 7 and all(v['type'] == 'monkey' for v in fort0) and len(a0) == 2 and not any(k[0] == 'b' for k in m0),
              f'初遭遇の前：要塞は凶暴化したサル7・見張り場2（物資置き場は遠いので出ない）{len(fort0)}/{len(a0)}')
        await pg.evaluate("() => { window.__w.prog.chapter2.progress.mutantMet = true; }")
        for _ in range(30):
            await pg.evaluate(STEP, [8, 1 / 30])
            m1 = await pg.evaluate(MEM)
            if sum(1 for k in m1 if k[0] == 'f') == 10 and sum(1 for k in m1 if k[0] == 'a') == 3:
                break
            await pg.wait_for_timeout(200)
        fm = [v for k, v in m1.items() if k[0] == 'f']
        check(len(fm) == 10 and sum(1 for v in fm if v['type'] == 'mutant') == 3 and sum(1 for k in m1 if k[0] == 'a') == 3,
              f'初遭遇の記録のあと：要塞10（変異3＝3割）・見張り場3 {len(fm)}')
        W0 = await pg.evaluate("""() => { const W = window.__w, kf = W.REG.live.kf, e = kf.mem.get('f0'), t = kf.towers.filter(t => t.site === 'fort')[0]; const hp = e.hp; W.damageEnemy(e, 50, 'heavy', 0);
          return {y: e.kfY, onTower: Math.hypot(e.x - t.x, e.z - t.z) < 0.1, hpSame: e.hp === hp, modelY: Math.round((e.m.g.position.y - W.groundH(e.x, e.z)) * 10) / 10}; }""")
        check(W0['y'] > 4 and W0['onTower'] and W0['hpSame'], f'見張りは見張り台の上にいて、攻撃は届かない {W0}')

        # ---- 見つける・見つけない（見張り f0：西の見張り台・西向き） ----
        S1 = await pg.evaluate("""() => { const W = window.__w, P = W.P, e = W.REG.live.kf.mem.get('f0'), t = {x: e.x, z: e.z}, out = {};
          const at = (x, z, rot) => { P.x = x; P.z = z; e.rot = rot; e.kfLosAt = -9; return W.kfSees(e); };
          out.d15 = at(t.x - 15, t.z, -Math.PI / 2); out.d17 = at(t.x - 17, t.z, -Math.PI / 2); out.d19 = at(t.x - 19, t.z, -Math.PI / 2);
          out.side = at(t.x - 12, t.z, 0); // 南を向いているときに西 12m（横は 18m の3分の1）
          out.hug = at(7249, t.z, -Math.PI / 2); // 西の壁のすぐ外（1m）：壁の上より視線が低い
          out.wallX = W.REG.live.kf.walls.some(w => w[4] === 'fort' && Math.abs(w[0] - 7250) < 0.6 && Math.abs(w[2] - 7250) < 0.6 && Math.min(w[1], w[3]) < t.z && Math.max(w[1], w[3]) > t.z);
          out.house = W.kfLOS(7285, 1066, 2, 7330, 1066, 2); // 家（22）を横切る
          return out; }""")
        check(S1['d15'] and S1['d17'] and not S1['d19'], f'見張りは正面 18m で見つける（15m・17m は見つけ、19m は見つけない）{S1}')
        check(not S1['side'], '横は短い距離でしか見つけない（12m では見つけない）')
        check(S1['wallX'] and not S1['hug'], 'バリケードのすぐ陰（壁の外 1m）は見つけない（壁越しに見つけない）')
        check(not S1['house'], '家の陰は見えない')

        # ---- 見つけて知らせる・増援が順に集まる ----
        await pg.evaluate("""() => { const W = window.__w, e = W.REG.live.kf.mem.get('f0'); W.P.x = e.x - 13; W.P.z = e.z; e.kf.look = -Math.PI / 2; W.REG.live.kf.alarms = 0; }""")
        seen = {}
        for i in range(40):
            await pg.evaluate(STEP, [6, 1 / 30])
            m = await pg.evaluate(MEM)
            seen[i] = m['f0']['st']
            if m['f0']['st'] == 'kfcall' and 'call' not in seen:
                seen['call'] = i
            if m['f0']['y'] == 0 and 'down' not in seen and 'call' in seen:
                seen['down'] = i
        m2 = await pg.evaluate(MEM)
        joins = sorted([(v['join'], k) for k, v in m2.items() if v['join'] is not None])
        alarms = await pg.evaluate("() => window.__w.REG.live.kf.alarms")
        gaps = [round(joins[i + 1][0] - joins[i][0], 2) for i in range(len(joins) - 1)]
        print('見張り：', {k: v for k, v in seen.items() if not isinstance(k, int)}, '集まった：', joins, '間', gaps)
        check('call' in seen and 'down' in seen and seen['down'] > seen['call'], '見張りは見つけると台の上で鳴いて知らせ、少しして飛び降りる')
        check(alarms >= 1 and len(joins) == 3 and all(1.0 <= g <= 1.5 for g in gaps), f'近くの仲間3体が約1.2秒おきに順に集まる（{len(joins)}体・間 {gaps}）')

        # ---- 見失った後：探してから戻る ----
        await pg.evaluate("() => { const W = window.__w; W.P.x = 7120; W.P.z = 1150; }")  # 遠くの見えない所へ
        hist = {}
        for i in range(60):
            await pg.evaluate(STEP, [30, 1 / 30])
            m = await pg.evaluate(MEM)
            for k, v in m.items():
                h = hist.setdefault(k, {'st': set(), 'look': 0})
                h['st'].add(v['st'])
                if v['look']:
                    h['look'] = max(h['look'], v['look'])
            if i > 40 and all(v['st'] in ('idle',) for v in m.values()):
                break
        m3 = await pg.evaluate(MEM)
        searched = [k for k, h in hist.items() if ('search' in h['st'] or 'kfsearch' in h['st'])]
        looks = {k: hist[k]['look'] for k in searched}
        print('探した：', looks, '今：', {k: v['st'] for k, v in m3.items() if k[0] == 'f'})
        check(searched and all(11.0 <= l <= 12.6 for l in looks.values()), f'見失うと、最後に見た場所のまわりを約12秒探す（1秒ごとに見た最大）{looks}')
        check(all(v['st'] == 'idle' for k, v in m3.items() if k[0] == 'f') and m3['f0']['y'] > 4, f'探し終えると持ち場へ戻り、見張りは台に登り直す（f0 の高さ {m3["f0"]["y"]}）')
        pos1 = await pg.evaluate("() => { const e = window.__w.REG.live.kf.mem.get('f3'); return [e.x, e.z]; }")
        await pg.evaluate(STEP, [150, 1 / 30])
        pos2 = await pg.evaluate("() => { const e = window.__w.REG.live.kf.mem.get('f3'); return [e.x, e.z, e.m.g.position.x, e.m.g.position.z]; }")
        moved = ((pos2[0] - pos1[0]) ** 2 + (pos2[1] - pos1[1]) ** 2) ** 0.5
        check(moved > 1.0 and abs(pos2[2] - pos2[0]) < 0.01 and abs(pos2[3] - pos2[1]) < 0.01, f'巡回に戻って歩く（5秒で {moved:.1f}m）。遠く（90m 先）でも形の位置は合っている')

        # ---- 変異したサル（物資の見張り）：見失うと探して戻る ----
        G = await pg.evaluate("""() => { const W = window.__w, e = W.REG.live.kf.mem.get('f9'); W.P.x = e.x - 8; W.P.z = e.z; e.rot = Math.atan2(W.P.x - e.x, W.P.z - e.z); e.kfLosAt = -9; return {st: e.state, home: e.home}; }""")
        await pg.evaluate(STEP, [60, 1 / 30])
        g1 = await pg.evaluate("() => { const e = window.__w.REG.live.kf.mem.get('f9'); return {st: e.state, aggro: e.aggro}; }")
        await pg.evaluate("() => { const W = window.__w; W.P.x = 7120; W.P.z = 1150; }")
        gst = set()
        for i in range(50):
            await pg.evaluate(STEP, [30, 1 / 30])
            s = await pg.evaluate("() => { const e = window.__w.REG.live.kf.mem.get('f9'); return [e.state, Math.hypot(e.x - e.home.x, e.z - e.home.z), e.aggro]; }")
            gst.add(s[0])
            if i > 20 and s[0] == 'idle':
                break
        check(g1['aggro'] and 'kfsearch' in gst and 'kfreturn' in gst and s[0] == 'idle' and s[1] < 2 and not s[2], f'変異したサルも見失うと探し、持ち場に戻って落ち着く {g1} → {sorted(gst)}')

        # ---- 倒された守りが戻る ----
        D = await pg.evaluate("""() => { const W = window.__w, e = W.REG.live.kf.mem.get('f3'); W.P.x = 7290; W.P.z = 1150; e.hp = 1; W.damageEnemy(e, 999, 'heavy', 0); return e.state; }""")
        await pg.evaluate(STEP, [100, 1 / 30])
        d1 = await pg.evaluate("() => { const W = window.__w; return {t: Math.round(W.prog.kami.fm.f3 - W.stats.time), has: W.REG.live.kf.mem.has('f3')}; }")
        await pg.evaluate("() => { window.__w.stats.time += 600; }")
        await pg.evaluate(STEP, [20, 1 / 30])
        d2 = await pg.evaluate("() => window.__w.REG.live.kf.mem.has('f3')")
        await pg.evaluate("() => { const W = window.__w; W.P.x = 7120; W.P.z = 1150; }")
        await pg.evaluate(STEP, [20, 1 / 30])
        d3 = await pg.evaluate("() => window.__w.REG.live.kf.mem.has('f3')")
        check(D == 'dead' and not d1['has'] and 590 < d1['t'] <= 600 and not d2 and d3, f'倒された守りは10分（遊んだ時間）戻らず、主人公が近い間も戻らない。離れると戻る {d1}')

        # ---- 320m 離れると片付き、近づくと覚えた位置から出る ----
        before = await pg.evaluate("() => { const e = window.__w.REG.live.kf.mem.get('f6'); return [e.x, e.z]; }")
        await pg.evaluate("() => { const W = window.__w; W.P.x = 6900; W.P.z = 1300; }")
        await pg.evaluate(STEP, [20, 1 / 30])
        gone = await pg.evaluate("() => [...window.__w.REG.live.kf.mem.keys()].filter(k => k[0] === 'f').length")
        await pg.evaluate("() => { const W = window.__w; W.P.x = 7120; W.P.z = 1150; }")
        for _ in range(20):
            await pg.evaluate(STEP, [8, 1 / 30])
            if await pg.evaluate("() => [...window.__w.REG.live.kf.mem.keys()].filter(k => k[0] === 'f').length === 10"):
                break
            await pg.wait_for_timeout(200)
        after = await pg.evaluate("() => { const e = window.__w.REG.live.kf.mem.get('f6'); return [e.x, e.z]; }")
        jump = ((after[0] - before[0]) ** 2 + (after[1] - before[1]) ** 2) ** 0.5
        check(gone == 0 and jump < 3.0, f'320m 離れると片付き、近づくと覚えた位置の近くから出る（ずれ {jump:.2f}m）')

        # ---- 物資置き場 ----
        await pg.evaluate("() => { window.__w.S.mode = 'playing'; }")
        S2 = await pg.evaluate("""() => { const W = window.__w, st = W.REG.live.kf.stashes.find(s => s.id === 'fort'); W.P.x = st.fx; W.P.z = st.fz;
          const snap = () => ({wood: W.inv.wood || 0, stone: W.inv.stone || 0, iron: W.inv.iron || 0, rope: W.inv.rope || 0, straw: W.inv.straw || 0, mutScale: W.inv.mutScale || 0});
          const diff = (a, b) => Object.fromEntries(Object.keys(a).map(k => [k, b[k] - a[k]]));
          const take = () => { const L = W.allInter().filter(o => /物資/.test(o.label)); if (L[0]) L[0].act(); return L[0] && L[0].label; };
          const s0 = snap(); const l1 = take(); const s1 = snap(); const l2 = take(); const s2 = snap(); W.stats.time += 3600; const l3 = take(); const s3 = snap();
          W.saveGame(); const saved = JSON.parse(localStorage.getItem('eiheiji_vs_beasts_v010')).kami.st; W.applySave(W.readSave());
          return {l1, first: diff(s0, s1), l2, second: diff(s1, s2), l3, refill: diff(s2, s3), saved, loaded: W.prog.kami.st}; }""")
        print('物資：', S2)
        check(S2['first'] == {'wood': 20, 'stone': 12, 'iron': 6, 'rope': 4, 'straw': 6, 'mutScale': 3}, f'要塞の物資：1回目は大量（木材20・石12・屑鉄6・縄4・藁6・変異した鱗3）')
        check(all(v == 0 for v in S2['second'].values()) and 'また貯まるまで' in (S2['l2'] or ''), f'すぐには取れない（{S2["l2"]}）')
        check(S2['refill'] == {'wood': 6, 'stone': 4, 'iron': 2, 'rope': 0, 'straw': 0, 'mutScale': 1}, '60分（遊んだ時間）たつと少し貯まっている（木材6・石4・屑鉄2・鱗1）')
        check(S2['saved'].get('fort', {}).get('n') == 2 and S2['loaded'].get('fort', {}).get('n') == 2, '持ち出した回数と時刻が保存・読み込みされる')

        await pg.evaluate("async () => { await window.__w.regionTravel('komyoji', null, {force: true}); }")
        await pg.wait_for_timeout(500)
        end = await pg.evaluate("() => { const W = window.__w; let cells = 0; for (const a of W.cgrid.values()) cells += a.filter(o => o.tag !== 'truck').length; return {circles: W.circles.length, oboxes: W.oboxes.filter(o => o.tag !== 'truck').length, cells, kami: W.enemies.filter(e => !e.removed && e.x > 4000).length}; }")
        check(end['circles'] == base['circles'] and end['oboxes'] == base['oboxes'] and end['cells'] == base['cells'] and end['kami'] == 0, f'光明寺に戻ると何も残らない {end}')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: kamishihi watch' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
