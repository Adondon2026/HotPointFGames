"""Combat presentation frames must preserve the actual result and viewer privacy."""
import importlib.util, os, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def pc(owner,rank,id):return {'owner':owner,'rank':rank,'id':id,'revealed_to':[],'carrying_flag_owner':None}
def scenario(a,d):
 g=m._army_game_state.GameState();g.phase='play';g.turn=0;g.board={(5,0):pc(0,a,1),(6,0):pc(1,d,2),(1,0):pc(0,'工兵',3),(10,4):pc(1,'工兵',4)};g.initial_replay_frame=g._truth_frame();assert g.move(0,(5,0),(6,0))[0];return g
for a,d,outcome,count in [('司令','军长','attacker',3),('军长','司令','defender',3),('炸弹','军长','both',2),('团长','团长','both',2)]:
 g=scenario(a,d);e=m._army_presentation(g,0)[0];assert e['result']==outcome and e['battle'];assert len(e['before']['pieces'])==4 and len(e['after']['pieces'])==count;assert e['before']['pieces'][1]['rank']=='UNKNOWN';assert all(p['rank']=='UNKNOWN' for p in e['after']['pieces'] if p['owner']==1)
 e2=m._army_presentation(g,1)[0];assert e2['before']['pieces'][0]['rank']=='UNKNOWN';assert e2['before']['pieces'][1]['rank']==d
 # A real undo removes the event from the active presentation branch.
 assert g.request(0,'undo')[0];assert g.respond(1,True)[0];assert m._army_presentation(g,0)==[]
g=m._army_game_state.GameState();g.phase='play';g.turn=0;g.board={(5,0):pc(0,'司令',1),(6,0):pc(1,'军旗',2),(10,4):pc(1,'工兵',4)};g.initial_replay_frame=g._truth_frame();assert g.move(0,(5,0),(6,0))[0];assert g.phase=='over';assert m._army_presentation(g,0)[0]['result']=='capture_flag'
print('Army combat presentation, three outcomes, privacy, undo and final flag: PASS')
