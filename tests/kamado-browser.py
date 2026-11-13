#!/usr/bin/env python3
"""v0.66 かまどの料理と食材の確認（画面のない Chromium。数分）。docs/kamado-cooking-plan.md

- かまどは最初から築ける（石4・木材4）。作業台では料理を作れない（かまどだけ）
- 食材：獣は肉を落とす。食料が要る所（餌・畑の手入れ）は、肉・野菜・米でも足りる
- 料理は固有のレシピではなく、鍋の中身に近い料理ほど出やすい：
  米だけ→おにぎり、肉と米→ソースカツ丼、肉と野菜→ぼたん鍋、野菜3つ→胡麻豆腐か里芋のころ煮、肉だけ→串焼き。
  肉を入れなければ肉の料理は出ない。食料はどの食材のかわりにもなる（何ができるか分からない）
- 鍋を火にかけると、食材と薪（木材1）が減り、45秒でできる。できるまで何の料理か分からない。取り出すと手持ちに入る
- 新しい料理を食べると効果が出る。肉と米は生では食べられない
- 保存：かまどの並びとできた物。v0.64 の形（数だけ）も読める
- エラーなし
使い方：THREE_JS=…/three.min.js python3 tests/kamado-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
HOOK = ("window.__t={get P(){return P},get S(){return S},get prog(){return prog},get inv(){return inv},get enemies(){return enemies},get drops(){return drops},FOODS,FAC,FACM,RECIPES,"
        "craft:id=>craft(id),kamaOdds:p=>kamaOdds(p),kamaRoll:p=>kamaRoll(p),kamaHint:p=>kamaHint(p),kamaCook:p=>kamaCook(p),kamaCoal:n=>kamaCoal(n),kamaTake:()=>kamaTake(),kamaLoad:q=>kamaLoad(q),"
        "facUpdate:dt=>facUpdate(dt),eat:k=>eat(k),rawFood:()=>rawFood(),rawTake:n=>rawTake(n),foodAdd:(k,n)=>foodAdd(k,n),f7Flush:()=>f7Flush(),interactables:()=>interactables(),"
        "spawnEnemy:(...a)=>spawnEnemy(...a),damageEnemy:(...a)=>damageEnemy(...a),updateEnemies:dt=>updateEnemies(dt),saveGame:()=>saveGame(),applySave:d=>applySave(d),hbDefs:()=>hbDefs(),iconOf:id=>iconOf(id)};\n")
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)


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

        st = await pg.evaluate("""() => { const T = window.__t, I = T.inv; const r = T.RECIPES.find(x => x.id === 'kamaBuild'); const shown = r.show(); I.stone = 4; I.wood = 4;
          const o0 = I.onigiri; I.food = 5; T.craft('onigiri'); const bench = I.onigiri - o0; T.craft('kamaBuild');
          const P = T.P, F = T.FAC.kama; P.x = F.pos.x; P.z = F.pos.z - F.D / 2 - 0.7; return {shown, bench, built: T.prog.kama.built, left: [I.stone, I.wood], label: (T.interactables() || {}).label}; }""")
        print('かまど：', st)
        check(st['shown'] and st['built'] == 1 and st['left'] == [0, 0], 'かまどは最初から築ける（石4・木材4）')
        check(st['bench'] == 0, '作業台ではおにぎりを作れない（料理はかまどだけ）')
        check(str(st['label']).startswith('かまど：火は落ちている'), f'かまどを調べられる（{st["label"]}）')

        od = await pg.evaluate("""() => { const T = window.__t; const top = p => { const o = T.kamaOdds(p); return Object.entries(o).sort((a, b) => b[1] - a[1]).map(([k, v]) => [k, Math.round(v * 100)]); };
          const seen = new Set(); for (let i = 0; i < 400; i++) seen.add(T.kamaRoll({meat: 1, veg: 1, rice: 1}));
          return {rice2: top({rice: 2}), mr: top({meat: 1, rice: 1}), mv: top({meat: 1, veg: 1}), veg3: top({veg: 3}), veg2: top({veg: 2}), meat2: top({meat: 2}), rv: top({rice: 2, veg: 1}), food2: top({food: 2}),
            hint: T.kamaHint({meat: 1, rice: 1}), mix: [...seen].sort()}; }""")
        for k in ['rice2', 'mr', 'mv', 'veg3', 'veg2', 'meat2', 'rv', 'food2']:
            print(f'  {k}:', od[k][:5])
        print('  hint:', od['hint'], ' mix:', od['mix'])
        check(od['rice2'][0] == ['onigiri', 100], '米だけ → おにぎり')
        check(od['mr'][0][0] == 'katsudon' and od['mr'][0][1] >= 70, '肉と米 → ソースカツ丼が出やすい')
        check(od['mv'][0][0] == 'botan' and od['mv'][0][1] >= 70, '肉と野菜 → ぼたん鍋が出やすい')
        check({od['veg3'][0][0], od['veg3'][1][0]} == {'gomadofu', 'koroni'}, '野菜3つ → 胡麻豆腐か里芋のころ煮')
        check(od['veg2'][0][0] == 'grilledVeg', '野菜2つ → 焼き野菜が出やすい')
        check(od['meat2'][0] == ['kushi', 100], '肉だけ → 串焼き')
        check(od['rv'][0][0] in ('herbPorridge', 'bento') and not any(k in ('kushi', 'katsudon', 'botan') for k, _ in od['rv']), '米と野菜 → 薬草粥・精進弁当。肉を入れなければ肉の料理は出ない')
        check(len(od['food2']) >= 5, f'食料だけ → いろいろな料理が出うる（{len(od["food2"])}種）')
        check(len(od['mix']) >= 3, f'肉・野菜・米を1つずつ → 毎回同じではない（{od["mix"]}）')
        check('ソースカツ丼' in od['hint'], f'鍋に入れると、できやすい料理が出る（{od["hint"]}）')

        ck = await pg.evaluate("""() => { const T = window.__t, I = T.inv, K = T.prog.kama; T.foodAdd('rice', 4); T.foodAdd('meat', 2); I.wood = 10; T.f7Flush();
          const dish = T.kamaCook({meat: 0, veg: 0, rice: 2, food: 0}); const after = {rice: I.rice, wood: I.wood, q: K.q.slice()};
          const none = T.kamaCook({meat: 0, veg: 0, rice: 1, food: 0}); const short = T.kamaCook({meat: 0, veg: 3, rice: 0, food: 0});
          for (let i = 0; i < 44 * 10; i++) T.facUpdate(0.1); const at44 = Object.assign({}, K.out); for (let i = 0; i < 12; i++) T.facUpdate(0.1); const at45 = Object.assign({}, K.out);
          const o0 = I.onigiri; T.kamaTake(); T.f7Flush(); return {dish, after, none, short, at44, at45, got: I.onigiri - o0, out: K.out}; }""")
        print('料理：', ck)
        check(ck['dish'] == 'onigiri' and ck['after'] == {'rice': 2, 'wood': 9, 'q': ['onigiri']}, '火にかけると、食材と薪（木材1）が減り、かまどの並びに入る')
        check(ck['none'] is None and ck['short'] is None, '食材が1つだけ・持っていない食材では作れない')
        check(ck['at44'] == {} and ck['at45'] == {'onigiri': 1} and ck['got'] == 1 and ck['out'] == {}, '45秒でできて、取り出すと手持ちに入る')

        mix = await pg.evaluate("""() => { const T = window.__t, I = T.inv, K = T.prog.kama; I.wood = 20; T.kamaCoal(1); T.foodAdd('veg', 2); T.f7Flush(); T.kamaCook({meat: 2, veg: 0, rice: 0, food: 0}); const q = K.q.slice();
          for (let i = 0; i < 31 * 10; i++) T.facUpdate(0.1); const mid = Object.assign({}, K.out); for (let i = 0; i < 46 * 10; i++) T.facUpdate(0.1); T.kamaTake(); T.f7Flush();
          const P = T.P; P.hp = 40; P.full = 20; P.buffT = 0; const k0 = I.kushi; T.eat('kushi'); const ate = {hp: P.hp, full: P.full, buff: P.buffT, left: I.kushi - k0};
          const m0 = I.meat; T.foodAdd('meat', 1); T.f7Flush(); T.eat('meat'); const rawMeat = I.meat; P.full = 50; T.eat('veg'); return {q, mid, coal: I.charcoal, ate, rawMeat, vegLeft: I.veg, full: P.full}; }""")
        print('並び・食べる：', mix)
        check(mix['q'] == ['charcoal', 'kushi'] and mix['mid'] == {'charcoal': 1} and mix['coal'] == 1, '木炭と料理を、入れた順に1つずつ作る')
        check(mix['ate'] == {'hp': 70, 'full': 50, 'buff': 20, 'left': -1}, '串焼きを食べると 体力+30・満腹+30・20秒間 攻撃力+30%')
        check(mix['rawMeat'] == 1 and mix['vegLeft'] == 1 and mix['full'] == 65, '肉は生では食べられない。野菜はかじれる')

        src = await pg.evaluate("""() => { const T = window.__t, P = T.P, I = T.inv; for (const d of [...T.drops]) d.n = 0; const n0 = T.drops.length;
          const e = T.spawnEnemy('bear', P.x + 30, P.z - 30, 'field', {}); for (let i = 0; i < 40 && e.state !== 'dead'; i++) T.damageEnemy(e, 30, 'heavy', 0);
          const kinds = T.drops.slice(n0).map(d => d.k); T.f7Flush(); for (const k of ['food', 'meat', 'veg', 'rice']) { const n = I[k]; if (n > 0) T.rawTake(n); } T.f7Flush();
          T.foodAdd('food', 1); T.foodAdd('meat', 1); T.foodAdd('rice', 1); T.f7Flush(); const have = T.rawFood(); T.rawTake(2); T.f7Flush();
          const hb = T.hbDefs().filter(d => d.kind === 'food').map(d => d.id); T.foodAdd('botan', 1); T.f7Flush(); const hb2 = T.hbDefs().filter(d => d.kind === 'food').map(d => d.id);
          return {kinds, have, left: {food: I.food, meat: I.meat, rice: I.rice}, hb, hb2, icon: !!T.iconOf('botan') && !!T.iconOf('meat')}; }""")
        print('食材：', src)
        check('meat' in src['kinds'] and 'food' not in src['kinds'], '獣は肉を落とす')
        check(src['have'] == 3 and src['left'] == {'food': 0, 'meat': 0, 'rice': 1}, '食料が要る所は、肉・野菜・米でも足りる（食料から先に使う）')
        check('botan' not in src['hb'] and 'botan' in src['hb2'] and src['icon'], '新しい料理は、持っているときに手持ちバーに出る（絵もある）')

        sv = await pg.evaluate("""() => { const T = window.__t, K = T.prog.kama; K.q = ['charcoal', 'botan']; K.t = 12.5; K.out = {katsudon: 2, charcoal: 1}; T.saveGame(); const d = JSON.parse(localStorage.getItem('eiheiji_vs_beasts_v010'));
          T.applySave(JSON.parse(JSON.stringify(d))); const back = {q: T.prog.kama.q, t: T.prog.kama.t, out: T.prog.kama.out, botan: T.inv.botan};
          const old = T.kamaLoad({v: 1, built: 1, q: 2, t: 7, out: 3}); const bad = T.kamaLoad({v: 1, built: 1, q: ['charcoal', 'xxx', 'meat'], t: 5, out: {xxx: 4, onigiri: 1}});
          const none = JSON.parse(JSON.stringify(d)); delete none.kama; delete none.inv.meat; delete none.f7; T.applySave(none);
          return {v: d.v, back, old: {q: old.q, out: old.out, t: old.t}, bad: {q: bad.q, out: bad.out}, none: {built: T.prog.kama.built, meat: T.inv.meat}}; }""")
        print('保存：', sv)
        check(sv['v'] == 1 and sv['back'] == {'q': ['charcoal', 'botan'], 't': 12.5, 'out': {'katsudon': 2, 'charcoal': 1}, 'botan': 1}, 'かまどの並び・できた物・料理を保存して読める（v:1 のまま）')
        check(sv['old'] == {'q': ['charcoal', 'charcoal'], 'out': {'charcoal': 3}, 't': 7}, 'v0.64 の形（数だけ）のかまども読める')
        check(sv['bad'] == {'q': ['charcoal'], 'out': {'onigiri': 1}}, '知らない名前は読み飛ばす')
        check(sv['none'] == {'built': 0, 'meat': 0}, 'かまど・食材の項目がない旧セーブは、未建設・0で読める')
        check(not errs, f'エラーなし {errs[:3]}')
        await b.close()
    print('PASS: kamado cooking' if ok else 'FAILED')
    sys.exit(0 if ok else 1)

asyncio.run(main())
