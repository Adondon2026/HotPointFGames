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
g._siege_zombie_round(endless,1,[],snap_for(endless),[],None)
assert state['wave']==2 and state['spawned']>old,'must spawn even with living enemies remaining'
for _ in range(8):
    g._siege_zombie_round(endless,1,[],snap_for(endless),[],None)
assert state['wave']==6 and not state['won'] and state['round']==10
assert sum(b['kind']=='zombie' and b['hp']>0 for b in endless['bodies'])<=54
assert state['spawned']>=old+3
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
