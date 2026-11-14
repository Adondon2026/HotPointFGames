"""Rear shots, random formations, timed regeneration, healing, true split and strong wind."""
import importlib.util, os, tempfile, math, random, copy
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def aim(r,side,x,y,a):
    sx,sy=g._siege_launcher(side,r);d=1 if side==0 else -1;rad=math.radians(a);dx=(x-sx)*d;dy=y-sy;w=r['wind'];den=.5*(g._SIEGE_GRAV+d*w*math.tan(rad))
    if abs(den)<1e-8:return None
    t2=(dy+dx*math.tan(rad))/den
    if t2<=0:return None
    t=math.sqrt(t2);p=(dx-.5*d*w*t*t)/(math.cos(rad)*t)/8
    return p if 15<=p<=100 else None
checks=0
for name,field in g._SIEGE_FIELDS.items():
    positions=set()
    for seed in range(5):
        random.seed(seed);r=g._siege_new('A','a',True,13,name,'high');positions.add(tuple((i['x'],i['y']) for i in r['items']))
        assert len(r['items'])==13 and len({i['slot'] for i in r['items']})==13
        # New formations can be hit under no wind; rear targets must be reachable by own rear shot.
        r['wind']=0;rear=[i for i in r['items'] if i['x']<g._siege_launcher(0,r)[0]-55];assert rear
        for it in r['items']:
            got=False
            for side in (0,1):
                for a in range(8,174,3):
                    q=copy.deepcopy(r);q['turn']=side;q['items']=[dict(it)];p=aim(q,side,it['x'],it['y'],a)
                    if p is None:continue
                    g._siege_fire(q,a,p)
                    if q['event']['pickups']:got=True;break
                if got:break
            assert got,(name,seed,it);checks+=1
        # Strong wind still permits an actual damage-producing shot, not necessarily at 48 degrees.
        for side in (0,1):
            for w in (-125,125):
                got=False
                for a in range(25,76,5):
                    q=copy.deepcopy(r);q['turn']=side;q['wind']=w;q['items']=[];target=next(b for b in q['bodies'] if b['side']==1-side and b['kind']=='core');p=aim(q,side,target['x'],target['y'],a)
                    if p is None:continue
                    g._siege_fire(q,a,p)
                    if any(b['hp']<b['max'] for b in q['bodies'] if b['side']==1-side):got=True;break
                assert got,(name,seed,side,w);checks+=1
    assert len(positions)==5
# Specific rear projectile with a healing pickup, 18 HP capped; refill only after four additional shots.
r=g._siege_new('A','a',True,0,'standard');r['wind']=0
core=next(b for b in r['bodies'] if b['side']==0 and b['kind']=='core');core['hp']=70
sx,sy=g._siege_launcher(0,r);t=.35;a=math.radians(110);v=640
r['items']=[dict(id=0,slot=0,kind='heal',x=sx+v*math.cos(a)*t,y=sy-v*math.sin(a)*t+230*t*t,r=15)]
g._siege_fire(r,110,80);assert r['event']['pickups'][0]['healed']==18 and r['buffs'][0]['heal']==0
assert not r['items'] and len(r['respawns'])==1
for n in range(4):
    g._siege_fire(r,5,15)
    if n<3:assert not r['items']
assert len(r['items'])==1 and r['items'][0]['id']==1000 and r['items'][0]['slot']==0 and not r['respawns']
# Actual distinct child trajectories and timed impacts.
r=g._siege_new('A','a',True,0);r['buffs'][0]['splitshot']=1;g._siege_fire(r,42,65)
assert any(len(f[3])==2 and abs(f[3][0][1]-f[3][1][1])>10 for f in r['event']['frames'])
assert len(r['event']['fragmentHits'])==2 and r['event']['fragmentHits'][0]!=r['event']['fragmentHits'][1]
# Strong wind changes the landing point significantly and stays fixed for one flight.
r=g._siege_new('A','a',True,0);q=copy.deepcopy(r);r['wind']=-125;q['wind']=125
for x in (r,q):g._siege_fire(x,55,70)
assert abs(r['event']['impact'][0]-q['event']['impact'][0])>150
print('v0.12:',checks,'actual trajectory checks; random formation, rear heal, delayed refill, split projectiles, strong wind PASS')
