from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
if 'NUSHI_WILL52' in s:
    print('Already patched')
    raise SystemExit(0)
assert len(s)>7_000_000, 'unexpected base file size'

def change(old, new, label):
    global s
    count=s.count(old)
    assert count==1, f'{label}: expected 1 anchor, found {count}'
    s=s.replace(old,new,1)

assert s.count('九頭竜のヌシ')==9
s=s.replace('九頭竜のヌシ','光明寺のヌシ')

css="""
body.nushiFarewell52 #hud,body.nushiFarewell52 #touch{visibility:hidden!important}
#nushiIntroText52{position:absolute;left:6%;right:6%;bottom:1vh;text-align:center;color:#eee5d2;font:clamp(13px,2.2vw,19px)/1.55 "Zen Antique",serif;text-shadow:0 2px 8px #000}
#nushiFarewell52{position:fixed;inset:0;z-index:110;display:flex;align-items:flex-end;justify-content:center;box-sizing:border-box;padding:0 18px max(10vh,env(safe-area-inset-bottom,0px));border-top:7vh solid #07090a;border-bottom:7vh solid #07090a;background:linear-gradient(to bottom,rgba(2,8,10,.1) 20%,rgba(3,9,12,.78) 96%)}
#nushiFarewell52[hidden]{display:none!important}
#nushiFarewell52 .nushiPanel52{width:min(680px,100%);padding:20px 22px 18px;border:1px solid rgba(225,216,183,.35);background:rgba(13,20,21,.88);color:#efe8db;box-shadow:0 16px 48px rgba(0,0,0,.45)}
#nushiFarewell52 .nushiEyebrow52{font:12px/1.4 sans-serif;letter-spacing:.22em;color:#d9bb84;margin:0 0 8px}
#nushiFarewell52 .nushiSpeaker52{font:clamp(17px,3vw,25px)/1.3 "Zen Antique",serif;color:#f3e1bc;margin:0 0 12px}
#nushiFarewell52 .nushiLine52{font:clamp(15px,2.5vw,20px)/1.85 "Zen Kaku Gothic New",sans-serif;min-height:4em;white-space:pre-wrap;margin:0 0 12px}
#nushiFarewell52 .nushiNext52{float:right;min-height:42px;padding:8px 22px;border:1px solid #ae9770;background:#4b4031;color:white;font:14px sans-serif;cursor:pointer}
@media(max-height:500px){#nushiFarewell52{padding-bottom:6px;border-top-width:3vh;border-bottom-width:3vh}#nushiFarewell52 .nushiPanel52{padding:9px 14px}#nushiFarewell52 .nushiLine52{min-height:2em;margin-bottom:5px;line-height:1.4}#nushiFarewell52 .nushiSpeaker52{margin-bottom:5px}}
"""
change("body.cinema52 #cinemaMatte52{display:block}\n</style>","body.cinema52 #cinemaMatte52{display:block}\n"+css+"</style>","CSS")

change("const matte52=document.createElement('div');matte52.id='cinemaMatte52';document.body.appendChild(matte52);",
       "const matte52=document.createElement('div');matte52.id='cinemaMatte52';document.body.appendChild(matte52);\nconst introText52=document.createElement('div');introText52.id='nushiIntroText52';matte52.appendChild(introText52);","intro captions")
change("const steps=[.7,1.75,2.55];while(e.cinemaSteps52<steps.length&&e.st>=steps[e.cinemaSteps52]){beastImpact52(e,.65+e.cinemaSteps52*.2);e.cinemaSteps52++;spawnParticles(e.x,.2,e.z,8,0x998c75,3);}",
       "const steps=[.65,1.58,2.55];while(e.cinemaSteps52<steps.length&&e.st>=steps[e.cinemaSteps52]){beastImpact52(e,.9+e.cinemaSteps52*.28);e.cinemaSteps52++;spawnParticles(e.x,.2,e.z,12,0x998c75,4);}","heavy footsteps")
change("if(e.st>=2.85&&!e.cinemaRoared52){e.cinemaRoared52=true;beastVoice51(e,'roar');}",
       "if(e.st>=2.85&&!e.cinemaRoared52){e.cinemaRoared52=true;beastVoice51(e,'roar');introText52.textContent='かつてシシガミ様と呼ばれた、光明寺のヌシ。';}\n if(e.st>=5.1&&!e.cinemaLastText52){e.cinemaLastText52=true;introText52.textContent='その瞳には、九頭竜の怒りが宿っていた。';}","roar captions")
change("document.body.classList.remove('cinema52');cam.pos.copy(camera.position);","document.body.classList.remove('cinema52');introText52.textContent='';cam.pos.copy(camera.position);","intro exit")
change("bossE.cinemaSteps52=0; bossE.cinemaRoared52=false; clearCinemaInput52();",
       "bossE.cinemaSteps52=0; bossE.cinemaRoared52=false; bossE.cinemaLastText52=false; introText52.textContent='……沢の奥から、何かが近づいてくる。'; clearCinemaInput52();","intro setup")
change("S.ground52=Math.max(S.ground52||0,power*attenuation);",
       "S.ground52=Math.max(S.ground52||0,power*attenuation);\n if(AC&&AC.state==='running'&&!S.muted&&attenuation>0.01)noise(.27,.075*power*attenuation,130);","low impact")

lore=r"""
/* 光明寺のヌシ：討伐後の物語。セーブと報酬の既存仕様は維持する。 */
const NUSHI_WILL52='…..今さっき牙を向けていたワシすらも助けようとする優しい心の持ち主はお前しかいないじゃろうて';
const nushiFarewell52=document.createElement('div');
nushiFarewell52.id='nushiFarewell52';
nushiFarewell52.hidden=true;
nushiFarewell52.innerHTML='<section class="nushiPanel52" aria-live="polite"><p class="nushiEyebrow52">光明寺のヌシ — 最後の対話</p><h2 class="nushiSpeaker52"></h2><p class="nushiLine52"></p><button class="nushiNext52" type="button">次へ</button></section>';
document.body.appendChild(nushiFarewell52);
const nushiFarewellLines52=[
 ['――','沢の奥に静けさが戻った。巨大な猪は、もう牙を向けてこなかった。'],
 ['光明寺のヌシ','……よう、わしを止めてくれたのう。長い夢から目が覚めたようじゃ。'],
 ['光明寺のヌシ','昔はシシガミ様などと呼ばれておった。九頭竜とは、あやつが守神だった頃からの知り合いじゃ。'],
 ['光明寺のヌシ','それが、あやつの怒りに心を奪われ……お前たちにまで牙を向けてしもうた。'],
 ['主人公','まだ助けられるはずだ。町に戻って、みんなに相談しよう。'],
 ['光明寺のヌシ',NUSHI_WILL52]
];
let farewell52=null,lastFarewellNext52=0;
function showFarewellLine52(){
 if(!farewell52)return;
 const line=nushiFarewellLines52[farewell52.index];
 nushiFarewell52.querySelector('.nushiSpeaker52').textContent=line[0];
 nushiFarewell52.querySelector('.nushiLine52').textContent=line[1];
 nushiFarewell52.querySelector('.nushiNext52').textContent=farewell52.index===nushiFarewellLines52.length-1?'結果を見る':'次へ';
}
function beginFarewell52(e){
 farewell52={e:e,index:0,t:0};
 e.state='farewell';e.st=0;e.spd=0;
 S.mode='nushiFarewell52';S.resultT=0;
 keys.clear();held.atk=false;joy.id=null;joy.x=joy.y=0;cam.dragDX=0;
 stopBeastVoices51();
 document.body.classList.remove('cinema52');
 document.body.classList.add('nushiFarewell52');
 $('bossBar').hidden=true;
 nushiFarewell52.hidden=false;
 showFarewellLine52();
}
function finishFarewell52(){
 if(!farewell52)return;
 const e=farewell52.e;
 if(e&&!e.removed){e.state='dead';e.st=0;e.spd=0;}
 farewell52=null;
 nushiFarewell52.hidden=true;document.body.classList.remove('nushiFarewell52');
 saveGame();showResult();
}
function nextFarewell52(){
 if(!farewell52)return;
 const now=performance.now();if(now-lastFarewellNext52<240)return;
 lastFarewellNext52=now;
 if(farewell52.index<nushiFarewellLines52.length-1){farewell52.index++;showFarewellLine52();}
 else finishFarewell52();
}
nushiFarewell52.querySelector('.nushiNext52').addEventListener('click',nextFarewell52);
document.addEventListener('keydown',function(ev){
 if(S.mode!=='nushiFarewell52')return;
 if([' ','Enter','e','E','Escape'].includes(ev.key)){ev.preventDefault();ev.stopImmediatePropagation();if(!ev.repeat)nextFarewell52();}
},true);
function updateFarewell52(dt){
 if(!farewell52)return;
 farewell52.t+=dt;S.time+=dt;
 const e=farewell52.e;
 if(e&&!e.removed)updateEnemyAnim(e,dt);
}
function farewellCamera52(dt){
 if(!farewell52||!farewell52.e)return;
 const e=farewell52.e,gy=groundH(e.x,e.z),t=farewell52.t;
 const a=e.rot+.38+Math.sin(t*.23)*.06,d=10.4-Math.min(1,t/10)*1.2;
 const x=e.x+Math.sin(a)*d,z=e.z+Math.cos(a)*d;
 camera.position.set(x,Math.max(gy+2.8,groundH(x,z)+1.0),z);
 camera.lookAt(e.x,gy+2.4,e.z);
 if(camera.fov!==52){camera.fov=52;camera.updateProjectionMatrix();}
 fadeForest(x,z,e.x,e.z);
}
"""
change("// ================= ボス戦 =================",lore+"\n// ================= ボス戦 =================","farewell scene")

change("""function bossDefeated(e){
  if(prog.bossDefeated) return; prog.bossDefeated=true; bossActive=false;
  e.ind.visible=false; hideSector(e);
  inv.fang+=1; inv.hide+=8; prog.unlockBoss=true; prog.stage='cleared';
  setBarrier(false);
  S.slowmo=1.2; sfx('win'); S.shake=1;
  banner('討伐成功','ヌシの牙・獣素材8を手に入れた',3);
  saveGame();
  S.resultT=2.6;
}""",
"""function bossDefeated(e){
  if(prog.bossDefeated) return; prog.bossDefeated=true; bossActive=false;
  e.ind.visible=false; hideSector(e);
  inv.fang+=1; inv.hide+=8; prog.unlockBoss=true; prog.stage='cleared';
  setBarrier(false);
  S.slowmo=0; S.shake=.35; S.resultT=0;
  saveGame();
  beginFarewell52(e);
}""","boss defeat")

change("function updateCamera(dt){\n if(bossCinema52()){ cinemaCamera52(dt); return; }",
       "function updateCamera(dt){\n if(S.mode==='nushiFarewell52'){farewellCamera52(dt);return;}\n if(bossCinema52()){ cinemaCamera52(dt); return; }","camera hook")
change("if(S.mode==='playing'){\n    if(!F11.hold) f11Sim(raw);",
       "if(S.mode==='nushiFarewell52')updateFarewell52(rdt);\n  if(S.mode==='playing'){\n    if(!F11.hold) f11Sim(raw);","frame hook")

change('<p>山林に静けさが戻った。ヌシの首には、錆びた金属の輪がはめられていた。</p>\n    <div class="clue">刻印：「EIHEI-BIO　個体番号 007／強化段階 III」</div>',
       '<p>沢の奥に静けさが戻った。かつてシシガミ様と呼ばれた長命の猪は、九頭竜の支配から解かれた。</p>\n    <div class="clue">最後の言葉：「…..今さっき牙を向けていたワシすらも助けようとする優しい心の持ち主はお前しかいないじゃろうて」</div>','result')
change('v0.29の物語はここまで。','この章の物語はここまで。','version blurb')
change('ヌシの首輪：「EIHEI-BIO 個体番号 007／強化段階 III」……個体番号があるということは、他にも？',
       '光明寺のヌシが残したもの。青緑の鱗には、九頭竜の力の痕跡がかすかに残っている。','inventory lore')

will='…..今さっき牙を向けていたワシすらも助けようとする優しい心の持ち主はお前しかいないじゃろうて'
assert s.count(will)==2
assert '九頭竜のヌシ' not in s
assert s.count('beginFarewell52(e);')==1
p.write_text(s,encoding='utf-8')
print('Updated index.html, bytes:',len(s.encode('utf-8')),'will occurrences:',s.count(will))
