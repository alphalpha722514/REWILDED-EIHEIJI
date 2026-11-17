#!/usr/bin/env python3
"""作業F（救援無線・相談・KEI truck・見送り・山王での初遭遇・仲間に）の試遊版を作る（previews/p2-story/index.html）。docs/p2-story-f.md

本編（作業ブランチの index.html）をコピーして、試遊用の機能だけを加える。イベントの仕組み・台詞（2026-11-17 すべて承認）・KEI truck の仮の値は本編と同じ。
- 保存キーを試遊用に変える（本編のセーブを上書きしない）
- タイトル画面の右上のボタン：
  ・防衛戦を終えたところから（光明寺。勝利の会話 → 救援無線 → 相談 → KEI truck を探す）
  ・KEI truck を直すところから（相談まで済み。部品と燃料は光明寺で拾う。素材は上のボタンで足せる）
  ・KEI truck を直したところから（直して燃料も入れ、見送りも済み。国道416号で運転席に乗った状態。2026-11-17 ユーザー依頼）
  ・上志比の山王の手前から（見送りまで済み・KEI truck で一度来た。東へ少し歩くと初遭遇）
  ・旧セーブを読み込む（防衛戦は済み・作業F の記録なし → 歩いて上志比へ行ける権利を残したまま、光明寺で無線から）
- 遊んでいる間、画面の上にボタン：素材を足す・車の素材を足す（v0.78：車両基地・改修・荷台の施設・燃料に使う木材・石・屑鉄・縄・獣素材・木炭）・KEI truck の前へ・山王の手前へ・回復・進み（いまの記録を出す）
本編を更新したら、このスクリプトを実行し直して作り直す。
使い方：python3 tools/build-p2-story-preview.py
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()


def rep(s, a, b):
    n = s.count(a)
    if n != 1:
        raise SystemExit(f'置き換え位置が {n} か所（1か所のはず）: {a[:60]!r}')
    return s.replace(a, b)


s = src
s = rep(s, "const SAVE_KEY='eiheiji_vs_beasts_v010'", "const SAVE_KEY='eiheiji_vs_beasts_p2story'")
m = re.search(r'<span class="tver">(v[0-9.]+) デモ版', s)
if not m:
    raise SystemExit('版表記が見つからない')
s = s.replace(m.group(0), f'<span class="tver">{m.group(1)} 作業F 物語イベント テスト版（本編とは別に保存）', 1)

BTN = 'style="font-size:12px;padding:6px 10px;min-height:0"'
s = rep(s, '    <div class="tact">',
        '    <div id="p2ftest" style="position:absolute;top:calc(8px + env(safe-area-inset-top,0px));right:calc(8px + env(safe-area-inset-right,0px));'
        'justify-content:flex-end;z-index:5;display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100% - 16px)">'
        f'<button id="btnFRadio" {BTN}>テスト：防衛戦を終えたところから</button>'
        f'<button id="btnFTruck" {BTN}>テスト：KEI truck を直すところから</button>'
        f'<button id="btnFDrive" {BTN}>テスト：KEI truck を直したところから（すぐ運転）</button>'
        f'<button id="btnFSanno" {BTN}>テスト：上志比の山王の手前から</button>'
        f'<button id="btnFLegacy" {BTN}>テスト：旧セーブを読み込む</button></div>\n    <div class="tact">')
test_code = r"""
// ---- 試遊用（試遊版だけ）：作業F の流れを試す ----
function fstBase(){ freshState(); resetWorld(null); hideAllOv(); $('hud').hidden=false; S.mode='playing'; cv.focus();
 prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true; prog.chapter2=chapter2State(null,true); prog.chapter2.progress.openingStarted=true;
 prog.level=4; prog.exp=XP.lv[3]||0; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; P.weapon='spear'; P.dur=WEAPONS.spear.maxDur; prog.arms.spear=P.dur; prog.arms.axeIron=WEAPONS.axeIron.maxDur;
 for(const [slot,id] of Object.entries({head:'forest_head',chest:'forest_chest',legs:'forest_legs',feet:'forest_feet'})){ if(!prog.gear.owned.includes(id)) prog.gear.owned.push(id); prog.gear.equip[slot]=id; }
 f47ApplyVisual(); updHolster(); refreshWeaponMesh(); f7Flush(); inv.onigiri=0; inv.bento=0; foodAdd('onigiri',3); foodAdd('bento',2); return prog.chapter2.progress; }
function fstNearSanno(R){ const a=stfAnchor(); if(!a) return false; const ar=REG.live.arrival, L=Math.hypot(ar.x-a.x,ar.z-a.z)||1, a0=Math.atan2((ar.x-a.x)/L,(ar.z-a.z)/L);
 for(const r of [R,R+6,R-6,R+12]) for(let k=0;k<24;k++){ const ang=a0+(k%2?1:-1)*Math.ceil(k/2)*0.12, x=a.x+Math.sin(ang)*r, z=a.z+Math.cos(ang)*r; if(szWalkable(x,z)&&szFree(x,z,0.6)){ P.x=x; P.z=z; P.facing=Math.atan2(a.x-x,a.z-z); setCam(P.facing); return true; } }
 return false; }
function fstAtTruck(){ const t=trk(); if(t.region!==REG.cur) return false; const tp=truckPos(); P.x=tp.x-Math.cos(TRUCK.a)*2.4; P.z=tp.z+Math.sin(TRUCK.a)*2.4; P.facing=Math.atan2(tp.x-P.x,tp.z-P.z); setCam(P.facing); return true; }
async function fstTest(kind){
 if(kind==='radio'){ fstBase(); ev.kind='chapter2'; ev.ended=false; winEvent(); toast('試遊：会話のあと、救援無線 → 相談'); return; }
 if(kind==='truck'){ const p=fstBase(); Object.assign(p,{defenseComplete:true,defenseRewarded:true,radioHeard:true,departureDecision:true,departureComplete:false}); TRUCK.sync=false;
   banner('試遊：KEI truck を直す','国道416号の東の出口の手前に軽トラックがある。部品は資材倉庫の前と国道416号の脇、燃料は資材倉庫の前。素材（木材・屑鉄・縄・石・竹）は上の「素材を足す」で1台分足せる',8); saveGame(); return; }
 if(kind==='drive'){ const p=fstBase(); Object.assign(p,{defenseComplete:true,defenseRewarded:true,radioHeard:true,departureDecision:true,departureComplete:true});
   const t=trk(); Object.assign(t,{found:true,repaired:true,fueled:true,fuel:TRUCK_CFG.fuel,parts:['p1','p2'],region:'komyoji'}); delete t.x; delete t.z; delete t.a; TRUCK.sync=false;
   truckModel(); truckPos(); fstAtTruck(); truckBoard();
   banner('試遊：KEI truck を直したところ','直して燃料も入れた KEI truck に乗っている。移動の操作で運転、E／行動ボタンで降りる。東の出口（国道416号）へ運転すると上志比へ',8); saveGame(); return; }
 if(kind==='sanno'){ const p=fstBase(); Object.assign(p,{defenseComplete:true,defenseRewarded:true,radioHeard:true,departureDecision:true,departureComplete:true});
   const t=trk(); Object.assign(t,{found:true,repaired:true,fueled:true,parts:['p1','p2'],trips:1}); TRUCK.sync=false;
   const ok=await regionTravel('kamishihi',null,{force:true}); if(!ok){ toast('上志比を読み込めませんでした',true); return; }
   t.region='kamishihi'; t.x=P.x+3; t.z=P.z; t.a=P.facing; TRUCK.sync=false;
   fstNearSanno(56); banner('試遊：山王の手前','山王の駅（東）へ少し歩くと、スズキと変異したサルの場面が始まります',6); saveGame(); return; }
 if(kind==='legacy'){ const p=fstBase(); Object.assign(p,{defenseComplete:true,defenseRewarded:true}); saveGame(); continueGame();
   toast('試遊：旧セーブ（防衛戦は済み・作業F の記録なし）として読み直した。歩いて上志比へ行けるまま、光明寺で無線から'); } }
{ const on0=(id,k)=>{ const b=document.getElementById(id); if(b) b.addEventListener('click',()=>fstTest(k)); }; on0('btnFRadio','radio'); on0('btnFTruck','truck'); on0('btnFDrive','drive'); on0('btnFSanno','sanno'); on0('btnFLegacy','legacy');
  const bar=document.createElement('div'); bar.id='p2fbar'; bar.style.cssText='position:fixed;top:calc(6px + env(safe-area-inset-top,0px));left:50%;transform:translateX(-50%);z-index:30;display:flex;gap:6px;flex-wrap:wrap;justify-content:center;max-width:calc(100% - 16px)';
  const B=(id,t)=>`<button id="${id}" style="font-size:12px;padding:5px 9px;min-height:0;opacity:.88">${t}</button>`;
  bar.innerHTML=B('fsa','素材を足す')+B('fsg','車の素材を足す')+B('fsb','KEI truck の前へ')+B('fse','山王の手前へ')+B('fsc','回復')+B('fsd','進み');
  document.body.appendChild(bar); bar.hidden=true;
  const on=(id,f)=>document.getElementById(id).addEventListener('click',e=>{ e.stopPropagation(); f(); cv.focus(); });
  on('fsa',()=>{ const m=TRUCK_CFG.mats; for(const k in m) inv[k]=(inv[k]|0)+m[k]; toast('試遊：KEI truck の修理に使う素材を1台分足した（'+Object.keys(m).map(k=>(RNAME[k]||k)+m[k]).join('・')+'。数は暫定）'); });
  on('fsg',()=>{ const m={wood:40,stone:20,iron:30,rope:15,hide:10,charcoal:6}; for(const k in m) inv[k]=(inv[k]|0)+m[k]; toast('試遊：KEI truck の仕組みに使う素材を足した（'+Object.keys(m).map(k=>(RNAME[k]||k)+m[k]).join('・')+'）'); });
  on('fsb',async()=>{ if(P.dead||REG.busy||STF.busy||TRUCK.drive) return; const t=trk(); if(!truckShown()){ toast('試遊：KEI truck はまだ出ていない（防衛戦のあと）',true); return; }
    if(t.region!==REG.cur){ const ok=await regionTravel(t.region,null,{force:true}); if(!ok) return; } fstAtTruck(); toast('試遊：KEI truck の前'); });
  on('fse',async()=>{ if(P.dead||REG.busy||STF.busy) return; if(!stfP().defenseComplete){ toast('試遊：先にタイトルのボタンで始めてください',true); return; }
    if(REG.cur!=='kamishihi'){ const ok=await regionTravel('kamishihi',null,{force:true}); if(!ok) return; } fstNearSanno(56); toast('試遊：山王の手前（東へ歩くと初遭遇）'); });
  on('fsc',()=>{ if(!P.dead){ P.hp=P.maxHp; foodAdd('onigiri',2); toast('試遊：体力を戻し、おにぎりを2つ足した'); } });
  on('fsd',()=>{ const p=stfP(), t=trk(), f=v=>v===true?'済':v===false?'まだ':'記録なし';
    const STN={none:'防衛戦の前',radio:'無線を待つ',decide:'相談を待つ',open:'記録なし（今までどおり）',truck:'KEI truck を直す',sendoff:'見送りを待つ',away:'出発した'}, MN={none:'',meet:'・山王で初遭遇を待つ',talk:'・スズキと話すのを待つ',done:'・スズキは仲間'};
    toast(`試遊：${STN[stfStage()]}${MN[stfMeetStage()]}｜無線 ${f(p.radioHeard)}・相談 ${f(p.departureDecision)}・車 ${t.repaired?'直した':'壊れている'}／燃料 ${t.fueled?'入れた':'まだ'}／部品 ${t.parts.length}／上志比へ ${t.trips}回・見送り ${f(p.departureComplete)}・初遭遇 ${f(p.mutantMet)}${p.legacyKamishihiAccess?'・旧セーブの移動権あり':''}`); });
  setInterval(()=>{ bar.hidden=!(S.mode==='playing'); },300); }
"""
s = rep(s, '// ================= NPC =================', test_code + '// ================= NPC =================')

out = os.path.join(ROOT, 'previews', 'p2-story', 'index.html')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf8').write(s)
print('wrote', out, len(s))
