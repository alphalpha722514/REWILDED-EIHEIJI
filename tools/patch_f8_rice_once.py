from pathlib import Path
import re,subprocess,tempfile
p=Path("index.html")
s=p.read_text(encoding="utf-8")
old=s
def rep(a,b):
 global s
 if s.count(a)!=1: raise RuntimeError("anchor mismatch: "+a[:65]+" count "+str(s.count(a)))
 s=s.replace(a,b,1)
def block(a,b,v):
 global s
 i=s.find(a);j=s.find(b,i+len(a))
 if i<0 or j<0: raise RuntimeError("missing block "+a)
 s=s[:i]+v+s[j:]
rep("作物は大根1種類で、収穫は「食料」になる。","作物は大根と稲。稲の収穫では食料と藁を取得できる。")
rep("const F8={grow:240, yield:3, care:0.2, seeds0:3, cost:{wood:4,rope:1}, full:true,","const F8={grow:240,yield:3,riceGrow:390,riceYield:4,riceStraw:4,care:0.2,seeds0:3,riceSeeds0:1,cost:{wood:4,rope:1},full:true,")
block("function f8Fresh(){","// ---- 見た目（作るのは一度だけ。",'''function f8Fresh(){return {v:2,intro:0,plots:[[0,0,0,0],[0,0,0,0],[0,0,0,1]]};}
function f8Count(){return F8.full?3:1;}
function f8Crop(p){return p&&p[3]===1?1:0;}
function f8Grow(p){return f8Crop(p)?F8.riceGrow:F8.grow;}
function f8Name(p){return f8Crop(p)?'稲':'大根';}
function f8Stage(p){if(p[0]===3)return 3;if(p[0]!==2)return 0;return p[1]/f8Grow(p)<0.5?1:2;}
function f8Bar(p){const v=p[0]===3?3:Math.min(3,Math.floor(p[1]/f8Grow(p)*3));return '■'.repeat(v)+'□'.repeat(3-v);}
''')
rep("    F8M[i]={site:put(site),bed:put(bed),s1:put(mk(1)),s2:put(mk(2)),s3:put(mk(3))}; });",'''    const rice=(stage)=>{const g=new THREE.Group();for(let r=0;r<3;r++)for(let c=0;c<4;c++){
      const x=(r-1)*0.42,z=-D/2+0.36+c*(D-0.72)/3,h=stage===1?0.17:stage===2?0.42:0.67;
      g.add(mesh(G.box,mat(stage===3?0xa6b04a:0x73a344),x,0.13+h/2,z,0.025,h,0.025));
      if(stage>=2)for(const side of [-1,1]){const l=mesh(G.box,mat(0x6d963c),x+side*0.10,0.17+h*0.54,z,0.025,h*0.75,0.025);l.rotation.z=side*0.45;g.add(l);}
      if(stage===3)g.add(mesh(G.box,mat(0xd6be70),x+0.035,0.16+h,z+0.02,0.09,0.16,0.055));
    }return g;};
    F8M[i]={site:put(site),bed:put(bed),s1:put(mk(1)),s2:put(mk(2)),s3:put(mk(3)),r1:put(rice(1)),r2:put(rice(2)),r3:put(rice(3))}; });''')
rep("    m.site.visible=on&&p[0]===0; m.bed.visible=on&&p[0]>=1; m.s1.visible=on&&st===1; m.s2.visible=on&&st===2; m.s3.visible=on&&st===3; }); }",'''    const ri=f8Crop(p)===1;m.site.visible=on&&p[0]===0;m.bed.visible=on&&p[0]>=1;
    m.s1.visible=on&&!ri&&st===1;m.s2.visible=on&&!ri&&st===2;m.s3.visible=on&&!ri&&st===3;
    m.r1.visible=on&&ri&&st===1;m.r2.visible=on&&ri&&st===2;m.r3.visible=on&&ri&&st===3;});}''')
block("function f8Intro(){","function f8Build2(i)",'''function f8Intro(){const f=prog.f8;if(f.intro)return;f.intro=1;inv.seed=(inv.seed||0)+F8.seeds0;inv.riceSeed=(inv.riceSeed||0)+F8.riceSeeds0;f.plots[0][0]=Math.max(1,f.plots[0][0]);f8Apply();sfx('pickup');
  queueDialog([[npcYone,'おう、菜園を見に来たんか。大根の種を3つ分けたるわ。植え床にまいて「調べる」で世話するだけや。'],[npcYone,'放っといても枯れんし、育つのは遊んどる間だけや。採るとき、とう立ちした株から種を1つ取っとくとええ。']],()=>saveGame());toast('大根の種 +3・稲の種 +1');}
function f8Sow(i,crop=0){const p=prog.f8.plots[i];if(!p||p[0]!==1)return false;const key=crop===1?'riceSeed':'seed',name=crop===1?'稲':'大根';
  if((inv[key]||0)<1){sfx('deny');toast(name+'の種がない（米田に相談・収穫で1つ戻る）',true);return false;}
  inv[key]--;p[0]=2;p[1]=0;p[2]=0;p[3]=crop;f8Apply();sfx('craft');floatText(F8PLOTS[i].x,1.0,F8PLOTS[i].z,'種をまいた','#cfe8a0');
  toast('共同菜園 '+(i+1)+' に'+name+'の種をまいた（約'+Math.round(f8Grow(p)/60)+'分）');saveGame();return true;}
function f8PickSow(i){const p=prog.f8.plots[i];if(!p||p[0]!==1)return false;
  const rice=window.confirm('共同菜園 '+(i+1)+'：稲を植えますか？\\nOK＝稲（6分30秒）、キャンセル＝大根（4分）');return f8Sow(i,rice?1:0);}
function f8CareFx(i){if(!F8.full)return false;const p=prog.f8.plots[i];if(!p||p[0]!==2||p[2])return false;p[2]=1;p[1]=Math.min(f8Grow(p),p[1]+(f8Grow(p)-p[1])*F8.care);f8Apply();return true;}
function f8Care(i){if(!f8CareFx(i))return false;sfx('pickup');floatText(F8PLOTS[i].x,1.0,F8PLOTS[i].z,'草取りをした','#cfe8a0');saveGame();return true;}
function f8Harvest(i){const p=prog.f8.plots[i];if(!p||p[0]!==3)return false;f31Harvest(i);
  const rice=f8Crop(p)===1,name=rice?'稲':'大根',food=rice?F8.riceYield:F8.yield;p[0]=1;p[1]=0;p[2]=0;
  if(rice){inv.riceSeed=(inv.riceSeed||0)+1;inv.straw=(inv.straw||0)+F8.riceStraw;}else inv.seed=(inv.seed||0)+1;
  foodAdd('food',food);f8Apply();sfx('pickup');floatText(F8PLOTS[i].x,1.2,F8PLOTS[i].z,'食料+'+food,'#f0dca0');
  toast(name+'を収穫した　食料 +'+food+(rice?'・藁 +'+F8.riceStraw+'・稲の種 +1':'・大根の種 +1'));saveGame();return true;}
''')
block("function f8Interactables(L){","// 成長（遊んでいる間だけ。",'''function f8Interactables(L){const f=prog.f8;for(let i=0;i<f8Count();i++){const pl=F8PLOTS[i],dx=Math.max(0,Math.abs(P.x-pl.x)-F8.W/2),dz=Math.max(0,Math.abs(P.z-pl.z)-F8.D/2),d=Math.hypot(dx,dz);if(d>1.3)continue;const p=f.plots[i],nm='共同菜園 '+(i+1),crop=f8Name(p);
  if(!f.intro){L.push({d,label:'共同菜園：米田から大根と稲の種をもらう',act:f8Intro});continue;}
  if(p[0]===0)L.push({d,label:nm+'：植え床を作る（木材4・縄1）',act:()=>f8Build2(i)});
  else if(p[0]===1)L.push({d,label:nm+'：作物を選んで種をまく（大根 '+(inv.seed||0)+'・稲 '+(inv.riceSeed||0)+'）',act:()=>f8PickSow(i)});
  else if(p[0]===2)L.push({d,label:nm+'：'+crop+'が育っている '+f8Bar(p)+(p[2]?'（草取り済み）':'　草取りをする（残り時間20%短縮）'),act:()=>f8Care(i)});
  else L.push({d,label:nm+'：'+crop+'を収穫する',act:()=>f8Harvest(i)});}}
''')
block("function f8Update(dt){","// 種の保険：",'''function f8Update(dt){const f=prog.f8;let ch=false,ripe=false;for(let i=0;i<f8Count();i++){const p=f.plots[i];if(p[0]!==2)continue;const st=f8Stage(p),grow=f8Grow(p);p[1]+=dt;if(p[1]>=grow){p[1]=grow;p[0]=3;ch=true;ripe=true;}else if(f8Stage(p)!==st)ch=true;}if(ch)f8Apply();if(ripe)F8N.pend=true;if(F8.full)f8Hint();if(F8.full&&F8N.pend&&!f7Busy()&&S.time-F8N.lastT>=60){F8N.pend=false;F8N.lastT=S.time;toast('共同菜園の作物が採れるようになった');}}
''')
block("function f8SeedTopUp(){","// まだ菜園を始めていないとき",'''function f8SeedTopUp(){const f=prog.f8;if(!f.intro)return 0;const rad=f.plots.filter(p=>(p[0]===2||p[0]===3)&&f8Crop(p)===0).length,rice=f.plots.filter(p=>(p[0]===2||p[0]===3)&&f8Crop(p)===1).length;
  const n=Math.max(0,F8.seeds0-(inv.seed||0)-rad),rn=Math.max(0,F8.riceSeeds0-(inv.riceSeed||0)-rice);if(!n&&!rn)return 0;inv.seed=(inv.seed||0)+n;inv.riceSeed=(inv.riceSeed||0)+rn;
  queueDialog([[npcYone,'種が足りんのか。ほな分けたるわ。採るとき種を1つ取っとくのを忘れんようにな。']],()=>saveGame());toast('大根の種 +'+n+'・稲の種 +'+rn);return n+rn;}
''')
block("function f8Save(){","// ================= タイトル画面のカメラ",'''function f8Save(){const f=prog.f8;return {v:2,intro:f.intro?1:0,plots:f.plots.map(p=>[p[0],Math.round(p[1]*10)/10,p[2]?1:0,f8Crop(p)])};}
function f8Load(q){const f=f8Fresh();if(!q||typeof q!=='object'||(q.v!==1&&q.v!==2))return f;f.intro=q.intro?1:0;
  if(Array.isArray(q.plots))for(let i=0;i<3;i++){const p=q.plots[i];if(!Array.isArray(p))continue;let st=num(p[0],0,0,3),crop=q.v===2&&p[3]===1?1:0,grow=crop===1?F8.riceGrow:F8.grow;
    const g=typeof p[1]==='number'&&isFinite(p[1])?clamp(p[1],0,grow):0;if(st===2&&g>=grow)st=3;
    f.plots[i]=[st,st===2?g:st===3?grow:0,st===2&&p[2]?1:0,crop];}if(f.intro&&f.plots[0][0]===0)f.plots[0][0]=1;return f;}

''')
rep("iron:0,seed:0};","iron:0,seed:0,riceSeed:0};")
rep("const planted=f.plots.filter(p=>p[0]===2||p[0]===3).length; return F8.seeds0-(inv.seed||0)-planted>0;","const planted=f.plots.filter(p=>(p[0]===2||p[0]===3)&&f8Crop(p)===0).length,ricePlanted=f.plots.filter(p=>(p[0]===2||p[0]===3)&&f8Crop(p)===1).length; return F8.seeds0-(inv.seed||0)-planted>0||F8.riceSeeds0-(inv.riceSeed||0)-ricePlanted>0;")
assert len(s)>len(old) and "eiheiji_vs_beasts_v010" in s
# Each executable inline script must compile. JSON asset blocks are intentionally skipped.
scripts=re.findall(r'<script\b([^>]*)>([\s\S]*?)</script>',s,re.I)
for i,(attrs,body) in enumerate(scripts):
 if 'src=' in attrs or 'application/json' in attrs: continue
 f=Path(tempfile.gettempdir())/f'f8check_{i}.js';f.write_text(body,encoding='utf-8')
 subprocess.run(['node','--check',str(f)],check=True)
p.write_text(s,encoding='utf-8')
print("F8 rice patch applied and all inline JavaScript syntax checked; bytes",len(s.encode()))
