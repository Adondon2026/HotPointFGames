"""Configurable zombie loot strength, 2/4/6 portals and cooperative bot tactics."""
import importlib.util,os,tempfile,random
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='siege_buff_strength_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

assert set(g._SIEGE_ZOMBIE_BUFF_INTENSITIES)=={'normal','advanced','rare'}
def world(level):
    r=g._siege_new('A','a',True,8,'classic','off',0)
    r.update(zombieSolo=True,zombiePlayerCount=1,zombieMap='front',
             zombieWaveMode='endless',zombieBuffIntensity=level)
    g._siege_v24_setup(r,'zombie')
    g._siege_field(r)
    return r

slots=[];pickup=[];draw_max=[];supply=[]
for level in ('normal','advanced','rare'):
    r=world(level)
    slots.append(len([x for x in r['items'] if 'slot' in x]))
    r['items']=[]
    item=g._siege_zombie_pickup(r,'springdrop',300,170)
    pickup.append(item['amount'])
    ceiling=max(g._SIEGE_ZOMBIE_RARITIES.index(
        {**g._SIEGE_V24_LEVELS,**r.get('rarities',{})}[g._siege_zombie_draw(r)])
        for _ in range(45))
    draw_max.append(ceiling)
    # Keep the supply experiment free of single-charge caps.
    r['allowedBuffs']=['springdrop','stonedrop','wooddrop','big','repeat']
    r['buffs'][0].update({k:0 for k in r['buffs'][0]})
    before=sum(r['buffs'][0].values())
    random.seed(142)
    g._siege_zombie_supply(r)
    supply.append(sum(r['buffs'][0].values())-before)
assert slots==[8,10,12],slots
assert pickup==[1,2,3],pickup
assert draw_max==[0,1,2],draw_max
assert supply==[1,2,3],supply
assert g._siege_zombie_buff_profile({'zombieBuffIntensity':'corrupt'})==g._SIEGE_ZOMBIE_BUFF_INTENSITIES['normal']
# Adding levels cannot silently override an existing whitelist or a chosen
# custom rarity, both of which remain independently room-authoritative.
r=world('rare')
r['allowedBuffs']=['springdrop']
assert set(g._siege_zombie_draw(r) for _ in range(20))=={'springdrop'}
r['rarities']={'springdrop':'precious'}
assert g._siege_zombie_draw(r) is None  # tier 3 is unavailable at round 1, even in strong mode

# Co-op bot must use the new tactical buffs and compound recipe instead of
# collecting skills indefinitely. Plan-only records the actual chosen action.
r=world('advanced')
r.update(zombieSolo=False,zombiePlayerCount=2,turn=1)
r['zombie']['wave']=4
g._siege_zombie_spawn(r)
inv=r['buffs'][1]
inv.update(skyportal=2,repeat=2,compound=1,splitshot=2,blackhole=1,bounceblast=1,pierce=1)
for k in ('wooddrop','stonedrop','springdrop'):inv[k]=0
r['compoundRecipes'][1]=['blackburst']
plan={'planOnly':True}
g._siege_bot(r,plan)
angle,power,selected=plan['plan']
assert 0<=angle<360 and 15<=power<=100
assert selected.get('skyportal',0)>=1,selected
assert selected.get('compound')==1,selected
assert selected.get('repeat',0)>=1,selected
assert selected.get('splitshot',0)>=1,selected
# The bot does not spend its mobility/building resources on normal attacks.
assert not any(k in selected for k in ('wooddrop','stonedrop','springdrop','gunteleport','coreteleport'))
print('Zombie buff intensity: 8/10/12 slots, 1/2/3 pickup & supplies, higher tiers, whitelist and AI tactical skills PASS')
