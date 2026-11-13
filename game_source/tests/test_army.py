"""Reference-engine integration, privacy, persistence, settings and actual bot turn."""
import importlib.util, json, os, tempfile, time, random
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g);h=object.__new__(g.Handler)
def act(p,a,**kw):
 r=h.handle_action(p,a,kw);assert r[1]==200,(a,r);return r
with g.LOCK:
 g.STATE=g.fresh_state();g.STATE['hostPlayerId']='a';g.add_local_bot();a=g.STATE['players'][0];a.update(id='a',name='甲',isBot=False,ready=True);act(a,'set_mode',mode='army');act(a,'add_bot');b=g.STATE['players'][1];b.update(id='b',name='乙',isBot=False,ready=True);a['ready']=True
 act(a,'army_settings',victory='return',first='host',mountains=True,annotations=True)
 assert h.handle_action(b,'army_settings',dict(victory='capture',first='guest'))[1]==403
 assert not g.add_local_bot();act(a,'start');assert g.STATE['phase']=='army_setup'
 va=g.public_state('a')['army'];vb=g.public_state('b')['army'];assert len(va['pieces'])==len(vb['pieces'])==25 and all(p['owner']==0 for p in va['pieces']) and all(p['owner']==1 for p in vb['pieces']);assert va['replay_full'] is None
 assert not g._army_rules.validate_setup(0,g.STATE['armyDrafts'][0]);act(a,'army_random');act(a,'army_setup');assert g.STATE['phase']=='army_setup';act(b,'army_setup');assert g.STATE['phase']=='army_play'
 va=g.public_state('a')['army'];vb=g.public_state('b')['army'];assert len(va['pieces'])==50 and len(vb['pieces'])==50;assert all(p['rank']=='UNKNOWN' for p in va['pieces'] if p['owner']==1);assert all(p['rank']=='UNKNOWN' for p in vb['pieces'] if p['owner']==0);assert va['replay_full'] is None and not vb['legal'];assert 'armyData' not in g.public_state('a')
 # Server side move, undo, persist/restore.
 legal=next(x for x in va['legal'] if x['dst']);act(a,'army_move',src=legal['src'],dst=legal['dst'][0]);assert g.STATE['turnPlayerId']=='b';act(a,'army_request',kind='undo');act(b,'army_respond',accept=True);assert g.STATE['turnPlayerId']=='a';assert len(g.army_get().history)==0
 before=g.army_get().view_for(0);g.STATE=json.loads(json.dumps(g.STATE));assert g.army_get().view_for(0)==before
 act(a,'army_request',kind='draw');act(b,'army_respond',accept=True);assert g.STATE['phase']=='finished' and g.STATE['winnerId'] is None;v=g.public_state('a')['army'];assert v['draw'] and v['replay_full'][0]['label']=='0';assert len(v['replay_full'])==2
 act(a,'reset');assert 'armyData' not in g.STATE
 a=g.player_by_id('a');b=g.player_by_id('b');b['isBot']=True;act(a,'solo_start');act(a,'army_setup');v=g.public_state('a')['army'];legal=next(x for x in v['legal'] if x['dst']);act(a,'army_move',src=legal['src'],dst=legal['dst'][0]);g.update_timers();g._army_due=(g._army_due[0],0);g.update_timers();assert g.STATE['turnPlayerId']=='a' or g.STATE['phase']=='finished';assert len(g.army_get().history)>=2
 if g.STATE['phase']!='finished':act(a,'army_resign')
 assert g.STATE['phase']=='finished' and g.STATE['winnerId']=='b'
 # Rule-specific reference scenarios (standard topology).
 r=g._army_rules;T=g._army_topology
 def pc(owner,rank,id=0):return {'owner':owner,'rank':rank,'id':id,'revealed_to':[],'carrying_flag_owner':None}
 assert r.battle_result('工兵','地雷')=='ATTACKER' and r.battle_result('炸弹','司令')=='BOTH'
 board={(5,0):pc(0,'工兵')};assert r.movement_details(board,0,(5,0),'ML',True)[0];assert not r.movement_details(board,0,(5,0),'ML',False)[0];assert T.rotate_node_180('ML')=='MR'
 board={(0,1):pc(0,'司令')};assert not r.movement_details(board,0,(0,1),(0,2),True)[0]
 print('Army setup, two-view privacy, moves, undo/draw, replay, JSON persistence, bot, rule checks: PASS')
