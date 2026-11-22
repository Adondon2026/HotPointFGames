(()=>{'use strict';
const $=id=>document.getElementById(id), canvas=$('sea'),ctx=canvas.getContext('2d',{alpha:false});
const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v)), lerp=(a,b,t)=>a+(b-a)*t;
const DEG=Math.PI/180, PX_PER_M=4.3, KNOTS_PER_WORLD=1/(PX_PER_M*.514444);
const DOCK_X=675, DOCK_TOP=135, DOCK_BOTTOM=720;
const BERTH={x:645,y:442,a:-Math.PI/2}, TELEGRAPH=['倒车二','倒车一','停车','前进一','前进二'];
const SEAS=[{name:'平静港池',current:0,wind:0},{name:'侧风',current:.14,wind:.25},{name:'横流',current:1.0,wind:.20}];
const SW=()=>window.innerWidth, SH=()=>window.innerHeight;
let boat,seaIndex=0,won=false,paused=false,settle=0,lastCollision=-100,trail=[],lastFrame=0,noticeUntil=0,lastInput=0,drawClock=0;
let viewport={w:SW(),h:SH(),dpr:1}, cam={x:585,y:780,z:.95,manual:false};
const canvasPointers=new Map();let wheelPointer=null,enginePointer=null;
const speedKn=()=>Math.hypot(boat.gx,boat.gy)*KNOTS_PER_WORLD;
function say(message,duration=2400){$('prompt').textContent=message;$('prompt').classList.add('show');noticeUntil=performance.now()+duration;}
function angleDiff(a,b){return Math.atan2(Math.sin(a-b),Math.cos(a-b));}
function corners(){const f=Math.cos(boat.a),s=Math.sin(boat.a),rx=-s,ry=f;return [[55,15],[55,-15],[-44,15],[-44,-15]].map(([l,w])=>({x:boat.x+f*l+rx*w,y:boat.y+s*l+ry*w}));}
function mooringGap(){return DOCK_X-Math.max(...corners().map(p=>p.x));}
function distToBerth(){return Math.hypot(boat.x-BERTH.x,boat.y-BERTH.y);}
function resize(){viewport.w=canvas.clientWidth||SW();viewport.h=canvas.clientHeight||SH();viewport.dpr=Math.min(2,window.devicePixelRatio||1);
 canvas.width=Math.round(viewport.w*viewport.dpr);canvas.height=Math.round(viewport.h*viewport.dpr);ctx.setTransform(viewport.dpr,0,0,viewport.dpr,0,0);ctx.imageSmoothingEnabled=false;updateControls();}
function reset(){boat={x:562,y:875,a:-Math.PI/2,u:0,v:0,r:0,rudder:0,rudderActual:0,engine:0,gx:0,gy:0,hits:0,time:0};
 won=false;paused=false;settle=0;lastCollision=-100;trail=[];$('finish').hidden=true;$('menu').hidden=true;
 cam.manual=false;cam.x=boat.x+35;cam.y=boat.y-60;cam.z=autoZoom();canvasPointers.clear();
 $('level').value=String(seaIndex);$('follow').hidden=true;updateControls();updateUI();say('拖动左侧舵轮、右侧车钟；在海面双指缩放',5200);}
function autoZoom(){return clamp(Math.min(viewport.w/370,viewport.h/680)*.96,.74,1.2)+(distToBerth()<180?.19*(1-distToBerth()/180):0);}
function follow(){cam.manual=false;$('follow').hidden=true;say('镜头跟随船舶',1200);}
function updateCamera(dt){if(cam.manual)return;
 const forwardX=Math.cos(boat.a),forwardY=Math.sin(boat.a);
 const look=viewport.h<650?42:76, targetX=boat.x+forwardX*look+28,targetY=boat.y+forwardY*look;
 const a=1-Math.exp(-dt*2.5);cam.x=lerp(cam.x,targetX,a);cam.y=lerp(cam.y,targetY,a);cam.z=lerp(cam.z,autoZoom(),a);}
function updateControls(){
 $('rudderLabel').textContent=Math.abs(boat?.rudder||0)<.6?'正舵':(boat.rudder<0?'左':'右')+Math.abs(boat.rudder).toFixed(0)+'°';
 $('wheelDisc').style.transform='rotate('+((boat?.rudder||0)*4)+'deg)';
 $('wheel').setAttribute('aria-valuenow',String(Math.round(boat?.rudder||0)));
 $('engineLabel').textContent=TELEGRAPH[(boat?.engine||0)+2];
 const t=$('engineRail'),h=t.clientHeight||166,eng=boat?.engine||0;
 $('engineHandle').style.top=(20+(2-eng)*(h-40)/4)+'px';$('engineHandle').textContent=['倒Ⅱ','倒Ⅰ','停','进Ⅰ','进Ⅱ'][eng+2];
 t.setAttribute('aria-valuenow',String(eng));t.setAttribute('aria-valuetext',TELEGRAPH[eng+2]);
}
function setRudder(v){if(won||paused)return;const next=clamp(v,-35,35);if(Math.abs(next-boat.rudder)<.1)return;boat.rudder=next;lastInput=performance.now();updateControls();}
function setEngine(v){if(won||paused)return;const next=clamp(Math.round(v),-2,2);if(next===boat.engine)return;boat.engine=next;lastInput=performance.now();updateControls();say(TELEGRAPH[next+2],900);}
function changeLevel(v){seaIndex=clamp(Number(v)||0,0,2);reset();}
function openMenu(){if(won)return;paused=true;$('menu').hidden=false;$('resume').focus();}
function closeMenu(){$('menu').hidden=true;paused=false;$('menuButton').focus();}
$('menuButton').addEventListener('click',openMenu);$('resume').addEventListener('click',closeMenu);
$('restart').addEventListener('click',reset);$('retry').addEventListener('click',reset);
$('nextSea').addEventListener('click',()=>changeLevel((seaIndex+1)%3));
$('level').addEventListener('change',e=>changeLevel(e.target.value));
$('follow').addEventListener('click',follow);
$('menu').addEventListener('pointerdown',e=>{if(e.target===$('menu'))closeMenu();});
document.addEventListener('keydown',e=>{
 if(e.key==='Escape'){if(!$('menu').hidden)closeMenu();else openMenu();return;}
 if(!$('menu').hidden||!$('finish').hidden)return;
 if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();setRudder(boat.rudder+(e.key==='ArrowLeft'?-2:2));}
 if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();setEngine(boat.engine+(e.key==='ArrowUp'?1:-1));}
 if(e.key===' '){e.preventDefault();setEngine(0);}if(e.key.toLowerCase()==='r')reset();
 if(e.key==='Home')follow();
});
const wheel=$('wheel');
function wheelAngle(e){const rect=wheel.getBoundingClientRect();return Math.atan2(e.clientY-(rect.top+rect.height/2),e.clientX-(rect.left+rect.width/2));}
wheel.addEventListener('pointerdown',e=>{
 if(won||paused)return;e.preventDefault();const rect=wheel.getBoundingClientRect(),dx=e.clientX-(rect.left+rect.width/2),dy=e.clientY-(rect.top+rect.height/2);
 if(Math.hypot(dx,dy)<22){setRudder(0);say('正舵',850);return;}
 wheelPointer={id:e.pointerId,last:wheelAngle(e)};wheel.setPointerCapture(e.pointerId);wheel.classList.add('pressed');
});
wheel.addEventListener('pointermove',e=>{
 if(!wheelPointer||wheelPointer.id!==e.pointerId)return;e.preventDefault();
 const current=wheelAngle(e),delta=angleDiff(current,wheelPointer.last);wheelPointer.last=current;
 setRudder(boat.rudder+delta/DEG/4);
});
function stopWheel(e){if(wheelPointer&&wheelPointer.id===e.pointerId){wheelPointer=null;wheel.classList.remove('pressed');}}
wheel.addEventListener('pointerup',stopWheel);wheel.addEventListener('pointercancel',stopWheel);wheel.addEventListener('lostpointercapture',stopWheel);
wheel.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();setRudder(boat.rudder+(e.key==='ArrowLeft'?-2:2));}if(e.key==='Home'){e.preventDefault();setRudder(0);}});
const throttle=$('engineRail');
function engineFromY(clientY){const rect=throttle.getBoundingClientRect(),y=clamp(clientY-rect.top-20,0,Math.max(1,rect.height-40));return 2-Math.round(y/Math.max(1,rect.height-40)*4);}
throttle.addEventListener('pointerdown',e=>{if(won||paused)return;e.preventDefault();enginePointer=e.pointerId;throttle.setPointerCapture(e.pointerId);throttle.classList.add('pressed');setEngine(engineFromY(e.clientY));});
throttle.addEventListener('pointermove',e=>{if(enginePointer!==e.pointerId)return;e.preventDefault();setEngine(engineFromY(e.clientY));});
function stopEngine(e){if(enginePointer===e.pointerId){enginePointer=null;throttle.classList.remove('pressed');}}
throttle.addEventListener('pointerup',stopEngine);throttle.addEventListener('pointercancel',stopEngine);throttle.addEventListener('lostpointercapture',stopEngine);
throttle.addEventListener('keydown',e=>{if(e.key==='ArrowUp'||e.key==='ArrowDown'){e.preventDefault();setEngine(boat.engine+(e.key==='ArrowUp'?1:-1));}if(e.key==='Home'){e.preventDefault();setEngine(0);}});
function worldFromScreen(x,y){return{x:(x-viewport.w/2)/cam.z+cam.x,y:(y-viewport.h/2)/cam.z+cam.y};}
canvas.addEventListener('pointerdown',e=>{
 if(paused||won)return;e.preventDefault();canvas.setPointerCapture(e.pointerId);canvasPointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
});
canvas.addEventListener('pointermove',e=>{
 if(!canvasPointers.has(e.pointerId))return;e.preventDefault();
 const prev=canvasPointers.get(e.pointerId),before=[...canvasPointers.values()];canvasPointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
 if(canvasPointers.size===1){
  const dx=e.clientX-prev.x,dy=e.clientY-prev.y;if(Math.abs(dx)+Math.abs(dy)<.5)return;
  cam.manual=true;cam.x-=dx/cam.z;cam.y-=dy/cam.z;
 }else if(canvasPointers.size===2){
  const after=[...canvasPointers.values()],oldDx=before[0].x-before[1].x,oldDy=before[0].y-before[1].y;
  const newDx=after[0].x-after[1].x,newDy=after[0].y-after[1].y;
  const oldDistance=Math.hypot(oldDx,oldDy),newDistance=Math.hypot(newDx,newDy);
  const oldMid={x:(before[0].x+before[1].x)/2,y:(before[0].y+before[1].y)/2};
  const newMid={x:(after[0].x+after[1].x)/2,y:(after[0].y+after[1].y)/2};
  const anchor=worldFromScreen(oldMid.x,oldMid.y);
  cam.manual=true;cam.z=clamp(cam.z*newDistance/Math.max(1,oldDistance),.55,2.1);
  cam.x=anchor.x-(newMid.x-viewport.w/2)/cam.z;cam.y=anchor.y-(newMid.y-viewport.h/2)/cam.z;
 }
 if(cam.manual)$('follow').hidden=false;
});
function endCanvasPointer(e){canvasPointers.delete(e.pointerId);}
canvas.addEventListener('pointerup',endCanvasPointer);canvas.addEventListener('pointercancel',endCanvasPointer);canvas.addEventListener('lostpointercapture',endCanvasPointer);
function physics(dt){
 if(paused||won)return;boat.time+=dt;
 const engineForce=[-3.3,-1.65,0,2.4,4.2][boat.engine+2];
 boat.u+= (engineForce-.07*boat.u-.006*boat.u*Math.abs(boat.u))*dt;
 boat.u=clamp(boat.u,-14,30);
 const maxStep=22*dt;boat.rudderActual+=clamp(boat.rudder-boat.rudderActual,-maxStep,maxStep);
 const turnTarget=.082*(boat.rudderActual/35)*clamp(boat.u/22,-.7,1.1);
 boat.r+=(turnTarget-boat.r)*(1-Math.exp(-dt/2.5));boat.a+=boat.r*dt;
 const sea=SEAS[seaIndex],gust=1+Math.sin(boat.time*.5)*.24;
 boat.v+=(-.80*boat.v-.52*boat.u*boat.r+sea.wind*gust)*dt;
 const fx=Math.cos(boat.a),fy=Math.sin(boat.a),rx=-fy,ry=fx;
 const stream=sea.current*(1+Math.sin(boat.time*.17)*.12);
 boat.gx=fx*boat.u+rx*boat.v+stream;boat.gy=fy*boat.u+ry*boat.v;
 boat.x+=boat.gx*dt;boat.y+=boat.gy*dt;
 if(!trail.length||Math.hypot(boat.x-trail[trail.length-1].x,boat.y-trail[trail.length-1].y)>4){
 trail.push({x:boat.x,y:boat.y});if(trail.length>110)trail.shift();}
 const hull=corners(),inside=hull.filter(p=>p.x>DOCK_X&&p.y>=DOCK_TOP&&p.y<=DOCK_BOTTOM),maxPen=Math.max(0,...inside.map(p=>p.x-DOCK_X));
 if(maxPen>0){
  boat.x-=maxPen+.4;
  if(boat.gx>0){boat.u-=boat.gx*fx*.92;boat.v-=boat.gx*rx*.92;}
  if(Math.abs(boat.gx)>2&&boat.time-lastCollision>1.6){boat.hits++;lastCollision=boat.time;say('船侧碰到码头，请减速调整',2700);}
 }
 let boundary=false;
 for(const p of hull){if(p.x<30){boat.x+=30-p.x;boundary=true;}if(p.x>1050){boat.x-=p.x-1050;boundary=true;}if(p.y<25){boat.y+=25-p.y;boundary=true;}if(p.y>1110){boat.y-=p.y-1110;boundary=true;}}
 if(boundary){boat.u*=.66;boat.v*=.5;if(boat.time-lastCollision>1.6){lastCollision=boat.time;boat.hits++;say('已到港区边界',1900);}}
 const gap=mooringGap(),dy=Math.abs(boat.y-BERTH.y),align=Math.abs(angleDiff(boat.a,BERTH.a));
 const berthGood=dy<42&&gap>=3&&gap<=24&&align<9*DEG&&Math.abs(boat.u)<2.4&&Math.abs(boat.v)<1.15;
 settle=berthGood?settle+dt:0;
 if(settle>1.5){
  won=true;boat.engine=0;
  const score=Math.max(1,3-Math.min(2,boat.hits)-(boat.time>170?1:0));
  $('stars').textContent='★'.repeat(score)+'☆'.repeat(3-score);
  $('result').textContent='用时 '+Math.round(boat.time)+' 秒 · 碰撞 '+boat.hits+' 次。船舶已在码头边低速停稳。';
  $('finish').hidden=false;updateControls();return;
 }
}
function updateUI(){
 if(!boat)return;const dist=distToBerth(),near=dist<205;
 $('speed').textContent=speedKn().toFixed(1)+' kn';
 $('readout').classList.toggle('ghost',!near&&performance.now()-lastInput>4000);
 $('berth').hidden=!near;
 if(near){$('gap').textContent=Math.max(0,mooringGap()/PX_PER_M).toFixed(1)+' m';$('surge').textContent=(boat.u*KNOTS_PER_WORLD).toFixed(1)+' kn';
  $('gap').classList.toggle('warning',mooringGap()<0||mooringGap()>60);
 }
 if(boat.time>4&&near&&boat.u>9&&dist<135&&performance.now()>noticeUntil+800)say('接近泊位：提前倒车，留出停车距离',2500);
 if(performance.now()>noticeUntil)$('prompt').classList.remove('show');
}
function box(x,y,w,h,color){ctx.fillStyle=color;ctx.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h));}
function strokeLine(x1,y1,x2,y2,color,w=1){ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.strokeStyle=color;ctx.lineWidth=w;ctx.stroke();}
function drawWater(){
 const left=cam.x-viewport.w/(2*cam.z)-70,right=cam.x+viewport.w/(2*cam.z)+70;
 const top=cam.y-viewport.h/(2*cam.z)-70,bottom=cam.y+viewport.h/(2*cam.z)+70;
 box(left,top,right-left,bottom-top,'#15546a');
 for(let y=Math.floor(top/38)*38;y<bottom;y+=38){
  for(let x=Math.floor(left/48)*48;x<right;x+=48){
   const wav=Math.sin(x*.027+y*.039+boat.time*.7)*2.5;
   box(x+10+wav,y+14,13,2,'#236d83');if((Math.floor(x/48)+Math.floor(y/38))%3===0)box(x+25,y+21,7,2,'#34768a');
  }
 }
}
function drawPier(){
 box(DOCK_X+5,DOCK_TOP,480,DOCK_BOTTOM-DOCK_TOP,'#53646a');
 box(DOCK_X,DOCK_TOP,480,DOCK_BOTTOM-DOCK_TOP,'#8b9086');box(DOCK_X,DOCK_TOP,5,DOCK_BOTTOM-DOCK_TOP,'#decda0');
 box(DOCK_X+19,DOCK_TOP+9,440,DOCK_BOTTOM-DOCK_TOP-18,'#828c84');
 for(let y=DOCK_TOP+13;y<DOCK_BOTTOM-10;y+=44){
  box(DOCK_X+8,y,9,18,'#e4bf68');box(DOCK_X+22,y+29,390,2,'#6a7773');
 }
 // Lines, cargo and shore furniture
 for(const [x,y,c] of [[759,228,'#ba765a'],[801,228,'#a6b5a4'],[759,263,'#668c94'],[810,475,'#ba765a'],[850,475,'#718f82'],[782,515,'#bf9d63']]){
  box(x,y,52,26,'#46585a');box(x+2,y+2,48,21,c);
  for(let k=5;k<45;k+=8)box(x+k,y+5,2,14,'#d7d6bd55');
 }
 for(let y=DOCK_TOP+43;y<DOCK_BOTTOM-30;y+=95){box(DOCK_X+1,y,10,15,'#293e45');box(DOCK_X+1,y+2,4,8,'#d6bd70');}
 box(DOCK_X+72,DOCK_TOP+32,8,178,'#58696c');box(DOCK_X+60,DOCK_TOP+38,31,6,'#dfbc70');
}
function drawBerth(){
 const x=BERTH.x-18,y=BERTH.y-63;
 ctx.fillStyle='rgba(244,208,130,.075)';ctx.fillRect(x,y,36,126);
 ctx.strokeStyle='rgba(248,221,154,.85)';ctx.lineWidth=2;ctx.setLineDash([8,7]);ctx.strokeRect(x,y,36,126);ctx.setLineDash([]);
 for(const yy of [BERTH.y-59,BERTH.y+59]){box(DOCK_X-5,yy,10,8,'#e4c47b');}
 ctx.fillStyle='#ebdda8';ctx.font='bold 12px monospace';ctx.textAlign='right';ctx.fillText('泊位 A1',DOCK_X-12,BERTH.y-73);
}
function drawTrail(){
 if(trail.length<2)return;ctx.beginPath();trail.forEach((p,i)=>{if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);});
 ctx.strokeStyle='rgba(176,226,219,.32)';ctx.lineWidth=2;ctx.stroke();
}
function drawStopMark(){
 if(!$('assist').checked||distToBerth()>255||boat.u<3)return;
 let u=boat.u,d=0;
 for(let t=0;t<20&&u>0;t+=.1){const force=-3.3-.07*u-.006*u*Math.abs(u);u=Math.max(0,u+force*.1);d+=u*.1;}
 const fx=Math.cos(boat.a),fy=Math.sin(boat.a),x=boat.x+fx*d,y=boat.y+fy*d;
 ctx.beginPath();ctx.moveTo(boat.x,boat.y);ctx.lineTo(x,y);ctx.strokeStyle='rgba(248,212,143,.63)';ctx.lineWidth=2;ctx.setLineDash([4,6]);ctx.stroke();ctx.setLineDash([]);
 strokeLine(x-8,y-8,x+8,y+8,'#f2cf80',2);strokeLine(x+8,y-8,x-8,y+8,'#f2cf80',2);
 ctx.fillStyle='#f4ddb2';ctx.font='10px sans-serif';ctx.textAlign='center';ctx.fillText('倒车停车估计',x,y+20);
}
function drawShip(){
 ctx.save();ctx.translate(boat.x,boat.y);ctx.rotate(boat.a+Math.PI/2);
 // A compact coastal harbor vessel (about 23m), not a giant cargo ship.
 ctx.fillStyle='#203b48';ctx.beginPath();ctx.moveTo(-15,44);ctx.lineTo(15,44);ctx.lineTo(15,-31);ctx.lineTo(10,-45);ctx.lineTo(0,-55);ctx.lineTo(-10,-45);ctx.lineTo(-15,-31);ctx.closePath();ctx.fill();
 ctx.fillStyle='#e4e2d0';ctx.fillRect(-11,-30,22,67);
 box(-10,-27,20,18,'#be7660');box(-10,-5,20,16,'#af986c');box(-10,15,20,17,'#839789');
 box(-9,30,18,11,'#f0ebdd');box(-7,30,14,6,'#5b96a5');box(-4,-45,8,11,'#e8cda0');
 box(-12,41,24,3,'#f0f0e3');
 if(Math.abs(boat.u)>2){const wash=clamp(Math.abs(boat.u)*.5,4,22),color=boat.u>=0?'#9dd5dd':'#70b0c3';box(-wash/2,49,wash,3,color);box(-wash*.38,57,wash*.76,2,'#6daec1');}
 // actual rudder is distinct from the commanded virtual wheel
 const ra=boat.rudderActual*DEG;
 strokeLine(0,44,Math.sin(ra)*17,44+Math.cos(ra)*17,'#e8c679',2);
 ctx.restore();
}
function render(){
 const {w,h,dpr}=viewport;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#174d62';ctx.fillRect(0,0,w,h);
 ctx.save();ctx.translate(w/2,h/2);ctx.scale(cam.z,cam.z);ctx.translate(-cam.x,-cam.y);
 drawWater();drawTrail();drawPier();drawBerth();drawStopMark();drawShip();
 ctx.restore();
 // Mild vignette improves contrast under translucent controls without masking the scene.
 const grad=ctx.createLinearGradient(0,h*.65,0,h);grad.addColorStop(0,'rgba(7,27,37,0)');grad.addColorStop(1,'rgba(7,27,37,.28)');ctx.fillStyle=grad;ctx.fillRect(0,h*.65,w,h*.35);
}
function frame(timestamp){
 if(!lastFrame)lastFrame=timestamp;const dt=Math.min(.05,Math.max(0,(timestamp-lastFrame)/1000));lastFrame=timestamp;
 if(!document.hidden){
  if(!paused&&!won){const count=Math.max(1,Math.ceil(dt/.016));for(let i=0;i<count;i++)physics(dt/count);}
  updateCamera(dt);render();
  if(timestamp-drawClock>110){drawClock=timestamp;updateUI();}
 }
 requestAnimationFrame(frame);
}
window.addEventListener('resize',resize);window.addEventListener('orientationchange',resize);
resize();reset();requestAnimationFrame(frame);
})();