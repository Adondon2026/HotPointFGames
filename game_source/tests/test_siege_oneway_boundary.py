"""Endless exterior entry and finite-life building block collision regression."""
import importlib.util,os,tempfile,random,math
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='siege_gate_boundary_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

assert 'onewaydrop' in g._SIEGE_V24_SKILLS
assert 'onewaydrop' in g._SIEGE_PAYLOADS
assert g._SIEGE_OBJECT_LIMITS['onewaydrop']==24
assert g._SIEGE_V24_CAPS['onewaydrop']==5

def room(map_key):
    r=g._siege_new('A','a',True,8,'classic','off',0)
    r.update(zombieSolo=True,zombiePlayerCount=1,zombieMap=map_key,zombieWaveMode='endless')
    g._siege_v24_setup(r,'zombie')
    g._siege_field(r)
    r['phase']='play'
    return r

def exterior(z):
    return z['x']+z['w']/2<0 or z['x']-z['w']/2>960

# The opening wave already exists on the battlefield and is visible from
# outside-to-edge entry animation, before players fire. Reinforcements, unlike
# that pre-entered opening wave, still spawn fully beyond the exterior border.
for map_key in ('front','crossfire','ridge','basin','crest'):
    r=room(map_key)
    initial=[b for b in r['bodies'] if b['kind']=='zombie']
    assert initial and r['zombie']['wave']==1 and r['zombie']['spawned']==len(initial)
    assert all(not exterior(z) for z in initial),(map_key,[(b['x'],b['w']) for b in initial])
    assert all(exterior({**z,'x':z['entryFromX']}) for z in initial),map_key
    assert all(z['x']<=130 or z['x']>=830 for z in initial),map_key
    assert all((z['entryFromX']<0 and z['x']>z['entryFromX']) or
               (z['entryFromX']>960 and z['x']<z['entryFromX']) for z in initial),map_key
    if map_key in ('crossfire','basin','crest'):
        assert any(z['x']<130 for z in initial) and any(z['x']>830 for z in initial),map_key
    r['zombie']['wave']=6
    before={b['id'] for b in r['bodies']}
    # Interior obstacles deliberately fill common legacy spawn slots.
    for x in (40,90,840,900):
        r['bodies'].append(dict(id=r['nextBodyId'],side=0,kind='stone',x=x,y=390,w=48,h=50,hp=80,max=80,vx=0.,vy=0.,fixed=True))
        r['nextBodyId']+=1
    g._siege_zombie_spawn(r)
    new=[b for b in r['bodies'] if b['kind']=='zombie' and b['id'] not in before]
    assert new and all(exterior(z) for z in new),map_key

# The opening wave has pre-entered from the border and starts walking farther
# inward during the first ordinary enemy phase, before the next spawn.
r=room('front')
z=next(b for b in r['bodies'] if b['kind']=='zombie')
start=z['x']
snap=lambda t,p:[round(t,3),p,[g._siege_pos(b) for b in r['bodies']],[],6,[]]
g._siege_zombie_round(r,1,[],snap,[],None)
assert z['x']<start and z['x']>0 and z['x']<960,'zombie walks inward from right exterior'
assert z['x']-z['w']/2<960, 'first entrant should become visible naturally'

# A one-way item creates a normal physical stone building, not a world-only
# decorative tile; its blocking direction is authoritative and has four uses.
r=room('front')
assert not any(b.get('special') in ('oneway','spring') for b in r['bodies']), 'map must start without demo blocks'
r['buffs'][0]['onewaydrop']=1
g._siege_fire(r,70,56,{'onewaydrop':1})
blocks=[b for b in r['bodies'] if b.get('generated') and b.get('special')=='oneway']
assert blocks,'one-way item must build a real block'
block=blocks[0]
assert block['kind']=='stone' and block['hp']==block['max']==80 and block['onewayHits']==4
assert block['passDir']==g._siege_direction(r,0)
assert g._siege_oneway_pass(block,200*block['passDir'])
assert not g._siege_oneway_pass(block,-200*block['passDir'])
for remaining in (3,2,1,0):
    assert g._siege_oneway_hit(block)
    assert block['onewayHits']==remaining
    assert (block['hp']>0)==(remaining>0)
assert not g._siege_oneway_hit(block)

# Elastic blocks return a physically outward impulse with genuinely different
# randomized angles on repeated identical incoming hits, for both x signs.
plate=dict(x=400.,y=240.,w=42.,h=28.,kind='stone',hp=72.,max=72.,special='spring')
rng=random.Random(42)
shots=[g._siege_spring_bounce(plate,400,198,400,228,0.,380.,6.,rng) for _ in range(25)]
assert len({round(vx,1) for _,_,vx,vy in shots})>=15
assert any(vx>100 for _,_,vx,vy in shots)
assert any(vx< -100 for _,_,vx,vy in shots)
assert all(vy<0 and math.isfinite(vx) and math.isfinite(vy) for _,_,vx,vy in shots)
plate.update(springHits=4)
for left in (3,2,1,0):
    assert g._siege_spring_hit(plate)
    assert plate['springHits']==left
    assert (plate['hp']>0)==(left>0)

print('Zombie exterior entry, buildable/recyclable one-way 4-hit blocks, and seeded multidirectional spring bounce PASS')
