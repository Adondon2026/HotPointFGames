"""Air buff slots stay unchanged across any number of shots/waves; refills follow intensity."""
import importlib.util,os,tempfile
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='siege_air_slots_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def room(level='normal',mode='endless'):
    r=g._siege_new('A','a',True,8,'classic','off',0)
    r.update(zombieSolo=True,zombiePlayerCount=1,zombieMap='front',
             zombieWaveMode=mode,zombieBuffIntensity=level)
    g._siege_v24_setup(r,'zombie')
    g._siege_field(r)
    r['phase']='play'
    return r

def snapshot(r):
    return [(it['id'],it.get('slot'),it['kind'],it['amount'],it['x'],it['y'],it.get('recipe'))
            for it in r['items']]

# Endless waves used to reroll every existing slot. 8 consecutive rounds and
# 5-plus shots must not alter a single item that no shell has touched.
r=room('rare')
original=snapshot(r)
assert len(original)==12
snap=lambda t,p:[round(t,3),p,[g._siege_pos(b) for b in r['bodies']],[],6,[]]
for n in range(8):
    r['shots'][0]+=1
    assert not g._siege_refill(r)
    g._siege_zombie_round(r,1,[],snap,[],None)
    assert snapshot(r)==original,('uncollected items rerolled',n)
    assert not r['respawns']
assert r['zombie']['wave']==6

# Finite wave changes must also preserve the exact same air items.
r=room('advanced','classic')
original=snapshot(r)
for b in r['bodies']:
    if b['kind']=='zombie':b['hp']=0
snap=lambda t,p:[round(t,3),p,[g._siege_pos(b) for b in r['bodies']],[],6,[]]
g._siege_zombie_round(r,1,[],snap,[],None)
assert r['zombie']['wave']==2 and snapshot(r)==original

# A real shell acquires one occupied slot, and only that slot schedules a
# replacement. Current pickup shot is not counted as a subsequent shot.
for level,delay,layers in (('normal',2,1),('advanced',1,2),('rare',1,3)):
    r=room(level)
    r['items']=r['items'][:2]
    for it in r['items']:
        it.update(kind='wooddrop',amount=layers)
    obtained,other=r['items']
    x,y=g._siege_muzzle(0,r,0)
    obtained.update(x=x+9.,y=y,slot=0)
    other.update(x=850.,y=70.,slot=1)
    r['allowedBuffs']=['wooddrop']
    r['buffs'][0]['wooddrop']=0
    stable=(other['id'],other['kind'],other['amount'],other['x'],other['y'])
    g._siege_fire(r,0,20,{})
    assert r['shots'][0]==1
    assert any(p['id']==obtained['id'] for p in r['event']['pickups'] if not p.get('auto')),level
    assert len(r['items'])==1 and r['items'][0]['id']==other['id'],level
    assert len(r['respawns'])==1,level
    waiting=r['respawns'][0]
    assert waiting['slot']==0 and waiting['readyAt']==1+delay,(level,waiting)
    assert len(r['event']['refreshed'])==0
    assert (other['id'],other['kind'],other['amount'],other['x'],other['y'])==stable
    for _ in range(delay-1):
        r['shots'][0]+=1
        assert g._siege_refill(r)==[]
        assert len(r['items'])==1 and r['items'][0]['id']==other['id']
    r['shots'][0]+=1
    refreshed=g._siege_refill(r)
    assert len(refreshed)==1 and refreshed[0]['slot']==0,level
    assert refreshed[0]['kind']=='wooddrop' and refreshed[0]['amount']==layers,level
    assert len(r['items'])==2 and len(r['respawns'])==0
    assert (other['id'],other['kind'],other['amount'],other['x'],other['y'])==stable

print('Zombie air buffs: no reroll in 8 endless cycles or wave changes; replenish consumed slots after 2/1/1 subsequent shots PASS')
