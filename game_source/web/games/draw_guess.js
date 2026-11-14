function canvas(){return $("drawCanvas")}
function drawStroke(ctx,s){ctx.save();ctx.lineCap="round";ctx.lineJoin="round";ctx.strokeStyle=s.color;ctx.lineWidth=s.width;if(s.erase){ctx.globalCompositeOperation="destination-out";ctx.lineWidth=s.width*2}ctx.beginPath();s.points.forEach((p,i)=>{const x=p[0]*ctx.canvas.width,y=p[1]*ctx.canvas.height;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});if(s.points.length===1)ctx.lineTo(s.points[0][0]*ctx.canvas.width+.1,s.points[0][1]*ctx.canvas.height+.1);ctx.stroke();ctx.restore()}
function applyDrawCanvas(force=false){
  if(state.mode!=="draw")return;
  const d=state.draw,c=canvas(),ctx=c.getContext("2d");
  const full=force||d.fullCanvas||drawCanvasRevision!==d.canvasRevision||renderedStrokeSeq>d.strokeSeq;
  if(full){ctx.clearRect(0,0,c.width,c.height);(d.strokes||[]).forEach(s=>drawStroke(ctx,s))}else{(d.strokes||[]).forEach(s=>drawStroke(ctx,s))}
  drawCanvasRevision=d.canvasRevision;renderedStrokeSeq=d.strokeSeq;
  $("canvasEmpty").classList.toggle("hidden",d.strokeSeq>0||(d.strokes||[]).length>0);
}
function startTimer(){if(timerHandle)return;timerHandle=setInterval(()=>{if(!state||state.mode!=="draw")return;const r=Math.max(0,Math.ceil((state.draw.deadline||0)-Date.now()/1000));$("drawTimer").textContent=r?` · ${r}s`:""},250)}
function renderDraw(){
  if(state.mode!=="draw")return;
  const d=state.draw,drawer=state.players.find(p=>p.id===d.drawerId),isDrawer=d.drawerId===playerId;
  $("drawKicker").textContent=state.phase==="draw_choose"?(isDrawer?"选题":"画家正在选题"):state.phase==="draw_play"?(isDrawer?"你的题目":"正在作画"):"答案";
  $("drawMain").textContent=state.phase==="draw_choose"?(isDrawer?"请选择":"请稍候"):state.phase==="draw_play"?(isDrawer?d.word:d.hint):(d.answer||"");
  $("drawSub").textContent=state.phase==="draw_play"?(isDrawer?`${d.libraryLabel} · 不能写字、数字或拼音`:`${drawer?.name||""} 正在画 · ${d.libraryLabel}`):state.phase==="draw_reveal"?d.result:`第 ${d.turnIndex+1}/${d.totalTurns} 题 · ${d.libraryLabel||""}`;
  $("wordChoicePanel").classList.toggle("hidden",!(state.phase==="draw_choose"&&isDrawer));const choiceKey=JSON.stringify(d.choices||[]);if($("wordChoices").dataset.key!==choiceKey){$("wordChoices").dataset.key=choiceKey;$("wordChoices").innerHTML="";
  (d.choices||[]).forEach((w,i)=>{const b=document.createElement("button");b.className="word-choice";b.innerHTML=`${esc(w.word)}<small>${esc(w.category)} · ${w.difficultyLabel} · ${w.libraryLabel}</small>`;b.onclick=()=>action("draw_choose",{index:i});$("wordChoices").appendChild(b)});}
  const showCanvas=["draw_play","draw_reveal"].includes(state.phase);$("canvasPanel").classList.toggle("hidden",!showCanvas);$("drawTools").classList.toggle("hidden",!(state.phase==="draw_play"&&isDrawer));
  const guessed=(d.correctIds||[]).includes(playerId);$("guessRow").classList.toggle("hidden",!(state.phase==="draw_play"&&!isDrawer&&!guessed));const guessKey=JSON.stringify(d.guesses||[]);if($("guessFeed").dataset.key!==guessKey){$("guessFeed").dataset.key=guessKey;$("guessFeed").innerHTML="";
  (d.guesses||[]).slice(-20).forEach(g=>{const x=document.createElement("div");x.className="guess-chip"+(g.correct?" correct":"");x.textContent=g.correct?`${g.name} 猜对了`:`${g.name}：${g.text}`;$("guessFeed").appendChild(x)});$("guessFeed").scrollTop=$("guessFeed").scrollHeight;}
  $("drawReveal").classList.toggle("hidden",state.phase!=="draw_reveal");$("drawResult").textContent=d.result||"";$("drawNextBtn").classList.toggle("hidden",!state.canAdvanceRound);
  applyDrawCanvas(drawCanvasRevision!==d.canvasRevision);startTimer();lastPhase=state.phase;
}

async function flushStrokeQueue(){
  if(strokeSending)return;strokeSending=true;
  try{
    while(strokeQueue.length){
      const payload=strokeQueue[0],requestId=(crypto.randomUUID?.()||("stroke_"+Date.now()+"_"+Math.random()));let done=false;
      for(let attempt=0;attempt<3&&!done;attempt++){
        try{
          const d=await api("/api/action",{method:"POST",body:JSON.stringify({token,type:"draw_stroke",requestId,...payload})});
          if(d.ok){renderedStrokeSeq=Math.max(renderedStrokeSeq,Number(d.strokeSeq||renderedStrokeSeq));drawCanvasRevision=Number(d.canvasRevision??drawCanvasRevision);done=true}else if(d.error){toast(d.error);done=true}
        }catch(e){if(attempt<2)await sleep(180*(attempt+1))}
      }
      strokeQueue.shift();
      if(!done){setNet("wait");await refresh(true)}
    }
  }finally{strokeSending=false}
}
function queueStroke(payload){strokeQueue.push(payload);if(strokeQueue.length>12)strokeQueue=strokeQueue.slice(-12);flushStrokeQueue()}
