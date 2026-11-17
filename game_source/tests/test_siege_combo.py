"""Regression tests for the Noita-inspired projectile pipeline and resource accounting."""
import importlib.util,os,tempfile,time
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def new():
    r=g._siege_new('A','a',True,0,'standard','off',0,'stock')
    r['bodies']=[b for b in r['bodies'] if b['kind']=='core']
    r['launchers']=[[235,368],[725,368]]
    return r

def fire(sel,config=None,angle=175,power=65):
    r=new();r['buffs'][0].update(sel)
    g._siege_fire(r,angle,power,sel,config=config)
    return r,r['event']

r,e=fire({'wooddrop':2,'stonedrop':1,'power':2,'blackhole':1},{'build':'safe'})
assert e['engineering'] and not e['holes'] and r['buffs'][0]['power']==2 and r['buffs'][0]['blackhole']==1
assert len(e['drops'])+r['buffs'][0]['wooddrop']+r['buffs'][0]['stonedrop']==3
assert e['cores']==[100,100],e['cores']
r,e=fire({'fuse':1},{'fuseMode':'strict','fuseTime':2})
assert abs(e['hitAt']-2)<.02,e['hitAt']
r,e=fire({'fuse':1},{'fuseMode':'either','fuseTime':2})
assert e['hitAt']<2,e['hitAt']
r,d=fire({'fuse':1},{'fuseMode':'delay','fuseTime':1})
assert abs(d['hitAt']-e['hitAt']-1)<.04,(d['hitAt'],e['hitAt'])
r,e=fire({'splitshot':2},{'splitMode':'timer','splitTime':.7,'parentEnd':'vanish'},90,65)
assert abs(e['hitAt']-.7)<.02 and any(v[0]=='spawn' and v[4]==4 for v in e['behaviorEvents']),e['behaviorEvents']
assert any(v[0]=='finish' and not v[4] for v in e['behaviorEvents'])
r,e=fire({'bounce':2,'larpa':2,'bounceblast':1},{})
assert e['bounces'] and 0<sum(v[4] for v in e['behaviorEvents'] if v[0]=='spawn')<=4
assert 0<sum(v[0]=='bounceBlast' for v in e['behaviorEvents'])<=2
r,e=fire({'bounce':1,'splitshot':1},{'splitMode':'bounce','parentEnd':'vanish'})
assert any(v[0]=='spawn' and v[4]==2 for v in e['behaviorEvents'])
r,e=fire({'downpour':1},{},90,65)
assert sum(v[4] for v in e['behaviorEvents'] if v[0]=='spawn' and v[5]=='down')==2
r,e=fire({'splitshot':1},{'splitMode':'expire','parentEnd':'vanish'})
assert any(v[0]=='spawn' and v[4]==2 for v in e['behaviorEvents'])
cfg=g._siege_config({'scopes':{'homing':'child','power':'mother'},'childFuseTime':2})
s=g._siege_compile_spec({'splitshot':1,'homing':1,'power':2},cfg)
assert 'homing' not in s['root'] and 'power' not in s['child'] and s['child']['homing']==1
assert g._siege_compile_spec({'homing':1},cfg)['root']['homing']==1
for bad in ({'fuseTime':float('nan')},{'scopes':{'bad':'child'}},{'splitMode':'unknown'}):
    try:g._siege_config(bad)
    except ValueError:pass
    else:raise AssertionError(bad)
b=lambda i,x,kind,**kw:dict(id=i,x=x,y=300,w=20,h=20,kind=kind,hp=42,**kw)
r={'bodies':[b(1,100,'wood',burnRounds=2),b(2,120,'wood'),b(3,140,'stone'),b(4,160,'wood')]}
assert g._siege_burn_round(r)
assert r['bodies'][0]['hp']==37 and r['bodies'][1]['burnRounds']==2 and not r['bodies'][2].get('burnRounds') and not r['bodies'][3].get('burnRounds')
for _ in range(4):g._siege_burn_round(r)
assert r['bodies'][0]['hp']==32 and r['bodies'][1]['hp']==32
r=new()
for inv in r['buffs']:inv['fuse']=1
now=time.time();rt=g._siege_sync_runtime(r,now)
rt['plans']=[(90,65,{'fuse':1}),(90,65,{'fuse':1})]
rt['configs']=[g._siege_config({'fuseTime':1}),g._siege_config({'fuseTime':2})]
g._siege_sync_compute(r,rt,now)
assert r['shots']==[1,1] and rt['replay'] and not any(inv['fuse'] for inv in r['buffs'])
# Every configurable copy pattern creates real, bounded shells.
for mode,pattern in [('expire','radial'),('trail','trail'),('chaos','chaos'),('orbit','orbit')]:
    r,e=fire({'larpa':2},{'copyMode':mode},90,65)
    n=sum(v[4] for v in e['behaviorEvents'] if v[0]=='spawn' and v[5]==pattern)
    assert 0<n<=4,(mode,e['behaviorEvents'])
r,e=fire({'splitshot':2},{'childSplit':True},90,65)
assert sum(v[4] for v in e['behaviorEvents'] if v[0]=='spawn' and v[5]=='secondary')==4
r,e=fire({'splitshot':1,'firearc':1},{},90,65)
assert e['fireArcs'],e['behaviorEvents']
# Persistent mines are unarmed on their deployment shot and trigger on a later shot.
r,e=fire({'mine':1},{},175,65)
assert len(r['mines'])==1 and e['mineEvents'][0][0]=='place'
m=r['mines'][0];r['turn']=0;r['phase']='play'
g._siege_fire(r,175,65,{})
assert not r['mines'] and any(v[0]=='detonate' for v in r['event']['mineEvents']),r['event']['mineEvents']
# A projectile shield is reserved for simultaneous combat and deflects an approaching shell.
r,e=fire({'shotshield':1},{},90,65)
assert r['buffs'][0]['shotshield']==1
r=new();r['combatMode']='sync';r['buffs'][0]['shotshield']=1
now=time.time();rt=g._siege_sync_runtime(r,now)
rt['plans']=[(20,65,{'shotshield':1}),(20,65,{})];rt['locked']=[True,True]
g._siege_sync_compute(r,rt,now)
samples=[v for f in rt['replay']['frames'] for v in f[2]]
assert any(v[0]=='shieldDeflect' for shot in samples for v in shot.get('behaviorEvents',[])), 'shield never deflected'
# A surviving hit object carries an attached gravity field.
r=new();r['bodies'].append(dict(id=90,side=1,x=430,y=350,w=40,h=70,kind='stone',hp=1000,max=1000,vx=0.,vy=0.))
r['buffs'][0]['blackhole']=1;g._siege_fire(r,5,55,{'blackhole':1},config={'blackholeMode':'attached'})
assert r['event']['holePaths'],r['event']['holes']
print('Siege combo: all projectile patterns, triggers, resource budgets, material fire, deflection, persistent mines and sync PASS')

# Catalog and lifecycle regressions: the browser must be able to enter and poll,
# and every UI must use exactly the same set of item kinds as the server.
import json
for page in (g.SIEGE_PAGE,g.HTML_PAGE):
    raw=page.split('const siegeCatalog=',1)[1]
    catalog=json.JSONDecoder().raw_decode(raw)[0]
    assert set(catalog)==set(g._SIEGE_ITEMS)
    assert len({v['path'] for v in catalog.values()})==len(catalog)
    assert len({v['color'] for v in catalog.values()})==11
    assert all(catalog[k]['color']=='#b4b7bc' for k in g._SIEGE_NEGATIVE)
assert "siegeBuffList.length" in g.HTML_PAGE
assert "n+'/16'" not in g.HTML_PAGE
assert 'return {unlock,enterBattle:' in g.SIEGE_PAGE
assert 'siegeV24Keys.map' in g.SIEGE_PAGE
key='b'*48
created=g.siege_request({'type':'create','key':key,'bot':True,'allowedBuffs':list(g._SIEGE_ITEMS)})
assert created['ok'] and created['bot']
code=created['code'];r=g._SIEGE_ROOMS[code]
first=g.siege_request({'type':'fire','key':key,'code':code,'rev':r['rev'],'angle':42,'power':65})
assert first['ok'] and first['shots']==[1,0]
r['until']=time.time()-1
second=g.siege_request({'type':'state','key':key,'code':code,'last':first['rev']})
assert second['ok'] and second['shots']==[1,1] and second['event']['side']==1
print('Siege catalog and bot handoff PASS')

# Free-fire trial: full inventory including negative and immediate-use items,
# no bot turn, no scoring or terminal state, preview leaves the room unchanged.
import copy
key='c'*48
v=g.siege_request({'type':'create','key':key,'trial':True})
assert v['ok'] and v['trial'] and v['ammo']==0 and v['buffMode']=='stock'
assert set(v['buffs'][0])==set(g._SIEGE_ITEMS) and all(v['buffs'][0][k] for k in g._SIEGE_ACTIVE_ITEMS) and not any(v['buffs'][0][k] for k in g._SIEGE_RETIRED)
code=v['code'];r=g._SIEGE_ROOMS[code]
r['bodies']=[b for b in r['bodies'] if b['kind']=='core']
r['launchers']=[[235,368],[725,368]]
# Put the dummy directly in a simple horizontal trajectory.
target=next(b for b in r['bodies'] if b['side']==1)
target.update(x=440,y=368,vx=0.,vy=0.,fixed=True)
cfg={'simple':True}
before=copy.deepcopy(r)
preview=g.siege_request({'type':'trialPreview','key':key,'code':code,'angle':5,'power':90,'selection':{'power':5},'config':cfg})
assert preview['ok'] and preview['paths'] and preview['damage']>0,preview
assert r['bodies']==before['bodies'] and r['buffs']==before['buffs'] and r['rev']==before['rev'] and r['shots']==[0,0]
for i in range(3):
    v=g.siege_request({'type':'fire','key':key,'code':code,'rev':r['rev'],'angle':5,'power':90,'selection':{'power':5},'config':cfg})
    assert v['ok'] and v['cores'][1]==100 and v['turn']==0 and v['phase']=='play' and v['shots']==[i+1,0]
    assert v['trialDamage']>0 and v['buffs'][0]['power']==5
    r['until']=0
v=g.siege_request({'type':'trialReset','key':key,'code':code,'mode':'sky'})
assert v['ok'] and v['field']=='sky' and v['shots']==[0,0] and len(v['bodies'])>2
# Level-dependent motion: actual velocity is updated at the apex, not a user-entered time.
cfg=g._siege_config({'simple':True})
for level in range(1,6):
    assert g._siege_motion_delta(200,-20,0,0,.5,1/60,{'dive':level},cfg,0,[],False)==(200,-20,False)
    x,y,dived=g._siege_motion_delta(200,1,0,0,.5,1/60,{'dive':level},cfg,0,[],False)
    assert x==0 and y==300+60*(level-1) and dived
    vx=200
    for j in range(1,301):
        vx,_,_=g._siege_motion_delta(vx,0,0,0,j/60,1/60,{'pingpong':level},cfg,0,[],False)
    assert vx==200*(-1)**level
    assert abs(g._siege_gravity({'antigrav':level},{})-460*max(-.5,1-.3*level))<1e-8
# Every inventory type has a named outcome description.
assert '俯冲开始时间（秒）' not in g.SIEGE_PAGE and '高级组合 · 母弹与子弹' not in g.SIEGE_PAGE
assert 'trialPreview' in g.SIEGE_PAGE and 'liteSiegeTrial' in g.HTML_PAGE
print('Siege trial and automatic modifier stacks PASS')

# Compare actual dive impact against a stationary dummy, holding angle/power fixed.
damage=[]
for n in (1,5):
    r=g._siege_new('Trial','d'*48,True,0,'classic','off',0,'stock')
    r['trial']=True;g._siege_trial_stock(r)
    r['bodies']=[b for b in r['bodies'] if b['kind']=='core']
    r['launchers']=[[235,368],[725,368]]
    # At 70 degrees and power 55, the apex lies near x=388.
    core=next(b for b in r['bodies'] if b['side']==1)
    core.update(x=388,y=380,w=150,h=40,vx=0.,vy=0.,fixed=True)
    g._siege_fire(r,70,55,{'dive':n},config={'simple':True})
    assert any(e[0]=='dive' for e in r['event']['behaviorEvents'])
    damage.append(r['trialDamage'])
assert 0<damage[0]<damage[1],damage
assert g._siege_release_interval(5,.35)<g._siege_release_interval(1,.35)
assert g._siege_dive_strike(5)==2
print('Siege dive strike damage and release density PASS')

# Exercise the final HTTP dispatcher, not just the isolated siege_request helper.
import threading, urllib.request, urllib.error
server=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
base='http://127.0.0.1:'+str(server.server_address[1])
def http(path,data=None):
    req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    try:res=urllib.request.urlopen(req,timeout=10)
    except urllib.error.HTTPError as e:res=e
    with res:return res.status,res.read()
def trial_api(data):
    status,raw=http('/trial/api/siege',data)
    return status,json.loads(raw)
try:
    status,page=http('/trial/siege')
    assert status==200 and b'/trial/api/siege' in page
    assert http('/siege?trial=1')[0]==200
    assert http('/trial/siege?from=%2Fr%2FABCDEF%2F')[0]==200
    assert http('/siege')[0]==404
    assert http('/api/siege',{'type':'create','key':'e'*48})[0]==404
    key='e'*48
    status,v=trial_api({'type':'create','key':key,'trial':True})
    assert status==200 and v['ok'] and v['trial'] and v['cores']==[100,100]
    code=v['code']
    assert trial_api({'type':'create','key':key,'trial':True})[1]['code']==code
    assert json.loads(http('/api/siege-trial',{'type':'state','key':key,'code':code})[1])['trial']
    def q(kind,**kw):return trial_api(dict(type=kind,key=key,code=code,**kw))[1]
    assert q('state')['trial']
    assert not trial_api(dict(type='state',key='f'*48,code=code))[1]['ok']
    assert not q('join')['ok']
    assert not q('return')['ok']
    p=q('trialPreview',angle=42,power=65,selection={'dive':1},config={'simple':True})
    assert p['ok'] and p['paths']
    v=q('fire',rev=v['rev'],angle=42,power=65,selection={'dive':1},config={'simple':True})
    assert v['ok'] and v['manualFlight'] and v['liveShots'][0]['controls']['dive']==1 and v['cores'][1]==100
    shot=v['liveShots'][0]['shotNo']
    assert not trial_api(dict(type='maneuver',key='f'*48,code=code,action='dive',shotNo=shot))[1]['ok']
    v=q('maneuver',action='dive',shotNo=shot)
    assert v['ok'] and v['slowRate']==.9 and v['liveShots'][0]['controls']['dive']==0
    assert not q('maneuver',action='dive',shotNo=shot)['ok']
    arena=g._SIEGE_ROOMS[code];clock=time.time()
    for j in range(1,121):
        if g._siege_manual_tick(arena,clock+j*.25):break
    v=q('state')
    assert v['ok'] and not v.get('manualFlight') and v['shots']==[1,0] and v['cores'][1]==100
    arena['until']=0
    v=q('trialReset',mode='sky')
    assert v['ok'] and v['field']=='sky' and v['shots']==[0,0]
    normal=g.siege_request(dict(type='create',key=key,bot=True))
    assert normal['ok'] and not normal['trial']
    assert not trial_api(dict(type='state',key=key,code=normal['code']))[1]['ok']
    assert q('leave')['ok'] and code not in g._SIEGE_ROOMS
    assert not q('state')['ok']
    assert not q('leave')['ok']
    assert http('/')[0]==200
    status,raw=http('/api/rooms',{'name':'Route regression'})
    assert status==200 and json.loads(raw)['ok']
    assert http('/api/rooms')[0]==200
finally:
    server.shutdown();server.server_close()
print('Siege trial HTTP route, isolation, preview, fire, reset PASS')

# Unified rules: exact child count, one generation, inherited movement and payloads.
def unified(sel,trigger=None,angle=90,power=25,**kw):
    r=new();r['stackCaps']=dict(g._SIEGE_HARD_CAPS);r['buffs'][0].update(sel)
    cfg={'unified':True,'build':'attack','triggers':trigger or {},**kw}
    g._siege_fire(r,angle,power,sel,config=cfg)
    return r,r['event']
cfg=g._siege_config({'unified':True,'triggers':{'splitshot':'bounce','wooddrop':'end'}})
spec=g._siege_compile_spec({'splitshot':5,'bounce':2,'through':3,'power':2,'shock':3,'wooddrop':5},cfg)
assert 'splitshot' not in spec['child'] and spec['child']=={'bounce':2,'through':3,'power':2,'shock':3,'wooddrop':5}
r,e=unified({'splitshot':5,'bounce':2},{'splitshot':'bounce'})
split=[v for v in e['behaviorEvents'] if v[0]=='split']
assert len(split)==1 and split[0][4]==5 and abs(split[0][5]-.2)<1e-8 and split[0][6]=='bounce',e['behaviorEvents']
assert len([b for b in e['bounces'] if b[3]==-1])==1 and any(b[3]>=0 for b in e['bounces'])
assert len({f[0] for frame in e['frames'] for f in frame[3]})==5
# No actual reflection = no reflection payload and full refund.
r,e=unified({'splitshot':5,'wooddrop':2},{'splitshot':'bounce','wooddrop':'bounce'})
assert not any(v[0]=='split' for v in e['behaviorEvents']) and not e['drops']
assert r['buffs'][0]['splitshot']==5 and r['buffs'][0]['wooddrop']==2
# Repeated real bounces dispatch the same payload, no hidden bounce charges.
r,e=unified({'bounce':3,'mine':2},{'mine':'bounce'})
assert e['payloadEvents']['mine']==3 and e['generatedCounts']['mine']==6
# A 5-way split with five material layers can exceed the old five-block limit.
r,e=unified({'splitshot':5,'wooddrop':5},{'splitshot':'launch','wooddrop':'end'},angle=90,power=25)
assert e['generatedCounts']['wooddrop']==24 and e['payloadEvents']['wooddrop']==5 and len(e['drops'])==24,(e['generatedCounts'],e['payloadEvents'],e['behaviorEvents'])
# With five independent terminal events, five layers still contribute to 24 blocks.
# Ten independent terminal events require only three layers after capping at 24.
r,e=unified({'repeat':1,'splitshot':5,'wooddrop':5},{'splitshot':'launch','wooddrop':'end'},angle=90,power=25)
assert len([v for v in e['behaviorEvents'] if v[0]=='split'])==2
assert e['payloadEvents']['wooddrop']==10 and e['generatedCounts']['wooddrop']==24 and r['buffs'][0]['wooddrop']==2,(e['payloadEvents'],e['generatedCounts'],r['buffs'][0])
# Terminal split waits until penetration has been exhausted; children start with their own through count.
r=new();r['buffs'][0].update(splitshot=5,through=1)
for i,x in enumerate((350,450,550)):
    r['bodies'].append(dict(id=90+i,side=1,x=x,y=350,w=24,h=120,kind='stone',hp=1000,max=1000,vx=0.,vy=0.,fixed=True))
g._siege_fire(r,5,75,{'splitshot':5,'through':1},config={'unified':True,'triggers':{'splitshot':'end'}})
e=r['event'];split=[v for v in e['behaviorEvents'] if v[0]=='split']
assert len(split)==1 and 420<split[0][2]<450 and 90 in e['passed'],(split,e['passed'])
assert next(b for b in r['bodies'] if b['id']==91)['hp']<1000
# Full-power repeat source shells independently conserve power when splitting.
for mode in ('serial','volley'):
    r,e=unified({'repeat':2,'splitshot':5},{'splitshot':'launch'},burstMode=mode)
    splits=[v for v in e['behaviorEvents'] if v[0]=='split']
    assert len(splits)==3 and all(v[4]==5 and abs(v[5]-.2)<1e-8 for v in splits),splits
assert len(g._SIEGE_ACTIVE_ITEMS)==35 and not set(g._SIEGE_RETIRED)&set(g._siege_allowed({'allowedBuffs':None}))
print('Siege unified: event dispatch, single-generation split, conserved power, full-power repeat, inherited penetration and capped/refunded payloads PASS')

# In synchronous combat, each child inherits a fresh projectile shield.
r=new();r['bot']=False;r['combatMode']='sync';r['buffs'][0].update(splitshot=5,shotshield=1)
rt=g._siege_sync_runtime(r,time.time());rt['plans']=[(90,25,{'splitshot':5,'shotshield':1}),(90,25,{})]
rt['configs']=[g._siege_config({'unified':True,'triggers':{'splitshot':'launch'}}),g._siege_config({'unified':True})]
g._siege_sync_compute(r,rt,time.time())
shots=[shot for frame in rt['replay']['frames'] for shot in frame[2] if shot['side']==0]
assert any(len(shot.get('shields',[]))==5 and all(sh['left']==2 for sh in shot['shields']) for shot in shots)
# The event blast radius and damage grow with layers, and each real bounce triggers once.
r,e=unified({'bounce':3,'bounceblast':5},{'bounceblast':'bounce'})
blasts=[v for v in e['behaviorEvents'] if v[0]=='bounceBlast']
assert len(blasts)==3 and all(v[4]==83 for v in blasts) and e['payloadEvents']['bounceblast']==3,blasts
assert 'drawPayloadBlasts' in g.SIEGE_PAGE and 'splitPattern' in g.SIEGE_PAGE and '二次分裂 · 开' not in g.SIEGE_PAGE
print('Siege unified shield inheritance and per-event explosion radius PASS')

# v0.23: player commands are authoritative changes to velocity; layer count is
# a shared per-shot click budget, not an automatic timed trajectory modifier.
for k in g._SIEGE_MANUAL_KEYS:
    r=new();r['buffs'][0][k]=5;now=time.time()
    cfg=g._siege_public_config({})
    g._siege_manual_start(r,0,45,65,{k:5},False,cfg,now)
    rt=g._SIEGE_MANUAL_ROUNDS[id(r)]
    g._siege_manual_tick(r,now+.2);before=rt['active'][0]['sample']
    x,y=before['p'];shot=before['shotNo']
    assert before['controls'][k]==5 and not any(e[0]=='maneuver' for e in before['behaviorEvents'])
    g._siege_command(rt,0,k,shot,now+.2)
    assert rt['slowRate']==.5 and rt['active'][0]['control']['left'][k]==4
    g._siege_manual_tick(r,now+.4);after=rt['active'][0]['sample'];xx,yy=after['p']
    assert after['controls'][k]==4 and any(e[0]=='maneuver' and e[4]==k for e in after['behaviorEvents'])
    assert .08<=after['age']-before['age']<=.12,(before['age'],after['age'])
    if k=='pingpong':assert xx<x,(x,xx)
    elif k=='dive':assert yy>y,(y,yy)
    else:assert yy<y,(y,yy)
    for j in range(3,161):
        if g._siege_manual_tick(r,now+j*.25):break
    assert id(r) not in g._SIEGE_MANUAL_ROUNDS and r['shots']==[1,0] and r['turn']==1 and r['buffs'][0][k]==4
# Delayed bounce split follows actual reflected motion.
r,e=unified({'splitshot':5,'bounce':2},{'splitshot':'bounce'},delayedSplit=True)
bounce=next(v for v in e['bounces'] if v[3]==-1);split=next(v for v in e['behaviorEvents'] if v[0]=='split')
assert .09<=split[1]-bounce[2]<=.13 and split[4]==5 and abs(split[3]-bounce[1])>5,(bounce,split)
# Actual concurrent round, not a replay: shared bullet time and owner-specific commands.
r=new();r['bot']=False;r['combatMode']='sync';r['buffs'][0]['dive']=3;r['buffs'][1]['pingpong']=2
now=time.time();rt=g._siege_sync_runtime(r,now);rt['plans']=[(55,65,{'dive':3}),(55,65,{'pingpong':2})];rt['configs']=[g._siege_public_config({}),g._siege_public_config({})]
g._siege_sync_compute(r,rt,now);engine=rt['activeEngine'];assert len(engine['active'])==2 and not rt['replay']
g._siege_sync_tick(r,rt,now+.2);left=engine['active'][0]['sample'];right=engine['active'][1]['sample']
try:g._siege_command(engine,1,'dive',right['shotNo'],now+.2);assert False
except ValueError:pass
g._siege_command(engine,0,'dive',left['shotNo'],now+.2)
g._siege_sync_tick(r,rt,now+.4)
assert engine['slowRate']==.7 and engine['active'][0]['sample']['controls']['dive']==2
assert abs(engine['active'][0]['sample']['age']-engine['active'][1]['sample']['age'])<.02
for j in range(3,161):
    if g._siege_sync_tick(r,rt,now+j*.25):break
assert not rt.get('activeEngine') and r['shots']==[1,1] and rt['round']==2
# Fire falls from the trajectory and can ignite a wooden structure below it.
r=new();r['buffs'][0]['firetrail']=3
r['bodies'].append(dict(id=90,side=1,x=400,y=395,w=100,h=42,kind='wood',hp=42,max=42,vx=0.,vy=0.,fixed=True))
g._siege_fire(r,60,65,{'firetrail':3},config={'unified':True,'delayedSplit':True})
assert r['event']['emberEvents'] and next(b for b in r['bodies'] if b['id']==90).get('burnDamage',0)>=14
# New map themes preserve map IDs and include a guaranteed legal bounce pickup.
for mode in ('fragments','peaks','obstacle','overtop'):
    r=g._siege_new('A','a',True,13,mode)
    assert r['field']==mode and any(i['kind']=='bounce' for i in r['items'])
r=g._siege_new('A','a',True,0,'fragments')
assert any(b['kind']=='wood' and b['h']>=70 for b in r['bodies'])
r=g._siege_new('A','a',True,0,'overtop');assert r['reflectors']
assert 'manualActions' in g.SIEGE_PAGE and 'siegeMapSize' in g.HTML_PAGE and 'trialSize' in g.SIEGE_PAGE
print('Siege v0.23: live maneuvers, shared bullet time, charges, delayed reflection split, falling fire and themed maps PASS')

# v0.24 compact rules: 23 items, fixed limits, independent skills, physical
# collision effects and seeded theme worlds. Historical tests above use v0.23.
def v24(theme='classic',allowed=None):
    r=new()
    if allowed is not None:r['allowedBuffs']=allowed
    g._siege_v24_setup(r,theme)
    r['items']=[];r['respawns']=[];r['until']=0
    return r
assert len(g._SIEGE_V24_KEYS)==26 and g._SIEGE_V24_CAPS['splitshot']==3 and g._SIEGE_V24_CAPS['repeat']==3
assert g._SIEGE_V24_CAPS['heal']==g._SIEGE_V24_CAPS['homing']==1
assert g._SIEGE_V24_CAPS['shield']==3 and g._SIEGE_V24_CAPS['bounce']==5
r=v24();r['buffs'][0].update(splitshot=3,repeat=3,bounceblast=1)
g._siege_fire(r,75,55,{'splitshot':3,'repeat':3,'bounceblast':1},config=g._siege_public_config({'triggers':{'splitshot':'end','bounceblast':'launch'}}))
e=r['event'];splits=[x for x in e['behaviorEvents'] if x[0]=='split']
assert len(splits)==4 and all(x[4]==8 and abs(x[5]-.125)<1e-8 and x[6]=='launch' for x in splits),splits
assert len({f[0] for fr in e['frames'] for f in fr[3] if f[0]>=20000})==32
assert not e['bounces'] and e['payloadEvents']['bounceblast']>0
# Giant shells gain meaningful blast damage and reach, with a more modest footprint.
r=v24();r['buffs'][0]['big']=3;g._siege_fire(r,75,55,{'big':3},config=g._siege_public_config({}))
assert r['event']['radius']==18 and r['event']['blastRadius']==82
# Controlled geometry: a vertical shell hits a fixed durable stone target.
def balance_target(kind='stone',x=235,y=240):
    r=v24();r['bodies']=[b for b in r['bodies'] if b['kind']=='core'];r['launchers']=[[235,368],[725,368]]
    b=dict(id=999,side=1,x=x,y=y,w=60,h=30,kind=kind,hp=1000,max=1000,vx=0.,vy=0.,fixed=True)
    r['bodies'].append(b);return r,b
damage=[]
for n in (0,1,3,5):
    r,b=balance_target();r['buffs'][0]['big']=n
    g._siege_fire(r,90,55,{'big':n} if n else {},config=g._siege_public_config({}))
    assert r['event']['hitId']==999
    damage.append(1000-b['hp'])
assert all(a<b for a,b in zip(damage,damage[1:])),damage
# A bounce damages the first contact and then the projectile keeps flying.
r,b=balance_target();r['buffs'][0]['bounce']=1
g._siege_fire(r,90,55,{'bounce':1},config=g._siege_public_config({}))
e=r['event'];hits=[x for x in e['behaviorEvents'] if x[0]=='bounceHit']
assert hits and hits[0][4]==999 and b['hp']<1000 and e['hitAt']>hits[0][1],(hits,b,e['hitAt'])
assert any(f[0]>hits[0][1]+.05 and f[1] for f in e['frames'])
print('Siege giant damage by layer:',damage,'ricochet contact + continued flight PASS')
# Empty inventory must accept every positive pickup, and expose it in public state.
for k in g._SIEGE_V24_KEYS:
    if k in g._SIEGE_NEGATIVE:continue
    r=v24();x,y=g._siege_muzzle(0,r,75)
    r['items']=[dict(id=999,kind=k,x=x,y=y,r=20,amount=1,zone='center',slot=999)]
    g._siege_fire(r,75,40,{},config=g._siege_public_config({}))
    assert r['buffs'][0][k]==1 and any(i['id']==999 for i in r['event']['pickups']),k
    assert g._siege_public(r,'a',-1)['buffs'][0][k]==1,k
print('Siege v0.24 positive pickup inventory and public state PASS')
# Elite items appear only at protected resource slots and obey the whitelist.
r=v24('classic',list(g._SIEGE_ELITE_KEYS))
assert g._siege_v24_draw(r,'air')=='salvage'
assert all(g._siege_v24_draw(r,'center') in ('demolish','compound') for _ in range(20))
# Compound adds one penetration and one explosion without consuming their stocks.
r=v24();r['buffs'][0]['compound']=1;r['compoundRecipes']=['burst',None]
g._siege_fire(r,90,40,{'compound':1},config=g._siege_public_config({}))
assert r['buffs'][0]['compound']==0 and r['event']['payloadEvents']['bounceblast']>0
# Curated recipes are committed at pickup, stable in public inventory, and
# consumed only at fire; each constituent adds one layer without spending stock.
assert set(g._SIEGE_COMPOUND_RECIPES)=={'breach','ricochet','burst','seek','siegebreak'}
for recipe,effects in g._SIEGE_COMPOUND_RECIPES.items():
    r=v24();x,y=g._siege_muzzle(0,r,75)
    r['items']=[dict(id=999,kind='compound',recipe=recipe,x=x,y=y,r=20,amount=1,zone='center')]
    g._siege_fire(r,75,40,{},config=g._siege_public_config({}))
    assert r['compoundRecipes'][0]==[recipe] and g._siege_public(r,'a',-1)['compoundRecipes'][0]==[recipe]
    r['turn']=0;r['until']=0
    g._siege_fire(r,75,40,{'compound':1},config=g._siege_public_config({}))
    assert r['event']['compoundRecipe']==recipe and tuple(r['event']['compoundEffects'])==effects and r['buffs'][0]['compound']==0 and r['compoundRecipes'][0]==[]
    assert all(r['buffs'][0][k]==0 for k in effects)
# Trial mode permits every recipe while keeping the total per-shot cap of 3.
r=v24();g._siege_trial_reset(r,'classic')
assert all(r['compoundRecipes'][0].count(k)==3 for k in g._SIEGE_COMPOUND_RECIPES)
try:g._siege_selection(r,{'compound:burst':3,'compound:seek':1},0);assert False
except ValueError:pass
assert g._siege_selection(r,{'compound:burst':2,'compound:seek':1},0)=={'compound:burst':2,'compound:seek':1}
g._siege_fire(r,75,40,{'compound:burst':2,'compound:seek':1},config=g._siege_public_config({}))
assert r['event']['compoundRecipesUsed']==['burst','burst','seek'] and r['buffs'][0]['compound']==3
# Mixed compound selection consumes only selected recipes, shares the cap of 3.
r=v24();r['buffs'][0]['compound']=3;r['compoundRecipes']=[['burst','breach','ricochet'],[]]
g._siege_fire(r,75,40,{'compound:burst':1,'compound:breach':1},config=g._siege_public_config({}))
assert r['event']['compoundRecipesUsed']==['burst','breach'] and r['event']['compoundEffects'].count('through')==2
assert r['buffs'][0]['compound']==1 and r['compoundRecipes'][0]==['ricochet']
# Presentation timing does not depend on the final simulated debris frame.
frames=[[0,[1,1],[],[],6,[]],[.1,None,[],[],6,[]],[6,None,[],[],6,[]]]
timing=g._siege_replay_timing(frames,6,.1)
assert timing==dict(shellEnd=.1,handoffAt=1.,visualEnd=.1,playbackDuration=1.48),timing
assert g._siege_replay_timing(frames,60,.1)==timing
# Real TNT action cannot be skipped or compressed, quiet jitter after it can.
frames=[[0,[1,1],[[1,200,300,42]],[],6,[]],[.1,None,[[1,200,300,42]],[],6,[]],[1.2,None,[[1,200,300,42]],[],6,[]],[1.4,None,[[1,260,300,42]],[],6,[]],[1.6,None,[[1,280,300,42]],[],6,[]],[2.,None,[[1,281,300,42]],[],6,[]],[6.,None,[[1,281.2,300,42]],[],6,[]]]
timing=g._siege_replay_timing(frames,6,.1,events=[['bounceBlast',1.2,200,300,92]])
assert 1.7<=timing['visualEnd']<=2.2 and timing['playbackDuration']>=timing['visualEnd'],timing
# The real public room lock follows playbackDuration, not physics duration.
r=v24();g._siege_fire(r,90,40,{},config=g._siege_public_config({}))
e=r['event'];assert e['handoffAt']>=1 and e['playbackDuration']>=round(e['handoffAt']+.48,3)
assert abs((r['until']-time.time())-(.38+e['playbackDuration']+.10))<.2
r=v24();now=time.time();rt=g._siege_sync_runtime(r,now);g._siege_sync_compute(r,rt,now)
e=rt['replay'];assert e['handoffAt']>=1 and abs((r['until']-time.time())-(.38+e['playbackDuration']+.10))<.2
assert rt['replay']['shellEnd']<=rt['replay']['duration']
print('Siege replay tempo: 0.1s shell, 1s viewing minimum, 1.48s display independent of debris PASS')
# Salvage removes either team's ORIGINAL or generated material, no core damage.
for owner in (0,1,-1):
    r=v24();r['bodies']=[b for b in r['bodies'] if b['kind']=='core'];r['buffs'][0]['salvage']=1
    b=dict(id=99,side=owner,x=235,y=350,w=36,h=38,kind='stone',hp=75,max=75,vx=0.,vy=0.)
    r['bodies'].append(b);g._siege_fire(r,90,40,{'salvage':1},config=g._siege_public_config({}))
    assert b['hp']==0 and r['buffs'][0]['salvage']==0 and r['buffs'][0]['stonedrop']==1 and r['event']['cores']==[100,100],(owner,b,r['event']['impact'])
# Actual opponent-half material contact, not just an enemy ownership label.
r=v24();r['bodies']=[b for b in r['bodies'] if b['kind']=='core'];g._siege_fire(r,45,70,{},config=g._siege_public_config({}))
pt=next(f[1] for f in r['event']['frames'] if f[1] and 530<f[1][0]<620)
r=v24();r['bodies']=[b for b in r['bodies'] if b['kind']=='core'];r['buffs'][0]['salvage']=1
b=dict(id=99,side=1,x=pt[0],y=pt[1],w=42,h=42,kind='wood',hp=42,max=42,vx=0.,vy=0.,fixed=True)
r['bodies'].append(b);g._siege_fire(r,45,70,{'salvage':1},config=g._siege_public_config({}))
assert b['hp']==0 and r['buffs'][0]['wooddrop']==1 and r['buffs'][0]['salvage']==0
# Three demolition charges widen the first impact and consume all three.
r=v24();r['buffs'][0]['demolish']=3;g._siege_fire(r,90,40,{'demolish':3},config=g._siege_public_config({}))
assert r['buffs'][0]['demolish']==0 and any(e[0]=='bounceBlast' and e[4]==160 for e in r['event']['behaviorEvents'])
# Salvage with no eligible material returns the charge.
r=v24();r['bodies']=[b for b in r['bodies'] if b['kind']=='core'];r['buffs'][0]['salvage']=1
g._siege_fire(r,90,40,{'salvage':1},config=g._siege_public_config({}))
assert r['buffs'][0]['salvage']==1
# Actual terminal effects: test an isolated material near the vertical shell.
for k in ('demolish','salvage'):
    r=v24();r['buffs'][0][k]=1
    b=dict(id=99,side=1 if k=='demolish' else 0,x=235,y=350,w=36,h=38,kind='wood',hp=42,max=42,vx=0.,vy=0.,generated=True)
    r['bodies'].append(b)
    g._siege_fire(r,90,40,{k:1},config=g._siege_public_config({}))
    assert b['hp']==0 and r['buffs'][0][k]==0,(k,b,r['event']['impact'])
    if k=='salvage':assert r['buffs'][0]['wooddrop']==1 and r['event']['cores']==[100,100]
print('Siege elite resources: protected pool, compound, demolition, salvage and refund PASS')
# Full inventory leaves the pickup at its position, including independent skills.
for k in ('shield','homing','splitshot','heal'):
    r=v24();r['buffs'][0][k]=g._SIEGE_V24_CAPS[k];x,y=g._siege_muzzle(0,r,75)
    r['items']=[dict(id=999,kind=k,x=x,y=y,r=20,amount=1,zone='center',slot=999)]
    g._siege_fire(r,75,40,{},config=g._siege_public_config({}))
    assert any(i['id']==999 for i in r['items']) and not any(i['id']==999 for i in r['event']['pickups'])
# Partial acceptance leaves remaining layers in place.
r=v24();r['buffs'][0]['bounce']=4;x,y=g._siege_muzzle(0,r,75)
r['items']=[dict(id=999,kind='bounce',x=x,y=y,r=20,amount=3,zone='center',slot=999)]
g._siege_fire(r,75,40,{},config=g._siege_public_config({}))
assert r['buffs'][0]['bounce']==5 and r['items'][0]['amount']==2
# Every positive skill uses the same draft/commit path; no immediate use.
r=v24();r['buffs'][0].update(shield=3,heal=1,coreteleport=1,gunteleport=1)
core=next(b for b in r['bodies'] if b['side']==0 and b['kind']=='core');core['hp']=50
for k in ('shield','armor','heal','coreteleport','gunteleport'):
    r['buffs'][0][k]=max(1,r['buffs'][0][k])
    assert g._siege_selection(r,{k:1},0)=={k:1}
    assert g._siege_selection(r,{k:0},0)=={}
    try:g._siege_v24_skill(r,0,k,None,time.time());assert False
    except ValueError:pass
assert core['hp']==50 and r['buffs'][0]['heal']==1 and not r['armed'][0]
g._siege_fire(r,75,40,{'shield':2,'heal':1},config=g._siege_public_config({}))
assert core['hp']==68 and r['buffs'][0]['heal']==0 and r['buffs'][0]['shield']==1 and r['armed'][0]['shield']==2
r=v24();r['buffs'][0]['heal']=1
g._siege_fire(r,75,40,{'heal':1},config=g._siege_public_config({}))
assert r['buffs'][0]['heal']==1
# Teleport destination can be in the opponent half; neither core may overlap.
for k in ('coreteleport','gunteleport'):
    r=v24();r['buffs'][0][k]=1
    g._siege_fire(r,45,70,{k:1},config=g._siege_public_config({}))
    assert r['event']['teleports'] and r['event']['teleports'][0][4]>480,(k,r['event']['impact'],r['event']['teleports'])
for k in ('coreteleport','gunteleport'):
    r=v24();r['buffs'][0][k]=1
    g._siege_fire(r,110,25,{k:1},config=g._siege_public_config({}))
    assert r['event']['teleports'] and r['event']['teleports'][0][0]==k and r['buffs'][0][k]==0,(k,r['event']['impact'],r['event']['teleports'])
    assert 35<=r['event']['teleports'][0][4]<=435
print('Siege v0.24 all skills: quantity selection, deferred heal/shield and legal teleport/refund PASS')
# Armor is a reversible draft, never an immediate-use skill.
r=v24();r['buffs'][0]['armor']=5
assert g._siege_selection(r,{'armor':5},0)=={'armor':5}
assert g._siege_selection(r,{'armor':2},0)=={'armor':2}
assert g._siege_selection(r,{'armor':0},0)=={} and r['buffs'][0]['armor']==5 and not r['armed'][0]
try:g._siege_v24_skill(r,0,'armor',None,time.time());assert False
except ValueError:pass
assert r['buffs'][0]['armor']==5
g._siege_fire(r,75,40,{'armor':2},config=g._siege_public_config({}))
assert r['buffs'][0]['armor']==3 and r['armed'][0]['armor']==2
assert 'armor' not in r['event']['attackCounts']
r['turn']=1
g._siege_fire(r,75,40,{},config=g._siege_public_config({}))
assert r['event']['defenseCounts']['armor']==2 and not r['armed'][0]
# Sync draft/cancel doesn't consume armor; the committed round does.
r=v24();r['buffs'][0]['armor']=5;now=time.time();rt=g._siege_sync_runtime(r,now)
g._siege_sync_plan(r,rt,0,{'round':rt['round'],'angle':75,'power':40,'selection':{'armor':4}},False)
g._siege_sync_plan(r,rt,0,{'round':rt['round'],'angle':75,'power':40,'selection':{'armor':1}},False)
assert r['buffs'][0]['armor']==5 and not r['armed'][0]
g._siege_sync_compute(r,rt,now)
assert r['buffs'][0]['armor']==4 and not r['armed'][0]
print('Siege v0.24 armor: reversible selection, commit and opposing defense, sync PASS')
# Automatic guidance: no influence in own half, mirrored strong steering in
# enemy half, every branch uses the same rule, no live controls.
import math
r=v24();cores=r['bodies'];cfg=g._siege_public_config({})
assert not g._siege_has_controls(r,{'homing':1},0,cfg)
r['buffs'][0]['homing']=1
assert not g._siege_has_controls(r,{'homing':1},0,cfg)
for side,x in ((0,479.99),(1,480.01)):
    assert g._siege_v24_guidance(100.,-300.,x,100.,1/60,side,cores)==(100.,-300.)
for side,x in ((0,510.),(1,450.)):
    target=next(b for b in cores if b['side']==1-side and b['kind']=='core')
    vx,vy=(350. if side==0 else -350.),-300.
    def err(vx,vy):
        return abs((math.atan2(target['y']-100.,target['x']-x)-math.atan2(vy,vx)+math.pi)%(2*math.pi)-math.pi)
    before=err(vx,vy)
    for _ in range(10):vx,vy=g._siege_v24_guidance(vx,vy,x,100.,1/60,side,cores)
    assert err(vx,vy)<before*.2 and math.hypot(vx,vy)<=800.000001
# Actual shots agree before midfield, then guided shells hit the exposed core.
def guidance_shot(side,selected):
    r=v24();r['turn']=side;r['buffs'][side].update(selected)
    g._siege_fire(r,45,70,selected,config=g._siege_public_config({}))
    return r['event']
for side in (0,1):
    normal=guidance_shot(side,{})
    guided=guidance_shot(side,{'homing':1})
    prefix=[(f[0],f[1]) for f in normal['frames'] if f[1] and (f[1][0]<480 if side==0 else f[1][0]>480)]
    assert prefix and all((f[0],f[1]) in prefix for f in guided['frames'] if f[1] and f[0]<=prefix[-1][0]),(side,prefix,guided['impact'])
    assert guided['cores'][1-side]<100 and guided['cores'][1-side]<normal['cores'][1-side],(side,normal['cores'],guided['cores'],guided['impact'])
# Split/serial projectile engine has automatic guidance without manual controls.
r=v24();sel={'homing':1,'splitshot':2,'repeat':1};r['buffs'][0].update(sel)
g._siege_fire(r,45,70,sel,config=cfg)
e=r['event'];assert len({f[0] for fr in e['frames'] for f in fr[3] if f[0]>=20000})==8
assert e['cores'][1]<100 and not any(v[0]=='maneuver' for v in e['behaviorEvents'])
assert id(r) not in g._SIEGE_MANUAL_ROUNDS
print('Siege v0.24 automatic homing: mirrored midfield gate, strong tracking, split and replay PASS')
# Physical barrels propagate, not merely visual particles.
r=v24('art')
for i,x in enumerate((350,405,460)):
    r['bodies'].append(dict(id=90+i,side=-1,x=x,y=365,w=20,h=24,kind='barrel',hp=18,max=18,vx=0.,vy=0.))
g._siege_fire(r,5,65,{},config=g._siege_public_config({}))
assert all(b['hp']==0 for b in r['bodies'] if b['kind']=='barrel')
assert len([e for e in r['event']['behaviorEvents'] if e[0]=='bounceBlast'])>=3
# Theme selection and persistent protected resource weights.
for theme in ('classic','art'):
    r=v24(theme);r.update(mode='random',itemCount=13);g._siege_field(r)
    assert len(r['items'])==13 and set(i['kind'] for i in r['items'])<=set(g._siege_allowed(r))
    assert any(i['zone']=='center' for i in r['items'])
    assert all(i['kind'] in ('demolish','compound') for i in r['items'] if i['zone'] in ('center','side'))
    assert all(i['kind'] not in ('demolish','compound') for i in r['items'] if i['zone']=='air')
    if theme=='art':assert any(b['kind']=='barrel' for b in r['bodies']) and 'heal' not in g._siege_allowed(r)
    it=next(i for i in r['items'] if i['zone']=='center');r['items'].remove(it)
    r['respawns']=[{**it,'readyAt':0}];r['bodies']=[b for b in r['bodies'] if b['kind']=='core']
    g._siege_refill(r);refill=next(i for i in r['items'] if i['slot']==it['slot'])
    assert refill['zone']=='center' and (refill['x'],refill['y'])==(it['x'],it['y']) and refill['kind'] in ('demolish','compound')
assert 'siegeRarityModal' in g.HTML_PAGE and 'v24StockSummary' in g.SIEGE_PAGE and 'skillDock' not in g.SIEGE_PAGE
print('Siege v0.24: 32 conserved projectiles, giant radius, capped pickups, skill charges, point guidance, barrel chains, theme and persistent rarity PASS')

# Negative effects are independent of rarity configuration and protected slots.
r=v24('classic',['heavy','splitshot'])
g._siege_v24_setup(r,'classic',{'heavy':'precious','splitshot':'rare'})
assert 'heavy' not in r['rarities']
for zone in ('side','center'):
    assert all(g._siege_v24_draw(r,zone) is None for _ in range(30))
r=v24('classic',['heavy'])
assert g._siege_v24_draw(r,'air')=='heavy' and g._siege_v24_draw(r,'center') is None
r.update(mode='random',itemCount=13);g._siege_field(r)
assert len(r['items'])==13 and all(i['zone']=='air' and i['kind']=='heavy' for i in r['items'])
assert 'siege-theme-switch' in g.HTML_PAGE and 'v24StockSummary' in g.SIEGE_PAGE and 'stock-group-label' in g.SIEGE_PAGE
print('Siege UI polish: fixed negative resource pool and grouped stock controls PASS')


# Dual TNT and terminal-only support. Historical v0.23 behaviour remains above.
assert g._SIEGE_V24_CAPS['tntdrop']==g._SIEGE_V24_CAPS['tntwait']==5
for s in ({'tntdrop':2,'splitshot':2},{'tntdrop':5,'tntwait':5,'splitshot':3,'repeat':3}):
    alloc=g._siege_tnt_alloc(s)
    assert sum(sum(a.values()) for a in alloc)==8
    assert sum(bool(a) for a in alloc)==(4 if not s.get('repeat') else 8)
    assert all(all(n<=s[k] for k,n in a.items()) for a in alloc)
# Support material emits only at the terminal collision, not at the wall bounce.
r=v24();r['buffs'][0].update(bounce=1,wooddrop=2)
g._siege_fire(r,175,65,{'bounce':1,'wooddrop':2},config=g._siege_public_config({}))
e=r['event'];assert e['bounces'] and e['payloadEvents']['wooddrop']==1
assert e['generatedCounts']['wooddrop']==2 and e['cores']==[100,100],e
# Automatic TNT waits for support AND a quiet interval, then irreversibly lights.
b=dict(kind='tnt',hp=18,x=400,y=300,w=24,h=24,vx=0.,vy=0.)
for j in range(30):g._siege_tnt_step(b,[b],416,j/60,1/60)
assert 'tntDeadline' not in b
b['y']=404
for j in range(12):g._siege_tnt_step(b,[b],416,1+j/60,1/60)
assert abs(b['tntDeadline']-(1+11/60+1))<1e-8
deadline=b['tntDeadline'];b['vy']=-300
g._siege_tnt_step(b,[b],416,1.3,1/60);assert b['tntDeadline']==deadline
# Actual automatic TNT is generated and explodes before the shot finishes.
r=v24();r['buffs'][0]['tntdrop']=1
g._siege_fire(r,90,40,{'tntdrop':1},config=g._siege_public_config({}))
e=r['event'];auto=[b for b in r['bodies'] if b['kind']=='tnt']
assert len(auto)==1 and auto[0]['hp']==0 and auto[0].get('detonated'),(auto,e['duration'])
assert e['generatedCounts']['tntdrop']==1 and any(x[0]=='bounceBlast' for x in e['behaviorEvents'])
last_blast=max(x[1] for x in e['behaviorEvents'] if x[0]=='bounceBlast')
assert .60<=e['duration']-last_blast<2.0,(e['duration'],last_blast)
print('Siege TNT quiet settle tail:',round(e['duration']-last_blast,3))
# Waiting TNT survives a shot without a fuse.
r=v24();r['buffs'][0]['tntwait']=1
g._siege_fire(r,90,40,{'tntwait':1},config=g._siege_public_config({}))
waiting=[b for b in r['bodies'] if b['kind']=='tnt_wait']
assert len(waiting)==1 and waiting[0]['hp']>0 and 'tntDeadline' not in waiting[0]
# Direct hit starts a real chain, but a distant waiting entity stays alive.
r=v24()
for i,(x,y) in enumerate(((235,250),(270,250),(305,250),(540,404))):
    r['bodies'].append(dict(id=90+i,side=1,x=x,y=y,w=24,h=24,kind='tnt_wait',hp=18,max=18,vx=0.,vy=0.,generated=True))
g._siege_fire(r,90,40,{},config=g._siege_public_config({}))
tnts=[b for b in r['bodies'] if b['kind']=='tnt_wait']
assert all(b['hp']==0 and b.get('detonated') for b in tnts[:3]),tnts
assert tnts[3]['hp']>0 and 'tntDeadline' not in tnts[3],tnts
assert len([e for e in r['event']['behaviorEvents'] if e[0]=='bounceBlast'])==3
assert g._siege_wall_damage(120)==0 and 80<g._siege_wall_damage(650)<=85
assert g._siege_wall_damage(200)<g._siege_wall_damage(400)<g._siege_wall_damage(650)
r=v24();core=next(b for b in r['bodies'] if b['kind']=='core' and b['side']==1)
core.update(x=940,y=394,vx=650.,vy=0.)
g._siege_fire(r,90,40,{},config=g._siege_public_config({}))
assert 0<core['hp']<100,core
# At an already damaged core, a high-speed boundary strike can finish the game.
r=v24();core=next(b for b in r['bodies'] if b['kind']=='core' and b['side']==1)
core.update(x=940,y=394,vx=650.,vy=0.,hp=20)
g._siege_fire(r,90,40,{},config=g._siege_public_config({}))
assert core['hp']==0 and r['winner']==0,core
print('Siege dual TNT: shared allocation, terminal support, fuse, persistent trap, chain and wall collision PASS')

# Real simulated impulses, not just event counters: same-side TNT accelerates a
# core further towards the wall than the same charges spread around it.
def chain_layout(xs):
    r=v24();core=next(b for b in r['bodies'] if b['kind']=='core' and b['side']==1)
    core.update(x=800,y=394,vx=0.,vy=0.)
    for i,x in enumerate(xs):
        r['bodies'].append(dict(id=90+i,side=0,x=x,y=404,w=24,h=24,kind='tnt_wait',hp=18,max=18,vx=0.,vy=0.,generated=True,tntDeadline=0,tntSource=0))
    g._siege_fire(r,90,40,{},config=g._siege_public_config({}))
    e=r['event'];right=max(z[1] for f in e['frames'] for z in f[2] if z[0]==core['id'])
    assert len([v for v in e['behaviorEvents'] if v[0]=='bounceBlast'])==3
    return right,core['hp']
same=chain_layout((720,746,772));opposite=chain_layout((720,854,828))
assert same[0]>opposite[0]+50 and same[1]<opposite[1]-5,(same,opposite)
print('TNT directional impulse comparison:',same,opposite)
# Black hole + automatic TNT, with an actual terminal placement and later detonation.
r=v24();r['buffs'][0].update(blackhole=1,tntdrop=1)
g._siege_fire(r,90,40,{'blackhole':1,'tntdrop':1},config=g._siege_public_config({}))
e=r['event'];assert e['payloadEvents']['blackhole']==1 and e['generatedCounts']['tntdrop']==1
assert any(b['kind']=='tnt' and b.get('detonated') for b in r['bodies'])
# Maximum projectile combination respects the shared charge budget in the actual world.
r=v24();sel=dict(splitshot=3,repeat=3,tntdrop=5,tntwait=5);r['buffs'][0].update(sel)
g._siege_fire(r,75,55,sel,config=g._siege_public_config({}))
counts=r['event']['generatedCounts']
assert 0<counts['tntdrop'] and 0<counts['tntwait'] and counts['tntdrop']+counts['tntwait']<=8,counts
for k in ('tntdrop','tntwait'):assert r['buffs'][0][k]==5-min(5,counts[k]),(k,counts,r['buffs'][0])
# Waiting stock cap returns unused inventory and never deletes existing traps.
r=v24();r['buffs'][0]['tntwait']=1
for i in range(12):
    r['bodies'].append(dict(id=90+i,side=0,x=400+35*i,y=404,w=24,h=24,kind='tnt_wait',hp=18,max=18,vx=0.,vy=0.,generated=True))
g._siege_fire(r,90,40,{'tntwait':1},config=g._siege_public_config({}))
assert r['event']['generatedCounts'].get('tntwait',0)==0 and r['buffs'][0]['tntwait']==1
assert sum(b['kind']=='tnt_wait' and b['hp']>0 for b in r['bodies'])==12
print('Siege physical combinations: directional TNT, blackhole TNT, actual 32-shell budget and persistent trap cap PASS')

# Cooperative zombie theme: two guns face the same direction, one shared core,
# server-authoritative alternating shots and enemy phase after both shots.
r=v24('zombie');g._siege_field(r)
assert r['combatMode']=='turn' and r['ammo']==0 and len([b for b in r['bodies'] if b['kind']=='core'])==1
assert g._siege_core(r['bodies'],0)==g._siege_core(r['bodies'],1)==100
assert g._siege_muzzle(1,r,45)[0]>r['launchers'][1][0]
z=next(b for b in r['bodies'] if b['kind']=='zombie');x=z['x']
g._siege_fire(r,90,25,{},config=g._siege_public_config({}))
assert r['turn']==1 and z['x']==x and r['zombie']['round']==1
g._siege_fire(r,90,25,{},config=g._siege_public_config({}))
assert r['turn']==0 and r['zombie']['round']==2 and z['x']<x and r['event']['zombiePhase']>=0
assert g._siege_public(r,'a',-1)['zombie']['wave']==1
# Advance all waves, win together, and restart without stale enemy state.
for wave in range(1,7):
    for b in r['bodies']:
        if b['kind']=='zombie':b['hp']=0
    r['turn']=1;g._siege_fire(r,90,25,{},config=g._siege_public_config({}))
    if wave<6:assert r['zombie']['wave']==wave+1 and r['phase']=='play'
assert r['phase']=='over' and r['zombie']['won']
g._siege_rematch(r);assert r['zombie']['wave']==1 and not r['zombie']['won']
# Real enemy attack consumes shared defense and can end the game.
r=v24('zombie');g._siege_field(r);core=g._siege_core_body(r['bodies'],0)
r['bodies']=[core];z=dict(id=999,side=2,kind='zombie',zombieType='giant',x=core['x']+48,y=377,w=58,h=78,hp=190,max=190,vx=0.,vy=0.,fixed=True)
r['bodies'].append(z);r['zombie']['spawned']=1;r['turn']=1;r['armed'][0]={'shield':1}
g._siege_fire(r,90,25,{},config=g._siege_public_config({}))
assert abs(core['hp']-(100-24*.35))<.01 and r['armed']==[{},{}],core
core['hp']=10;r['turn']=1
g._siege_fire(r,90,25,{},config=g._siege_public_config({}))
assert r['phase']=='over' and not r['zombie']['won'] and g._siege_core(r['bodies'],1)==0
print('Siege zombie coop: shared core, same direction, alternating turns, enemy action, six waves, defeat and rematch PASS')

# Cooperative loot respects the room whitelist, wave gate and enemy strength.
r=v24('zombie');r['allowedBuffs']=['big','repeat','homing'];g._siege_field(r)
assert set(g._siege_allowed(r))=={'big','repeat','homing'}
assert all(i['kind']=='big' for i in r['items'])
assert all(not n or k=='big' for inv in r['buffs'] for k,n in inv.items())
assert g._siege_zombie_draw(r,'giant')=='big'
r['zombie']['wave']=3
assert g._siege_zombie_draw(r,'heavy')=='repeat'
r['zombie']['wave']=5
assert g._siege_zombie_draw(r,'giant')=='homing'
z=next(b for b in r['bodies'] if b['kind']=='zombie');z['hp']=0
n=len(r['items']);g._siege_zombie_drops(r);g._siege_zombie_drops(r)
assert len(r['items'])==n+1 and r['items'][-1]['kind']=='big' and 'slot' not in r['items'][-1]
r['allowedBuffs']=[];assert g._siege_zombie_draw(r) is None
# Difficulty scales real spawned enemies, and higher difficulties give larger drops.
r=v24('zombie');r['zombieDifficulty']='hell';g._siege_field(r)
z=next(b for b in r['bodies'] if b['kind']=='zombie')
assert z['hp']==round(44*1.55,1) and r['zombie']['difficulty']=='hell'
z['hp']=0;g._siege_zombie_drops(r)
assert r['items'][-1]['amount']==2
print('Siege coop progression: whitelist, rarity gates, single enemy drops and difficulty PASS')

# New cannon bodies, full-circle firing, and terrain-specific cooperative play.
r=v24('zombie');r['zombieMap']='crossfire';g._siege_field(r)
assert r['zombieBothSides'] and len([b for b in r['bodies'] if b['kind']=='cannon'])==2
assert g._siege_core_body(r['bodies'],0)['x']==480
assert g._siege_muzzle(0,r,0)[0]<g._siege_launcher(0,r)[0]
assert g._siege_muzzle(1,r,0)[0]>g._siege_launcher(1,r)[0]
assert min(b['x'] for b in r['bodies'] if b['kind']=='zombie')<480<max(b['x'] for b in r['bodies'] if b['kind']=='zombie')
r=v24('zombie');r['zombieMap']='ridge';g._siege_field(r)
gun=g._siege_cannon(r,0);assert gun and not gun.get('fixed')
assert g._siege_floor(r,100)<g._siege_floor(r,480)
assert g._siege_launcher(0,r)[1]<g._siege_launcher(1,r)[1]
assert g._siege_muzzle(0,r,270)[1]>g._siege_launcher(0,r)[1]
old=g._siege_launcher(0,r);gun['x']+=8;assert g._siege_launcher(0,r)[0]==old[0]+8
# A cooperative defense remains armed during the teammate shot and clears at the enemy phase.
r=v24('zombie');g._siege_field(r);r['buffs'][0]['shield']=1
g._siege_fire(r,90,25,{'shield':1},config=g._siege_public_config({}))
assert r['armed'][0].get('shield')==1 and r['turn']==1
g._siege_fire(r,90,25,{},config=g._siege_public_config({}))
assert r['event']['armedBefore'][0]['shield']==1 and r['armed']==[{},{}]
# A solo round advances zombies directly, never a synthetic opponent.
r=v24('zombie');r['zombieSolo']=True;r['bot']=False;r['players']=r['players'][:1];g._siege_field(r)
assert len([b for b in r['bodies'] if b['kind']=='cannon'])==1
g._siege_fire(r,270,25,{},config=g._siege_public_config({}))
assert r['turn']==0 and r['zombie']['round']==2 and len(r['players'])==1
print('Siege new terrain, physical cannon, all-angle aim, defense lifetime and solo regression PASS')

# Core is a penetrable target, and damage is applied before continued flight.
r,b=balance_target('core');r['buffs'][0]['through']=1
g._siege_fire(r,90,55,{'through':1},config=g._siege_public_config({}))
assert b['id'] in r['event']['passed'] and b['hp']<b['max'],(b,r['event']['passed'])
# Every special enemy appears in the wave roster; first wave remains approachable.
assert set(('runner','pole','bomber','priest','dancer','guard','siegecar'))<=set(k for wave in g._SIEGE_ZOMBIE_WAVES for k in wave)
assert set(g._SIEGE_ZOMBIE_WAVES[0])=={'walker'}
# Reward history should avoid identical draws when multiple choices are available.
r=v24('zombie');r['allowedBuffs']=['big','bounce','wooddrop','stonedrop','push'];g._siege_field(r)
assert len({g._siege_zombie_draw(r) for _ in range(30)})>=3
# Bot separates a planned barricade from its offensive round.
r=v24('zombie');g._siege_field(r);r['turn']=1
r['buffs'][1].update(wooddrop=2,stonedrop=2,pierce=1)
r['zombie']['round']=3
captured=[];original=g._siege_bot_fire
try:
    g._siege_bot_fire=lambda r,a,p,live=None,planned=None:captured.append((a,p,planned))
    g._siege_bot(r)
finally:g._siege_bot_fire=original
assert captured and 0<=captured[0][0]<360
plan=captured[0][2]
assert not (any(plan.get(k) for k in ('wooddrop','stonedrop')) and any(plan.get(k) for k in ('pierce','through','big','splitshot','repeat')))
print('Core penetration, varied zombie roster/rewards and bot payload separation PASS')

# All rigid body types can receive immediate upward and directional knockback.
for kind in ('wood','stone','core','cannon','zombie','tnt','tnt_wait'):
    b=dict(id=901,kind=kind,x=400,y=350,w=36,h=44,hp=100,max=100,vx=0.,vy=0.,fixed=True)
    g._siege_v24_push(b,400,80,1)
    assert b['vx']>150 and b['vy']<0 and not b.get('fixed') and b['pushTime']>0,(kind,b)
# Coop guidance is time-gated, not tied to a world X coordinate.
r=v24('zombie');g._siege_field(r);core=g._siege_core_body(r['bodies'],0)
z=dict(id=999,kind='zombie',zombieType='walker',x=90,y=250,w=32,h=42,hp=100,max=100,vx=0.,vy=0.,side=2)
bs=[core,z]
assert g._siege_v24_guidance(100.,-200.,170.,250.,1/60,0,bs,.19)==(100.,-200.)
vx,vy=g._siege_v24_guidance(100.,-200.,170.,250.,1/60,0,bs,.2)
assert vx!=100. and vy!=-200.
assert g._siege_v24_guidance(100.,-200.,170.,250.,1/60,0,[core],.5)==(100.,-200.)
# A real blackhole shot releases a previously fixed zombie and damages it over time.
r=v24('zombie');g._siege_field(r);core=g._siege_core_body(r['bodies'],0);gun=g._siege_cannon(r,0)
z=dict(id=999,kind='zombie',zombieType='walker',x=gun['x'],y=240,w=32,h=42,hp=1000,max=1000,vx=0.,vy=0.,side=2,fixed=True)
r['bodies']=[core,gun,z];r['buffs'][0]['blackhole']=1
g._siege_fire(r,90,55,{'blackhole':1},config=g._siege_public_config({}))
e=r['event'];assert len([v for v in e['behaviorEvents'] if v[0]=='blackholeHit'])>=2
assert e['visualEnd']>=e['holes'][0][2]+1.9 and z['hp']<940,(z,e['visualEnd'],e['holes'])
# A high core cannot be protected indefinitely by a fragile load-bearing block.
r=v24('zombie');g._siege_field(r);core=g._siege_core_body(r['bodies'],0);core.update(x=480,y=346.)
wood=dict(id=997,kind='wood',side=0,x=480,y=394,w=36,h=44,hp=1,max=42,vx=0.,vy=0.)
z=dict(id=998,kind='zombie',zombieType='walker',side=2,x=420,y=395,w=32,h=42,hp=100,max=100,vx=0.,vy=0.,fixed=True)
r['bodies']=[core,wood,z];r['zombie']['spawned']=1;r['turn']=1
assert wood in g._siege_zombie_supports(r,core)
g._siege_fire(r,90,25,{},config=g._siege_public_config({}))
assert wood['hp']==0 and core['y']>356,(wood,core,r['event']['behaviorEvents'])
print('Entity knockback, time-gated zombie guidance, blackhole DOT and elevated support collapse PASS')

# Continuous terrain clearance: no walker or flyer should become buried in ridges.
for kind in ('walker','flyer'):
    r=v24('zombie');r['zombieMap']='ridge';g._siege_field(r)
    core=g._siege_core_body(r['bodies'],0)
    w,h,hp,_,_=g._SIEGE_ZOMBIE_TYPES[kind];x=810
    z=dict(id=998,kind='zombie',zombieType=kind,side=2,x=x,y=(g._siege_floor_body(r,x,w)-h/2 if kind=='walker' else 185.),w=w,h=h,hp=hp,max=hp,vx=0.,vy=0.,fixed=True)
    r['bodies']=[core,z];r['zombie']['spawned']=1
    def snap_terrain(now,p):return [now,p,[[b['id'],b['x'],b['y'],b['hp']] for b in r['bodies']],[],6,[]]
    for phase in range(3):
        frames=[];g._siege_zombie_round(r,0,frames,snap_terrain,[])
        for frame in frames:
            zz=next((b for b in frame[2] if b[0]==998),None)
            if zz and zz[3]>0:
                assert zz[2]+h/2 <=g._siege_floor_body(r,zz[1],w)+1.5,(kind,phase,zz)
    assert z['x']<x-120,(kind,z)
# Zombie pressure may move the gun into a gap, but cannot translate a chain of stone blocks.
r=v24('zombie');g._siege_field(r);core=g._siege_core_body(r['bodies'],0);gun=g._siege_cannon(r,0)
core.update(x=100,y=390);gun.update(x=420,y=392,vx=0.,vy=0.)
stones=[dict(id=900+i,kind='stone',side=0,x=375-i*40,y=394,w=36,h=44,hp=75,max=75,vx=0.,vy=0.) for i in range(3)]
z=dict(id=998,kind='zombie',zombieType='walker',side=2,x=458,y=395,w=32,h=42,hp=44,max=44,vx=0.,vy=0.,fixed=True)
r['bodies']=[core,gun,*stones,z];r['zombie']['spawned']=1
start_stones=[b['x'] for b in stones]
g._siege_zombie_round(r,0,[],lambda t,p:[t,p,[],[],6,[]],[])
assert [b['x'] for b in stones]==start_stones
assert gun['x']>=stones[0]['x']+(gun['w']+stones[0]['w'])/2+1.
# Siege vehicle difficulty changes fire cadence, range, target and armor penetration.
plans=[]
for difficulty in ('easy','medium','hard','hell'):
    r=v24('zombie');r['zombieDifficulty']=difficulty;g._siege_field(r)
    core=g._siege_core_body(r['bodies'],0);core.update(x=520,y=390)
    vehicle=dict(id=998,kind='zombie',zombieType='siegecar',side=2,x=360,y=394,w=62,h=44,hp=135,max=135,vx=0.,vy=0.,fixed=True)
    wall=dict(id=997,kind='stone',side=0,x=440,y=394,w=36,h=44,hp=300,max=300,vx=0.,vy=0.)
    r['bodies']=[core,vehicle,wall];r['zombie']['round']=2
    plans.append(g._siege_siegecar_plan(r,vehicle,core))
assert plans[0] is not None and all(plans)
assert plans[-1]['damage']>plans[0]['damage']
r['zombie']['round']=3
# The vehicle emits a distinct shot event, and damage arrives later in the turn.
r['zombie']['round']=1
events=[];frames=[]
g._siege_zombie_round(r,0,frames,lambda t,p:[t,p,[[b['id'],b['x'],b['y'],b['hp']] for b in r['bodies']],[],6,[]],events)
shot=next(e for e in events if e[0]=='siegeCarShot')
impact=next(e for e in events if e[0]=='siegeCarImpact')
assert impact[1]>shot[1] and wall['hp']<300
# v24 contact split fires at the first physical body (not the terrain or muzzle).
r=v24();r['bodies']=[b for b in r['bodies'] if b['kind']=='core']
r['launchers']=[[235,368],[725,368]]
target=dict(id=997,side=1,kind='stone',x=235,y=235,w=60,h=30,hp=1000,max=1000,vx=0.,vy=0.,fixed=True)
r['bodies'].append(target);r['buffs'][0]['splitshot']=1
g._siege_fire(r,90,55,{'splitshot':1},config=g._siege_public_config({'triggers':{'splitshot':'contact'}}))
splits=[e for e in r['event']['behaviorEvents'] if e[0]=='split']
assert splits and splits[0][-1]=='contact' and splits[0][1]>.01,splits
# Demolition breaches zombies and strips the guard's damage-transfer ability.
r=v24('zombie');g._siege_field(r)
core=g._siege_core_body(r['bodies'],0);gun=g._siege_cannon(r,0)
guard=dict(id=998,kind='zombie',zombieType='guard',side=2,x=gun['x'],y=240,w=44,h=54,hp=500,max=500,vx=0.,vy=0.,fixed=True)
r['bodies']=[core,gun,guard];r['buffs'][0]['demolish']=1
g._siege_fire(r,90,55,{'demolish':1},config=g._siege_public_config({}))
assert guard['hp']<500 and guard.get('sunderRounds',0)>0
assert any(e[0]=='sunder' for e in r['event']['behaviorEvents'])
print('Sloped enemy clearance, non-propagating cannon push, siegecar, contact split and demolition anti-armor PASS')

# Zombies must ignore movable cannon bodies during pathing and contact.
# A cannon still obeys gravity, explosions and solid stone-block collisions.
r=v24('zombie');g._siege_field(r)
core=g._siege_core_body(r['bodies'],0);gun=g._siege_cannon(r,0)
core.update(x=110.,y=g._siege_floor_body(r,110,core['w'])-core['h']/2)
gun.update(x=420.,y=g._siege_floor_body(r,420,gun['w'])-gun['h']/2,vx=0.,vy=0.)
z=dict(id=998,kind='zombie',zombieType='walker',side=2,
       x=505.,y=g._siege_floor_body(r,505,32)-21.,w=32,h=42,hp=44,max=44,
       vx=0.,vy=0.,fixed=True)
r['bodies']=[core,gun,z];r['zombie']['spawned']=1
before=gun['x']
snapshot=lambda t,p:[t,p,[],[],6,[]]
for _ in range(2):g._siege_zombie_round(r,1.,[],snapshot,[])
assert z['x']<before-(z['w']+gun['w'])/2,(z,gun)
assert gun['x']==before and gun['hp']==75 and not gun.get('fixed'),gun
g._siege_v24_push(gun,400,-80,1)
assert gun['vx']>0 and gun['vy']<0 and not gun.get('fixed'),gun
print('Zombie walks through cannon; cannon stays dynamic and can be knocked back PASS')

# Zombie action plays at normal speed, but cannot add a two-second waiting tail.
r=v24('zombie');g._siege_field(r)
r['zombie']['spawned']=sum(b['kind']=='zombie' and b['hp']>0 for b in r['bodies'])
r['turn']=1
g._siege_fire(r,90,25,{},config=g._siege_public_config({}))
ev=r['event']
phase=ev.get('zombiePhase')
assert phase is not None,(r['zombie'],ev.get('behaviorEvents'))
assert ev['duration']-phase<=1.501,(ev['duration'],phase)
assert ev['playbackDuration']-ev['duration']<=.181,(ev['playbackDuration'],ev['duration'])
print('Zombie phase: one second of action plus <=0.5s physical tail and <=0.18s hold PASS')

# Dense waves may overlap but must not permanently block each other's progress.
r=v24('zombie');g._siege_field(r);core=g._siege_core_body(r['bodies'],0)
core.update(x=110.,y=g._siege_floor_body(r,110,core['w'])-core['h']/2)
dense=[]
for j,kind in enumerate(('walker','walker','flyer')):
    w,h,hp,_,_=g._SIEGE_ZOMBIE_TYPES[kind];x=780.
    dense.append(dict(id=940+j,kind='zombie',zombieType=kind,side=2,x=x,
                      y=g._siege_floor_body(r,x,w)-h/2 if kind!='flyer' else 180.,
                      w=w,h=h,hp=hp,max=hp,vx=0.,vy=0.,fixed=True))
r['bodies']=[core,*dense];r['zombie']['spawned']=len(dense)
g._siege_zombie_round(r,1.,[],lambda now,p:[now,p,[],[],6,[]],[])
assert all(z['x']<755 for z in dense),dense

# A zombie must not stall to fight a block already behind its direction of travel.
r=v24('zombie');g._siege_field(r);core=g._siege_core_body(r['bodies'],0)
core.update(x=110.,y=g._siege_floor_body(r,110,core['w'])-core['h']/2)
w,h,hp,_,_=g._SIEGE_ZOMBIE_TYPES['walker'];x=760.
z=dict(id=991,kind='zombie',zombieType='walker',side=2,x=x,
       y=g._siege_floor_body(r,x,w)-h/2,w=w,h=h,hp=hp,max=hp,vx=0.,vy=0.,fixed=True)
b=dict(id=992,kind='stone',side=0,x=x+30,y=z['y'],w=36,h=44,hp=500,max=500,vx=0.,vy=0.)
r['bodies']=[core,z,b];r['zombie']['spawned']=1
g._siege_zombie_round(r,1.,[],lambda now,p:[now,p,[],[],6,[]],[])
assert z['x']<x-30 and b['hp']==500,(z,b)

# A knocked-back zombie resting on a roof must regain walking AI even though
# the terrain is lower. A flyer can regain powered flight while airborne.
for kind in ('walker','flyer'):
    r=v24('zombie');g._siege_field(r);core=g._siege_core_body(r['bodies'],0)
    core.update(x=110.,y=g._siege_floor_body(r,110,core['w'])-core['h']/2)
    w,h,hp,_,_=g._SIEGE_ZOMBIE_TYPES[kind];x=760.
    roof=dict(id=993,kind='stone',side=0,x=x,y=300.,w=90,h=50,hp=1000,max=1000,vx=0.,vy=0.)
    y=roof['y']-roof['h']/2-h/2 if kind=='walker' else 200.
    z=dict(id=994,kind='zombie',zombieType=kind,side=2,x=x,y=y,
           w=w,h=h,hp=hp,max=hp,vx=0.,vy=0.,fixed=False)
    r['bodies']=[core,roof,z];r['zombie']['spawned']=1
    g._siege_zombie_round(r,1.,[],lambda now,p:[now,p,[],[],6,[]],[])
    assert z.get('fixed') and z['x']<x-25,(kind,z)
print('Dense zombie crowd, obstacle behind and airborne/roof AI recovery PASS')

# Siegecar shells must collide with terrain before any body behind a ridge.
# Check both approach directions and the actual server impact/damage events.
for left in (False,True):
    r=v24('zombie');r['zombieDifficulty']='hell';g._siege_field(r)
    if left:
        r['terrain']=[(0,416),(225,416),(300,245),(340,245),(420,416),(960,416)]
        xcar,xcore=110.,570.
    else:
        r['terrain']=[(0,416),(450,416),(525,245),(565,245),(640,416),(960,416)]
        xcar,xcore=850.,390.
    core=g._siege_core_body(r['bodies'],0)
    core.update(x=xcore,y=390.,hp=100.,max=100.)
    car=dict(id=998,kind='zombie',zombieType='siegecar',side=2,x=xcar,y=394.,
             w=62,h=44,hp=135,max=135,vx=0.,vy=0.,fixed=True)
    wall=dict(id=997,kind='stone',side=0,x=(xcar+xcore)/2+(-85 if left else 85),
              y=390.,w=36,h=44,hp=300,max=300,vx=0.,vy=0.)
    r['bodies']=[core,car,wall];r['zombie']['round']=2;r['zombie']['spawned']=1
    plan=g._siege_siegecar_plan(r,car,core)
    assert plan and plan['ground'] and plan['target'] is None and not plan['penetration'],(left,plan)
    ax,ay=plan['origin'];bx,by=plan['point']
    assert abs(by+5-g._siege_floor(r,bx))<.02,(left,plan)
    # Projectile centre must remain outside the ground for its whole flight.
    for j in range(100):
        q=j/100.;xx=ax+(bx-ax)*q;yy=ay+(by-ay)*q
        assert yy+5<=g._siege_floor(r,xx)+.02,(left,j,xx,yy)
    events=[];frames=[]
    g._siege_zombie_round(r,0,frames,lambda t,p:[t,p,[],[],6,[]],events)
    shots=[e for e in events if e[0]=='siegeCarShot']
    impacts=[e for e in events if e[0]=='siegeCarImpact']
    assert shots and impacts and shots[0][7]==-1 and impacts[0][4]==-1,(left,events)
    assert impacts[0][1]>shots[0][1] and core['hp']==100 and wall['hp']==300,(left,core,wall)
    assert abs(impacts[0][2]-shots[0][4])<.01 and abs(impacts[0][3]-shots[0][5])<.01
# Flat unobstructed ground must not incorrectly absorb or disable valid fire.
r=v24('zombie');r['zombieDifficulty']='hell';g._siege_field(r)
core=g._siege_core_body(r['bodies'],0);core.update(x=400.,y=390.,hp=100.)
car=dict(id=998,kind='zombie',zombieType='siegecar',side=2,x=850.,y=394.,
         w=62,h=44,hp=135,max=135,vx=0.,vy=0.,fixed=True)
r['bodies']=[core,car];r['zombie']['round']=2;r['zombie']['spawned']=1
plan=g._siege_siegecar_plan(r,car,core)
assert plan and plan['target'] is core and not plan['ground'],plan
events=[]
g._siege_zombie_round(r,0,[],lambda t,p:[t,p,[],[],6,[]],events)
assert core['hp']<100 and next(e for e in events if e[0]=='siegeCarImpact')[4]==core['id']
print('Siegecar projectile terrain/solid first hit, visual impact and damage consistency PASS')
