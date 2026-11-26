#!/usr/bin/env python3
"""古い農家（E3-1・E3-2）の検収用の試遊版を作る。docs/p3e3-farm-preview.md を参照。"""
import argparse
import hashlib
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = 'b0d81988bbf755f63bb556b077df7f411ec4d1ef'  # E3-2：古い農家の調査・アイテム発見と入口の選び方の直し、p3e3-search、2026-11-26
BLOB = 'b0ae7edaa9ae04d2f00f3b4bf3873843bb20c2f1'  # E3-2 の index.html（git の blob）
# それより前：REF = e41f38854bbbe464187c8b54f91613d1d244419a（E3-2：古い農家の調査・アイテム発見、p3e3-search、2026-11-26）・BLOB = 8685c4d8c0f6045548970337c49931f483c3e96e
# それより前：REF = 93b1da2095306396794992ecb0761c0752aaddbf（v0.90：三人称カメラの上下の操作の公開の準備、cam-pitch、2026-11-26）・BLOB = 01d98dbdb6d7fc7b01ff04836507e845c989a8be
# それより前：REF = b8d35964acbec591c3c9f6f9fd39bf9cb8a530fe（v0.89（P3-E の E3-1・古い農家の中）の公開の準備、p3e3-farm-interior、2026-11-26）・BLOB = 4365d9987c4c277969e1ee241ac3e6be3c49e33d
# それより前：REF = d2cf2f4f3d1c7a92b89da44cc9387ee99ca5862f（v0.88.1 に E3-1 を入れたもの）・BLOB = 603f7ce7421bef937bc12f998b049b19386f650c
OUT = os.path.join(ROOT, 'previews', 'p3e3-farm', 'index.html')
PRE = 'eiheiji_p3e3f_'  # 試遊版の設定のキーの頭

ap = argparse.ArgumentParser()
ap.add_argument('--ref', default=REF, help='index.html を取り出すコミット（既定：b0d8198）')
ap.add_argument('--src', help='git から取り出さず、このファイルを元にする')
ap.add_argument('--out', help='出力先（既定：previews/p3e3-farm/index.html）')
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
        sys.exit(f'{a.ref} の index.html を取り出せない（元ファイルが手元にある場合は --src を使う）：{e.stderr.decode(errors="replace").strip()}')
    where = a.ref
blob = hashlib.sha1(b'blob %d\0' % len(raw) + raw).hexdigest()
if not a.src and blob != BLOB:
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
s = rep(s, "const SAVE_KEY='eiheiji_vs_beasts_v010'", "const SAVE_KEY='eiheiji_vs_beasts_p3e3farm'")
s = rep(s, "const SND_KEY='REWILDED_EIHEIJI_SETTINGS'", "const SND_KEY='REWILDED_EIHEIJI_SETTINGS_p3e3farm'")
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
if any(not (k.startswith(PRE) or k.endswith('p3e3farm')) for k in left):
    sys.exit(f'試遊版のものでないキーがある：{left}')

# ページのいちばん初め：本編のキーは読まない・書かない・消さない（キーの文字列は分けて書く。上の確かめに掛からないように）
guard = ("<script>/* 試遊版だけ（previews/p3e3-farm）：本編のセーブと設定のキーには触れない */"
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
s = s.replace(m.group(0), f'<span class="tver">{m.group(1)} 古い農家（E3-1・E3-2） 検収用の試遊版（本編とは別に保存）', 1)

# ---- タイトル画面のボタン ----
BTN = 'style="font-size:12px;padding:6px 10px;min-height:36px;touch-action:manipulation"'
s = rep(s, '    <div class="tact">',
        '    <div id="farmTitle" style="position:absolute;top:calc(8px + env(safe-area-inset-top,0px));right:calc(8px + env(safe-area-inset-right,0px));'
        'justify-content:flex-end;z-index:5;display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100% - 16px)">'
        f'<button id="btnFarmStart" {BTN}>テスト：古い農家の前で始める</button></div>\n    <div class="tact">')

test_code = r"""
// ---- 古い農家（E3-1・E3-2）の試遊版だけ。docs/p3e3-farm-preview.md ----
const FARM_TIMES=[
  ['朝', 9, 'day'], ['夕方', 17, 'dusk'], ['夜', 23, 'night']
];
function farmPreviewDoor(){ return P3A.doors.find(d=>d.id==='house26'); }
function farmPreviewBase(){
  regionResetHome(); freshState(); resetWorld(null); hideAllOv();
  $('hud').hidden=false; S.mode='playing'; cv.focus();
  Object.assign(prog,{bossDefeated:true,stage:'cleared',unlockTrap:true,unlockBoss:true,introSeen:true});
  prog.chapter2=chapter2State(null,true); prog.chapter2.currentChapter=2;
  Object.assign(prog.chapter2.progress,{
    openingStarted:true,defenseComplete:true,defenseRewarded:true,radioHeard:true,
    departureDecision:true,departureComplete:true,mutantMet:true
  });
  Object.assign(trk(),{found:true,repaired:true,fueled:true,parts:['p1','p2'],trips:1,region:'komyoji',lv:4,gas:100});
  TRUCK.sync=false;
  Object.assign(p3bState().hq,{sv:[1,1,1],talk:1,plan:1,visited:1,beasts:1});
  szJoin();
}
function farmPreviewTod(hour){ return (hour-P3B.h0)*P3B.hour; }
function farmPreviewClock(index){
  FARM_PREVIEW.time=index;
  prog.f10.tod=farmPreviewTod(FARM_TIMES[index][1]);
  f10LightNow();
}
// 農家のそばでは初遭遇と同じ処理で獣を遠ざけ、離れたら動けるようにする。
function farmPreviewShelter(){
  if(!FARM_PREVIEW.shelter) return;
  const door=farmPreviewDoor();
  if(REG.cur==='kamishihi'&&door&&(P3A.inside||dist(P.x,P.z,door.x,door.z)<35)) stfHoldBeasts(door);
  else stfRelease();
}
async function farmPreviewGo(start=false){
  if(FARM_PREVIEW.busy||REG.busy||P3A.busy) return;
  FARM_PREVIEW.busy=true;
  try{
    if(start){ audioInit(); farmPreviewBase(); }
    if(TRUCK.drive) truckExit(true);
    if(P3A.inside) await p3aExit();
    if(REG.cur!=='kamishihi'&&!(await regionTravel('kamishihi',null,{force:true}))) return;
    const door=farmPreviewDoor();
    if(door){
      // 入口から 1.75m を優先し、当たり判定と地形を調べる。
      const outward=-KAMI.D.bld[26][4];
      for(const radius of [1.75,2,1.5]) for(const step of [0,1,-1,2,-2,3,-3,4,-4,5,-5,6,-6,7,-7,8,-8,9,-9,10,-10,11,-11,12]){
        const angle=outward+step/24*TAU, x=door.x+Math.sin(angle)*radius, z=door.z+Math.cos(angle)*radius;
        if(!szWalkable(x,z)||!f4Free(x,z,P.r+0.1)) continue;
        P.x=x; P.z=z; P.facing=Math.atan2(door.x-x,door.z-z); setCam(P.facing);
        FARM_PREVIEW.shelter=true; farmPreviewShelter(); p3aSzFollow();
        if(start){ resetWeather(); farmPreviewClock(0); }
        saveGame();
        toast(start?'試遊：古い農家の前から始めた（入口で「古い農家に入る」）':'試遊：古い農家の前に戻った');
        return;
      }
    }
    toast('古い農家の入口の前に立てる場所が見つかりませんでした',true);
  }finally{ FARM_PREVIEW.busy=false; }
}
{
  const tg=document.createElement('button'), pn=document.createElement('div');
  tg.id='farmToggle'; tg.textContent='試遊メニュー';
  tg.style.cssText='position:fixed;left:calc(8px + env(safe-area-inset-left,0px));z-index:40;font-size:12px;padding:5px 12px;min-height:0;opacity:.9;touch-action:manipulation';
  pn.id='farmPanel';
  pn.style.cssText='position:fixed;left:calc(8px + env(safe-area-inset-left,0px));z-index:40;width:min(calc(100% - 16px - env(safe-area-inset-left,0px) - env(safe-area-inset-right,0px)),540px);overflow-y:auto;'+
    'background:rgba(18,26,20,.93);color:#eef3ea;border:1px solid rgba(255,255,255,.25);border-radius:10px;padding:8px 10px;box-sizing:border-box;font-size:12px;line-height:1.5';
  pn.innerHTML='<div id="farmStat"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:5px;margin-top:6px">'+
    [['go','古い農家の前へ'],['suzuki',''],['time',''],['detail',''],['resetSearch','調査記録を初期化して試す']].map(([id,label])=>
      `<button data-farm="${id}" style="font-size:12px;padding:7px 6px;min-height:36px;touch-action:manipulation">${label}</button>`).join('')+'</div>';
  document.body.append(tg,pn); tg.hidden=true; pn.hidden=true;
  tg.setAttribute('aria-controls',pn.id); tg.setAttribute('aria-expanded','false');
  const setOpen=open=>{ pn.hidden=!open; tg.setAttribute('aria-expanded',String(open)); };
  const updateMenu=()=>{
    if(pn.hidden) return;
    const suzuki=!SZ.joined?'未加入':SZ.down?'倒れている':SZ.order==='follow'?'ついて来る':SZ.order==='wait'?'ここで待つ':'拠点で過ごす';
    const place=P3A.inside?(P3A.inId==='farm'?'農家の中':'別の建物の中'):'外';
    $('farmStat').textContent=`いる所：${place}　時刻：${p3bClockText()}　スズキ：${suzuki}`;
    const button=id=>pn.querySelector(`[data-farm="${id}"]`);
    button('suzuki').textContent='スズキ：'+suzuki;
    button('suzuki').disabled=!SZ.joined||SZ.down;
    button('time').textContent='時刻：'+(FARM_TIMES[FARM_PREVIEW.time]?.[0]||p3bClockText());
    button('detail').textContent='描く細かさ：'+(GFX.detail==='lite'?'軽量':'標準');
  };
  // 体力と目標の帯、そのほか左上に見えている操作ボタンの下に置く。
  const placeMenu=()=>{
    let y=4;
    const width=Math.max(tg.getBoundingClientRect().width,100);
    const els=[$('stats'),$('objective'),...(touchMode?document.querySelectorAll('#touch button'):[])];
    for(const el of els){
      const b=el.getBoundingClientRect(), cs=getComputedStyle(el);
      if(b.width>=4&&b.height>=4&&cs.visibility!=='hidden'&&cs.opacity!=='0'&&!el.closest('[hidden]')&&
         b.top<innerHeight*0.35&&b.left<8+width) y=Math.max(y,b.bottom);
    }
    const top=Math.min(Math.round(y+6),Math.max(0,innerHeight-120));
    tg.style.top=top+'px'; pn.style.top=(top+36)+'px';
    pn.style.maxHeight=`min(300px, calc(${Math.max(0,innerHeight-top-44)}px - env(safe-area-inset-bottom,0px)))`;
  };
  $('btnFarmStart').addEventListener('click',()=>farmPreviewGo(true));
  tg.addEventListener('click',()=>{ setOpen(pn.hidden); placeMenu(); updateMenu(); });
  pn.addEventListener('click',async e=>{
    const button=e.target.closest('button[data-farm]');
    if(!button||FARM_PREVIEW.busy||REG.busy||P3A.busy||S.mode!=='playing'||P.dead) return;
    const action=button.dataset.farm;
    if(action==='go'){ setOpen(false); await farmPreviewGo(); }
    else if(action==='suzuki'){
      szOrder(SZ.order==='follow'?'wait':'follow');
      if(SZ.order==='follow'){ SZ.region=REG.cur; p3aSzFollow(); }
      saveGame();
    }else if(action==='time'){
      farmPreviewClock(((FARM_PREVIEW.time??-1)+1)%FARM_TIMES.length); saveGame();
    }else if(action==='detail') applyDetail(GFX.detail==='lite'?'std':'lite');
    else if(action==='resetSearch'){
      p3eFarmMerge(p3bState().e3,null,null);
      // 保存時に統合する控えも消しておく。
      prog.chapter2.progress.e3farm={s:0,map:0};
      saveGame();
      setOpen(false);
      toast('調査記録と地図の印を初期化しました。拾った物は残ります');
    }
    updateMenu(); cv.focus();
  });
  setInterval(()=>{
    const on=S.mode==='playing'; tg.hidden=!on;
    if(!on) setOpen(false); else { placeMenu(); updateMenu(); }
  },250);
}
"""
# 時刻と明かりの境目は本編では別なので、試遊版の時刻選択中だけ指定の明かりで比較する。
s = rep(s, 'function f10Phase(t){', """const FARM_PREVIEW={busy:false, time:null, shelter:false};
function f10Phase(t){
  if(t==null&&FARM_PREVIEW.time!==null){
    const [,hour,phase]=FARM_TIMES[FARM_PREVIEW.time], start=farmPreviewTod(hour);
    if(prog.f10.tod>=start&&prog.f10.tod<start+P3B.hour) return phase;
  }""")
s = rep(s, 'function updateEnemies(dt){', 'function updateEnemies(dt){\n  farmPreviewShelter();')
s = rep(s, 'function updateNPCs(dt){', test_code + '\nfunction updateNPCs(dt){')

generated = s.encode('utf8')
with open(out, 'wb') as output:
    output.write(generated)
out_blob = hashlib.sha1(b'blob %d\0' % len(generated) + generated).hexdigest()
print(f'生成：{out}（{len(generated)} バイト、blob {out_blob}）\n元：{where}（blob {blob}）')
