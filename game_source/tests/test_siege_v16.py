"""True muzzle, all-surface ricochet, independent fragment effects, relocation and finite black hole."""
import copy,importlib.util,math,os,tempfile,random
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp();spec=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def new(mode='standard'):return g._siege_new('A','a',True,0,mode,'off',0,'stock')
# 5 giant shells: all maps and sides have a clear forward shot, center starts at the actual muzzle.
for mode in (*g._SIEGE_FIELDS,*g._SIEGE_NEW_FIELDS):
 for side in (0,1):
  r=new(mode);r['turn']=side;r['buffs'][side]['big']=5;g._siege_fire(r,42,70,{'big':5});e=r['event'];x,y=e['frames'][0][1];mx,my=g._siege_muzzle(side,r,42,36,e['motionStart']);assert abs(x-mx)<.11 and abs(y-my)<.11,(mode,side,e['frames'][0]);assert y+36<g._siege_floor(r,x) and e['hitAt']>.05,(mode,side,e['hitAt']);assert e['radius']==36
# Every rigid surface including core reflects, before final explosion; no impact damage at first bounce.
for kind in ('stone','core'):
 r=new();r['bodies']=[b for b in r['bodies'] if b['kind']=='core' or (b['side']==1 and b['kind']=='stone')][:4];b=next(b for b in r['bodies'] if b['side']==1 and b['kind']==kind);b.update(x=430,y=350,fixed=True);r['bodies']=[b]+[q for q in r['bodies'] if q['kind']=='core' and q is not b];r['buffs'][0]['bounce']=1;g._siege_fire(r,5,55,{'bounce':1});e=r['event'];assert e['bounces'] and e['bounces'][0][0]<430 and e['bounces'][0][1]<395,(kind,e['bounces']);assert e['hitAt']>e['bounces'][0][2]
# Blocked giant is rejected without consuming the charge.
r=new();r['buffs'][0]['big']=5
try:g._siege_fire(r,175,60,{'big':5})
except ValueError:pass
else:raise AssertionError('blocked rear muzzle')
assert r['buffs'][0]['big']==5 and r['shots']==[0,0]
# Real inherited modifiers; split children do not recursively split.
r=new();r['buffs'][0].update(big=2,power=2,splitshot=1,bounce=1,blackhole=1,wooddrop=1,through=1);g._siege_fire(r,42,43,{k:n for k,n in r['buffs'][0].items() if n});e=r['event'];assert e['fragmentRadius']==18 and any(len(f[3])==2 for f in e['frames']);assert len(e['holes'])>=2 and len(e['drops'])>=2,(e['holes'],e['drops']);assert e['duration']>=max(h[2]+2 for h in e['holes'])-.02
# Separate teleports retain hp, target safe full-map column and consume only one.
for kind in ('gunteleport','coreteleport'):
 r=new();r['buffs'][0][kind]=3;core=next(b for b in r['bodies'] if b['side']==0 and b['kind']=='core');core['hp']=73;old=g._siege_launcher(0,r) if kind=='gunteleport' else (core['x'],core['y']);g._siege_fire(r,42,30,{kind:1});e=r['event'];assert e['teleports'] and e['teleports'][0][0]==kind and 45<=e['teleports'][0][4]<=915;assert r['buffs'][0][kind]==2 and 0<core['hp']<=73;assert old!=(g._siege_launcher(0,r) if kind=='gunteleport' else (core['x'],core['y']))
# Blackhole is an actual two-second attraction, stronger with more charges; no object disappears into it.
r=new();g._siege_fire(r,42,30);x,y=r['event']['impact'];base=new();b=next(b for b in base['bodies'] if b['side']==0 and b['kind']=='stone');b.update(x=x-100,y=350,w=24,h=24,hp=1000,max=1000);base['bodies']=[b]+[c for c in base['bodies'] if c['kind']=='core'];results=[]
for n in (0,1,3):
 q=copy.deepcopy(base);q['buffs'][0]['blackhole']=n;g._siege_fire(q,42,30,{'blackhole':n} if n else {});ev=q['event'];bb=next(c for c in q['bodies'] if c['id']==b['id']);assert bb['hp']>0;results.append(bb['x']);
 if n:assert len(ev['holes'])==1 and ev['duration']>=ev['holes'][0][2]+2-.02
assert results[2]>results[1]>results[0],results
print('v0.16: 22 giant launch checks, block/core bounce, safe blocked muzzle, inherited fragments, teleport, blackhole attraction PASS')
