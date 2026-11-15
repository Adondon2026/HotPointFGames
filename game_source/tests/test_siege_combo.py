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
    assert len({v['color'] for v in catalog.values()})==6
    assert all(catalog[k]['color']=='#b4b7bc' for k in g._SIEGE_NEGATIVE)
assert "siegeBuffList.length" in g.HTML_PAGE
assert "n+'/16'" not in g.HTML_PAGE
assert 'return {unlock,enterBattle:' in g.SIEGE_PAGE
assert 'Object.entries(siegeCatalog).map' in g.SIEGE_PAGE
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
assert set(v['buffs'][0])==set(g._SIEGE_ITEMS) and all(v['buffs'][0].values())
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
    status,raw=http('/api/siege-trial',data)
    return status,json.loads(raw)
try:
    status,page=http('/siege?trial=1')
    assert status==200 and b'/api/siege-trial' in page
    assert http('/siege')[0]==404
    assert http('/api/siege',{'type':'create','key':'e'*48})[0]==404
    key='e'*48
    status,v=trial_api({'type':'create','key':key})
    assert status==200 and v['ok'] and v['trial'] and v['cores']==[100,100]
    code=v['code']
    def q(kind,**kw):return trial_api(dict(type=kind,key=key,code=code,**kw))[1]
    assert q('state')['trial']
    assert not trial_api(dict(type='state',key='f'*48,code=code))[1]['ok']
    assert not q('join')['ok']
    assert not q('return')['ok']
    p=q('trialPreview',angle=42,power=65,selection={'dive':1},config={'simple':True})
    assert p['ok'] and p['paths']
    v=q('fire',rev=v['rev'],angle=42,power=65,selection={'dive':1},config={'simple':True})
    assert v['ok'] and v['shots']==[1,0] and v['cores'][1]==100
    g._SIEGE_ROOMS[code]['until']=0
    v=q('trialReset',mode='sky')
    assert v['ok'] and v['field']=='sky' and v['shots']==[0,0]
    normal=g.siege_request(dict(type='create',key=key,bot=True))
    assert normal['ok'] and not normal['trial']
    assert not trial_api(dict(type='state',key=key,code=normal['code']))[1]['ok']
    assert http('/')[0]==200
finally:
    server.shutdown();server.server_close()
print('Siege trial HTTP route, isolation, preview, fire, reset PASS')
