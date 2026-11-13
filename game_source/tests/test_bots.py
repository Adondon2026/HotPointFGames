"""Exercise complete solo games using exactly the same action handlers as the browser."""
import importlib.util, os, tempfile, time, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='hotpoint-bot-')
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
handler=object.__new__(g.Handler)
def setup(mode):
 g.STATE=g.fresh_state();g.TOKENS={};g.STATE['mode']=mode;g.STATE['hostPlayerId']='human'
 g.add_local_bot();p=g.STATE['players'][0];p.update(id='human',name='玩家',isBot=False,ready=False);return p
def act(p,kind,**data):
 result=handler.handle_action(p,kind,data);assert result[1]==200,(kind,result);return result
for mode in ('cards','dice','chuanma','ddz','draw'):
 with g.LOCK:
  p=setup(mode)
  act(p,'add_bot');assert len(g.STATE['players'])==2
  bot=g.STATE['players'][1];act(p,'remove_bot',targetId=bot['id']);assert len(g.STATE['players'])==1
  if mode=='chuanma':
   act(p,'add_bot');act(p,'add_bot');act(p,'add_bot')
  act(p,'solo_start');assert len(g.STATE['players'])==(3 if mode=='ddz' else 4 if mode=='chuanma' else 2)
  assert g.STATE['matchId'];steps=0
  while g.STATE['phase']!='finished' and steps<2000:
   steps+=1;phase=g.STATE['phase'];players=g.STATE['players']
   if phase.endswith('_reveal'):act(p,'next_round');continue
   if mode=='draw':
    if phase=='draw_choose':assert g.bot_step(g.player_by_id(g.STATE['draw']['drawerId']))
    else:assert g.STATE['draw']['strokes'];act(p,'draw_guess',guess=g.STATE['draw']['word'])
   elif mode=='ddz':
    turn=g.player_by_id(g.STATE['turnPlayerId']);g.STATE['ddz']['botDueAt']=0
    if turn.get('isBot'):assert g.ddz_bot_step()
    elif phase=='ddz_bidding':act(turn,'ddz_bid',score=g.choose_ddz_bot_bid(turn))
    else:
     cards=g.choose_ddz_bot_play(turn)
     if cards:act(turn,'ddz_play',cardIds=[c['id'] for c in cards])
     else:act(turn,'ddz_pass')
   elif mode=='chuanma':
    cm=g.STATE['chuanma']
    if phase in ('cm_exchange','cm_dingque'):
     key='exchangeSelections' if phase=='cm_exchange' else 'dingqueSelections';turn=next(x for x in players if x['id'] not in cm[key])
    elif phase=='cm_response':turn=g.player_by_id(next(x for x in cm['responseOptions'] if x not in cm['responses']))
    else:turn=g.player_by_id(g.STATE['turnPlayerId'])
    assert g.bot_step(turn),(phase,turn)
   else:assert g.bot_step(g.player_by_id(g.STATE['turnPlayerId']))
  assert g.STATE['phase']=='finished',(mode,steps,g.STATE['phase']);print(mode,'complete',steps)
  act(p,'reset');assert g.STATE['phase']=='lobby';assert all(x.get('isBot') or x['id']=='human' for x in g.STATE['players'])
  act(p,'leave');assert not g.STATE['players'] and not g.STATE['hostPlayerId']
print('All five solo modes, manual bot lifecycle and complete matches: PASS')
