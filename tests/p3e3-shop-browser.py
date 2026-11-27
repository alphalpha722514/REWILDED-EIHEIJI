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
SHOP = 'よろず屋に入る'
UP, DOWN, EXIT = '2階へ上がる', '1階へ下りる', '外へ出る'
READY = f"{PLAYING}&&performance.now()>=p3ShopActionAfter"
DOOR = "P3A.doors.find(d=>d.inId==='shop')"
FRONT = f"dist(P.x,P.z,({DOOR}).x,({DOOR}).z)<3"
SZ_FRONT = f"dist(SZ.x,SZ.z,({DOOR}).x,({DOOR}).z)<6&&szFree(SZ.x,SZ.z,SZ.r-0.01)"
SZ_POS = '[SZ.x,SZ.z,SZ.wx,SZ.wz]'
COUNTER = """window.shopFades=0; const oldFade=stfFade;
  stfFade=async on=>{if(on) window.shopFades++; await oldFade(on)};"""
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

            async def cross(label, target, stress=False):
                await wait(f'{READY}&&curInter?.label==={json.dumps(label)}')
                before = await ev('window.shopFades')
                if stress and touch:
                    box = await page.locator('#tbAct').bounding_box()
                    x, y = box['x']+box['width']/2, box['y']+box['height']/2
                    # 最初は実ボタンをタップ。暗転で非表示になる間も同じ画面位置を押す。
                    await page.touchscreen.tap(x, y)
                    for _ in range(2):
                        await page.touchscreen.tap(x, y)
                    await wait(target)
                    await page.touchscreen.tap(x, y)
                    await page.touchscreen.tap(x, y)
                elif stress:
                    await page.keyboard.down('e')
                    await page.keyboard.down('e')  # repeat=true
                    await wait(f'window.shopFades>{before}')
                    # 遷移中に離して連打し、最後の押下を明転後も保持する。
                    await page.keyboard.up('e')
                    await page.keyboard.press('e')
                    await page.keyboard.down('e')
                    await wait(f"({target})&&{PLAYING}")
                    await page.keyboard.down('e')
                    await page.keyboard.up('e')
                else:
                    await raw_action()
                await wait(f"({target})&&{PLAYING}")
                await seconds(0.35)
                check(await ev(f"window.shopFades==={before+1}&&({target})&&{PLAYING}&&!SZR.on&&!$('defenseChoice')"),
                      f'{w}×{h} {label} が1回だけ効く')

            def inside(level):
                return f"P3A.inside&&P3A.inId==='shop'&&P3A.interior.level==={level}"

            async def stairs(level, stress=False):
                await at_mark('stairs')
                await cross(UP if level == 2 else DOWN, inside(level), stress)
                check(await ev(f"""p3eShopFloorAt(P.x,P.z)==={level}&&szWalkable(P.x,P.z)&&
                  P3A.floors.every(f=>f.g.visible===(f.level==={level})&&f.cols.every(c=>c.active===f.g.visible))"""),
                      f'{level}階の到着後もその階だけに表示・当たり・歩行範囲がある')

            async def enter(stress=False):
                await at_door()
                await cross(SHOP, inside(1), stress)

            async def leave(stress=False):
                await at_mark('exit')
                await cross(EXIT, '!P3A.inside', stress)
                check(await ev(f'!REG.inB&&REG.live.group.visible&&({FRONT})'), '店先に戻り、屋外の当たりが復帰')

            async def save_reload():
                coords = await ev(SZ_POS)
                await ev('saveGame()')
                check(await ev(SZ_POS) == coords, '保存してもプレイ中の位置と待機目標は変わらない')
                p = await ev(PROGRESS)
                check(await ev("""(()=>{const d=readSave();return storageOK&&d.v===1&&SAVE_KEY==='eiheiji_vs_beasts_v010'&&
                  d.chapter2.currentRegion==='kamishihi'&&chapter2State(d.chapter2,true).currentChapter===2&&
                  !p3eShopFloorAt(d.suzuki.x,d.suzuki.z)&&Object.keys(d.p3.e3).sort().join()==='farm,map,s'})()"""),
                      '既存の地域・版・調査項目で保存し、スズキは屋外で再開できる座標')
                await boot()
                check(await ev(f'!P3A.inside&&!REG.inB&&({FRONT})') and await ev(PROGRESS) == p,
                      'つづきからは店先。地図・農家調査・拠点・装備と素材を保持')

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
            await at_door(offset=1.8)
            await ev("szOrder('follow'); szPut(P.x+0.55,P.z,0)")
            await cross(SHOP, inside(1), stress=True)
            check(await ev("szHere()&&p3eShopFloorAt(SZ.x,SZ.z)===1"), '追従指示と競合した店先から二人で入店')

            async def geometry(level):
                counts = await ev("""P3A.floors.map(f=>{let n=0; f.g.traverse(m=>{
                  if(m.isMesh) n+=(m.geometry.index?.count??m.geometry.attributes.position.count)/3*(m.isInstancedMesh?m.count:1);
                  });return n})""")
                await ev('P.facing=Math.PI/2;setCam(P.facing)')
                await seconds(0.45)
                screen = await ev('renderer.info.render.triangles')
                check(max(counts) <= 10000 and 0 < sum(counts) < 15000 and 0 < screen <= hq_triangles*1.15,
                      f'{w}×{h} {level}階の画面 {screen}、本部 {hq_triangles}、屋内両階 {counts}')
                check(await ev(f"""P3A.floors[0].mk.length===1&&P3A.floors[0].marks[0].exit&&
                  !P3A.floors[1].mk.length&&P3A.interior.marks.every(k=>k.exit||k.glow===false)"""),
                      '出口だけが発光する')

            await geometry(1)
            check(await ev("""(()=>{const {o}=P3A.interior.def, blocked=(x,z)=>!szFree(o.x+x,o.z+z,0.42);
              const path=[[1.6,6.8],[6.2,6.8],[7.2,8.7],[8.8,8.7],[11,7.1],[11,5.6]];
              return [[0,2],[8,4],[12.6,7],[2.6,2.2],[5.8,2.2],[2.7,11.8],[6.3,10.3],[10.5,12.95],[11,2.7]]
                .every(([x,z])=>blocked(x,z))&&path.every(([x,z],i)=>!blocked(x,z)&&(!i||
                  szLine(o.x+path[i-1][0],o.z+path[i-1][1],o.x+x,o.z+z)));
              })()"""), '外壁・仕切り・仮棚・レジ・段の当たりと中央通路から階段までの経路')
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
            await cross(UP, inside(2), stress=True)
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
            await leave(stress=True)
            check(await ev("SZ.order==='follow'&&szHere()&&dist(P.x,P.z,SZ.x,SZ.z)<8"), '同行者も店先へ出る')
            await enter()
            await save_reload()
            await wait("!SZ.place&&szHere()")
            check(await ev("SZ.order==='follow'&&dist(P.x,P.z,SZ.x,SZ.z)<8"), '店内保存した追従者も店先で再開')
            await enter()
            await stairs(2)
            # 待機点の横で、一度は本物の指示メニューから「ここで待て」を選ぶ。
            await at(4, 6)
            await ev("szPut(P.x+1.05,P.z,0)")
            await act('スズキに指示する')
            await page.get_by_role('button', name='ここで待て', exact=True).click()
            stationary = await ev(SZ_POS)
            await stairs(1, stress=True)
            await seconds(0.8)
            check(await ev(SZ_POS) == stationary and await ev("!szHere()&&!SZ.m.g.visible&&!SZR.on"),
                  '別階の待機者は非表示。位置と待機目標が押し戻されない')
            await stairs(2)
            check(await ev(SZ_POS) == stationary and await ev('szHere()'), '同じ待機位置で再会')
            await stairs(1)
            await leave(stress=True)
            check(await ev(f"SZ.order==='wait'&&SZ.x===SZ.wx&&SZ.z===SZ.wz&&({SZ_FRONT})"),
                  '別階で待たせて退出すると店先に戻り、待機目標も一致')
            outside = await ev(SZ_POS)
            await enter()
            await stairs(2)
            check(await ev(SZ_POS) == outside and await ev('!szHere()'), '屋外の待機者は入店・階移動で動かない')
            await save_reload()
            check(await ev(f"SZ.order==='wait'&&({SZ_FRONT})") and
                  all(abs(a-b)<0.03 for a,b in zip(outside, await ev(SZ_POS))), '店外の待機位置も読み戻せる')

            await ev("szOrder('follow')")
            await enter()
            await at(4, 6.8)
            await ev("szPut(P.x+1.1,P.z,0);szOrder('wait')")
            await stairs(2)
            await save_reload()
            check(await ev(f"SZ.order==='wait'&&SZ.x===SZ.wx&&SZ.z===SZ.wz&&({SZ_FRONT})"), '店内1階の待機者は再開時に店先へ')
            await ev("szOrder('follow')")
            await enter()
            await stairs(2)
            await ev('szDown()')
            down = await ev('[SZ.x,SZ.z]')
            await stairs(1)
            check(await ev('[SZ.x,SZ.z]') == down and await ev("SZ.down&&!szHere()&&!SZ.m.g.visible"), '転倒者は階を移らない')
            await ev('saveGame()')
            down_save = await ev('localStorage.getItem(SAVE_KEY)')
            await leave()
            check(await ev(f"SZ.down&&SZ.hp===0&&({SZ_FRONT})"), '退出時に倒れたまま店先に戻る')
            await ev(f'localStorage.setItem(SAVE_KEY,{json.dumps(down_save)})')
            await boot()
            check(await ev(f"SZ.down&&SZ.hp===0&&({SZ_FRONT})&&({FRONT})"), '1階保存でも2階の転倒状態を保って店先で再開')

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
            await ctx.close()
        check(not errors, f'ページエラー {errors}')
        await browser.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f'FAIL {exc}', file=sys.stderr)
        sys.exit(1)
