#!/usr/bin/env python3
"""v0.88（P3-E の E-2：上志比の森林）の検収用の試遊版を作る（previews/p3e2-forest/index.html）。docs/p3e2-forest-preview.md

- 元にするのは作業ブランチ p3e2-forest の index.html（既定はコミット e378a7b。E-2 の最後のコミット）。本編の index.html（main）は使わない・変えない
- 保存キーと設定のキーを、すべて試遊版だけのものに変える（本編のセーブ・設定を読まない・書かない）
  さらにページのいちばん初めで、本編のキーを読む・書く・消すのを止める（変え忘れがあっても本編に触れない）
- タイトル画面の右上に「テスト：上志比の森で始める」ボタン
  （防衛戦と作業F は済み・鉄の斧・直した KEI truck に荷台の救急箱・光明寺のかまどは建ててある）
- 遊んでいる間は、画面の上の「試遊メニュー」から：森の中の場所へ移る・KEI truck をそばに呼ぶ・光明寺のかまどへ行く・
  苗木と山の薬草と素材を足す・時間を進める・昼にする・描く細かさを切り替える

使い方：python3 tools/build-p3e2-forest-preview.py [--ref コミット] [--src index.html のパス]
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = 'e378a7b4a1d1ef100a07da4abdeb734a344857e0'  # p3e2-forest の E-2 の最後のコミット（v0.88）
BLOB = '1d59ead7199bab58c488f814603db8ef54533e7a'  # そのときの index.html（git の blob）
OUT = os.path.join(ROOT, 'previews', 'p3e2-forest', 'index.html')
PRE = 'eiheiji_p3e2f_'  # 試遊版の設定のキーの頭

ap = argparse.ArgumentParser()
ap.add_argument('--ref', default=REF, help='index.html を取り出すコミット（既定：E-2 の e378a7b）')
ap.add_argument('--src', help='git から取り出さず、このファイルを元にする')
a = ap.parse_args()

if a.src:
    raw = open(a.src, 'rb').read()
    where = a.src
else:
    try:
        raw = subprocess.run(['git', '-C', ROOT, 'show', f'{a.ref}:index.html'], check=True, capture_output=True).stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f'{a.ref} の index.html を取り出せない（git fetch origin p3e2-forest をしてから）：{e.stderr.decode(errors="replace").strip()}')
    where = a.ref
blob = hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest()
if not a.src and a.ref == REF and blob != BLOB:
    sys.exit(f'元の index.html が想定と違う（{blob}）')
src = raw.decode('utf8')
if 'v0.88' not in src:
    sys.exit('元の index.html が v0.88 ではない')


def rep(s, a_, b_, n=1):
    c = s.count(a_)
    if c != n:
        sys.exit(f'置き換える所が {n} か所でない（{c} か所）：{a_[:70]}')
    return s.replace(a_, b_)


s = src
# ---- 保存キー・設定のキーを試遊版だけのものに ----
s = rep(s, "const SAVE_KEY='eiheiji_vs_beasts_v010'", "const SAVE_KEY='eiheiji_vs_beasts_p3e2forest'")
s = rep(s, "const SND_KEY='REWILDED_EIHEIJI_SETTINGS'", "const SND_KEY='REWILDED_EIHEIJI_SETTINGS_p3e2forest'")
s = rep(s, "const WEATHER_PREF='eiheiji_weatherEffects'", f"const WEATHER_PREF='{PRE}weatherEffects'")
for k, n in (('shadow', 2), ('perf', 2), ('aimMode', 3), ('detail', 2)):
    s = rep(s, f"'eiheiji_{k}'", f"'{PRE}{k}'", n)
MAIN_KEYS = ['eiheiji_vs_beasts_v010', 'REWILDED_EIHEIJI_SETTINGS', 'eiheiji_weatherEffects',
             'eiheiji_shadow', 'eiheiji_perf', 'eiheiji_aimMode', 'eiheiji_detail']
for k in MAIN_KEYS:
    if re.search(r"['\"`]" + re.escape(k) + r"['\"`]", s):
        sys.exit(f'本編のキーが残っている：{k}')
left = sorted(set(re.findall(r"localStorage\.(?:getItem|setItem|removeItem)\(\s*'([^']+)'", s)) - {'__t'})
if any(not (k.startswith(PRE) or k.endswith('p3e2forest')) for k in left):
    sys.exit(f'試遊版のものでないキーがある：{left}')

# ページのいちばん初め：本編のキーは読まない・書かない・消さない（キーの文字列は分けて書く。上の確かめに掛からないように）
guard = ("<script>/* 試遊版だけ（previews/p3e2-forest）：本編のセーブと設定のキーには触れない */"
         "(function(){ try{ const B=new Set([" + ','.join("'" + k[:7] + "'+'" + k[7:] + "'" for k in MAIN_KEYS) + "]), S=Storage.prototype, g=S.getItem, st=S.setItem, r=S.removeItem;"
         " const no=(f,k)=>{ try{ console.warn('試遊版：本編のキーには触れない',f,k); }catch(e){} };"
         " S.getItem=function(k){ if(B.has(String(k))){ no('get',k); return null; } return g.call(this,k); };"
         " S.setItem=function(k,v){ if(B.has(String(k))){ no('set',k); return; } return st.call(this,k,v); };"
         " S.removeItem=function(k){ if(B.has(String(k))){ no('remove',k); return; } return r.call(this,k); };"
         " S.clear=function(){ no('clear',''); }; }catch(e){} })();</script>")
s = rep(s, '<head><meta charset=utf8>', '<head><meta charset=utf8>' + guard)

# ---- 版の表示 ----
m = re.search(r'<span class="tver">(v[0-9.]+) デモ版', s)
if not m or m.group(1) != 'v0.88':
    sys.exit('版の表示が見つからない')
s = s.replace(m.group(0), f'<span class="tver">{m.group(1)} 上志比の森林 検収用の試遊版（本編とは別に保存）', 1)

# ---- タイトル画面のボタン ----
BTN = 'style="font-size:12px;padding:6px 10px;min-height:0;touch-action:manipulation"'
s = rep(s, '    <div class="tact">',
        '    <div id="ftTitle" style="position:absolute;top:calc(8px + env(safe-area-inset-top,0px));right:calc(8px + env(safe-area-inset-right,0px));'
        'justify-content:flex-end;z-index:5;display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100% - 16px)">'
        f'<button id="btnFTStart" {BTN}>テスト：上志比の森で始める</button></div>\n    <div class="tact">')

test_code = r"""
// ---- 試遊用（試遊版 previews/p3e2-forest だけ）：E-2 上志比の森林の検収。docs/p3e2-forest-preview.md ----
const FT={busy:false, i:{kona:0,sugi:0,take:0,herb:0}};
function ftBase(){ freshState(); resetWorld(null); hideAllOv(); $('hud').hidden=false; S.mode='playing'; cv.focus();
 prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true; prog.chapter2=chapter2State(null,true); prog.chapter2.currentChapter=2;
 Object.assign(prog.chapter2.progress,{openingStarted:true,defenseComplete:true,defenseRewarded:true,radioHeard:true,departureDecision:true,departureComplete:true,mutantMet:true}); // 作業F は済み（山王の初遭遇も済み）
 prog.level=4; prog.exp=XP.lv[3]||0; P.maxHp=f31MaxHp(4); P.hp=P.maxHp;
 prog.arms.axeIron=WEAPONS.axeIron.maxDur; prog.arms.spear=WEAPONS.spear.maxDur; P.weapon='axeIron'; P.dur=prog.arms.axeIron;
 for(const [slot,id] of Object.entries({head:'forest_head',chest:'forest_chest',legs:'forest_legs',feet:'forest_feet'})){ if(!prog.gear.owned.includes(id)) prog.gear.owned.push(id); prog.gear.equip[slot]=id; }
 f47ApplyVisual(); updHolster(); refreshWeaponMesh(); f7Flush(); inv.onigiri=0; inv.bento=0; foodAdd('onigiri',3); foodAdd('bento',2);
 prog.kama.built=1; facApply(); // 光明寺のかまど（拠点）
 const t=trk(); Object.assign(t,{found:true,repaired:true,fueled:true,parts:['p1','p2'],trips:1,region:'komyoji',lv:4,gas:100}); t.fac=t.fac||{}; t.fac.aid=1; delete t.x; delete t.z; delete t.a; TRUCK.sync=false; }
// 歩ける・何も無い所か
function ftFree(x,z,r){ return kamiReach(x,z)&&kamiCls(x,z)!==2&&f4Free(x,z,r); }
function ftPut(x,z,lx,lz){ P.x=x; P.z=z; P.facing=Math.atan2(lx-x,lz-z); setCam(P.facing); }
// 木のそばの立てる所（木から少し離れた、歩ける所）
function ftNear(x,z,r0){ for(const r of [r0,r0+1,r0+2,r0+3.5]) for(let k=0;k<12;k++){ const a=k/12*TAU, px=x+Math.cos(a)*r, pz=z+Math.sin(a)*r; if(ftFree(px,pz,0.6)) return [px,pz]; } return null; }
// 林の場所：切れる木（当たり判定のある木。REG.live.ktrees）を 20m 四方に分けて、その種類が多い所を近い順に
function ftWoods(ty){ const out=[], G=new Map(); if(!REG.live||!REG.live.ktrees) return out;
 for(const t of REG.live.ktrees.values()){ if(t.felled||!t.ty) continue; const gk=Math.floor(t.x/20)*7919+Math.floor(t.z/20); let a=G.get(gk); if(!a){ a=[]; G.set(gk,a); } a.push(t); }
 for(const a of G.values()){ const L=a.filter(t=>t.ty===ty); if(L.length<6||L.length<a.length*0.5) continue; const o=L[0]; if(!kamiReach(o.x,o.z)) continue; out.push({x:o.x,z:o.z,d:dist(P.x,P.z,o.x,o.z)}); }
 return out.sort((p,q)=>p.d-q.d); }
async function ftGo(kind){ if(REG.cur!=='kamishihi'){ if(!(await ftTravel('kamishihi'))) return false; }
 if(kind==='herb'){ const H=REG.live.kw.nodes.filter(n=>n.k==='herb').map(n=>({n,d:dist(P.x,P.z,n.x,n.z)})).sort((p,q)=>p.d-q.d); if(!H.length){ toast('山の薬草が見つからない',true); return false; }
   const h=H[(FT.i.herb++)%Math.min(H.length,6)].n, p=ftNear(h.x,h.z,1.4)||[h.x+0.8,h.z]; ftPut(p[0],p[1],h.x,h.z); toast(`試遊：山の薬草のそばへ移った（白い小さな花の葉。全部で${H.length}か所。押すたびに近い所を順に）`); return true; }
 if(kind==='take'){ const C=(E2.take||[]).map(c=>({c,d:dist(P.x,P.z,c.x,c.z)})).sort((p,q)=>p.d-q.d); if(!C.length){ toast('竹林が見つからない',true); return false; }
   const c=C[(FT.i.take++)%Math.min(C.length,6)].c, r=1.0*c.s*E2GS.take+0.6, p=ftNear(c.x,c.z,r)||[c.x+r,c.z]; ftPut(p[0],p[1],c.x,c.z); toast('試遊：竹林のそばへ移った（「竹林の竹を切る」）'); return true; }
 if(kind==='view'){ let best=null; for(const n of REG.live.kw.nodes){ if(n.k!=='herb') continue; const h=kamiH(n.x,n.z); if(!best||h>best.h) best={h,x:n.x,z:n.z}; }
   if(!best){ toast('見晴らしの良い所が見つからない',true); return false; } const p=ftNear(best.x,best.z,2)||[best.x,best.z], lo=[[1,0],[0,1],[-1,0],[0,-1]].map(([dx,dz])=>[dx,dz,kamiH(p[0]+dx*30,p[1]+dz*30)]).sort((u,v)=>u[2]-v[2])[0]; ftPut(p[0],p[1],p[0]+lo[0]*30,p[1]+lo[1]*30); toast('試遊：森の奥の高い所へ移った（まわりを見渡す）'); return true; }
 const W=ftWoods(kind); if(!W.length){ toast('林が見つからない',true); return false; } const w=W[(FT.i[kind]++)%Math.min(W.length,6)], p=ftNear(w.x,w.z,2.4)||[w.x+2.4,w.z]; ftPut(p[0],p[1],w.x,w.z);
 toast(kind==='kona'?'試遊：広葉樹の林へ移った（鉄の斧で切ると苗木が取れる）':'試遊：杉林へ移った（杉は苗木が取れない・今までどおり）'); return true; }
async function ftTravel(to){ if(REG.cur===to) return true; FT.busy=true; try{ const ok=await regionTravel(to,null,{force:true}); if(!ok){ toast(to==='kamishihi'?'上志比を読み込めませんでした':'光明寺へ戻れませんでした',true); return false; } return true; } finally{ FT.busy=false; } }
// KEI truck を自分のそばへ（上志比にいるときは上志比へ）
function ftTruck(){ const t=trk(); for(const [r,w] of [[4,1.8],[5.5,1.8],[7,1.8],[9,1.8],[5,1.3],[7,1.3],[10,1.3],[13,1.3]]) for(let k=0;k<16;k++){ const a=P.facing+Math.PI/2+k/16*TAU, x=P.x+Math.sin(a)*r, z=P.z+Math.cos(a)*r; const ok=REG.cur==='kamishihi'?ftFree(x,z,w):(szWalkable(x,z)&&szFree(x,z,w));
   if(ok){ t.region=REG.cur; t.x=x; t.z=z; t.a=P.facing; t.tip=0; TRUCK.sync=false; TRUCK.drive=false; toast('試遊：KEI truck をそばに置いた（荷台に救急箱。山の薬草を入れられる）'); return true; } }
 toast('KEI truck を置ける平らな所がない（少し動いてからもう一度）',true); return false; }
async function ftKamado(){ if(!(await ftTravel('komyoji'))) return; prog.kama.built=1; facApply(); const p=FAC.kama.pos; P.x=p.x; P.z=p.z+FAC.kama.D/2+0.9; P.facing=Math.PI; setCam(P.facing);
 toast('試遊：光明寺のかまどの前へ移った（「山の薬草で薬草粥を炊く」。米と木材は「素材を足す」で）'); }
function ftItems(){ inv.naegi=(inv.naegi||0)+3; inv.mherb=(inv.mherb||0)+3; foodAdd('rice',3); inv.wood=(inv.wood||0)+10; f7Flush(); toast(`試遊：苗木+3（${inv.naegi}）・山の薬草+3（${inv.mherb}）・米+3・木材+10`); saveGame(); }
function ftHeal(){ if(P.dead) return; P.hp=P.maxHp; foodAdd('onigiri',2); f7Flush(); toast('試遊：体力を戻し、おにぎりを2つ足した'); }
// 時間を進める：遊んだ時間（苗木・山の薬草・竹が戻るのに使う）と、ゲームの中の時刻を一緒に
function ftTime(sec){ stats.time+=sec; if(typeof p3bAdvance==='function') p3bAdvance(sec/P3B.hour); E2.t=0; if(REG.cur==='kamishihi'&&REG.live){ kamiNodesUpdate(REG.live,stats.time); E2.dirty=true; }
 toast(`試遊：時間を${Math.round(sec/60)}分進めた（ゲームの中の${Math.round(sec/P3B.hour)}時間）`); }
function ftNoon(){ prog.f10.tod=150; f10LightNow(); toast('試遊：朝9時にした（昼の間は鳥の声がする）'); }
function ftStat(){ const k=prog.kami||{pl:{}}, T=stats.time, pl=Object.values(k.pl||{}), nx=pl.length?Math.max(0,Math.min(...pl)+E2.grow-T):0, h=p3bClock();
 return `${REG.cur==='kamishihi'?'上志比':'光明寺'}　${h[0]}:${String(h[1]).padStart(2,'0')}　苗木 ${inv.naegi||0}・山の薬草 ${inv.mherb||0}・米 ${inv.rice||0}・木材 ${inv.wood||0}`+
   `<br>植えた苗木 ${pl.length}${pl.length?`（次に育つまで ${fmtTime(nx)}）`:''}・救急箱の薬草 ${stats.time<(TRUCK.herbT||0)?'あと'+fmtTime(TRUCK.herbT-stats.time):'なし'}・描く細かさ ${GFX.detail==='lite'?'軽量':'標準'}`; }
async function ftStart(){ if(FT.busy) return; ftBase(); if(!(await ftTravel('kamishihi'))) return; for(let i=0;i<4;i++){ await ftGo('kona'); if(ftTruck()) break; } prog.f10.tod=150; f10LightNow(); saveGame();
 banner('試遊：上志比の森（v0.88）','広葉樹の林の中から始めます。画面の左上の「試遊メニュー」で、場所を移る・素材を足す・時間を進めることができます（本編とは別に保存）',8); }
{ const b=document.getElementById('btnFTStart'); if(b) b.addEventListener('click',()=>ftStart());
  const tg=document.createElement('button'); tg.id='ftToggle'; tg.textContent='試遊メニュー';
  tg.style.cssText='position:fixed;top:120px;left:calc(8px + env(safe-area-inset-left,0px));z-index:40;font-size:12px;padding:5px 12px;min-height:0;opacity:.9;touch-action:manipulation';
  const pn=document.createElement('div'); pn.id='ftPanel';
  pn.style.cssText='position:fixed;top:156px;left:calc(8px + env(safe-area-inset-left,0px));z-index:40;width:min(calc(100vw - 16px),540px);max-height:300px;overflow-y:auto;-webkit-overflow-scrolling:touch;'+
   'background:rgba(18,26,20,.93);color:#eef3ea;border:1px solid rgba(255,255,255,.25);border-radius:10px;padding:8px 10px;box-sizing:border-box;font-size:12px;line-height:1.5;touch-action:manipulation';
  const G=(t,btns)=>`<div style="margin:6px 0 2px;color:#b9d7a5;font-weight:bold">${t}</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:5px">${btns.map(([id,l])=>`<button data-ft="${id}" style="font-size:12px;padding:7px 6px;min-height:36px;touch-action:manipulation">${l}</button>`).join('')}</div>`;
  pn.innerHTML=`<div id="ftStat" style="opacity:.9"></div>`+
   G('場所を移る（上志比）',[['kona','広葉樹の林へ'],['sugi','杉林へ'],['take','竹林へ'],['herb','山の薬草のそばへ'],['view','森の奥の高い所へ'],['truck','KEI truck をそばに呼ぶ']])+
   G('かまど（光明寺）',[['kamado','光明寺のかまどの前へ'],['back','上志比の森へ戻る']])+
   G('持ち物',[['items','苗木・山の薬草・米・木材を足す'],['heal','体力を戻す・食料を足す']])+
   G('時間',[['t5','5分進める'],['t20','20分進める（薬草が戻る）'],['t40','40分進める（苗木が育つ）'],['noon','朝9時にする']])+
   G('画面',[['detail','描く細かさを切り替える'],['close','メニューを閉じる']])+
   `<div style="margin-top:6px;opacity:.75">時間を進めると、食べ物の傷み・工事なども同じだけ進みます。数はすべて暫定です。</div>`;
  document.body.appendChild(tg); document.body.appendChild(pn); tg.hidden=true; pn.hidden=true;
  const stat=()=>{ const el=document.getElementById('ftStat'); if(el&&!pn.hidden) el.innerHTML=ftStat(); };
  const close=()=>{ pn.hidden=true; try{ cv.focus(); }catch(e){} };
  tg.addEventListener('click',e=>{ e.stopPropagation(); pn.hidden=!pn.hidden; stat(); if(pn.hidden) close(); });
  pn.addEventListener('click',async e=>{ e.stopPropagation(); const bt=e.target.closest('button[data-ft]'); if(!bt) return; const k=bt.dataset.ft;
    if(FT.busy||REG.busy){ toast('読み込み中。少し待ってから',true); return; } if(P.dead&&k!=='close'){ toast('倒れている間は使えない',true); return; }
    if(['kona','sugi','take','herb','view'].includes(k)){ close(); await ftGo(k); }
    else if(k==='truck'){ close(); if(REG.cur!=='kamishihi') await ftGo('kona'); ftTruck(); }
    else if(k==='kamado'){ close(); await ftKamado(); }
    else if(k==='back'){ close(); await ftGo('kona'); }
    else if(k==='items') ftItems(); else if(k==='heal') ftHeal();
    else if(k==='t5') ftTime(300); else if(k==='t20') ftTime(1200); else if(k==='t40') ftTime(2400); else if(k==='noon') ftNoon();
    else if(k==='detail') applyDetail(GFX.detail==='lite'?'std':'lite'); else if(k==='close') close();
    stat(); });
  // 置き場所：画面の左の上にある表示（体力・目標の帯など）のすぐ下。PC とスマホで表示の大きさが違うので、毎回測る（いつも出ている体力の欄 #stats と目標の帯 #objective だけを測る。通知や案内の文では動かさない。スマホのスティックの範囲は画面の下側なので、その上に収まる）
  const place=()=>{ let y=4; for(const id of ['stats','objective']){ const el=document.getElementById(id); if(!el) continue; const b=el.getBoundingClientRect(), cs=getComputedStyle(el); if(b.width<4||b.height<4||cs.visibility==='hidden'||cs.opacity==='0') continue;
      if(b.top<innerHeight*0.35&&b.left<innerWidth*0.45) y=Math.max(y,b.bottom); }
    tg.style.top=Math.round(y+6)+'px'; pn.style.top=Math.round(y+42)+'px'; pn.style.maxHeight=Math.max(180,Math.round(innerHeight-y-42-120))+'px'; };
  setInterval(()=>{ const on=S.mode==='playing'; tg.hidden=!on; if(!on) pn.hidden=true; if(on) place(); stat(); },500); }
"""
s = rep(s, '// ================= NPC =================', test_code + '// ================= NPC =================')

os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf8').write(s)
print('wrote', os.path.relpath(OUT, ROOT), len(s), 'bytes ／ 元：', where, blob[:12])
