#!/usr/bin/env python3
"""スズキの仲間 AI（P2 作業E）の試遊版を作る（previews/p2-suzuki/index.html）。

本編（index.html）をコピーして、試遊用の機能だけを加える。スズキの動き・数は本編と同じ（暫定値）。
本編では、作業F の初遭遇で仲間になるまでスズキは出ない。呼び出すボタンは、この試遊版だけにある（2026-11-15 指示書 Q59）。
- 保存キーを試遊用に変える（本編のセーブを上書きしない。呼び出した状態も本編のセーブに混ざらない）
- タイトル画面の右上に「スズキと始める（光明寺）」「スズキと始める（上志比）」ボタン（防衛戦を終えた状態・防具と槍）
- 遊んでいる間、画面の上にボタン：
  ・スズキを呼ぶ（仲間にして、主人公のすぐ後ろへ）
  ・上志比へ／光明寺へ（地域を移る。ついて来ているスズキも移る）
  ・回復・食料を足す
  ・スズキの今の状態を出す（指示・いる地域・体力・主人公との距離）
  ・v0.71：獣を近くに出す（押すたびに イノシシ → サル → クマ → 変異したサル。主人公の前 10m に、主人公に気づいた状態で）
  ・v0.71：スズキの体力を50にする（体力が少ないときの戦い方を見る）
  ・v0.72：スズキを倒れさせる（助け起こす長押しを試す）
本編を更新したら、このスクリプトを実行し直して作り直す。
使い方：python3 tools/build-p2-suzuki-preview.py
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
s = rep(s, "const SAVE_KEY='eiheiji_vs_beasts_v010'", "const SAVE_KEY='eiheiji_vs_beasts_p2suzuki'")
m = re.search(r'<span class="tver">(v[0-9.]+) デモ版', s)
if not m:
    raise SystemExit('版表記が見つからない')
s = s.replace(m.group(0), f'<span class="tver">{m.group(1)} スズキの仲間 AI テスト版（本編とは別に保存）', 1)

BTN = 'style="font-size:12px;padding:6px 10px;min-height:0"'
s = rep(s, '    <div class="tact">',
        '    <div id="p2stest" style="position:absolute;top:calc(8px + env(safe-area-inset-top,0px));right:calc(8px + env(safe-area-inset-right,0px));'
        'justify-content:flex-end;z-index:5;display:flex;flex-wrap:wrap;gap:6px;max-width:calc(100% - 16px)">'
        f'<button id="btnSStartK" {BTN}>テスト：スズキと始める（光明寺）</button>'
        f'<button id="btnSStartU" {BTN}>テスト：スズキと始める（上志比）</button></div>\n    <div class="tact">')
test_code = r"""
// ---- 試遊用（試遊版だけ）：スズキの仲間 AI を試す ----
async function sTestStart(where){
 freshState(); resetWorld(null); hideAllOv(); $('hud').hidden=false; S.mode='playing'; cv.focus();
 prog.bossDefeated=true; prog.stage='cleared'; prog.unlockTrap=true; prog.unlockBoss=true; prog.introSeen=true; prog.chapter2=chapter2State(null,true);
 prog.chapter2.progress.openingStarted=true; prog.chapter2.progress.defenseComplete=true;
 prog.level=4; prog.exp=XP.lv[3]||0; P.maxHp=f31MaxHp(4); P.hp=P.maxHp; P.weapon='spear'; P.dur=WEAPONS.spear.maxDur; prog.arms.spear=P.dur; prog.arms.axeIron=WEAPONS.axeIron.maxDur;
 for(const [slot,id] of Object.entries({head:'forest_head',chest:'forest_chest',legs:'forest_legs',feet:'forest_feet'})){ if(!prog.gear.owned.includes(id)) prog.gear.owned.push(id); prog.gear.equip[slot]=id; }
 f47ApplyVisual(); updHolster(); refreshWeaponMesh(); f7Flush(); inv.onigiri=0; inv.bento=0; foodAdd('onigiri',3); foodAdd('bento',2);
 if(where==='kamishihi'){ const ok=await regionTravel('kamishihi',null,{force:true}); if(!ok){ toast('上志比を読み込めませんでした',true); return; } }
 szJoin();
 banner('試遊：スズキの仲間 AI','スズキが後ろからついて来ます。近くで E（行動ボタン）を押すと指示を選べます。上のボタンで呼ぶ・地域を移る',6); saveGame(); }
{ const b1=document.getElementById('btnSStartK'); if(b1) b1.addEventListener('click',()=>sTestStart('komyoji'));
  const b2=document.getElementById('btnSStartU'); if(b2) b2.addEventListener('click',()=>sTestStart('kamishihi'));
  const bar=document.createElement('div'); bar.id='p2sbar'; bar.style.cssText='position:fixed;top:calc(6px + env(safe-area-inset-top,0px));left:50%;transform:translateX(-50%);z-index:30;display:flex;gap:6px;flex-wrap:wrap;justify-content:center;max-width:calc(100% - 16px)';
  const B=(id,t)=>`<button id="${id}" style="font-size:12px;padding:5px 9px;min-height:0;opacity:.85">${t}</button>`;
  bar.innerHTML=B('sta','スズキを呼ぶ')+B('stb','上志比へ／光明寺へ')+B('stc','回復・食料を足す')+B('std','スズキの状態')+B('ste','獣を近くに出す')+B('stf','スズキの体力を50に')+B('stg','スズキを倒れさせる');
  document.body.appendChild(bar); bar.hidden=true;
  const on=(id,f)=>document.getElementById(id).addEventListener('click',e=>{ e.stopPropagation(); f(); cv.focus(); });
  on('sta',()=>{ if(P.dead) return; if(!SZ.joined||SZ.region!==REG.cur){ szJoin(); } else { SZ.down=false; SZ.hp=Math.max(SZ.hp,1); szCombatReset(); szPlaceBehind(); } SZ.order='follow'; toast('試遊：スズキを呼んだ（ついて来る）'); });
  on('stb',async()=>{ if(P.dead||REG.busy) return; const to=REG.cur==='komyoji'?'kamishihi':'komyoji'; await regionTravel(to,null,{force:true}); });
  on('stc',()=>{ if(!P.dead){ P.hp=P.maxHp; foodAdd('onigiri',2); toast('試遊：体力を戻し、おにぎりを2つ足した'); } });
  on('std',()=>{ const O={follow:'ついて来る',wait:'ここで待つ',base:'拠点で過ごす'}; toast(SZ.joined?`スズキ：${O[SZ.order]}・${regionName(SZ.region)}・体力 ${Math.ceil(SZ.hp)}/${SZ.maxHp}${SZ.region===REG.cur?'・主人公から '+dist(SZ.x,SZ.z,P.x,P.z).toFixed(1)+'m':''}`:'スズキはまだ仲間でない（「スズキを呼ぶ」で仲間にする）'); });
  { const TYPES=['boar','monkey','bear','mutant']; let ti=0;
    on('ste',async()=>{ if(P.dead) return; const type=TYPES[ti++%TYPES.length], f=P.facing, x=P.x+Math.sin(f)*10, z=P.z+Math.cos(f)*10;
      let e=enemies.find(o=>!o.removed&&o.state!=='dead'&&o.type===type&&o.mode==='field'&&!o.kf);
      if(!e&&type==='mutant'){ try{ e=await spawnMutant(x,z); }catch(err){ e=null; } }
      if(!e){ toast('試遊：'+(ET[type]?ET[type].name:type)+'が近くにいない（別の地域で試す）',true); return; }
      e.x=x; e.z=z; e.home={x,z}; e.hp=e.maxHp; e.rot=Math.atan2(P.x-x,P.z-z); setState(e,type==='monkey'||type==='mutant'?'kite':'chase'); e.hitP=S.time; toast('試遊：'+ET[type].name+'を主人公の前 10m に出した'); }); }
  on('stf',()=>{ if(SZ.joined&&!SZ.down){ SZ.hp=50; toast('試遊：スズキの体力を50にした（54以下は敵から離れて戦う）'); } });
  on('stg',()=>{ if(szHere()&&!SZ.down){ szDown(); } });
  setInterval(()=>{ bar.hidden=!(S.mode==='playing'); },300); }
"""
s = rep(s, '// ================= NPC =================', test_code + '// ================= NPC =================')

out = os.path.join(ROOT, 'previews', 'p2-suzuki', 'index.html')
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, 'w', encoding='utf8').write(s)
print('wrote', out, len(s))
