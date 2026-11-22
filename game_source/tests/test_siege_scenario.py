"""Private scenario regression; run after build.py."""
import importlib.util
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py'
spec=importlib.util.spec_from_file_location('scenario_game',path)
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
key='a'*48
v=g.siege_request(dict(type='create',key=key,trial=True,rulesVersion=24))
r=g._SIEGE_ROOMS[v['code']]
scene=dict(version=1,name='test',ammo=3,cannon=dict(x=100,y=392),core=dict(x=800,y=390),
           blocks=[],items=[],stock={},zombies=[dict(kind='walker',x=350,y=390,round=0,drop=dict(mode='fixed',kind='gunteleport',amount=1)),
                                                dict(kind='walker',x=1000,y=390,round=2,drop=dict(mode='none'))])
v=g.siege_request(dict(type='scenarioLoad',key=key,code=v['code'],scene=scene))
assert v['ok'] and v['scenarioActive'] and not v['trial'] and v['scenarioPending']==1
z=next(b for b in r['bodies'] if b['kind']=='zombie');z['hp']=0
g._siege_zombie_drops(r)
assert r['buffs'][0]['gunteleport']==1
g._siege_zombie_drops(r)
assert r['buffs'][0]['gunteleport']==1
g._siege_scenario_spawn_due(r,1);assert len(r['scenarioPending'])==1
g._siege_scenario_spawn_due(r,2);assert not r['scenarioPending']
z=next(b for b in r['bodies'] if b['kind']=='zombie' and b['hp']>0);assert z['x']==1000
z['hp']=0;g._siege_zombie_drops(r);assert r['buffs'][0]['gunteleport']==1
ground=dict(kind='stone',x=700,y=398,w=120,h=36)
validated=g._siege_scenario_validate({**scene,'blocks':[ground]})
assert validated['blocks'][0]['y']==398
try:g._siege_scenario_validate({**scene,'blocks':[{**ground,'y':399}]})
except ValueError:pass
else:raise AssertionError('out-of-world building unexpectedly accepted')
g._siege_scenario_load(r,scene)
g._siege_fire(r,45,50,{})
assert r['shots'][0]==1 and r['zombie']['round']==2 and r['buffs'][0]['big']==0
assert r['scenarioPending'] and r['scenarioSource']['zombies'][1]['round']==2
g._siege_trial_reset(r,'standard');assert not r.get('scenarioActive') and r['theme']=='classic' and r['trial']

# Editor and server agree that rectangular objects may touch but not interpenetrate.
special=[dict(kind='spring',x=490,y=395,w=42,h=28),
         dict(kind='oneway',x=540,y=375,w=24,h=72,passDir=-1),
         dict(kind='ladder',x=590,y=326,w=28,h=180)]
s={**scene,'blocks':special}
g._siege_scenario_load(r,s)
assert [b.get('special') for b in r['bodies'] if b.get('special')] == ['spring','oneway','ladder']
assert [b['passDir'] for b in r['bodies'] if b.get('special')=='oneway']==[-1]
assert any(b.get('special')=='ladder' and b.get('fixed') for b in r['bodies'])
assert g._siege_scenario_validate({**scene,'blocks':[dict(kind='wood',x=390,y=390,w=48,h=30)]})
for overlap in [
    dict(kind='wood',x=350,y=390,w=40,h=30),  # zombie
    dict(kind='wood',x=800,y=390,w=45,h=35),  # core
]:
    try:g._siege_scenario_validate({**scene,'blocks':[overlap]})
    except ValueError as e:assert '重叠' in str(e)
    else:raise AssertionError('overlapping scene accepted')
# Engineer raises a ladder beside a high barrier, not a siege-car shell.
challenge={**scene,'core':dict(x=720,y=180),
           'blocks':[dict(kind='stone',x=460,y=350,w=48,h=130)],
           'zombies':[dict(kind='engineer',x=390,y=390,round=0,drop=dict(mode='none'))]}
g._siege_scenario_load(r,challenge)
eng=next(b for b in r['bodies'] if b.get('zombieType')=='engineer')
for _ in range(3):
    if any(b.get('engineerLadder') for b in r['bodies']):break
    g._siege_zombie_round(r,0.,[],lambda t,shot:[],[],None)
assert any(b.get('engineerLadder') and b['hp']>0 for b in r['bodies']),'engineer did not build ladder'
y=eng['y']
for _ in range(4):g._siege_zombie_round(r,0.,[],lambda t,shot:[],[],None)
assert eng['y']<y,'zombies did not climb ladder'
print('scenario regression passed')
