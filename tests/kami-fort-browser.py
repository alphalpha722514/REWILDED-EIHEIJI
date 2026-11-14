#!/usr/bin/env python3
"""v0.68（P2 第2段階）サルの占拠区域（中心要塞・小拠点2か所）の確認（画面のない Chromium。数分かかる）。

本物の上志比のデータで、
- 中心要塞・小拠点A（見張り場）・小拠点B（物資置き場）ができ、見張り台4つ・物資置き場2つがある
- 第1段階の獣・群れ・採集の場所が占拠区域に入っていない
- 要塞の物資置き場へは、侵入経路3つ（正面の門・建物の隙間・裏道）の **どれか1つだけを開けても** 外から歩いて着ける。
  3つとも塞ぐと着けない（＝ほかに抜け道がない）。主人公の大きさ（半径0.5m）で、0.5m 刻みの格子を探す
- 見つけた道を、本物の当たり判定（resolve）で主人公に歩かせても、押し戻されずに着く
- 小拠点B の物資置き場にも外から着ける。主要な道（要塞の外を回る道）は通れる
- 物資置き場：要塞・小拠点B から物資を持ち出せる（v0.69。数と再補充は kami-watch-browser.py）
- 光明寺に戻ると当たり判定が元どおり／エラーなし
KAMI_SHOTS=フォルダ で、地図と要塞の画面を撮る。

使い方：THREE_JS=…/three.min.js python3 tests/kami-fort-browser.py
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
SHOTS = os.environ.get('KAMI_SHOTS')
HOOK = ("window.__k={get REG(){return REG},get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get stats(){return stats},"
        "circles,oboxes,cgrid,scene,camera,get KF(){return KF},regionTravel,saveGame,readSave,applySave,resolve,addOBox,gridRemove,f4Free,kamiReach,kamiInZone,"
        "allInter:()=>{ const L=[]; g4Interactables(L); return L; },openMap:()=>{ if(S.mode==='playing') openMap(); }};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)

# 0.5m 格子で、主人公（半径0.5）が通れる所を探す。start から goal へ着けるか。着けたら道（格子の点の列）を返す
BFS = """([sx, sz, gx, gz, x0, x1, z0, z1]) => { const K = window.__k, st = 0.5, nx = Math.round((x1 - x0) / st) + 1, nz = Math.round((z1 - z0) / st) + 1;
  const ok = new Int8Array(nx * nz).fill(-1), prev = new Int32Array(nx * nz).fill(-1);
  const free = (i, k) => { const n = k * nx + i; if (ok[n] < 0) { const x = x0 + i * st, z = z0 + k * st; ok[n] = (K.f4Free(x, z, 0.5) && K.kamiReach(x, z)) ? 1 : 0; } return ok[n] === 1; };
  const cell = (x, z) => [Math.round((x - x0) / st), Math.round((z - z0) / st)];
  const [si, sk] = cell(sx, sz), [gi, gk] = cell(gx, gz); if (!free(si, sk)) return {ok: false, why: 'start blocked'};
  const q = [sk * nx + si]; prev[q[0]] = q[0]; let h = 0;
  while (h < q.length) { const n = q[h++], i = n % nx, k = (n / nx) | 0; if (Math.abs(i - gi) <= 1 && Math.abs(k - gk) <= 1) {
      const path = []; let m = n; while (true) { path.push([x0 + (m % nx) * st, z0 + ((m / nx) | 0) * st]); if (prev[m] === m) break; m = prev[m]; } return {ok: true, path: path.reverse(), seen: h}; }
    for (const [di, dk] of [[1,0],[-1,0],[0,1],[0,-1]]) { const a = i + di, b = k + dk; if (a < 0 || b < 0 || a >= nx || b >= nz) continue; const m = b * nx + a; if (prev[m] >= 0) continue; if (!free(a, b)) continue; prev[m] = n; q.push(m); } }
  return {ok: false, seen: h}; }"""
# 道を本物の当たり判定で歩かせる（1回に0.25m ずつ。押し戻された量の最大を返す）
WALK = """(path) => { const K = window.__k, P = K.P; P.x = path[0][0]; P.z = path[0][1]; let worst = 0, stuck = 0;
  for (let i = 1; i < path.length; i++) { const [tx, tz] = path[i]; for (let s = 0; s < 2; s++) { const ax = P.x + (tx - P.x) / (2 - s), az = P.z + (tz - P.z) / (2 - s); P.x = ax; P.z = az; K.resolve(P, false); const d = Math.hypot(P.x - ax, P.z - az); worst = Math.max(worst, d); if (d > 0.2) stuck++; } }
  const end = path[path.length - 1]; return {worst: Math.round(worst * 100) / 100, stuck, endD: Math.round(Math.hypot(P.x - end[0], P.z - end[1]) * 100) / 100}; }"""


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
        await pg.wait_for_timeout(1000)
        base = await pg.evaluate("() => { const K = window.__k; let cells = 0; for (const a of K.cgrid.values()) cells += a.length; return {circles: K.circles.length, oboxes: K.oboxes.length, cells}; }")
        await pg.evaluate("""async () => { const K = window.__k; K.prog.bossDefeated = true; K.prog.stage = 'cleared'; K.prog.chapter2.unlocked = true; K.prog.chapter2.progress.defenseComplete = true;
          await K.regionTravel('kamishihi', null, {force: true}); }""")
        await pg.wait_for_timeout(500)
        A = await pg.evaluate("""() => { const K = window.__k, L = K.REG.live, kf = L.kf, kw = L.kw;
          const by = {}; for (const w of kf.walls) { const len = Math.hypot(w[2] - w[0], w[3] - w[1]); by[w[4]] = (by[w[4]] || 0) + len; }
          const inZone = kw.sp.filter(s => K.kamiInZone(s.x, s.z)).length + kw.groups.filter(g => K.kamiInZone(g.x, g.z)).length + kw.nodes.filter(n => K.kamiInZone(n.x, n.z)).length;
          return {walls: Object.fromEntries(Object.entries(by).map(([k, v]) => [k, Math.round(v)])), towers: kf.towers.map(t => t.site), stashes: kf.stashes.map(s => [s.id, s.fx, s.fz]),
            barri: K.oboxes.filter(o => o.barri).length, inZone, groups: kw.groups.length, sp: kw.sp.length, nodes: kw.nodes.length}; }""")
        print('占拠区域：', A)
        check(A['walls'].get('fort', 0) > 150 and A['walls'].get('outA', 0) > 10 and A['walls'].get('outB', 0) > 20, f'要塞・小拠点A・小拠点B のバリケード（長さ m）{A["walls"]}')
        check(sorted(A['towers']) == ['fort', 'fort', 'fort', 'outA'] and [s[0] for s in A['stashes']] == ['fort', 'outB'], '見張り台（要塞3・見張り場1）と物資置き場（要塞・小拠点B）')
        check(A['inZone'] == 0 and A['groups'] == 4 and A['sp'] == 20, f'第1段階の獣・群れ・採集の場所は占拠区域に入っていない（入っている数 {A["inZone"]}）')

        # ---- 侵入経路：1つだけ開けても着ける・全部塞ぐと着けない ----
        fort = [s for s in A['stashes'] if s[0] == 'fort'][0]
        gaps = await pg.evaluate("() => window.__k.KF.sites[0].gaps")
        outside = [7222, 1031]  # 国道416号（要塞の西）
        box = [7205, 7375, 1000, 1150]
        async def block(keys):
            return await pg.evaluate("""(keys) => { const K = window.__k, s = K.KF.sites[0]; window.__blk = (window.__blk || []);
              for (const g of s.gaps) if (keys.includes(g.k)) { const along = g.k === 'alley' ? 0 : Math.PI / 2; window.__blk.push(K.addOBox(g.x, g.z, g.w + 1.5, 1.2, along, 'house', {test: 1})); } return window.__blk.length; }""", keys)
        async def unblock():
            await pg.evaluate("() => { const K = window.__k; for (const o of (window.__blk || [])) { K.gridRemove(o); o.active = false; const i = K.oboxes.indexOf(o); if (i >= 0) K.oboxes.splice(i, 1); } window.__blk = []; }")
        res = {}
        for open_k in ['front', 'alley', 'back', None]:
            await block([g['k'] for g in gaps if g['k'] != open_k])
            r = await pg.evaluate(BFS, [outside[0], outside[1], fort[1], fort[2], *box])
            res[open_k] = r
            if r['ok']:
                w = await pg.evaluate(WALK, r['path'])
                res[open_k]['walk'] = w
            await unblock()
        for k, nm in [('front', '正面の門（国道416号）'), ('alley', '建物の隙間（南の家と家の間）'), ('back', '裏道（東の田んぼの壁の破れ目）')]:
            r = res[k]
            check(r['ok'] and r['walk']['stuck'] == 0 and r['walk']['endD'] < 0.6,
                  f'{nm}だけを開けても、外から物資置き場に歩いて着ける（道 {len(r.get("path", []))} 点・押し戻し最大 {r.get("walk", {}).get("worst")}m）')
        check(not res[None]['ok'], f'3つとも塞ぐと着けない（ほかに抜け道がない。調べた格子 {res[None].get("seen")}）')
        r_all = await pg.evaluate(BFS, [outside[0], outside[1], fort[1], fort[2], *box])
        check(r_all['ok'], 'ふだん（3つとも開いている）は着ける')
        # 主要な道：要塞の外を回って、南の道・東の家並みへ行ける
        around = await pg.evaluate(BFS, [outside[0], outside[1], 7362, 1140, *box])
        await block(['front', 'alley', 'back'])
        around2 = await pg.evaluate(BFS, [outside[0], outside[1], 7362, 1140, *box])
        await unblock()
        check(around['ok'] and around2['ok'], '要塞を通らずに、外を回って東の家並み（藤巻下荒井線）へ行ける')
        outB = [s for s in A['stashes'] if s[0] == 'outB'][0]
        rb = await pg.evaluate(BFS, [6729, 1290, outB[1], outB[2], 6700, 6810, 1240, 1350])
        check(rb['ok'], '小拠点B の物資置き場に外から着ける')
        ra = await pg.evaluate(BFS, [6935, 1019, 7000, 1020, 6900, 7040, 990, 1060])
        check(ra['ok'], '小拠点A（見張り場）の前の国道416号は通れる')

        # ---- 物資置き場（v0.69 から本編でも持ち出せる。細かい確かめは kami-watch-browser.py） ----
        S = await pg.evaluate("""() => { const K = window.__k, out = {}; for (const st of K.REG.live.kf.stashes) { K.P.x = st.fx; K.P.z = st.fz; const w0 = K.inv.wood;
            const L1 = K.allInter().filter(o => /物資/.test(o.label)); if (L1[0]) L1[0].act(); out[st.id] = {lab: L1[0] && L1[0].label, wood: K.inv.wood - w0}; } return out; }""")
        print('物資置き場：', S)
        check(S['fort']['wood'] == 20 and S['outB']['wood'] == 10 and '持ち出す' in (S['fort']['lab'] or ''), '要塞・小拠点B の物資置き場から、外から歩いて行って物資を持ち出せる（敵を倒さなくてもよい）')

        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            await pg.evaluate("() => window.__k.openMap()")
            await pg.wait_for_timeout(800)
            await pg.screenshot(path=os.path.join(SHOTS, 'fort_map.png'), timeout=180000)
            await pg.keyboard.press('Escape')
            await pg.wait_for_timeout(300)
            # 主人公の位置と見る先（見る先へ向いて C でカメラを後ろへ）
            for name, x, z, tx, tz in [('fort_gate', 7232, 1034, 7256, 1042), ('fort_alley', 7292, 1126, 7291, 1105), ('fort_back', 7356, 1072, 7340, 1061), ('fort_inside', 7262, 1060, 7300, 1050),
                                       ('fort_stash', 7322, 1080, 7333, 1080), ('fort_tower', 7272, 1066, 7257, 1049), ('out_A', 6962, 1012, 6962, 1031), ('out_B', 6768, 1296, 6768, 1312)]:
                await pg.evaluate("([x, z, tx, tz]) => { const K = window.__k; K.P.x = x; K.P.z = z; K.P.facing = Math.atan2(tx - x, tz - z); }", [x, z, tx, tz])
                await pg.keyboard.press('c')
                await pg.wait_for_timeout(2500)
                await pg.screenshot(path=os.path.join(SHOTS, name + '.png'), timeout=180000)

        await pg.evaluate("async () => { await window.__k.regionTravel('komyoji', null, {force: true}); }")
        await pg.wait_for_timeout(500)
        end = await pg.evaluate("() => { const K = window.__k; let cells = 0; for (const a of K.cgrid.values()) cells += a.length; return {circles: K.circles.length, oboxes: K.oboxes.length, cells, barri: K.oboxes.filter(o => o.barri && o.active !== false).length}; }")
        print('光明寺：', base, '→', end)
        check(end['circles'] == base['circles'] and end['oboxes'] == base['oboxes'] and end['cells'] == base['cells'], '光明寺に戻ると、当たり判定が元どおり（バリケードは残らない）')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: kamishihi fort' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
