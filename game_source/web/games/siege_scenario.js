
// Touch-first scenario workbench. Reuses the battle canvas, terrain, sprites and icons.
let scenarioEditing=false;
const SCENE_KEY='gh_siege_scenes_v1',DRAFT_KEY='gh_siege_scene_draft_v2';
const sc=$,scClone=x=>JSON.parse(JSON.stringify(x));
const sceneTypes={cannon:'炮台',core:'子刊',wood:'木块',stone:'石块',barrel:'TNT',spring:'弹跳方块',oneway:'单向方块',ladder:'竖向楼梯',zombie:'僵尸',item:'增益'};
const scenarioBuffKeys=siegeV24Keys.filter(k=>!siegeV24Negatives.includes(k)&&k!=='compound');
const scBuff=k=>siegeV24Names[k]||k;
const scZombie=k=>trialZombieNotes[k]?.[0]||k;
const scDims={engineer:[32,44,76],walker:[32,42,44],shield:[36,44,68],heavy:[42,52,100],flyer:[30,34,38],climber:[30,40,52],giant:[58,78,190],runner:[26,38,32],pole:[30,44,48],bomber:[30,40,42],priest:[32,46,65],dancer:[34,46,75],guard:[44,54,150],siegecar:[62,44,135]};
function freshScene(){return {version:1,name:'高楼救援',ammo:8,cannon:{x:100,y:392},core:{x:745,y:134},blocks:[{kind:'stone',x:745,y:172,w:220,h:24},{kind:'stone',x:745,y:280,w:220,h:24},{kind:'stone',x:745,y:398,w:220,h:36},{kind:'stone',x:820,y:226,w:24,h:84},{kind:'stone',x:820,y:336,w:24,h:88}],zombies:[{kind:'walker',x:525,y:390,round:0,drop:{mode:'fixed',kind:'gunteleport',amount:1}},{kind:'walker',x:695,y:246,round:0,drop:{mode:'fixed',kind:'gunteleport',amount:1}},{kind:'walker',x:680,y:139,round:0,drop:{mode:'none'}}],items:[],stock:{}}}
function blankScene(){return {version:1,name:'新建场景',ammo:0,cannon:{x:100,y:392},core:{x:800,y:390},blocks:[],zombies:[],items:[],stock:{}}}
function scValid(s){return s&&s.version===1&&s.cannon&&s.core&&Array.isArray(s.blocks)&&Array.isArray(s.zombies)&&Array.isArray(s.items)&&s.stock&&typeof s.stock==='object'}
function sceneLibrary(){try{const v=JSON.parse(localStorage.getItem(SCENE_KEY)||'[]');return Array.isArray(v)?v.filter(x=>x&&scValid(x.scene)):[]}catch(_){return []}}
function scRestore(){try{const v=JSON.parse(localStorage.getItem(DRAFT_KEY)||'null');return v&&scValid(v.scene)?v:null}catch(_){return null}}
let sceneDraft=freshScene(),sceneId=null,sceneInitialized=false,scenePick=null,sceneBrush=null,scenePanel='',sceneCat='建筑',sceneBuffCat='全部',sceneAdvanced=false,sceneUndo=[],sceneRedo=[],sceneGesture=null,sceneSelectMode=false,sceneSelection=[],sceneMarquee=null;
const scCamera={x:480,y:210,w:430}; // centre and width, independent of the replay camera
const scStyle=document.createElement('style');
scStyle.textContent=
 '#game.sc-edit #hud,#game.sc-edit #controls,#game.sc-edit #manualControls,#game.sc-edit #stockPanel,#game.sc-edit #roomInfo,#game.sc-edit #trialBestiary,#game.sc-edit #minimap,#game.sc-edit #windInfo,#game.sc-edit #status,#game.sc-edit #result{display:none!important}'+
 '#game #scenarioEditor{position:absolute;inset:0;z-index:12;pointer-events:none;color:#f3efdf;font-size:14px;line-height:1.4}#scenarioEditor.hidden{display:none}'+
 '#scenarioEditor .scbar,#scenarioEditor .scpanel{pointer-events:auto;background:#203633; border:1px solid #83958988;border-radius:12px;box-shadow:0 4px 15px #16262238}'+
 '#scenarioEditor .scbar{position:absolute;display:flex;align-items:center;gap:4px;padding:4px;left:max(8px,env(safe-area-inset-left));right:max(8px,env(safe-area-inset-right));margin:auto;max-width:560px}'+
 '#scenarioEditor #scTop{top:max(8px,env(safe-area-inset-top))}#scenarioEditor #scBottom{bottom:max(8px,env(safe-area-inset-bottom))}'+
 '#scenarioEditor button{min-width:44px;min-height:44px;padding:7px 9px;font-size:13px;white-space:nowrap;border:0;background:transparent;color:inherit;border-radius:8px;font-weight:600}#scenarioEditor button:hover,#scenarioEditor button.active{background:#48635b}#scenarioEditor button.primary{background:#e9b76b;color:#28372f}#scenarioEditor button:disabled{opacity:.3}'+
 '#scenarioEditor .scicon{display:inline-grid;place-items:center;flex:0 0 44px;padding:0}#scenarioEditor .scicon svg{width:21px;height:21px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}'+
 '#scenarioEditor .scname{flex:1;min-width:0;text-align:left;padding:0 5px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}#scenarioEditor .scname b,#scenarioEditor .scname small{display:block;overflow:hidden;text-overflow:ellipsis}#scenarioEditor .scname b{font-size:13px}#scenarioEditor .scname small{font-size:10px;color:#b3c5b8}'+
 '#scenarioEditor #scBottom button{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;padding:4px 2px;font-size:11px}#scenarioEditor #scBottom svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}'+
 '#scenarioEditor .scpanel{position:absolute;top:calc(max(8px,env(safe-area-inset-top)) + 60px);left:max(8px,env(safe-area-inset-left));right:max(8px,env(safe-area-inset-right));max-width:560px;margin:auto;max-height:36dvh;overflow-y:auto;overscroll-behavior:contain;touch-action:pan-y;padding:10px;display:grid;gap:8px}'+
 '#scenarioEditor .schead{display:flex;align-items:center;gap:8px;min-height:30px}#scenarioEditor .schead b{flex:1;font-size:15px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap} #scenarioEditor .schead button{display:grid;place-items:center;min-height:40px;min-width:44px;padding:4px 7px}#scenarioEditor .schead button svg{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round}'+
 '#scenarioEditor .scline{display:flex;align-items:center;gap:8px;min-width:0}#scenarioEditor .scline>span:first-child{flex:1;min-width:75px;color:#c5d4c9;font-size:13px}#scenarioEditor .scline select,#scenarioEditor .scline input{min-width:0;max-width:65%;margin:0}'+
 '#scenarioEditor input,#scenarioEditor select{font:inherit;color:#f4eddb;background:#152c29;border:1px solid #607c6b;border-radius:7px;min-height:44px;padding:6px 8px}#scenarioEditor input[type=number]{width:78px;text-align:center}#scenarioEditor select{width:auto}'+
 '#scenarioEditor .sctabs{display:flex;align-items:center;gap:4px;overflow:auto;scrollbar-width:none;touch-action:pan-x}#scenarioEditor .sctabs button{flex:1;min-height:36px;padding:5px 9px;color:#c5d4c9}#scenarioEditor .sctabs button.active{color:#fff1c9;background:#446057}'+
 '#scenarioEditor .scpalette{display:flex;gap:6px;overflow-x:auto;padding-bottom:3px;scrollbar-width:thin;touch-action:pan-x}#scenarioEditor .scresource{display:flex;flex:0 0 72px;min-height:70px;flex-direction:column;justify-content:center;align-items:center;gap:5px;border:1px solid #5d7668;padding:5px 2px;font-size:11px;white-space:normal;line-height:1.15}#scenarioEditor .scresource.active{border-color:#e7c47d;background:#354c41;color:#ffe1aa}#scenarioEditor .scresource svg{width:25px;height:25px}'+
 '#scenarioEditor .scactions{display:flex;gap:6px;align-items:center;justify-content:flex-end}#scenarioEditor .scactions button{border:1px solid #5d7668}#scenarioEditor .scdanger{color:#e5a89b}#scenarioEditor .scsecondary{color:#b8cbbd;font-size:12px}#scenarioEditor .scgroup{border-top:1px solid #829b853f;padding-top:7px;display:grid;gap:6px}'+
 '#scenarioEditor .scpicker{max-height:26dvh;min-height:75px;overflow-y:auto;overscroll-behavior:contain;touch-action:pan-y;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:4px;padding:6px;border:1px solid #516b5d;border-radius:9px}#scenarioEditor .scpicker button{white-space:normal;overflow-wrap:anywhere;min-height:42px;text-align:left;border:1px solid #516b5d}#scenarioEditor .scpicker input{grid-column:1/-1;width:100%;margin:0}#scenarioEditor .scstep{display:flex;gap:4px;align-items:center}#scenarioEditor .scstep button{border:1px solid #516b5d;min-width:44px}#scenarioEditor .scstep input{width:74px}#scenarioEditor .scbadge{font-size:12px;color:#efd6a2}#scenarioEditor .scselection{display:grid;gap:6px}#scenarioEditor .scselection button{border:1px solid #516b5d}#scenarioEditor .sclist{display:grid;gap:4px}#scenarioEditor .sclist button{text-align:left;white-space:normal;border:1px solid #5d766866;overflow-wrap:anywhere}#scenarioEditor .scstockrow{display:grid;grid-template-columns:minmax(0,1fr) 44px 38px 44px;align-items:center;gap:5px}#scenarioEditor .scstockrow button{border:1px solid #5d7668}#scenarioEditor .scstockrow span:nth-child(3){text-align:center}'+
 '#scenarioEditor #scHint{position:absolute;left:50%;transform:translateX(-50%);bottom:calc(max(8px,env(safe-area-inset-bottom)) + 65px);max-width:90%;padding:5px 10px;border-radius:7px;background:#203633dd;color:#eee4c9;font-size:11px;white-space:normal;text-align:center;pointer-events:none}'+
 '@media(orientation:landscape){#scenarioEditor .scpanel{top:calc(max(4px,env(safe-area-inset-top)) + 56px);left:auto;right:max(6px,env(safe-area-inset-right));width:min(310px,38vw);max-height:calc(100% - 122px);padding:8px}#scenarioEditor #scBottom{max-width:360px}#scenarioEditor .scbar{padding:3px}#scenarioEditor #scTop{top:max(4px,env(safe-area-inset-top))}#scenarioEditor #scBottom{bottom:max(4px,env(safe-area-inset-bottom))}#scenarioEditor .scpanel button{min-height:40px}#scenarioEditor .scresource{min-height:62px}}'+
 '@media(max-width:350px){#scenarioEditor #scTop{gap:1px}#scenarioEditor #scTop .scicon{flex-basis:40px;min-width:40px}#scenarioEditor #scTop .primary{padding:5px 7px}}';
document.head.append(scStyle);
const scIcons={back:'<path d="m15 18-6-6 6-6"/>',undo:'<path d="M9 14 4 9l5-5M4 9h10a6 6 0 0 1 0 12"/>',redo:'<path d="m15 4 5 5-5 5m5-5H10a6 6 0 0 0 0 12"/>',select:'<rect x="4" y="5" width="16" height="14" rx="1" stroke-dasharray="3 3"/><path d="m13 13 7 7"/>',add:'<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',map:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 15 5-5 4 4 3-3 4 4"/>',settings:'<path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="#203633"/><circle cx="15" cy="17" r="3" fill="#203633"/>',folder:'<path d="M3 7a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v8H3z"/>',close:'<path d="m6 6 12 12M18 6 6 18"/>'};
const scIcon=k=>'<svg viewBox="0 0 24 24" aria-hidden="true">'+scIcons[k]+'</svg>';
const editor=document.createElement('section');editor.id='scenarioEditor';editor.className='hidden';editor.setAttribute('aria-label','场景工作台');
editor.innerHTML='<div class="scbar" id="scTop"><button id="scClose" class="scicon" aria-label="返回实验室">'+scIcon('back')+'</button><div class="scname"><b id="scTitle">场景布置</b><small id="scState">草稿</small></div><button class="scicon" id="scUndo" aria-label="撤销">'+scIcon('undo')+'</button><button class="scicon" id="scRedo" aria-label="重做">'+scIcon('redo')+'</button><button id="scPlay" class="primary">试玩</button></div><aside id="scPanel" class="scpanel hidden" aria-label="编辑面板"><div class="schead"><b id="scPanelTitle"></b><button id="scPanelClose" aria-label="收起面板">'+scIcon('close')+'</button></div><div id="scPanelBody"></div></aside><div id="scHint" class="hidden" role="status"></div><div class="scbar" id="scBottom">'+[['select','框选'],['add','添加'],['map','全图'],['settings','设置'],['folder','场景库']].map(([k,n])=>'<button id="scBtn-'+k+'" aria-label="'+n+'">'+scIcon(k)+n+'</button>').join('')+'</div>';
sc('game').append(editor);
let scHintTimer;
function scHint(t,persistent=false){clearTimeout(scHintTimer);const el=sc('scHint');el.textContent=t;el.classList.toggle('hidden',!t);if(t&&!persistent)scHintTimer=setTimeout(()=>{el.classList.add('hidden')},2400)}
function scSaveDraft(){try{localStorage.setItem(DRAFT_KEY,JSON.stringify({scene:sceneDraft,id:sceneId}))}catch(_){}}
function scSnap(){return JSON.stringify(sceneDraft)}
function scHistory(before){if(before===scSnap())return;sceneUndo.push(before);if(sceneUndo.length>80)sceneUndo.shift();sceneRedo=[];scSaveDraft();scChrome()}
function scChange(fn){const before=scSnap();fn();if(scFirstOverlap()){sceneDraft=JSON.parse(before);scenePick=null;sceneSelection=[];scenePanel='';scRenderPanel();scHint('对象发生重叠，已恢复原位置');return false}scHistory(before);return true}
function scRestoreHistory(from,to){if(!from.length)return;to.push(scSnap());sceneDraft=JSON.parse(from.pop());scenePick=null;sceneSelection=[];sceneBrush=null;scenePanel='';scSaveDraft();scRenderPanel();scChrome()}
function scChrome(){sc('scTitle').textContent=sceneDraft.name||'新建场景';sc('scState').textContent=sceneBrush?'布置 '+scBrushName():sceneId?'已保存场景 · 草稿自动保存':'场景布置 · 草稿自动保存';sc('scUndo').disabled=!sceneUndo.length;sc('scRedo').disabled=!sceneRedo.length;sc('scBtn-select').classList.toggle('active',sceneSelectMode);for(const [k,v] of [['add','add'],['settings','settings'],['folder','library']])sc('scBtn-'+k).classList.toggle('active',scenePanel===v||(k==='add'&&!!sceneBrush))}
function updateScenarioButton(){const btn=sc('scenarioToggle');btn.classList.toggle('hidden',!(trialPage||room?.trial||room?.scenarioActive));btn.disabled=!!(requesting||playing||room?.busy||overview);btn.textContent=room?.scenarioActive?'布置':'关卡'}
function scEntries(){return [{type:'cannon',obj:sceneDraft.cannon},{type:'core',obj:sceneDraft.core},...sceneDraft.blocks.map(obj=>({type:obj.kind,obj,list:sceneDraft.blocks})),...sceneDraft.zombies.map(obj=>({type:'zombie',obj,list:sceneDraft.zombies})),...sceneDraft.items.map(obj=>({type:'item',obj,list:sceneDraft.items}))]}
function scSize(e){if(e.type==='cannon')return [46,48];if(e.type==='core')return [50,52];if(e.type==='item')return [30,30];if(e.type==='zombie'){const v=room?.zombieCatalog?.[e.obj.kind];return v?.w?[v.w,v.h]:(scDims[e.obj.kind]||scDims.walker).slice(0,2)}return [e.obj.w,e.obj.h]}
function scHp(e){return e.type==='core'?100:e.type==='cannon'?75:e.type==='zombie'?(room?.zombieCatalog?.[e.obj.kind]?.hp||scDims[e.obj.kind]?.[2]||44):e.type==='stone'?90:e.type==='barrel'?35:e.type==='spring'?72:e.type==='oneway'?80:e.type==='ladder'?55:45}
function scMove(e,x,y){const o=e.obj,oldX=o.x,oldY=o.y,[w,h]=scSize(e),ex=e.type==='zombie';o.x=Math.round(clamp(x,ex?-240:Math.max(25,w/2),ex?1200:Math.min(935,960-w/2)));o.y=Math.round(clamp(y,Math.max(24,h/2),Math.min(e.list===sceneDraft.blocks?416:392,416-h/2)));if(!scCanOccupy(e)){o.x=oldX;o.y=oldY;scHint('此处已有物体，不能重叠');return false}return true}
function scView(){const ar=canvas.width/Math.max(1,canvas.height),w=scCamera.w,h=w/ar;return {x:scCamera.x-w/2,y:scCamera.y-h/2,w,h,z:canvas.width/w}}
function scBound(){const v=scView();scCamera.x=clamp(scCamera.x,-240,1200);scCamera.y=clamp(scCamera.y,Math.min(208,-80+v.h/2),Math.max(208,480-v.h/2));}
function scFull(){const ar=canvas.width/Math.max(1,canvas.height);scCamera.w=Math.max(1440,510*ar);scCamera.x=480;scCamera.y=210;scHint('全图 · 双指放大查看细节')}
function scHome(){scCamera.w=clamp(canvas.width/Math.max(1,canvas.height)*430,300,680);scCamera.x=sceneDraft.cannon.x+scCamera.w*.32;scCamera.y=250;scBound()}
function scPoint(px,py){const r=canvas.getBoundingClientRect(),v=scView();return [v.x+(px-r.left)*v.w/r.width,v.y+(py-r.top)*v.h/r.height]}
function scEntities(){return scEntries().filter(e=>e.type!=='item').map((e,i)=>{const o=e.obj,[w,h]=scSize(e),hp=scHp(e),special=['spring','oneway','ladder'].includes(e.type)?e.type:undefined;return {id:i,kind:e.type==='spring'||e.type==='oneway'?'stone':e.type==='ladder'?'wood':e.type,special,passDir:o.passDir||1,side:e.type==='zombie'?2:0,shared:e.type==='core',zombieType:e.type==='zombie'?o.kind:undefined,x:o.x,y:o.y,w,h,hp,max:hp}})}
function renderScenarioFrame(now){const v=scView(),realRoom=room,oldY=camera.y;const bodies=scEntities();room={...realRoom,field:'standard',terrain:[[0,416],[960,416]],rise:0,bodies,items:sceneDraft.items,zombie:{solo:true,bothSides:false},gunMotion:[],liveShots:[]};camera.y=v.y;
try{ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='#728c8b';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.setTransform(v.z,0,0,v.z,-v.x*v.z,-v.y*v.z);scene(now);
ctx.save();ctx.strokeStyle='#dde8da50';ctx.lineWidth=1/v.z;const step=v.w>1000?80:40;ctx.beginPath();for(let x=0;x<=960;x+=step){ctx.moveTo(x,0);ctx.lineTo(x,416)}for(let y=0;y<=416;y+=step){ctx.moveTo(0,y);ctx.lineTo(960,y)}ctx.stroke();ctx.fillStyle='#435e5a';ctx.fillRect(-240,416,240,64);ctx.fillRect(960,416,240,64);ctx.setLineDash([7/v.z,5/v.z]);ctx.strokeStyle='#ecdfaa';ctx.beginPath();ctx.moveTo(0,-80);ctx.lineTo(0,416);ctx.moveTo(960,-80);ctx.lineTo(960,416);ctx.stroke();ctx.restore();
for(const b of bodies)if(b.kind!=='cannon')block(b,b.x,b.y,b.hp);
for(const it of sceneDraft.items){ctx.save();ctx.fillStyle='#263d3c';ctx.strokeStyle=itemColors[it.kind]||'#e9d395';ctx.lineWidth=2;ctx.beginPath();ctx.arc(it.x,it.y,15,0,Math.PI*2);ctx.fill();ctx.stroke();drawItemIcon(it.kind,it.x,it.y,20);ctx.restore()}
for(const o of sceneDraft.zombies){if(!o.round&&o.drop?.mode!=='fixed')continue;const [w,h]=scSize({type:'zombie',obj:o}),x=o.x+w/2,y=o.y-h/2;ctx.save();ctx.fillStyle='#203633';ctx.beginPath();ctx.arc(x,y,10,0,Math.PI*2);ctx.fill();if(o.drop?.mode==='fixed')drawItemIcon(o.drop.kind,x,y,15);else{ctx.font='bold 10px sans-serif';ctx.textAlign='center';ctx.fillStyle='#f5dfab';ctx.fillText(String(o.round),x,y+3)}ctx.restore()}
if(sceneSelectMode&&sceneMarquee){const a=sceneMarquee;ctx.save();ctx.strokeStyle='#fff0b3';ctx.fillStyle='#f5e0a52b';ctx.lineWidth=2/v.z;ctx.setLineDash([6/v.z,4/v.z]);ctx.fillRect(Math.min(a.x,a.x2),Math.min(a.y,a.y2),Math.abs(a.x2-a.x),Math.abs(a.y2-a.y));ctx.strokeRect(Math.min(a.x,a.x2),Math.min(a.y,a.y2),Math.abs(a.x2-a.x),Math.abs(a.y2-a.y));ctx.restore()}for(const e of sceneSelection){const o=e.obj,[w,h]=scSize(e);ctx.save();ctx.strokeStyle='#ffefaa';ctx.lineWidth=2/v.z;ctx.strokeRect(o.x-w/2,o.y-h/2,w,h);ctx.restore()}if(scenePick){const o=scenePick.obj,[w,h]=scSize(scenePick),pad=4/v.z;ctx.save();ctx.strokeStyle='#fff0b3';ctx.lineWidth=2/v.z;ctx.setLineDash([5/v.z,4/v.z]);ctx.strokeRect(o.x-w/2-pad,o.y-h/2-pad,w+2*pad,h+2*pad);ctx.setLineDash([]);if(scenePick.list===sceneDraft.blocks){ctx.fillStyle='#fff0b3';for(const [sx,sy] of [[-1,-1],[1,-1],[-1,1],[1,1]]){const a=8/v.z;ctx.fillRect(o.x+sx*w/2-a/2,o.y+sy*h/2-a/2,a,a)}}ctx.restore()}
}finally{room=realRoom;camera.y=oldY}}
function scNode(tag,cls,text){const e=document.createElement(tag);if(cls)e.className=cls;if(text!=null)e.textContent=text;return e}
function scButton(text,fn,cls=''){const b=scNode('button',cls,text);b.type='button';b.onclick=fn;return b}
function scRow(parent,label){const row=scNode('div','scline');row.append(scNode('span','',label));parent.append(row);return row}
function scSelect(parent,label,value,opts,onChange){const row=scRow(parent,label);if(opts.length>8){const now=opts.find(x=>x[0]===value)?.[1]||value;const btn=scButton(now+' · 更换',()=>{const next=picker.classList.contains('hidden');picker.classList.toggle('hidden',!next);if(next)input.focus()});row.append(btn);const picker=scNode('div','scpicker hidden'),input=scNode('input');input.type='search';input.placeholder='搜索'+label;input.setAttribute('aria-label','搜索'+label);picker.append(input);const grid=scNode('div');grid.style.display='contents';picker.append(grid);const draw=()=>{grid.replaceChildren();for(const [v,n] of opts.filter(([v,n])=>String(n).includes(input.value.trim())||String(v).includes(input.value.trim()))){const choice=scButton(n,()=>{picker.classList.add('hidden');onChange(v)},v===value?'active':'');grid.append(choice)}};input.oninput=draw;draw();parent.append(picker);return btn}const el=scNode('select');el.setAttribute('aria-label',label);for(const [v,n] of opts){const o=scNode('option','',n);o.value=v;el.append(o)}el.value=value;el.onchange=()=>onChange(el.value);row.append(el);return el}
function scNumber(parent,label,value,min,max,onChange){const row=scRow(parent,label),el=scNode('input');el.type='number';el.min=min;el.max=max;el.step=1;el.value=value;el.setAttribute('aria-label',label);el.onchange=()=>{const n=clamp(Math.round(Number(el.value)||0),min,max);el.value=n;onChange(n)};row.append(el);return el}
function scText(parent,label,value,onChange){const row=scRow(parent,label),el=scNode('input');el.type='text';el.maxLength=40;el.value=value;el.setAttribute('aria-label',label);el.onchange=()=>onChange(el.value.trim()||'新建场景');row.append(el)}
function scTabs(parent,options,active,fn){const bar=scNode('div','sctabs');for(const k of options)bar.append(scButton(k,()=>fn(k),k===active?'active':''));parent.append(bar)}
function scActions(parent){const bar=scNode('div','scactions');parent.append(bar);return bar}
function scGroup(parent){const g=scNode('div','scgroup');parent.append(g);return g}
function scCap(k){return room?.stackCaps?.[k]||1}
function scBrushName(){return !sceneBrush?'':sceneBrush.type==='zombie'?scZombie(sceneBrush.kind):sceneBrush.type==='item'?scBuff(sceneBrush.kind):sceneTypes[sceneBrush.type]}
function scPanelSet(type){scenePanel=type;sceneAdvanced=false;scRenderPanel();scChrome()}
function scDismiss(cancelBrush=false){scenePanel='';if(cancelBrush)sceneBrush=null;scRenderPanel();scChrome();if(!sceneBrush)scHint('')}
function scChooseBrush(type,kind){scenePick=null;sceneSelection=[];sceneSelectMode=false;sceneBrush={type,kind};if(type==='zombie')Object.assign(sceneBrush,{round:0,drop:{mode:'random'}});if(type==='item')sceneBrush.amount=1;if(['wood','stone','barrel','spring','oneway','ladder'].includes(type))Object.assign(sceneBrush,{w:type==='spring'?42:type==='oneway'||type==='ladder'?28:48,h:type==='spring'?28:type==='oneway'?72:type==='ladder'?128:24,...(type==='oneway'?{passDir:1}:{})});scRenderPanel();scChrome();scHint(scBrushName()+' · 点击空地连续布置',true)}
function scResourceIcon(type,k){if(type==='item')return siegeIcon(k,24);if(type==='zombie'){const skin=k==='heavy'?'#839575':k==='bomber'?'#d7a15c':k==='priest'?'#a7b3d1':'#a0bd67';const extra=k==='shield'||k==='guard'?'<rect x="23" y="13" width="7" height="15" fill="#a9c8ce"/>':k==='flyer'?'<path d="M8 16 1 8v12l7 2m16-6 7-8v12l-7 2" fill="#c2d7a5"/>':k==='pole'?'<path d="M1 28 31 5" stroke="#dfc084" stroke-width="3"/>':k==='dancer'?'<path d="M6 4h20M10 4V0h12v4" stroke="#bc6788" stroke-width="3"/>':k==='runner'?'<rect x="9" y="2" width="14" height="3" fill="#e4a04f"/>':k==='bomber'?'<rect x="9" y="17" width="14" height="5" fill="#a8463d"/>':k==='priest'?'<path d="M16 15v8m-4-4h8" stroke="#d8e4bc" stroke-width="2"/>':k==='siegecar'?'<rect x="2" y="16" width="28" height="12" fill="#7b8069"/><path d="M17 12h14" stroke="#424f4b" stroke-width="5"/>':'';return '<svg viewBox="0 0 32 32"><rect x="9" y="2" width="14" height="12" rx="2" fill="'+skin+'"/><rect x="8" y="14" width="16" height="10" fill="#71865e"/><path d="M12 24v6m8-6v6" stroke="#9aa69b" stroke-width="4"/><path d="M12 6h3m3 0h3" stroke="#26382b" stroke-width="2"/>'+extra+'</svg>'}const c={wood:'#ac835b',stone:'#9da9a9',barrel:'#bb6550',spring:'#ae9cc5',oneway:'#8bbdb0',ladder:'#d1ae77',core:'#e8d9ac',cannon:'#b28a4b'}[type];return '<svg viewBox="0 0 32 32"><rect x="3" y="7" width="26" height="19" rx="2" fill="'+c+'"/><path d="M5 16h22" stroke="#293b35" stroke-opacity=".5"/></svg>'}
function scReward(parent,o,change){scStepNumber(parent,'出现轮次',o.round,0,100,n=>change(()=>o.round=n));parent.append(scNode('div','scsecondary','击杀奖励'));scTabs(parent,['随机','指定','无'],({random:'随机',fixed:'指定',none:'无'})[o.drop?.mode||'random'],v=>{change(()=>{o.drop=v==='指定'?{mode:'fixed',kind:'gunteleport',amount:1}:{mode:v==='随机'?'random':'none'}});scRenderPanel()});if(o.drop?.mode==='fixed'){scSelect(parent,'奖励',o.drop.kind,scenarioBuffKeys.map(k=>[k,scBuff(k)]),v=>{change(()=>{o.drop.kind=v;o.drop.amount=1});scRenderPanel()});if(scCap(o.drop.kind)>1)scNumber(parent,'数量',o.drop.amount,1,scCap(o.drop.kind),n=>change(()=>o.drop.amount=n))}}
function scRenderPanel(){const panel=sc('scPanel'),body=sc('scPanelBody');panel.classList.toggle('hidden',!scenarioEditing||!scenePanel);body.replaceChildren();body.style.display='grid';body.style.gap='8px';if(!scenePanel)return;
const title=sc('scPanelTitle');
if(scenePanel==='add'){title.textContent='添加对象';scTabs(body,['建筑','僵尸','增益','单位'],sceneCat,k=>{sceneCat=k;scRenderPanel()});if(sceneCat==='增益'){scTabs(body,['全部','弹药','技能','机制','效果'],sceneBuffCat,k=>{sceneBuffCat=k;scRenderPanel()})}
const resources=sceneCat==='建筑'?['wood','stone','barrel','spring','oneway','ladder'].map(k=>[k,k,sceneTypes[k]]):sceneCat==='单位'?['cannon','core'].map(k=>[k,k,sceneTypes[k]]):sceneCat==='僵尸'?Object.keys(scDims).map(k=>['zombie',k,scZombie(k)]):scenarioBuffKeys.filter(k=>sceneBuffCat==='全部'||siegeV24Group(k)===sceneBuffCat).map(k=>['item',k,scBuff(k)]);
const palette=scNode('div','scpalette');for(const [type,k,name] of resources){const b=scButton('',()=>scChooseBrush(type,k),'scresource'+(sceneBrush?.type===type&&sceneBrush?.kind===k?' active':''));b.innerHTML=scResourceIcon(type,k);b.append(scNode('span','',name));b.setAttribute('aria-label','添加'+name);palette.append(b)}body.append(palette);
if(sceneBrush){const g=scGroup(body),line=scNode('div','scline');line.append(scNode('span','',scBrushName()+' · 连续布置'),scButton('参数',()=>{sceneAdvanced=!sceneAdvanced;scRenderPanel()},sceneAdvanced?'active':''),scButton('收起',()=>scDismiss(false)));g.append(line);if(sceneAdvanced){if(sceneBrush.type==='zombie')scReward(g,sceneBrush,fn=>fn());else if(sceneBrush.type==='item')scNumber(g,'数量',sceneBrush.amount,1,scCap(sceneBrush.kind),n=>sceneBrush.amount=n);else if(['wood','stone','barrel','spring','oneway','ladder'].includes(sceneBrush.type)){scNumber(g,'宽度',sceneBrush.w,12,240,n=>sceneBrush.w=n);scNumber(g,'高度',sceneBrush.h,12,sceneBrush.type==='ladder'?320:160,n=>sceneBrush.h=n);if(sceneBrush.type==='oneway')scSelect(g,'穿行方向',String(sceneBrush.passDir||1),[['1','从左向右'],['-1','从右向左']],v=>sceneBrush.passDir=Number(v))}}}
}else if(scenePanel==='object'&&scenePick){const e=scenePick,o=e.obj,change=fn=>scChange(fn);title.textContent=e.type==='zombie'?scZombie(o.kind):e.type==='item'?scBuff(o.kind):sceneTypes[e.type];
if(e.type==='zombie'){scReward(body,o,change)}else if(e.type==='item'){scSelect(body,'增益',o.kind,scenarioBuffKeys.map(k=>[k,scBuff(k)]),v=>{change(()=>{o.kind=v;o.amount=1});scRenderPanel()});scNumber(body,'数量',o.amount,1,scCap(o.kind),n=>change(()=>o.amount=n))}else if(e.list===sceneDraft.blocks){scNumber(body,'宽度',o.w,12,240,n=>change(()=>{o.w=n;scMove(e,o.x,o.y)}));scNumber(body,'高度',o.h,12,e.type==='ladder'?320:160,n=>change(()=>{o.h=n;scMove(e,o.x,o.y)}));if(e.type==='oneway')scSelect(body,'允许穿行方向',String(o.passDir||1),[['1','从左向右'],['-1','从右向左']],v=>change(()=>o.passDir=Number(v)));body.append(scNode('small','scsecondary','也可直接拖动战场中的四角调整尺寸'))}
const a=scActions(body);a.append(scButton(sceneAdvanced?'收起坐标':'精确坐标',()=>{sceneAdvanced=!sceneAdvanced;scRenderPanel()}));if(e.list){a.append(scButton('复制',()=>{if(e.list.length>=scLimit(e.type))return scHint('对象已达上限');change(()=>{const obj=scCopySpot(e);if(obj){e.list.push(obj);scenePick={...e,obj}}});scRenderPanel()}),scButton('删除',()=>{change(()=>e.list.splice(e.list.indexOf(o),1));scenePick=null;scDismiss(true)},'scdanger'))}
if(sceneAdvanced){const g=scGroup(body);scNumber(g,'X',o.x,e.type==='zombie'?-240:25,e.type==='zombie'?1200:935,n=>change(()=>scMove(e,n,o.y)));scNumber(g,'Y',o.y,24,392,n=>change(()=>scMove(e,o.x,n)));if(e.type==='zombie')scSelect(g,'种类',o.kind,Object.keys(scDims).map(k=>[k,scZombie(k)]),v=>{change(()=>{o.kind=v;scMove(e,o.x,o.y)});scRenderPanel()})}
}else if(scenePanel==='settings'){title.textContent='关卡设置';scNumber(body,'炮弹数量（0 为无限）',sceneDraft.ammo,0,100,n=>scChange(()=>sceneDraft.ammo=n));const row=scRow(body,'初始增益');row.append(scButton(Object.keys(sceneDraft.stock).length?'已配置 '+Object.keys(sceneDraft.stock).length+' 类':'未配置',()=>scPanelSet('stock')));body.append(scNode('small','scsecondary','胜利：清除所有已安排僵尸，并保护子刊。挑战模式不自动补给。'))
}else if(scenePanel==='stock'){title.textContent='初始增益';scTabs(body,['全部','弹药','技能','机制','效果'],sceneBuffCat,k=>{sceneBuffCat=k;scRenderPanel()});for(const k of scenarioBuffKeys.filter(k=>sceneBuffCat==='全部'||siegeV24Group(k)===sceneBuffCat)){const row=scNode('div','scstockrow'),name=scNode('span');name.innerHTML=siegeIcon(k,18)+' ';name.append(document.createTextNode(scBuff(k)));const count=scNode('span','',String(sceneDraft.stock[k]||0));const set=delta=>{const n=clamp((sceneDraft.stock[k]||0)+delta,0,scCap(k));scChange(()=>{if(n)sceneDraft.stock[k]=n;else delete sceneDraft.stock[k]});count.textContent=n;minus.disabled=n===0;plus.disabled=n===scCap(k)};const minus=scButton('−',()=>set(-1)),plus=scButton('+',()=>set(1));minus.disabled=!sceneDraft.stock[k];plus.disabled=(sceneDraft.stock[k]||0)>=scCap(k);minus.setAttribute('aria-label','减少'+scBuff(k));plus.setAttribute('aria-label','增加'+scBuff(k));row.append(name,minus,count,plus);body.append(row)}body.prepend(scButton('返回关卡设置',()=>scPanelSet('settings')))
}else if(scenePanel==='library'){title.textContent='场景库';scText(body,'场景名称',sceneDraft.name,v=>scChange(()=>sceneDraft.name=v));const a=scActions(body);a.append(scButton('新建',()=>scReplace(blankScene())),scButton('保存',()=>scSave(false),'primary'),scButton('另存',()=>scSave(true)));const list=scNode('div','sclist');for(const s of sceneLibrary()){const row=scNode('div','scline');const b=scButton(s.scene.name+(s.id===sceneId?' · 当前':''),()=>scReplace(s.scene,s.id));b.style.flex='1';row.append(b,scButton('删除',()=>{if(!confirm('删除场景「'+s.scene.name+'」？'))return;try{localStorage.setItem(SCENE_KEY,JSON.stringify(sceneLibrary().filter(x=>x.id!==s.id)));if(sceneId===s.id)sceneId=null;scSaveDraft();scRenderPanel();scChrome()}catch(e){scHint('删除失败：'+e.message)}},'scdanger'));list.append(row)}body.append(list);const details=scNode('details','scgroup'),summary=scNode('summary','scsecondary','更多场景操作');details.append(summary);const bar=scActions(details);bar.append(scButton('导入',scImport),scButton('导出',scExport),scButton('示例',()=>scReplace(freshScene())));details.append(scButton('复原自由靶场',()=>scRun(true)));body.append(details)}
}
function scLimit(type){return type==='zombie'?54:type==='item'?50:100}
function scReplace(s,id=null){sceneDraft=scClone(s);sceneId=id;scenePick=null;sceneSelection=[];sceneSelectMode=false;sceneBrush=null;sceneUndo=[];sceneRedo=[];scSaveDraft();scChrome();scRenderPanel();scHome()}
function scSave(copy){try{const all=sceneLibrary();if(copy||!sceneId)sceneId=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,6);const i=all.findIndex(s=>s.id===sceneId),entry={id:sceneId,scene:scClone(sceneDraft)};if(i<0)all.push(entry);else all[i]=entry;localStorage.setItem(SCENE_KEY,JSON.stringify(all));scSaveDraft();scRenderPanel();scChrome();scHint('已保存')}catch(e){scHint('保存失败：'+e.message)}}
function scExport(){const blob=new Blob([JSON.stringify(sceneDraft,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=scNode('a');a.href=url;a.download='siege-scene.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function scImport(){const input=scNode('input');input.type='file';input.accept='.json,application/json';input.onchange=async()=>{try{if(!input.files[0]||input.files[0].size>65536)throw Error('文件过大');const s=JSON.parse(await input.files[0].text());if(!scValid(s))throw Error('场景格式无效');scReplace(s);scHint('已导入')}catch(e){scHint(e.message)}};input.click()}
function scOpen(){if(!room||requesting||playing||room.busy||overview)return;sceneSelection=[];sceneSelectMode=false;if(!sceneInitialized){const d=scRestore();if(d){sceneDraft=d.scene;sceneId=d.id||null}else if(room.scenarioSource)sceneDraft=scClone(room.scenarioSource);sceneInitialized=true;scHome()}
scenePick=null;sceneBrush=null;scenePanel='';scenarioEditing=true;closePanels();trialBestiaryOpen=false;drag=null;pan=null;overview=null;sc('game').classList.add('sc-edit');editor.classList.remove('hidden');scRenderPanel();scChrome();scHint('点击对象编辑 · 拖动空地移动视野');update()}
function scClose(){scenarioEditing=false;sceneGesture=null;sceneBrush=null;scenePick=null;sceneSelection=[];sceneSelectMode=false;scenePanel='';scSaveDraft();editor.classList.add('hidden');sc('game').classList.remove('sc-edit');scHint('');update()}
sc('scenarioToggle').onclick=scOpen;sc('scClose').onclick=scClose;
sc('scUndo').onclick=()=>scRestoreHistory(sceneUndo,sceneRedo);sc('scRedo').onclick=()=>scRestoreHistory(sceneRedo,sceneUndo);
sc('scPanelClose').onclick=()=>scDismiss(false);
sc('scBtn-select').onclick=()=>{sceneSelectMode=!sceneSelectMode;scenePick=null;sceneSelection=[];sceneBrush=null;scDismiss(false);scChrome();scHint(sceneSelectMode?'拖动空白处框选对象，随后可整体移动':'',sceneSelectMode)};
sc('scBtn-add').onclick=()=>{if(scenePanel==='add'||sceneBrush){scenePick=null;scDismiss(true)}else{scenePick=null;scPanelSet('add')}};
sc('scBtn-map').onclick=()=>{scDismiss(true);scenePick=null;scFull()};
sc('scBtn-settings').onclick=()=>{scenePick=null;sceneBrush=null;scenePanel==='settings'?scDismiss(true):scPanelSet('settings')};
sc('scBtn-folder').onclick=()=>{scenePick=null;sceneBrush=null;scenePanel==='library'?scDismiss(true):scPanelSet('library')};
async function scRun(free=false){if(requesting||playing||room?.busy)return;if(!free&&scFirstOverlap()){scHint('请先处理重叠的对象，再试玩',true);return}requesting=true;sc('scPlay').disabled=true;scSaveDraft();try{const d=await req(free?'trialReset':'scenarioLoad',free?{mode:'standard'}:{scene:sceneDraft});scClose();selection={};shotConfig=defaultShotConfig();stockKey='';notice='';apply(d);cameraSnap(home(0))}catch(e){scHint(e.message,true)}finally{requesting=false;sc('scPlay').disabled=false;update()}}
sc('scPlay').onclick=()=>scRun();
function scPickAt(x,y){const pad=9/scView().z*(window.devicePixelRatio||1);return scEntries().reverse().find(e=>{const [w,h]=scSize(e);return Math.abs(x-e.obj.x)<=w/2+pad&&Math.abs(y-e.obj.y)<=h/2+pad})||null}
function scHandleAt(x,y){if(!scenePick||scenePick.list!==sceneDraft.blocks)return null;const o=scenePick.obj,[w,h]=scSize(scenePick),tol=16/scView().z*(window.devicePixelRatio||1);for(const [sx,sy] of [[-1,-1],[1,-1],[-1,1],[1,1]])if(Math.hypot(x-o.x-sx*w/2,y-o.y-sy*h/2)<tol)return {sx,sy,ax:o.x-sx*w/2,ay:o.y-sy*h/2};return null}
function scPlace(x,y){const b=sceneBrush;if(!b)return;if(b.type==='cannon'||b.type==='core'){scChange(()=>scMove({type:b.type,obj:sceneDraft[b.type]},x,y));return}const list=b.type==='zombie'?sceneDraft.zombies:b.type==='item'?sceneDraft.items:sceneDraft.blocks;if(list.length>=scLimit(b.type))return scHint('对象已达上限');const obj=b.type==='zombie'?{kind:b.kind,x,y,round:b.round,drop:scClone(b.drop)}:b.type==='item'?{kind:b.kind,x,y,amount:b.amount}:{kind:b.kind,x,y,w:b.w,h:b.h,...(b.type==='oneway'?{passDir:b.passDir||1}:{})};const e={type:b.type,obj,list};if(!scMove(e,x,y))return;if(!scCanOccupy(e)){scHint('此处已有物体，请选择空位');return}scChange(()=>{list.push(obj)});scHint(scBrushName()+' · 点击空地连续布置',true)}
function scStart(px,py){const [x,y]=scPoint(px,py),handle=!sceneBrush&&scHandleAt(x,y),hit=!sceneBrush&&scPickAt(x,y);sceneGesture={kind:handle?'size':hit?'object':'pan',hit:handle?scenePick:hit,handle,px,py,cx:scCamera.x,cy:scCamera.y,x,y,before:scSnap(),moved:false};if(sceneGesture.hit){const o=sceneGesture.hit.obj;sceneGesture.dx=o.x-x;sceneGesture.dy=o.y-y}}
function scMotion(px,py){const g=sceneGesture;if(!g||g.kind==='pinch')return;const dx=px-g.px,dy=py-g.py;if(!g.moved&&Math.hypot(dx,dy)<7)return;g.moved=true;const [x,y]=scPoint(px,py);if(g.kind==='object'){scenePick=g.hit;scMove(g.hit,x+g.dx,y+g.dy)}else if(g.kind==='size'){const o=g.hit.obj,a=g.handle;const maxH=g.hit.type==='ladder'?320:160;const bx=clamp(x,a.sx<0?Math.max(0,a.ax-240):a.ax+12,a.sx<0?a.ax-12:Math.min(960,a.ax+240)),by=clamp(y,a.sy<0?Math.max(0,a.ay-maxH):a.ay+12,a.sy<0?a.ay-12:Math.min(416,a.ay+maxH));o.w=Math.round(Math.abs(bx-a.ax));o.h=Math.round(Math.abs(by-a.ay));o.x=(bx+a.ax)/2;o.y=(by+a.ay)/2;scMove(g.hit,o.x,o.y)}else{const r=canvas.getBoundingClientRect(),v=scView();scCamera.x=g.cx-dx*v.w/r.width;scCamera.y=g.cy-dy*v.h/r.height;scBound()}}
function scEnd(px,py,cancel=false){const g=sceneGesture;sceneGesture=null;if(!g||g.kind==='pinch')return;if(cancel){if(g.moved&&g.kind!=='pan'){sceneDraft=JSON.parse(g.before);scenePick=null;scDismiss(false)}return}
if(g.moved){if(g.kind==='object'||g.kind==='size'){scHistory(g.before);if(scenePanel==='object')scRenderPanel()}return}
if(sceneBrush){const [x,y]=scPoint(px,py);scPlace(x,y);if(scenePanel==='add')scDismiss(false);return}
if(g.hit){scenePick=g.hit;scPanelSet('object')}else{scenePick=null;scDismiss(true)}}
function scPinchStart(a,b){if(sceneGesture?.moved&&['object','size'].includes(sceneGesture.kind)){sceneDraft=JSON.parse(sceneGesture.before);scenePick=null;scDismiss(false)}const mx=(a.clientX+b.clientX)/2,my=(a.clientY+b.clientY)/2;sceneGesture={kind:'pinch',distance:Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY),w:scCamera.w,anchor:scPoint(mx,my)}}
function scPinchMove(a,b){const g=sceneGesture;if(g?.kind!=='pinch')return;const dist=Math.max(12,Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY)),mx=(a.clientX+b.clientX)/2,my=(a.clientY+b.clientY)/2;scCamera.w=clamp(g.w*g.distance/dist,120,Math.max(1440,canvas.width/Math.max(1,canvas.height)*510));const pt=scPoint(mx,my);scCamera.x+=g.anchor[0]-pt[0];scCamera.y+=g.anchor[1]-pt[1];scBound()}
// Capture only while editing; existing game gesture handlers remain untouched.
for(const type of ['touchstart','touchmove','touchend','touchcancel'])canvas.addEventListener(type,e=>{if(!scenarioEditing)return;e.preventDefault();e.stopImmediatePropagation();const t=e.touches;if(t.length>=2){if(sceneGesture?.kind!=='pinch')scPinchStart(t[0],t[1]);else scPinchMove(t[0],t[1]);return}if(sceneGesture?.kind==='pinch'){if(!t.length)sceneGesture=null;return}const a=(t[0]||e.changedTouches[0]);if(!a)return;if(type==='touchstart')scStart(a.clientX,a.clientY);else if(type==='touchmove')scMotion(a.clientX,a.clientY);else scEnd(a.clientX,a.clientY,type==='touchcancel')},{capture:true,passive:false});
for(const type of ['pointerdown','pointermove','pointerup','pointercancel','lostpointercapture'])canvas.addEventListener(type,e=>{if(!scenarioEditing||e.pointerType==='touch')return;e.stopImmediatePropagation();e.preventDefault();if(type==='pointerdown'){if(e.button!==0)return;scStart(e.clientX,e.clientY);try{canvas.setPointerCapture(e.pointerId)}catch(_){}}else if(type==='pointermove')scMotion(e.clientX,e.clientY);else scEnd(e.clientX,e.clientY,type!=='pointerup')},true);
canvas.addEventListener('wheel',e=>{if(!scenarioEditing)return;e.preventDefault();const a=scPoint(e.clientX,e.clientY);scCamera.w=clamp(scCamera.w*Math.exp(e.deltaY*.001),120,Math.max(1440,canvas.width/Math.max(1,canvas.height)*510));const b=scPoint(e.clientX,e.clientY);scCamera.x+=a[0]-b[0];scCamera.y+=a[1]-b[1];scBound()},{passive:false});


// Geometry and touch tools shared by all authored scenario objects.
function scOverlap(a,b){
 const [w,h]=scSize(a),[ww,hh]=scSize(b);
 return Math.abs(a.obj.x-b.obj.x)*2<w+ww-.0001&&Math.abs(a.obj.y-b.obj.y)*2<h+hh-.0001;
}
function scFirstOverlap(){
 const arr=scEntries();
 for(let i=0;i<arr.length;i++)for(let k=0;k<i;k++)if(scOverlap(arr[i],arr[k]))return [arr[k],arr[i]];
 return null;
}
function scCanOccupy(entry,ignore=new Set()){
 return scEntries().every(e=>e.obj===entry.obj||ignore.has(e.obj)||!scOverlap(entry,e));
}
function scBoundsOK(e){
 const o=e.obj,[w,h]=scSize(e),ex=e.type==='zombie';
 return o.x>= (ex?-240:Math.max(25,w/2))-.001
   &&o.x<= (ex?1200:Math.min(935,960-w/2))+.001
   &&o.y>=Math.max(24,h/2)-.001
   &&o.y<=Math.min(e.list===sceneDraft.blocks?416:392,416-h/2)+.001;
}
function scCopySpot(e){
 const [w,h]=scSize(e);
 for(const [dx,dy] of [[w+8,0],[-w-8,0],[0,-h-8],[0,h+8],[w+8,-h-8],[-w-8,-h-8],[w*2+12,0]]){
  const obj=scClone(e.obj);obj.x=Math.round(obj.x+dx);obj.y=Math.round(obj.y+dy);
  const candidate={type:e.type,obj,list:e.list};
  if(scBoundsOK(candidate)&&scCanOccupy(candidate))return obj;
 }
 scHint('附近没有足够空间复制，请先移动其他对象');
 return null;
}
// Avoid the native Android 100-option dropdown for spawn rounds.
function scStepNumber(parent,label,value,min,max,onChange){
 const row=scRow(parent,label),control=scNode('div','scstep');
 const minus=scButton('−',()=>set(Number(input.value)-1));
 const input=scNode('input');input.type='number';input.inputMode='numeric';input.min=min;input.max=max;input.value=value;input.setAttribute('aria-label',label);
 const plus=scButton('+',()=>set(Number(input.value)+1));
 const hint=scNode('span','scbadge',value===0?'开局':'');
 const set=n=>{n=clamp(Number.isFinite(n)?Math.round(n):min,min,max);input.value=n;minus.disabled=n===min;plus.disabled=n===max;hint.textContent=n===0?'开局':'第 '+n+' 轮后';onChange(n)};
 input.onchange=()=>set(Number(input.value));minus.disabled=value<=min;plus.disabled=value>=max;
 hint.textContent=value===0?'开局':'第 '+value+' 轮后';
 control.append(minus,input,plus,hint);row.append(control);return input;
}
// Repeated drag, resize, paste and coordinate edits share the same collision rule.
const scPreviousMotion=scMotion;
const scPreviousPanel=scRenderPanel;
scRenderPanel=function(){
 if(scenePanel!=='multi'){scPreviousPanel();return}
 const panel=sc('scPanel'),body=sc('scPanelBody');
 panel.classList.toggle('hidden',!scenarioEditing||!sceneSelection.length);
 body.replaceChildren();if(!sceneSelection.length)return;
 sc('scPanelTitle').textContent='已框选 '+sceneSelection.length+' 个对象';
 const info=scNode('div','scsecondary','拖动任一选中对象，可整体移动。支持统一复制与删除。');
 body.append(info);
 const actions=scActions(body);
 actions.append(scButton('复制所选',scCopySelection),scButton('删除所选',scDeleteSelection,'scdanger'),scButton('取消选择',()=>{
  sceneSelection=[];sceneSelectMode=false;scenePanel='';scRenderPanel();scChrome()
 }));
};
function scDeleteSelection(){
 const deletable=sceneSelection.filter(e=>e.list);
 if(!deletable.length)return scHint('炮台和子刊不可删除');
 scChange(()=>{for(const e of deletable){const i=e.list.indexOf(e.obj);if(i>=0)e.list.splice(i,1)}});
 sceneSelection=[];scenePanel='';scRenderPanel();scChrome();
}
function scCopySelection(){
 const originals=sceneSelection.filter(e=>e.list);
 if(!originals.length)return scHint('没有可复制对象');
 if(originals.some(e=>e.list.length+originals.filter(o=>o.list===e.list).length>scLimit(e.type)))
  return scHint('所选对象数量超过关卡上限');
 const offsets=[[80,0],[-80,0],[0,-80],[0,80],[160,0],[-160,0],[0,-160],[0,160]];
 for(const [dx,dy] of offsets){
  const copies=originals.map(e=>({type:e.type,list:e.list,obj:{...scClone(e.obj),x:Math.round(e.obj.x+dx),y:Math.round(e.obj.y+dy)}}));
  if(!copies.every(c=>scBoundsOK(c)&&scCanOccupy(c)))continue;
  if(copies.some((c,i)=>copies.slice(0,i).some(d=>scOverlap(c,d))))continue;
  scChange(()=>{for(const c of copies)c.list.push(c.obj)});
  sceneSelection=copies;scenePanel='multi';scRenderPanel();scChrome();scHint('已复制 '+copies.length+' 个对象');return;
 }
 scHint('找不到不重叠的复制位置，请先腾出空间');
}
const scPreviousStart=scStart,scPreviousEnd=scEnd;
scStart=function(px,py){
 if(!sceneSelectMode||sceneBrush){scPreviousStart(px,py);return}
 const [x,y]=scPoint(px,py),hit=scPickAt(x,y);
 if(hit&&sceneSelection.some(e=>e.obj===hit.obj)){
  sceneGesture={kind:'group',px,py,x,y,before:scSnap(),moved:false,
   original:sceneSelection.map(e=>({e,x:e.obj.x,y:e.obj.y}))};
 }else{
  sceneGesture={kind:'marquee',px,py,x,y,before:scSnap(),moved:false};
  sceneMarquee={x,y,x2:x,y2:y};
 }
};
scMotion=function(px,py){
 const g=sceneGesture;
 if(g?.kind==='marquee'){const [x,y]=scPoint(px,py);sceneMarquee={x:g.x,y:g.y,x2:x,y2:y};g.moved=Math.hypot(px-g.px,py-g.py)>7;return}
 if(g?.kind==='group'){
  if(Math.hypot(px-g.px,py-g.py)<7&&!g.moved)return;
  g.moved=true;const [x,y]=scPoint(px,py),dx=Math.round(x-g.x),dy=Math.round(y-g.y);
  const before=g.original.map(({e})=>[e.obj,e.obj.x,e.obj.y]);
  for(const {e,x:ox,y:oy} of g.original){e.obj.x=ox+dx;e.obj.y=oy+dy}
  if(!g.original.every(({e})=>scBoundsOK(e))||scFirstOverlap()){
   for(const [o,ox,oy] of before){o.x=ox;o.y=oy}scHint('所选物体无法移动到此处')
  }
  return;
 }
 const before=g?.kind==='size'?{...g.hit.obj}:null;
 scPreviousMotion(px,py);
 if(before&&(!scBoundsOK(g.hit)||!scCanOccupy(g.hit))){
  Object.assign(g.hit.obj,before);
  scHint('此尺寸会与其他物体重叠');
 }
};
scEnd=function(px,py,cancel=false){
 const g=sceneGesture;
 if(g?.kind==='marquee'){
  sceneGesture=null;sceneMarquee=null;
  if(cancel)return;
  if(!g.moved){
   const [x,y]=scPoint(px,py),hit=scPickAt(x,y);
   sceneSelection=hit?[hit]:[];
  }else{
   const [x,y]=scPoint(px,py),minX=Math.min(g.x,x),maxX=Math.max(g.x,x),minY=Math.min(g.y,y),maxY=Math.max(g.y,y);
   sceneSelection=scEntries().filter(e=>{
    const [w,h]=scSize(e),o=e.obj;
    return o.x+w/2>=minX&&o.x-w/2<=maxX&&o.y+h/2>=minY&&o.y-h/2<=maxY
   });
  }
  scenePick=null;scenePanel=sceneSelection.length?'multi':'';scRenderPanel();scChrome();
  scHint(sceneSelection.length?'已选择 '+sceneSelection.length+' 个对象':'没有选中对象');return;
 }
 if(g?.kind==='group'){
  sceneGesture=null;
  if(cancel){
   for(const {e,x,y} of g.original){e.obj.x=x;e.obj.y=y}
  }else if(g.moved)scHistory(g.before);
  else scPanelSet('multi');
  return;
 }
 scPreviousEnd(px,py,cancel)
};
