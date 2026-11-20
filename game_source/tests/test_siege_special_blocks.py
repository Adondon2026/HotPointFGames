"""Special blocks are constructible materials, never preset front-map decor."""
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
assert not any(b.get('special') in ('oneway','spring') for b in r['bodies']),\
    'front map must not start with the two experimental blocks'
# Explicit blocks test directional collision without putting them in the map
# template; real construction from skills is covered by separate fire tests.
gate=dict(id=r['nextBodyId'],side=0,kind='stone',special='oneway',
          x=515.,y=372.,w=20.,h=88.,hp=80.,max=80.,
          passDir=1,onewayHits=4,vx=0.,vy=0.,fixed=True)
spring=dict(id=r['nextBodyId']+1,side=0,kind='stone',special='spring',
            x=665.,y=390.,w=44.,h=28.,hp=72.,max=72.,
            springHits=4,vx=0.,vy=0.,fixed=True)
r['bodies'].extend([gate,spring])
assert len({b['id'] for b in r['bodies']})==len(r['bodies'])
assert g._siege_oneway_pass(gate,220.) and not g._siege_oneway_pass(gate,-220.)
assert not g._siege_oneway_pass(spring,220.)
y=gate['y']
forward=g._siege_siegecar_trace(r,(gate['x']-90,y),(gate['x']+90,y))[0]
reverse=g._siege_siegecar_trace(r,(gate['x']+90,y),(gate['x']-90,y))[0]
assert forward is not gate,'friendly projectile crosses directional block'
assert reverse is gate,'reverse projectile collides with directional block'
old=spring['hp']
for n in range(4):
    assert g._siege_spring_hit(spring)
    assert spring['hp']<old
    old=spring['hp']
assert spring['hp']==0 and spring['springHits']==0
assert not g._siege_spring_hit(spring)
print('Siege specials: no preset blocks, directional pass, 4 impacts, recyclable materials PASS')
