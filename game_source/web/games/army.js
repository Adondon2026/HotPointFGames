// Board coordinates remain canonical; each player's own side is displayed below.
const armyRanks=['司令','军长','师长','旅长','团长','营长','连长','排长','工兵','地雷','炸弹','军旗'];
const armyNodes=Array.from({length:60},(_,i)=>[Math.floor(i/5),i%5]).concat(['ML','MR']);
const armyKey=n=>JSON.stringify(n);const armyCamp=new Set([[2,1],[2,3],[3,2],[4,1],[4,3],[9,1],[9,3],[8,2],[7,1],[7,3]].map(armyKey));const armyHQ=new Set([[0,1],[0,3],[11,1],[11,3]].map(armyKey));
let armySelected=null,armyMatch=null,armyBoardKey='',armyMarkTarget=null,armyMarkMode=false,armyMarks={},armyReplayIndex=null;
// Animate public frames rather than guessing from the latest board. No rank inference.
let armyFxMatch=null,armyFxSeen=null,armyFxQueue=[],armyFx=null,armyFxTimer=null,armyFxStage='',armyFxLast=null,armyFxInitialized=false;
function armyFxClear(){clearTimeout(armyFxTimer);armyFxTimer=null;armyFxQueue=[];armyFx=null;armyFxStage='';armyFxLast=null;armyBoardKey='';}
function armyFxBusy(){return !!armyFx||armyFxQueue.length>0}
// Keep the two participants visible until the outcome has been read.
const armyFxDurations={approach:430,clash:450,result:720,settle:650,move:260,moveResult:160};
function armyFxStep(){
 if(armyFx||!armyFxQueue.length)return;
 armyFx=armyFxQueue.shift();armyFxStage='approach';armyFxLast=null;armyBoardKey='';
 const battle=armyFx.battle;
 const stages=battle?[['clash',armyFxDurations.approach],['result',armyFxDurations.clash],['settle',armyFxDurations.result],['done',armyFxDurations.settle]]:[['result',armyFxDurations.move],['done',armyFxDurations.moveResult]];
 const next=()=>{const [stage,ms]=stages.shift();armyFxTimer=setTimeout(()=>{armyFxStage=stage;armyBoardKey='';if(stage==='done'){armyFxLast=armyFx;armyFx=null;armyFxStage='';armyFxStep()}else next();renderSafe()},ms)};
 next();
}
function armyFxSync(v){const events=v.presentation||[],last=events.at(-1);if(armyFxMatch!==v.match){armyFxClear();armyFxMatch=v.match;armyFxSeen=null;armyFxInitialized=false}if(v.phase==='setup'){armyFxClear();armyFxSeen=null;armyFxInitialized=true;return}if(!armyFxInitialized){armyFxInitialized=true;armyFxSeen=last?.id??null;armyFxLast=last||null;return}if(!last){if(armyFxSeen!==null)armyFxClear();armyFxSeen=null;return}if(last.id===armyFxSeen)return;let start=events.findIndex(e=>e.parent===armyFxSeen);if(start<0||document.hidden){armyFxClear();armyFxSeen=last.id;armyFxLast=last;return}armyFxQueue.push(...events.slice(start));armyFxSeen=last.id;armyFxStep()}
function armyFxLabel(e,owner){if(!e)return '';const a=e.player===owner,own=a?'我方':'敌方',other=a?'敌方':'我方';const piece=e.before.pieces.find(p=>armyKey(p.node)===armyKey(e.src)),target=e.before.pieces.find(p=>armyKey(p.node)===armyKey(e.dst));const label=(side,p)=>side+(p&&p.rank!=='UNKNOWN'?p.rank:'棋子');const A=label(own,piece),D=label(other,target);return {attacker:`${A} 吃掉 ${D}`,defender:`${D} 吃掉 ${A}`,both:`${A} 与 ${D} 同归于尽`,capture_flag:`${A} 攻占军旗`,pick_flag:`${A} 夺旗`,return_flag:`${A} 背回军旗`,move:`${A} 移动`}[e.result]||''}
// A non-overlapping contact pair, oriented along the last leg of the move.
function armyFxContact(dst,prev,horizontal){
 const w=horizontal?6.7:16,h=horizontal?13:5.1;
 const dx=prev[0]-dst[0],dy=prev[1]-dst[1],axis=Math.abs(dx)/w>=Math.abs(dy)/h?0:1;
 const gap=(axis===0?w:h)*1.12,sign=Math.sign(axis===0?dx:dy)||1;
 const pad=(axis===0?w:h)/2+1;
 const a=[...dst],d=[...dst];
 a[axis]+=sign*gap;
 if(a[axis]<pad||a[axis]>100-pad){
  a[axis]=Math.max(pad,Math.min(100-pad,a[axis]));d[axis]=a[axis]-sign*gap;
 }
 return {a,d,axis};
}
function armyFxOutcome(e,owner){
 const both=e.result==='both';
 const winner=both?null:e.result==='defender'?1-e.player:e.player;
 return {both,winner,caption:both?'同归于尽':e.result==='capture_flag'?'攻占军旗':e.result==='pick_flag'?'夺取军旗':e.result==='return_flag'?'背回军旗':winner===owner?'我方吃子':'敌方吃子'};
}
function armyFxOverlay(board,e,owner){
 if(!e)return;
 const [x,y]=armyPosition(e.src,owner),dst=armyPosition(e.dst,owner),p=e.before.pieces.find(p=>armyKey(p.node)===armyKey(e.src)),d=e.before.pieces.find(p=>armyKey(p.node)===armyKey(e.dst));
 const nodes=e.path.map(n=>armyPosition(n,owner)),prev=nodes.at(-2)||[x,y],contact=armyFxContact(dst,prev,armyHorizontal()),a=contact.a,b=contact.d;
 const ghost=(piece,pos,cls,role)=>{
  if(!piece)return null;
  const el=document.createElement('div');el.className='army-node piece army-fx-ghost '+(piece.owner===owner?'own':'enemy')+' '+cls;el.textContent=piece.rank==='UNKNOWN'?'':piece.rank;el.style.left=pos[0]+'%';el.style.top=pos[1]+'%';
  if(piece.carrying_flag){const f=document.createElement('span');f.className='army-flag';f.textContent='⚑';el.append(f)}
  if(role){const mark=document.createElement('span');mark.className='army-fx-role'+(contact.axis===1?(pos[0]>55?' side-left':' side-right'):'');mark.textContent=role;el.append(mark)}
  if(cls.includes('loser')){const cross=document.createElement('span');cross.className='army-fx-cross';cross.textContent='×';el.append(cross)}
  board.append(el);return el;
 };
 const move=(el,points,duration)=>{
  if(!el)return;const end=points.at(-1);el.style.setProperty('--fx-x',end[0]+'%');el.style.setProperty('--fx-y',end[1]+'%');
  el.style.setProperty('--fx-duration',duration+'ms');
  if(el.animate&&!matchMedia('(prefers-reduced-motion: reduce)').matches){el.animate(points.map(([l,t])=>({left:l+'%',top:t+'%'})),{duration,easing:'ease-in-out',fill:'forwards'})}
 };
 const caption=(txt,kind,pos)=>{
  const el=document.createElement('div');el.className='army-fx-caption '+kind;el.textContent=txt;
  // Place below/above the pair, not on either piece; keep inside the board.
  const mid=(a[0]+b[0])/2, top=Math.min(a[1],b[1]),bottom=Math.max(a[1],b[1]),offset=armyHorizontal()?13:8;
  const y=bottom+offset<=94?bottom+offset:top-offset;
  el.style.left=Math.max(23,Math.min(77,pos?pos[0]:mid))+'%';el.style.top=Math.max(6,Math.min(94,y))+'%';board.append(el);
 };
 if(armyFxStage==='approach'&&p){
  const end=e.battle?a:dst,el=ghost(p,[x,y],'moving','');
  // Preserve the real railway path before the final contact offset.
  move(el,nodes.slice(0,-1).concat([end]),e.battle?410:245);
  if(e.battle&&d)ghost(d,dst,'defending','');
 }
 if(armyFxStage==='clash'&&p&&d){
  ghost(p,a,'duelist attacker','进攻');ghost(d,b,'duelist defender','防守');
  caption('交战','clash');
 }
 if(armyFxStage==='result'&&e.battle){
  const outcome=armyFxOutcome(e,owner);
  const style=piece=>outcome.both||piece.owner!==outcome.winner?'duelist loser':'duelist survivor';
  if(p)ghost(p,a,style(p),'进攻');if(d)ghost(d,b,style(d),'防守');
  caption(outcome.caption,outcome.both?'mutual':'decided');
 }
 if(armyFxStage==='settle'&&e.battle){
  const outcome=armyFxOutcome(e,owner),survivor=e.after.pieces.find(p=>armyKey(p.node)===armyKey(e.dst));
  if(survivor){const start=survivor.id===p?.id?a:b;move(ghost(survivor,start,'moving survivor',''),[start,dst],260)}
  const mark=document.createElement('div');mark.className='army-fx-ring '+(outcome.both?'mutual':'resolved');mark.style.left=dst[0]+'%';mark.style.top=dst[1]+'%';mark.textContent=outcome.both?'××':'';board.append(mark);
  caption(outcome.caption,outcome.both?'mutual':'decided',dst);
 }
}
function armyIsSetup(){return state?.army?.phase==='setup'}function armyHorizontal(){return !armyIsSetup()&&matchMedia('(orientation:landscape) and (max-height:520px) and (min-width:540px)').matches}function armyPosition(n,owner){if(owner===0)n=typeof n==='string'?(n==='ML'?'MR':'ML'):[11-n[0],4-n[1]];const [x,y]=typeof n==='string'?[n==='ML'?29:71,50]:[10+n[1]*20,4.2+n[0]*7.9+(n[0]>=6?4.7:0)];return armyIsSetup()?[x,(y-52)*2.05]:armyHorizontal()?[100-y,x]:[x,y]}
function armyEdges(){const edges=[];const add=(a,b,rail=false)=>edges.push([a,b,rail]);for(const [start,end] of [[0,5],[6,11]]){for(let r=start;r<=end;r++)for(let c=0;c<4;c++)add([r,c],[r,c+1],[1,5,6,10].includes(r));for(let r=start;r<end;r++)for(let c=0;c<5;c++)add([r,c],[r+1,c],(c===0||c===4)&&r>=1&&r<=9)}for(const c of [0,2,4])add([5,c],[6,c],true);for(const k of armyCamp){const [r,c]=JSON.parse(k);for(const dr of [-1,1])for(const dc of [-1,1])add([r,c],[r+dr,c+dc])}return edges}
function armySeat(el,p,active,txt){el.classList.toggle('active',active);el.replaceChildren();const b=document.createElement('b');b.textContent=p?.name||'玩家';const s=document.createElement('span');s.textContent=txt;el.append(b,s)}
function armyCanAct(v){return !armyFxBusy()&&v.phase==='play'&&v.turn===v.owner&&!v.pending_request&&armyReplayIndex===null}
async function armyClick(n){const v=state.army;if(!v||armyReplayIndex!==null||armyFxBusy())return;const k=armyKey(n),p=v.pieces.find(p=>armyKey(p.node)===k);if(armyMarkMode&&v.phase==='play'&&p&&p.owner!==v.owner&&p.rank==='UNKNOWN'&&v.room_rules.allow_annotations){armyMarkTarget=p.id;$('armyMark').classList.remove('hidden');const mark=armyMarks[p.id];$('armyOp').value=mark?.op||'?';$('armyRank').value=mark?.rank||'司令';return}if(v.phase==='setup'&&!v.ready[v.owner]){if(!p||p.owner!==v.owner)return;if(armySelected===null){armySelected=k;renderArmy();return}if(armySelected===k){armySelected=null;renderArmy();return}const src=JSON.parse(armySelected);armySelected=null;await action('army_swap',{src,dst:n});return}if(!armyCanAct(v))return;if(p?.owner===v.owner){armySelected=armySelected===k?null:k;renderArmy();return}if(armySelected){const allowed=v.legal.find(x=>armyKey(x.src)===armySelected)?.dst||[];if(!allowed.some(x=>armyKey(x)===k))return;const src=JSON.parse(armySelected);armySelected=null;await action('army_move',{src,dst:n})}}
function renderArmy(){const v=state?.army;if(!v)return;if(v.match!==armyMatch){armyMatch=v.match;armySelected=null;armyMarkTarget=null;armyMarkMode=false;armyReplayIndex=null;armyMarks={};$('armyMark').classList.add('hidden');$('armyMenu').classList.add('hidden');armyBoardKey=''}if(!v.room_rules.allow_annotations){armyMarks={};armyMarkMode=false}$('armyGame').dataset.stage=v.phase;const owner=v.owner,replaying=armyReplayIndex!==null,frames=v.replay_full||[],frame=replaying?frames[armyReplayIndex]?.frame:null,showMode=$('armyReplayMode').value,fx=!replaying?armyFx:null,fxFrame=fx?((armyFxStage==='settle'||(!fx.battle&&armyFxStage==='result'))?fx.after:fx.before):null,pieces=fxFrame?fxFrame.pieces:frame?frame.pieces.map(p=>({...p,rank:showMode==='all'?p.rank:showMode==='hidden'?'UNKNOWN':p.owner===owner||p.revealed_to?.includes(owner)?p.rank:'UNKNOWN'})):v.pieces,flags=fxFrame?.ground_flags||frame?.ground_flags||v.ground_flags,trace=fx?{path:fx.path}:frame?.last_move_trace||v.last_move_trace;
 if(armySelected&&!pieces.some(p=>armyKey(p.node)===armySelected&&p.owner===owner))armySelected=null;const legal=armySelected&&armyCanAct(v)?v.legal.find(x=>armyKey(x.src)===armySelected)?.dst||[]:[];const valid=new Set(legal.map(armyKey)),path=trace?.path||[],last=new Set(path.length?[armyKey(path[0]),armyKey(path.at(-1))]:[]);const by=new Map(pieces.map(p=>[armyKey(p.node),p]));const key=JSON.stringify([owner,pieces,flags,path,armySelected,[...valid],armyMarks,v.room_rules.mountains,replaying,armyHorizontal(),v.phase,fx?.id,armyFxStage]);if(key!==armyBoardKey){armyBoardKey=key;const board=$('armyBoard');board.replaceChildren();const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 100 100');svg.setAttribute('preserveAspectRatio','none');const line=(a,b,color,w,dash)=>{const e=document.createElementNS(svg.namespaceURI,'line'),[x,y]=armyPosition(a,owner),[xx,yy]=armyPosition(b,owner);for(const [k,v] of Object.entries({x1:x,y1:y,x2:xx,y2:yy,stroke:color,'stroke-width':w}))e.setAttribute(k,v);if(dash)e.setAttribute('stroke-dasharray',dash);svg.append(e)};const inSetup=n=>Array.isArray(n)&&(owner===0?n[0]<=5:n[0]>=6);for(const [a,b,rail] of armyEdges())if(!armyIsSetup()||inSetup(a)&&inSetup(b))line(a,b,rail?'#a9bda3':'#577a61',rail?.85:.42,rail?'1.3 .8':null);for(let i=1;i<path.length;i++)line(path[i-1],path[i],'#f1c66d',.9);board.append(svg);for(const n of armyNodes){if(armyIsSetup()&&!inSetup(n))continue;if(typeof n==='string'&&!v.room_rules.mountains)continue;const k=armyKey(n),p=fx&&((armyFxStage==='approach'&&(k===armyKey(fx.src)||(fx.battle&&k===armyKey(fx.dst))))||(fx.battle&&['clash','result'].includes(armyFxStage)&&(k===armyKey(fx.src)||k===armyKey(fx.dst)))||(fx.battle&&armyFxStage==='settle'&&k===armyKey(fx.dst)))?null:by.get(k),[x,y]=armyPosition(n,owner),b=document.createElement('button');b.type='button';b.className='army-node'+(armyCamp.has(k)?' camp':armyHQ.has(k)?' hq':typeof n==='string'?' mountain':'')+(p?' piece '+(p.owner===owner?'own':'enemy'):'')+(armySelected===k?' selected':'')+(valid.has(k)?' legal':'')+(last.has(k)?' last':'');b.style.left=x+'%';b.style.top=y+'%';const mark=p&&p.rank==='UNKNOWN'&&!replaying?armyMarks[p.id]:null;if(p&&p.rank!=='UNKNOWN')delete armyMarks[p.id];b.textContent=p?(p.rank==='UNKNOWN'?(mark&&mark.op!=='?'?mark.op+mark.rank:''):p.rank):armyCamp.has(k)?'营':armyHQ.has(k)?'本营':typeof n==='string'?'山':' ';const flag=flags.some(f=>armyKey(f.node)===k);if(p?.carrying_flag||flag){const f=document.createElement('span');f.className='army-flag';f.textContent='⚑';b.append(f)}b.setAttribute('aria-label',(p?.rank==='UNKNOWN'&&!b.textContent.trim()?'暗棋':b.textContent)+' '+(typeof n==='string'?n:n.join(',')));b.dataset.node=k;b.onclick=()=>armyClick(n);board.append(b)}if(fx)armyFxOverlay(board,fx,owner)}
 const own=state.players.find(p=>p.id===v.seats[owner]),opp=state.players.find(p=>p.id===v.seats[1-owner]);const setup=v.phase==='setup',mine=setup?!v.ready[owner]:armyCanAct(v);$('armyStatus').textContent=replaying?'复盘':fx?(armyFxStage==='approach'?(fx.player===owner?'我方行棋':'敌方行棋'):armyFxStage==='clash'?'交战中':fx.battle||fx.result!=='move'?'战斗结果':'行棋完成'):setup?(v.ready[owner]?'等待对方布阵':'调整布阵'):v.phase==='over'?(v.draw?'和棋':v.winner===owner?'你获胜':'本局结束'):v.pending_request?'等待请求处理':mine?'轮到你 · 选择棋子':'对方回合';$('armyStatus').classList.toggle('my-turn',mine&&!replaying);armySeat($('armyOpponent'),opp,!replaying&&v.phase==='play'&&(fx?fx.player!==owner:v.turn!==owner),setup?(v.ready[1-owner]?'已准备':'布阵中'):`${pieces.filter(p=>p.owner!==owner).length} 枚棋子`);armySeat($('armySelf'),own,(fx?fx.player===owner:mine)&&!replaying,setup?(v.ready[owner]?'已准备':'布阵中'):`${pieces.filter(p=>p.owner===owner).length} 枚棋子`);$('armySetup').classList.toggle('hidden',!setup||v.ready[owner]);$('armyNotice').classList.toggle('army-battle-result',!!(fx&&['result','settle'].includes(armyFxStage)&&fx.battle));$('armyNotice').textContent=fx?(armyFxStage==='approach'?(fx.player===owner?'我方棋子正在移动':'敌方棋子正在移动'):armyFxStage==='clash'?'双方交战':armyFxLabel(fx,owner)):replaying?(frame?.message||''):setup?(v.ready[owner]?'已确认布阵，等待对方':armySelected?'选择另一枚棋子交换':'已生成合法布阵，可自由调整'):(armyFxLast?armyFxLabel(armyFxLast,owner):v.logs.at(-1)||v.message);const req=v.pending_request;$('armyRequest').classList.toggle('hidden',!req||req.from===owner);$('armyRequestText').textContent=req?.type==='undo'?'对方请求悔棋':'对方请求和棋';$('armyUndo').classList.toggle('hidden',v.phase!=='play');$('armyDraw').classList.toggle('hidden',v.phase!=='play');$('armyResign').classList.toggle('hidden',v.phase!=='play');$('armyMarkMode').classList.toggle('hidden',v.phase!=='play'||!v.room_rules.allow_annotations);$('armyMarkMode').textContent=armyMarkMode?'退出标记':'标记暗棋';$('armyLogs').replaceChildren(...(v.logs||[]).slice().reverse().map(t=>{const el=document.createElement('div');el.textContent=t;return el}));$('armyReplay').classList.toggle('hidden',!replaying);if(replaying){const f=frames[armyReplayIndex];$('armyReplayLabel').textContent=`第 ${f.label} 步 · ${f.active_branch?'主线':'悔棋分支'}`;$('armyPrev').disabled=armyReplayIndex<=0;$('armyNext').disabled=armyReplayIndex>=frames.length-1}}
for(const [id,type] of [['armyRandom','army_random'],['armyReady','army_setup']])$(id).onclick=()=>{armySelected=null;action(type)};$('armyMenuBtn').onclick=()=>$('armyMenu').classList.toggle('hidden');$('armyRules').onclick=()=>{$('armyMenu').classList.add('hidden');liteRules()};$('armyUndo').onclick=()=>{$('armyMenu').classList.add('hidden');action('army_request',{kind:'undo'})};$('armyDraw').onclick=()=>{$('armyMenu').classList.add('hidden');action('army_request',{kind:'draw'})};$('armyResign').onclick=()=>{if(confirm('确定认输？'))action('army_resign')};$('armyAccept').onclick=()=>action('army_respond',{accept:true});$('armyReject').onclick=()=>action('army_respond',{accept:false});$('armyMarkMode').onclick=()=>{armyMarkMode=!armyMarkMode;$('armyMenu').classList.add('hidden');$('armyMark').classList.add('hidden');renderArmy()};$('armyRank').replaceChildren(...armyRanks.map(r=>{const o=document.createElement('option');o.textContent=r;return o}));$('armySaveMark').onclick=()=>{if(armyMarkTarget!==null){const op=$('armyOp').value;if(op==='?')delete armyMarks[armyMarkTarget];else armyMarks[armyMarkTarget]={op,rank:$('armyRank').value}}$('armyMark').classList.add('hidden');armyMarkTarget=null;renderArmy()};for(const id of ['armyVictory','armyFirst','armyMountains','armyAnnotations'])$(id).onchange=()=>action('army_settings',{victory:$('armyVictory').value,first:$('armyFirst').value,mountains:$('armyMountains').checked,annotations:$('armyAnnotations').checked});
$('armyPrev').onclick=()=>{armyReplayIndex=Math.max(0,armyReplayIndex-1);renderArmy()};$('armyNext').onclick=()=>{armyReplayIndex=Math.min(state.army.replay_full.length-1,armyReplayIndex+1);renderArmy()};$('armyReplayMode').onchange=renderArmy;$('armyCloseReplay').onclick=()=>{armyReplayIndex=null;renderSafe()};
const armyRenderBase=render;render=function(){if(state?.mode==='army'&&state.army&&state.phase!=='lobby'){if(armyReplayIndex===null)armyFxSync(state.army)}else if(armyFxMatch!==null){armyFxClear();armyFxMatch=null;armyFxInitialized=false}armyRenderBase();if(state?.mode!=='army'){if($('armyReplayOpen'))$('armyReplayOpen').classList.add('hidden');return;}if(state.phase==='lobby'){armyReplayIndex=null;const s=state.settings;$('armyVictory').value=s.armyVictory;$('armyFirst').value=s.armyFirst;$('armyMountains').checked=s.armyMountains;$('armyAnnotations').checked=s.armyAnnotations;return}if(state.phase==='finished'&&state.army){let b=$('armyReplayOpen');if(!b){b=document.createElement('button');b.id='armyReplayOpen';b.className='full secondary';b.textContent='观看本局复盘';$('winnerCard').append(b);b.onclick=()=>{armyReplayIndex=0;renderSafe()}}b.classList.toggle('hidden',!state.army.replay_full?.length);if(armyReplayIndex!==null||armyFxBusy()){$('winnerCard').classList.add('hidden');$('gameCard').classList.remove('hidden');$('armyGame').classList.remove('hidden');document.body.dataset.view='game';renderArmy()}}};

window.addEventListener("resize",()=>{if(state?.mode==="army"&&state.phase!=="lobby")renderSafe()});
