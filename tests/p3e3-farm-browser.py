#!/usr/bin/env python3
"""古い農家の入退室・間取り・当たり・同行・保存を画面のない Chromium で確認する。"""

import asyncio
import json
import math
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / 'index.html').read_text(encoding='utf8').replace(
    'function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){', 1)
BASE = """(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; return 1; })()"""
ROOMS = [
    ['doma', '土間', 0, 4.4, 6, 21.6],
    ['irori', '囲炉裏の間', 6, 13, 11, 21.6],
    ['zashiki', '座敷', 11, 13, 16.3, 21.6],
    ['nando', '納戸', 6, 4.4, 11, 13],
    ['kuramae', '蔵前', 11, 4.4, 16.3, 13],
    ['kura', '蔵', 11, 0, 16, 4.4],
]
GAPS = [[0, 15.6, 2.4], [6, 17.4, 6.0], [8.4, 13, 2], [13.6, 13, 2],
        [11, 8.7, 2], [11, 17.3, 2], [13.5, 4.4, 2]]
MAIN_PATH = [[1.6, 15.6], [3.2, 19.05], [6.9, 19.05], [10.07, 19.05],
             [10.07, 17.3], [13.6, 17.3], [13.6, 8.8], [13.5, 4.4], [13.5, 2.3]]
SIDE_PATH = [[6.9, 15.5], [8.4, 14.0], [8.4, 8.7], [12.5, 8.7]]
HQ = ['入口ホール', '倉庫', '総合作業場', '廊下', '機械室', '事務所跡', '階段室',
      '2階の廊下', '共同住居1', '共同住居2', '拠点管理', '閉じた部屋（復興で開く）', '閉じた部屋（復興で開く）']
FACTORY = ['整備場', '部品庫', '事務所跡']
PLAYING = "S.mode==='playing'&&!P3A.busy&&!REG.busy"
FARM_LABEL = '古い農家に入る'


def sample_path(points):
    samples = [points[0]]
    for (x0, z0), (x1, z1) in zip(points, points[1:]):
        count = math.ceil(math.hypot(x1 - x0, z1 - z0) / 0.5)
        samples.extend([x0 + (x1 - x0) * i / count, z0 + (z1 - z0) * i / count]
                       for i in range(1, count + 1))
    return samples


async def main():
    failures = []
    errors = []
    three = Path(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read_bytes()
    shot_dir = Path(os.environ['E3_SHOTS']) if os.environ.get('E3_SHOTS') else None

    def check(condition, message):
        print(('ok   ' if condition else 'FAIL ') + message, flush=True)
        if not condition:
            failures.append(message)

    async def route(request):
        url = urlsplit(request.request.url)
        if url.path.endswith('/three.min.js'):
            return await request.fulfill(body=three, content_type='application/javascript')
        if url.netloc == 'game.local':
            if url.path in ('/', '/index.html'):
                return await request.fulfill(body=HTML, content_type='text/html; charset=utf-8')
            file = (ROOT / url.path.lstrip('/')).resolve()
            if file.is_relative_to(ROOT) and file.is_file():
                return await request.fulfill(path=str(file))
            return await request.fulfill(status=404, body='')
        await request.abort()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])

        async def open_page(width, height, touch=False):
            ctx = await browser.new_context(
                viewport={'width': width, 'height': height}, has_touch=touch, is_mobile=touch)
            await ctx.route('**/*', route)
            page = await ctx.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            return ctx, page

        ctx, page = await open_page(1280, 720)

        async def ev(code):
            return await page.evaluate('code=>window.__ev(code)', code)

        async def wait(code):
            await page.wait_for_function('code=>window.__ev(code)', arg=code, timeout=180000)

        async def game_seconds(seconds):
            until = await ev('stats.time') + seconds
            await wait(f'stats.time>={until}')

        async def boot(button):
            await page.goto('http://game.local/', wait_until='load', timeout=300000)
            await wait("typeof P3IN==='object'")
            await page.locator(button).click()

        async def dialog_until(done):
            for _ in range(24):
                await wait(f"!$('dialog').hidden||({done})")
                if await ev(done):
                    return
                await page.locator('#dialog').click()
            raise RuntimeError('会話が終了しない')

        async def at_door(door_id):
            return await ev(f"""(()=>{{ const d=P3A.doors.find(k=>k.id==={json.dumps(door_id)});
              P.x=d.x; P.z=d.z; return [d.x,d.z]; }})()""")

        async def at_room(x, z):
            await ev(f'(P.x=P3IN.farm.o.x+{x},P.z=P3IN.farm.o.z+{z})')

        async def offer(label, act=False):
            return await ev(f"""(()=>{{ const L=[]; p3aInteractables(L);
              const item=L.find(k=>k.label.includes({json.dumps(label)}));
              if(item&&{json.dumps(act)}) item.act(); return item?.label||''; }})()""")

        async def enter(door_id, label, touch=False):
            entry = await at_door(door_id)
            if touch:
                await wait(f'curInter?.label==={json.dumps(label)}')
                await page.locator('#tbAct').tap()
            elif not await offer(label, True):
                raise RuntimeError(f'入口の案内が出ない（{label}）')
            await wait(f"{PLAYING}&&P3A.inside")
            return entry

        async def leave(touch=False):
            await ev("(()=>{ const m=P3A.interior.marks.find(k=>k.exit); P.x=m.x; P.z=m.z; })()")
            if touch:
                await wait("curInter?.label==='外へ出る'")
                await page.locator('#tbAct').tap()
            elif not await offer('外へ出る', True):
                raise RuntimeError('出口の案内が出ない')
            await wait(f'{PLAYING}&&!P3A.inside')

        async def continue_game():
            await boot('#btnContinue')
            await wait(f"{PLAYING}&&REG.cur==='kamishihi'&&P3A.on")

        async def entry_triangles():
            # 入室地点と向きをそろえ、同じ画面サイズでカメラが落ち着いた後のフレームを読む。
            await ev("""(()=>{ const def=P3IN[P3A.inId];
              P.x=def.o.x+def.entry.x; P.z=def.o.z+def.entry.z;
              P.facing=Math.PI/2; setCam(P.facing); p3aSzFollow();
            })()""")
            await game_seconds(0.45)
            return await ev('renderer.info.render.triangles')

        async def screenshots(width, height):
            if not shot_dir:
                return
            shot_dir.mkdir(parents=True, exist_ok=True)
            spots = [(3, 10), (7.3, 19.5), (13.6, 16.5),
                     (8.5, 9.4), (13.6, 9.5), (13.5, 2.3)]
            for (room, *_), (x, z) in zip(ROOMS, spots):
                await at_room(x, z)
                await game_seconds(0.45)
                await page.screenshot(path=str(shot_dir / f'{room}-{width}x{height}.png'))

        await boot('#btnNew')
        await dialog_until("$('dialog').hidden&&S.mode==='playing'")
        await ev(BASE)
        await ev("regionTravel('kamishihi',null,{force:true})")
        await wait(f"{PLAYING}&&P3A.on")
        # 前庭と農家付近の獣が、入口を調べている間に来ないようにする
        await ev("""(()=>{ const ds=P3A.doors.filter(d=>['hq','factory','house26'].includes(d.id));
          for(const e of enemies) if(!e.removed&&ds.some(d=>dist(e.x,e.z,d.x,d.z)<220)) e.x+=900;
          p3bState().hq.beasts=1; })()""")
        await at_door('house26')
        check(not await offer(FARM_LABEL), '設立前の農家は入口の案内が出ない')
        await ev("(stfP().mutantMet=true,szJoin())")
        await enter('hq', '大きな建物に入る')
        check(await ev("[P3A.inId,P3A.interior.rooms.map(r=>r.name),P3A.interior.marks.length]")
              == ['hq', HQ, 5], '本部の13部屋と設立前の印5個')
        for i in range(3):
            await ev(f"""(()=>{{ const m=P3A.interior.marks.find(k=>k.sv==={i}); P.x=m.x; P.z=m.z; }})()""")
            if not await offer('調べる', True):
                raise RuntimeError('本部の調査の案内が出ない')
            if i < 2:
                await wait(f"P3A.interior.marks.every(k=>k.sv!=={i})")
        # 最後の調査の近くにスズキを置いて、設立の会話を最後まで読む
        await ev('p3aSzFollow()')
        await dialog_until("p3cOn()&&$('dialog').hidden")
        await wait(f"{PLAYING}&&P3A.interior.marks.some(k=>k.id==='mgmt')")
        check(await ev('P3A.interior.marks.length') == 11, '本部の設立後の印11個')
        hq_triangles = await entry_triangles()
        await leave()

        await enter('factory', '整備工場跡に入る')
        check(await ev("[P3A.inId,P3A.interior.rooms.map(r=>r.name),P3A.interior.marks.length]")
              == ['factory', FACTORY, 1], '整備工場跡の3部屋と初回の印1個')
        await leave()

        await at_door('house26')
        check(await offer(FARM_LABEL) == FARM_LABEL, '設立後に古い農家の入口の案内が出る')
        hq_before = await ev('JSON.stringify(prog.p3.hq)')
        entry = await enter('house26', FARM_LABEL)
        check(await ev("""P3A.inId==='farm'&&!REG.live.group.visible&&
          dist(P.x,P.z,21001.6,21135.6)<0.05"""), '農家の入口に入り、外が隠れて操作できる')
        check(await ev('p3bSzInside()'), 'スズキが一緒に入る')
        check(await page.get_by_text('古い農家に入った', exact=True).count() == 1, '初回の入室だけにトーストが出る')
        check(await ev("prog.p3.e3.farm===1&&JSON.parse(localStorage.getItem(SAVE_KEY)).p3.e3.farm===1")
              and await ev('JSON.stringify(prog.p3.hq)') == hq_before, '初回訪問だけを保存し、本部の進行はそのまま')
        farm_triangles = await entry_triangles()
        check(0 < farm_triangles <= 1.15 * hq_triangles,
              f'画面全体の三角形は本部の1.15倍以下（農家 {farm_triangles}、本部 {hq_triangles}）')
        rooms = await ev("P3A.interior.rooms.map(r=>[r.id,r.name,r.x0-21000,r.z0-21120,r.x1-21000,r.z1-21120])")
        check(len(rooms) == len(ROOMS) and all(
            a[:2] == b[:2] and all(abs(x - y) <= 0.05 for x, y in zip(a[2:], b[2:]))
            for a, b in zip(rooms, ROOMS)), '部屋6つの名前と寸法')
        check(await ev("P3A.interior.marks.map(k=>[k.id,k.label,!!k.exit])")
              == [['exit', '外へ出る', True],
                  ['search0', 'かまどを調べる', False], ['search1', '流しと水甕を調べる', False],
                  ['search2', '農具の棚を調べる', False], ['search3', '囲炉裏を調べる', False],
                  ['search4', '茶箪笥を調べる', False], ['search5', '仏壇に手を合わせる', False],
                  ['search6', '箪笥と長持を調べる', False], ['search7', '蔵の棚を調べる', False]],
              '地点は出口と調べる所8か所')
        gaps = await ev("""P3IN.farm.plan().walls.filter(w=>w[5]).map(([a,b,c,d,,[lo,hi]])=>{
          const t=(lo+hi)/2/dist(a,b,c,d); return [lerp(a,c,t),lerp(b,d,t),hi-lo];
        }).sort((a,b)=>a[0]-b[0]||a[1]-b[1])""")
        expected = sorted(GAPS)
        check(len(gaps) == len(expected) and all(
            all(abs(x - y) < 0.001 for x, y in zip(a, b)) for a, b in zip(gaps, expected)),
            '戸口7つの中心と幅（入口2.4m・框6.0m・ほか2m）')
        check(await ev(f"{json.dumps(GAPS)}.every(([x,z])=>szFree(21000+x,21120+z,x===0?0.05:0.4))"),
              '戸口の中央に当たりがない（西の入口の外止めは別に確認）')
        check(await ev("""P3IN.farm.plan().walls.every(([a,b,c,d,,gap])=>{
          const len=dist(a,b,c,d);
          const mids=gap?[gap[0]/2,(gap[1]+len)/2]:[len/2];
          return mids.every(m=>!szFree(21000+lerp(a,c,m/len),21120+lerp(b,d,m/len),0.4));
        })&&!szFree(20999.7,21135.6,0.05)"""), '壁の各区間の中央と入口の外止めに当たりがある')
        main_samples, side_samples = map(sample_path, (MAIN_PATH, SIDE_PATH))
        for samples, name in [(main_samples, '入口から座敷を通って蔵'), (side_samples, '囲炉裏の間から納戸を通って蔵前')]:
            blocked = await ev(f"""{json.dumps(samples)}.filter(([x,z])=>
              !szFree(21000+x,21120+z,0.4)||!szFree(21000+x,21120+z,0.8))""")
            check(not blocked, f'{name}まで幅1.6mの経路を0.5m以下の間隔で確認 {blocked[:3]}')

        # スズキの追従を観察できる速度で、主人公を経路に沿って動かす
        for x, z in main_samples[1:]:
            await at_room(x, z)
            await game_seconds(0.12)
        deadline = await ev('stats.time') + 5
        await wait(f'dist(SZ.x,SZ.z,P.x,P.z)<6||stats.time>{deadline}')
        check(await ev('dist(SZ.x,SZ.z,P.x,P.z)<6'), '主人公が蔵に着いてから5ゲーム秒以内にスズキが6m以内に来る')

        # 蔵戸の開き方は主人公とスズキで個別に確かめる
        await ev("szOrder('wait')")
        check(await ev("""(()=>{ const d=P3A.interior.doors.find(d=>Math.abs(d.z-21124.4)<0.05);
          if(!d) return false;
          const prev=[P.x,P.z,SZ.x,SZ.z], test=who=>{
            P.x=21003; P.z=21134; SZ.x=21003; SZ.z=21134; d.o=0;
            who.x=d.x; who.z=d.z+1;
            for(let i=0;i<20;i++) p3bInteriorTick(1/60);
            return d.o>0.8;
          };
          const player=test(P), suzuki=test(SZ);
          [P.x,P.z,SZ.x,SZ.z]=prev;
          return player&&suzuki;
        })()"""), '主人公・スズキそれぞれが戸に近づくと開く')
        check(await ev("""(()=>{ const old=camera.position.clone(), px=P.x,pz=P.z;
          P.x=21001.6; P.z=21128; camera.position.set(20997,7,21128);
          p3bInteriorTick(0);
          const hidden=P3A.interior.uppers.some(u=>u.x0===21000&&u.x1===21000&&!u.m.visible);
          camera.position.copy(old); P.x=px; P.z=pz; p3bInteriorTick(0); return hidden;
        })()"""), 'カメラと主人公の間にある手前の壁の上が隠れる')
        interior_triangles = await ev("""(()=>{ let total=0;
          P3A.interior.g.traverse(o=>{
            if(!o.isMesh) return;
            const g=o.geometry;
            total+=(g.index?.count??g.attributes.position.count)/3;
          });
          return total;
        })()""")
        check(0 < interior_triangles < 15000,
              f'農家の屋内グループは輪郭線込みで15,000三角形未満（{interior_triangles}）')
        await screenshots(1280, 720)
        await ev("szOrder('follow')")
        await leave()
        check(await ev(f"REG.live.group.visible&&dist(P.x,P.z,{entry[0]},{entry[1]})<3"),
              '外へ出ると入口の3m以内に戻り、外が見える')
        await ev("szOrder('wait')")
        await enter('house26', FARM_LABEL)
        check(not await ev('p3bSzInside()'), '待機中のスズキは外に残る')
        check(await page.get_by_text('古い農家に入った', exact=True).count() == 0, '再入室ではトーストが出ない')
        # 農家の中を表示したまま再読み込みして、屋外から再開することも確認
        await continue_game()
        check(await ev('!P3A.inside&&prog.p3.e3.farm===1'), 'つづきからは上志比の屋外で、訪問を記憶している')
        old_save = await ev("""(()=>{ const d=JSON.parse(localStorage.getItem(SAVE_KEY));
          delete d.p3.e3; localStorage.setItem(SAVE_KEY,JSON.stringify(d)); return [SAVE_KEY,JSON.stringify(d)]; })()""")
        await continue_game()
        check(await ev('prog.p3.e3.farm===0&&p3cOn()'), '旧セーブの訪問は0で、拠点設立は読み込まれる')
        await enter('house26', FARM_LABEL)
        check(await ev("P3A.inId==='farm'&&prog.p3.e3.farm===1"), '旧セーブで農家に入り保存できる')
        await leave()
        await ctx.close()

        ctx, page = await open_page(390, 844, touch=True)
        await page.add_init_script(script=f'localStorage.setItem(...{json.dumps(old_save)})')
        await continue_game()
        await ev("if(szHere()) szOrder('wait')")
        await enter('house26', FARM_LABEL, touch=True)
        check(await ev("P3A.inId==='farm'"), '390×844の行動ボタンで農家に入れる')
        await screenshots(390, 844)
        await leave(touch=True)
        check(await ev('!P3A.inside&&REG.live.group.visible'), '390×844の行動ボタンで外に出られる')
        await ctx.close()
        check(not errors, f'ページのエラーなし {errors[:3]}')
        await browser.close()
    return int(bool(failures))


if __name__ == '__main__':
    try:
        sys.exit(asyncio.run(main()))
    except Exception as exc:
        print(f'FAIL 実行中にエラー（{exc}）', file=sys.stderr)
        sys.exit(1)
