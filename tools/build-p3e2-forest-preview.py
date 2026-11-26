#!/usr/bin/env python3
"""v0.88（P3-E の E-2：上志比の森林）の検収用の試遊版を作る（previews/p3e2-forest/index.html）。docs/p3e2-forest-preview.md

- 元にするのは v0.90 の index.html（既定はコミット 93b1da2。三人称カメラの上下の操作の公開の準備、cam-pitch、2026-11-26）。本編の index.html（main）は使わない・変えない
- 保存キーと設定のキーを、すべて試遊版だけのものに変える（本編のセーブ・設定を読まない・書かない）
  さらにページのいちばん初めで、本編のキーを読む・書く・消すのを止める（変え忘れがあっても本編に触れない）
- タイトル画面の右上に「テスト：上志比の森で始める」ボタン
  （防衛戦と作業F は済み・鉄の斧・直した KEI truck に荷台の救急箱・光明寺のかまどは建ててある）
- 遊んでいる間は、画面の上の「試遊メニュー」から：森の中の場所へ移る・KEI truck をそばに呼ぶ・光明寺のかまどへ行く・
  苗木と山の薬草と素材を足す・時間を進める・昼にする・描く細かさを切り替える

使い方：python3 tools/build-p3e2-forest-preview.py [--ref コミット] [--src index.html のパス] [--out 出力パス]
"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = '93b1da2095306396794992ecb0761c0752aaddbf'  # v0.90：三人称カメラの上下の操作の公開の準備、cam-pitch、2026-11-26
BLOB = '01d98dbdb6d7fc7b01ff04836507e845c989a8be'  # v0.90 の index.html（git の blob）
# それより前：REF = b8d35964acbec591c3c9f6f9fd39bf9cb8a530fe（v0.89（P3-E の E3-1・古い農家の中）の公開の準備、p3e3-farm-interior、2026-11-26）・BLOB = 4365d9987c4c277969e1ee241ac3e6be3c49e33d
# それより前：REF = a4120aa61866a1cdea4ea88ae83c66ca94fd2010（v0.88.1（作業中）：森の音を静かに・KEI truck の音（作り直し：5段ギア・水平対向4気筒・始動音）、v0.88.1-sound、2026-11-25）・BLOB = 96f9ee20178d091de855e63d61e345f0c2867707
# それより前：REF = a12e3faf3bfef6be203778926b04d85d65a88877（v0.88.1（作業中）：森の音を静かに・KEI truck の音・地域移動ですぐ無音、v0.88.1-sound、2026-11-25）・BLOB = dc4bbc7f5e85398a0eb75851c5d053bec9b33353
# それより前：REF = 38f883654f64401c29296f874269ff16ede4ccfb（v0.88.1（作業中）：森の音を静かに・KEI truck の音、v0.88.1-sound、2026-11-25）・BLOB = ab50466f2f746ef6ec3a8996c96424ab3a2d7d2a
# それより前：REF = b821333719011fe6bc89324d561abfef03171c81（v0.88 の統合＋森の音の修正、2026-11-25）・BLOB = af8f36656f017ef5554655a8dbb908d1bfc73b82
# それより前：REF = 151a04c7475554743745be717e796c735d403667（v0.88 の統合。v0.87.1＋E-2＋2026-11-25 の決定）・BLOB = 36b848506691e5d00fd072b202b841f57491b8a2
# それより前：REF = d381dfb2f8b1bd3b2fb7d04264b6da000944b997（p3e2-hurt-drop-src。ddd2d39 に被ダメージで運搬を手放す修正）・BLOB = 8f41da70b479ed31dc4e3c19b5b75fd02f91fa7f
# それより前：REF = ddd2d3929b611fbaad02ecd46a991c2ba11a87aa（p3e2-truck-log-attrs。丸太の種類を保つ修正）・BLOB = a05aedc15339f5315cfbe06e1b7de0bc68a633e5
# さらに前：REF = f0abc54（p3e2-felling-fix。伐採の修正）・BLOB = fd42dd13…、さらに前は REF = e378a7b（p3e2-forest）・BLOB = 1d59ead7…
OUT = os.path.join(ROOT, 'previews', 'p3e2-forest', 'index.html')
PRE = 'eiheiji_p3e2f_'  # 試遊版の設定のキーの頭

ap = argparse.ArgumentParser()
ap.add_argument('--ref', default=REF, help='index.html を取り出すコミット（既定：v0.90 の 93b1da2）')
ap.add_argument('--src', help='git から取り出さず、このファイルを元にする')
ap.add_argument('--out', help='出力先（既定：previews/p3e2-forest/index.html）')
a = ap.parse_args()
out = OUT if a.out is None else os.path.abspath(a.out)
if a.out is None:
    os.makedirs(os.path.dirname(out), exist_ok=True)
elif not os.path.isdir(os.path.dirname(out)):
    sys.exit(f'出力先のフォルダがない：{os.path.dirname(out)}')

if a.src:
    raw = open(a.src, 'rb').read()
    where = a.src
else:
    try:
        raw = subprocess.run(['git', '-C', ROOT, 'show', f'{a.ref}:index.html'], check=True, capture_output=True).stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f'{a.ref} の index.html を取り出せない（REF のコミットが無ければ git fetch origin main か v0.88-integration をしてから）：{e.stderr.decode(errors="replace").strip()}')
    where = a.ref
blob = hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest()
if not a.src and a.ref == REF and blob != BLOB:
    sys.exit(f'元の index.html が想定と違う（{blob}）')
src = raw.decode('utf8')
if not re.search(r'<span class="tver">v0\.(?:8[89]|9[0-9])(?:\.[0-9]+)? デモ版', src):
    sys.exit('元の index.html が v0.88・v0.89・v0.9x 系ではない')


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
# 古い REF の index.html には上下の設定がない。
if "'eiheiji_camPitch'" in s:
    s = rep(s, "'eiheiji_camPitch'", f"'{PRE}camPitch'")
MAIN_KEYS = ['eiheiji_vs_beasts_v010', 'REWILDED_EIHEIJI_SETTINGS', 'eiheiji_weatherEffects',
             'eiheiji_shadow', 'eiheiji_perf', 'eiheiji_aimMode', 'eiheiji_detail', 'eiheiji_camPitch']
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
if not m or not re.fullmatch(r'v0\.(?:8[89]|9[0-9])(?:\.[0-9]+)?', m.group(1)):
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
   `<br>植えた苗木 ${pl.length}${pl.length?`（次に育つまで ${fmtTime(nx)}）`:''}・救急箱の薬草 ${stats.time<(TRUCK.herbT||0)?'あと'+fmtTime(TRUCK.herbT-stats.time):'なし'}・描く細かさ ${GFX.detail==='lite'?'軽量':'標準'}・案内 ${PUI.on?'新しい形':'今までの形'}`; }
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
   G('画面',[['detail','描く細かさを切り替える'],['pui','案内の表示：新しい形 ⇄ 今までの形'],['close','メニューを閉じる']])+
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
    else if(k==='pui'){ puiSet(!PUI.on); toast(PUI.on?'試遊：案内の表示を「新しい形」にした（名前だけ小さく。押すと詳しく）':'試遊：案内の表示を「今までの形」にした（比べる用）'); }
    stat(); });
  // 置き場所：画面の左の上にある表示（体力・目標の帯など）のすぐ下。PC とスマホで表示の大きさが違うので、毎回測る（いつも出ている体力の欄 #stats と目標の帯 #objective だけを測る。通知や案内の文では動かさない。スマホのスティックの範囲は画面の下側なので、その上に収まる）
  const place=()=>{ let y=4; const tb=tg.getBoundingClientRect(), tw=Math.max(tb.width,100); const els=['stats','objective'].map(id=>document.getElementById(id)).concat(touchMode?[...document.querySelectorAll('#touch button')]:[]);
    for(const el of els){ if(!el) continue; const b=el.getBoundingClientRect(), cs=getComputedStyle(el); if(b.width<4||b.height<4||cs.visibility==='hidden'||cs.display==='none'||cs.opacity==='0'||el.closest('[hidden]')) continue;
      if(b.top<innerHeight*0.35&&b.left<8+tw) y=Math.max(y,b.bottom); } // 左上の、ボタンが入る幅にある物（体力の欄・目標の帯・スマホの地図ボタンなど）の下
    tg.style.top=Math.round(y+6)+'px'; pn.style.top=Math.round(y+42)+'px'; pn.style.maxHeight=Math.max(180,Math.round(innerHeight-y-42-120))+'px'; };
  setInterval(()=>{ const on=S.mode==='playing'; tg.hidden=!on; if(!on) pn.hidden=true; if(on) place(); stat(); },500); }
"""
s = rep(s, '// ================= NPC =================', test_code + '// ================= NPC =================')

# ---- 「調べる」の案内（#prompt）を小さくする（2026-11-23 ユーザー依頼。まず試遊版だけ。docs/prompt-ui.md） ----
# 近くの調べられる物（木・採集物・施設・住民・探索地点・KEI truck など）は、すべて interactables() → #prompt の1か所で出る。
# ここだけを変える：ふだんは名前だけの小さな1行（括弧の中の説明は省く。「長押し」の操作の説明は残す）。押すと全文（詳しく）。
# 会話・選択肢・警告（toast）・大きな案内（banner）・チュートリアルは別の部品なので変えない。調べる操作（E・行動ボタン）と判定も変えない。
PROMPT_OLD = ("  const pr=$('prompt');\n"
              "  if(curInter){ pr.hidden=false; const t=(touchMode?'T':'E')+curInter.label; if(txtCache.get('prompt')!==t){ txtCache.set('prompt',t); pr.innerHTML=''; const k=document.createElement('span'); k.className='k'; k.textContent=touchMode?'調べる':'E'; pr.appendChild(k); pr.appendChild(document.createTextNode(curInter.label)); } }\n"
              "  else pr.hidden=true;\n"
              "  $('tbAct').classList.toggle('ready',!!curInter);\n"
              "  $('tbAct').classList.toggle('quiet',!!curInter&&touchMode); // v0.33：帯が出ている間はボタンの光を弱める\n")
PROMPT_NEW = ("  const pr=$('prompt');\n"
              "  if(PUI.on) puiUpdate(pr,curInter); else { // 試遊版：今までの形（比べる用。下の2行は v0.88 のまま）\n"
              "  if(curInter){ pr.hidden=false; const t=(touchMode?'T':'E')+curInter.label; if(txtCache.get('prompt')!==t){ txtCache.set('prompt',t); pr.innerHTML=''; const k=document.createElement('span'); k.className='k'; k.textContent=touchMode?'調べる':'E'; pr.appendChild(k); pr.appendChild(document.createTextNode(curInter.label)); } }\n"
              "  else pr.hidden=true; }\n"
              "  $('tbAct').classList.toggle('ready',!!curInter);\n"
              "  $('tbAct').classList.toggle('quiet',!!curInter&&touchMode&&!PUI.on); // v0.33：帯が出ている間はボタンの光を弱める（新しい形では帯が小さいので弱めない）\n")
s = rep(s, PROMPT_OLD, PROMPT_NEW)
prompt_code = r"""
// ---- 「調べる」の案内を小さく（試遊版 previews/p3e2-forest だけ。docs/prompt-ui.md） ----
const PUI={on:true,key:'',open:false,t:0};
// 名前だけ：全角の括弧（素材の数・秒数などの説明）を省く。操作の説明（長押し）は残す
function puiShort(l){ const s=String(l).replace(/（[^（）]*）/g,m=>/長押し/.test(m)?m:'').replace(/[ 　]+$/,'').replace(/[ 　]{2,}/g,'　'); return s||String(l); }
// 置き場所：まわりの表示（体力の欄・目標の帯・持ち物の数・地図・防衛戦とボス戦の帯・操作の説明・手持ちバー・スマホのボタン・試遊メニュー）を測って、
// 重ならない所へ。まず画面の上の真ん中（目標の帯のすぐ下。主人公の頭より上）、だめなら右寄せ、左寄せ。PC もスマホも同じ。測るのは中身が変わったときと0.5秒に1回
function puiRects(skip){ const out=[], add=el=>{ if(!el||el===skip) return; const b=el.getBoundingClientRect(), cs=getComputedStyle(el); if(b.width<4||b.height<4||cs.visibility==='hidden'||cs.display==='none'||cs.opacity==='0'||el.closest('[hidden]')) return; out.push([b.left,b.top,b.right,b.bottom]); };
  for(const id of ['stats','notice','objective','res','coreBar','bossBar','mini','help','items']) add(document.getElementById(id));
  if(touchMode) for(const el of document.querySelectorAll('#touch button')) add(el);
  add(document.getElementById('ftToggle')); return out; }
// x0〜x1 の幅で、画面の上半分にある物の下へ落とした y
function puiDrop(R,x0,x1,y0){ let y=y0; for(const r of R) if(r[0]<x1&&x0<r[2]&&r[1]<innerHeight*0.45) y=Math.max(y,r[3]+6); return y; }
function puiPlace(pr){ PUI.t=0.5; const R=puiRects(pr), b=pr.getBoundingClientRect(), w=b.width, h=b.height, W=innerWidth, H=innerHeight, top0=8;
  const hit=(x,y)=>R.some(r=>x<r[2]&&r[0]<x+w&&y<r[3]&&r[1]<y+h);
  let best=null; for(const x of [(W-w)/2, W-w-10, 10]){ const y=puiDrop(R,x,x+w,top0); if(y+h<=H*0.62&&!hit(x,y)){ best=[x,y]; break; } }
  if(!best){ const x=(W-w)/2; best=[x,puiDrop(R,x,x+w,top0)]; }
  pr.style.setProperty('--pui-x',Math.round(Math.max(4,best[0]))+'px'); pr.style.setProperty('--pui-y',Math.round(best[1])+'px'); }
function puiUpdate(pr,ci){
  if(!ci){ if(!pr.hidden){ pr.hidden=true; } PUI.key=''; PUI.open=false; return; }
  const full=String(ci.label), sh=puiShort(full), more=sh!==full;
  if(sh!==PUI.key){ PUI.key=sh; PUI.open=false; } // 別の物に近づいたら、詳しい説明は閉じる
  const open=PUI.open&&more; pr.hidden=false; pr.classList.add('cmp'); pr.classList.toggle('open',open); pr.classList.toggle('more',more);
  const t='P'+(touchMode?'T':'E')+(open?'1':'0')+(more?'+':'-')+(open?full:sh);
  if(txtCache.get('prompt')!==t){ txtCache.set('prompt',t); pr.innerHTML='';
    if(!touchMode){ const k=document.createElement('span'); k.className='k'; k.textContent='E'; pr.appendChild(k); } // スマホは「調べる」ボタンが光るので、字の札は付けない
    const tx=document.createElement('span'); tx.className='tx'; tx.textContent=open?full:sh; pr.appendChild(tx);
    if(more){ const m=document.createElement('span'); m.className='mo'; m.textContent=open?'閉じる':'詳しく'; pr.appendChild(m); }
    pr.title=more?(open?'押すと閉じる':'押すと詳しい説明'):''; puiPlace(pr); }
  PUI.t-=1/30; if(PUI.t<=0) puiPlace(pr); }
function puiSet(on){ PUI.on=!!on; PUI.key=''; PUI.open=false; const pr=$('prompt'); pr.classList.remove('cmp','open','more'); pr.style.removeProperty('--pui-x'); pr.style.removeProperty('--pui-y'); pr.title=''; txtCache.delete('prompt'); }
{ const pr=document.getElementById('prompt'); if(pr){ pr.addEventListener('click',e=>{ e.stopPropagation(); if(!PUI.on||!pr.classList.contains('more')) return; PUI.open=!PUI.open; txtCache.delete('prompt'); try{ cv.focus(); }catch(_){} });
  pr.addEventListener('pointerdown',e=>{ if(PUI.on) e.stopPropagation(); }); } }
"""
s = rep(s, '// ================= NPC =================', prompt_code + '// ================= NPC =================')
PROMPT_CSS = ("<style>/* 試遊版だけ（previews/p3e2-forest）：「調べる」の案内を小さく。docs/prompt-ui.md */\n"
  "#prompt.cmp{display:flex;align-items:center;gap:6px;left:var(--pui-x,50%)!important;right:auto!important;top:var(--pui-y,44px)!important;transform:none!important;"
  "bottom:auto!important;width:max-content!important;max-width:min(420px,calc(100vw - 24px))!important;margin:0!important;box-sizing:border-box;"
  "font-size:12px!important;line-height:1.45!important;padding:3px 10px!important;border-radius:13px!important;white-space:nowrap!important;text-align:left!important;"
  "background:rgba(22,24,20,.58)!important;box-shadow:none!important;border-color:rgba(255,255,255,.18)!important;pointer-events:auto;cursor:default;opacity:.94;}\n"
  "#prompt.cmp[hidden]{display:none!important}\n"
  "#prompt.cmp .k{flex:none;font-size:11px;line-height:16px;padding:0 5px;margin:0;border-radius:3px;}\n"
  "#prompt.cmp .tx{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}\n"
  "#prompt.cmp .mo{flex:none;font-size:10.5px;color:var(--gold);opacity:.9;border-left:1px solid rgba(255,255,255,.2);padding-left:6px;}\n"
  "#prompt.cmp.more{cursor:pointer;}\n"
  "#prompt.cmp.open{white-space:normal!important;width:auto!important;max-width:min(520px,calc(100vw - 24px))!important;align-items:flex-start;}\n"
  "#prompt.cmp.open .tx{white-space:normal;overflow:visible;}\n"
  "</style>")
s = rep(s, '</head>', PROMPT_CSS + '</head>')

with open(out, 'w', encoding='utf8') as output:
    output.write(s)
print('wrote', out, len(s.encode('utf8')), 'bytes ／ 元：', where, blob[:12])
