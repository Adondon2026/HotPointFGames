const SUIT_SYMBOL={S:"♠",H:"♥",D:"♦",C:"♣"};
function ddzCardClass(c,mini=false){
  let cls=mini?"ddz-mini":"ddz-card";
  if(c.suit==="H"||c.suit==="D")cls+=" red-suit";
  if(c.rank==="BJ")cls+=" joker-black";
  if(c.rank==="RJ")cls+=" joker-red";
  return cls;
}
function ddzCardLabel(c){if(c.rank==="BJ")return "小王";if(c.rank==="RJ")return "大王";return c.rank}
function renderDdzCard(c,mini=false){
  const el=document.createElement("div");el.className=ddzCardClass(c,mini);
  if(mini){el.textContent=c.rank==="BJ"?"小王":c.rank==="RJ"?"大王":`${c.rank}${SUIT_SYMBOL[c.suit]||""}`;return el}
  const suit=SUIT_SYMBOL[c.suit]||"★";
  el.innerHTML=`<div class="rank">${ddzCardLabel(c)}</div><div class="suit">${c.rank==="BJ"?"♚":c.rank==="RJ"?"♛":suit}</div><div class="mini-rank">${c.rank==="BJ"||c.rank==="RJ"?"":suit}</div>`;
  return el;
}
function renderDdz(){
  if(state.mode!=="ddz")return;
  const d=state.ddz,turn=state.players.find(p=>p.id===state.turnPlayerId);
  const bidding=state.phase==="ddz_bidding",playing=state.phase==="ddz_play";
  $("ddzKicker").textContent=bidding?"叫地主":"经典斗地主";
  $("ddzMain").textContent=bidding?(d.highestBid?`当前 ${d.highestBid} 分`:"等待叫分"):(d.landlordName?`${d.landlordName} · 地主 · ${d.baseBid} 分`:"");
  const turnText=turn?.id===playerId?(bidding?"轮到你叫分":"轮到你出牌"):(d.botThinking?`${turn?.name||"机器人"} 思考中…`:`等待 ${turn?.name||""}`);
  $("ddzSub").textContent=bidding?turnText:`${turnText} · ${d.baseBid}分 × ${d.multiplier}倍`;
  $("ddzBottom").classList.toggle("hidden",!d.bottomCards?.length);
  $("ddzBottom").innerHTML="";
  (d.bottomCards||[]).forEach(c=>$("ddzBottom").appendChild(renderDdzCard(c,true)));

  const last=d.lastPlay;
  const bidText=(d.bidHistory||[]).map(x=>`${esc(x.playerName)}：${x.score?x.score+" 分":"不叫"}`).join("　");
  $("ddzLastPlay").innerHTML=last
    ?`${esc(last.playerName)}：${esc(last.comboLabel)}<div class="ddz-small-row" id="ddzLastCards"></div>`
    :(bidding?(bidText||"每人只能叫一次，分数必须高于当前叫分"):(d.message||"新一轮，请自由出牌"));
  if(last){
    const row=$("ddzLastCards");
    (last.cards||[]).forEach(c=>row.appendChild(renderDdzCard(c,true)));
  }

  const hand=$("ddzHand");hand.innerHTML="";
  const valid=new Set((state.myDdzCards||[]).map(c=>c.id));
  [...selectedDdzCards].forEach(id=>{if(!valid.has(id))selectedDdzCards.delete(id)});
  if(state.turnPlayerId!==playerId&&!bidding)selectedDdzCards.clear();
  (state.myDdzCards||[]).forEach((c,index)=>{
    const el=renderDdzCard(c,false);
    el.style.zIndex=String(index+1);
    el.classList.toggle("selected",selectedDdzCards.has(c.id));
    el.onclick=()=>{
      if(!playing||state.turnPlayerId!==playerId)return;
      if(selectedDdzCards.has(c.id))selectedDdzCards.delete(c.id);else selectedDdzCards.add(c.id);
      renderDdz();
    };
    hand.appendChild(el);
  });
  $("ddzSelection").textContent=selectedDdzCards.size?`已选 ${selectedDdzCards.size} 张`:(playing?"点牌选择，或使用“提示”":"先看牌，再决定叫分");

  $("ddzBidPanel").classList.toggle("hidden",!bidding);
  document.querySelectorAll("[data-ddz-bid]").forEach(btn=>{
    const score=Number(btn.dataset.ddzBid);
    btn.disabled=!bidding||state.turnPlayerId!==playerId||(score>0&&score<=d.highestBid);
  });
  $("ddzPlayPanel").classList.toggle("hidden",!playing);
  const myTurn=playing&&state.turnPlayerId===playerId;
  $("ddzPlayBtn").disabled=!myTurn||selectedDdzCards.size===0;
  $("ddzPassBtn").disabled=!myTurn||!last;
  $("ddzHintBtn").disabled=!myTurn;
}
