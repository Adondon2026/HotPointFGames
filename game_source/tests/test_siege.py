import importlib.util,os,tempfile,math,json,time
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp();root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
a='a'*48;b='b'*48;c='c'*48
create=m.siege_request({'type':'create','key':a,'name':'A'});code=create['code'];assert create['phase']=='wait'
assert not m.siege_request({'type':'fire','key':a,'code':code,'angle':42,'power':65,'rev':0})['ok']
assert m.siege_request({'type':'join','key':b,'code':code,'name':'B'})['seat']==1
assert not m.siege_request({'type':'join','key':c,'code':code})['ok']
assert not m.siege_request({'type':'fire','key':b,'code':code,'angle':42,'power':65,'rev':0})['ok']
assert not m.siege_request({'type':'fire','key':a,'code':code,'angle':float('nan'),'power':65,'rev':0})['ok']
shot=m.siege_request({'type':'fire','key':a,'code':code,'angle':42,'power':65,'rev':0,'last':0});e=shot['event'];assert shot['ok'] and e['hitId'] is not None and shot['turn']==1
assert shot['cores'][1]<100 and shot['cores'][0]==100
assert any(b['hp']<b['max'] for b in shot['bodies'] if b['side']==1)
assert not any(b['hp']<=0 for b in shot['bodies'] if b['side']==1)
assert any(abs(a[2]-b[2])>1 for a,b in zip(e['frames'][0][2],e['frames'][-1][2]))
assert m.siege_request({'type':'state','key':b,'code':code,'last':0})['event']==e
assert m.siege_request({'type':'state','key':b,'code':code,'last':1})['event'] is None
assert not m.siege_request({'type':'fire','key':b,'code':code,'angle':42,'power':65,'rev':1})['ok']
r=m._SIEGE_ROOMS[code];r['until']=0
assert not m.siege_request({'type':'fire','key':b,'code':code,'angle':42,'power':65,'rev':0})['ok']
second=m.siege_request({'type':'fire','key':b,'code':code,'angle':42,'power':65,'rev':1,'last':1});assert second['ok'] and second['turn']==0 and second['shots']==[1,1]
# Mirrored fresh shots have essentially equal damage; structures settle and no invalid coordinates.
for side in (0,1):
 q=m._siege_new('A',a,True);q['turn']=side;m._siege_fire(q,42,65)
 assert 85<m._siege_core(q['bodies'],1-side)<100
 assert all(math.isfinite(z) for f in q['event']['frames'] for row in f[2] for z in row)
 assert len(json.dumps(q['event']))<150000
# bot acts automatically after playback; rematch clears state.
q=m.siege_request({'type':'create','key':a,'bot':True});r=m._SIEGE_ROOMS[q['code']];m._siege_fire(r,42,65);r['until']=0
v=m.siege_request({'type':'state','key':a,'code':q['code'],'last':1});assert v['shots']==[1,1]
r['phase']='over';r['until']=0;v=m.siege_request({'type':'rematch','key':a,'code':q['code'],'last':2});assert v['shots']==[0,0] and v['cores']==[100,100]
assert '/pet' not in m.HTML_PAGE and 'PET_PAGE' not in vars(m)
print('Siege: rooms, turn validation, duplicate protection, collapse, mirrored shots, sync, bot, rematch, pet removal PASS')
# Random symmetric layouts, complete type coverage, and actual projectile reachability.
import random
for seed in range(5):
    random.seed(seed);items=m._siege_items();assert len(items)==13
    assert set(i['kind'] for i in items)==set(list(m._SIEGE_ITEMS)[:6])
    for i,j in zip(items[:12:2],items[1:12:2]):
        assert i['x']+j['x']==960 and i['y']==j['y'] and i['kind']==j['kind']
    for it in items:
        got=False
        for side in (0,1):
            sx,sy=m._siege_launcher(side);dx=(it['x']-sx)*(1 if side==0 else -1)
            if dx<=0:continue
            for a1 in range(5,86,2):
                ar=math.radians(a1);den=2*math.cos(ar)**2*(it['y']-sy+dx*math.tan(ar))
                if den<=0:continue
                p1=math.sqrt(460*dx*dx/den)/8
                if not 15<=p1<=100:continue
                q=m._siege_new('A',a,True);q['turn']=side;q['items']=[dict(it)];m._siege_fire(q,a1,p1)
                if q['event']['pickups']:got=True;break
            if got:break
        assert got,it
assert m._siege_items()!=m._siege_items()
# An exact flight path picks up several distinct items, including duplicate charges.
r=m._siege_new('A',a,True);r['items']=[];angle,power=42,65;rad=math.radians(angle);v=power*8
for i,(t,kind) in enumerate(zip([.10,.20,.30,.40,.50,.60],['shield','shield','big','big','power','pierce'])):
    r['items'].append(dict(id=i,kind=kind,x=235+v*math.cos(rad)*t,y=390-v*math.sin(rad)*t+230*t*t,r=15))
m._siege_fire(r,angle,power);e=r['event'];assert len(e['pickups'])==6 and not r['items'] and e['attacks']==[]
assert [p['id'] for p in e['pickups']]==list(range(6));assert r['buffs'][0]['shield']==2 and r['buffs'][0]['big']==2
# Same charges last multiple corresponding turns. Different types activate together.
for remaining in [1,0]:
    r['turn']=1;m._siege_fire(r,5,15);assert r['event']['defenses']==['shield'] and r['buffs'][0]['shield']==remaining
    r['turn']=0;m._siege_fire(r,5,15);assert r['buffs'][0]['big']==remaining and r['event']['radius']==12
    assert r['event']['attacks']==(['big','power','pierce'] if remaining==1 else ['big'])
r['turn']=0;m._siege_fire(r,5,15);assert r['event']['attacks']==[] and r['event']['radius']==6
# Defensive effects actually reduce damage. Armor and shield both consume one charge.
base=m._siege_new('A',a,True);base['items']=[];m._siege_fire(base,42,65)
protected=m._siege_new('A',a,True);protected['items']=[];protected['buffs'][1].update(shield=2,armor=2);m._siege_fire(protected,42,65)
assert m._siege_core(protected['bodies'],1)>m._siege_core(base['bodies'],1)
assert protected['event']['defenses']==['shield','armor'] and protected['buffs'][1]['shield']==1 and protected['buffs'][1]['armor']==1
# Old saved pending buffs migrate without losing inventory.
r=m._siege_new('A',a,True);r['buffs']=[{'attack':'power','shield':True},{'attack':None,'shield':False}];m._siege_normalize_buffs(r)
assert r['buffs'][0]['power']==1 and r['buffs'][0]['shield']==1
print('Siege v0.7: randomized mirrored items, actual reachability, multi-pickup, stacked charges, simultaneous effects, stronger shield, migration PASS')

# All configured totals are exact, including disabled mode and even layouts.
for n in range(26):
    for seed in range(3):
        random.seed(seed);items=m._siege_items(n);assert len(items)==n
        assert len({i['id'] for i in items})==n
        for i,j in zip(items[:n//2*2:2],items[1:n//2*2:2]):
            assert i['x']+j['x']==960 and i['y']==j['y'] and i['kind']==j['kind']
        if n%2:assert items[-1]['x']==480
print('Siege v0.8: exact configurable counts 0–25, mirrored pairs PASS')
