
const $=id=>document.getElementById(id),sleep=ms=>new Promise(r=>setTimeout(r,ms)),DIE=["","⚀","⚁","⚂","⚃","⚄","⚅"];
const roomPrefix=location.pathname.match(/^\/r\/[A-Fa-f0-9]{6}/)?.[0]||"";const seatStorage=k=>k+roomPrefix;
let token=localStorage.getItem(seatStorage("gh_token"))||"",playerId=localStorage.getItem(seatStorage("gh_player_id"))||"",seatKey=localStorage.getItem(seatStorage("gh_seat_key"))||"";
if(!seatKey){seatKey=(crypto.randomUUID?.()||("seat_"+Date.now()+"_"+Math.random().toString(36).slice(2)));localStorage.setItem(seatStorage("gh_seat_key"),seatKey)}
let state=null,polling=false,busy=false,refreshing=false,joining=false,reconnecting=false,selectedCards=new Set(),selectedDdzCards=new Set(),selectedCmTiles=new Set(),bidQty=1,bidFace=2;
let drawColor="#111111",drawWidth=7,eraser=false,drawing=false,currentPoints=[],renderedStrokeSeq=-1,drawCanvasRevision=-1,lastPhase="",timerHandle=null,strokeQueue=[],strokeSending=false;

function toast(msg){const t=$("toast");t.textContent=msg;t.classList.add("show");clearTimeout(window.__toast);window.__toast=setTimeout(()=>t.classList.remove("show"),1900)}
function setNet(s){$("net").className="net "+s}
function renderSafe(){try{render();return true}catch(e){console.error("界面渲染异常",e);const now=Date.now();if(!window.__lastRenderError||now-window.__lastRenderError>5000){toast("界面更新异常，请点击刷新");window.__lastRenderError=now}return false}}
async function api(path,opts={}){const c=new AbortController(),tm=setTimeout(()=>c.abort(),12000);try{const r=await fetch((roomPrefix&&/^\/api\/(join|state|action)(?:\?|$)/.test(path)?roomPrefix:"")+path,{cache:"no-store",headers:{"Content-Type":"application/json"},signal:c.signal,...opts});const tx=await r.text();let d={};try{d=JSON.parse(tx)}catch{}if(!r.ok)throw new Error(d.error||tx||("HTTP "+r.status));return d}finally{clearTimeout(tm)}}
function shell(){$("joinCard").classList.add("hidden");$("bottomBar").classList.remove("hidden");setNet("ok")}
async function join(){if(joining)return;joining=true;$("joinBtn").disabled=true;try{const name=$("nameInput").value.trim()||"玩家";localStorage.setItem("gh_name",name);const d=await api("/api/join",{method:"POST",body:JSON.stringify({name,token,playerId,seatKey,claim:localStorage.getItem(seatStorage("gh_room_claim"))||""})});if(d.ok===false)throw new Error(d.error);token=d.token;playerId=d.playerId;localStorage.setItem(seatStorage("gh_token"),token);localStorage.setItem(seatStorage("gh_player_id"),playerId);shell();poll()}catch(e){toast("加入失败："+e.message)}finally{joining=false;$("joinBtn").disabled=false}}
async function reconnect(){if(reconnecting)return false;reconnecting=true;try{const d=await api("/api/join",{method:"POST",body:JSON.stringify({name:localStorage.getItem("gh_name")||"玩家",token,playerId,seatKey,claim:localStorage.getItem(seatStorage("gh_room_claim"))||""})});if(!d.ok)return false;token=d.token;playerId=d.playerId;localStorage.setItem(seatStorage("gh_token"),token);localStorage.setItem(seatStorage("gh_player_id"),playerId);return true}catch(e){return false}finally{reconnecting=false}}
async function refresh(force=false){
  if(!token||refreshing||(!force&&busy))return null;
  refreshing=true;
  try{
    const drawArgs=`&drawSeq=${encodeURIComponent(renderedStrokeSeq)}&drawRevision=${encodeURIComponent(drawCanvasRevision)}`;
    const d=await api(`/api/state?token=${encodeURIComponent(token)}${drawArgs}&_=${Date.now()}`);
    state=d.state;setNet("ok");renderSafe();return d;
  }catch(e){
    setNet("wait");
    if(await reconnect()){
      try{const drawArgs=`&drawSeq=${encodeURIComponent(renderedStrokeSeq)}&drawRevision=${encodeURIComponent(drawCanvasRevision)}`;
    const d=await api(`/api/state?token=${encodeURIComponent(token)}${drawArgs}&_=${Date.now()}`);state=d.state;setNet("ok");renderSafe();return d}catch(_){setNet("bad")}
    }else setNet("bad");
    return null;
  }finally{refreshing=false}
}
async function poll(){if(polling)return;polling=true;while(polling){await refresh();let ms=document.hidden?3000:1500;if(state?.mode==="draw"&&state?.phase==="draw_play")ms=document.hidden?2600:1000;else if(["cards","dice","chuanma"].includes(state?.mode)&&state?.phase!=="lobby"&&state?.phase!=="finished")ms=document.hidden?3000:650;await sleep(ms)}}
async function action(type,extra={}){
  if(busy&&type!=="draw_stroke")return null;
  if(tgBusy()&&["cards_play","cards_challenge","dice_bid","dice_challenge","dice_exact","cm_discard","cm_respond","cm_self_hu","cm_gang","next_round"].includes(type))return null;
  const lock=type!=="draw_stroke",requestId=(crypto.randomUUID?.()||("req_"+Date.now()+"_"+Math.random()));
  if(lock)busy=true;
  try{
    while(refreshing)await sleep(40);
    let lastError=null;
    for(let attempt=0;attempt<3;attempt++){
      try{
        const d=await api("/api/action",{method:"POST",body:JSON.stringify({token,type,requestId,drawSeq:renderedStrokeSeq,drawRevision:drawCanvasRevision,...extra})});
        if(d.state){state=d.state;renderSafe()}
        if(!d.ok)toast(d.error||"状态已更新");
        return d;
      }catch(e){
        lastError=e;
        if(attempt<2)await sleep(280*(attempt+1));
      }
    }
    if(type!=="draw_stroke"){
      await refresh(true);
      toast("连接有波动，已同步最新状态");
    }
    return null;
  }finally{if(lock)busy=false}
}
function me(){return state?.players.find(p=>p.id===playerId)}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
function clearLocalSeat(){["gh_token","gh_player_id","gh_seat_key"].forEach(k=>localStorage.removeItem(seatStorage(k)))}
async function manualRefresh(){while(refreshing)await sleep(40);const d=await refresh(true);toast(d?"已刷新最新状态":"刷新失败，请检查连接")}
function endCurrentGame(){if(state?.isHost&&state.phase!=="lobby"&&confirm("结束当前游戏并回到房间？所有真人玩家将保持准备状态。"))action("reset")}
async function leaveRoom(){if(!state)return;if(state.phase!=="lobby"){if(confirm("牌局进行中暂离会保留座位，重新打开本页即可恢复。现在暂离？"))location.replace("about:blank");return}if(!confirm("确定退出房间并释放座位？"))return;try{const d=await api("/api/action",{method:"POST",body:JSON.stringify({token,type:"leave",requestId:(crypto.randomUUID?.()||Date.now()+"")})});if(!d.ok){toast(d.error);return}}catch(e){toast("退出失败，请重试");return}clearLocalSeat();location.href="/"}
function kickPlayer(id,name){if(confirm(`将 ${name} 移出房间？`))action("kick",{targetId:id})}
function renameSelf(oldName){const name=prompt("修改昵称",oldName);if(name&&name.trim()&&name.trim()!==oldName){localStorage.setItem("gh_name",name.trim());action("rename",{name:name.trim()})}}
function renderPlayers(el){el.innerHTML="";state.players.forEach(p=>{const d=document.createElement("div");const lobby=state.phase==="lobby";d.className="player"+(p.id===playerId?" me":"")+(state.turnPlayerId===p.id?" turn":"")+(p.out?" out":"")+(p.connected?"":" offline")+(lobby&&p.id===playerId?" self-edit":"");let meta=lobby?`${p.connected?"在线":"离线"} · ${p.ready?"已准备":"未准备"}`:(state.mode==="cards"?`🍷 ${p.life}`:state.mode==="dice"?`🎲 ${p.diceCount}`:state.mode==="draw"?`⭐ ${p.score}`:state.mode==="chuanma"?`${p.cmWon?"已胡 · ":""}${p.cmMissing?"缺"+({W:"万",T:"筒",B:"条"}[p.cmMissing])+" · ":""}${p.cmScore>=0?"+":""}${p.cmScore} · ${p.handCount}张`:`${p.role||"待定"} · ${p.handCount} 张`);if(!lobby&&!p.connected)meta+=" · 离线";d.innerHTML=`<div class="pname">${p.isBot?"🤖 ":""}${esc(p.name)}${p.id===state.hostPlayerId?" · 房主":""}</div><div class="pmeta">${meta}${lobby&&p.id===playerId?" · 点按改名":""}</div>`;if(lobby&&p.id===playerId)d.onclick=()=>renameSelf(p.name);if(lobby&&state.isHost&&p.id!==playerId&&!p.isBot){const k=document.createElement("button");k.className="seat-kick";k.textContent=p.connected?"移出房间":"清理离线座位";k.onclick=e=>{e.stopPropagation();kickPlayer(p.id,p.name)};d.appendChild(k)}el.appendChild(d)})}
function renderLobby(){const lobby=state.phase==="lobby";$("lobbyCard").classList.toggle("hidden",!lobby);$("gameCard").classList.toggle("hidden",lobby||state.phase==="finished");$("winnerCard").classList.toggle("hidden",state.phase!=="finished");$("settingsBtn").classList.toggle("hidden",!state.isHost||!lobby);$("endGameBtn").classList.toggle("hidden",!state.isHost||lobby);if(!lobby)return;renderPlayers($("playersLobby"));$("readyBtn").textContent=me()?.ready?"取消准备":"准备";["Cards","Dice","Draw","Ddz","Chuanma","Army","Siege"].forEach(x=>$("mode"+x).classList.toggle("active",state.mode===x.toLowerCase()));$("startBtn").classList.toggle("hidden",!state.isHost);$("startBtn").disabled=!state.canStart;const online=state.players.filter(p=>p.connected).length;$("lobbyHint").textContent=state.mode==="ddz"?`斗地主固定 3 人 · 在线 ${online}/${state.players.length}`:state.mode==="chuanma"?`川麻 2～4 名真人 · 不补机器人 · 在线 ${online}/${state.players.length}`:`2～4 人 · 在线 ${online}/${state.players.length}`;$("siegeItemCount").value=state.settings.siegeItemCount??13;$("siegeAmmo").value=state.settings.siegeAmmo??0;$("siegeMode").value=state.settings.siegeMode==="dynamic"?"random":state.settings.siegeMode??"random";$("siegeWind").value=state.settings.siegeWind??"medium";$("cardLives").value=state.settings.cardLives;$("diceStart").value=state.settings.diceStart;$("onesWild").checked=state.settings.onesWild;$("exactEnabled").checked=state.settings.exactEnabled;$("drawRounds").value=state.settings.drawRounds;$("drawTime").value=state.settings.drawTime;$("drawDifficulty").value=state.settings.drawDifficulty;$("drawLibrary").value=state.settings.drawLibrary||"random"}
