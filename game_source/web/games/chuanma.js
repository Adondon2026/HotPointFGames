const CM_SUIT_LABEL={W:"万",T:"筒",B:"条"};
function cmTileClass(tile,mini=false){return (mini?"cm-tile cm-mini":"cm-tile")+` suit-${tile.suit}`}
function renderCmTile(tile,mini=false){const el=document.createElement("div");el.className=cmTileClass(tile,mini);el.innerHTML=`<strong>${tile.rank}</strong><span>${CM_SUIT_LABEL[tile.suit]}</span>`;return el}
function cmSelectionValidExchange(){if(selectedCmTiles.size!==3)return false;const tiles=(state.chuanma.myHand||[]).filter(t=>selectedCmTiles.has(t.id));return tiles.length===3&&new Set(tiles.map(t=>t.suit)).size===1}
function selectedCmTile(){const id=[...selectedCmTiles][0];return (state?.chuanma?.myHand||[]).find(t=>t.id===id)}
function renderChuanma(){
  if(state.mode!=="chuanma")return;
  const cm=state.chuanma,phase=state.phase,turn=state.players.find(p=>p.id===state.turnPlayerId),mePlayer=me();
  const phaseNames={cm_exchange:"换三张",cm_dingque:"定缺",cm_play:"血战到底",cm_response:"等待响应"};
  $("cmKicker").textContent=phaseNames[phase]||"四川麻将";
  $("cmMain").textContent=phase==="cm_exchange"?cm.exchangeDirection:phase==="cm_dingque"?"万 · 筒 · 条":(turn?.id===playerId?"轮到你":turn?`等待 ${turn.name}`:"等待其他玩家");
  $("cmSub").textContent=`牌墙 ${cm.wallCount} 张${cm.myMissing?` · 你缺${CM_SUIT_LABEL[cm.myMissing]}`:""}`;
  $("cmNotice").textContent=cm.message||"";

  const valid=new Set((cm.myHand||[]).map(t=>t.id));[...selectedCmTiles].forEach(id=>{if(!valid.has(id))selectedCmTiles.delete(id)});
  if(phase!=="cm_exchange"&&!(phase==="cm_play"&&state.turnPlayerId===playerId))selectedCmTiles.clear();
  const hand=$("cmHand");hand.innerHTML="";
  const tiles=cm.myHand||[];const split=matchMedia('(orientation:portrait) and (max-width:520px)').matches&&tiles.length>=10;
  let cut=tiles.length;if(split){const candidates=Array.from({length:tiles.length-1},(_,i)=>i+1).filter(i=>i>=Math.floor(tiles.length/2)-2&&i<=Math.ceil(tiles.length/2)+2&&tiles[i-1].suit!==tiles[i].suit);cut=candidates.sort((a,b)=>Math.abs(a-tiles.length/2)-Math.abs(b-tiles.length/2))[0]||Math.ceil(tiles.length/2)}
  const rows=[document.createElement('div')];rows[0].className='cm-hand-row';hand.append(rows[0]);if(split){rows.push(document.createElement('div'));rows[1].className='cm-hand-row';hand.append(rows[1])}hand.classList.toggle('cm-two-rows',split);rows[0].style.setProperty('--cm-count',String(Math.max(1,cut)));if(split)rows[1].style.setProperty('--cm-count',String(Math.max(1,tiles.length-cut)));
  (cm.myHand||[]).forEach((tile,index)=>{
    const el=renderCmTile(tile,false);el.style.zIndex=String(index+1);el.classList.toggle("selected",selectedCmTiles.has(tile.id));
    if(tile.id===cm.myDrawnId)el.classList.add("drawn");
    if(cm.myMissing&&tile.suit===cm.myMissing)el.classList.add("missing-suit");
    const selected=(cm.myHand||[]).find(t=>selectedCmTiles.has(t.id));
    const blocked=(phase==="cm_exchange"&&selected&&selected.suit!==tile.suit)||(phase==="cm_play"&&cm.canDiscard&&cm.myMissing&&(cm.myHand||[]).some(t=>t.suit===cm.myMissing)&&tile.suit!==cm.myMissing);
    if(blocked)el.classList.add("ineligible");
    el.onclick=()=>{
      if(blocked||tgBusy())return;
      if(phase==="cm_exchange"){
        if(cm.exchangeSubmitted)return;
        if(selectedCmTiles.has(tile.id))selectedCmTiles.delete(tile.id);else if(selectedCmTiles.size<3)selectedCmTiles.add(tile.id);else toast("换三张最多选择 3 张");
      }else if(phase==="cm_play"&&state.turnPlayerId===playerId&&cm.canDiscard){
        selectedCmTiles.clear();selectedCmTiles.add(tile.id);
      }
      renderChuanma();
    };rows[split&&index>=cut?1:0].appendChild(el);
  });
  if(cm.myWon)hand.innerHTML='<div class="muted">你已经胡牌，正在观看血战继续</div>';

  $("cmExchangePanel").classList.toggle("hidden",phase!=="cm_exchange");
  $("cmDingquePanel").classList.toggle("hidden",phase!=="cm_dingque");
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
  else $("cmSelection").textContent=selectedCmTiles.size?"已选 1 张":cm.canDiscard&&cm.myMissing&&cm.myHand.some(t=>t.suit===cm.myMissing)?"优先打缺门":"";
}

$("cmExchangeBtn").onclick=()=>action("cm_exchange",{tileIds:[...selectedCmTiles]}).then(d=>{if(d?.ok)selectedCmTiles.clear()});
document.querySelectorAll("[data-cm-missing]").forEach(btn=>btn.onclick=()=>action("cm_dingque",{suit:btn.dataset.cmMissing}));
document.querySelectorAll("[data-cm-response]").forEach(btn=>btn.onclick=()=>action("cm_respond",{choice:btn.dataset.cmResponse}));
$("cmDiscardBtn").onclick=async()=>{const tile=selectedCmTile();if(!tile)return;const d=await action("cm_discard",{tileId:tile.id});if(d?.ok)selectedCmTiles.clear()};
$("cmHuBtn").onclick=()=>action("cm_self_hu");
$("cmGangBtn").onclick=()=>{const options=state.chuanma.gangOptions||[];let option=null;const tile=selectedCmTile();if(tile)option=options.find(x=>x.suit===tile.suit&&x.rank===tile.rank);option=option||options[0];if(option)action("cm_gang",{suit:option.suit,rank:option.rank})};
