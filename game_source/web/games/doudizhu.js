const SUIT_SYMBOL={S:"♠",H:"♥",D:"♦",C:"♣"};
function ddzCardClass(c,mini=false){return (mini?"ddz-mini":"ddz-card")+(c.suit==="H"||c.suit==="D"?" red-suit":"")+(c.rank==="BJ"?" joker-black":c.rank==="RJ"?" joker-red":"")}
function ddzCardLabel(c){return c.rank==="BJ"?"小王":c.rank==="RJ"?"大王":c.rank}
function renderDdzCard(c,mini=false){
 const el=document.createElement(mini?'div':'button');el.className=ddzCardClass(c,mini);if(!mini)el.type='button';
 const suit=SUIT_SYMBOL[c.suit]||'★';el.innerHTML=`<span class="rank">${ddzCardLabel(c)}</span><span class="suit">${suit}</span>`;
 el.setAttribute('aria-label',ddzCardLabel(c)+suit);return el;
}
// A single ordered presentation queue, distinct from authoritative rule state.
let ddzDeal=null,ddzSeen=0,ddzQueue=[],ddzShown=null,ddzTimer=null,ddzCurrent=null,ddzSeatEvents={},ddzHandKey='',ddzBottomKey='',ddzHistoryKey='',ddzFresh=false,ddzWasLobby=false,ddzFinalDeferred=false;
function ddzResetPresentation(){clearTimeout(ddzTimer);ddzTimer=null;ddzDeal=null;ddzSeen=0;ddzQueue=[];ddzShown=null;ddzCurrent=null;ddzSeatEvents={};ddzHandKey='';ddzBottomKey='';ddzHistoryKey='';ddzFresh=false;ddzFinalDeferred=false;selectedDdzCards.clear();$('ddzBottom').classList.add('hidden');$('ddzHistory').classList.add('hidden');$('ddzBottomToggle').setAttribute('aria-expanded','false');$('ddzHistoryToggle').setAttribute('aria-expanded','false')}
function ddzEventText(e){return e.kind==='play'?e.comboLabel:e.kind==='pass'?'不出':e.kind==='bid'?(e.score?`叫 ${e.score} 分`:'不叫'):e.kind==='landlord'?'成为地主':e.kind==='trick'?'重新领出':''}
function ddzApplyEvent(e){ddzCurrent=e;if(e.kind==='play'){ddzShown=e;ddzSeatEvents={}}if(e.kind==='trick'){ddzShown=null;ddzSeatEvents={}}if(e.kind==='landlord'){ddzShown=null;ddzSeatEvents={}}if(e.playerId)ddzSeatEvents[e.playerId]=e}
function ddzRunQueue(){if(ddzTimer||!ddzQueue.length)return;const e=ddzQueue.shift();ddzApplyEvent(e);const ms=e.kind==='landlord'?1150:e.kind==='play'?(e.comboLabel==='炸弹'||e.comboLabel==='王炸'?1100:750):e.kind==='trick'?450:600;ddzTimer=setTimeout(()=>{ddzTimer=null;ddzRunQueue();if(state?.mode==='ddz')renderSafe()},ms)}
function ddzSync(d){
 const key=d.dealId||'legacy:'+state.roundNo,events=d.events||[];
 if(key!==ddzDeal){const fresh=ddzWasLobby||ddzDeal!==null;ddzResetPresentation();ddzDeal=key;ddzWasLobby=false;ddzFresh=fresh;if(!fresh){events.forEach(ddzApplyEvent);ddzSeen=events.at(-1)?.seq||0;ddzShown=d.lastPlay;return}}
 const incoming=events.filter(e=>e.seq>ddzSeen);if(incoming.length){ddzSeen=incoming.at(-1).seq;ddzQueue.push(...incoming)}
 // Reconnect / long background gap: restore the current table, not a long replay.
 if(document.hidden||ddzQueue.length>12){clearTimeout(ddzTimer);ddzTimer=null;ddzQueue.forEach(ddzApplyEvent);ddzQueue=[];ddzShown=d.lastPlay;return}
 ddzRunQueue();if(!ddzTimer&&!ddzQueue.length)ddzShown=d.lastPlay;
}
function ddzBusy(){return !!ddzTimer||ddzQueue.length>0}
function ddzShowCards(el,cards){el.replaceChildren(...(cards||[]).map(c=>renderDdzCard(c,true)))}
function ddzRenderOpponent(el,p){if(!p){el.replaceChildren();return}const event=ddzSeatEvents[p.id];const active=ddzBusy()?ddzCurrent?.playerId===p.id:state.turnPlayerId===p.id;el.classList.toggle('active',active);el.innerHTML=`<div class="ddz-avatar">${p.isBot?'机':'友'}</div><div class="ddz-op-info"><strong>${esc(p.name.replace(/^机器人/,''))}</strong><span>${p.role==='待定'?'':esc(p.role)+' · '}${p.handCount} 张</span></div><span class="ddz-seat-action">${event?.kind==='pass'?'不出':event?.kind==='bid'?ddzEventText(event):''}</span>`}
function renderDdz(){
 if(state.mode!=='ddz')return;const d=state.ddz,bidding=state.phase==='ddz_bidding',playing=state.phase==='ddz_play',ended=state.phase==='finished';ddzSync(d);const presenting=ddzBusy(),turn=state.players.find(p=>p.id===state.turnPlayerId),myTurn=!presenting&&state.turnPlayerId===playerId;
 const meIndex=state.players.findIndex(p=>p.id===playerId),others=state.players.length===3?[state.players[(meIndex+2)%3],state.players[(meIndex+1)%3]]:state.players.filter(p=>p.id!==playerId);ddzRenderOpponent($('ddzLeft'),others[0]);ddzRenderOpponent($('ddzRight'),others[1]);
 $('ddzKicker').textContent='斗地主';$('ddzMain').textContent=bidding?'叫地主':`底分 ${d.baseBid||1} · ${d.multiplier||1} 倍`;
 const bottom=d.bottomCards||[];const bkey=bottom.map(c=>c.id).join(',');$('ddzBottomToggle').classList.toggle('hidden',!bottom.length);if(bkey!==ddzBottomKey){ddzBottomKey=bkey;ddzShowCards($('ddzBottom'),bottom)}
 const last=presenting?ddzShown:d.lastPlay,evt=ddzCurrent;const landlord=presenting&&evt?.kind==='landlord';const cards=landlord?evt.cards:last?.cards;
 const center=$('ddzLastPlay');const centerKey=JSON.stringify([bidding,last,landlord?evt:null,presenting&&evt?.kind==='bid'?evt:null,d.highestBid]);if(center.dataset.key!==centerKey){center.dataset.key=centerKey;center.replaceChildren();const label=document.createElement('div');label.className='ddz-play-label';label.textContent=landlord?`${evt.playerName} 成为地主 · 底牌`:last?`${last.playerName.replace(/^机器人/,'')} · ${last.comboLabel}`:bidding?(d.highestBid?`当前 ${d.highestBid} 分`:'等待叫分'):'新一轮 · 自由出牌';center.append(label);if(cards?.length){const row=document.createElement('div');row.className='ddz-small-row';row.id='ddzLastCards';ddzShowCards(row,cards);center.append(row)}}
 $('ddzEventLine').textContent=evt&&evt.kind!=='play'&&!landlord?`${evt.playerName?.replace(/^机器人/,'')||''} ${ddzEventText(evt)}`:'';
 $('ddzSub').textContent=presenting?'正在展示行动':myTurn?(bidding?'轮到你叫分':'轮到你出牌'):ended?'本局结束':turn?`等待 ${turn.name.replace(/^机器人/,'')}`:'等待';$('ddzSub').classList.toggle('your-turn',myTurn);
 $('ddzMyInfo').textContent=`${me()?.role==='待定'?'你':me()?.role||'你'} · ${state.myDdzCards.length} 张`;
 const hand=$('ddzHand'),valid=new Set(state.myDdzCards.map(c=>c.id));[...selectedDdzCards].forEach(id=>{if(!valid.has(id))selectedDdzCards.delete(id)});const key=state.myDdzCards.map(c=>c.id).join(',');if(key!==ddzHandKey){ddzHandKey=key;const x=hand.scrollLeft;hand.replaceChildren();state.myDdzCards.forEach((c,i)=>{const el=renderDdzCard(c);el.dataset.cardId=c.id;el.style.zIndex=String(i+1);el.onclick=()=>{if(state.phase!=='ddz_play'||ddzBusy()||state.turnPlayerId!==playerId)return;if(selectedDdzCards.has(c.id))selectedDdzCards.delete(c.id);else selectedDdzCards.add(c.id);renderDdz()};hand.append(el)});hand.scrollLeft=x}
 [...hand.children].forEach(el=>{const sel=selectedDdzCards.has(el.dataset.cardId);el.classList.toggle('selected',sel);el.setAttribute('aria-pressed',String(sel))});$('ddzSelection').textContent=selectedDdzCards.size?`已选 ${selectedDdzCards.size} 张`:'';
 $('ddzBidPanel').classList.toggle('hidden',!bidding);$('ddzPlayPanel').classList.toggle('hidden',!playing);document.querySelectorAll('[data-ddz-bid]').forEach(btn=>{const score=Number(btn.dataset.ddzBid);btn.disabled=!bidding||!myTurn||(score>0&&score<=d.highestBid)});$('ddzPlayBtn').disabled=!playing||!myTurn||!selectedDdzCards.size;$('ddzPassBtn').disabled=!playing||!myTurn||!d.lastPlay;$('ddzHintBtn').disabled=!playing||!myTurn;
 const hkey=ddzDeal+':'+ddzSeen;if(hkey!==ddzHistoryKey){ddzHistoryKey=hkey;const list=$('ddzHistoryList');list.replaceChildren(...(d.events||[]).slice().reverse().map(e=>{const item=document.createElement('div');item.className='ddz-history-row';const t=document.createElement('span');t.textContent=`${e.playerName||''} ${ddzEventText(e)}`;item.append(t);if(e.cards?.length){const row=document.createElement('div');row.className='ddz-small-row';ddzShowCards(row,e.cards);item.append(row)}return item}));if(!list.children.length)list.textContent='暂无行动记录'}
}
$('ddzBottomToggle').onclick=()=>{$('ddzHistory').classList.add('hidden');$('ddzHistoryToggle').setAttribute('aria-expanded','false');const el=$('ddzBottom');el.classList.toggle('hidden');$('ddzBottomToggle').setAttribute('aria-expanded',String(!el.classList.contains('hidden')))};
$('ddzHistoryToggle').onclick=()=>{$('ddzBottom').classList.add('hidden');$('ddzBottomToggle').setAttribute('aria-expanded','false');const el=$('ddzHistory');el.classList.toggle('hidden');$('ddzHistoryToggle').setAttribute('aria-expanded',String(!el.classList.contains('hidden')))};
$('ddzHistoryClose').onclick=()=>{$('ddzHistory').classList.add('hidden');$('ddzHistoryToggle').setAttribute('aria-expanded','false')};
$('ddzRulesBtn').onclick=()=>liteRules();
