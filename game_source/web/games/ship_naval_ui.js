// Naval mode is a thin presentation layer over the Siege battlefield.
// The same canvas, input/panning, replay, HUD, effects, items and networking are retained.
let navalMoveMode=false,navalTouch=null,navalMoveId=-1,navalMoveStart=0,navalInitialAim='';
const navalTools=document.createElement('div');
navalTools.id='navalTools';navalTools.className='hidden';
navalTools.innerHTML='<button type="button" id="navalShoot" aria-pressed="true">开炮</button><button type="button" id="navalMove" aria-pressed="false">移动</button><span id="navalHint">本回合选择一项行动</span>';
$('game').append(navalTools);
const navalStyle=document.createElement('style');
navalStyle.textContent=`
#navalTools{position:absolute;z-index:4;bottom:calc(124px + env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:6px;max-width:calc(100vw - 16px);background:#123344c7;border:1px solid #c5e5db55;padding:5px;border-radius:13px;backdrop-filter:blur(6px);white-space:nowrap}
#navalTools button{padding:8px 15px;min-height:37px;font-size:13px;background:transparent;color:#e5f4ef;border:1px solid transparent;border-radius:9px}
#navalTools button.active{background:#dce9d0;color:#213d40}
#navalHint{font-size:10px;color:#c2d8d8;padding:0 6px}
#game.naval.move-mode #controls{display:none}
#game.naval #windInfo,#game.naval #trialLink,#game.naval #stockSave,#game.naval #stockLoad{display:none!important}
#game.naval .seat .buff{max-height:29px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
#game.naval #status{bottom:calc(178px + env(safe-area-inset-bottom))}
#game.naval.move-mode #status{bottom:calc(190px + env(safe-area-inset-bottom))}
@media(max-width:360px){#navalTools{bottom:calc(137px + env(safe-area-inset-bottom))}#navalHint{display:none}}
@media(orientation:landscape) and (max-height:520px){#navalTools{bottom:calc(65px + env(safe-area-inset-bottom))}#navalHint{display:none}#game.naval #status{bottom:calc(112px + env(safe-area-inset-bottom))}}
`;
document.head.append(navalStyle);
$('navalShoot').onclick=()=>{navalMoveMode=false;navalModeView();};
$('navalMove').onclick=()=>{if(!canAim())return;navalMoveMode=true;closePanels();navalModeView();};
function navalModeView(){
 const active=!!room?.naval,can=active&&canAim();
 navalTools.classList.toggle('hidden',!active);
 $('game').classList.toggle('naval',active);
 $('game').classList.toggle('move-mode',active&&navalMoveMode);
 $('navalShoot').classList.toggle('active',!navalMoveMode);
 $('navalMove').classList.toggle('active',navalMoveMode);
 $('navalShoot').setAttribute('aria-pressed',String(!navalMoveMode));
 $('navalMove').setAttribute('aria-pressed',String(navalMoveMode));
 $('navalMove').disabled=!can;
 $('navalHint').textContent=navalMoveMode?'点击圆圈内目的地':'本回合开炮或移动';
 if(active&&room?.phase==='play'&&!can&&navalMoveMode){navalMoveMode=false;$('game').classList.remove('move-mode')}
}
async function navalAttemptMove(pt){
 if(!room?.naval||!canAim()||!navalMoveMode)return;
 const [sx,sy]=launcher(room.seat),dist=Math.hypot(pt[0]-sx,pt[1]-sy);
 if(dist>room.moveRadius+1||dist<8){notice='请选择圆圈内部其他位置';update();return;}
 requesting=true;navalMoveMode=false;navalModeView();update();
 try{
  const d=await req('move',{x:pt[0],y:pt[1],rev});
  if(!d.ok)throw Error(d.error||'移动失败');
  apply(d);notice='';
 }catch(e){notice=e.message;navalMoveMode=true;update();}
 finally{requesting=false;update();}
}
const navalOriginalUpdate=update;
update=function(){
 if(room?.naval&&navalInitialAim!==room.code){navalInitialAim=room.code;angle=0;power=70;}
 navalOriginalUpdate();
 if(room?.naval&&room.phase!=='play')navalMoveMode=false;
 navalModeView();
 if(room?.naval){
  $('turn').textContent=room.phase==='over'?'海战结束':playing?'炮弹飞行':room.busy?'行动交接':room.turn===room.seat?'你的回合 · 开炮或移动':'对方回合';
  $('fire').textContent='开炮';
  if($('navalMove').classList.contains('active'))$('status').textContent=notice||'点击船舶周围的半透明圆圈，移动会结束本回合';
 }
};
const navalStandardScene=scene;
scene=function(t){
 if(!room?.naval)return navalStandardScene(t);
 const ocean='#155a70';
 rect(0,-1800,960,3600,ocean);
 for(let y=-1200;y<1700;y+=39)for(let x=8;x<960;x+=54){
  const o=Math.sin((x+y)*.025+t*.0007)*5;
  rect(x+o,y+12,13,2,'#2c7890');if((Math.floor(x/54)+Math.floor(y/39))%3===0)rect(x+21,y+18,6,2,'#1f6e85');
 }
 // Coastline is decorative, unlike the old gravity-driven ground.
 rect(0,2,960,14,'#5c8f91');rect(0,401,960,15,'#5c8f91');
 for(let x=12;x<960;x+=52){rect(x,5,25,4,'#c3ba8a');rect(x,404,25,4,'#c3ba8a');}
 for(let x=104;x<940;x+=82){rect(x,235,26,2,'#a8d7d143');}
 // Ship bodies use the same authoritative cannon positions as the Siege engine.
 for(let side=0;side<2;side++){
  const b=room.bodies.find(b=>b.kind==='cannon'&&b.side===side);
  if(!b)continue;
  let x=b.x,y=b.y-24,heading=side===0?0:Math.PI;
  const move=room.navalMove;
  if(move&&move.seat===side){
   if(move.id!==navalMoveId){navalMoveId=move.id;navalMoveStart=performance.now();}
   const q=clamp((performance.now()-navalMoveStart)/(move.duration*1000),0,1),smooth=q*q*(3-2*q);
   if(move.id===room.rev&&q<1){x=move.from[0]+(move.to[0]-move.from[0])*smooth;y=move.from[1]+(move.to[1]-move.from[1])*smooth;heading=Math.atan2(move.to[1]-move.from[1],move.to[0]-move.from[0]);}
  }
  ctx.save();ctx.translate(x,y);ctx.rotate(heading+Math.PI/2);
  // Reusable pixel ship sprite: cannon body is only rendered differently.
  ctx.fillStyle='#183746';ctx.beginPath();ctx.moveTo(0,-26);ctx.lineTo(10,-18);ctx.lineTo(13,12);ctx.lineTo(10,23);ctx.lineTo(-10,23);ctx.lineTo(-13,12);ctx.lineTo(-10,-18);ctx.closePath();ctx.fill();
  rect(-9,-15,18,29,side===0?'#e0d4b8':'#c2d5e0');rect(-7,-11,14,8,side===0?'#c88c63':'#648faf');rect(-6,2,12,9,'#e5e9df');rect(-4,3,8,4,'#6795a6');
  ctx.restore();
  if(side===room.seat&&canAim()&&!navalMoveMode){
   const a=angle*Math.PI/180,d=gunDirection(side);
   line(x,y,x+60*d*Math.cos(a),y-60*Math.sin(a),'#f6e8ae',2);
  }
 }
 if(navalMoveMode&&canAim()&&!playing){
  const [x,y]=launcher(room.seat),rad=room.moveRadius;
  ctx.save();ctx.fillStyle='rgba(131,216,206,.10)';ctx.strokeStyle='#9bdfd0';ctx.lineWidth=2;ctx.setLineDash([8,6]);
  ctx.beginPath();ctx.arc(x,y,rad,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#e0f0de';ctx.textAlign='center';ctx.font='bold 12px system-ui';ctx.fillText('点击圆圈内移动',x,y-rad-12);ctx.restore();
 }
};
const navalStandardBlock=block;
block=function(b,x,y,hp){
 if(!room?.naval||hp<=0)return navalStandardBlock(b,x,y,hp);
 if(b.kind==='cannon')return;
 ctx.save();
 if(b.kind==='core'){
  ctx.translate(x,y);
  ctx.fillStyle='#2b5762';ctx.beginPath();ctx.arc(0,0,47,0,7);ctx.fill();
  rect(-b.w/2,-b.h/2,b.w,b.h,b.side===0?'#9f8c6b':'#688b9c');
  rect(-b.w/2+6,-b.h/2+7,b.w-12,b.h-14,'#d4c8a5');
  rect(-13,-16,26,32,b.side===0?'#bd795b':'#668cab');
  ctx.fillStyle='#f3e9c9';ctx.textAlign='center';ctx.font='bold 13px system-ui';ctx.fillText('子滩',0,4);
  rect(-b.w/2,-b.h/2-12,b.w,5,'#233e47');rect(-b.w/2,-b.h/2-12,b.w*clamp(hp/b.max,0,1),5,'#bedec8');
 }else if(b.kind==='stone'){
  ctx.translate(x,y);ctx.fillStyle='#3f7783';ctx.beginPath();ctx.ellipse(0,0,b.w*.7,b.h*.68,0,0,7);ctx.fill();
  ctx.fillStyle='#929e8a';ctx.beginPath();ctx.ellipse(0,0,b.w*.52,b.h*.49,.3,0,7);ctx.fill();
  rect(-10,-6,16,6,'#d0cda5');
 }else{ctx.restore();return navalStandardBlock(b,x,y,hp)}
 ctx.restore();
};
