function renderDice(){
  if(state.mode!=="dice")return;
  const turn=state.players.find(p=>p.id===state.turnPlayerId),b=state.dice.currentBid;
  const maxDice=state.players.filter(p=>!p.out).reduce((sum,p)=>sum+Number(p.diceCount||0),0);
  bidQty=Math.max(1,Math.min(bidQty,Math.max(1,maxDice)));
  tgBid(b);
  $("diceRuleNotice").textContent=state.settings.onesWild
    ?"1 点万能"
    :"1 点不万能";
  $("diceTurnText").textContent=state.phase==="dice_reveal"?"本轮已结算":(turn?.id===playerId?"轮到你":"等待 "+(turn?.name||""));
  $("myDice").innerHTML="";
  (state.myDice||[]).forEach(n=>{const d=document.createElement("div");d.className="die";d.append(tgDie(n));$("myDice").appendChild(d)});
  if(!(state.myDice||[]).length)$("myDice").innerHTML='<div class="muted">你已出局，正在观战</div>';
  normalizeDice();bidQty=Math.min(bidQty,Math.max(1,maxDice));$("qtyValue").textContent=bidQty;$("faces").innerHTML="";
  for(let n=1;n<=6;n++){const f=document.createElement("button");f.className="face"+(bidFace===n?" active":"");f.append(tgDie(n));f.setAttribute("aria-label",n+" 点");f.onclick=()=>{bidFace=n;renderDice()};$("faces").appendChild(f)}
  const myTurn=!tgBusy()&&state.phase==="dice_bidding"&&state.turnPlayerId===playerId&&!me()?.out;
  $("diceControls").classList.toggle("hidden",state.phase!=="dice_bidding");
  $("bidBtn").disabled=!myTurn||!diceValid();$("challengeDiceBtn").disabled=!myTurn||!b;$("exactBtn").disabled=!myTurn||!b||!state.settings.exactEnabled;
  const reveal=state.phase==="dice_reveal"||state.phase==="finished";$("diceReveal").classList.toggle("hidden",!reveal);
  if(reveal){
    $("diceResult").textContent=state.roundResult;
    const box=$("diceRevealHands");box.innerHTML="";
    (state.dice.revealed||[]).forEach(row=>{
      const line=document.createElement("div");line.className="dice-reveal-row";
      const name=document.createElement("div");name.className="dice-reveal-name";name.textContent=row.playerName;
      const dice=document.createElement("div");dice.className="dice-reveal-dice";
      (row.dice||[]).forEach(n=>{const x=document.createElement("span");x.append(tgDie(n));dice.appendChild(x)});
      line.append(name,dice);box.appendChild(line);
    });
    $("diceNextBtn").classList.toggle("hidden",!state.canAdvanceRound);
  }
}

