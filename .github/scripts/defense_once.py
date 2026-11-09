#!/usr/bin/env python3
# One-time, base-checked patch for REWILDED EIHEIJI. Runs on checked-out main only.
import pathlib,re,subprocess,tempfile,json
f=pathlib.Path("index.html")
original=f.read_text(encoding="utf-8")
s=original
changes=[]
def R(a,b,name):
    global s
    count=s.count(a)
    if count!=1: raise RuntimeError("%s: expected one anchor, found %d: %s"%(name,count,a[:70]))
    s=s.replace(a,b,1)
    changes.append(name)
def B(a,b,replacement,name):
    global s
    i=s.find(a)
    if i<0 or s.find(a,i+1)>=0: raise RuntimeError("ambiguous start "+name)
    j=s.find(b,i+len(a))
    if j<0: raise RuntimeError("missing end "+name)
    s=s[:i]+replacement+s[j:]
    changes.append(name)
R("// ================= レンダラー =================",
  "// 追加見張り台の固定予定地\nconst SCOUT={x:BX+16,z:BZ,model:null,col:null};\n\n// ================= レンダラー =================","site")
R("g.position.set(x,0,z); const m=bake(g); world.add(m); addBox(x,z,2.2,2.2,'tower',{h:7}); regFade(m,x,z,1.8,7);\n}",
  "g.position.set(x,0,z); const m=bake(g); world.add(m); const col=addBox(x,z,2.2,2.2,'tower',{h:7}); regFade(m,x,z,1.8,7); return {m,col};\n}","tower visual reuse")
R("fenceKit:0,trapKit:0,stakeKit:0,onigiri:1","fenceKit:0,trapKit:0,stakeKit:0,spikeKit:0,pitKit:0,onigiri:1","kit inventory")
R("bossDefeated:false,prepT:150,gatherT:0,introSeen:false",
  "bossDefeated:false,scoutTower:false,scoutWarned:false,scoutRaidWarned:false,prepT:150,gatherT:0,introSeen:false","tower progress")
R("let p=mv.counter?e.poiseMax*0.5:mv.poise*(WPOISE[info.weapon]||1)*f31PoiseMul(info.weapon);",
  "let p=info.source==='spike'?mv.poise:(mv.counter?e.poiseMax*0.5:mv.poise*(WPOISE[info.weapon]||1)*f31PoiseMul(info.weapon));","spike poise")
R("const stake=f.type==='stake'; const worn=!f.broken&&f.hp/f.max<0.4;",
  "const stake=f.type==='stake',spike=f.type==='spike'; const worn=!f.broken&&f.hp/f.max<0.4;","spike flag")
R("    // くぐり戸\n    v.add(J(mesh(rbox",
  """    if(spike){
      for(let i=0;i<9;i++){ const o=-L/2+0.2+i*(L-0.4)/8,out=gp.horiz?1:(gp.c.x<BX?-1:1);
        const sp=mesh(G.cone6,mat(0x493824),...H(o,1.0,0.48*out),0.14,0.95,0.14);
        if(gp.horiz)sp.rotation.x=-0.98;else sp.rotation.z=-out*0.98;v.add(J(sp,0.10)); }
    }
    // くぐり戸
    v.add(J(mesh(rbox""","spike geometry")
R("f.max=type==='stake'?260:120;","f.max=type==='stake'?260:type==='spike'?90:120;","spike durability")
R("const traps=TRAP_SLOTS.map((s,i)=>Object.assign({i,state:'empty'},s));",
  """function spikeFenceContact(gp,e){
  if(!gp||!e||e.state==='dead'||gp.fence.type!=='spike'||gp.fence.broken)return;
  const cd=e.spikeCd||(e.spikeCd={});if(S.time-(cd[gp.id]??-100)<1)return;
  cd[gp.id]=S.time;const dir=Math.atan2(e.x-gp.c.x,e.z-gp.c.z);
  damageEnemy(e,6,'trap',dir,{source:'spike',mv:{poise:12}});
}
const traps=TRAP_SLOTS.map((s,i)=>Object.assign({i,state:'empty',type:'snare'},s));""","spike hit")
R("  const armed=t.state==='armed'; const v=new THREE.Group();\n  v.add(J(mesh(G.cyl8",
  """  const armed=t.state==='armed'; const v=new THREE.Group();
  if(t.type==='pit'){
    v.add(mesh(G.circ,bmat(armed?0x362b20:0x201b16,0.92),0,0.035,0,1.12,1,1.12));
    for(let i=0;i<10;i++){const a=i*TAU/10,x=Math.sin(a),z=Math.cos(a);
      const p=mesh(G.box,mat(0x735536),x*1.02,0.08,z*1.02,0.46,0.11,0.16);p.rotation.y=a;v.add(p);}
    if(armed)for(let i=-3;i<=3;i++){const b=mesh(G.cyl8,mat(0x8b744f),i*0.28,0.09,0,0.045,2.0,0.045);b.rotation.x=Math.PI/2;v.add(b);}
    g.add(bake(v));return;
  }
  v.add(J(mesh(G.cyl8""","pit geometry")
R("function setTrap(t,state){ t.state=state; trapVisual(t); }\n\n// ================= 敵 =================",
  """function setTrap(t,state,type){if(type==='pit'||type==='snare')t.type=type;t.state=state;trapVisual(t);}
function buildScoutSite(){
  const {x,z}=SCOUT;
  world.add(mesh(G.circ,bmat(0xc5ad7d,0.45),x,groundH(x,z)+0.03,z,1.55,1,1.55));
  const tower=watchtower(x,z);SCOUT.model=tower.m;SCOUT.col=tower.col;SCOUT.model.visible=false;SCOUT.col.active=false;
}
function scoutVisual(){if(!SCOUT.model)return;SCOUT.model.visible=!!prog.scoutTower;SCOUT.col.active=!!prog.scoutTower;}

// ================= 敵 =================""","trap and tower visual")
R("  return resolve(e,true,e.type==='monkey');\n}\nfunction steer(",
  "  const hit=resolve(e,true,e.type==='monkey');\n  if(hit&&hit.tag==='fence'&&e.type!=='monkey')spikeFenceContact(hit.ref,e);\n  return hit;\n}\nfunction steer(","fence contact")
R("if(hit.tag==='fence'){ damageFence(hit.ref,dmgF); setState(e,'stun'); e.stunT=stunT; sfx('stun'); return true; }",
  "if(hit.tag==='fence'){ spikeFenceContact(hit.ref,e); damageFence(hit.ref,dmgF); if(e.state==='dead'||e.state==='broken')return true; setState(e,'stun'); e.stunT=stunT; sfx('stun'); return true; }","charge spikes")
R("if(t&&t.kind==='fence'&&tDist(e,t)<range+0.3) damageFence(t.ref,dmgF);",
  "if(t&&t.kind==='fence'&&tDist(e,t)<range+0.3){ spikeFenceContact(t.ref,e); damageFence(t.ref,dmgF); }","bear spikes")
R("'stomp','trapped'];","'stomp','trapped','stun'];","lod stun")
R("function triggerTrap(t,e){\n  setTrap(t,'sprung');",
  """function triggerTrap(t,e){
  if(t.type==='pit'){
    if(!['boar','bear','boss'].includes(e.type))return;
    setTrap(t,'sprung');sfx('trap');f10Noise(t.x,t.z,12,'impact');
    e.ind.visible=false;hideSector(e);damageEnemy(e,e.type==='boss'?18:28,'trap',0);
    if(e.state!=='dead'){setState(e,e.type==='boss'?'trapped':'stun');e.stunT=e.type==='boss'?2.5:5;e.spd=0;}
    floatText(t.x,2.2,t.z,'落とし穴！','#f0c34a',true);
    if(e.type==='boss')toast('ヌシが落とし穴に落ちた！ すぐに抜け出しそうだ');
    return;
  }
  setTrap(t,'sprung');""","pit trigger")
R("function f9GenInfo(){ const L=[], st=prog.stage, si=STAGES.indexOf(st); let gate=null;",
  """function scoutDirectionLine(){
  if(!prog.scoutTower)return '';
  let names=[];
  if(ev.kind&&Array.isArray(ev.waves)&&ev.waves.length){
    const wave=ev.waves[Math.min(ev.waveIdx,ev.waves.length-1)]||ev.waves[0];
    names=[...new Set(wave.map(w=>w[1]))].map(i=>GAPS[i]&&GAPS[i].name).filter(Boolean);
  }else if(prog.stage==='invasionPrep')names=GAPS.map(g=>g.name);
  else if(prog.stage==='buildFence')names=[GAPS[0].name];
  return names.length?'見張り台から見ると、群れは'+names.join('・')+'の方向から来るで。':'';
}
function f9GenInfo(){ const L=[], st=prog.stage, si=STAGES.indexOf(st); let gate=null;""","Gen wave direction")
R("return {text:L.slice(0,2).join('')+trk36GenHint(),gate};",
  "return {text:L.slice(0,2).join('')+scoutDirectionLine()+trk36GenHint(),gate};","Gen extra line")
R("function interactables(){",
  """function chooseDefense(title,options){
  if(!options.length)return;if(options.length===1){options[0].act();return;}
  const old=document.getElementById('defenseChoice');if(old)old.remove();
  const wrap=document.createElement('div');wrap.id='defenseChoice';wrap.tabIndex=-1;
  wrap.style.cssText='position:fixed;inset:0;z-index:99998;background:#0009;display:flex;align-items:center;justify-content:center;padding:18px;box-sizing:border-box';
  const panel=document.createElement('div');panel.style.cssText='width:min(360px,92vw);max-height:80vh;overflow:auto;background:#202b25;border:2px solid #d4b66b;border-radius:12px;padding:14px;color:#f5efdf;box-shadow:0 4px 20px #000a;font:15px system-ui';
  const titleEl=document.createElement('div');titleEl.textContent=title;titleEl.style.cssText='font-weight:bold;margin-bottom:10px';panel.appendChild(titleEl);
  const close=()=>{wrap.remove();S.mode='playing';cv.focus();};
  for(const opt of [...options,{label:'戻る',act:null}]){
    const b=document.createElement('button');b.type='button';b.textContent=opt.label;
    b.style.cssText='display:block;width:100%;min-height:44px;margin:7px 0;padding:9px;border:1px solid #d4b66b;border-radius:7px;background:#33453a;color:#fff;font:15px system-ui;touch-action:manipulation';
    b.onclick=()=>{close();if(opt.act)opt.act();};panel.appendChild(b);
  }
  wrap.appendChild(panel);wrap.onclick=e=>{if(e.target===wrap)close();};
  wrap.onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();close();}};
  document.body.appendChild(wrap);keys.clear();S.mode='menu';wrap.focus();
}
function interactables(){""","chooser UI")
B("  for(const g of GAPS){\n    const d=Math.min(dist(P.x,P.z,g.in.x,g.in.z)",
  "  g4Interactables(L);",
  """  for(const g of GAPS){
    const d=Math.min(dist(P.x,P.z,g.in.x,g.in.z),dist(P.x,P.z,g.c.x,g.c.z))-0.5;if(d>3)continue;
    const f=g.fence;
    if(!f.type){
      const choices=[];
      if(inv.stakeKit>0)choices.push({label:'杭柵を設置（杭柵キット1）',act:()=>placeFence(g,'stake')});
      if(inv.spikeKit>0)choices.push({label:'トゲ柵を設置（トゲ柵キット1）',act:()=>placeFence(g,'spike')});
      if(inv.fenceKit>0)choices.push({label:'木柵を設置（木柵キット1）',act:()=>placeFence(g,'wood')});
      L.push(choices.length?{d,label:choices.length===1?g.name+'に'+choices[0].label:g.name+'の柵を選んで設置',act:()=>chooseDefense(g.name+'の柵台',choices)}:
        {d,label:g.name+'の柵台：木柵・トゲ柵・杭柵キットが必要',act:()=>sfx('deny')});
    }else if(f.broken)L.push({d,label:g.name+'の柵を再建（木材2）',act:()=>repairFence(g,2,true)});
    else if(f.hp<f.max)L.push({d,label:g.name+'の柵を修理（木材1で+60）　'+Math.ceil(f.hp)+'/'+f.max,act:()=>repairFence(g,1,false)});
    else{
      const choices=[];
      if(f.type!=='stake'&&inv.stakeKit>0)choices.push({label:'杭柵に作り替え（杭柵キット1）',act:()=>placeFence(g,'stake')});
      if(f.type==='wood'&&inv.spikeKit>0)choices.push({label:'トゲ柵に作り替え（トゲ柵キット1）',act:()=>placeFence(g,'spike')});
      L.push(choices.length?{d,label:choices.length===1?g.name+'の柵を'+choices[0].label:g.name+'の柵を作り替える',act:()=>chooseDefense(g.name+'の作り替え',choices)}:
        {d:d+0.5,label:g.name+'の柵　耐久 '+f.max+'/'+f.max,act:()=>{}});
    }
  }
  for(const t of traps){const d=dist(P.x,P.z,t.x,t.z);if(d>1.8)continue;
    if(t.state==='empty'){
      const choices=[];
      if(inv.trapKit>0)choices.push({label:'くくり罠を仕掛ける（くくり罠キット1）',act:()=>placeTrap(t,'snare')});
      if(inv.pitKit>0)choices.push({label:'落とし穴を掘る（落とし穴キット1）',act:()=>placeTrap(t,'pit')});
      L.push(choices.length?{d,label:choices.length===1?choices[0].label:'設置する罠を選ぶ',act:()=>chooseDefense('罠台',choices)}:
        {d,label:'罠台：くくり罠・落とし穴キットが必要',act:()=>sfx('deny')});
    }else if(t.state==='sprung')L.push({d,label:t.type==='pit'?'落とし穴を掘り直す（木材2）':'罠を掛け直す（木材1）',act:()=>rearmTrap(t)});
    else L.push({d,label:t.type==='pit'?'落とし穴：作動待ち':'くくり罠：作動待ち',act:()=>{}});
  }
  {const d=dist(P.x,P.z,SCOUT.x,SCOUT.z);
   if(d<2.6)L.push({d,label:prog.scoutTower?'見張り台：見張り中':'見張り台を建設（木材10・縄4）',act:()=>buildScoutTower()});}
""","defense interactions")
B("function placeFence(g,type){","function repairFence(g,cost,full){",
  """function placeFence(g,type){
  const k=type==='stake'?'stakeKit':type==='spike'?'spikeKit':'fenceKit';if(inv[k]<=0)return;
  inv[k]--;setFence(g,type);toast(g.name+'に'+(type==='stake'?'杭柵':type==='spike'?'トゲ柵':'木柵')+'を設置した');sfx('wood');saveGame();
}
""","spike placement")
B("function placeTrap(t){","// ================= クラフト =================",
  """function placeTrap(t,type='snare'){
  const pit=type==='pit',k=pit?'pitKit':'trapKit';if(t.state!=='empty')return;
  if(inv[k]<=0){toast(pit?'落とし穴キットがない':'くくり罠キットがない',true);sfx('deny');return;}
  inv[k]--;setTrap(t,'armed',type);toast(pit?'落とし穴を設置した':'くくり罠を仕掛けた');sfx('trap');saveGame();
}
function rearmTrap(t){
  const cost=t.type==='pit'?2:1;
  if(inv.wood<cost){toast('木材が足りない（必要'+cost+'）',true);sfx('deny');return;}
  inv.wood-=cost;setTrap(t,'armed');toast(t.type==='pit'?'落とし穴を掘り直した':'罠を掛け直した');sfx('trap');saveGame();
}
function buildScoutTower(){
  if(prog.scoutTower)return;
  if(inv.wood<10||inv.rope<4){toast('見張り台：木材10と縄4が必要',true);sfx('deny');return;}
  inv.wood-=10;inv.rope-=4;prog.scoutTower=true;scoutVisual();sfx('wood');
  toast('見張り台が完成した。群れの接近を早く知らせられる！');saveGame();
}

""","pit placement and tower build")
R("give:()=>{inv.trapKit++;}},\n",
  """give:()=>{inv.trapKit++;}},
 {id:'spikeFence',name:'トゲ柵キット',cost:{wood:4,hide:1},desc:'柵台に設置。耐久90。接触した獣に6ダメージと体勢削り',give:()=>{inv.spikeKit++;}},
 {id:'pitTrap',name:'落とし穴キット',cost:{wood:4,rope:1},desc:'罠台に設置。イノシシ・クマを5秒拘束し28ダメージ。サルは飛び越える。ヌシは2.5秒。使用後は木材2で掘り直し',lock:()=>!prog.unlockTrap,lockMsg:'小規模襲撃を退けると解放',give:()=>{inv.pitKit++;}},
""","craft recipes")
R("['木柵キット',inv.fenceKit],['杭柵キット',inv.stakeKit],['くくり罠キット',inv.trapKit]];",
  "['木柵キット',inv.fenceKit],['トゲ柵キット',inv.spikeKit],['杭柵キット',inv.stakeKit],['くくり罠キット',inv.trapKit],['落とし穴キット',inv.pitKit]];","inventory names")
R('<div class="row"><span>くくり罠キット</span><b id="rTrap">0</b></div>',
  '<div class="row"><span>くくり罠キット</span><b id="rTrap">0</b></div>\n     <div class="row"><span>トゲ柵キット</span><b id="rSpike">0</b></div>\n     <div class="row"><span>落とし穴キット</span><b id="rPit">0</b></div>',"HUD kit labels")
R("setTxt('rTrap',inv.trapKit); setTxt('rStake',inv.stakeKit);",
  "setTxt('rTrap',inv.trapKit); setTxt('rSpike',inv.spikeKit); setTxt('rPit',inv.pitKit); setTxt('rStake',inv.stakeKit);","HUD kit counts")
R("['rFence',inv.fenceKit],['rTrap',inv.trapKit]])",
  "['rFence',inv.fenceKit],['rTrap',inv.trapKit],['rSpike',inv.spikeKit],['rPit',inv.pitKit]])","HUD kit visibility")
R("unlockBoss:prog.unlockBoss,clues:prog.clues,bossDefeated:prog.bossDefeated},f31SaveProg()",
  "unlockBoss:prog.unlockBoss,clues:prog.clues,bossDefeated:prog.bossDefeated,scoutTower:!!prog.scoutTower,scoutWarned:!!prog.scoutWarned,scoutRaidWarned:!!prog.scoutRaidWarned},f31SaveProg()","save tower")
R("traps:traps.map(t=>t.state),stats",
  "traps:traps.map(t=>t.type==='pit'?{type:'pit',state:t.state}:t.state),stats","save trap")
R("prog.unlockTrap=!!p.unlockTrap; prog.unlockBoss=!!p.unlockBoss; prog.bossDefeated=!!p.bossDefeated; f31LoadProg(p);",
  "prog.unlockTrap=!!p.unlockTrap; prog.unlockBoss=!!p.unlockBoss; prog.bossDefeated=!!p.bossDefeated; prog.scoutTower=!!p.scoutTower; prog.scoutWarned=!!p.scoutWarned; prog.scoutRaidWarned=!!p.scoutRaidWarned; f31LoadProg(p);","load tower")
R("if(f&&(f.type==='wood'||f.type==='stake')) setFence(g,f.type,num(f.hp,0,0,999));",
  "if(f&&(f.type==='wood'||f.type==='stake'||f.type==='spike')) setFence(g,f.type,num(f.hp,0,0,999));","load spike")
R("traps.forEach((t,i)=>{ const s=extra&&extra.traps[i]; setTrap(t,['armed','sprung'].includes(s)?s:'empty'); });",
  """traps.forEach((t,i)=>{const s=extra&&extra.traps[i],type=s&&typeof s==='object'&&s.type==='pit'?'pit':'snare';
    const state=typeof s==='string'?s:(s&&typeof s==='object'?s.state:null);
    setTrap(t,['armed','sprung'].includes(state)?state:'empty',type);
  });
  scoutVisual();""","load old and new traps")
R("buildFenceSlots(); buildTraps();\n  spawnFieldEnemies();",
  "buildFenceSlots(); buildTraps(); buildScoutSite();\n  spawnFieldEnemies();","tower init")
R("prog.stage='invasionPrep'; prog.prepT=150; if(lightMode=",
  "prog.stage='invasionPrep'; prog.prepT=150; prog.scoutWarned=false; if(lightMode=","prepare warning flag")
R("if(prog.stage==='buildFence'&&!ev.kind){ prog.gatherT+=dt; if(GAPS.some(g=>g.fence.type)){ prog.raidDelay=(prog.raidDelay||0)+dt; if(prog.raidDelay>2.5) startEvent('raid'); }",
  """if(prog.stage==='buildFence'&&!ev.kind){prog.gatherT+=dt;if(GAPS.some(g=>g.fence.type)){
    if(prog.scoutTower&&!prog.scoutRaidWarned){prog.scoutRaidWarned=true;toast('見張り台：南門へ向かう獣の気配！',true);}
    prog.raidDelay=(prog.raidDelay||0)+dt;if(prog.raidDelay>2.5)startEvent('raid');}""","early raid toast")
R("if(prog.stage==='invasionPrep'&&!ev.kind){ prog.prepT-=dt; if(prog.prepT<=0) startEvent('invasion'); }",
  """if(prog.stage==='invasionPrep'&&!ev.kind){
    prog.prepT-=dt;const early=prog.scoutTower?120:45;
    if(!prog.scoutWarned&&prog.prepT<=early&&prog.prepT>0){prog.scoutWarned=true;
      toast(prog.scoutTower?'見張り台：三方向から獣が近づいている！ 早めに備えよ':'もうすぐ群れが来る。柵と罠を最終確認しよう',true);}
    if(prog.prepT<=0)startEvent('invasion');
  }""","early invasion toast")
R("  c.fillStyle='#d8b04a'; c.beginPath(); c.arc(X(CORE.x),Z(CORE.z),3,0,TAU); c.fill();",
  "  c.fillStyle='#d8b04a'; c.beginPath(); c.arc(X(CORE.x),Z(CORE.z),3,0,TAU); c.fill();\n  if(prog.scoutTower){c.fillStyle='#91d7ab';c.fillRect(X(SCOUT.x)-2,Z(SCOUT.z)-2,4,4);}","map landmark")
R("function hideAllOv(){ for(const id of ['title','howto','pause','craft','inv','dead','result','quests','mapOv','store','npcOv']) $(id).hidden=true; }",
  "function hideAllOv(){ for(const id of ['title','howto','pause','craft','inv','dead','result','quests','mapOv','store','npcOv']) $(id).hidden=true; const c=document.getElementById('defenseChoice');if(c)c.remove(); }","chooser cleanup")
assert "const SAVE_KEY='eiheiji_vs_beasts_v010';" in s
assert "fenceFix',name:'柵の修理（全か所）'" in s
assert "e.stunT=3.5;" in s and "e.stunT=e.type==='boss'?2.5:5;" in s
assert "f.max=type==='stake'?260:type==='spike'?90:120;" in s
assert "const AILOD_SKIP=" in s and "'trapped','stun'" in s
for left,right in [
 ("function startEvent(kind){","function queueWave(i){"),
 ("function updateBoss(e,dt){","function updateEnemyAnim(e,dt){"),
 ("const F11B={","function f11InvHp(hp){"),
 ("  {id:'fenceFix'","  {id:'toolRepair'")]:
    def region(t):return t[t.index(left):t.index(right,t.index(left))]
    assert region(original)==region(s), "Protected section changed: "+left
assert len(s)>len(original) and len(original)>7_000_000
# Extract actual executable blocks (exclude embedded JSON and remote three.js).
with tempfile.TemporaryDirectory() as td:
    checked=[]
    for n,m in enumerate(re.finditer(r'<script\b([^>]*)>(.*?)</script\s*>',s,re.I|re.S),1):
        attrs,body=m.groups()
        if re.search(r'\bsrc=|type\s*=\s*["\x27]application/json',attrs,re.I):continue
        temp=pathlib.Path(td)/("block_%d.js"%n)
        temp.write_text(body,encoding="utf-8")
        subprocess.run(["node","--check",str(temp)],check=True)
        checked.append({"block":n,"bytes":len(body)})
    assert len(checked)>=3, checked
    # Fast behavior harness: use the exact patched functions (not reimplementations).
    def cut(start,end):return s[s.index(start):s.index(end,s.index(start))]
    spike=cut("function spikeFenceContact(gp,e){","const traps=TRAP_SLOTS")
    pit=cut("function triggerTrap(t,e){","// ================= 防衛対象 =================")
    gen=cut("function scoutDirectionLine(){","function f9GenInfo(){")
    js="""
const assert=require('node:assert/strict');
let S={time:5},touches=[],effects=[];
function damageEnemy(e,d,k,ang,info){touches.push({d,info});e.hp-=d;}
function setTrap(t,state){t.state=state;}
function sfx(){}function f10Noise(){}function hideSector(){}
function setState(e,s){e.state=s;}function floatText(){}function toast(){}
""" + spike+pit+gen+"""
const gp={id:'S',c:{x:10,z:10},fence:{type:'spike',broken:false}};
const x={type:'boar',x:11,z:10,hp:100,state:'chase',ind:{visible:true}};
spikeFenceContact(gp,x);
assert.equal(x.hp,94);assert.equal(touches[0].info.mv.poise,12);
S.time+=.2;spikeFenceContact(gp,x);assert.equal(touches.length,1);
S.time+=1;spikeFenceContact(gp,x);assert.equal(touches.length,2);
let t={type:'pit',state:'armed',x:0,z:0};
const foe=(type)=>({type,hp:100,state:'chase',ind:{visible:true}});
const boar=foe('boar');triggerTrap(t,boar);
assert.equal(t.state,'sprung');assert.equal(boar.stunT,5);assert.equal(boar.hp,72);
t.state='armed';const bear=foe('bear');triggerTrap(t,bear);assert.equal(bear.stunT,5);
t.state='armed';const monkey=foe('monkey');triggerTrap(t,monkey);assert.equal(t.state,'armed');assert.equal(monkey.hp,100);
t.state='armed';const boss=foe('boss');triggerTrap(t,boss);assert.equal(boss.stunT,2.5);assert.equal(boss.hp,82);
t={type:'snare',state:'armed',x:0,z:0};const old=foe('boar');triggerTrap(t,old);assert.equal(old.stunT,3.5);assert.equal(old.hp,78);
let prog={scoutTower:true,stage:'invasionPrep'},ev={kind:null};
const GAPS=[{name:'南門'},{name:'東口'},{name:'沢口'}];
assert(scoutDirectionLine().includes('南門・東口・沢口'));
ev={kind:'invasion',waveIdx:1,waves:[[],[['boar',1,0],['monkey',2,1]]]};
assert(scoutDirectionLine().includes('東口・沢口'));
prog.scoutTower=false;assert.equal(scoutDirectionLine(),'');
console.log('BEHAVIOR PASS: spike damage/poise metadata & cooldown; pit boar/bear/boss; monkey immune; snare legacy; scout directions');
"""
    p=pathlib.Path(td)/"defense_tests.js";p.write_text(js,encoding="utf-8")
    subprocess.run(["node",str(p)],check=True)
    assert "const early=prog.scoutTower?120:45;" in s
    assert "if(prog.prepT<=0)startEvent('invasion');" in s
    assert "typeof s==='string'?s" in s and "type==='pit'?'pit':'snare'" in s
    assert "traps:traps.map(t=>t.type==='pit'?{type:'pit',state:t.state}:t.state)" in s
f.write_text(s,encoding="utf-8")
print(json.dumps({"original_bytes":len(original),"patched_bytes":len(s),"patches":changes,"node_check_blocks":checked,"result":"PASS"},ensure_ascii=False))
