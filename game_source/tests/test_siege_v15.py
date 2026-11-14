"""Floating geometry, bonus bundles, finite ricochet and real sequential construction."""
import importlib.util,os,tempfile,random,math,copy
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def new(m='standard',n=0):return g._siege_new('A','a',True,n,m,'off',0,'stock')
for mode in ('floating','floatingcenter'):
 for seed in range(10):
  random.seed(seed);r=new(mode,25);assert len(r['items'])==25
  assert all(i['amount'] in (1,2,3,5) for i in r['items'])
  assert all(a['amount']==b['amount'] for a,b in zip(r['items'][:24:2],r['items'][1:24:2]))
 r=new(mode);core=next(b for b in r['bodies'] if b['side']==0 and b['kind']=='core');g._siege_motion(r,0);y=core['y'];g._siege_motion(r,math.pi/.8/2);assert core['y']-y==46
 assert abs(g._siege_launcher(0,r,0)[1]-g._siege_launcher(0,r,math.pi/.8)[1])>100
 g._siege_fire(r,65,70);ev=r['event'];assert abs(ev['frames'][0][1][1]-g._siege_muzzle(0,r,65,6,ev['motionStart'])[1])<.1
 assert len({f[2][core['id']][2] for f in ev['frames']})>5
# Collect five charges but do not automatically consume them on the current shot.
r=new();x,y=g._siege_muzzle(0,r,75);r['items']=[dict(id=0,kind='big',amount=5,x=x,y=y,r=20)];g._siege_fire(r,75,35);assert r['buffs'][0]['big']==5 and not r['event']['attacks'];assert r['event']['pickups'][0]['amount']==5
for n in (1,2,3,5):
 r=new();r['buffs'][0]['bounce']=n;g._siege_fire(r,88,25,{'bounce':n});assert len(r['event']['bounces'])==n and r['buffs'][0]['bounce']==0,(n,r['event']['bounces'])
# The same x location gets successive physical blocks, stacked with ordinary dimensions.
for kind,h in [('wooddrop',38),('stonedrop',44)]:
 r=new();r['buffs'][0][kind]=3;g._siege_fire(r,42,35,{kind:3});ev=r['event'];blocks=[b for b in r['bodies'] if b.get('generated')];assert len(blocks)==3 and len(ev['drops'])==3 and r['buffs'][0][kind]==0
 assert all(b['hp']>0 and not b['falling'] for b in blocks);assert all(abs(a['y']-b['y']-h)<2 for a,b in zip(blocks,blocks[1:]));assert all(b[3]>a[3] for a,b in zip(ev['drops'],ev['drops'][1:]))
# A deliberately exposed core, on either side, takes additional damage from falling stone.
for side in (0,1):
 r=new();r['bodies']=[b for b in r['bodies'] if b['kind']=='core'];core=next(b for b in r['bodies'] if b['side']==side);core.update(x=480,y=394,fixed=True);other=next(b for b in r['bodies'] if b['side']!=side);other.update(x=850,y=394,fixed=True)
 a=copy.deepcopy(r);g._siege_fire(a,42,35);r['buffs'][0]['stonedrop']=1;g._siege_fire(r,42,35,{'stonedrop':1});assert g._siege_core(r['bodies'],side)<g._siege_core(a['bodies'],side)-15,(side,r['event']['impact'],r['event']['cores'],a['event']['cores'])
print('v0.15: floating maps, mirrored bundles, 1/2/3/5 bounces, wood and stone stacks, self/enemy drop damage PASS')
