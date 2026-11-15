"""Regression tests for the Noita-inspired projectile pipeline and resource accounting."""
import importlib.util,os,tempfile,time
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def new():
    r=g._siege_new('A','a',True,0,'standard','off',0,'stock')
    r['bodies']=[b for b in r['bodies'] if b['kind']=='core']
    r['launchers']=[[235,368],[725,368]]
    return r

def fire(sel,config=None,angle=175,power=65):
    r=new();r['buffs'][0].update(sel)
    g._siege_fire(r,angle,power,sel,config=config)
    return r,r['event']

r,e=fire({'wooddrop':2,'stonedrop':1,'power':2,'blackhole':1},{'build':'safe'})
assert e['engineering'] and not e['holes'] and r['buffs'][0]['power']==2 and r['buffs'][0]['blackhole']==1
assert len(e['drops'])+r['buffs'][0]['wooddrop']+r['buffs'][0]['stonedrop']==3
assert e['cores']==[100,100],e['cores']
r,e=fire({'fuse':1},{'fuseMode':'strict','fuseTime':2})
assert abs(e['hitAt']-2)<.02,e['hitAt']
r,e=fire({'fuse':1},{'fuseMode':'either','fuseTime':2})
assert e['hitAt']<2,e['hitAt']
r,d=fire({'fuse':1},{'fuseMode':'delay','fuseTime':1})
assert abs(d['hitAt']-e['hitAt']-1)<.04,(d['hitAt'],e['hitAt'])
r,e=fire({'splitshot':2},{'splitMode':'timer','splitTime':.7,'parentEnd':'vanish'},90,65)
assert abs(e['hitAt']-.7)<.02 and any(v[0]=='spawn' and v[4]==4 for v in e['behaviorEvents']),e['behaviorEvents']
assert any(v[0]=='finish' and not v[4] for v in e['behaviorEvents'])
r,e=fire({'bounce':2,'larpa':2,'bounceblast':1},{})
assert e['bounces'] and 0<sum(v[4] for v in e['behaviorEvents'] if v[0]=='spawn')<=4
assert 0<sum(v[0]=='bounceBlast' for v in e['behaviorEvents'])<=2
r,e=fire({'bounce':1,'splitshot':1},{'splitMode':'bounce','parentEnd':'vanish'})
assert any(v[0]=='spawn' and v[4]==2 for v in e['behaviorEvents'])
r,e=fire({'downpour':1},{},90,65)
assert sum(v[4] for v in e['behaviorEvents'] if v[0]=='spawn' and v[5]=='down')==2
r,e=fire({'splitshot':1},{'splitMode':'expire','parentEnd':'vanish'})
assert any(v[0]=='spawn' and v[4]==2 for v in e['behaviorEvents'])
cfg=g._siege_config({'scopes':{'homing':'child','power':'mother'},'childFuseTime':2})
s=g._siege_compile_spec({'splitshot':1,'homing':1,'power':2},cfg)
assert 'homing' not in s['root'] and 'power' not in s['child'] and s['child']['homing']==1
assert g._siege_compile_spec({'homing':1},cfg)['root']['homing']==1
for bad in ({'fuseTime':float('nan')},{'scopes':{'bad':'child'}},{'splitMode':'unknown'}):
    try:g._siege_config(bad)
    except ValueError:pass
    else:raise AssertionError(bad)
b=lambda i,x,kind,**kw:dict(id=i,x=x,y=300,w=20,h=20,kind=kind,hp=42,**kw)
r={'bodies':[b(1,100,'wood',burnRounds=2),b(2,120,'wood'),b(3,140,'stone'),b(4,160,'wood')]}
assert g._siege_burn_round(r)
assert r['bodies'][0]['hp']==37 and r['bodies'][1]['burnRounds']==2 and not r['bodies'][2].get('burnRounds') and not r['bodies'][3].get('burnRounds')
for _ in range(4):g._siege_burn_round(r)
assert r['bodies'][0]['hp']==32 and r['bodies'][1]['hp']==32
r=new()
for inv in r['buffs']:inv['fuse']=1
now=time.time();rt=g._siege_sync_runtime(r,now)
rt['plans']=[(90,65,{'fuse':1}),(90,65,{'fuse':1})]
rt['configs']=[g._siege_config({'fuseTime':1}),g._siege_config({'fuseTime':2})]
g._siege_sync_compute(r,rt,now)
assert r['shots']==[1,1] and rt['replay'] and not any(inv['fuse'] for inv in r['buffs'])
print('Siege combo: engineering, shared resources, fuse modes, all split triggers, bounded copies, scopes, fire and sync PASS')
