#!/usr/bin/env python3
"""防衛戦の試遊版を作る（previews/p1-balance/index.html）。

本編（index.html）をコピーして、試遊用の機能だけを加える。ゲームの数値・動きは本編と同じ。
- 保存キーを試遊用に変える（本編のセーブを上書きしない。同じサイトなので保存場所を共有するため）
- タイトル画面の右上に「A／B／C の準備で始める」ボタン（P1 の3条件。docs/p1-balance-report.md）

本編を更新したら、このスクリプトを実行し直して試遊版を作り直す。
使い方：python3 tools/build-p1-preview.py
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
s = rep(s, "const SAVE_KEY='eiheiji_vs_beasts_v010'", "const SAVE_KEY='eiheiji_vs_beasts_p1test'")
m = re.search(r'<span class="tver">(v[0-9.]+) デモ版', s)
if not m:
    raise SystemExit('版表記が見つからない')
s = s.replace(m.group(0), f'<span class="tver">{m.group(1)} 防衛戦テスト版（本編とは別に保存）', 1)

BTN = 'style="font-size:12px;padding:6px 10px;min-height:0"'
s = rep(s, '    <div class="tact">',
        '    <div id="p1test" style="position:absolute;top:calc(8px + env(safe-area-inset-top,0px));right:calc(8px + env(safe-area-inset-right,0px));'
        'justify-content:flex-end;z-index:5;display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100% - 16px)">'
        f'<button id="btnP1A" {BTN}>テスト：A 準備なし</button><button id="btnP1B" {BTN}>テスト：B 一部準備</button>'
        f'<button id="btnP1C" {BTN}>テスト：C 十分な準備</button></div>\n    <div class="tact">')
test_code = r"""
// ---- 試遊用（試遊版だけ）：A／B／C の準備を整えて、源さんの横から始める ----
const P1TEST={
 A:{level:2,weapon:'nata1',armor:{},gates:[null,null,null],traps:[],food:{onigiri:0,bento:0},wood:0},
 B:{level:3,weapon:'nata2',armor:{head:'basic_head',chest:'basic_chest'},gates:['wood','stake',null],traps:[[0,'pit'],[2,'snare']],food:{onigiri:3,bento:0},wood:4},
 C:{level:4,weapon:'spear',armor:{head:'forest_head',chest:'forest_chest',legs:'forest_legs',feet:'forest_feet'},gates:['stake','stake','wood'],traps:[[0,'pit'],[1,'snare'],[2,'pit'],[4,'pit']],food:{onigiri:3,bento:2},wood:10}};
function p1TestStart(k){ const c=P1TEST[k];
 freshState(); resetWorld(null); hideAllOv(); $('hud').hidden=false; S.mode='playing'; cv.focus();
 prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true; prog.chapter2=chapter2State(null,true);
 prog.level=c.level; prog.exp=XP.lv[c.level-1]||0; P.maxHp=f31MaxHp(c.level); P.hp=P.maxHp;
 P.weapon=c.weapon; P.dur=WEAPONS[c.weapon].maxDur; prog.arms[c.weapon]=P.dur;
 for(const [slot,id] of Object.entries(c.armor)){ if(!prog.gear.owned.includes(id)) prog.gear.owned.push(id); prog.gear.equip[slot]=id; }
 f47ApplyVisual(); updHolster(); refreshWeaponMesh();
 f7Flush(); inv.onigiri=0; inv.bento=0; if(c.food.onigiri) foodAdd('onigiri',c.food.onigiri); if(c.food.bento) foodAdd('bento',c.food.bento); inv.wood=c.wood;
 GAPS.forEach((g,i)=>setFence(g,c.gates[i]||null)); for(const [i,kind] of c.traps) setTrap(traps[i],'armed',kind);
 P.x=npcGen.x+1.2; P.z=npcGen.z+1.2;
 banner('試遊：準備'+k,'源さんに話しかけて「第二章の防衛戦を始める」を選んでください（本編とは別に保存）',5); saveGame(); }
for(const k of ['A','B','C']){ const b=document.getElementById('btnP1'+k); if(b) b.addEventListener('click',()=>p1TestStart(k)); }
"""
s = rep(s, '// ================= NPC =================', test_code + '// ================= NPC =================')

out = os.path.join(ROOT, 'previews', 'p1-balance', 'index.html')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf8').write(s)
print('wrote', out, len(s))
