function renderDice(){
  if(state.mode!=="dice")return;
  const turn=state.players.find(p=>p.id===state.turnPlayerId),b=state.dice.currentBid;
  const maxDice=state.players.filter(p=>!p.out).reduce((sum,p)=>sum+Number(p.diceCount||0),0);
  bidQty=Math.max(1,Math.min(bidQty,Math.max(1,maxDice)));
  $("diceBid").textContent=b?`至少 ${b.quantity} 个 ${DIE[b.face]}`:"尚未叫骰";
  $("diceRuleNotice").textContent=state.settings.onesWild
    ?"叫骰表示“至少”有这么多。叫2～6点时，1点也算万能点；开你只在实际数量更少时成功，抓准必须刚好相等。"
    :"叫骰表示“至少”有这么多。当前1点不万能；开你只在实际数量更少时成功，抓准必须刚好相等。";
  $("diceTurnText").textContent=state.phase==="dice_reveal"?"本轮已结算":(turn?.id===playerId?"轮到你":"等待 "+(turn?.name||""));
  $("myDice").innerHTML="";
  (state.myDice||[]).forEach(n=>{const d=document.createElement("div");d.className="die";d.textContent=DIE[n];$("myDice").appendChild(d)});
  if(!(state.myDice||[]).length)$("myDice").innerHTML='<div class="muted">你已出局，正在观战</div>';
  normalizeDice();$("qtyValue").textContent=bidQty;$("faces").innerHTML="";
  for(let n=1;n<=6;n++){const f=document.createElement("button");f.className="face"+(bidFace===n?" active":"");f.textContent=DIE[n];f.onclick=()=>{bidFace=n;renderDice()};$("faces").appendChild(f)}
  const myTurn=state.phase==="dice_bidding"&&state.turnPlayerId===playerId&&!me()?.out;
  $("diceControls").classList.toggle("hidden",state.phase!=="dice_bidding");
  $("bidBtn").disabled=!myTurn||!diceValid();$("challengeDiceBtn").disabled=!myTurn||!b;$("exactBtn").disabled=!myTurn||!b||!state.settings.exactEnabled;
  const reveal=state.phase==="dice_reveal";$("diceReveal").classList.toggle("hidden",!reveal);
  if(reveal){
    $("diceResult").textContent=state.roundResult;
    const box=$("diceRevealHands");box.innerHTML="";
    (state.dice.revealed||[]).forEach(row=>{
      const line=document.createElement("div");line.className="dice-reveal-row";
      const name=document.createElement("div");name.className="dice-reveal-name";name.textContent=row.playerName;
      const dice=document.createElement("div");dice.className="dice-reveal-dice";
      (row.dice||[]).forEach(n=>{const x=document.createElement("span");x.textContent=DIE[n];dice.appendChild(x)});
      line.append(name,dice);box.appendChild(line);
    });
    $("diceNextBtn").classList.toggle("hidden",!state.canAdvanceRound);
  }
}

