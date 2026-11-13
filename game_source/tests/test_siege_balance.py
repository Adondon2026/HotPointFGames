"""Compare actual damage, destruction and no-item match completion."""
import importlib.util, os, tempfile, math
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp();root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def battle(layout,buffs=(),side=0):
 r=g._siege_new('A','a',True,0);r['bodies']=g._siege_fort(0,layout);r['turn']=side;r['buffs'][side].update({k:1 for k in buffs});g._siege_fire(r,42,65)
 b=[b for b in r['bodies'] if b['side']==1-side];return r,sum(x['max']-x['hp'] for x in b),sum(x['hp']==0 for x in b)
for layout in ('tower','wall','split'):
 r,base,dead=battle(layout);assert dead==0 and r['event']['blastRadius']==52
 boosted,damage,dead=battle(layout,g._SIEGE_ATTACK);assert damage>base*2 and dead>=1 and boosted['event']['blastRadius']==88
 for buff in g._SIEGE_ATTACK:
  q,d,n=battle(layout,(buff,));assert d>base,(layout,buff,d,base)
  assert q['buffs'][0][buff]==0
 # With zero items, repeated aimed shots can still destroy each fort.
 q=g._siege_new('A','a',True,0);q['bodies']=g._siege_fort(0,layout)
 for i in range(12):
  q['turn']=0;target=next(b for b in q['bodies'] if b['kind']=='core' and b['side']==1);x,y=g._siege_launcher(0,q);dx=target['x']-x;dy=target['y']-y;a=math.radians(48)
  p=math.sqrt(460*dx*dx/(2*math.cos(a)**2*(dy+dx*math.tan(a))))/8;g._siege_fire(q,48,p)
  if q['phase']=='over':break
 assert q['phase']=='over' and q['winner']==0
 print(layout, 'normal / all boosts damage:',round(base,1),round(damage,1),'ordinary aimed shots to win:',i+1)
print('Siege balance PASS')
