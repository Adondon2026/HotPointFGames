"""v0.20.0 integration: server-authoritative new buffs, negatives and walls."""
import importlib.util, math, os, pathlib, random, tempfile, time
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='zmz_v20_')
spec=importlib.util.spec_from_file_location('v20',pathlib.Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
positives={'spiral','repeat','push','clone'}
negatives={'heavy','vanish','wobble','fart'}
assert positives<=set(g._SIEGE_ITEMS) and negatives==set(g._SIEGE_NEGATIVE)
assert positives<=set(g._SIEGE_SELECTABLE) and not (negatives&set(g._SIEGE_SELECTABLE))
assert len(g._SIEGE_ITEMS)==24
def fresh():
    r=g._siege_new('A','a',True,0,'standard','off',0,'stock')
    r['turn']=0;r['items']=[];r['wind']=0
    return r
def fire(r,power=85,angle=42,select=None):
    r['turn']=0;r['phase']='play';g._siege_fire(r,angle,power,select)
    assert r['event'] and r['shots'][0]>=1
    return r['event']
# Diverse item pools generate BOTH good and bad new pickups.
kinds=set()
for seed in range(32):
    random.seed(seed)
    f=g._SIEGE_FIELDS['standard']
    kinds.update(i['kind'] for i in g._siege_items(25,f,allowed=g._SIEGE_ITEMS))
assert kinds>=positives|negatives,kinds
# Negative effects are forced only on the NEXT own shot; repeated same kind is unique.
r=fresh();x,y=g._siege_muzzle(0,r,42)
r['items']=[dict(id=k,kind='heavy',amount=1,x=x+15*k,y=y,r=18) for k in (1,2)]
e=fire(r);assert 'heavy' not in e['negativeActive'] and r['negativePending'][0]=={'heavy':1}
r['items']=[];e=fire(r);assert e['negativeActive']==['heavy'] and not r['negativePending'][0]
base=fresh();baseline=fire(base)
heavy=fresh();heavy['negativePending'][0]['heavy']=1;eh=fire(heavy)
assert eh['impact'][0]<baseline['impact'][0]-120,(eh['impact'],baseline['impact'])
vanish=fresh();vanish['negativePending'][0]['vanish']=1;ev=fire(vanish)
sizes=[f[1][2] for f in ev['frames'] if f[1]]
assert sizes[0]>sizes[-1] and min(sizes)>=2.5
fart=fresh();fart['negativePending'][0]['fart']=1;ep=fire(fart)
assert len(ep['puffs'])>3 and ep['impact'][1]<baseline['impact'][1]-50
wobble=fresh();wobble['negativePending'][0]['wobble']=1;ew=fire(wobble)
assert 'wobble' in ew['negativeActive'] and ew['frames'][10][1]!=baseline['frames'][10][1]
combo=fresh()
for kind in negatives:combo['negativePending'][0][kind]=1
mix=fire(combo)
assert set(mix['negativeActive'])==negatives and not combo['negativePending'][0]
# The centre follows gravity but the spiral modulation changes as stack rises.
one=fresh();one['buffs'][0]['spiral']=1;e1=fire(one,select={'spiral':1})
three=fresh();three['buffs'][0]['spiral']=3;e3=fire(three,select={'spiral':3})
assert e1['frames'][6][1]!=e3['frames'][6][1]
# Additional shells appear at delayed frames; 3 stacks produce 4 total shell paths.
rep=fresh();rep['buffs'][0]['repeat']=3;er=fire(rep,select={'repeat':3})
assert max(len(frame[3]) for frame in er['frames'])>=3
assert len(er['frames'][0][3])==0
# Clone expires after two further owner shots and adds independently damaging projectiles.
cl=fresh();cl['buffs'][0]['clone']=1;ec=fire(cl,select={'clone':1})
assert len(cl['clones'])==1 and cl['clones'][0]['remaining']==2
ec2=fire(cl);assert cl['clones'][0]['remaining']==1 and any(p[0]>=300 for f in ec2['frames'] for p in f[3])
ec3=fire(cl);assert not cl['clones'] and any(p[0]>=300 for f in ec3['frames'] for p in f[3])
ec4=fire(cl);assert not any(p[0]>=300 for f in ec4['frames'] for p in f[3])
# Wall = invulnerable physical contact with explosion, and bounce uses side wall.
wall=fresh();wall['bodies']=[b for b in wall['bodies'] if b['kind']=='core'];ewall=fire(wall)
assert ewall['hitAt']>0 and ewall['impact'] and ewall['impact'][0]>=949
bb=fresh();bb['bodies']=[b for b in bb['bodies'] if b['kind']=='core'];bb['buffs'][0]['bounce']=2
eb=fire(bb,select={'bounce':2})
assert any(x>=940 for x,y,*_ in eb['bounces']),eb['bounces']
# All effects stack without changing attack-selection validation.
stack=fresh()
for kind in positives:stack['buffs'][0][kind]=2
stack['negativePending'][0].update({k:1 for k in negatives})
es=fire(stack,select={k:2 for k in positives})
assert positives<=set(es['attacks']) and negatives==set(es['negativeActive'])
# Two simultaneous shots use one server-authoritative common physics world.
sync=fresh();sync['bot']=False;sync['buffs'][0].update(spiral=2,repeat=2,clone=1);sync['negativePending'][1]['heavy']=1
sync['buffs'][1]['push']=1;sync['combatMode']='sync';sync['reloadSeconds']=0
rt=g._siege_sync_runtime(sync,time.time())
rt['plans']=[(42,80,{'spiral':2,'repeat':2,'clone':1}),(42,80,{'push':1})];rt['locked']=[True,True]
g._siege_sync_compute(sync,rt,time.time())
assert sync['shots']==[1,1] and rt['replay']['frames']
print('ZMZ v0.20.0: new buffs, negative next-shot triggers, compound physics, wall bounce, clones and sync PASS')
