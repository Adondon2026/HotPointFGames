import copy, importlib.util, math, os, random, tempfile
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def new(mode='standard',buff='stock'):return g._siege_new('A','a',True,0,mode,'off',0,buff)
r=new();r['buffs'][0].update(big=3,power=2,shield=3,vision=2);g._siege_fire(r,42,65,{});assert r['buffs'][0]['big']==3 and not r['event']['attacks'];g._siege_fire(r,42,65,{});g._siege_fire(r,42,65,{'big':2,'power':1,'shield':2});assert r['event']['radius']==18 and r['event']['blastRadius']==124 and r['buffs'][0]['big']==1 and r['armed'][0]=={'shield':2};g._siege_fire(r,42,65,{});assert r['event']['defenseCounts']=={'shield':2} and not r['armed'][0] and r['buffs'][0]['shield']==1
before=copy.deepcopy(r);r['turn']=0
for bad in ({'big':9},{'vision':2},{'heal':1},{'power':True},{'big':-1}):
    try:g._siege_fire(r,42,65,bad)
    except ValueError:pass
    else:raise AssertionError(bad)
assert r['buffs']==before['buffs'] and r['shots']==before['shots']
r=new();r['buffs'][0]['splitshot']=2;g._siege_fire(r,60,75,{'splitshot':2});assert any(len(f[3])==4 for f in r['event']['frames'])
r=new('overtop');assert g._siege_launcher(0,r)[0]<next(b['x'] for b in r['bodies'] if b['side']==0 and b['kind']=='core');g._siege_fire(r,5,70);assert any(b['hp']<b['max'] for b in r['bodies'] if b['side']==0)
r=new('sky');assert len([b for b in r['bodies'] if b.get('platform')])==2;assert all(b['y']<230 for b in r['bodies'] if b['side']>=0);g._siege_fire(r,5,15);assert all(b['y']<230 for b in r['bodies'] if b['side']>=0 and b['hp']>0)
r=new('movingwall');wall=r['bodies'][-1];g._siege_motion(r,0);a=wall['y'];g._siege_motion(r,math.pi/.8/2);assert wall['y']-a>100;g._siege_fire(r,45,70);ys=[f[2][-1][2] for f in r['event']['frames']];assert max(ys)-min(ys)>50
# Actual successful attacks from both sides at extreme winds, new spatial layouts.
checks=0
for mode in g._SIEGE_NEW_FIELDS:
 for side in (0,1):
  for wind in (-125,0,125):
   r=new(mode);r['turn']=side;r['wind']=wind;got=False
   for angle in range(35,86,5):
    for power in range(40,101,5):
     q=copy.deepcopy(r);g._siege_fire(q,angle,power)
     if any(b['hp']<b['max'] for b in q['bodies'] if b['side']==1-side):got=True;break
    if got:break
   assert got,(mode,side,wind);checks+=1
print('v0.13: inventory, validation, stack, defense, split, self-hit, platform, dynamic barrier and',checks,'real hit checks PASS')
