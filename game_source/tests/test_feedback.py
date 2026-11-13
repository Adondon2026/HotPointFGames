"""Regression tests for public resource changes and action-aligned snapshots."""
import importlib.util, os, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='feedback-')
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
h=object.__new__(g.Handler)
def setup(mode):
    g.STATE=g.fresh_state();g.STATE['mode']=mode;g.add_local_bot();p=g.STATE['players'][0];p.update(id='human',name='人',isBot=False,ready=True);g.STATE['hostPlayerId']=p['id'];g.add_local_bot();b=g.STATE['players'][1];b.update(isBot=False,ready=True);g.STATE['matchId']='m-'+mode;return p,b
with g.LOCK:
    p,b=setup('cards');g.start_cards_round(p['id']);g.STATE['card']['targetRank']='A';p['hand']=[{'id':'x','rank':'K'}];assert h.handle_action(p,'cards_play',{'cardIds':['x']})[1]==200;assert h.handle_action(b,'cards_challenge',{})[1]==200
    e=g.STATE['tableEvents'][-1];assert e['loserId']==p['id'] and e['changes']==[{'playerId':p['id'],'before':3,'after':2,'delta':-1}],e
    assert g.STATE['tableEvents'][0]['metrics'][p['id']]==3
    p,b=setup('dice');g.start_dice_round(p['id']);p['dice']=[2]*5;b['dice']=[3]*5;assert h.handle_action(p,'dice_bid',{'quantity':6,'face':2})[1]==200;assert h.handle_action(b,'dice_challenge',{})[1]==200;assert g.STATE['tableEvents'][-1]['changes'][0]['delta']==-1
    g.start_dice_round(p['id']);p['dice']=[2]*4;b['dice']=[3]*5;assert h.handle_action(b,'dice_bid',{'quantity':4,'face':2})[1]!=200
    g.STATE['turnPlayerId']=b['id'];assert h.handle_action(b,'dice_bid',{'quantity':4,'face':2})[1]==200;assert h.handle_action(p,'dice_exact',{})[1]==200;assert g.STATE['tableEvents'][-1]['changes']==[{'playerId':p['id'],'before':4,'after':5,'delta':1}]
    p,b=setup('draw');g.STATE['phase']='draw_play';g.STATE['roundNo']=1;g.STATE['draw'].update(drawerId=b['id'],word='太阳',aliases=[],deadline=g.time.time()+60,correctIds=[],guesses=[],turnIndex=0,totalTurns=2);assert h.handle_action(p,'draw_guess',{'guess':'太阳'})[1]==200;e=g.STATE['tableEvents'][-1];assert e['kind']=='draw_guess' and e['changes'][0]['delta']>0 and 'guess' not in e and 'word' not in e;assert e['changes'][1]['delta']==50
    p,b=setup('ddz');g.add_local_bot();g.deal_ddz();g.apply_ddz_bid(p,3);g.apply_ddz_play(p,[p['ddzHand'][0]]);e=g.STATE['ddz']['events'][-1];assert e['handCounts'][p['id']]==19 and e['multiplier']==1
print('Resource loss/gain, guess scores, public DDZ count snapshots: PASS')
