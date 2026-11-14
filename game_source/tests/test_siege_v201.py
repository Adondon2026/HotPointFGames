"""Arena edges are solid: main and fragment impacts retain effects in both modes."""
import importlib.util, pathlib, tempfile, os, time
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',pathlib.Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def new(side=0,at=120):
 r=g._siege_new('A','a',False,0,'classic','off',0,'stock',None,{'bounce':20});r['players'].append({'name':'B','key':'b'});r['phase']='play';r['turn']=side
 r['bodies']=[dict(id=i,side=i,x=x,y=399,w=26,h=32,kind='core',hp=100,max=100,vx=0.,vy=0.,fixed=True) for i,x in enumerate((260,700))];r['launchers']=[[at,300],[960-at,300]];return r
for side in (0,1):
 r=new(side);r['buffs'][side].update(bounce=1,wooddrop=1,stonedrop=1,blackhole=1)
 g._siege_fire(r,175,65,{'bounce':1,'wooddrop':1,'stonedrop':1,'blackhole':1});e=r['event'];assert e['bounces'] and abs(e['bounces'][0][0]-(6.2 if side==0 else 953.8))<.2,e['bounces'];assert e['hitAt']>e['bounces'][0][2];assert len(e['drops'])==2 and e['holes']
 r=new(side);r['buffs'][side].update(wooddrop=1,stonedrop=1,blackhole=1);g._siege_fire(r,175,65,{'wooddrop':1,'stonedrop':1,'blackhole':1});e=r['event'];assert e['impact'][0]==(6 if side==0 else 954),e['impact'];assert len(e['drops'])==2 and e['holes'];assert all(19<=x[1]<=941 for x in e['drops']);assert len([b for b in r['bodies'] if b.get('generated')])==2
 # Start further from wall so splitting occurs before reaching it.
 r=new(side,420);r['buffs'][side].update(splitshot=1,wooddrop=1,blackhole=1);g._siege_fire(r,155,100,{'splitshot':1,'wooddrop':1,'blackhole':1});e=r['event'];assert any(abs(x-(6 if side==0 else 954))<.2 for x,y,t in e['fragmentHits']),e['fragmentHits'];assert len(e['drops'])>=2 and len(e['holes'])>=2
 r=new(side,420);r['buffs'][side].update(splitshot=1,bounce=1);g._siege_fire(r,155,100,{'splitshot':1,'bounce':1});e=r['event'];assert any(abs(x-(6.2 if side==0 else 953.8))<.3 and i>=0 for x,y,t,i in e['bounces']),e['bounces']
# Sync uses same shared physics; both shells bounce at the side and eventually hit.
r=new();r['combatMode']='sync';r['reloadSeconds']=0
for b in r['buffs']:b.update(bounce=1,wooddrop=1,blackhole=1)
rt=g._siege_sync_runtime(r);rt['plans']=[(175,65,{'bounce':1,'wooddrop':1,'blackhole':1})]*2;rt['locked']=[True,True];g._siege_sync_compute(r,rt,time.time());shots=[s for f in rt['replay']['frames'] for s in f[2]]
for side in (0,1):assert any(s['side']==side and any(abs(b[0]-(6.2 if side==0 else 953.8))<.3 for b in s['bounces']) for s in shots)
assert len([b for b in r['bodies'] if b.get('generated')])==2
print('v0.20.1 edge bounce, wall impact, fragments, effects and synchronized shots PASS')
