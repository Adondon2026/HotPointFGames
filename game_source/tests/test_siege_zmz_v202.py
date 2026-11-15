"""ZMZ v0.20.2: negative angle/heaviness, inherited multi-shell effects and collapsing supports."""
import importlib.util, pathlib, tempfile, os, random, math
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='siege_v202_')
spec=importlib.util.spec_from_file_location('game',pathlib.Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
random.seed(20202)

def room():
    r=g._siege_new('A','a',False,0,'classic','off',0,'stock')
    r['players'].append(dict(name='B',key='b'));r['phase']='play';r['turn']=0
    r['bodies']=[
        dict(id=0,side=0,x=100,y=400,w=30,h=32,kind='core',hp=100,max=100,vx=0.,vy=0.,fixed=True),
        dict(id=1,side=1,x=850,y=400,w=30,h=32,kind='core',hp=100,max=100,vx=0.,vy=0.,fixed=True)]
    r['launchers']=[[235,368],[725,368]]
    return r

# Unstable is a one-time change in launch direction, never the old W oscillation.
assert g._siege_v20_offset(0.7,0,{'wobble':1})==(0.,0.)
r=room();r['negativePending'][0].update(wobble=1,heavy=1)
g._siege_fire(r,45,60)
ev=r['event']
assert set(ev['negativeActive'])=={'wobble','heavy'} and not r['negativePending'][0]
assert 13.9<=abs(ev['angleOffset'])<=24.01,(ev['angle'],ev['angleOffset'])
assert ev['requestedAngle']==45 and ev['angle']==45+ev['angleOffset']
for aimed in (5,175):
    r=room();r['negativePending'][0]['wobble']=1;g._siege_fire(r,aimed,45)
    assert abs(r['event']['angleOffset'])>=13.9,(aimed,r['event']['angleOffset'])

r=room();g._siege_fire(r,45,60);normal=r['event']['impact'][0]
r=room();r['negativePending'][0]['heavy']=1;g._siege_fire(r,45,60);heavy=r['event']['impact'][0]
assert heavy<normal-140,(heavy,normal)

# Push is a two-second constant-speed cruise per stack, cumulative on separate hits.
body=dict(kind='stone',hp=75,fixed=True,motionY=42,vx=0.,vy=0.)
g._siege_v20_push(body,400,-100,1)
assert 'fixed' not in body and 'motionY' not in body
assert abs(body['pushTime']-2.)<1e-8 and 220<=math.hypot(body['pushVX'],body['pushVY'])<=610
assert body['pushVX']>0 and body['pushVY']<0
g._siege_v20_push(body,0,350,2)
assert body['pushTime']==6. and abs(body['vx'])<1e-8 and body['vy']>0

# Every repeat shell must split separately; EACH impact creates the selected clone.
r=room();r['buffs'][0].update(splitshot=1,repeat=1,clone=1,push=1)
g._siege_fire(r,28,42,{'splitshot':1,'repeat':1,'clone':1,'push':1})
ev=r['event']
assert ev['attackCounts']['splitshot']==1 and ev['attackCounts']['repeat']==1
assert len(ev['fragmentHits'])>=5,ev['fragmentHits']
assert len(r['clones'])==1,(len(r['clones']),ev['fragmentHits'])
assert all(c['side']==0 and c['remaining']==2 for c in r['clones'])

# A teleported gun may stand on a block; when the block is destroyed it drops.
r=room();support=dict(id=9,side=-1,x=320,y=276,w=145,h=32,kind='stone',hp=100,max=100,vx=0.,vy=0.,fixed=True)
r['bodies'].append(support);r['launchers'][0]=[320,212];r['gunGravity'][0]=True
for _ in range(12):g._siege_gun_gravity(r,1/60)
assert abs(r['launchers'][0][1]-212)<.1
support['hp']=0
for _ in range(125):g._siege_gun_gravity(r,1/60)
assert abs(r['launchers'][0][1]-(_floor:=g._siege_floor(r,320)-48))<1,(r['launchers'][0],_floor)

# Destroyed supports must not leave a previously moved core suspended in air.
r=room();r['bodies'][1].update(x=401,y=317,fixed=False)
r['bodies'].insert(1,dict(id=10,side=1,x=401,y=354,w=62,h=40,kind='stone',hp=2,max=75,vx=0.,vy=0.,fixed=True))
g._siege_fire(r,15,50)
core=next(b for b in r['bodies'] if b['side']==1 and b['kind']=='core')
assert core['y']>360,('core stayed suspended',core['y'],r['event']['impact'])
print('v0.20.2 negative HUD state, launch offset, heavy gravity, cumulative push, all repeat/split clone effects, and collapsing supports PASS')
