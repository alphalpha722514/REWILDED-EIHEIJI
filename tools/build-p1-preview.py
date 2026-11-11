#!/usr/bin/env python3
"""P1 調整案の試遊版を作る（previews/p1-balance/index.html）。

本編（index.html）は変えない。本編をコピーして、承認待ちの調整案（暫定）と試遊用の機能だけを加える。
- 保存キーを試遊用に変える（本編のセーブを上書きしない。同じサイトなので保存場所を共有するため）
- 猿は、無傷の柵がある門で、よじ登るために止まる（第2章の防衛戦だけ）
- 火の見やぐらの耐久 300→420、第2章の敵の攻撃倍率 1.6→1.4
- 初回クリア報酬（木材6・藁6・おにぎり2）。2回目以降は報酬なし
- タイトル画面に「A／B／C の準備で始める」ボタン

使い方：python3 tools/build-p1-preview.py
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, 'index.html'), encoding='utf8').read()


def rep(s, a, b):
    n = s.count(a)
    if n != 1:
        raise SystemExit(f'置き換え位置が {n} か所（1か所のはず）: {a[:60]!r}')
    return s.replace(a, b)


s = src
# 1. 試遊版は別の保存キー（本編のセーブを守る）
s = rep(s, "const SAVE_KEY='eiheiji_vs_beasts_v010'", "const SAVE_KEY='eiheiji_vs_beasts_p1test'")
s = rep(s, '<span class="tver">v0.54.1 デモ版　第二章・光明寺防衛戦',
        '<span class="tver">P1 調整テスト版（本編とは別に保存）　第二章・光明寺防衛戦')

# 2. 調整値（暫定）
s = rep(s, "const C2_DEFENSE={warning:30,coreHp:300,rest:18,coreDamage:14,coreInterval:2.0,hpMul:2.0,damageMul:1.6,",
        "const C2_DEFENSE={warning:30,coreHp:420,rest:18,coreDamage:14,coreInterval:2.0,hpMul:2.0,damageMul:1.4,climb:4,")

# 3. 猿は無傷の柵をよじ登るために止まる（第2章の防衛戦だけ）
s = rep(s, "if(e.rphase==='approach'){ if(dist(e.x,e.z,g.out.x,g.out.z)<2) e.rphase='gate'; else return {kind:'point',x:g.out.x,z:g.out.z}; }",
        "if(e.rphase==='approach'){ if(dist(e.x,e.z,g.out.x,g.out.z)<2){ e.rphase='gate'; if(ev.kind==='chapter2'&&g.fence.type&&!g.fence.broken){ e.climbT=C2_DEFENSE.climb||0; if(e.climbT>0) floatText(e.x,2.1,e.z,'柵をよじ登っている','#f0dca0'); } } else return {kind:'point',x:g.out.x,z:g.out.z}; }")
s = rep(s, "      if(e.aggro){ setState(e,'kite'); e.atkT=1.2; break; }\n      if(t.kind==='flee'){ steer(e,t.x,t.z,ET.monkey.speed,dt);",
        "      if(e.aggro){ setState(e,'kite'); e.atkT=1.2; break; }\n      if(e.climbT>0){ e.climbT-=dt; e.spd=0; break; }\n      if(t.kind==='flee'){ steer(e,t.x,t.z,ET.monkey.speed,dt);")

# 4. 初回クリア報酬（暫定）。すでに防衛完了の記録があるセーブには出さない
s = rep(s, "    const c=syncChapter2();c.progress.openingStarted=true;c.progress.defenseComplete=true;c.currentChapter=2;\n    banner('光明寺防衛戦　完了','町で装備と物資を整えられます。上志比への出発は次の更新で追加予定です。',5);",
        "    const c=syncChapter2();const first=!c.progress.defenseComplete&&!c.progress.defenseRewarded;c.progress.openingStarted=true;c.progress.defenseComplete=true;c.currentChapter=2;\n"
        "    if(first){ c.progress.defenseRewarded=true; inv.wood+=6; inv.straw+=6; foodAdd('onigiri',2); banner('光明寺防衛戦　完了','住民からの礼：木材6・藁6・おにぎり2。上志比への出発は次の更新で追加予定です。',5); }\n"
        "    else banner('光明寺防衛戦　完了（再挑戦）','戦績を更新しました。報酬は初回のみです。',5);")

# 5. 試遊用：A／B／C の準備で始めるボタン
BTN = 'style="font-size:12px;padding:6px 10px;min-height:0"'
s = rep(s, '    <div class="tact">',
        '    <div id="p1test" style="position:absolute;top:calc(8px + env(safe-area-inset-top,0px));right:calc(8px + env(safe-area-inset-right,0px));justify-content:flex-end;'
        'z-index:5;display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100% - 16px)">'
        f'<button id="btnP1A" {BTN}>テスト：A 準備なし</button><button id="btnP1B" {BTN}>テスト：B 一部準備</button>'
        f'<button id="btnP1C" {BTN}>テスト：C 十分な準備</button></div>\n    <div class="tact">')
test_code = r"""
// ---- P1 試遊用（試遊版だけ）：A／B／C の準備を整えて、源さんの横から始める ----
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
 banner('P1 試遊：準備'+k,'源さんに話しかけて「第二章の防衛戦を始める」を選んでください（本編とは別に保存）',5); saveGame(); }
for(const k of ['A','B','C']){ const b=document.getElementById('btnP1'+k); if(b) b.addEventListener('click',()=>p1TestStart(k)); }
"""
s = rep(s, '// ================= NPC =================', test_code + '// ================= NPC =================')

out = os.path.join(ROOT, 'previews', 'p1-balance', 'index.html')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf8').write(s)
print('wrote', out, len(s))
