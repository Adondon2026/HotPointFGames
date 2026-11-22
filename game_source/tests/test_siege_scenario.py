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
g._siege_trial_reset(r,'standard');assert not r.get('scenarioActive') and r['theme']=='classic' and r['trial']
print('scenario regression passed')
