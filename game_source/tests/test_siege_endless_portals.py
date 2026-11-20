"""Endless reinforcements, targeted portals, and generated recyclable spring blocks."""
import importlib.util,os,tempfile,copy,math
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='siege_endless_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
assert g._SIEGE_COMPOUND_RECIPES['blackburst']==('blackhole','bounceblast')
assert g._SIEGE_V24_CAPS['skyportal']==3
assert g._SIEGE_V24_LEVELS['skyportal']=='rare'
assert 'springdrop' in g._SIEGE_V24_SKILLS
assert g._SIEGE_V24_CAPS['springdrop']>=1

def new_zombie(mode):
    r=g._siege_new('A','a',True,8,'classic','off',0)
    r.update(zombieSolo=True,zombiePlayerCount=1,zombieMap='front',zombieWaveMode=mode)
    g._siege_v24_setup(r,'zombie')
    g._siege_field(r)
    r['phase']='play';r['items']=[]
    return r

def snap_for(r):
    return lambda t,p:[round(t,3),p,[g._siege_pos(b) for b in r['bodies']],[],6,[]]

endless=new_zombie('endless')
state=endless['zombie'];assert state['endless'] and state['wave']==1
old=state['spawned']
# The first wave is already present. Every three *complete player cycles*,
# not every shot or enemy action, produce one new reinforcement group.
for cycle in range(1,19):
    events=[]
    previous=state['spawned']
    g._siege_zombie_round(endless,1,[],snap_for(endless),events,None)
    expected_wave=min(state['totalWaves'],1+cycle//3)
    assert state['round']==cycle+1 and state['wave']==expected_wave,(cycle,state)
    triggered=[e for e in events if e[0]=='zombieWave']
    assert len(triggered)==int(cycle%3==0),(cycle,triggered)
    if cycle%3:
        assert state['spawned']==previous,(cycle,'reinforcement before third cycle')
    elif cycle<=15:
        assert state['spawned']>previous,(cycle,'third cycle must spawn even while enemies survive')
    assert not state['won']
assert state['wave']==6 and state['round']==19
assert sum(b['kind']=='zombie' and b['hp']>0 for b in endless['bodies'])<=54
assert state['spawned']>=old+3
# "Three rounds" means three full rotations across all player cannons.
# A single participant firing early in the round must never spawn a wave.
for seats in (2,3):
    coop=g._siege_new('A','a',True,0,'classic','off',0)
    coop.update(zombieSolo=False,zombiePlayerCount=seats,
                zombieMap='front',zombieWaveMode='endless')
    coop['players']=[dict(name='P'+str(i),key='k'+str(i)) for i in range(seats)]
    coop['shots']=[0]*seats
    g._siege_v24_setup(coop,'zombie')
    g._siege_field(coop)
    coop['phase']='play';coop['items']=[];coop['allowedBuffs']=[]
    starting=coop['zombie']['spawned']
    for fired in range(3*seats):
        assert coop['turn']==fired%seats
        g._siege_fire(coop,90,25,{})
        assert coop['zombie']['round']==1+(fired+1)//seats
        assert coop['zombie']['wave']==1+(fired+1)//(3*seats)
        if fired+1<3*seats:assert coop['zombie']['spawned']==starting
        assert coop['phase']=='play'
    assert coop['zombie']['spawned']>starting,('no wave after 3 complete rotations',seats)

finite=new_zombie('classic');before=finite['zombie']['spawned']
g._siege_zombie_round(finite,1,[],snap_for(finite),[],None)
assert finite['zombie']['wave']==1 and finite['zombie']['spawned']==before

portal=new_zombie('endless')
# Distribute three authentic living enemy bodies into separate non-overlapping clusters.
for b,x in zip([b for b in portal['bodies'] if b['kind']=='zombie'],[360.,620.,890.]):
    b['x']=x;b['y']=g._siege_floor_body(portal,x,b['w'])-b['h']/2
assert [len(g._siege_zombie_portal_targets(portal,n)) for n in (1,2,3)]==[2,4,6]
targets=g._siege_zombie_portal_targets(portal,3)
assert len(targets)==6 and all(20<=x<=940 and y>=20 for x,y in targets)
assert len({round(x,1) for x,y in targets})>=3
portal['buffs'][0]['skyportal']=3;portal['buffs'][0]['repeat']=1
g._siege_fire(portal,82,60,{'skyportal':3,'repeat':1})
ev=portal['event']
assert ev['skyPortals'] and len(ev['skyPortals'])==6
assert sum(e[0]=='skyPortal' for e in ev['behaviorEvents'])==6
assert ev['attackCounts']['skyportal']==3
assert portal['buffs'][0]['skyportal']==0
assert any(len(f[3])>=2 for f in ev['frames']),'portal volleys must appear as real replay fragments'
assert all(math.isfinite(x) for frame in ev['frames'] for row in frame[2] for x in row)

spring=new_zombie('endless')
spring['buffs'][0]['springdrop']=1
g._siege_fire(spring,70,56,{'springdrop':1})
deployed=[b for b in spring['bodies'] if b.get('generated') and b.get('special')=='spring']
assert deployed,'generated elastic block must be in authoritative world'
assert all(b['springHits']==4 and b['kind']=='stone' for b in deployed)
g._siege_spring_hit(deployed[0]);assert deployed[0]['springHits']==3
print('Siege v24 endless/spring/sky portal: continuous 6-tier spawn, 2/4/6 portals, repeated volley and spring drop PASS')
