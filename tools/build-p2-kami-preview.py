#!/usr/bin/env python3
"""上志比の獣・採集・伐採の試遊版を作る（previews/p2-kami/index.html）。開発用テストモードはこの試遊版だけ（2026-11-14 ユーザー決定）。

本編（index.html）をコピーして、試遊用の機能だけを加える。獣の数・採集の量は本編と同じ（暫定値）。
- 保存キーを試遊用に変える（本編のセーブを上書きしない。テストの設定も本編のセーブに混ざらない）
- タイトル画面の右上に「上志比で始める」ボタン（防衛戦を終えた状態・防具と鉄の斧・槍・石の槌）
- 遊んでいる間、画面の上にボタン：
  ・変異したサルを解禁（初遭遇の前でも、町の群れに変異したサルが加わる。この遊びの間だけ。保存しない）
  ・獣と採集の場所を地図に出す（G の全体地図に点で出す）
  ・時間を5分進める（倒した獣・取った物が戻るのを確かめる）
  ・回復・食料を足す
本編を更新したら、このスクリプトを実行し直して作り直す。
使い方：python3 tools/build-p2-kami-preview.py
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
s = rep(s, "const SAVE_KEY='eiheiji_vs_beasts_v010'", "const SAVE_KEY='eiheiji_vs_beasts_p2kami'")
m = re.search(r'<span class="tver">(v[0-9.]+) デモ版', s)
if not m:
    raise SystemExit('版表記が見つからない')
s = s.replace(m.group(0), f'<span class="tver">{m.group(1)} 上志比の獣・採集 テスト版（本編とは別に保存）', 1)

BTN = 'style="font-size:12px;padding:6px 10px;min-height:0"'
s = rep(s, '    <div class="tact">',
        '    <div id="p2ktest" style="position:absolute;top:calc(8px + env(safe-area-inset-top,0px));right:calc(8px + env(safe-area-inset-right,0px));'
        'justify-content:flex-end;z-index:5;display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100% - 16px)">'
        f'<button id="btnKStart" {BTN}>テスト：上志比で始める</button></div>\n    <div class="tact">')
test_code = r"""
// ---- 試遊用（試遊版だけ）：上志比の獣・採集・伐採を試す（開発用テストモード） ----
async function kTestStart(){
 freshState(); resetWorld(null); hideAllOv(); $('hud').hidden=false; S.mode='playing'; cv.focus();
 prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true; prog.chapter2=chapter2State(null,true);
 prog.chapter2.progress.openingStarted=true; prog.chapter2.progress.defenseComplete=true;
 prog.level=4; prog.exp=XP.lv[3]||0; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; P.weapon='spear'; P.dur=WEAPONS.spear.maxDur; prog.arms.spear=P.dur; prog.arms.axeIron=WEAPONS.axeIron.maxDur; toolGain('hammerStone');
 for(const [slot,id] of Object.entries({head:'forest_head',chest:'forest_chest',legs:'forest_legs',feet:'forest_feet'})){ if(!prog.gear.owned.includes(id)) prog.gear.owned.push(id); prog.gear.equip[slot]=id; }
 f47ApplyVisual(); updHolster(); refreshWeaponMesh(); f7Flush(); inv.onigiri=0; inv.bento=0; foodAdd('onigiri',3); foodAdd('bento',2);
 const ok=await regionTravel('kamishihi',null,{force:true}); if(!ok){ toast('上志比を読み込めませんでした',true); return; }
 banner('試遊：上志比の獣・採集','獣・群れ・採集場所を置きました（数は暫定）。上のボタンで、変異したサルの解禁・場所の表示（G の地図）・時間の早送りができます',6); saveGame(); }
{ const b=document.getElementById('btnKStart'); if(b) b.addEventListener('click',()=>kTestStart());
  const bar=document.createElement('div'); bar.id='p2kbar'; bar.style.cssText='position:fixed;top:calc(6px + env(safe-area-inset-top,0px));left:50%;transform:translateX(-50%);z-index:30;display:flex;gap:6px;flex-wrap:wrap;justify-content:center;max-width:calc(100% - 16px)';
  const B=(id,t)=>`<button id="${id}" style="font-size:12px;padding:5px 9px;min-height:0;opacity:.85">${t}</button>`;
  bar.innerHTML=B('kta','変異したサルを解禁：切')+B('ktb','場所を地図に出す：切')+B('ktc','時間を5分進める')+B('ktd','回復・食料を足す');
  document.body.appendChild(bar); bar.hidden=true;
  const sync=()=>{ document.getElementById('kta').textContent='変異したサルを解禁：'+(KW_TEST.mutant?'入':'切'); document.getElementById('ktb').textContent='場所を地図に出す：'+(KW_TEST.marks?'入':'切'); };
  document.getElementById('kta').addEventListener('click',e=>{ e.stopPropagation(); KW_TEST.mutant=!KW_TEST.mutant; sync(); toast(KW_TEST.mutant?'試遊：変異したサルを解禁（町の群れに加わる。保存しない）':'試遊：解禁を戻した（出ている変異したサルはそのまま）'); cv.focus(); });
  document.getElementById('ktb').addEventListener('click',e=>{ e.stopPropagation(); KW_TEST.marks=!KW_TEST.marks; sync(); toast(KW_TEST.marks?'試遊：G の地図に、獣（茶・橙・黄・白・赤）・群れ（桃）・採集（水色・灰）を出す':'試遊：地図の点を消した'); cv.focus(); });
  document.getElementById('ktc').addEventListener('click',e=>{ e.stopPropagation(); stats.time+=300; toast('試遊：遊んだ時間を5分進めた（倒した獣・取った物の戻りを確かめる）'); cv.focus(); });
  document.getElementById('ktd').addEventListener('click',e=>{ e.stopPropagation(); if(!P.dead){ P.hp=P.maxHp; foodAdd('onigiri',2); toast('試遊：体力を戻し、おにぎりを2つ足した'); } cv.focus(); });
  setInterval(()=>{ bar.hidden=!(S.mode==='playing'); },300); }
"""
s = rep(s, '// ================= NPC =================', test_code + '// ================= NPC =================')

out = os.path.join(ROOT, 'previews', 'p2-kami', 'index.html')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf8').write(s)
print('wrote', out, len(s))
