"""Zombie loot is earned directly on kill, without extra pickup shots."""
import importlib.util,os,tempfile
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='siege_auto_loot_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def room(level='normal',players=1):
    r=g._siege_new('A','a',True,8,'classic','off',0)
    r.update(zombieSolo=players==1,zombiePlayerCount=players,zombieMap='front',
             zombieWaveMode='endless',zombieBuffIntensity=level)
    g._siege_v24_setup(r,'zombie')
    g._siege_field(r)
    r['phase']='play'
    return r

# Three levels still determine how many charges a kill grants. Killing a
# zombie does not create any world item or any pending respawn entry.
for level,charges in (('normal',1),('advanced',2),('rare',3)):
    r=room(level)
    r['allowedBuffs']=['wooddrop']
    r['buffs'][0]['wooddrop']=0
    z=next(b for b in r['bodies'] if b['kind']=='zombie')
    before_items=list(r['items']);before_respawns=list(r['respawns'])
    z['hp']=0
    pickups=[]
    g._siege_zombie_drops(r,owner=0,at=1.25,pickups=pickups)
    assert r['buffs'][0]['wooddrop']==charges,(level,r['buffs'][0]['wooddrop'])
    assert r['items']==before_items and r['respawns']==before_respawns
    assert len(pickups)==1 and pickups[0]['auto']
    assert pickups[0]['gained']==charges and pickups[0]['at']==1.25
    assert pickups[0]['kind']=='wooddrop' and pickups[0]['side']==0
    assert z['rewarded']
    g._siege_zombie_drops(r,owner=0,at=1.35,pickups=pickups)
    assert len(pickups)==1 and r['buffs'][0]['wooddrop']==charges, 'one kill earns only one reward'

# Owner priority, cross-player overflow and per-person cap are preserved.
r=room('rare',players=3)
r['allowedBuffs']=['wooddrop']
for i in range(3):r['buffs'][i]['wooddrop']=0
r['buffs'][1]['wooddrop']=4  # cap 5; remaining 2 charges overflow to teammates
events=[]
z=next(b for b in r['bodies'] if b['kind']=='zombie')
z['hp']=0;z['lastHitSide']=1
g._siege_zombie_drops(r,owner=0,at=2.,pickups=events)
assert [r['buffs'][i]['wooddrop'] for i in range(3)]==[2,5,0],r['buffs']
assert [(p['side'],p['gained']) for p in events]==[(1,1),(0,2)],events
assert all(p['auto'] for p in events)

# A full team can still kill enemies without overflow, fake extra objects or
# exceeding caps; future kills award nothing rather than adding hidden stacks.
r=room('rare',players=2)
r['allowedBuffs']=['wooddrop']
for inv in r['buffs']:inv['wooddrop']=g._siege_cap(r,'wooddrop')
before=len(r['items'])
z=next(b for b in r['bodies'] if b['kind']=='zombie');z['hp']=0
ev=[]
g._siege_zombie_drops(r,owner=1,at=3.,pickups=ev)
assert ev==[] and len(r['items'])==before and z['rewarded']
assert all(inv['wooddrop']==g._siege_cap(r,'wooddrop') for inv in r['buffs'])

# Rare compound loot must add matching recipes along with its inventory count.
r=room('rare')
r['allowedBuffs']=['compound'];r['zombie']['wave']=6
r['buffs'][0]['compound']=0;r['compoundRecipes'][0]=[]
earned=g._siege_zombie_reward(r,'giant',owner=0)
assert earned==[(0,'compound',3)],earned
assert r['buffs'][0]['compound']==3 and len(r['compoundRecipes'][0])==3

# The real shot pipeline must include the award in its replay feedback, while
# leaving r['items'] empty, never materializing kill loot.
r=room('advanced')
r['allowedBuffs']=['wooddrop'];r['items']=[]
r['buffs'][0]['wooddrop']=0
dead=next(b for b in r['bodies'] if b['kind']=='zombie')
dead['hp']=0
g._siege_fire(r,68,35,{})
awards=[p for p in r['event']['pickups'] if p.get('auto')]
assert awards and any(p['kind']=='wooddrop' and p['side']==0 and p['gained']>=1 for p in awards),awards
assert r['items']==[] and dead['rewarded']
print('Zombie auto-loot: no dropped items, 1/2/3 charges, co-op owner, cap overflow, compound recipes, live fire replay PASS')
