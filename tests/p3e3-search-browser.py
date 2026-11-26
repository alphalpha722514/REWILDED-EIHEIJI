#!/usr/bin/env python3
"""E3-2 の調査・古い地図・v0.90 経由のセーブを Chromium で確認する。"""

import asyncio
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
LEGEND = '古い地図：よろず屋・集会所・薬草の生えやすい所'
BANNER = ['古い地図を手に入れた。', '地図（PC は G、スマホは「地図」ボタン）に印が増えた']
KEY = 'eiheiji_vs_beasts_v010'
REWARDS = {'charcoal': 3, 'rice': 2, 'rope': 2, 'iron': 3, 'food': 1, 'oldParts': 1}
# 案内の基準点と、主人公半径0.5mで立つ位置を個別に検査する。
SPOTS = [
    ('かまど', (2.6, 19.6, 1.3), (2.9, 19.4), {'charcoal': 2},
     '焚き口の灰をよけると、燃え残りの炭が出てきた。（木炭 ×2）', 'かまどは冷えきっている。'),
    ('流しと水甕', (1.8, 19, 1.3), (1.95, 18.05), {'rice': 2},
     '流しの下の米びつに、米が少し残っていた。（米 ×2）', '甕の水は濁っている。飲まないほうがいい。'),
    ('農具の棚', (1.2, 7.2, 1.6), (1.2, 7.2), {'rope': 2, 'iron': 1},
     '農具の間に、束ねた縄が掛けてあった。刃の欠けた鎌も、鉄くずとして使えそうだ。（縄 ×2・屑鉄 ×1）',
     '鍬も鎌も、長く使い込まれている。'),
    ('囲炉裏', (8.5, 17.3, 1.9), (8.5, 15.95), {'charcoal': 1},
     '炉縁の脇の炭入れに、炭がひとつかみ残っていた。（木炭 ×1）', '自在鉤に鍋が掛かったままだ。'),
    ('茶箪笥', (10.2, 20.2, 1.4), (10.2, 20.15), {'food': 1},
     '茶箪笥の下の段に、封をした乾物の袋があった。（食料 ×1）', '湯呑みが一つ、倒れたままになっている。'),
    ('仏壇', (15.1, 17.6, 1.6), (15.1, 17.6), {},
     '小さく手を合わせた。', '小さく手を合わせた。'),
    ('箪笥と長持', (8.4, 5.9, 1.8), (8.4, 5.9), {},
     '引き出しが半分開いたままになっている。長持には、着物が畳まれたまま入っていた。',
     '着物が畳まれたまま残っている。'),
    ('蔵の棚', (14.5, 2.2, 1.6), (14.5, 2.2), {'oldParts': 1, 'iron': 2},
     '棚の奥の木箱に、折り畳んだ紙が入っていた。広げると、この辺りを描いた古い地図だった。',
     '棚には古い道具の箱が並んでいる。（古い地図は地図の画面で見られる）'),
]
PLAYING = "S.mode==='playing'&&!P3A.busy&&!REG.busy"
READY = f"{PLAYING}&&REG.cur==='kamishihi'&&P3A.on"
READ = 'JSON.parse(localStorage.getItem(SAVE_KEY))'
STATE = '[prog.p3.e3.s,prog.p3.e3.map]'
EMPTY = [[0] * 8, 0]
DONE = [[1] * 8, 1]


def old_html():
    if os.environ.get('OLD_HTML'):
        return Path(os.environ['OLD_HTML']).read_text(encoding='utf8')
    try:
        return subprocess.run(
            ['git', 'show', '79ed170:index.html'], cwd=ROOT, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf8').stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError('v0.90 の index.html を取得できません。OLD_HTML=手元のパス を指定してください。') from exc


def label(i, again=False):
    return '仏壇に手を合わせる' if i == 5 else SPOTS[i][0] + ('を見る' if again else 'を調べる')


def tracked(d):
    progress = {k: v for k, v in d['chapter2']['progress'].items() if k != 'e3farm'}
    p3 = {k: v for k, v in d['p3'].items() if k != 'e3'}
    # 追従中の座標は再開時に置き直す仕様。同行・待機・地域・体力を比べる。
    suzuki = {k: d['suzuki'][k] for k in ('v', 'joined', 'order', 'region', 'hp', 'down', 'wx', 'wz')}
    return [progress, p3, suzuki, d['p3']['e3']['farm'], d['prog'], *(
        d[k] for k in ('p3c', 'kami', 'p3d', 'weapon', 'dur', 'arms', 'inv', 'stash'))]


# 地図の描画に実際に渡った円・文字・輪郭を採る。ズームや文字のアンチエイリアスに依存しない。
TRACE_MAP = """(miniMap=>{ const c=miniMap?mini:$('mapCv').getContext('2d');
  const result={circles:[],labels:[],outlines:0};
  const methods={arc:c.arc,fillText:c.fillText,stroke:c.stroke};
  c.arc=function(x,z,r,...rest){ result.circles.push([x,z,r,this.fillStyle]); return methods.arc.call(this,x,z,r,...rest); };
  c.fillText=function(t,...rest){ result.labels.push(t); return methods.fillText.call(this,t,...rest); };
  c.stroke=function(...args){ if(this.strokeStyle==='#ffe08a'&&this.lineWidth===1.5) result.outlines++; return methods.stroke.apply(this,args); };
  try{ if(miniMap) drawMini(); else drawMap(); } finally { for(const k of Object.keys(methods)) delete c[k]; }
  return result;
})"""
STEP = """((from,to)=>{
  const o=P3IN.farm.o; P.x=o.x+from[0]; P.z=o.z+from[1]; P._px=P.x; P._pz=P.z;
  const free=szFree(P.x,P.z,P.r);
  const dx=to[0]-from[0], dz=to[1]-from[1], n=Math.ceil(Math.hypot(dx,dz)/0.05)||1;
  P.facing=Math.atan2(dx,dz);
  let hit=false;
  for(let i=0;i<n;i++){ P.x+=dx/n; P.z+=dz/n; if(resolve(P,false)) hit=true; }
  return {free,hit,x:P.x-o.x,z:P.z-o.z,label:interactables()?.label};
})"""


async def main():
    old = old_html()
    from playwright.async_api import async_playwright

    farm_test = runpy.run_path(str(ROOT / 'tests/p3e3-farm-browser.py'))
    current, base = farm_test['HTML'], farm_test['BASE']
    old = old.replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){', 1)
    three = Path(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read_bytes()
    shots = Path(os.environ['E3_SHOTS']) if os.environ.get('E3_SHOTS') else None
    errors, failures = [], []

    def check(condition, msg):
        print(('ok   ' if condition else 'FAIL ') + msg, flush=True)
        if not condition:
            failures.append(msg)

    async def route(request):
        url = urlsplit(request.request.url)
        if url.path.endswith('/three.min.js'):
            return await request.fulfill(body=three, content_type='application/javascript')
        if url.netloc == 'game.local':
            if url.path in ('/', '/index.html', '/old.html'):
                return await request.fulfill(body=old if url.path == '/old.html' else current,
                                             content_type='text/html; charset=utf-8')
            file = (ROOT / url.path.lstrip('/')).resolve()
            if file.is_relative_to(ROOT) and file.is_file():
                return await request.fulfill(path=str(file))
            return await request.fulfill(status=404, body='')
        await request.abort()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])

        async def open_page(touch=False):
            w, h = (390, 844) if touch else (1280, 720)
            ctx = await browser.new_context(viewport={'width': w, 'height': h},
                                            has_touch=touch, is_mobile=touch)
            await ctx.route('**/*', route)
            page = await ctx.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            return ctx, page

        ctx, page = await open_page()

        async def ev(code):
            return await page.evaluate('code=>window.__ev(code)', code)

        async def wait(code):
            await page.wait_for_function('code=>window.__ev(code)', arg=code, timeout=180000)

        async def boot(button, path='/'):
            await page.goto('http://game.local' + path, wait_until='load', timeout=300000)
            await wait("typeof P3IN==='object'")
            await page.locator(button).click()
            if button == '#btnContinue':
                await wait(READY)

        async def finish_dialog(touch=False):
            dialog = page.locator('#dialog')
            for _ in range(8):
                if not await dialog.is_visible():
                    return
                await page.wait_for_timeout(200)
                if touch:
                    await dialog.tap()
                else:
                    await page.keyboard.press('e')
            raise RuntimeError('会話欄を閉じられない')

        async def press(label_text, touch=False):
            await wait(f'curInter?.label==={json.dumps(label_text)}')
            if touch:
                await page.locator('#tbAct').tap()
            else:
                await page.keyboard.press('e')

        async def enter(door, text, touch=False):
            await ev(f"""(()=>{{ const d=P3A.doors.find(d=>d.id==={json.dumps(door)});
              P.x=d.x; P.z=d.z;
              for(const e of enemies) if(dist(e.x,e.z,P.x,P.z)<220) e.x+=900;
            }})()""")
            await press(text, touch)
            await wait(f'{PLAYING}&&P3A.inside')

        async def farm(touch=False):
            await enter('house26', '古い農家に入る', touch)

        async def stand(i):
            x, z = SPOTS[i][2]
            await ev(f'(P.x=P3IN.farm.o.x+{x},P.z=P3IN.farm.o.z+{z},prog.lastSaveT=0)')
            check(await ev('szFree(P.x,P.z,P.r)'), f'{i+1}の前に立てる')

        async def leave():
            await ev("(()=>{ const m=P3A.interior.marks.find(k=>k.exit); P.x=m.x; P.z=m.z; })()")
            await press('外へ出る')
            await wait(f'{PLAYING}&&!P3A.inside')

        async def triangles():
            await ev("""(()=>{ const d=P3IN[P3A.inId];
              P.x=d.o.x+d.entry.x; P.z=d.o.z+d.entry.z; P.facing=Math.PI/2; setCam(P.facing);
            })()""")
            t = await ev('stats.time')
            await wait(f'stats.time>{t + 0.45}')
            return await ev('renderer.info.render.triangles')

        async def inventory():
            return await ev('Object.assign({},inv)')

        async def search(i, again=False, touch=False):
            await stand(i)
            before, saved = await inventory(), await ev('localStorage.getItem(SAVE_KEY)')
            await ev("$('toasts').replaceChildren(); window.pickups=0")
            await press(label(i, again), touch)
            expected = SPOTS[i][5 if again else 4]
            if i == 5 or (i == 7 and not again):
                check(await ev("!$('dialog').hidden&&$('dlgName').textContent===''") and
                      await page.locator('#dlgText').inner_text() == expected, f'{i+1}の地の文')
                if touch:
                    await page.locator('#tbAct').wait_for(state='hidden')
                    check(not await page.locator('#tbAct').is_visible(), '会話中は行動ボタンが隠れる')
                if i == 7:
                    check(await ev("$('banner').firstChild?.textContent") != BANNER[0], '帯は地の文のあと')
                await finish_dialog(touch)
                if i == 7:
                    check(await ev("[...$('banner').childNodes].map(n=>n.textContent)") == BANNER and
                          await ev("$('banner').classList.contains('show')"), '古い地図の案内の帯')
            else:
                check(await page.locator('#toasts .toast').all_text_contents() == [expected], f'{i+1}のトースト')
            inv = await inventory()
            delta = {k: n - before[k] for k, n in inv.items() if n != before[k]}
            expected_reward = {} if again else SPOTS[i][3]
            check(delta == expected_reward, f'{i+1}の報酬 {delta}')
            check(await ev('window.pickups') == int(bool(expected_reward)), f'{i+1}の拾う音')
            if again:
                check(await ev('localStorage.getItem(SAVE_KEY)') == saved, f'{i+1}の再調査は保存しない')
            else:
                check(await ev(f'{READ}.p3.e3.s[{i}]===1&&({READ}.chapter2.progress.e3farm.s&(1<<{i}))!==0') and
                      await ev(f'{READ}.inv') == inv, f'{i+1}は記録と報酬をすぐ保存')
            check(await ev("['rice','food'].every(k=>prog.f7.hand[k].reduce((sum,b)=>sum+b[0],0)===inv[k])"),
                  '米と食料の鮮度の束と個数が一致')

        async def watch_pickups():
            await ev("""(()=>{ const orig=sfx; sfx=function(k,...args){
              if(k==='pickup') window.pickups++; return orig(k,...args);
            }; })()""")

        async def map_open(touch=False):
            if touch:
                await page.locator('#tbMap').tap()
            else:
                await page.keyboard.press('g')
            await wait("!$('mapOv').hidden&&MAPV.W>0")

        async def map_trace(mini=False):
            return await ev(TRACE_MAP + ('(true)' if mini else '(false)'))

        def herb_circles(draw):
            return [c[:3] for c in draw['circles'] if c[3].startswith('rgba(164, 224, 146,')]

        async def screenshot(name):
            if shots:
                shots.mkdir(parents=True, exist_ok=True)
                await page.screenshot(path=str(shots / name))

        await boot('#btnNew')
        await finish_dialog()
        await ev(base)
        await ev("""(()=>{ Object.assign(prog.p3.hq,{plan:1,talk:1,sv:[1,1,1],beasts:1,visited:1});
          prog.p3.rep.storage=[1,1,1]; prog.p3.got.gen=1;
          prog.p3c.hint=1; prog.p3d.rod.basic=1; prog.p3d.casts=3;
          prog.kami.sc=[0]; prog.stash.komyoji.wood=3;
          P.dur=WEAPONS[P.weapon].maxDur-1; prog.gear.equip.head=null;
          stfP().mutantMet=true; szJoin(); prog.f7.intro|=1;
        })()""")
        await ev("regionTravel('kamishihi',null,{force:true})")
        await wait(READY)
        await ev("""(()=>{ szOrder('wait'); saveGame(); const d=readSave();
          delete d.p3.e3.s; delete d.p3.e3.map; delete d.chapter2.progress.e3farm;
          localStorage.setItem(SAVE_KEY,JSON.stringify(d));
        })()""")
        legacy = await ev('localStorage.getItem(SAVE_KEY)')
        await boot('#btnContinue')
        check(await ev(STATE) == EMPTY and await ev('p3cOn()'), '旧セーブは拠点を保ち、全地点が未調査')
        await map_open()
        pre_map = await map_trace()
        check(await page.locator('#oldMapLegend').is_hidden() and not herb_circles(pre_map) and
              not {'よろず屋', '集会所'}.intersection(pre_map['labels']) and not pre_map['outlines'] and
              not herb_circles(await map_trace(mini=True)), '取得前の全体地図とミニマップに古い地図の表示がない')
        await page.keyboard.press('g')

        await enter('hq', '拠点本部に入る')
        hq_triangles = await triangles()
        await leave()
        await farm()
        check(await ev("P3A.interior.mk.length===1&&P3A.interior.marks.filter(m=>m.glow===false).length===8"),
              '光る箱は出口だけ')
        points = await ev("""P3A.interior.marks.filter(m=>!m.exit).map(m=>
          [+(m.x-P3IN.farm.o.x).toFixed(2),+(m.z-P3IN.farm.o.z).toFixed(2),m.r])""")
        check(points == [list(s[1]) for s in SPOTS], '8地点の案内座標と半径')
        farm_triangles = await triangles()
        check(0 < farm_triangles <= 1.15 * hq_triangles, f'画面全体の三角形数 {farm_triangles}/{hq_triangles}')
        interior = await ev("""(()=>{ let n=0;
          P3A.interior.g.traverse(o=>{ if(o.isMesh) n+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3; });
          return n;
        })()""")
        check(0 < interior < 15000, f'屋内の三角形数 {interior}')

        for i, starts in enumerate([[(3.6, 19.4), (2.9, 18.5)], [(2.65, 18.05), (1.95, 17.2)]]):
            for start in starts:
                approach = await ev(f'{STEP}({json.dumps(start)},{json.dumps(SPOTS[i][2])})')
                check(approach['free'] and not approach['hit'] and approach['label'] == label(i),
                      f'{i+1}が手前で選ばれる（進入位置 {start}）')
        for x, z in [(8.5, 15.95), (8.5, 18.65), (7.15, 17.3), (9.85, 17.3)]:
            await ev(f'(P.x=P3IN.farm.o.x+{x},P.z=P3IN.farm.o.z+{z})')
            check(await ev('szFree(P.x,P.z,P.r)&&interactables()?.label==="囲炉裏を調べる"'),
                  f'囲炉裏の四辺から案内が出る（{x}, {z}）')
        for start, target, limit, name in [
            ((1.6, 10), (-1, 10), 0.5, '外壁'),
            ((2.9, 19.4), (2.9, 21.4), 19.5, 'かまど'),
            ((8.5, 15.95), (8.5, 18.8), 16.05, '囲炉裏'),
        ]:
            result = await ev(f'{STEP}({json.dumps(start)},{json.dumps(target)})')
            stopped = result['x'] >= limit if name == '外壁' else result['z'] <= limit + 0.001
            check(result['free'] and result['hit'] and stopped, f'{name}を通り抜けない')

        await watch_pickups()
        initial = await inventory()
        for i in range(len(SPOTS)):
            await search(i)
        after = await inventory()
        check({k: v - initial[k] for k, v in after.items() if v != initial[k]} == REWARDS and
              sum(REWARDS.values()) == 12 and await ev(STATE) == DONE, '合計12個と地図、調査8件')
        for i in range(len(SPOTS)):
            await search(i, again=True)

        await leave()
        await map_open()
        world_map = await map_trace()
        circles = herb_circles(world_map)
        check(await page.locator('#oldMapLegend').inner_text() == LEGEND and
              await page.locator('#oldMapLegend').is_visible(), '全体地図の古い地図の凡例')
        check({'よろず屋', '集会所'}.issubset(world_map['labels']) and world_map['outlines'] == 2 and
              len(circles) == 12, '全体地図に縁取り2件・名前2件・薬草の円12個')
        check(herb_circles(await map_trace()) == circles, '薬草の円の位置が安定する')
        await screenshot('search-map-pc.png')
        await page.keyboard.press('g')
        await ev("""(()=>{ const h=REG.live.kw.nodes.find(n=>n.key==='h0');
          P.x=h.x; P.z=h.z; P.scoutT=90;
        })()""")
        mini_map = await map_trace(mini=True)
        check(not mini_map['labels'] and not mini_map['outlines'] and len(herb_circles(mini_map)) == 12 and
              any(0 <= x <= 150 and 0 <= z <= 196 and abs(r-15/1.6)<0.001 and
                  0 < ((x-75)**2 + (z-98)**2)**0.5 < 7/1.6 + .001
                  for x, z, r in herb_circles(mini_map)), 'ミニマップはずらした半径15mの円だけを追加')
        check(any(abs(x-75)<.001 and abs(z-98)<.001 and r==2 and col=='#7ad0ff'
                  for x, z, r, col in mini_map['circles']), 'ずがに汁はミニマップに薬草の小さな点を描く')
        await map_open()
        check(any(r==3.4 and col=='#7ad0ff' for _, _, r, col in (await map_trace())['circles']),
              'ずがに汁は全体地図にも点を描く')
        await page.keyboard.press('g')
        await ev("regionTravel('komyoji',null,{force:true})")
        await wait(f"{PLAYING}&&REG.cur==='komyoji'")
        await map_open()
        home_map = await map_trace()
        check(await page.locator('#oldMapLegend').is_hidden() and
              await page.locator('#mapOv .maplegend').first.is_visible() and not herb_circles(home_map) and
              not {'よろず屋', '集会所'}.intersection(home_map['labels']), '光明寺の地図には従来の凡例だけ')
        await page.keyboard.press('g')
        await ev("regionTravel('kamishihi',null,{force:true})")
        await wait(READY)
        await ev('saveGame()')
        check(await ev('SAVE_KEY') == KEY and await ev(f'{READ}.v') == 1, '保存キーと版番号')
        await boot('#btnContinue')
        check(await ev(STATE) == DONE, 'この版で読み直しても調査と地図が残る')
        await ev('saveGame()')
        before_rollback = await ev(READ)

        await boot('#btnContinue', '/old.html')
        check(await ev("p3eFarmMarks().length===1&&prog.p3.e3.s===undefined"), 'v0.90 の実ページを読み込んだ')
        await ev('saveGame()')
        rolled = await ev(READ)
        check(rolled['p3']['e3'] == {'farm': 1} and
              rolled['chapter2']['progress']['e3farm'] == {'s': 255, 'map': 1}, 'v0.90 の再保存で写しが残る')
        check(tracked(rolled) == tracked(before_rollback), 'v0.90 の再保存で既存の進行・装備・持ち物が残る')
        await boot('#btnContinue')
        check(await ev(STATE) == DONE and tracked(await ev(READ)) == tracked(before_rollback),
              '巻き戻り後にこの版で8件と地図と既存セーブ項目がそろう')
        await farm()
        await watch_pickups()
        for i in range(len(SPOTS)):
            await search(i, again=True)
        await boot('#btnNew')
        await finish_dialog()
        check(await ev(STATE) == EMPTY and await ev(f'{READ}.chapter2.progress.e3farm') == {'s': 0, 'map': 0},
              'はじめからで調査と地図が両方とも0')
        await ctx.close()

        ctx, page = await open_page(touch=True)
        await page.add_init_script(script=f'localStorage.setItem({json.dumps(KEY)},{json.dumps(legacy)})')
        await boot('#btnContinue')
        await farm(touch=True)
        await watch_pickups()
        await search(5, touch=True)
        await search(7, touch=True)
        note_box = await page.locator('#banner small').bounding_box()
        check(note_box and note_box['x'] >= 16 and note_box['x'] + note_box['width'] <= 390 - 16,
              '390×844で古い地図の帯の2行目に左右16px以上の余白がある')
        await screenshot('search-banner-iphone.png')
        await map_open(touch=True)
        legend = page.locator('#oldMapLegend')
        box = await legend.bounding_box()
        buttons = await page.locator('.mapbtns').bounding_box()
        check(await legend.inner_text() == LEGEND and box and buttons and
              0 <= box['x'] and box['x'] + box['width'] <= 390 and box['y'] + box['height'] <= buttons['y'],
              '390×844の地図ボタンで凡例が見え、操作ボタンと重ならない')
        await screenshot('search-map-iphone.png')
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
