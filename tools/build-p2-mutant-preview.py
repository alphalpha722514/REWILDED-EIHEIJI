#!/usr/bin/env python3
"""変異したサルの試遊版を作る（previews/p2-mutant/index.html）。

本編（index.html）をコピーして、試遊用の機能だけを加える。サルの強さ・動きは本編と同じ（暫定値）。
- 保存キーを試遊用に変える（本編のセーブを上書きしない）
- タイトル画面の右上に「上志比の山王で始める」ボタン（防衛戦を終えた状態・防具と槍。着いたら初遭遇のサルが来る）
- 遊んでいる間、画面の上に「サルを呼ぶ（初遭遇：逃げ去る）」「サルを呼ぶ（通常：倒せる）」ボタン
本編を更新したら、このスクリプトを実行し直して作り直す。
使い方：python3 tools/build-p2-mutant-preview.py
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
s = rep(s, "const SAVE_KEY='eiheiji_vs_beasts_v010'", "const SAVE_KEY='eiheiji_vs_beasts_p2mutant'")
m = re.search(r'<span class="tver">(v[0-9.]+) デモ版', s)
if not m:
    raise SystemExit('版表記が見つからない')
s = s.replace(m.group(0), f'<span class="tver">{m.group(1)} 変異したサル テスト版（本編とは別に保存）', 1)

BTN = 'style="font-size:12px;padding:6px 10px;min-height:0"'
s = rep(s, '    <div class="tact">',
        '    <div id="p2test" style="position:absolute;top:calc(8px + env(safe-area-inset-top,0px));right:calc(8px + env(safe-area-inset-right,0px));'
        'justify-content:flex-end;z-index:5;display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100% - 16px)">'
        f'<button id="btnP2Start" {BTN}>テスト：上志比の山王で始める</button></div>\n    <div class="tact">')
test_code = r"""
// ---- 試遊用（試遊版だけ）：変異したサルを試す ----
async function p2TestStart(){
 freshState(); resetWorld(null); hideAllOv(); $('hud').hidden=false; S.mode='playing'; cv.focus();
 prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true; prog.chapter2=chapter2State(null,true);
 prog.chapter2.progress.openingStarted=true; prog.chapter2.progress.defenseComplete=true;
 prog.level=4; prog.exp=XP.lv[3]||0; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; P.weapon='spear'; P.dur=WEAPONS.spear.maxDur; prog.arms.spear=P.dur;
 for(const [slot,id] of Object.entries({head:'forest_head',chest:'forest_chest',legs:'forest_legs',feet:'forest_feet'})){ if(!prog.gear.owned.includes(id)) prog.gear.owned.push(id); prog.gear.equip[slot]=id; }
 f47ApplyVisual(); updHolster(); refreshWeaponMesh();
 const ok=await regionTravel('kamishihi',null,{force:true}); if(!ok){ toast('上志比を読み込めませんでした',true); return; }
 const st=(window.KAMISHIHI_MAP.pts.station||[]).find(s=>s[2]==='山王'); if(st){ P.x=st[0]+14; P.z=st[1]+6; P.facing=0; setCam(0); }
 banner('試遊：変異したサル','少しすると変異したサルが来ます（初遭遇：体力が減ると逃げ去る）。上のボタンでも呼べます',5);
 setTimeout(()=>{ if(S.mode==='playing') p2Spawn(true); },2500); saveGame(); }
async function p2Spawn(fleeOnly){ const a=P.facing||0, x=P.x+Math.sin(a)*11, z=P.z+Math.cos(a)*11;
 const e=await spawnMutant(x,z,{fleeOnly,aggro:true}); if(e){ setState(e,'alert'); toast(fleeOnly?'変異したサル（初遭遇：逃げ去る）':'変異したサル（通常：倒せる）'); } }
{ const b=document.getElementById('btnP2Start'); if(b) b.addEventListener('click',()=>p2TestStart());
  const bar=document.createElement('div'); bar.id='p2bar'; bar.style.cssText='position:fixed;top:calc(6px + env(safe-area-inset-top,0px));left:50%;transform:translateX(-50%);z-index:30;display:flex;gap:6px;flex-wrap:wrap;justify-content:center;max-width:calc(100% - 16px)';
  bar.innerHTML='<button id="p2a" style="font-size:12px;padding:5px 9px;min-height:0;opacity:.85">サルを呼ぶ（初遭遇：逃げ去る）</button><button id="p2b" style="font-size:12px;padding:5px 9px;min-height:0;opacity:.85">サルを呼ぶ（通常：倒せる）</button>';
  document.body.appendChild(bar); bar.hidden=true;
  document.getElementById('p2a').addEventListener('click',e=>{ e.stopPropagation(); p2Spawn(true); cv.focus(); });
  document.getElementById('p2b').addEventListener('click',e=>{ e.stopPropagation(); p2Spawn(false); cv.focus(); });
  setInterval(()=>{ bar.hidden=!(S.mode==='playing'); },300); }
"""
s = rep(s, '// ================= NPC =================', test_code + '// ================= NPC =================')

out = os.path.join(ROOT, 'previews', 'p2-mutant', 'index.html')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf8').write(s)
print('wrote', out, len(s))
