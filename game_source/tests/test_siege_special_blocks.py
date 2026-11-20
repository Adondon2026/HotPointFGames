"""Distinct recoverable one-way and finite-use spring blocks in zombie front map."""
import importlib.util,os,tempfile
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='siege_special_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

r=g._siege_new('A','a',True,0,'classic','off',0)
g._siege_v24_setup(r,'zombie')
r.update(zombieMap='front',zombiePlayerCount=2)
g._siege_field(r)
gate=next(b for b in r['bodies'] if b.get('special')=='oneway')
spring=next(b for b in r['bodies'] if b.get('special')=='spring')
assert len({b['id'] for b in r['bodies']})==len(r['bodies'])
assert gate['kind']=='stone' and spring['kind']=='stone' and not gate.get('platform') and not spring.get('platform')
assert g._siege_oneway_pass(gate,220.) and not g._siege_oneway_pass(gate,-220.)
assert not g._siege_oneway_pass(spring,220.)
y=gate['y']
forward=g._siege_siegecar_trace(r,(gate['x']-90,y),(gate['x']+90,y))[0]
reverse=g._siege_siegecar_trace(r,(gate['x']+90,y),(gate['x']-90,y))[0]
assert forward is None or forward is not gate, 'friendly projectile must cross directional gate'
assert reverse is gate, 'reverse projectile must collide with gate'
old=spring['hp']
for n in range(4):
    assert g._siege_spring_hit(spring)
    assert spring['hp']<old
    old=spring['hp']
assert spring['hp']==0 and spring['springHits']==0
assert not g._siege_spring_hit(spring)
print('Siege specials: forward pass, reverse stop, 4 spring impacts, salvage-compatible blocks PASS')
