/* Original 24-second siege soundtracks and cartoon SFX, generated locally by Web Audio.
   No third-party samples, network dependency, or audio autoplay before a gesture. */
const siegeAudio=(()=>{
  const tracks=['ocean','arcade','off'];
  let mode=tracks.includes(localStorage.getItem('siege_bgm'))?localStorage.getItem('siege_bgm'):'ocean';
  let effects=localStorage.getItem('siege_sfx')!=='off';
  let ctx=null,source=null,volume=null,started=false,seen=new Set();
  const duration=24, midi=n=>440*Math.pow(2,(n-69)/12);
  function show(){
    const b=document.getElementById('siegeMusicToggle'),f=document.getElementById('siegeEffectToggle');
    if(b){b.textContent={ocean:'♫ 海浪琶音',arcade:'♫ 轻快像素',off:'♫ 音乐关'}[mode];b.setAttribute('aria-label','切换背景音乐，当前'+b.textContent)}
    if(f){f.textContent=effects?'🔊 炮声开':'🔇 炮声关';f.setAttribute('aria-pressed',String(effects))}
  }
  function ready(){
    const Audio=window.AudioContext||window.webkitAudioContext;
    if(!Audio)return false;
    if(!ctx){ctx=new Audio();volume=ctx.createGain();volume.gain.value=.26;volume.connect(ctx.destination)}
    if(ctx.state==='suspended')ctx.resume().catch(()=>{});
    return true;
  }
  function build(which){
    const sr=22050,n=Math.round(duration*sr),buffer=ctx.createBuffer(1,n,sr),out=buffer.getChannelData(0);
    const rand=(()=>{let x=which==='ocean'?927411:311982;return ()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return (x>>>0)/4294967296}})();
    function note(m,start,len,amp,kind='bell'){
      const f=midi(m),length=Math.floor(len*sr),from=Math.round(start*sr);
      for(let i=0;i<length;i++){
        const t=i/sr,idx=(from+i+n*3)%n,phase=2*Math.PI*f*t;
        let env,v;
        if(kind==='pad'){env=(1-Math.exp(-t/.32))*Math.pow(Math.max(0,Math.sin(Math.PI*t/len)),1.7);v=Math.sin(phase)*.8+Math.sin(phase*1.002+.7)*.13}
        else if(kind==='bass'){env=(1-Math.exp(-t/.009))*Math.exp(-t/.18)*Math.min(1,(len-t)/.025);v=Math.sin(phase)*.85+Math.sin(phase*2)*.17}
        else if(kind==='chip'){env=Math.min(1,t/.009,Math.max(0,(len-t)/.05));v=Math.sin(phase)*.55+Math.sin(phase*2)*.18+Math.sin(phase*3)*.08}
        else{env=(1-Math.exp(-t/.012))*Math.exp(-t/.47)*Math.min(1,(len-t)/.075);v=Math.sin(phase)*.75+Math.sin(phase*2.004+.3)*.17*Math.exp(-t/.24)+Math.sin(phase*3.01+1.1)*.065*Math.exp(-t/.13)}
        out[idx]+=amp*env*v;
      }
    }
    if(which==='ocean'){
      const bars=[[65,69,72,76],[62,65,69,72],[58,62,65,69],[55,58,62,65],[65,69,72,76],[62,65,69,72],[60,64,67,71],[57,60,64,67]];
      bars.forEach((ch,b)=>{
        ch.forEach(m=>note(m-12,b*3-.08,3.3,.0018,'pad'));
        const order=b%2===0?[0,1,2,3,2,1,3,2]:[0,2,3,1,2,3,1,0];
        order.forEach((idx,i)=>note(ch[idx],b*3+i*.375,1.15,.075*(.8+.2*((i+b)%3))));
      });
      // Nearly inaudible high-passed surf, no synthetic low-frequency hum.
      let last=0;for(let i=0;i<n;i++){
        const white=rand()*2-1;last=.82*last+.18*white;
        const swell=.35+.18*Math.sin(i/n*2*Math.PI*5)+.11*Math.sin(i/n*2*Math.PI*9);
        out[i]+=(white-last)*swell*.00085;
      }
    }else{
      const chords=[[60,64,67,71],[59,62,65,67],[57,60,64,67],[60,64,65,69],[57,60,62,65],[59,62,65,67],[59,62,64,67],[57,60,64,67],[60,64,65,69],[60,64,67,71],[57,60,62,65],[59,62,65,67],[59,62,64,67],[57,60,64,67],[57,60,62,65],[59,62,65,67]];
      const roots=[48,43,45,41,38,43,40,45,41,36,38,43,40,45,38,43];
      const melody=[[76,null,79,81,79,76,74,72],[74,76,79,null,77,74,71,null],[72,76,79,81,null,79,76,72],[77,76,72,69,72,null,74,76],[74,null,77,81,79,77,74,null],[71,74,77,79,77,null,74,71],[76,79,83,81,79,76,null,74],[72,76,79,84,null,81,79,76],[77,81,null,84,81,79,77,76],[76,79,83,86,83,null,79,76],[74,77,81,79,77,74,72,null],[71,74,77,null,79,77,74,71],[76,79,83,81,79,null,76,74],[72,76,79,81,84,null,79,76],[77,79,81,84,81,79,77,74],[74,71,74,77,79,83,86,null]];
      const beat=.375;
      for(let b=0;b<16;b++){
        const start=b*1.5;
        [0,1,1.75,2.25,3,3.5].forEach((q,i)=>note(roots[b]+([1,3,5].includes(i)?7:0),start+q*beat,.22,.085,'bass'));
        [.5,1.5,2.5,3.5].forEach((q,i)=>note(chords[b][[0,2,1,3][i]]+12,start+q*beat,.13,.035,'chip'));
        melody[b].forEach((m,i)=>{if(m!==null)note(m,start+i*beat/2,.17,.155,'chip')});
      }
      // Gentle, soft noise percussion with two-note low kick, not a harsh buzzing square wave.
      for(let k=0;k<64;k++){
        const at=Math.round(k*beat*sr);
        for(let j=0;j<Math.floor(.075*sr);j++){
          const t=j/sr,idx=(at+j)%n,env=Math.exp(-t*38);
          out[idx]+=k%2===0? .042*Math.sin(2*Math.PI*(73+90*Math.exp(-t*20))*t)*env: .016*(rand()*2-1)*env;
        }
      }
    }
    let mx=0;for(let i=0;i<n;i++){out[i]=Math.tanh(out[i]*2.2)*.8;mx=Math.max(mx,Math.abs(out[i]))}
    if(mx>.8)for(let i=0;i<n;i++)out[i]*=.8/mx;
    // Circular interpolation at the loop boundary.
    const edge=400;for(let i=0;i<edge;i++){const a=i/edge;out[n-edge+i]=out[n-edge+i]*(1-a)+out[i]*a}
    return buffer;
  }
  const buffers={};
  function music(){
    if(!ready())return;
    if(source){try{source.stop()}catch(_){ }source.disconnect();source=null}
    if(mode==='off'||!started)return;
    if(!buffers[mode])buffers[mode]=build(mode);
    source=ctx.createBufferSource();source.buffer=buffers[mode];source.loop=true;source.connect(volume);source.start();
  }
  function unlock(){if(!ready())return;started=true;if(!source)music()}
  function tone(start,duration,from,to,gain=.1,type='sine'){
    const o=ctx.createOscillator(),g=ctx.createGain(),now=ctx.currentTime+start;
    o.type=type;o.frequency.setValueAtTime(from,now);o.frequency.exponentialRampToValueAtTime(Math.max(30,to),now+duration);
    g.gain.setValueAtTime(.0001,now);g.gain.exponentialRampToValueAtTime(Math.max(.00011,gain),now+.008);
    g.gain.exponentialRampToValueAtTime(.0001,now+duration);
    o.connect(g);g.connect(ctx.destination);o.start(now);o.stop(now+duration+.02);
  }
  function cannon(buffs=[]){
    if(!effects||!ready())return;
    // Original cute pop → rising swoosh → fluffy poof → little sparkle.
    tone(0,.17,155,92,.22);tone(.025,.28,430,980,.115);
    tone(.13,.31,875,445,.13);tone(.19,.35,355,145,.12);tone(.28,.2,1040,1360,.05);tone(.40,.14,1420,1600,.036);
    const keys=new Set(buffs);
    if(keys.has('big'))tone(.03,.5,175,70,.19);
    if(keys.has('power')||keys.has('pierce'))tone(.06,.23,540,1160,.08);
    if(keys.has('shock'))tone(.18,.7,430,90,.13);
    if(keys.has('splitshot'))for(let i=0;i<3;i++)tone(.18+i*.12,.12,520+i*140,850+i*120,.075);
    if(keys.has('bounce'))for(let i=0;i<3;i++)tone(.19+i*.12,.17,310+i*130,660+i*170,.075);
    if(keys.has('through'))tone(.06,.42,620,1420,.08);
    if(keys.has('blackhole'))tone(.2,.62,400,105,.08);
    if(keys.has('gunteleport')||keys.has('coreteleport'))for(let i=0;i<4;i++)tone(.18+i*.08,.11,720+i*130,1100+i*170,.055);
    if(keys.has('wooddrop')||keys.has('stonedrop'))tone(.3,.24,270,140,.07);
  }
  function onState(old,now){
    if(!now||!old||old.code!==now.code)return;
    for(let side=0;side<2;side++){
      const previous=old.shots?.[side]||0,newShots=now.shots?.[side]||0;
      if(newShots<=previous)continue;
      const id=now.code+':'+side+':'+newShots;
      if(seen.has(id))continue;seen.add(id);
      if(seen.size>300)seen.clear();
      // The authoritative event is available for turn mode; stock selection otherwise
      // falls back to visible inventory (e.g. simultaneous rounds).
      let buff=[];
      if(now.event?.side===side)buff=now.event.attacks||Object.keys(now.event.selected||{});
      else if(side===now.seat)buff=Object.keys(old.buffs?.[side]||{}).filter(k=>(old.buffs[side][k]||0)>0);
      cannon(buff);
    }
  }
  function setMusic(){
    mode=tracks[(tracks.indexOf(mode)+1)%tracks.length];
    localStorage.setItem('siege_bgm',mode);unlock();music();show();
  }
  function setEffects(){effects=!effects;localStorage.setItem('siege_sfx',effects?'on':'off');unlock();show()}
  document.getElementById('siegeMusicToggle')?.addEventListener('click',setMusic);
  document.getElementById('siegeEffectToggle')?.addEventListener('click',setEffects);
  document.addEventListener('pointerdown',()=>{if(document.body.classList.contains('in-battle'))unlock()},{passive:true});
  show();
  return {unlock,onState,stop:()=>{if(source){source.stop();source.disconnect();source=null}},cannon};
})();
