"""Dynamic battle geometry, wind, ammo, item reachability and rematches."""
import importlib.util,os,tempfile,random,math,copy
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp();root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def aim(r,side,x,y,a):
    sx,sy=g._siege_muzzle(side,r,a);dir=1 if side==0 else -1;rad=math.radians(a);w=r['wind'];dx=(x-sx)*dir;dy=y-sy
    den=.5*(g._SIEGE_GRAV+dir*w*math.tan(rad));t2=(dy+dx*math.tan(rad))/den
    if t2<=0:return None
    t=math.sqrt(t2);v=(dx-.5*dir*w*t*t)/(math.cos(rad)*t);p=v/8
    return p if 15<=p<=100 else None
# Wind pair is equal relative to each shooter, stable during flight. Test changed landing points.
r=g._siege_new('A','a',True,0,'dynamic','medium',0);assert r['ammo']==0
old=copy.deepcopy(r);r['wind']=24;g._siege_fire(r,42,65);assert r['event']['wind']==24 and r['wind']==-old['windPair'];assert r['offset']==old['offset']
# Same geometry with different wind produces different flight positions.
a=copy.deepcopy(old);b=copy.deepcopy(old);a['wind']=-32;b['wind']=32;g._siege_fire(a,60,65);g._siege_fire(b,60,65);assert a['event']['frames'][10][1]!=b['event']['frames'][10][1]
layouts=set();offsets=set();checks=0
for seed in range(9):
    random.seed(seed);r=g._siege_new('A','a',True,25,'dynamic','high',0);layouts.add(r['layout']);offsets.add(r['offset']);assert len(r['items'])==25
    for l,rr in zip(r['bodies'][:8],r['bodies'][8:]):assert l['x']+rr['x']==960 and l['y']==rr['y'] and l['kind']==rr['kind']
    for side in (0,1):
        for wind in (-52,0,52):
            q=copy.deepcopy(r);q['turn']=side;q['wind']=wind;q['items']=[]
            target=next(b for b in q['bodies'] if b['side']==1-side and b['kind']=='core');p=aim(q,side,target['x'],target['y'],48);assert p is not None
            g._siege_fire(q,48,p);assert q['event']['hitId'] is not None and any(b['hp']<b['max'] for b in q['bodies'] if b['side']==1-side),(seed,side,wind)
            checks+=1
    # Verify every item at no wind, plus strong wind on two representative maps.
    for wind in ([0,-52,52] if seed<2 else [0]):
        for it in r['items']:
            got=False
            for side in (0,1):
                for angle in range(8,174,3):
                    q=copy.deepcopy(r);q['turn']=side;q['wind']=wind;q['items']=[dict(it)];p=aim(q,side,it['x'],it['y'],angle)
                    if p is None:continue
                    g._siege_fire(q,angle,p)
                    if q['event']['pickups']:got=True;break
                if got:break
            assert got,(seed,wind,it,r['offset'],r['layout']);checks+=1
assert len(layouts)==3 and len(offsets)>5
# Infinite/finite ammo and rematch settings.
for ammo in (0,6,10,15,20):
    r=g._siege_new('A','a',True,0,'classic','off',ammo);r['shots']=[(ammo or 10)-1,(ammo or 10)-1];g._siege_fire(r,5,15);g._siege_fire(r,5,15);assert r['phase']==('over' if ammo else 'play')
    g._siege_rematch(r);assert r['ammo']==ammo and r['shots']==[0,0] and [g._siege_core(r['bodies'],i) for i in (0,1)]==[100,100]
print('Dynamic siege:',checks,'real target/item trajectory checks; three layouts, mirrored geometry, wind, ammo, rematch PASS')
