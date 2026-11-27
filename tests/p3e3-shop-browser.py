#!/usr/bin/env python3
"""よろず屋の両階・暗転入力・同行と保存を、PC と iPhone 寸法の Chromium で確認する。"""

import asyncio
import json
import os
from pathlib import Path
import runpy
import sys
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

# 農家試験と同じ本編・評価用フック・章進行で起動する。
FARM = runpy.run_path(str(Path(__file__).with_name('p3e3-farm-browser.py')))
ROOT, HTML, BASE, PLAYING = (FARM[k] for k in ('ROOT', 'HTML', 'BASE', 'PLAYING'))
MAP_TEST = runpy.run_path(str(Path(__file__).with_name('p3e3-search-browser.py')))
SHOP = 'よろず屋に入る'
UP, DOWN, EXIT = '2階へ上がる', '1階へ下りる', '外へ出る'
READY = f"{PLAYING}&&performance.now()>=p3ShopActionAfter"
DOOR = "P3A.doors.find(d=>d.inId==='shop')"
FRONT = f"dist(P.x,P.z,({DOOR}).x,({DOOR}).z)<3"
SZ_FRONT = f"dist(SZ.x,SZ.z,({DOOR}).x,({DOOR}).z)<6&&szFree(SZ.x,SZ.z,SZ.r-0.01)"
ARRIVAL = "dist(P.x,P.z,REG.live.arrival.x,REG.live.arrival.z)<0.05"
SZ_POS = '[SZ.x,SZ.z,SZ.wx,SZ.wz]'
COUNTER = """window.shopFades=0; const oldFade=stfFade;
  stfFade=async on=>{
    if(on) window.shopFades++;
    await oldFade(on);
    if(!on&&window.probeEdge) await new Promise(done=>{window.uncoverShop=done});
  };
  for(const type of ['keydown','pointerdown']) window.addEventListener(type,e=>{
    if(!window.probeEdge||!e.isTrusted||(type==='keydown'&&e.key!=='e')) return;
    window.edgeEvents.push({id:e.target.id, fading:p3ShopFading, repeat:!!e.repeat,
      guarded:performance.now()<p3ShopActionAfter});
  },true);"""
QUIET_YARD = """(()=>{ const doors=P3A.doors.filter(d=>!d.future);
  for(const e of enemies) if(!e.removed&&doors.some(d=>dist(e.x,e.z,d.x,d.z)<150)) e.x+=900;
  p3bState().hq.beasts=1; })()"""
PROGRESS = """JSON.stringify([p3bState().hq,p3bState().e3,prog.chapter2.progress.e3farm,
  inv.oldParts,inv.iron,P.weapon,prog.arms])"""


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print('ok  ', message, flush=True)


async def main():
    three = Path(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read_bytes()
    shot_dir = Path(os.environ['SHOP_SHOTS']) if os.environ.get('SHOP_SHOTS') else None
    errors = []

    async def route(r):
        url = urlsplit(r.request.url)
        if url.path.endswith('/three.min.js'):
            await r.fulfill(body=three, content_type='application/javascript')
        elif url.netloc == 'game.local':
            f = (ROOT / url.path.lstrip('/')).resolve()
            if url.path in ['/', '/index.html']:
                await r.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            elif f.is_relative_to(ROOT) and f.is_file():
                await r.fulfill(path=str(f))
            else:
                await r.fulfill(status=404, body='')
        else:
            await r.abort()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        for touch in (False, True):
            w, h = (390, 844) if touch else (1280, 720)
            ctx = await browser.new_context(viewport={'width': w, 'height': h}, has_touch=touch, is_mobile=touch)
            await ctx.route('**/*', route)
            page = await ctx.new_page()
            page.on('pageerror', lambda err: errors.append(str(err)))
            page.set_default_timeout(180000)

            await page.clock.install()

            async def ev(code):
                return await page.evaluate('s=>window.__ev(s)', code)

            async def wait(code):
                await page.wait_for_function('s=>window.__ev(s)', arg=code)

            async def seconds(n):
                t = await ev('stats.time') + n
                await wait(f'stats.time>={t}')

            async def boot(new=False):
                await page.goto('http://game.local/', wait_until='load', timeout=300000)
                await wait("typeof P3IN==='object'")
                await ev(COUNTER)
                await page.locator('#btnNew' if new else '#btnContinue').click()
                if new:
                    for _ in range(8):
                        if await ev(PLAYING):
                            break
                        await page.locator('#dialog').click()
                        await page.wait_for_timeout(200)
                    await wait(PLAYING)
                    await ev(BASE)
                    await ev("regionTravel('kamishihi',null,{force:true})")
                await wait(f"{PLAYING}&&REG.cur==='kamishihi'")
                await ev(QUIET_YARD)

            async def at_door(id='house110', offset=0):
                await ev(f"""(()=>{{const d=P3A.doors.find(d=>d.id==={json.dumps(id)});
                  P.x=P._px=d.x+{offset}*Math.sin(d.facing||0); P.z=P._pz=d.z+{offset}*Math.cos(d.facing||0);
                  P.lvx48=P.lvz48=0;}})()""")

            async def at(x, z):
                await ev(f"""(()=>{{const o=P3A.interior.def.o; P.x=P._px=o.x+{x}; P.z=P._pz=o.z+{z};
                  P.lvx48=P.lvz48=0;}})()""")

            async def at_mark(id):
                await ev(f"""(()=>{{const m=P3A.interior.marks.find(m=>m.id==={json.dumps(id)});
                  P.x=P._px=m.x; P.z=P._pz=m.z; P.lvx48=P.lvz48=0;}})()""")

            async def raw_action():
                if touch:
                    await page.locator('#tbAct').tap()
                else:
                    await page.keyboard.press('e')

            async def act(label):
                await wait(f'{READY}&&curInter?.label==={json.dumps(label)}')
                await raw_action()

            async def cross(label, target):
                await wait(f'{READY}&&curInter?.label==={json.dumps(label)}')
                before = await ev('window.shopFades')
                await raw_action()
                await wait(f"({target})&&{READY}")
                check(await ev(f"window.shopFades==={before+1}&&!SZR.on&&!$('defenseChoice')"),
                      f'{w}×{h} {label} が1回だけ効く')

            async def boundary(label, target, next_label, next_mark=None):
                await wait(f'{READY}&&curInter?.label==={json.dumps(label)}')
                before = await ev('window.shopFades')
                await ev('window.probeEdge=true;window.edgeEvents=[];window.uncoverShop=null')
                if touch:
                    box = await page.locator('#tbAct').bounding_box()
                    xy = (box['x'] + box['width']/2, box['y'] + box['height']/2)
                    await page.touchscreen.tap(*xy)
                else:
                    await page.keyboard.down('e')
                # 本物の明転が済み、暗転面とロックを外す直前で同期する。
                await wait(f"({target})&&typeof window.uncoverShop==='function'")
                if next_mark:
                    await at_mark(next_mark)
                await wait("!$('touch').hidden" if touch else "S.mode==='playing'")
                # 通信・描画の速さで220msの境界を飛び越さないよう、この入力列だけ時計を止める。
                await page.clock.pause_at(await ev('new Date(Date.now()+1000).toISOString()'))
                try:
                    if touch:
                        await page.touchscreen.tap(*xy)
                    else:
                        await page.keyboard.down('e')
                        await page.keyboard.up('e')
                        await page.keyboard.down('e')
                    await ev('window.uncoverShop()')
                    check(await ev(f"({PLAYING})&&!p3ShopFading&&(curInter=interactables())?.label==={json.dumps(next_label)}"),
                          f'{label} の明転直後に次の「{next_label}」を操作できる位置')
                    if touch:
                        await page.touchscreen.tap(*xy)
                        await page.touchscreen.tap(*xy)
                    else:
                        await page.keyboard.down('e')
                        await page.keyboard.up('e')
                        await page.keyboard.down('e')
                        # 抑止が解けても、暗転直後から保持した物理キーは押し直しにならない。
                        await page.clock.fast_forward(await ev('Math.ceil(p3ShopActionAfter-performance.now())+1'))
                        await page.keyboard.down('e')
                        check(await ev("p3ShopKeyHeld&&!keys.has('e')"), '押しっぱなしはキー解放まで保留')
                        await page.keyboard.up('e')
                    events = await ev('window.edgeEvents')
                    pre = [e for e in events if e['fading']]
                    post = [e for e in events if not e['fading'] and e['guarded']]
                    hits = (any(e['id']=='stfFade' for e in pre) and
                            sum(e['id']=='tbAct' for e in post)==2) if touch else (
                            {e['repeat'] for e in pre}=={False, True} and
                            {e['repeat'] for e in post}=={False, True})
                    check(hits and await ev(f"({target})&&({PLAYING})&&window.shopFades==={before+1}"),
                          f'{w}×{h} {label} の明転直前・直後の実入力で移動は1回')
                finally:
                    await ev('window.probeEdge=false')
                    await page.clock.resume()

            def inside(level):
                return f"P3A.inside&&P3A.inId==='shop'&&P3A.interior.level==={level}"

            async def stairs(level):
                await at_mark('stairs')
                await cross(UP if level == 2 else DOWN, inside(level))
                check(await ev(f"""p3eShopFloorAt(P.x,P.z)==={level}&&szWalkable(P.x,P.z)&&
                  P3A.floors.every(f=>f.g.visible===(f.level==={level})&&f.cols.every(c=>c.active===f.g.visible))"""),
                      f'{level}階の到着後もその階だけに表示・当たり・歩行範囲がある')

            async def enter():
                await at_door()
                await cross(SHOP, inside(1))

            async def leave():
                await at_mark('exit')
                await cross(EXIT, '!P3A.inside')
                check(await ev(f'!REG.inB&&REG.live.group.visible&&({FRONT})'), '店先に戻り、屋外の当たりが復帰')

            async def raw_save():
                snapshot = await ev(f"""(()=>{{const before={SZ_POS};saveGame();return {{
                  before, after:{SZ_POS}, raw:localStorage.getItem(SAVE_KEY), chapter:prog.chapter2,
                  p3:prog.p3, arms:prog.arms, inv, hp:SZ.down?0:Math.max(1,Math.round(SZ.hp)),
                  state:[1,SZ.joined,SZ.order,SZ.region,SZ.down]
                }}}})()""")
                raw = snapshot['raw']
                d = json.loads(raw)
                chapter = d['chapter2']
                check(type(chapter['currentChapter']) is int and chapter['currentChapter']==2 and
                      chapter['currentRegion']=='kamishihi' and d['v']==1 and
                      await ev("storageOK&&SAVE_KEY==='eiheiji_vs_beasts_v010'"),
                      'localStorage の生の章番号は数値2、地域と版も一致')
                check(set(d)==save_keys and chapter==snapshot['chapter'] and
                      d['p3']==snapshot['p3'] and d['arms']==snapshot['arms'] and
                      d['inv']==snapshot['inv'], '既存の保存項目・章進行・拠点・装備・素材が一致')
                suzuki = d['suzuki']
                check(set(suzuki)=={'v','joined','order','region','x','z','wx','wz','hp','down'} and
                      all(type(suzuki[k]) in (float,int) for k in ('x','z','wx','wz','hp')) and
                      [suzuki[k] for k in ('v','joined','order','region','down')]==
                      snapshot['state'] and suzuki['hp']==snapshot['hp'], 'スズキの項目・型・指示を保持')
                if suzuki['order']=='wait' or suzuki['down']:
                    x,z = suzuki['x'],suzuki['z']
                    check((x,z)==(suzuki['wx'],suzuki['wz']) and
                          await ev(f"szFree({x},{z},SZ.r)&&szWalkable({x},{z})&&dist({x},{z},({DOOR}).x,({DOOR}).z)<6"),
                          '待機・転倒時の生の座標と待機目標は同じ店先の空き点')
                check(snapshot['after']==snapshot['before'], '保存してもプレイ中の位置と待機目標は変わらない')
                return raw

            async def save_reload():
                await raw_save()
                progress = await ev(PROGRESS)
                await boot()
                check(await ev(f'!P3A.inside&&!REG.inB&&({ARRIVAL})') and await ev(PROGRESS)==progress,
                      '主人公は上志比の屋外到着点で再開し、農家の地図・拠点・装備と素材を保持')

            await boot(new=True)
            await ev("(stfP().mutantMet=true,szJoin())")
            await at_door()
            for have_map in (0, 1):
                check(await ev(f"""(()=>{{p3bState().e3.map={have_map}; const l=[];p3aInteractables(l);
                  return !l.some(a=>a.label==='入口を調べる'||a.label==='よろず屋に入る');}})()"""),
                      f'設立前・地図{have_map}で入口案内なし')
            await ev("p3bState().e3.map=0; Object.assign(p3bState().hq,{talk:1,plan:1,sv:[1,1,1]});")
            await at_door(offset=1.6)
            await ev("szPut(P.x+0.6,P.z,0)")
            await act('入口を調べる')
            check(await ev("!P3A.inside") and await page.get_by_text('ここから入る手がかりがない', exact=True).count() == 1,
                  '地図なしでは追従指示より入口を優先し、指定文を表示')
            check(await ev(f"""(()=>{{const d={DOOR};p3bState().e3.map=1;const l=[];p3aInteractables(l);
              const a=l.find(a=>a.label==='よろず屋に入る');p3bState().e3.map=0;a.act();
              p3bState().hq.plan=0;p3bState().e3.map=1;a.act();
              p3bState().hq.plan=1;p3bState().e3.map=0;return !P3A.busy&&!P3A.inside;}})()"""),
                  '案内取得後に地図・設立条件が変化しても実行時に再判定')

            check(await ev("""(()=>{szPut(P.x,P.z,0);szOrder('wait');
              const waiting=interactables()?.act===szTalk;
              szDown();const rescue=interactables()?.act===szRescueStart;
              SZ.down=false;SZ.hp=SZ.maxHp;
              return waiting&&rescue;})()"""), '入口と重なっても待機指示・救助の優先順位を保つ')

            # 農家の本物の蔵の棚で地図を取得。単独入力の比較の間はスズキを店先で待たせる。
            await ev("szOrder('wait')")
            await at_door('house26')
            await cross('古い農家に入る', "P3A.inside&&P3A.inId==='farm'")
            await at_mark('search7')
            await act('蔵の棚を調べる')
            await page.locator('#dialog').click()
            await wait(f'{PLAYING}&&p3bState().e3.map')
            await at_mark('exit')
            await cross(EXIT, '!P3A.inside')
            for id, label in [('hq', '拠点本部に入る'), ('factory', '整備工場跡に入る')]:
                await at_door(id)
                await cross(label, f"P3A.inside&&P3A.inId==='{id}'")
                if id == 'hq':
                    outside = await ev(SZ_POS)
                    await ev("szOrder('follow');p3aSzFollow();P.facing=Math.PI/2;setCam(P.facing)")
                    await seconds(0.45)
                    hq_triangles = await ev('renderer.info.render.triangles')
                    await ev(f"szPut({outside[0]},{outside[1]},0);szOrder('wait')")
                await at_mark('exit')
                await cross(EXIT, '!P3A.inside')
            await at_door(offset=3.1)
            check(await ev("!interactables()?.preferOverFollow"), '操作距離の外では店の案内なし')
            await ev("szPut(P.x+1,P.z,0);szOrder('wait')")
            check(await ev("interactables()?.act===szTalk"), '入口を離れれば通常の指示が出る')
            save_keys = set(await ev("saveGame();Object.keys(JSON.parse(localStorage.getItem(SAVE_KEY)))"))
            await at_door(offset=1.8)
            await ev("szOrder('follow'); szPut(P.x+0.55,P.z,0)")
            await cross(SHOP, inside(1))
            check(await ev("szHere()&&p3eShopFloorAt(SZ.x,SZ.z)===1"), '追従指示と競合した店先から二人で入店')

            async def geometry(level):
                counts = await ev("""P3A.floors.map(f=>{let n=0; f.g.traverse(m=>{
                  if(m.isMesh) n+=(m.geometry.index?.count??m.geometry.attributes.position.count)/3*(m.isInstancedMesh?m.count:1);
                  });return n})""")
                active = await ev('P3A.floors.filter(f=>f.g.visible).map(f=>f.level)')
                check(active == [level] and 0 < counts[level-1] <= 10000,
                      f'表示階 {level} の屋内は輪郭込み {counts[level-1]} 三角形')
                await ev('P.facing=Math.PI/2;setCam(P.facing)')
                await seconds(0.45)
                screen = await ev('renderer.info.render.triangles')
                check(max(counts) <= 10000 and 0 < sum(counts) < 15000 and 0 < screen <= hq_triangles*1.15,
                      f'{w}×{h} {level}階の画面 {screen}、本部 {hq_triangles}、屋内両階 {counts}')
                check(await ev(f"""P3A.floors[0].mk.length===1&&P3A.floors[0].marks[0].exit&&
                  !P3A.floors[1].mk.length&&P3A.interior.marks.every(k=>k.exit||k.glow===false)"""),
                      '出口だけが発光する')

            async def ground_floor():
                fixture_hits = [
                    ('食品棚', 2.6, 2.2), ('日用品棚', 5.8, 2.2), ('農業棚', 2.7, 11.8),
                    ('カウンター', 6.3, 10.3), ('菓子ケース', 6.3, 12.19),
                    ('冷蔵庫', 7.02, 0.62), ('冷蔵庫の開いた扉', 7.56, 1.29),
                    ('奥壁の在庫棚', 10.5, 12.95), ('側壁の在庫棚', 12.09, 10.96),
                    ('木箱', 8.74, 11.73), ('台車', 8.85, 10.42),
                ]
                for name, x, z in fixture_hits:
                    check(await ev(f"!szFree(P3A.interior.def.o.x+{x},P3A.interior.def.o.z+{z},0.04)"),
                          f'{name}の実物の位置に当たりがある')
                paths = [
                    [(0.6,6.8),(6.2,6.8),(7.2,8.7),(8.8,8.7),(11,7.1),(11,5.6)],
                    [(1.6,5.4),(7.2,5.4)], [(1.6,8.2),(7.2,8.2)],
                    [(4.2,6.8),(4.2,0.8)], [(4.5,6.8),(4.5,12.2),(5.3,12.2)],
                    [(8.8,8.7),(11,9.6),(10.7,11.7),(10.7,12.0)],
                ]
                for path in paths:
                    samples = FARM['sample_path'](path)
                    check(await ev(f"""(()=>{{const {{o}}=P3A.interior.def;
                      return {json.dumps(samples)}.every(([x,z])=>szWalkable(o.x+x,o.z+z)&&
                        szFree(o.x+x,o.z+z,Math.max(P.r,SZ.r)));}})()"""),
                          f'二人分の当たり半径で経路 {path[0]} → {path[-1]} が通る')
                check(await ev("""(()=>{const f=P3A.interior, luminous=[];
                  f.g.traverse(m=>{
                    if(m.isLight) luminous.push(m);
                    if(!m.isMesh) return;
                    for(const mat of [].concat(m.material)) if(mat!==inkMat&&
                      (mat.isMeshBasicMaterial||mat.emissive?.getHex()>0||mat.blending===THREE.AdditiveBlending))
                      luminous.push(m);
                  });
                  const exit=f.marks.find(k=>k.exit);
                  return luminous.length===1&&luminous[0]===f.mk[0]&&
                    Math.hypot(luminous[0].position.x-exit.x,luminous[0].position.z-exit.z)<0.001;
                })()"""), '発光する実メッシュは出口の位置に一つ。冷蔵庫と照明は消灯')

                report = await ev("""(()=>{const f=P3A.interior, shadows=renderer.shadowMap.enabled;
                  let meshes=0;
                  f.g.traverse(m=>{if(m.isMesh) meshes++});
                  try {
                    renderer.shadowMap.enabled=false;
                    renderer.render(scene,camera); const withShop=renderer.info.render.calls;
                    f.g.visible=false; renderer.render(scene,camera);
                    return [meshes,withShop-renderer.info.render.calls];
                  } finally {f.g.visible=true;renderer.shadowMap.enabled=shadows;renderer.render(scene,camera)}
                })()""")
                check(0 < report[1] <= report[0] <= 50,
                      f'1階は {report[0]} メッシュ、入口からの屋内通常描画は {report[1]} calls')

            async def screenshots():
                if shot_dir is None:
                    return
                shot_dir.mkdir(parents=True, exist_ok=True)
                previous = await ev('[prog.f10.tod,lightMode,P.facing,cam.pitch.in]')
                spots = [('entry',1.6,6.8,1.57), ('sales',4.2,4.8,3.14),
                         ('register',4.7,10.2,0.89), ('stock',10.8,9.6,0.08)]
                try:
                    await ev("prog.f10.tod=6*P3B.hour;lightMode='day';snapLight();cam.pitch.in=0")
                    for name, x, z, yaw in spots:
                        await at(x,z)
                        await ev(f'P.facing={yaw};setCam(P.facing)')
                        await seconds(0.65)
                        check(await ev("p3bClock()[0]===12&&lightMode==='day'"), f'{name} を昼に撮影')
                        await page.screenshot(path=str(shot_dir / f'{name}-{w}x{h}.png'))
                finally:
                    await at(1.6,6.8)
                    await ev(f"""[prog.f10.tod,lightMode,P.facing,cam.pitch.in]={json.dumps(previous)};
                      snapLight();setCam(P.facing);p3aSzFollow()""")

            await geometry(1)
            await ground_floor()
            await screenshots()
            check(await ev("""(()=>{const {o}=P3A.interior.def, blocked=(x,z)=>!szFree(o.x+x,o.z+z,0.42);
              const path=[[1.6,6.8],[6.2,6.8],[7.2,8.7],[8.8,8.7],[11,7.1],[11,5.6]];
              return [[0,2],[8,4],[12.6,7],[2.6,2.2],[5.8,2.2],[2.7,11.8],[6.3,10.3],[10.5,12.95],[11,2.7]]
                .every(([x,z])=>blocked(x,z))&&path.every(([x,z],i)=>!blocked(x,z)&&(!i||
                  szLine(o.x+path[i-1][0],o.z+path[i-1][1],o.x+x,o.z+z)));
              })()"""), '外壁・仕切り・商品棚・レジ・段の当たりと中央通路から階段までの経路')
            if not touch:
                await at(1.55, 2.2)
                await ev("P.facing=Math.PI/2;setCam(P.facing);cam.inYaw=null")
                await page.keyboard.down('w')
                await seconds(0.4)
                await page.keyboard.up('w')
                check(await ev("Math.abs(P.x-P3A.interior.def.o.x-1.7)<0.04"), '実際の前進入力でも食品棚の手前で止まる')
            await at(9.65, 5.6)
            check(await ev("!interactables()?.preferOverFollow"), '段の横からは階移動できない')
            await at(11, 6.5)
            await ev("szPut(P.x+0.2,P.z+0.15,0)")
            await cross(UP, inside(2))
            await geometry(2)
            if not touch:
                await ev("P.facing=0;setCam(0);cam.inYaw=null")
                before_z = await ev('P.z')
                await page.keyboard.down('w')
                await seconds(0.35)
                await page.keyboard.up('w')
                check(await ev(f"P.z>{before_z}+0.4&&p3eShopFloorAt(P.x,P.z)===2"), '上階到着後の最初の前進が上階内で効く')
            await ev('p3bRebuild()')
            await seconds(0.35)
            check(await ev("""szHere()&&p3eShopFloorAt(P.x,P.z)===2&&p3eShopFloorAt(SZ.x,SZ.z)===2&&
              REG.inB.minX===P3IN.shop.floors[1].o.x&&P3A.floors[0].cols.every(c=>!c.active)&&
              P3A.interior.rooms.map(r=>r.name).join()==='居間,寝室,踊り場,台所,収納'"""),
                  '再構築後も二人は2階。店主の住まいの部屋が残る')

            await stairs(1)
            await leave()
            check(await ev("SZ.order==='follow'&&szHere()&&dist(P.x,P.z,SZ.x,SZ.z)<8"), '同行者も店先へ出る')
            # 次の意図的な入力が、それぞれ次の遷移を一度だけ起こす。
            await at_door()
            await boundary(SHOP, inside(1), UP, 'stairs')
            await boundary(UP, inside(2), DOWN, 'stairs')
            await boundary(DOWN, inside(1), EXIT, 'exit')
            await boundary(EXIT, '!P3A.inside', SHOP)
            await cross(SHOP, inside(1))
            await leave()

            if touch:
                await page.locator('#tbMap').tap()
            else:
                await page.keyboard.press('g')
            await page.locator('#oldMapLegend').wait_for(state='visible')
            trace = await ev(MAP_TEST['TRACE_MAP']+'(false)')
            check({'よろず屋','集会所'}.issubset(trace['labels']) and trace['outlines']==2 and
                  sum(c[3].startswith('rgba(164, 224, 146,') for c in trace['circles'])==12,
                  '退出後の全体地図に建物の名前と輪郭2件、薬草の円12件')
            await page.locator('#mapClose').click()

            for id,label,room in [('house26','古い農家に入る','farm'),('hq','拠点本部に入る','hq'),
                                  ('factory','整備工場跡に入る','factory')]:
                await at_door(id, 1.8 if room=='farm' else 0)
                if room=='farm':
                    check(await ev("""(()=>{szPut(P.x+0.1,P.z,0);const offers=[];szInteractables(offers);
                      return offers.some(a=>a.act===szTalk&&a.d<1.8)&&SZ.order==='follow'&&
                        interactables()?.label==='古い農家に入る';})()"""),
                          '退出後、農家の入口で近くの同行者より入室を優先')
                await cross(label, f"P3A.inside&&P3A.inId==='{room}'")
                if room=='farm':
                    # 土間と囲炉裏の間の開口を振り返り、手前の上壁だけが消える構図。
                    await at(7.0,18.1)
                    await ev('cam.pitch.in=0;P.facing=Math.PI/2;setCam(P.facing)')
                    for key,angle in [('x','< -0.10'),('z','> 0.12')]:
                        await page.keyboard.down(key)
                        await wait('cam.pitch.in'+angle)
                        await page.keyboard.up(key)
                        await wait("""P3A.interior.uppers.some(u=>u.x0===21006&&u.x1===21006&&
                          u.z0<21138.1&&u.z1>21138.1&&!u.m.visible)&&
                          P3A.interior.uppers.some(u=>u.x0===21011&&u.m.visible)""")
                        check(await ev('cam.pitch.in'+angle), f'農家のカメラ上下（{key}）で手前の上壁が隠れ、奥の上壁は見える')
                    await ev('cam.pitch.in=0')
                await at_mark('exit')
                await cross(EXIT, '!P3A.inside&&!REG.inB&&REG.live.group.visible')
            await enter()
            await save_reload()
            await wait("!SZ.place&&szHere()")
            check(await ev("SZ.order==='follow'&&dist(P.x,P.z,SZ.x,SZ.z)<8"), '店内保存した追従者は屋外到着点の主人公に同行')
            await enter()
            await stairs(2)
            # 待機点の横で、一度は本物の指示メニューから「ここで待て」を選ぶ。
            await at(4, 6)
            await ev("szPut(P.x+1.05,P.z,0)")
            await act('スズキに指示する')
            await page.get_by_role('button', name='ここで待て', exact=True).click()
            stationary = await ev(SZ_POS)
            await stairs(1)
            await seconds(0.8)
            check(await ev(SZ_POS) == stationary and await ev("!szHere()&&!SZ.m.g.visible&&!SZR.on"),
                  '別階の待機者は非表示。位置と待機目標が押し戻されない')
            await stairs(2)
            check(await ev(SZ_POS) == stationary and await ev('szHere()'), '同じ待機位置で再会')
            await stairs(1)
            await leave()
            check(await ev(f"SZ.order==='wait'&&SZ.x===SZ.wx&&SZ.z===SZ.wz&&({SZ_FRONT})"),
                  '別階で待たせて退出すると店先に戻り、待機目標も一致')
            outside = await ev(SZ_POS)
            await enter()
            await stairs(2)
            check(await ev(SZ_POS) == outside and await ev('!szHere()'), '屋外の待機者は入店・階移動で動かない')
            await save_reload()
            check(await ev(f"SZ.order==='wait'&&({SZ_FRONT})") and
                  all(abs(a-b)<0.03 for a,b in zip(outside, await ev(SZ_POS))), '店外の待機位置も読み戻せる')

            for level in (1,2):
                await ev("szOrder('follow')")
                await enter()
                await at(4, 6.8)
                await ev("szPut(P.x+1.1,P.z,0);szOrder('wait')")
                if level==2:
                    await stairs(2)
                await save_reload()
                check(await ev(f"SZ.order==='wait'&&SZ.x===SZ.wx&&SZ.z===SZ.wz&&({SZ_FRONT})"),
                      f'{level}階保存から1階の待機者は店先へ')

            # 2階で倒れた直後と、主人公だけが1階へ戻った後の両方から再開する。
            for level in (2,1):
                await ev("SZ.down=false;SZ.hp=SZ.maxHp;szOrder('follow')")
                await enter()
                await stairs(2)
                await ev('szDown()')
                if level==1:
                    down = await ev('[SZ.x,SZ.z]')
                    await stairs(1)
                    check(await ev('[SZ.x,SZ.z]') == down and await ev("SZ.down&&!szHere()&&!SZ.m.g.visible"),
                          '転倒者は階を移らない')
                down_save = await raw_save()
                if level==1:
                    await leave()
                    check(await ev(f"SZ.down&&SZ.hp===0&&({SZ_FRONT})"), '退出時に倒れたまま店先に戻る')
                    await ev(f'localStorage.setItem(SAVE_KEY,{json.dumps(down_save)})')
                await boot()
                check(await ev(f"SZ.down&&SZ.hp===0&&({SZ_FRONT})&&({ARRIVAL})"),
                      f'{level}階保存でも2階の転倒者は店先、主人公は屋外到着点に復帰')

            # 入口帯を離れて救助の長押し。iPhone は実際のタッチ開始・終了を送る。
            await ev(f"""(()=>{{const d={DOOR};P.x=SZ.x+Math.sin(d.facing)*1.4;P.z=SZ.z+Math.cos(d.facing)*1.4;}})()""")
            await wait("curInter?.act===szRescueStart")
            if touch:
                button = await page.locator('#tbAct').bounding_box()
                cdp = await ctx.new_cdp_session(page)
                finger = {'x': button['x']+button['width']/2, 'y': button['y']+button['height']/2}
                await cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [finger]})
                await wait('!SZ.down')
                await cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
            else:
                await page.keyboard.down('e')
                await wait('!SZ.down')
                await page.keyboard.up('e')
            check(await ev('SZ.hp>0&&!SZR.on'), '店先で助け起こせる')
            for shop in (False, True):
                check(await ev(f"""(async()=>{{const mode=S.mode, fault=new Error('暗転中の試験');
                  try{{await p3inTransition({json.dumps(shop)},()=>{{throw fault}});}}
                  catch(e){{const fade=stfFadeEl();return e===fault&&S.mode===mode&&
                    !P3A.busy&&!p3ShopFading&&fade.style.opacity==='0'&&!fade.classList.contains('shopTransition');}}
                  return false;}})()"""), '移動の例外後に元のモード・暗転面・入力ロックが復帰')
            await ctx.close()
        check(not errors, f'ページエラー {errors}')
        await browser.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f'FAIL {exc}', file=sys.stderr)
        sys.exit(1)
