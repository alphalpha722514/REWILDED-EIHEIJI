#!/usr/bin/env python3
"""v0.87（P3-E の E-1）上志比の町並みの確認（画面のない Chromium。8分ほど）。docs/p3e-e1.md

- 上志比を作ると、細かい家にする区画の準備ができる（建物の数・除く建物：P3-A の試作・鉄工所の跡・サルの要塞の中）
- 19種類の家の形がすべて作れる（足場の四角から大きくはみ出さない）
- 近くへ行くと区画ごとに細かい家と小物（電柱・電線・側溝・カーブミラー・止まれ・塀・庭木・車など）ができ、今までの形はつぶして隠す（輪郭線の形も）
- 離れると捨てて、今までの形が元の位置に戻る（頂点が1つ残らず同じ）・小物の当たり判定も外す
- 家の当たり判定（家の大きさ・向き）・壊れた家の記録（がれきの場所）は変わらない
- 設定「描く細かさ：標準／軽量」：押すと切り替わる・保存される・軽量は作る範囲が狭い
- 光明寺へ戻ると捨てる（当たり判定が残らない）・エラーなし
- KAMI_E1_SHOTS=フォルダ で写真の場所（集落）の画面を撮る

使い方：THREE_JS=…/three.min.js python3 tests/p3e-town-browser.py
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THREE = open(os.environ.get('THREE_JS', '/home/claude/v010/node_modules/three/build/three.min.js')).read()
HTML = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read().replace('function updateNPCs(dt){', 'window.__ev=s=>eval(s);\nfunction updateNPCs(dt){', 1)
SHOTS = os.environ.get('KAMI_E1_SHOTS')
BASE = """(()=>{ prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true;
  prog.chapter2=chapter2State(null,true); const p=prog.chapter2.progress; p.openingStarted=true; p.defenseComplete=true; p.defenseRewarded=true; prog.chapter2.currentChapter=2;
  p.radioHeard=true; p.departureDecision=true; p.departureComplete=true; p.truck={found:true,repaired:true,fueled:true,parts:['p1','p2'],fuel:0,trips:1,region:'komyoji'};
  prog.level=4; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; TRUCK.sync=false; return 1; })()"""
STYLES = ['irimoya', 'tsumairi', 'tootan', 'modernW', 'modernT', 'modernB', 'kata', 'shop', 'public', 'kura', 'smallW', 'garage', 'carport', 'shedM', 'shedW', 'barnB', 'hasa', 'barnR', 'warehouse']
# 写真の場所（集落）の道の上：カメラの位置と見る先
VIEW = [6012, 1100.5, 5985, 1094]


async def main():
    ok = True

    def check(c, msg):
        nonlocal ok
        print(('ok   ' if c else 'FAIL ') + msg, flush=True)
        ok = ok and c

    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        ctx = await b.new_context(viewport={'width': 1100, 'height': 680})
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
        E = lambda c: pg.evaluate('(c)=>window.__ev(c)', c)

        async def until(js, ms=20000):
            for _ in range(ms // 200):
                if await E(js):
                    return True
                await pg.wait_for_timeout(200)
            return False

        await pg.goto('http://game.local/', wait_until='load', timeout=300000)
        await pg.wait_for_function("typeof window.__ev==='function'", timeout=300000)
        await pg.click('#btnNew')
        await pg.wait_for_timeout(500)
        for _ in range(15):
            if await pg.evaluate("document.getElementById('dialog').hidden"):
                break
            await pg.click('#dialog')
            await pg.wait_for_timeout(200)
        await E(BASE)
        await E("(()=>{ try{ localStorage.removeItem('eiheiji_detail'); }catch(e){} GFX.detail='std'; return 1; })()")
        home = await E("[circles.length, oboxes.length, boxes.length]")
        # 比べるために、細かい家を作らないで上志比を作ったときの数（当たり判定・壊れた家）を先に測る
        await E("(()=>{ E1.off=true; return 1; })()")
        await E("(async()=>{ await regionTravel('kamishihi',null,{force:true}); })()")
        await until("REG.cur==='kamishihi'&&!REG.busy", 120000)
        await pg.wait_for_timeout(600)
        await E("(()=>{ for(const e of enemies) if(!e.removed&&e.x>4000) e.x+=3000; prog.f10.tod=150; f10LightNow(); weather.state='clear'; return 1; })()")
        ref = await E("""(()=>{ const hb=oboxes.filter(o=>o.tag==='house'); return {house:hb.length, hsum:Math.round(hb.reduce((a,o)=>a+o.x*3+o.z*7+o.hx*11+o.hz*13+(o.h||0),0)*100), dmg:DAMAGED.length, dsum:Math.round(DAMAGED.reduce((a,d)=>a+d.x+d.z*3+d.lv*5,0)*100), circles:circles.length, oboxes:oboxes.length}; })()""")
        # 元の形の頂点（写真の場所のまわりの区画）を覚える
        await E("""(()=>{ window.__tl=[]; for(const R of E1.rng.values()){ if(!window.__tl.includes(R.t)&&R.t.bld) window.__tl.push(R.t); }
          window.__sum=()=>window.__tl.map(t=>{ let a=0; for(const m of [t.bld,t.bldInk]){ const v=m.geometry.attributes.position.array; for(let i=0;i<v.length;i+=7) a+=v[i]*((i%13)+1); } return Math.round(a); }); window.__s0=__sum(); return 1; })()""")
        st = await E("""(()=>{ const D=KAMI.D; let n=0; const sty={}; for(const c of E1.cells.values()) for(const bi of c.bld){ n++; const s=e1Style(D.bld[bi]); sty[s]=(sty[s]||0)+1; }
          const inCells=new Set(); for(const c of E1.cells.values()) for(const bi of c.bld) inCells.add(bi);
          const skip=[...P3A.skip].some(i=>inCells.has(i)), b11=inCells.has(11), fort=[...inCells].some(i=>e1InZone(D.bld[i][0],D.bld[i][1],0));
          const poles=[...E1.cells.values()].reduce((a,c)=>a+c.poles.length,0), yab=[...E1.cells.values()].reduce((a,c)=>a+c.yab.length,0), jn=[...E1.cells.values()].reduce((a,c)=>a+c.jn.length,0);
          return {cells:E1.cells.size, n, total:D.bld.length, skip, b11, fort, nsty:Object.keys(sty).length, poles, yab, jn}; })()""")
        check(st['cells'] > 50 and 700 < st['n'] < st['total'] and not st['skip'] and not st['b11'] and not st['fort'],
              f"区画の準備：{st['cells']}区画・細かくする家 {st['n']}/{st['total']}軒（P3-A の試作・鉄工所の跡・要塞の中は除く）")
        check(st['nsty'] == 19 and st['poles'] > 100 and st['yab'] > 20 and st['jn'] > 10, f"家の形19種類が出てくる（{st['nsty']}）・電柱 {st['poles']}本・矢羽根 {st['yab']}本・交差点 {st['jn']}か所")
        # 19種類の形：作れる・足場の四角から大きくはみ出さない
        fit = await E(f"""(()=>{{ const D=KAMI.D, out={{}}; const b=D.bld.find(b=>b[2]>9&&b[3]>7&&b[5]<200); const F=e1Front(b);
          for(const s of {STYLES}){{ const A=new GB(), B=new GB(); const info=e1House(A,B,b,F,s,1,p3aRng(5)); if(!info){{ out[s]='null'; continue; }}
            let mx=0, mz=0; const c=Math.cos(F.rot), sn=Math.sin(F.rot); for(const g of [A]) for(let i=0;i<g.p.length;i+=3){{ const dx=g.p[i]-b[0], dz=g.p[i+2]-b[1]; mx=Math.max(mx,Math.abs(dx*c+dz*sn)-F.L/2); mz=Math.max(mz,Math.abs(-dx*sn+dz*c)-F.W/2); }}
            out[s]=[A.v+B.v, Math.round(mx*10)/10, Math.round(mz*10)/10]; }} return out; }})()""")
        bad = {k: v for k, v in fit.items() if v == 'null' or v[0] < 100 or v[1] > 2.6 or v[2] > 3.4}
        check(len(fit) == 19 and not bad, f"19種類の形を作れる・はみ出しは軒と玄関の分だけ（横 2.6m・前 3.4m まで）{bad or ''}")
        print('  形ごとの頂点の数とはみ出し：', fit, flush=True)

        # ---- 近くへ行く ----
        await E("(()=>{ E1.off=false; return 1; })()")
        x, z, lx, lz = VIEW
        await E(f"(()=>{{ P.x=6200; P.z=900; cam.override={{p:new THREE.Vector3({x},groundH({x},{z})+1.7,{z}), l:new THREE.Vector3({lx},groundH({lx},{lz})+1.5,{lz}), fov:60}}; return 1; }})()")
        done = await until(f"!E1.busy&&[...E1.cells.values()].every(c=>c.o||e1RectD(c,{x},{z})>=gfxRad().in)", 240000)
        near = await E(f"""(()=>{{ let nc=0, nb=0, nm=0, nv=0, cols=0, hid=0, flat=0; for(const c of E1.cells.values()) if(c.o){{ nc++; nb+=c.bld.length; cols+=c.o.cols.length; nm+=c.o.meshes.length; for(const m of c.o.meshes) if(m.geometry&&!m.isInstancedMesh) nv+=m.geometry.attributes.position.count;
            for(const [a,s,save] of c.o.hide){{ hid++; const v=a.array; let same=true; for(let i=s+3;i<s+save.length;i+=3) if(v[i]!==v[s]||v[i+1]!==v[s+1]||v[i+2]!==v[s+2]){{ same=false; break; }} if(same) flat++; }} }}
          window.__e1c=[]; for(const c of E1.cells.values()) if(c.o) window.__e1c.push(...c.o.cols);
          const hb=oboxes.filter(o=>o.tag==='house'); return {{nc, nb, nm, nv, cols, hid, flat, house:hb.length, hsum:Math.round(hb.reduce((a,o)=>a+o.x*3+o.z*7+o.hx*11+o.hz*13+(o.h||0),0)*100), dmg:DAMAGED.length, circles:circles.length, oboxes:oboxes.length}}; }})()""")
        check(done and near['nc'] >= 3 and near['nb'] > 20, f"近くの区画に細かい家ができる：{near['nc']}区画・{near['nb']}軒・形 {near['nm']}・頂点 {near['nv']}")
        check(near['hid'] > 0 and near['hid'] == near['flat'], f"今までの形（と輪郭線）はつぶして隠す：{near['flat']}/{near['hid']}")
        check(near['house'] == ref['house'] and near['hsum'] == ref['hsum'], f"家の当たり判定は変わらない（{near['house']}・大きさと向きも同じ）")
        check(near['dmg'] == ref['dmg'], f"壊れた家の記録（がれきの場所）は変わらない（{near['dmg']}）")
        check(near['cols'] > 10 and near['circles'] + near['oboxes'] == ref['circles'] + ref['oboxes'] + near['cols'], f"小物の当たり判定（電柱・塀・車・松など）{near['cols']}")
        perf = await E("(()=>{ renderer.info.autoReset=true; renderer.render(scene,camera); return [renderer.info.render.triangles, renderer.info.render.calls]; })()")
        print(f"  この場所の描く量（三角形・描く回数）：{perf}", flush=True)
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            await E("($('hud').hidden=true, 1)")
            await pg.wait_for_timeout(1500)
            await pg.screenshot(path=os.path.join(SHOTS, 'street.png'), timeout=300000)
            await E(f"(()=>{{ cam.override={{p:new THREE.Vector3(5990,groundH(5990,1140)+25,1140), l:new THREE.Vector3(5975,groundH(5975,1085),1085), fov:55}}; return 1; }})()")
            await until("!E1.busy&&[...E1.cells.values()].every(c=>c.o||e1RectD(c,5990,1140)>=gfxRad().in)", 240000)
            await pg.wait_for_timeout(1500)
            await pg.screenshot(path=os.path.join(SHOTS, 'above.png'), timeout=300000)
            await E("($('hud').hidden=false, 1)")

        # ---- 設定：描く細かさ ----
        await E("($('btnDetail').click(), 1)")
        s1 = await E("[GFX.detail, localStorage.getItem('eiheiji_detail'), $('btnDetail').textContent, [...E1.cells.values()].filter(c=>c.o).length]")
        await until(f"!E1.busy&&[...E1.cells.values()].every(c=>c.o||e1RectD(c,{x},{z})>=gfxRad().in)", 240000)
        lite = await E("[...E1.cells.values()].filter(c=>c.o).length")
        check(s1[0] == 'lite' and s1[1] == 'lite' and s1[2] == '描く細かさ：軽量' and s1[3] == 0 and 1 <= lite < near['nc'] + 1,
              f"「描く細かさ」を押すと軽量に（保存される・いったん捨てて狭い範囲で作り直す：{lite}区画）{s1}")
        await E("($('btnDetail').click(), 1)")
        s2 = await E("[GFX.detail, localStorage.getItem('eiheiji_detail'), $('btnDetail').textContent]")
        check(s2 == ['std', 'std', '描く細かさ：標準'], f"もう一度押すと標準 {s2}")
        await until(f"!E1.busy&&[...E1.cells.values()].every(c=>c.o||e1RectD(c,{x},{z})>=gfxRad().in)", 240000)

        # ---- 離れる ----
        await E("(()=>{ P.x=6500; P.z=470; cam.override={p:new THREE.Vector3(6500,groundH(6500,470)+30,470), l:new THREE.Vector3(6520,groundH(6520,430),430), fov:55}; return 1; })()")
        await until("!E1.busy&&[...E1.cells.values()].every(c=>!c.o||e1RectD(c,6500,470)<=gfxRad().out)", 120000)
        await pg.wait_for_timeout(600)
        far = await E("""(()=>{ const s=__sum(); let diff=0; const L=[]; for(const c of E1.cells.values()) if(c.o) L.push(c); const keep=new Set(); for(const c of L) for(const [a] of c.o.hide) keep.add(a);
          for(let i=0;i<s.length;i++){ const t=__tl[i]; if(keep.has(t.bld.geometry.attributes.position)) continue; if(s[i]!==__s0[i]) diff++; }
          const live=new Set(); for(const c of L) for(const k of c.o.cols) live.add(k); const C=new Set(circles), O=new Set(oboxes); const left=__e1c.filter(k=>!live.has(k)&&(C.has(k)||O.has(k))).length;
          return {cells:L.length, cols:L.reduce((a,c)=>a+c.o.cols.length,0), was:__e1c.length, left, diff}; })()""")
        check(far['diff'] == 0, f"離れると捨てて、今までの形が元の位置に戻る（違う区画 {far['diff']}）")
        check(far['left'] == 0 and far['was'] > 0, f"捨てた区画の当たり判定も外れる（さっきの小物 {far['was']} のうち残り {far['left']}・今ある区画 {far['cells']}）")

        # ---- 光明寺へ戻る ----
        await E("(cam.override=null, 1)")
        await E("(async()=>{ await regionTravel('komyoji',null,{force:true}); })()")
        await until("REG.cur==='komyoji'&&!REG.busy", 120000)
        back = await E("[E1.cells===null, circles.length, oboxes.length, boxes.length]")
        check(back[0] and back[1:] == home, f"光明寺へ戻ると捨てる・当たり判定が残らない {back} / {home}")
        sv = await E("(saveGame(), Object.keys(JSON.parse(localStorage.getItem(SAVE_KEY))).filter(k=>/e1|detail/i.test(k)))")
        check(sv == [] and await E("SAVE_KEY") == 'eiheiji_vs_beasts_v010', f"セーブは変えていない（新しい項目なし）{sv}")
        check(not errs, f"エラーなし {errs[:3]}")
        await b.close()
    print('PASS: 上志比の町並み（E-1）' if ok else 'FAILED')
    sys.exit(0 if ok else 1)


asyncio.run(main())
