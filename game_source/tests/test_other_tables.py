"""Public history is ordered, bounded, and contains no concealed cards/dice."""
import importlib.util, os, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='other-tables-')
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
handler=object.__new__(g.Handler)
with g.LOCK:
 for mode in ('cards','dice','chuanma'):
  g.STATE=g.fresh_state();g.STATE['mode']=mode;g.add_local_bot();p=g.STATE['players'][0];p.update(id='human',name='人',isBot=False,ready=True);g.STATE['hostPlayerId']=p['id'];g.add_local_bot();g.add_local_bot()
  assert handler.handle_action(p,'solo_start',{})[1]==200
  steps=0
  while g.STATE['phase']!='finished' and steps<2000:
   steps+=1;phase=g.STATE['phase'];cm=g.STATE['chuanma']
   if phase.endswith('_reveal'): assert handler.handle_action(p,'next_round',{})[1]==200;continue
   if phase in ('cm_exchange','cm_dingque'):
    key='exchangeSelections' if phase=='cm_exchange' else 'dingqueSelections';turn=next(x for x in g.STATE['players'] if x['id'] not in cm[key])
   elif phase=='cm_response':turn=g.player_by_id(next(x for x in cm['responseOptions'] if x not in cm['responses']))
   else:turn=g.player_by_id(g.STATE['turnPlayerId'])
   assert g.bot_step(turn),(mode,phase)
  assert g.STATE['phase']=='finished';events=g.public_state(p['id'])['tableEvents'];assert events
  assert [e['seq'] for e in events]==sorted(set(e['seq'] for e in events))
  assert all(not {'cards','hand','dice','cardIds','tileIds','responseOptions'} & set(e) for e in events)
  assert all(e['kind']!='cm_respond' for e in events)
  assert any(e['kind']=={'cards':'cards_play','dice':'dice_bid','chuanma':'cm_discard'}[mode] for e in events)
  print(mode,len(events),'public actions OK')
print('Other table public history: PASS')
