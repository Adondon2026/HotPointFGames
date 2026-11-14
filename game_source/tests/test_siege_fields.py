"""Six layouts, moving pickups, boost charges, physical obstacles and vision."""
import copy, importlib.util, math, os, random, tempfile
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def aim(r,side,x,y,a):
    sx,sy=g._siege_muzzle(side,r,a);d=1 if side==0 else -1;rad=math.radians(a);dx=(x-sx)*d;dy=y-sy;w=r['wind'];t2=(dy+dx*math.tan(rad))/(.5*(g._SIEGE_GRAV+d*w*math.tan(rad)))
    if t2<=0:return None
    t=math.sqrt(t2);p=(dx-.5*d*w*t*t)/(math.cos(rad)*t)/8
    return p if 15<=p<=100 else None
checks=0
for name,field in g._SIEGE_FIELDS.items():
    random.seed(13);r=g._siege_new('A','a',True,25,name,'high',0)
    assert r['field']==name and r['layout']==field['layout'] and len(r['items'])==25
    assert len(set(i['kind'] for i in r['items']))==13 and set(i['kind'] for i in r['items'])<=set(g._SIEGE_ITEMS)
    assert set(field['pool'])<=set(i['kind'] for i in r['items'][:6])
    for l,rr in zip(r['items'][:24:2],r['items'][1:24:2]):
        for t in (0,1,2):
            x,y=g._siege_item_pos(l,t);xx,yy=g._siege_item_pos(rr,t);assert abs(x+xx-960)<1e-6 and abs(y-yy)<1e-6
    assert any(g._siege_item_pos(i,0)!=g._siege_item_pos(i,1) for i in r['items'])
    for side in (0,1):
        for wind in (-52,0,52):
            q=copy.deepcopy(r);q['turn']=side;q['wind']=wind;q['items']=[];target=next(b for b in q['bodies'] if b['side']==1-side and b['kind']=='core')
            p=aim(q,side,target['x'],target['y'],48);assert p is not None
            g._siege_fire(q,48,p);assert any(b['hp']<b['max'] for b in q['bodies'] if b['side']==1-side),(name,side,wind,q['event']['impact']);checks+=1
    for it in r['items']:
        got=False
        for side in (0,1):
            for a in range(8,174,3):
                q=copy.deepcopy(r);q['bot']=False;q['turn']=side;q['wind']=0;q['items']=[dict(it)];q['motionEpoch']=g.time.time();p=aim(q,side,it['x'],it['y'],a)
                if p is None:continue
                g._siege_fire(q,a,p)
                if q['event']['pickups']:got=True;break
            if got:break
        assert got,(name,it);checks+=1
    g._siege_rematch(r);assert r['field']==name and r['shots']==[0,0]
random.seed(6);seen={g._siege_new('A','a',True,0,'random')['field'] for _ in range(80)};assert seen==set(g._SIEGE_FIELDS)|set(g._SIEGE_NEW_FIELDS)
# Legacy vision charges become usable power charges, not a required camera entitlement.
r=g._siege_new('A','a',True,0,'standard');r['buffs'][0]['vision']=2;g._siege_normalize_buffs(r)
assert 'vision' not in r['buffs'][0] and r['buffs'][0]['power']==2
# Moving pickup at a known point in flight, not at its static anchor.
r=g._siege_new('A','a',True,0);r['motionEpoch']=g.time.time();t=.5;a=math.radians(42);sx,sy=g._siege_muzzle(0,r,42);x=sx+520*math.cos(a)*t;y=sy-520*math.sin(a)*t+230*t*t
r['items']=[dict(id=0,kind='power',x=x-60*math.sin(t*1.35),y=y,r=15,mx=60,my=0,phase=0)];g._siege_fire(r,42,65);assert r['buffs'][0]['power']==1
# New buffs actually change the shot/impact; old base balance remains separate.
r=g._siege_new('A','a',True,0);q=copy.deepcopy(r);q['buffs'][0].update(through=1,splitshot=1);g._siege_fire(r,42,65);g._siege_fire(q,42,65);assert q['event']['passed'] and len(q['event']['extraBlasts'])==2 and q['buffs'][0]['through']==0
r=g._siege_new('A','a',True,0);q=copy.deepcopy(r);r['buffs'][0]['shock']=1;q['buffs'][0]['shock']=1;q['buffs'][1]['buffer']=1;g._siege_fire(r,42,65);g._siege_fire(q,42,65);assert q['event']['defenses']==['buffer'] and q['buffs'][1]['buffer']==0 and q['event']['frames']!=r['event']['frames']
r=g._siege_new('A','a',True,0,'obstacle');assert any(b['side']==-1 for b in r['bodies']);r['wind']=0
p=aim(r,0,480,365,20);assert p;g._siege_fire(r,20,p);assert r['event']['hitId']==16
print('Six fields:',checks,'actual trajectory checks; random, motion, migration, penetration, fragments, buffer, obstacle PASS')
