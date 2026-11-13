const CM_SUIT_LABEL={W:"万",T:"筒",B:"条"};
function cmTileClass(tile,mini=false){return (mini?"cm-tile cm-mini":"cm-tile")+` suit-${tile.suit}`}
function renderCmTile(tile,mini=false){const el=document.createElement("div");el.className=cmTileClass(tile,mini);el.innerHTML=`<strong>${tile.rank}</strong><span>${CM_SUIT_LABEL[tile.suit]}</span>`;return el}
function cmSelectionValidExchange(){if(selectedCmTiles.size!==3)return false;const tiles=(state.chuanma.myHand||[]).filter(t=>selectedCmTiles.has(t.id));return tiles.length===3&&new Set(tiles.map(t=>t.suit)).size===1}
function selectedCmTile(){const id=[...selectedCmTiles][0];return (state?.chuanma?.myHand||[]).find(t=>t.id===id)}
// The hand is the only horizontal scroller. Native touch panning handles swipes;
// mouse dragging also works in a narrow desktop browser without selecting a tile.
let cmDrag=null,cmSuppressClickUntil=0;
function cmUpdateScroll(){const h=$('cmHand');h.classList.toggle('cm-scrollable',h.scrollWidth>h.clientWidth+2)}
const cmHandScroller=$('cmHand');
cmHandScroller.addEventListener('pointerdown',e=>{if(e.pointerType!=='mouse'||e.button!==0||cmHandScroller.scrollWidth<=cmHandScroller.clientWidth)return;cmDrag={id:e.pointerId,x:e.clientX,left:cmHandScroller.scrollLeft,moved:false};cmSuppressClickUntil=0},true);
cmHandScroller.addEventListener('pointermove',e=>{if(!cmDrag||cmDrag.id!==e.pointerId)return;const dx=e.clientX-cmDrag.x;if(!cmDrag.moved&&Math.abs(dx)<7)return;if(!cmDrag.moved){cmDrag.moved=true;cmHandScroller.setPointerCapture(e.pointerId)}cmHandScroller.scrollLeft=cmDrag.left-dx;e.preventDefault()});
function cmEndDrag(e){if(!cmDrag||cmDrag.id!==e.pointerId)return;if(cmDrag.moved)cmSuppressClickUntil=performance.now()+350;cmDrag=null}
window.addEventListener('pointerup',cmEndDrag);window.addEventListener('pointercancel',cmEndDrag);
cmHandScroller.addEventListener('click',e=>{if(performance.now()<cmSuppressClickUntil){e.preventDefault();e.stopImmediatePropagation();cmSuppressClickUntil=0}},true);
window.addEventListener('resize',cmUpdateScroll);
function renderChuanma(){
  if(state.mode!=="chuanma")return;
  const cm=state.chuanma,phase=state.phase,turn=state.players.find(p=>p.id===state.turnPlayerId),mePlayer=me();
  const phaseNames={cm_exchange:"换三张",cm_dingque:"定缺",cm_play:"血战到底",cm_response:"等待响应"};
  $("cmKicker").textContent=phaseNames[phase]||"四川麻将";
  $("cmMain").textContent=phase==="cm_exchange"?cm.exchangeDirection:phase==="cm_dingque"?"万 · 筒 · 条":(turn?.id===playerId?"轮到你":turn?`等待 ${turn.name}`:"等待其他玩家");
  $("cmSub").textContent=`牌墙 ${cm.wallCount} 张`;
  $("cmNotice").textContent=cm.message||"";

  const valid=new Set((cm.myHand||[]).map(t=>t.id));[...selectedCmTiles].forEach(id=>{if(!valid.has(id))selectedCmTiles.delete(id)});
  if(phase!=="cm_exchange"&&!(phase==="cm_play"&&state.turnPlayerId===playerId))selectedCmTiles.clear();
  const hand=$("cmHand"),source=cm.myHand||[],drawn=source.find(t=>t.id===cm.myDrawnId),tiles=drawn?source.filter(t=>t.id!==drawn.id).concat(drawn):source;
  const selection=[...selectedCmTiles].join(','),key=JSON.stringify([tiles,cm.myDrawnId,selection,phase,cm.canDiscard,cm.exchangeSubmitted,cm.myMissing,cm.myWon,tgBusy()]);
  if(hand.dataset.key!==key){const previousScroll=hand.scrollLeft, previousDraw=hand.dataset.drawnId||'', drawId=String(cm.myDrawnId||'');const match=String(state.tableMatch||'legacy'),newMatch=hand.dataset.match!==match;const newDraw=!!drawId&&(drawId!==previousDraw||newMatch);hand.dataset.match=match;hand.dataset.drawnId=drawId;hand.dataset.key=key;hand.replaceChildren();hand.classList.remove('cm-two-rows');hand.style.setProperty('--cm-count',String(Math.max(1,tiles.length)));hand.style.setProperty('--cm-draw-gap',drawn?'8px':'0px');
    const row=document.createElement('div');row.className='cm-hand-row';hand.append(row);
    const selected=source.find(t=>selectedCmTiles.has(t.id)),mustMissing=cm.myMissing&&source.some(t=>t.suit===cm.myMissing);
    tiles.forEach(tile=>{const el=document.createElement('button');el.type='button';el.className=cmTileClass(tile);el.innerHTML=`<strong>${tile.rank}</strong><span>${CM_SUIT_LABEL[tile.suit]}</span>`;el.dataset.tileId=tile.id;el.setAttribute('aria-label',`${tile.rank}${CM_SUIT_LABEL[tile.suit]}${tile.id===cm.myDrawnId?'，刚摸到':''}`);el.setAttribute('aria-pressed',String(selectedCmTiles.has(tile.id)));el.classList.toggle('selected',selectedCmTiles.has(tile.id));el.classList.toggle('drawn',tile.id===cm.myDrawnId);el.classList.toggle('missing-suit',!!cm.myMissing&&tile.suit===cm.myMissing);
      const blocked=(phase==='cm_exchange'&&selected&&selected.suit!==tile.suit)||(phase==='cm_play'&&cm.canDiscard&&mustMissing&&tile.suit!==cm.myMissing);el.classList.toggle('ineligible',!!blocked);el.disabled=!!blocked||tgBusy()||!((phase==='cm_exchange'&&!cm.exchangeSubmitted)||(phase==='cm_play'&&cm.canDiscard&&state.turnPlayerId===playerId));
      el.onclick=()=>{if(el.disabled||tgBusy())return;if(state.phase==='cm_exchange'){if(selectedCmTiles.has(tile.id))selectedCmTiles.delete(tile.id);else if(selectedCmTiles.size<3)selectedCmTiles.add(tile.id);else return}else if(state.phase==='cm_play'&&state.chuanma.canDiscard){if(selectedCmTiles.has(tile.id))selectedCmTiles.clear();else{selectedCmTiles.clear();selectedCmTiles.add(tile.id)}}renderSafe()};row.append(el);
    });if(cm.myWon)hand.innerHTML='<div class="muted">你已胡牌 · 观战中</div>';
    // Preserve the player's browsing position through polling and selection; reveal only a genuinely new draw.
    hand.scrollLeft=newDraw?hand.scrollWidth:newMatch?0:previousScroll;
    if(newDraw)requestAnimationFrame(()=>{if(hand.dataset.drawnId===drawId&&hand.dataset.match===match){hand.scrollLeft=hand.scrollWidth;cmUpdateScroll()}});
    cmUpdateScroll();
  }
  const preview=$('cmPickedPreview'),picked=phase==='cm_play'?selectedCmTile():null;preview.classList.toggle('hidden',!picked);if(picked){preview.replaceChildren(renderCmTile(picked,true));preview.setAttribute('aria-label','已选 '+picked.rank+CM_SUIT_LABEL[picked.suit])}else preview.replaceChildren();

  $("cmExchangePanel").classList.toggle("hidden",phase!=="cm_exchange"||cm.exchangeSubmitted);
  $("cmDingquePanel").classList.toggle("hidden",phase!=="cm_dingque"||cm.dingqueSubmitted);
  $("cmPlayPanel").classList.toggle("hidden",phase!=="cm_play"||state.turnPlayerId!==playerId||cm.myWon);
  $("cmResponsePanel").classList.toggle("hidden",phase!=="cm_response"||!cm.responseOptions?.length||cm.responded);
  $("cmExchangeBtn").disabled=cm.exchangeSubmitted||!cmSelectionValidExchange();
  $("cmExchangeBtn").textContent=cm.exchangeSubmitted?"已选好，等待其他人":"确认换三张";
  document.querySelectorAll("[data-cm-missing]").forEach(btn=>btn.disabled=cm.dingqueSubmitted);
  document.querySelectorAll("[data-cm-response]").forEach(btn=>btn.disabled=!(cm.responseOptions||[]).includes(btn.dataset.cmResponse));
  $("cmHuBtn").disabled=!cm.canHu;
  $("cmGangBtn").disabled=!(cm.gangOptions||[]).length;
  $("cmDiscardBtn").disabled=!cm.canDiscard||selectedCmTiles.size!==1;
  if(phase==="cm_exchange")$("cmSelection").textContent=cm.exchangeSubmitted?"已提交，不能再修改":selectedCmTiles.size?`已选 ${selectedCmTiles.size}/3 张（必须同花色）`:"请选择三张同花色的牌";
  else if(phase==="cm_dingque")$("cmSelection").textContent=cm.dingqueSubmitted?"已完成定缺，等待其他人":"选择一个你准备优先打空的花色";
  else if(phase==="cm_response")$("cmSelection").textContent=cm.responded?"已响应，等待其他玩家":"请选择碰、杠、胡或过";
  else $("cmSelection").textContent=selectedCmTiles.size?"已选 · 确认出牌":cm.canDiscard&&cm.myMissing&&cm.myHand.some(t=>t.suit===cm.myMissing)?"先打缺门":"";
}

$("cmExchangeBtn").onclick=()=>action("cm_exchange",{tileIds:[...selectedCmTiles]}).then(d=>{if(d?.ok)selectedCmTiles.clear()});
document.querySelectorAll("[data-cm-missing]").forEach(btn=>btn.onclick=()=>action("cm_dingque",{suit:btn.dataset.cmMissing}));
document.querySelectorAll("[data-cm-response]").forEach(btn=>btn.onclick=()=>action("cm_respond",{choice:btn.dataset.cmResponse}));
$("cmDiscardBtn").onclick=async()=>{const tile=selectedCmTile();if(!tile)return;const d=await action("cm_discard",{tileId:tile.id});if(d?.ok)selectedCmTiles.clear()};
$("cmHuBtn").onclick=()=>action("cm_self_hu");
$("cmGangBtn").onclick=()=>{const options=state.chuanma.gangOptions||[];let option=null;const tile=selectedCmTile();if(tile)option=options.find(x=>x.suit===tile.suit&&x.rank===tile.rank);option=option||options[0];if(option)action("cm_gang",{suit:option.suit,rank:option.rank})};
