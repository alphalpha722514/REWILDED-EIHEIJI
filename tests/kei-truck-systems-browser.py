#!/usr/bin/env python3
"""KEI truck の仕組み（v0.78、2026-11-17 20:57 ユーザー決定）と同じ版の直し（5990m・鱗の武器・運転席・ドア）の確認。
画面のない Chromium・SwiftShader（数分）。docs/kei-truck-systems.md

 ① 旧セーブ（v0.77 の truck：直した・燃料を入れた、だけ）→ 燃料100%・車体100・段階0・荷台は空で読む
 ② 運転：走った道のりで燃料が減る・燃料0ではアクセルが効かない・木炭で足す（持ち物・荷台）
    平らな道でいっぱいに切って走っても横転しない・主人公は運転席に座る（0.62倍・武器は隠す）・運転席のドアが開いて閉まる
 ③ 獣の攻撃：運転中は主人公でなく車体が受ける（0.6倍）
 ④ 横転：横の力が続くと倒れる → 降りる・車体 -25・横に倒れた姿 → 「起こす」
 ⑤ 車両基地：作業台で建てる → 柱の当たり。南門の外から運転して屋根の下に入れる。柱に 10m/秒でぶつかると車体が傷む
    止めると 直す・改修（段階1〜3：最高速度・耐久・加速が上がる）・荷台の施設（段階で解放）
 ⑥ 荷台：丸太は6本まで（地面の丸太・担いだ丸太）・素材は広さ60まで・あおりが下りる・積んだ見た目
    車のそばでは作るときに荷台の素材も使う（離れると使わない）・丸太置き場の近くで納める（木材は 担いで納めるのと同じ）
 ⑦ 住民の運搬：源さんが荷台の丸太を丸太置き場まで運ぶ（拠点の外に止めた車から門を通って）→ 終わると戻る
 ⑧ 荷台の炭焼き釜（段階2）で木炭ができる・見張り台（段階3）で地図の獣が 90m まで
 ⑨ 上志比にいる間は、光明寺の依頼・目的の印を出さない（5990m の直し）
 ⑩ 鱗の装備（2026-11-17 22:21 の直し）：蒼鱗の武器は防御（受ける -15%）。変異鱗の武器は 移動 +12%・回避の消費 -15%・最大体力 -15%・強攻撃が1.5倍で1回でスタミナをすべて使う・衝撃波なし
    変異した鱗の防具一式は 防御が蒼鱗と同じ・最大体力 0.7倍・機動力が上がる・衝撃波は8秒でたまる
 ⑪ セーブ → 続きから：燃料・車体・段階・荷台・施設・炭焼き・車両基地が戻る
環境変数：KTS_SHOTS=フォルダ（車両基地・荷台・横転の画面を撮る）、THREE_JS
"""
import asyncio
import json
import math
import os
import time

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
SRC = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()
SHOTS = os.environ.get('KTS_SHOTS')
TRUCK_Z_POST = 68.6 - 3.0  # 車両基地の北の柱の z（基地の中心 68.6、柱は ±3.0）
HOOK = "window.__ev=s=>eval(s);\n"  # ゲームの中の変数をそのまま読む（テストだけ）
HTML = SRC.replace('function updateNPCs(dt){', HOOK + 'function updateNPCs(dt){', 1)
BASE = """() => window.__ev(`(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'}; // v0.77 の形（新しい項目なし）
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; })()`)"""
# 運転の自動操縦：経由点へ向けてハンドルを切り、速さを保つ（キーを押したことにする）
AUTOPILOT = r"""window.__ev(`window.__ap=function(pts,vmax){ let i=0; window.__apDone=false; window.__apLog=[]; clearInterval(window.__apH);
  window.__apH=setInterval(()=>{ if(!TRUCK.drive){ keys.clear(); window.__apDone='降りた'; clearInterval(window.__apH); return; }
    const q=pts[i], d=dist(TRUCK.x,TRUCK.z,q[0],q[1]); if(d<(i===pts.length-1?0.8:1.6)){ i++; if(i>=pts.length){ keys.clear(); keys.add('s'); setTimeout(()=>keys.clear(),600); window.__apDone=true; clearInterval(window.__apH); return; } }
    const e=angDiff(TRUCK.a,Math.atan2(q[0]-TRUCK.x,q[1]-TRUCK.z)); keys.delete('a'); keys.delete('d'); keys.delete('w'); keys.delete('s');
    if(e>0.05) keys.add('a'); else if(e<-0.05) keys.add('d');
    const want=Math.min(vmax,0.7+d*0.6)*(Math.abs(e)>0.8?0.5:1), v=TRUCK.v; if(v<want) keys.add('w'); else if(v>want+1.2) keys.add('s');
    window.__apLog.push([+TRUCK.x.toFixed(1),+TRUCK.z.toFixed(1)]); },50); }`)"""


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg, flush=True)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport={'width': 800, 'height': 500})
        pg = await ctx.new_page()
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))

        async def route(r):
            u = r.request.url
            if 'three.min.js' in u or 'three.js/r128' in u:
                return await r.fulfill(body=THREE, content_type='application/javascript')
            if u.startswith('http://game.local'):
                path = u.split('http://game.local/', 1)[1].split('?')[0]
                if path in ('', 'index.html'):
                    return await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
                fp = os.path.join(ROOT, path)
                if os.path.isfile(fp):
                    return await r.fulfill(body=open(fp, 'rb').read())
                return await r.fulfill(status=404, body='')
            await r.abort()
        await ctx.route('**/*', route)

        async def ev(js, arg=None):
            return await (pg.evaluate(js, arg) if arg is not None else pg.evaluate(js))

        async def G(code):  # ゲームの中で式を評価する
            return await pg.evaluate('(c) => window.__ev(c)', code)

        async def until(code, timeout=60):
            t0 = time.time()
            while time.time() - t0 < timeout:
                v = await G(code)
                if v:
                    return v
                await pg.wait_for_timeout(250)
            return None

        async def wait_game(sec, timeout=120):  # ゲームの時間で待つ（画面のない Chromium は遅く、実時間では進みが足りない）
            t0 = await G("S.time")
            await until(f"S.time>{t0}+{sec}", timeout)

        async def shot(name, view=None):
            """view：[横, 高さ, 前後, 見る横, 見る高さ, 見る前後]（車の中の座標。+x が左・+z が前）"""
            if not SHOTS:
                return
            os.makedirs(SHOTS, exist_ok=True)
            if view:
                await G(f"""(()=>{{ const v={json.dumps(view)}, a=TRUCK.a, sa=Math.sin(a), ca=Math.cos(a), L=(lx,lz)=>[TRUCK.x+lx*ca+lz*sa,TRUCK.z-lx*sa+lz*ca], g=groundH(TRUCK.x,TRUCK.z);
                  const [x,z]=L(v[0],v[2]), [lx,lz]=L(v[3],v[5]); cam.override={{p:new THREE.Vector3(x,g+v[1],z),l:new THREE.Vector3(lx,g+v[4],lz),fov:46}}; }})()""")
                await pg.wait_for_timeout(1500)
            try:
                await pg.screenshot(path=os.path.join(SHOTS, name + '.png'), timeout=180000)
            except Exception as e:
                print('  （画面を撮れなかった：', name, str(e)[:60], '）')
            if view:
                await G("cam.override=null")

        async def boot(cont=False):
            await pg.goto('http://game.local/', wait_until='load', timeout=300000)
            await pg.wait_for_function("typeof window.__ev === 'function'", timeout=300000)
            await pg.click('#btnContinue' if cont else '#btnNew', timeout=240000)
            await pg.wait_for_timeout(500)
            for _ in range(15):
                if await ev("document.getElementById('dialog').hidden"):
                    break
                await pg.click('#dialog')
                await pg.wait_for_timeout(200)

        async def close_menus():
            await G("(()=>{ const c=document.getElementById('defenseChoice'); if(c) c.remove(); dlgQueue.length=0; if(!$('dialog').hidden){ $('dialog').hidden=true; } closeOverlay(); S.mode='playing'; })()")

        async def put_truck(x, z, a):
            await G(f"(()=>{{ if(TRUCK.drive) truckExit(true); const t=trk(); t.x={x}; t.z={z}; t.a={a}; t.region='komyoji'; TRUCK.sync=false; truckColOff(); }})()")
            await wait_game(0.2)

        async def board():
            await G("(()=>{ P.x=TRUCK.x+Math.cos(TRUCK.a)*-2.2; P.z=TRUCK.z-Math.sin(TRUCK.a)*-2.2; truckBoard(); })()")
            await pg.wait_for_timeout(300)

        # ================= ① 旧セーブ =================
        await boot()
        await ev(BASE)
        await pg.wait_for_timeout(800)
        t0 = await G("(()=>{ const t=trk(); return {gas:t.gas,hp:t.hp,lv:t.lv,bed:t.bed,fac:t.fac,tip:t.tip,max:trkHpMax(t),depot:depotS().built}; })()")
        check(t0['gas'] == 100 and t0['hp'] == 100 and t0['lv'] == 0 and t0['bed'] == {'logs': [], 'mats': {}} and t0['tip'] == 0 and t0['depot'] == 0,
              f'v0.77 の形の truck は 燃料100%・車体100/100・段階0・荷台は空・車両基地なしで読む {t0}')
        await until("TRUCK.m&&TRUCK.m.visible&&TRUCK.visKind==='repaired'", 120)

        # ================= ② 運転・燃料・座る・ドア =================
        hm = await G("truckHome()")
        await put_truck(hm['x'], hm['z'], hm['a'] + math.pi)  # 国道416号を西へ（東の出口へ行かない向き）
        await board()
        drv = await G("({drive:TRUCK.drive,scale:+pm.g.scale.x.toFixed(2),wp:weaponPivot.visible,door:+(TRUCK.doorA?TRUCK.doorA.r:0).toFixed(2)})")
        await wait_game(0.2)
        door = await G("+(TRUCK.doorA?TRUCK.doorA.r:0).toFixed(2)")
        doors = await G("(()=>{ const V=TRUCK_VIS[TRUCK.visKind]; return V&&V.doors?Object.fromEntries(Object.entries(V.doors).map(([k,o])=>[k,!!o])):null; })()")
        check(drv['drive'] and drv['scale'] == 0.62 and not drv['wp'], f'乗ると主人公は運転席に座る（0.62倍・武器は隠す）{drv}')
        check(doors == {'r': True, 'l': True, 'tg': True} and door > 0.3, f'ドア2枚とあおりが別の形・乗ると運転席のドアが開く（{door} rad）{doors}')
        await G("(()=>{ window.__x0=TRUCK.x; window.__z0=TRUCK.z; window.__g0=trk().gas; window.__od=0; window.__lx=TRUCK.x; window.__lz=TRUCK.z; window.__odH=setInterval(()=>{ window.__od+=dist(window.__lx,window.__lz,TRUCK.x,TRUCK.z); window.__lx=TRUCK.x; window.__lz=TRUCK.z; },30); keys.add('w'); })()")
        await wait_game(6, 300)
        await G("keys.add('d')")
        await wait_game(6, 300)
        await G("(()=>{ keys.clear(); keys.add('s'); })()")
        await wait_game(2.5, 200)
        await G("(()=>{ keys.clear(); clearInterval(window.__odH); })()")
        r2 = await G("(()=>{ const t=trk(); return {gas:t.gas,od:window.__od,g0:window.__g0,tip:t.tip,drive:TRUCK.drive,doorR:+TRUCK.doorA.r.toFixed(2),v:TRUCK.v}; })()")
        used = r2['g0'] - r2['gas']
        want = r2['od'] / 1000 * 12
        print('   走った道のり', round(r2['od'], 1), 'm・燃料', round(used, 3), '%（目安', round(want, 3), '）')
        check(r2['od'] > 30 and abs(used - want) < 0.05 + want * 0.05, f'走った道のりで燃料が減る（1km で12%）')
        check(r2['tip'] == 0 and r2['drive'], f'道でいっぱいに切って走っても横転しない（{r2}）')
        tu = await G("""(()=>{ const was=TRUCK.lastB, a0=TRUCK.air; TRUCK.air=0; const run=(lat,q,n,v=12)=>{ TRUCK.lastB={q:Math.tan(q)}; TRUCK.tipT=0; let k=0; for(;k<n;k++) if(truckTipCheckDry(0.1,lat,v)) break; return k; }; // q＋：右が下がる（左へ曲がると外）
          const r={flat:run(8.8,0,40),flatIn:run(8.8,-0.3,40),out8:run(7.7,0.15,40),out8L:run(-7.7,-0.15,40),out5:run(7.7,0.08,40),slow:run(7.7,0.3,40,8)}; TRUCK.lastB=was; TRUCK.air=a0; TRUCK.tipT=0; return r; })()""")
        print('   横転の判定（0.1秒ごと・倒れるまでの回数。40＝倒れない）', tu)
        check(tu['flat'] == 40 and tu['flatIn'] == 40 and tu['out5'] == 40 and tu['out8'] < 8 and tu['out8L'] < 8 and tu['slow'] == 40,
              '横転の判定：平らな所・内へ傾いた所・外へ5°では、いっぱいに切っても倒れない。外へ 約9°傾いた所でいっぱいに切ると 0.5秒あまりで倒れる（左右とも）。9m/秒より遅いと倒れない')
        check(r2['doorR'] == 0, '運転中はドアが閉まっている')
        await G("(()=>{ trk().gas=0; truckStop(); })()")
        await G("(()=>{ window.__x1=TRUCK.x; window.__z1=TRUCK.z; keys.add('w'); })()")
        await wait_game(2.0)
        mv = await G("(()=>{ keys.clear(); return {d:dist(window.__x1,window.__z1,TRUCK.x,TRUCK.z),v:Math.abs(TRUCK.v),txt:document.getElementById('buffTxt').textContent}; })()")
        check(mv['d'] < 1.0, f'燃料0ではアクセルが効かない（{mv["d"]:.2f}m）')
        check('燃料 0%' in mv['txt'], f'運転中は画面に燃料と車体を出す（{mv["txt"][:40]}）')
        await G("(()=>{ inv.charcoal=1; truckExit(true); })()")
        await pg.wait_for_timeout(300)
        await G("truckRefuel(0)")
        g1 = await G("({gas:trk().gas,c:inv.charcoal})")
        check(g1['gas'] == 25 and g1['c'] == 0, f'木炭1つで燃料 +25%（{g1}）')

        # ================= ③ 獣の攻撃 =================
        await board()
        hp0 = await G("({p:P.hp,t:trk().hp})")
        r3 = await G("(()=>{ const r=hurtPlayer(20,P.x+1,P.z,6,null); return {r,p:P.hp,t:trk().hp}; })()")
        check(r3['r'] is False and r3['p'] == hp0['p'] and abs((hp0['t'] - r3['t']) - 12) < 0.01, f'運転中の攻撃は車体が受ける（20 → 車体 -12・主人公は {r3["p"]}）')

        # ================= ④ 横転 =================
        await G("(()=>{ TRUCK.tipT=0; TRUCK.air=0; TRUCK.lastB={q:0}; for(let i=0;i<8&&TRUCK.drive;i++) truckTipCheck(0.1,11.5,12); })()")
        await wait_game(1.0)
        r4 = await G("(()=>{ const t=trk(); return {tip:t.tip,drive:TRUCK.drive,hp:t.hp,rz:+TRUCK.m.rotation.z.toFixed(2),A:+(TRUCK.tipA||0).toFixed(2),px:dist(P.x,P.z,TRUCK.x,TRUCK.z),lab:(interactables()||{}).label}; })()")
        check(r4['tip'] == 1 and not r4['drive'] and abs(r4['hp'] - (r3['t'] - 25)) < 0.01, f'横の力が続くと右へ横転する → 降りる・車体 -25（{r4["hp"]}）')
        check(r4['A'] > 1.3 and r4['rz'] > 1.2, f'横に倒れた姿（{r4["A"]} rad）')
        await shot('kts_1_tipped', [5.5, 2.6, 6.0, 0, 0.8, 0])
        check(r4['lab'] and '起こす' in r4['lab'], f'そばで「起こす」（{r4["lab"]}・車から {r4["px"]:.1f}m）')
        await G("(()=>{ truckBoard(); })()")
        check(not await G("TRUCK.drive"), '横転したままは乗れない')
        await G("truckRight()")
        await wait_game(1.2)
        r4b = await G("({tip:trk().tip,A:+(TRUCK.tipA||0).toFixed(2)})")
        check(r4b['tip'] == 0 and r4b['A'] < 0.05, f'起こすと元に戻る {r4b}')

        # ================= ⑤ 車両基地 =================
        await G("(()=>{ Object.assign(inv,{wood:200,stone:100,iron:100,rope:100,hide:100}); })()")
        await close_menus()
        rc = await G("(()=>{ P.x=BENCH.x; P.z=BENCH.z+1.2; openCraft(); const b=document.getElementById('craft_depotBuild'); return b?{dis:b.disabled}:null; })()")
        check(rc is not None and not rc['dis'], f'作業台に「車両基地を建てる」が出る（KEI truck を直したあと）{rc}')
        await G("craft('depotBuild')")
        await close_menus()
        r5 = await G("({b:depotS().built,vis:!!DEPOT.g&&DEPOT.g.visible,cols:DEPOT.cols.filter(c=>c.active).length,inv:{wood:inv.wood,stone:inv.stone,iron:inv.iron,rope:inv.rope}})")
        check(r5['b'] == 1 and r5['vis'] and r5['cols'] == 14 and r5['inv'] == {'wood': 180, 'stone': 88, 'iron': 92, 'rope': 94}, f'建てると基地の形・当たり（柱6本・奥の壁・道具）が出る・素材を引く {r5}')
        # 南門の外から運転して屋根の下へ
        await put_truck(150, 88, math.pi)
        await board()
        await ev(AUTOPILOT)
        await G("window.__ap([[150,79],[150,71.5],[153.5,68.6],[158.5,68.6],[164.2,68.6]],4)")  # v0.79：南門から入って右（東）へ
        dn = await until("window.__apDone", 600)
        await wait_game(0.8)
        await G("truckExit(true)")
        r5b = await G("({x:TRUCK.x,z:TRUCK.z,park:depotParked(),log:window.__apLog.filter((p,i)=>i%10===0)})")
        print('   通った所', r5b['log'][:40])
        check(dn is True and r5b['park'], f'南門の外から運転して車両基地の屋根の下に止められる（{r5b["x"]:.1f}, {r5b["z"]:.1f}）')
        await shot('kts_2_depot', [8.8, 5.2, -9.6, 0, 1.2, 0])  # 拠点の内側（北西）の上から
        await G("(()=>{ P.x=TRUCK_SYS.depot.x-TRUCK_SYS.depot.W/2-0.8; P.z=TRUCK_SYS.depot.z+2.4; })()")
        await pg.wait_for_timeout(400)
        lab = await G("(interactables()||{}).label")
        check(lab and '車両基地（直す' in lab, f'基地のそばで「{lab}」')
        await G("trk().hp=40")
        await G("depotMenu()")
        menu = await G("[...document.querySelectorAll('#defenseChoice button')].map(b=>b.textContent)")
        print('   車両基地の一覧', menu)
        check(any('車体を直す' in m for m in menu) and any('改修 段階1' in m for m in menu) and any('荷台の作業台を作る' not in m and '荷台の作業台（改修 段階1で作れる）' in m for m in menu),
              '一覧：直す・改修 段階1・荷台の施設（段階で解放）')
        await close_menus()
        await G("truckRepairStep(true)")
        r5c = await G("({hp:trk().hp,iron:inv.iron})")
        check(r5c['hp'] == 100 and r5c['iron'] == 92 - 3, f'直せるだけ直す（20ずつ・屑鉄1と木材1）{r5c}')
        pf = []
        uo = await G("Object.fromEntries(Object.entries(TRUCK_SYS.fac).map(([k,f])=>[k,f.lv]))")
        check(uo == {'bench': 1, 'tower': 2, 'kiln': 3}, f'荷台の施設は 作業台（段階1）→ 見張り台（段階2）→ 炭焼き釜（段階3）の順に解放（2026-11-18）{uo}')
        for lv in range(1, 6):
            await G("truckUpgrade()")
            pf.append(await G("(()=>{ const t=trk(), f=truckPerf(); return {lv:t.lv,speed:f.speed,acc:f.acc,hp:t.hp,max:trkHpMax(t)}; })()"))
        await close_menus()
        print('   改修', pf)
        check([x['lv'] for x in pf] == [1, 2, 3, 4, 5] and [x['speed'] for x in pf] == [15.5, 17, 18.5, 20, 21.5] and [x['max'] for x in pf] == [130, 165, 200, 240, 280] and pf[-1]['hp'] == 280
              and all(pf[i]['acc'] < pf[i + 1]['acc'] for i in range(4)),
              '改修 段階1〜5（2026-11-18 に段階4・5を足した）：最高速度・耐久・加速が上がる（直っていれば耐久の増えた分も満たす）')
        for fid in ('bench', 'kiln', 'tower'):
            await G(f"truckFacBuild('{fid}')")
        r5d = await G("({fac:trk().fac,ch:TRUCK.bedG?TRUCK.bedG.children.length:0})")
        await wait_game(0.3)
        r5d['ch'] = await G("TRUCK.bedG?TRUCK.bedG.children.length:0")
        check(r5d['fac'] == {'bench': 1, 'kiln': 1, 'tower': 1} and r5d['ch'] >= 6, f'荷台の施設3つを作る・荷台に見える {r5d}')
        # 柱にぶつかる
        await put_truck(153.6, TRUCK_Z_POST, math.pi / 2)  # 基地の入口の北の柱へ東向きに
        await board()
        await G("(()=>{ window.__h0=trk().hp; TRUCK.vx=10; TRUCK.vz=0; TRUCK.bumpT=-9; })()")
        await wait_game(1.0)
        bump = await G("({d:window.__h0-trk().hp,x:TRUCK.x,v:TRUCK.v})")
        await G("truckExit(true)")
        check(bump['d'] > 8, f'柱に 10m/秒でぶつかると車体が傷む（-{bump["d"]:.1f}）')

        # ================= ⑥ 荷台 =================
        await put_truck(150.5, 61, 0)
        await G("(()=>{ P.x=TRUCK.x+0.6; P.z=TRUCK.z-3.0; const L=prog.f4.logs; for(let i=0;i<7;i++) L.push([TRUCK.x-3.6-Math.floor(i/3)*0.6,TRUCK.z-1.5+(i%3)*0.9,0,['t','m','k'][i%3]]); f4LogsDirty(); })()")  # 丸太は車の右の横に置く
        await wait_game(0.3)
        lab = await G("(interactables()||{}).label")
        check(lab and '荷台' in lab, f'車の後ろで「{lab}」')
        await G("(()=>{ inv.stone=5; bedMenu(); })()")
        menu = await G("[...document.querySelectorAll('#defenseChoice button')].map(b=>b.textContent)")
        await close_menus()
        print('   荷台の一覧', menu)
        check(any('近くの丸太を積む' in m for m in menu) and any('素材を積む' in m for m in menu), f'荷台の一覧（{len(menu)}こ）')
        for _ in range(8):
            await G("bedTakeGroundLog()")
        await wait_game(0.6)
        tg = await G("+TRUCK.doorA.tg.toFixed(2)")
        check(tg > 0.2, f'荷台に積むとあおりが下りる（{tg} rad）')
        r6 = await G("({logs:trk().bed.logs.slice(),left:prog.f4.logs.length,units:bedUnits(trk())})")
        check(len(r6['logs']) == 6 and r6['units'] == 60, f'丸太は6本まで（広さ60がいっぱい）{r6}')
        await wait_game(0.3)
        await shot('kts_3_bed_logs', [-2.6, 3.4, -5.2, 0, 1.2, -0.8])
        await G("bedDropLog()")
        await G("(()=>{ P.x=TRUCK.x+0.9; P.z=TRUCK.z-2.9; prog.f4.carry='k'; })()")
        await wait_game(0.2)
        lab = await G("(interactables()||{}).label")
        check(lab and '担いでいる丸太を荷台に積む' in lab, f'丸太を担いで車の後ろへ「{lab}」')
        await G("interact()")
        r6b = await G("({carry:prog.f4.carry,logs:trk().bed.logs.length})")
        check(r6b == {'carry': 0, 'logs': 6}, f'担いだ丸太を積む {r6b}')
        # 素材：丸太を下ろしてから
        await G("(()=>{ trk().bed.logs=['m','m']; inv.wood=100; inv.stone=5; })()")
        await G("bedLoadMats()")
        r6c = await G("({mats:Object.assign({},trk().bed.mats),wood:inv.wood,units:bedUnits(trk())})")
        check(r6c['units'] == 60 and r6c['wood'] == 60, f'素材は広さの残り（60−丸太2本の20＝40）まで積む {r6c}')
        await G("(()=>{ inv.wood=0; P.x=TRUCK.x+2.5; P.z=TRUCK.z; prog.arms.club=null; })()")
        aff = await G("bedAfford({wood:3})")
        await G("craft('club')")
        r6d = await G("({wood:inv.wood,bed:trk().bed.mats.wood||0,club:prog.arms.club!=null})")
        await G("(()=>{ P.x=TRUCK.x+20; P.z=TRUCK.z; })()")
        far = await G("bedAfford({wood:3})")
        check(aff and r6d['club'] and r6d['bed'] == r6c['mats'].get('wood', 0) - 3 and not far, f'車のそばでは作るときに荷台の素材を使う（木材 荷台 {r6d["bed"]}）・20m 離れると使わない')
        await close_menus()
        # 丸太置き場の近くで納める
        yd = await G("({x:F4.yard.x,z:F4.yard.z})")
        await put_truck(yd['x'] - 7, yd['z'] + 3, math.pi / 2)
        await G("(()=>{ trk().bed.logs=['t','m','k']; window.__w0=inv.wood; window.__d0=prog.f4.delivered; P.x=TRUCK.x-3.5; P.z=TRUCK.z; })()")
        await G("bedDeliverLogs()")
        r6e = await G("({dw:inv.wood-window.__w0,dd:prog.f4.delivered-window.__d0,logs:trk().bed.logs.length})")
        check(r6e == {'dw': 9, 'dd': 3, 'logs': 0}, f'丸太置き場の近くで納める（細い2・杉3・太い4 ＝ 木材+9）{r6e}')

        # ================= ⑦ 住民の運搬 =================
        await put_truck(150, 86, 0)
        await G("(()=>{ const t=trk(); t.bed.logs=['m','k']; t.bed.mats={stone:4}; window.__w0=inv.wood; window.__s0=inv.stone; P.x=npcGen.x+1.2; P.z=npcGen.z; })()")
        can = await G("haulCan()")
        await G("(()=>{ f9Cur=npcGen; renderNPC(); })()")
        btn = await G("(()=>{ const b=document.getElementById('npc_haul'); return b?b.textContent:null; })()")
        check(can and btn and '運んでもらう' in btn, f'源さんに頼める（車は南門の外・丸太置き場から {await G("dist(TRUCK.x,TRUCK.z,F4.yard.x,F4.yard.z).toFixed(0)")}m）「{btn}」')
        await G("(()=>{ TRUCK_SYS.haul.walk=7; TRUCK_SYS.haul.load=0.5; })()")  # テストだけ速く歩かせる（画面のない Chromium は遅い）
        await G("document.getElementById('npc_haul').click()")
        await pg.wait_for_timeout(300)
        await close_menus()
        await G("(()=>{ P.x=130; P.z=40; })()")  # 少し離れて見ている
        mid = await until("HAUL.on&&HAUL.load&&HAUL.walk?{gy:+(npcGen.m.g.position.y-groundH(npcGen.x,npcGen.z)).toFixed(2),carry:!!HAUL.mesh&&HAUL.mesh.visible,x:npcGen.x,z:npcGen.z}:null", 90)
        check(mid and abs(mid['gy']) < 0.15 and mid['carry'], f'源さんは見張り台から下りて、荷を担いで地面を歩く {mid}')
        await shot('kts_4_haul', [-6, 6.5, 2.5, 0, 0.3, -8])  # 南東の上から、車と南門
        done = await until("!HAUL.on", 900)
        await G("(()=>{ TRUCK_SYS.haul.walk=2.6; TRUCK_SYS.haul.load=1.4; })()")
        r7 = await G("({on:HAUL.on,dw:inv.wood-window.__w0,ds:inv.stone-window.__s0,bed:trk().bed,gx:npcGen.x,gz:npcGen.z,hx:npcGen.home.x,hz:npcGen.home.z,col:npcGen.col?npcGen.col.active:'なし',gy:npcGen.m.g.position.y-groundH(npcGen.x,npcGen.z)})")
        check(done and r7['dw'] == 7 and r7['ds'] == 4 and r7['bed']['logs'] == [] and r7['bed']['mats'] == {}, f'源さんが門を通って丸太2本（木材+7）と素材を運ぶ {r7["dw"]}・{r7["ds"]}')
        check(abs(r7['gx'] - r7['hx']) < 0.01 and r7['col'] in (True, 'なし'), f'運び終わると見張りの場所へ戻る（{r7["gy"]:.1f}m の高さ）')

        # ================= ⑧ 炭焼き釜・見張り台 =================
        await G("(()=>{ const t=trk(); t.bed.mats={}; inv.wood=10; P.x=TRUCK.x+2.4; P.z=TRUCK.z; kilnPut(); kilnPut(); })()")
        q = await G("trk().kiln.q")
        await G("(()=>{ kilnUpdate(41); kilnUpdate(41); })()")
        r8 = await G("({q:trk().kiln.q,c:trk().bed.mats.charcoal||0,see:truckSee()})")
        check(q == 2 and r8['q'] == 0 and r8['c'] == 2, f'荷台の炭焼き釜：木材3で木炭1つ（荷台へ）{r8}')
        check(r8['see'] == 90, f'見張り台：車のそばでは地図の獣が {r8["see"]}m まで')
        await G("(()=>{ P.x=TRUCK.x+30; })()")
        check(await G("truckSee()") == 60, '車から離れると 60m に戻る')

        # ================= ⑨ 上志比では光明寺の印を出さない =================
        r9 = await G("(()=>{ const was=REG.cur; REG.cur='kamishihi'; const a=questHere(); REG.cur=was; return {kami:a,home:questHere()}; })()")
        check(r9 == {'kami': False, 'home': True}, f'光明寺の依頼・目的の印は光明寺だけ（5990m の直し）{r9}')

        # ================= ⑩ 鱗の武器 =================
        await G("(()=>{ P.x=TRUCK_SYS.depot.x+6; P.z=TRUCK_SYS.depot.z-9; P.atk=null; P.dodge=null; prog.gear.equip={head:null,chest:null,legs:null,feet:null}; })()")  # 拠点の中（木のない所）
        r10 = await G("""(()=>{ const out={}; const lv=prog.level||1; for(const id of ['spear','scSpear','rwSpear']){ prog.arms[id]=WEAPONS[id].maxDur; P.weapon=id; P.dur=WEAPONS[id].maxDur; SCALE_FX.wk=null; f78HpSync();
      P.atk=null; P.dodge=null; P.ctrT=0; P.swT=9; P.st=100; P.exh=false; const okA=startAttack('heavy'); const st=P.st, exh=P.exh; P.atk=null; P.st=100; P.exh=false;
      out[id]={max:f31MaxHp(lv),arm:+f31Armor(100).toFixed(1),wpn:f78Wpn(),wave:!!scaleWaveSrc(),heavy:WEAPONS[id].heavy,okA,st:+st.toFixed(1),exh}; } return out; })()""")
        print('   鱗の武器', {k: (v['max'], v['arm'], v['wave'], v['heavy'], v['st'], v['exh']) for k, v in r10.items()})
        b0, sc, rw = r10['spear'], r10['scSpear'], r10['rwSpear']
        check(abs(sc['arm'] - b0['arm'] * 0.85) < 0.2 and sc['max'] == b0['max'] and not sc['wave'] and sc['okA'] and sc['st'] > 50, '蒼鱗の武器：受ける -15%・最大体力は同じ・衝撃波なし・強攻撃のスタミナはふつう')
        check(rw['max'] == round(b0['max'] * 0.85) and rw['arm'] == b0['arm'] and not rw['wave'] and rw['wpn']['speed'] == 0.12 and rw['wpn']['dodge'] == 0.15,
              '変異鱗の武器：最大体力 -15%・移動 +12%・回避の消費 -15%・衝撃波なし（2026-11-17 22:21）')
        check(rw['heavy'] == round(sc['heavy'] * 1.5) and rw['okA'] and rw['st'] == 0 and rw['exh'], f'変異鱗の武器の強攻撃：蒼鱗の1.5倍（{sc["heavy"]}→{rw["heavy"]}）・1回でスタミナをすべて使う（息切れ）')
        r10b = await G("""(()=>{ const g=prog.gear, set=s=>{ for(const k of G47S){ const id=s+'_'+k; if(!g.owned.includes(id)) g.owned.push(id); g.equip[k]=id; } }; P.weapon='spear';
      set('blue'); const blue={cut:+f47Stats().cut.toFixed(3),hp:f47HpMul(),speed:+f47Stats().speed.toFixed(3),wave:scaleWaveSrc()};
      set('raw'); const raw={cut:+f47Stats().cut.toFixed(3),hp:f47HpMul(),speed:+f47Stats().speed.toFixed(3),dodge:+f47Stats().dodge.toFixed(3),wave:scaleWaveSrc()};
      for(const k of G47S) g.equip[k]=null; return {blue,raw}; })()""")
        print('   鱗の防具一式', r10b)
        check(r10b['raw']['cut'] == r10b['blue']['cut'] and r10b['raw']['hp'] < 0.71 and r10b['blue']['hp'] == 1 and r10b['raw']['speed'] > 0.25 and r10b['raw']['dodge'] > 0.25 and r10b['blue']['wave'] is None and r10b['raw']['wave']['charge'] == 8,
              '変異した鱗の防具一式：防御は蒼鱗と同じ・最大体力 0.7倍・機動力が上がる・衝撃波は8秒でたまる（2026-11-17 22:21）')

        # ================= ⑪ セーブ → 続きから =================
        await G("(()=>{ const t=trk(); t.gas=63.5; t.hp=150; t.bed.logs=['k']; t.bed.mats={iron:3}; t.kiln.q=1; t.kiln.t=12; saveGame(); })()")
        before = await G("JSON.parse(JSON.stringify({t:trk(),d:depotS()}))")
        await boot(cont=True)
        await pg.wait_for_timeout(1500)
        after = await G("JSON.parse(JSON.stringify({t:trk(),d:depotS(),dv:!!DEPOT.g&&DEPOT.g.visible}))")
        keys_ = ('gas', 'hp', 'lv', 'bed', 'fac', 'tip', 'repaired', 'fueled')
        same = all(before['t'][k] == after['t'][k] for k in keys_) and before['t']['kiln']['q'] == after['t']['kiln']['q'] and abs(before['t']['kiln']['t'] - after['t']['kiln']['t']) < 5  # 炭焼き釜は読み込んだあとも進む
        check(same and after['d'] == {'built': 1} and after['dv'], f'セーブ → 続きから：燃料・車体・段階・荷台・施設・炭焼き・車両基地が戻る {({k: after["t"][k] for k in keys_})}')
        sv = await G("JSON.parse(localStorage.getItem(SAVE_KEY))")
        check(sv.get('v') == 1 and 'truck' in sv['chapter2']['progress'] and 'depot' in sv['chapter2']['progress'], 'セーブは v:1 のまま・chapter2.progress.truck と depot に入る')

        check(not errs, f'ページのエラーなし {errs[:3]}')
        await b.close()
    print('ALL OK' if ok else 'SOME FAILED')
    return ok


if __name__ == '__main__':
    import sys
    sys.exit(0 if asyncio.run(main()) else 1)
