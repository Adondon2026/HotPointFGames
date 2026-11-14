"""Robot teleport policy, reverse aiming, explicit blocked-muzzle detonation."""
import importlib.util, pathlib, tempfile, os, time, random
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',pathlib.Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def new(mode='stock',bot=True):
    r=g._siege_new('A','a',True,0,'standard','off',0,mode);r['bot']=bot;r['players'][1]['key']='b';r['launchers']=[list(g._siege_launcher(i,r)) for i in (0,1)];return r
for mode in ('stock','auto'):
    r=new(mode);r['turn']=1;r['buffs'][1].update(gunteleport=1,coreteleport=1)
    r['launchers'][1]=[80,368];core=next(b for b in r['bodies'] if b['side']==0 and b['kind']=='core');core['x']=810
    r['bodies']=[b for b in r['bodies'] if b['kind']=='core'];r['bodies'][1]['x']=930
    plan={'planOnly':True};g._siege_bot(r,plan);a,p,sel=plan['plan'];assert a>90 and not any(k in sel for k in g._SIEGE_ONE_SHOT),(a,p,sel)
    x,y=g._siege_muzzle(1,r,a);r['items']=[dict(id=1,kind='gunteleport',amount=1,x=x,y=y,r=20)]
    old=list(r['launchers'][1]);g._siege_fire(r,a,p,{'gunteleport':1,'coreteleport':1} if mode=='stock' else None)
    assert not r['event']['teleports'] and r['launchers'][1]==old and r['items'][0]['kind']=='gunteleport'
    assert not any(r['buffs'][1][k] for k in g._SIEGE_ONE_SHOT)
# Force only after explicit authorization. Damage actually occurs at the muzzle.
for mode in ('stock','auto'):
    r=new(mode);r['buffs'][0]['big']=5 if mode=='stock' else 1;radius=36 if mode=='stock' else 12
    sel={'big':5} if mode=='stock' else None;a=175
    x,y=g._siege_muzzle(0,r,a,radius);b=next(b for b in r['bodies'] if b['kind']!='core');b.update(x=x,y=y,fixed=True);before=b['hp']
    try:g._siege_fire(r,a,65,sel)
    except ValueError as e:assert '建筑挡住' in str(e)
    else:raise AssertionError('unconfirmed blocked shot')
    assert r['shots']==[0,0] and r['buffs'][0]['big']==(5 if mode=='stock' else 1)
    g._siege_fire(r,a,65,sel,True);e=r['event'];assert e['hitAt']<.05 and abs(e['impact'][0]-x)<.11 and abs(e['impact'][1]-y)<.11 and b['hp']<before
# Raised ground at a terrain step blocks giant shell even when forced.
r=new();r['rise']=95;r['launchers'][0]=[340,368];r['buffs'][0]['big']=5
try:g._siege_fire(r,175,65,{'big':5},True)
except ValueError as e:assert '地面' in str(e)
else:raise AssertionError('ground force allowed')
assert r['shots']==[0,0] and r['buffs'][0]['big']==5
# Synchronized explicit confirmation survives round computation.
r=new(bot=False);r.update(combatMode='sync',reloadSeconds=0);r['buffs'][0]['big']=5;rt=g._siege_sync_runtime(r);x,y=g._siege_muzzle(0,r,175,36);b=next(b for b in r['bodies'] if b['kind']!='core');b.update(x=x,y=y,fixed=True)
d=dict(round=1,angle=175,power=65,selection={'big':5})
try:g._siege_sync_plan(r,rt,0,d,True)
except ValueError as e:assert '建筑挡住' in str(e)
else:raise AssertionError('unconfirmed sync')
assert not rt['locked'][0];g._siege_sync_plan(r,rt,0,dict(d,force=True),True);g._siege_sync_plan(r,rt,1,dict(round=1,angle=42,power=65,selection={}),True)
assert g._siege_sync_tick(r,rt) and r['shots']==[1,1] and r['buffs'][0]['big']==0
assert rt['replay']['frames'][0][2][0]['radius']==36
print('v0.18.2: robot reverse aim, no teleport, explicit force, ground protection, sync force PASS')
