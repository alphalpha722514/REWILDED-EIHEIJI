#!/usr/bin/env python3
"""v0.67（P2）上志比の獣・採集・伐採の確認（画面のない Chromium。数分かかる）。

本物の上志比のデータで、
- 獣（クマ4・イノシシ8・シカ3・イタチ2・凶暴化したサル3）と町の群れ4つ・採集場所が、歩ける所に置かれる（数は暫定）
- 近づくと獣が出て、遠く離れると片付く。倒すと決まった時間（遊んだ時間）まで戻らない。往復・セーブ・ロードでも戻らない
- 群れは初遭遇の前は凶暴化2体。初遭遇の記録（またはテストの解禁）があると変異したサルが加わる。全滅から5分で戻る
- 石・藁・竹・薪・畑・岩・がれきを取れる。取った物は往復・セーブ・ロードで戻らず、時間がたつと戻る（がれきは戻らない）
- 上志比の木を切って、枝を払い、丸太をその場で割れる。丸太は運べない。上志比を出ると倒木・丸太は消え、切った木は切ったまま
- 光明寺の当たり判定・獣・セーブの形が変わらない／エラーなし
を確かめる。KAMI_SHOTS=出力フォルダ で、置き場所の地図と画面を撮る。

使い方：THREE_JS=…/three.min.js python3 tests/kami-wild-browser.py
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
SHOTS = os.environ.get('KAMI_SHOTS')
HOOK = ("window.__k={get REG(){return REG},get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get stats(){return stats},get enemies(){return enemies},get F4(){return F4},"
        "circles,oboxes,boxes,cgrid,scene,renderer,get KW(){return KW},get KW_TEST(){return KW_TEST},get KOMYOJI_EAST_ARRIVE(){return KOMYOJI_EAST_ARRIVE},regionTravel,saveGame,readSave,applySave,interactables,f4Hit,f4FindTarget,damageEnemy,toolGain,"
        "get DAMAGED(){return DAMAGED},kamiTick,kamiNodesUpdate,kamiReach,kamiCls,setState,f4Free,kamiMutantOK,allInter:()=>{ const L=[]; g4Interactables(L); return L; },openMap:()=>{ if(S.mode==='playing') openMap(); else { sizeMap(); drawMap(); } }};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

TICK = """async (n) => { const K = window.__k; for (let i = 0; i < n; i++) { K.REG.live.kw.t = 0; K.kamiTick(K.REG.live, 0.25); await new Promise(r => setTimeout(r, 0)); } }"""
FRAMES = """async (n) => { for (let i = 0; i < n; i++) await new Promise(r => requestAnimationFrame(r)); }"""


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
        await pg.wait_for_function('window.__k', timeout=300000)
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await pg.wait_for_timeout(1500)
        base = await pg.evaluate("""() => { const K = window.__k; let cells = 0; for (const a of K.cgrid.values()) cells += a.length;
          return {circles: K.circles.length, oboxes: K.oboxes.length, cells, kids: K.scene.children.length, enemies: K.enemies.filter(e => !e.removed).length, dmg: K.DAMAGED.length}; }""")
        # 開放して上志比へ（防衛戦の後）。道具を持たせる
        await pg.evaluate("""async () => { const K = window.__k; K.prog.bossDefeated = true; K.prog.stage = 'cleared'; K.prog.chapter2.unlocked = true; K.prog.chapter2.progress.defenseComplete = true;
          K.toolGain('hammerStone'); K.prog.arms.axeIron = 140; await K.regionTravel('kamishihi', null, {force: true}); }""")
        await pg.wait_for_timeout(800)
        A = await pg.evaluate("""() => { const K = window.__k, L = K.REG.live, kw = L.kw, cnt = {}, nodes = {};
          for (const s of kw.sp) cnt[s.type] = (cnt[s.type] || 0) + 1; for (const n of kw.nodes) nodes[n.k] = (nodes[n.k] || 0) + (n.k === 'food' && n.chest ? 0 : 1);
          nodes.chest = kw.nodes.filter(n => n.chest).length;
          const D = window.KAMISHIHI_MAP, KM = K.REG.live; let bad = [];
          const chk = (x, z, what) => { const g = (window.__kr = window.__kr || 0); };
          return {cur: K.REG.cur, cnt, groups: kw.groups.length, nodes, ktrees: L.ktrees.size,
            pts: kw.sp.map(s => [s.x, s.z]).concat(kw.groups.map(g => [g.x, g.z]), kw.nodes.map(n => [n.x, n.z]))}; }""")
        print('上志比：', {k: v for k, v in A.items() if k != 'pts'})
        check(A['cur'] == 'kamishihi', '上志比へ移った')
        check(A['cnt'] == {'bear': 4, 'boar': 8, 'deer': 3, 'weasel': 2, 'monkey': 3} and A['groups'] == 4,
              f'獣の置き場所 {A["cnt"]}・群れ {A["groups"]}（暫定の推奨案どおり）')
        want = {'stone': 12, 'bamboo': 6, 'rock': 6, 'straw': 8, 'wood': 10, 'food': 6, 'chest': 2}
        check(all(A['nodes'].get(k) == v for k, v in want.items()) and A['nodes'].get('scrap', 0) >= 10,
              f'採集場所 {A["nodes"]}')
        R = await pg.evaluate("""(pts) => { const K = window.__k; let bad = 0; for (const [x, z] of pts) { if (!K.kamiReach(x, z) || K.kamiCls(x, z) === 2) bad++; } return bad; }""", A['pts'])
        check(R == 0, f'置き場所はすべて歩ける所（川の中・範囲の外なし。外れ {R}）')
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            await pg.evaluate("() => { window.__k.KW_TEST.marks = true; window.__k.openMap(); }")
            await pg.wait_for_timeout(300)
            await pg.evaluate("() => window.__k.openMap()")
            await pg.wait_for_timeout(600)
            await pg.screenshot(path=os.path.join(SHOTS, 'kami_wild_map.png'))
            await pg.keyboard.press('Escape')
            await pg.evaluate("() => { window.__k.KW_TEST.marks = false; }")
            await pg.wait_for_timeout(300)

        # ---- 獣：近づくと出る・離れると片付く ----
        await pg.evaluate("""() => { const K = window.__k, s = K.REG.live.kw.sp.find(s => s.type === 'bear'); K.P.x = s.x + 60; K.P.z = s.z; window.__bear = s; }""")
        await pg.evaluate(TICK, 3)
        B = await pg.evaluate("""() => { const K = window.__k, s = window.__bear; return {has: !!(s.e && !s.e.removed), type: s.e && s.e.type, inLive: K.REG.live.enemies.includes(s.e), mode: s.e && s.e.mode}; }""")
        check(B['has'] and B['type'] == 'bear' and B['inLive'] and B['mode'] == 'field', f'近づくとクマが出る（地域の獣として登録）{B}')
        await pg.evaluate("""() => { const K = window.__k, s = window.__bear; K.P.x = s.x + 300; K.P.z = s.z; }""")
        await pg.evaluate(TICK, 2)
        B2 = await pg.evaluate("() => { const s = window.__bear; return {e: !!s.e}; }")
        check(not B2['e'], '遠く離れると片付く（倒していないので時間は数えない）')
        # 倒すと、決まった時間まで戻らない（往復・セーブ・ロードでも）
        await pg.evaluate("""() => { const K = window.__k, s = window.__bear; K.P.x = s.x + 60; K.P.z = s.z; }""")
        await pg.evaluate(TICK, 2)
        await pg.evaluate("""() => { const K = window.__k, e = window.__bear.e; e.hp = 1; K.damageEnemy(e, 999, 'heavy', 0); }""")
        await pg.evaluate(TICK, 2)
        D1 = await pg.evaluate("""() => { const K = window.__k, s = window.__bear; return {e: !!s.e, t: K.prog.kami.sp[s.key] - K.stats.time, key: s.key}; }""")
        check(not D1['e'] and 70 < D1['t'] <= 81, f'倒したクマは約80秒（光明寺と同じ）戻らない {D1}')
        await pg.evaluate("""async () => { const K = window.__k; K.saveGame(); await K.regionTravel('komyoji', null, {force: true}); await K.regionTravel('kamishihi', null, {force: true}); }""")
        await pg.wait_for_timeout(400)
        await pg.evaluate("""(key) => { const K = window.__k, s = K.REG.live.kw.sp.find(s => s.key === key); window.__bear = s; K.P.x = s.x + 60; K.P.z = s.z; }""", D1['key'])
        await pg.evaluate(TICK, 3)
        D2 = await pg.evaluate("() => !!window.__bear.e")
        check(not D2, '往復しても、倒したクマはまだ戻らない')
        await pg.evaluate("() => { window.__k.stats.time += 90; }")
        await pg.evaluate(TICK, 2)
        D3 = await pg.evaluate("() => !!(window.__bear.e && window.__bear.e.type === 'bear')")
        check(D3, '時間（遊んだ時間）がたつとクマが戻る')

        # ---- 群れ：初遭遇の前は凶暴化2体、解禁で変異が加わる、全滅から5分 ----
        await pg.evaluate("""() => { const K = window.__k, g = K.REG.live.kw.groups[0]; window.__g = g; K.P.x = g.x + 70; K.P.z = g.z; }""")
        await pg.evaluate(TICK, 3)
        G1 = await pg.evaluate("() => window.__g.m.map(m => m.e && !m.e.removed ? m.e.type : null)")
        check(G1 == ['monkey', 'monkey', None], f'初遭遇の前の群れは凶暴化したサル2体 {G1}')
        await pg.evaluate("() => { window.__k.prog.chapter2.progress.mutantMet = true; }")
        await pg.evaluate(TICK, 2)
        for _ in range(40):
            if await pg.evaluate("() => !!(window.__g.m[2].e)"):
                break
            await pg.wait_for_timeout(250)
            await pg.evaluate(TICK, 1)
        G2 = await pg.evaluate("() => window.__g.m.map(m => m.e && !m.e.removed ? [m.e.type, m.e.mode] : null)")
        check(G2[2] == ['mutant', 'mutant'] and G2[0][0] == 'monkey', f'初遭遇の記録があると、変異したサルが加わる（2＋1）{G2}')
        # 1体が気づくと仲間も向かう
        await pg.evaluate("""() => { const K = window.__k, g = window.__g, e = g.m[0].e; K.P.x = e.x + 12; K.P.z = e.z; K.setState(e, 'kite'); }""")
        await pg.evaluate(TICK, 1)
        G3 = await pg.evaluate("() => window.__g.m.map(m => m.e ? [m.e.state, !!m.e.aggro] : null)")
        check(G3[1][0] in ('alert', 'kite', 'dash', 'wind', 'retreat') and G3[2][1], f'1体が気づくと仲間も向かってくる {G3}')
        # 全滅させる
        await pg.evaluate("""() => { const K = window.__k; for (const m of window.__g.m) if (m.e) { m.e.hp = 1; m.e.fleeOnly = false; K.damageEnemy(m.e, 9999, 'heavy', 0); } }""")
        await pg.evaluate(TICK, 2)
        G4 = await pg.evaluate("() => { const K = window.__k, st = K.prog.kami.g[window.__g.key]; return {d: st.d, w: st.w - K.stats.time, scale: K.enemies.length}; }")
        check(G4['d'] == [1, 1, 1] and 295 < G4['w'] <= 300.5, f'全滅すると5分（遊んだ時間）戻らない {G4}')
        await pg.evaluate("() => { const K = window.__k, g = window.__g; K.P.x = g.x + 70; K.P.z = g.z; K.stats.time += 200; }")  # 群れから離れて待つ（32m より近いと出ない）
        await pg.evaluate(TICK, 3)
        G5 = await pg.evaluate("() => window.__g.m.filter(m => m.e || m.pending).length")
        await pg.evaluate("() => { window.__k.stats.time += 110; }")
        await pg.evaluate(TICK, 3)
        for _ in range(20):
            if await pg.evaluate("() => window.__g.m.filter(m => m.e).length === 3"):
                break
            await pg.wait_for_timeout(250)
            await pg.evaluate(TICK, 1)
        G6 = await pg.evaluate("() => window.__g.m.filter(m => m.e).length")
        check(G5 == 0 and G6 == 3, f'5分たつと群れがそろって戻る（3分20秒では {G5} 体、5分10秒では {G6} 体）')
        await pg.evaluate("() => { window.__k.prog.chapter2.progress.mutantMet = false; }")

        # ---- 採集 ----
        GA = await pg.evaluate("""async () => { const K = window.__k, kw = K.REG.live.kw, out = {};
          const at = async (n, dx = 0.6) => { K.P.x = n.x + dx; K.P.z = n.z; K.kamiNodesUpdate(K.REG.live, K.stats.time); };
          const act = (re) => { const L = K.allInter().filter(o => re.test(o.label)).sort((a, b) => a.d - b.d); if (L[0]) { L[0].act(); return L[0].label; } return null; };
          const before = {stone: K.inv.stone, straw: K.inv.straw, bamboo: K.inv.bamboo, wood: K.inv.wood, iron: K.inv.iron, food: K.prog.f7 ? 0 : 0};
          let n = kw.nodes.find(n => n.k === 'stone'); await at(n); out.stoneLab = act(/河原の石を拾う/); out.stone = K.inv.stone - before.stone; out.stoneAgain = act(/河原の石を拾う/); out.stoneKey = n.key;
          n = kw.nodes.find(n => n.k === 'straw'); await at(n); out.strawLab = act(/稲を束ねる/); out.straw = K.inv.straw - before.straw;
          n = kw.nodes.find(n => n.k === 'bamboo'); await at(n, 2.2); out.bambooLab = act(/竹を切る/); out.bamboo = K.inv.bamboo - before.bamboo;
          n = kw.nodes.find(n => n.k === 'wood'); await at(n); out.woodLab = act(/薪を拾う/); out.wood = K.inv.wood - before.wood; out.woodKey = n.key;
          n = kw.nodes.find(n => n.k === 'food' && !n.chest); await at(n); out.foodLab = act(/大根を収穫する/);
          n = kw.nodes.find(n => n.k === 'scrap'); await at(n); out.scrapLab = act(/がれきを探る/); out.iron = K.inv.iron - before.iron; out.scrapAgain = act(/がれきを探る/); out.scrapKey = n.key;
          n = kw.nodes.find(n => n.k === 'rock'); await at(n, 1.8); const tg = K.f4FindTarget(1.6); out.rockTarget = tg && tg.type; const s0 = K.inv.stone;
          for (let i = 0; i < 12; i++) K.f4Hit({type: 'krock', r: n, x: n.x, z: n.z, d: 0.5}, 'light'); out.rock = K.inv.stone - s0; out.rockLeft = K.prog.kami.r[n.key]; out.rockKey = n.key;
          return out; }""")
        print('採集：', GA)
        check(GA['stoneLab'] and 1 <= GA['stone'] <= 2 and GA['stoneAgain'] is None, '河原の石を拾える（1〜2）。拾ったらもう拾えない')
        check(GA['strawLab'] and GA['straw'] == 3, '荒らされた田の稲を束ねる（藁+3）')
        check(GA['bambooLab'] and GA['bamboo'] == 2, '竹を切る（竹+2）')
        check(GA['woodLab'] and GA['wood'] == 2 and GA['foodLab'], '薪を拾う（木材+2）・大根を収穫する')
        check(GA['scrapLab'] and 1 <= GA['iron'] <= 2 and GA['scrapAgain'] is None, 'がれきを探る（屑鉄1〜2）。1回だけ')
        check(GA['rockTarget'] == 'krock' and GA['rock'] == 8 and GA['rockLeft'] == 0, f'岩を槌で割る（石 合計8）{GA["rock"]}')
        # 往復・セーブ・ロードで戻らない
        await pg.evaluate("""async () => { const K = window.__k; K.saveGame(); await K.regionTravel('komyoji', null, {force: true}); await K.regionTravel('kamishihi', null, {force: true}); }""")
        await pg.wait_for_timeout(300)
        GB = await pg.evaluate("""(keys) => { const K = window.__k, kw = K.REG.live.kw; const n = kw.nodes.find(n => n.key === keys[0]); K.P.x = n.x + 0.6; K.P.z = n.z; K.kamiNodesUpdate(K.REG.live, K.stats.time);
          const L = K.allInter(); const r = kw.nodes.find(n => n.key === keys[2]);
          return {stone: L.some(o => /河原の石を拾う/.test(o.label)), stoneSeen: n.m.visible, rockVis: r.m.visible, rockRubble: r.mr.visible,
            saved: JSON.parse(localStorage.getItem('eiheiji_vs_beasts_v010')).kami}; }""", [GA['stoneKey'], GA['scrapKey'], GA['rockKey']])
        check((not GB['stone']) and (not GB['stoneSeen']), '往復しても、拾った石は戻らない')
        check(GB['saved'] and GB['saved']['v'] == 1 and GA['stoneKey'] in GB['saved']['n'] and GA['scrapKey'] in GB['saved']['sc'] and GB['saved']['r'].get(GA['rockKey']) == 0,
              f'セーブに上志比の状態（キー kami）が入る {json.dumps(GB["saved"], ensure_ascii=False)[:160]}')
        GC = await pg.evaluate("""(keys) => { const K = window.__k; const d = K.readSave(); K.applySave(d); const k = K.prog.kami;
          return {n: k.n[keys[0]] > 0, sc: k.sc.includes(keys[1]), r: k.r[keys[2]]}; }""", [GA['stoneKey'], GA['scrapKey'], GA['rockKey']])
        check(GC['n'] and GC['sc'] and GC['r'] == 0, 'ロードしても、取った物の記録が残る')
        await pg.evaluate("() => { window.__k.stats.time += 400; }")
        GD = await pg.evaluate("""(keys) => { const K = window.__k, kw = K.REG.live.kw, n = kw.nodes.find(n => n.key === keys[0]), r = kw.nodes.find(n => n.key === keys[2]), s = kw.nodes.find(n => n.key === keys[1]);
          K.P.x = n.x + 0.6; K.P.z = n.z; K.kamiNodesUpdate(K.REG.live, K.stats.time); const a = K.allInter().some(o => /河原の石を拾う/.test(o.label));
          K.P.x = r.x + 30; K.P.z = r.z; K.kamiNodesUpdate(K.REG.live, K.stats.time); K.P.x = s.x + 0.6; K.P.z = s.z;
          return {stone: a, rock: K.prog.kami.r[keys[2]], scrapDone: K.allInter().some(o => /もう探った/.test(o.label))}; }""", [GA['stoneKey'], GA['scrapKey'], GA['rockKey']])
        check(GD['stone'] and GD['rock'] is None and GD['scrapDone'], f'時間がたつと石・岩は戻る。がれきは戻らない {GD}')

        # ---- 伐採 ----
        F = await pg.evaluate("""async () => { const K = window.__k, L = K.REG.live; let kt = null;
          for (const t of L.ktrees.values()) { if (t.felled || t.s >= 1.3) continue; if (K.f4Free(t.x + 1.2, t.z, 0.5) && K.f4Free(t.x + 7, t.z, 0.5) && K.kamiReach(t.x + 1.2, t.z)) { kt = t; break; } }
          K.P.x = kt.x + 1.15; K.P.z = kt.z; K.P.facing = -Math.PI / 2; const tg = K.f4FindTarget(1.6); const w0 = K.inv.wood;
          if (!tg || tg.type !== 'tree' || tg.rec.kind !== 'k') return {tg: tg && tg.type};
          kt = tg.rec.t; // いちばん近い木（選んだ木の隣の木のことがある）
          for (let i = 0; i < 30 && !kt.felled; i++) K.f4Hit(tg, 'heavy');
          const tr = K.F4.trunks.find(t => t.key === kt.key);
          for (let i = 0; i < 200 && tr && tr.fall >= 0; i++) await new Promise(r => requestAnimationFrame(r));
          const felled = K.prog.kami.f.includes(kt.key), inF4 = K.prog.f4.felled.includes(kt.key), colOff = !kt.col.active, parentOK = !!tr && tr.piv.parent === L.group;
          for (let i = 0; i < 20 && K.F4.trunks.includes(tr); i++) K.f4Hit({type: 'trunk', tr, x: tr.x, z: tr.z, d: 0.5}, 'heavy');
          const logs = L.kw.logs.length, f4logs = K.prog.f4.logs.length; const l = L.kw.logs[0];
          K.P.x = l[0] + 0.8; K.P.z = l[1]; const lt = K.f4FindTarget(1.6); const lab = K.allInter().map(o => o.label).find(s => /丸太/.test(s));
          for (let i = 0; i < 30 && L.kw.logs.includes(l); i++) K.f4Hit({type: 'klog', l, x: l[0], z: l[1], d: 0.4}, 'light');
          return {key: kt.key, tg: tg.type, felled, inF4, colOff, kami: tr && tr.kami, parentOK, logs, f4logs, ltype: lt && lt.type, lab, split: K.inv.wood - w0, left: L.kw.logs.length}; }""")
        print('伐採：', F)
        check(F['tg'] == 'tree' and F['felled'] and not F['inF4'] and F['colOff'] and F['kami'] and F['parentOK'], '上志比の木を切って倒せる（上志比の記録に入り、光明寺の記録には入らない）')
        check(F['logs'] >= 3 and F['ltype'] == 'klog' and F['lab'] and 'ここからは運べない' in F['lab'], f'枝を払うと丸太になる（運べない）：{F["lab"]}')
        check(F['split'] >= 2 and F['left'] == F['logs'] - 1, f'丸太をその場で割ると木材になる（+{F["split"]}）')
        await pg.evaluate("""async () => { const K = window.__k; K.saveGame(); await K.regionTravel('komyoji', null, {force: true}); }""")
        FK = await pg.evaluate("() => { const K = window.__k; return {kamiTr: K.F4.trunks.filter(t => t.kami).length, kchop: [...K.F4.chop.keys()].filter(k => k[0] === 'k').length, f4: JSON.parse(localStorage.getItem('eiheiji_vs_beasts_v010')).f4.trunks.length}; }")
        check(FK['kamiTr'] == 0 and FK['kchop'] == 0, f'上志比を出ると倒木・丸太は消える {FK}')
        await pg.evaluate("async () => { await window.__k.regionTravel('kamishihi', null, {force: true}); }")
        FR = await pg.evaluate("(key) => { const kt = window.__k.REG.live.ktrees.get(key); return {felled: kt.felled, col: kt.col.active}; }", F['key'])
        check(FR['felled'] and not FR['col'], '戻っても、切った木は切ったまま（当たり判定もない）')

        # ---- テスト用の解禁（試遊版のボタンが使う）は保存されない ----
        T = await pg.evaluate("""() => { const K = window.__k; K.KW_TEST.mutant = true; const ok = K.kamiMutantOK(); K.saveGame(); const s = localStorage.getItem('eiheiji_vs_beasts_v010'); K.KW_TEST.mutant = false;
          return {ok, inSave: /KW_TEST|mutantTest/.test(s), met: JSON.parse(s).chapter2.progress.mutantMet}; }""")
        check(T['ok'] and not T['inSave'] and not T['met'], f'テスト用の解禁はセーブに残らない {T}')

        if SHOTS:
            for name, sel in [('kami_wild_group', 'group'), ('kami_wild_rock', 'rock'), ('kami_wild_bamboo', 'bamboo')]:
                await pg.evaluate("""(sel) => { const K = window.__k, kw = K.REG.live.kw; let x, z;
                  if (sel === 'group') { const g = kw.groups[1]; x = g.x + 14; z = g.z + 8; } else { const n = kw.nodes.find(n => n.k === sel); x = n.x + 5; z = n.z + 4; }
                  K.P.x = x; K.P.z = z; }""", sel)
                await pg.evaluate(TICK, 3)
                await pg.wait_for_timeout(2500)
                await pg.screenshot(path=os.path.join(SHOTS, name + '.png'))

        # ---- 光明寺に戻ると元どおり ----
        await pg.evaluate("async () => { await window.__k.regionTravel('komyoji', null, {force: true}); }")
        await pg.wait_for_timeout(500)
        end = await pg.evaluate("""() => { const K = window.__k; let cells = 0; for (const a of K.cgrid.values()) cells += a.length;
          return {circles: K.circles.length, oboxes: K.oboxes.length, cells, kids: K.scene.children.length, enemies: K.enemies.filter(e => !e.removed && e.x > 4000).length, dmg: K.DAMAGED.length}; }""")
        print('光明寺：', base, '→', end)
        check(end['circles'] == base['circles'] and end['oboxes'] == base['oboxes'] and end['cells'] == base['cells'] and end['enemies'] == 0 and end['dmg'] == base['dmg'],
              '光明寺に戻ると、当たり判定・壊れた家の記録が元どおりで、上志比の獣は残らない')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: kamishihi wild' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
