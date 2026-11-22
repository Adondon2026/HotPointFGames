(()=>{'use strict';
const $=id=>document.getElementById(id),canvas=$('sea'),g=canvas.getContext('2d',{alpha:false});
const room=location.pathname.match(/^\/r\/[A-Fa-f0-9]{6}/)?.[0]||'';
const token=localStorage.getItem('gh_token'+room)||'';
if(!room||!token){location.replace(room||'/');return;}
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),TAU=Math.PI*2;
const values=[-35,-24,-12,0,12,24,35],commands=values.map(v=>v*Math.PI/180);
let viewport={w:innerWidth,h:innerHeight,dpr:1},cam={x:230,y:375,z:1.05};
let snapshot=null,displayShips=null,updatedAt=0,inflight=false,rudderIndex=3;
let desired={rudder:0,aimx:1364,aimy:375,fire:false},lastFrame=0,lastPoll=0,flashUntil=0,aimTouched=false,returning=false;
let tipTimer=0;
const map={w:1440,h:750},labels={heavy:'巨',split:'裂',blast:'爆',bounce:'弹'},colors={heavy:'#f0b777',split:'#c7a6eb',blast:'#f38f77',bounce:'#85d8c8',normal:'#e2e9d9'};
function resize(){viewport.w=canvas.clientWidth||innerWidth;viewport.h=canvas.clientHeight||innerHeight;viewport.dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(viewport.w*viewport.dpr);canvas.height=Math.round(viewport.h*viewport.dpr);}
function notify(text,ms=1900){const el=$('guidance');el.textContent=text;el.classList.add('visible');clearTimeout(tipTimer);tipTimer=setTimeout(()=>el.classList.remove('visible'),ms);}
function drawDial(){
 const ticks=$('ticks');ticks.replaceChildren();
 const svgNS='http://www.w3.org/2000/svg';
 const coords=[];
 for(let i=0;i<7;i++){const angle=(205+i*(130/6))*Math.PI/180;const x=87+69*Math.cos(angle),y=93+69*Math.sin(angle);coords.push({x,y});
  const dot=document.createElementNS(svgNS,'circle');dot.setAttribute('cx',String(x));dot.setAttribute('cy',String(y));dot.setAttribute('r',i===3?'6':'5');dot.setAttribute('fill',i===rudderIndex?'#ffdf9e':'#cce0d6');dot.setAttribute('opacity',i===rudderIndex?'1':'.65');ticks.append(dot);
  const title=document.createElementNS(svgNS,'text');title.setAttribute('x',String(x));title.setAttribute('y',String(y-10));title.setAttribute('fill',i===rudderIndex?'#fff0c5':'#bad4d0');title.setAttribute('font-size','11');title.setAttribute('text-anchor','middle');title.textContent=i===3?'0':String(Math.abs(values[i]));ticks.append(title);
 }
 const pos=coords[rudderIndex];$('pointer').setAttribute('d',`M87 93L${pos.x.toFixed(1)} ${pos.y.toFixed(1)}`);
 const degree=values[rudderIndex];$('rudderValue').textContent=degree===0?'正舵':(degree<0?'左':'右')+Math.abs(degree)+'°';$('dial').setAttribute('aria-valuenow',String(degree));
}
function chooseRudder(index){rudderIndex=clamp(index,0,6);desired.rudder=commands[rudderIndex];drawDial();}
$('dial').addEventListener('pointerdown',e=>{
 e.preventDefault();
 const r=$('dial').getBoundingClientRect(),x=(e.clientX-r.left)*175/r.width,y=(e.clientY-r.top)*135/r.height;
 if(Math.hypot(x-87,y-93)<19){chooseRudder(3);return;}
 let k=3,d=Infinity;
 for(let i=0;i<7;i++){const a=(205+i*(130/6))*Math.PI/180,tx=87+69*Math.cos(a),ty=93+69*Math.sin(a),dd=Math.hypot(x-tx,y-ty);if(dd<d){k=i;d=dd;}}
 chooseRudder(k);
});
$('dial').addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();chooseRudder(rudderIndex+(e.key==='ArrowLeft'?-1:1));}if(e.key==='Home'){e.preventDefault();chooseRudder(3);}});
function holdStart(e){if(snapshot?.winner!==null&&snapshot?.winner!==undefined)return;e.preventDefault();desired.fire=true;$('fire').classList.add('pressed');if(e.pointerId!==undefined)try{$('fire').setPointerCapture(e.pointerId);}catch(_){}send('control');}
function holdEnd(e){desired.fire=false;$('fire').classList.remove('pressed');}
$('fire').addEventListener('pointerdown',holdStart);for(const type of ['pointerup','pointercancel','lostpointercapture'])$('fire').addEventListener(type,holdEnd);
document.addEventListener('visibilitychange',()=>{if(document.hidden)holdEnd();});
function toWorld(x,y){return{x:(x-viewport.w/2)/cam.z+cam.x,y:(y-viewport.h/2)/cam.z+cam.y};}
canvas.addEventListener('pointerdown',e=>{
 e.preventDefault();const p=toWorld(e.clientX,e.clientY);desired.aimx=clamp(p.x,0,map.w);desired.aimy=clamp(p.y,0,map.h);aimTouched=true;
 notify('炮口已对准目标',700);
});
function myShip(){return snapshot?.ships?.[snapshot.seat];}
function follow(dt){
 if(!snapshot)return;const ship=displayShips?.[snapshot.seat]||myShip();if(!ship)return;
 const dir=snapshot.seat===0?1:-1,visibleAhead=Math.min(125,viewport.w*.25);
 const tx=ship.x+dir*visibleAhead,ty=ship.y;
 const k=1-Math.exp(-dt*4.3);
 cam.x+= (tx-cam.x)*k;cam.y+=(ty-cam.y)*k;
 const target=clamp(Math.min(viewport.w/390,viewport.h/620),.67,1.15);
 cam.z+=(target-cam.z)*k;
}
function updateUI(){
 if(!snapshot)return;const i=snapshot.seat,mine=snapshot.bases[i],other=snapshot.bases[1-i];
 $('hpMine').textContent=Math.ceil(mine);$('hpEnemy').textContent=Math.ceil(other);
 $('mineBar').style.width=clamp(mine/240*100,0,100)+'%';$('enemyBar').style.width=clamp(other/240*100,0,100)+'%';
 const canFire=snapshot.winner===null;$('fire').disabled=!canFire;
 $('chargeLabel').textContent=snapshot.cooldown>0.05?'装填 '+snapshot.cooldown.toFixed(1)+'s':'按住连续射击';
 if(!canFire){holdEnd();$('finish').hidden=false;const win=snapshot.winner===i;
  $('finishTitle').textContent=win?'胜利 · 保卫成功':'失利 · 子滩失守';
  $('finishText').textContent=win?'你率先击毁了敌方子滩':'对方率先击毁了你的子滩';
  $('rematch').hidden=!snapshot.host;$('finishReturn').hidden=!snapshot.host;
 }else $('finish').hidden=true;
}
async function send(type='control'){
 if(inflight||returning)return;
 inflight=true;
 const request={type,token};
 if(type==='control')Object.assign(request,desired);
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),2600);
 try{
  const response=await fetch(room+'/api/ship',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request),signal:controller.signal,cache:'no-store'});
  const data=await response.json();if(!data.ok){if(data.roomEnded){location.replace(room+'/');return;}notify(data.error||'连接中断',2200);return;}
  if(!snapshot&&data.seat===1&&!aimTouched){desired.aimx=76;desired.aimy=375;}snapshot=data;updatedAt=performance.now();if(!displayShips)displayShips=data.ships.map(s=>({...s}));
  updateUI();
 }catch(e){if(!document.hidden)notify('等待连接恢复…',800);}
 finally{clearTimeout(timer);inflight=false;}
}
async function command(type){if(inflight)return;const request={type,token};returning=true;
 try{const response=await fetch(room+'/api/ship',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(request)});const data=await response.json();
 if(!data.ok){notify(data.error||'操作失败');return;}if(type==='return'){location.replace(room+'/');return;}snapshot=data;displayShips=null;desired.fire=false;$('finish').hidden=true;notify('新一局开始',1100);
 }catch(e){notify('网络不稳定，请重试');}finally{returning=false;}
}
$('menuButton').onclick=()=>{$('menu').hidden=false;holdEnd();};
$('resume').onclick=()=>{$('menu').hidden=true;};
$('return').onclick=()=>{if(snapshot?.host)command('return');else notify('请等待房主结束本局');};
$('finishReturn').onclick=()=>command('return');$('rematch').onclick=()=>command('rematch');
document.addEventListener('keydown',e=>{
 if(e.key==='Escape')$('menu').hidden=!$('menu').hidden;
 if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();chooseRudder(rudderIndex+(e.key==='ArrowLeft'?-1:1));}
 if(e.key===' '){e.preventDefault();desired.fire=true;}
});document.addEventListener('keyup',e=>{if(e.key===' ')holdEnd();});
function rect(x,y,w,h,c){g.fillStyle=c;g.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h));}
function circle(x,y,r,c){g.fillStyle=c;g.beginPath();g.arc(x,y,r,0,TAU);g.fill();}
function stroke(x1,y1,x2,y2,color,width=1){g.strokeStyle=color;g.lineWidth=width;g.beginPath();g.moveTo(x1,y1);g.lineTo(x2,y2);g.stroke();}
function drawMap(t){
 const l=cam.x-viewport.w/(2*cam.z)-50,r=cam.x+viewport.w/(2*cam.z)+50,top=cam.y-viewport.h/(2*cam.z)-50,bot=cam.y+viewport.h/(2*cam.z)+50;
 rect(l,top,r-l,bot-top,'#155469');
 for(let y=Math.floor(top/34)*34;y<bot;y+=34)for(let x=Math.floor(l/43)*43;x<r;x+=43){
  rect(x+Math.sin(t*.0008+x*.02)*3,y+8,10,2,'#2c788c');
  if((Math.floor(x/43)+Math.floor(y/34))%4===0)rect(x+24,y+18,5,2,'#35869a');
 }
 // Boundary shallows and coast
 rect(-30,-30,map.w+60,38,'#497d81');rect(-30,map.h-8,map.w+60,38,'#497d81');
 for(let x=14;x<map.w;x+=55){rect(x,8,27,6,'#b5ac7a');rect(x,map.h-16,27,6,'#b5ac7a');}
 // navigation corridor markings
 for(let x=95;x<map.w;x+=76){rect(x,370,32,2,'rgba(165,208,197,.23)');}
 // Bases
 for(let i=0;i<2;i++){
  const x=i===0?74:map.w-74;
  circle(x,375,63,'#255567');circle(x,375,52,'#6b786a');circle(x,375,43,i===0?'#5b9d91':'#b07769');circle(x,375,31,'#304b52');
  for(let j=-1;j<=1;j++){rect(x-20+j*18,356,13,36,i===0?'#aacbc1':'#d0b4a1');rect(x-20+j*18,358,13,7,'#455f68');}
  g.fillStyle='#e6efe5';g.font='bold 17px monospace';g.textAlign='center';g.fillText('子滩',x,444);
 }
 // Reefs
 for(const [x,y,rr] of (snapshot?.rocks||[[590,216,49],[726,542,58],[842,296,50]])){
  circle(x,y,rr+14,'#407b81');circle(x,y,rr,'#b1a47c');circle(x-8,y-6,rr*.73,'#727e71');
  rect(x-18,y-6,19,8,'#bec49e');rect(x+9,y+11,15,7,'#536861');
 }
 // Pickup orbs
 for(const b of snapshot?.buffs||[]){
  if(!b.active)continue;
  const bob=Math.sin(t*.003+b.x)*3;
  circle(b.x,b.y+bob,25,'rgba(211,228,219,.17)');circle(b.x,b.y+bob,17,colors[b.kind]);
  circle(b.x-4,b.y+bob-5,5,'rgba(255,255,255,.35)');
  g.fillStyle='#123744';g.font='bold 14px sans-serif';g.textAlign='center';g.fillText(labels[b.kind]||'?',b.x,b.y+bob+5);
 }
}
function drawShip(s,i){
 if(!s||s.hp<=0)return;
 const mine=i===snapshot.seat;
 g.save();g.translate(s.x,s.y);g.rotate(s.a+Math.PI/2);
 const hull=mine?'#dfe4d1':'#e0bdb2';
 g.beginPath();g.moveTo(-15,29);g.lineTo(15,29);g.lineTo(14,-17);g.lineTo(10,-28);g.lineTo(0,-36);g.lineTo(-10,-28);g.lineTo(-14,-17);g.closePath();
 g.fillStyle='#253943';g.fill();rect(-11,-20,22,43,hull);rect(-9,-13,18,13,mine?'#69a6a3':'#c78368');rect(-9,4,18,13,mine?'#a1af96':'#a18e7c');rect(-7,19,14,6,'#e5e8d8');rect(-5,-29,10,6,'#e0c47f');
 g.restore();
 const top=s.y-47;rect(s.x-25,top,50,6,'#2b454e');rect(s.x-25,top,50*clamp(s.hp/100,0,1),6,mine?'#b9edce':'#edac9a');
}
function drawShots(t){
 const age=Math.min(.105,(performance.now()-updatedAt)/1000);
 for(const p of snapshot?.shots||[]){
  const x=p.x+(p.vx||0)*age,y=p.y+(p.vy||0)*age,r=p.kind==='heavy'?11:p.kind==='blast'?9:5;
  circle(x,y,r+5,'rgba(252,239,200,.14)');circle(x,y,r,colors[p.kind]||colors.normal);
  if(p.kind!=='normal'){g.fillStyle='#1d3f48';g.font='bold 10px sans-serif';g.textAlign='center';g.fillText(labels[p.kind]||'',x,y+3);}
 }
}
function drawAim(){
 if(!snapshot)return;const s=myShip();if(!s)return;
 const a=Math.atan2(desired.aimy-s.y,desired.aimx-s.x);
 stroke(s.x,s.y,s.x+Math.cos(a)*69,s.y+Math.sin(a)*69,'rgba(235,238,216,.5)',1.6);
 const x=desired.aimx,y=desired.aimy;
 g.strokeStyle='rgba(237,241,226,.62)';g.lineWidth=1.6;g.beginPath();g.arc(x,y,17,0,TAU);g.stroke();
 stroke(x-24,y,x-9,y,'#e4ece7');stroke(x+9,y,x+24,y,'#e4ece7');
 stroke(x,y-24,x,y-9,'#e4ece7');stroke(x,y+9,x,y+24,'#e4ece7');
}
function render(t,dt){
 if(!snapshot)return;
 if(displayShips){for(let i=0;i<2;i++){const s=displayShips[i],q=snapshot.ships[i],k=clamp(1-Math.exp(-dt*13),0,1);
  if(Math.hypot(s.x-q.x,s.y-q.y)>90){Object.assign(s,q);continue;}
  s.x+=(q.x-s.x)*k;s.y+=(q.y-s.y)*k;s.hp+=(q.hp-s.hp)*k;
  const d=Math.atan2(Math.sin(q.a-s.a),Math.cos(q.a-s.a));s.a+=d*k;
 }}
 follow(dt);
 const dpr=viewport.dpr;g.setTransform(dpr,0,0,dpr,0,0);g.fillStyle='#155469';g.fillRect(0,0,viewport.w,viewport.h);
 g.save();g.translate(viewport.w/2,viewport.h/2);g.scale(cam.z,cam.z);g.translate(-cam.x,-cam.y);
 drawMap(t);drawShots(t);for(let i=0;i<2;i++)drawShip(displayShips?.[i]||snapshot.ships[i],i);drawAim();g.restore();
 const h=viewport.h;const fade=g.createLinearGradient(0,h-235,0,h);fade.addColorStop(0,'rgba(8,30,41,0)');fade.addColorStop(1,'rgba(8,30,41,.35)');g.fillStyle=fade;g.fillRect(0,h-235,viewport.w,235);
}
function frame(t){if(!lastFrame)lastFrame=t;const dt=Math.min(.05,(t-lastFrame)/1000);lastFrame=t;if(!document.hidden)render(t,dt);requestAnimationFrame(frame);}
function poll(t){if(t-lastPoll<110)return;lastPoll=t;send();} // 9 Hz game-state/input exchange
window.addEventListener('resize',resize);window.addEventListener('orientationchange',resize);
resize();drawDial();notify('自动前进 · 点舵角刻度 · 点海面瞄准 · 按住开炮',5200);
setInterval(()=>{if(!document.hidden)poll(performance.now());},80);
send('state');requestAnimationFrame(frame);
})();