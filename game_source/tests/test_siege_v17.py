"""Cross-map teleport, independent live clocks, shared physics and saved room settings."""
import importlib.util, json, os, tempfile, threading, time, urllib.request, urllib.error
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def simple():
    r=g._siege_new('A','a',True,0,'classic','off',0,'stock')
    r['players'][1]['key']='b';r['bot']=False
    r['bodies']=[b for b in r['bodies'] if b['kind']=='core']
    for b in r['bodies']:b.update(x=100 if b['side']==0 else 850,y=416-b['h']/2,hp=73 if b['side']==0 else 100,vx=0.,vy=0.)
    return r
# Wall collision: each piece relocates across the centre, falls onto first support, no fall damage.
for kind in ('gunteleport','coreteleport'):
    r=simple();r['bodies'].append(dict(id=90,side=-1,kind='stone',x=650,y=326,w=60,h=180,hp=1000,max=1000,vx=0.,vy=0.,fixed=True))
    r['buffs'][0][kind]=1;g._siege_fire(r,20,75,{kind:1});e=r['event'];tr=e['teleports'][0]
    assert e['hitId']==90,(e['impact'],e['hitId'])
    assert tr[4]>480 and tr[7]<tr[5] and tr[8]>tr[6],tr
    assert abs(tr[4]-e['impact'][0])<=5,(tr,e['impact'])
    assert g._siege_core(r['bodies'],0)==73
    assert r['buffs'][0][kind]==0
    if kind=='coreteleport':
        c=next(b for b in r['bodies'] if b['side']==0 and b['kind']=='core')
        assert c['y']+c['h']/2==236 and not c.get('fixed'),c
    else:assert abs(g._siege_launcher(0,r)[1]+48-236)<.01,tr
# An out-of-map aerial shot relocates safely at the boundary instead of refunding.
r=simple();r['buffs'][0]['coreteleport']=1;g._siege_fire(r,45,100,{'coreteleport':1});tr=r['event']['teleports'][0]
assert tr[4]>880 and tr[8]>tr[6] and g._siege_core(r['bodies'],0)==73,tr
# Two shots active concurrently, one may finish and fire again before the other is done.
r=simple();r.update(combatMode='live',reloadSeconds=0);now=time.time();rt=g._siege_live_runtime(r,now)
g._siege_live_start(r,rt,0,15,15,{},now);g._siege_live_start(r,rt,1,85,100,{},now)
assert r['shots']==[1,1] and len(rt['active'])==2 and g._siege_core(r['bodies'],0)==73
assert not g._siege_live_can_fire(r,rt,0,now) and not g._siege_live_can_fire(r,rt,1,now)
try:g._siege_live_start(r,rt,0,15,15,{},now)
except ValueError:pass
else:raise AssertionError('second shot from same player accepted')
# Both projectile positions advance independently in the same clock.
old=[rt['active'][i]['sample']['p'] for i in (0,1)];now+=.1;g._siege_live_tick(r,rt,now)
assert all(rt['active'][i]['sample']['p']!=old[i] for i in (0,1))
for _ in range(200):
    now+=.05;g._siege_live_tick(r,rt,now)
    if 0 not in rt['active']:break
assert 1 in rt['active'] and g._siege_live_can_fire(r,rt,0,now),rt['active'].keys()
g._siege_live_start(r,rt,0,15,15,{},now);assert r['shots']==[2,1] and len(rt['active'])==2
# First shell destroys an actual wall before the second shell reaches it.
r=simple();r.update(combatMode='live',reloadSeconds=0);r['bodies'].append(dict(id=90,side=-1,kind='stone',x=480,y=350,w=60,h=110,hp=1,max=1,vx=0.,vy=0.,fixed=True));now=time.time();rt=g._siege_live_runtime(r,now)
g._siege_live_start(r,rt,0,5,80,{},now);g._siege_live_start(r,rt,1,20,55,{},now)
for _ in range(40):
    now+=.05;g._siege_live_tick(r,rt,now)
    b=rt['active'].get(1,{}).get('sample',{});pt=b.get('p')
    if pt and pt[0]<440:break
else:raise AssertionError('second shot did not cross destroyed wall')
assert next(b for b in r['bodies'] if b['id']==90)['hp']==0
# Finite ammunition and lethal hit: the other airborne shell is allowed to finish before result.
r=simple();r.update(combatMode='live',reloadSeconds=0,ammo=1);target=next(b for b in r['bodies'] if b['side']==1);target.update(x=400,y=350,w=60,h=100,hp=5,fixed=True);now=time.time();rt=g._siege_live_runtime(r,now)
g._siege_live_start(r,rt,0,5,40,{},now);g._siege_live_start(r,rt,1,85,100,{},now)
for _ in range(80):
    now+=.05;g._siege_live_tick(r,rt,now)
    if target['hp']==0:break
assert target['hp']==0 and r['phase']=='play' and rt['active'] and not g._siege_live_can_fire(r,rt,0,now)
for _ in range(400):
    now+=.05;g._siege_live_tick(r,rt,now)
    if not rt['active']:break
assert r['phase']=='over' and r['winner']==0
# A 5-second reload starts only after the owner's last shot resolves; no waiting for opponent.
r=simple();r.update(combatMode='live',reloadSeconds=5);now=time.time();rt=g._siege_live_runtime(r,now)
g._siege_live_start(r,rt,0,15,15,{},now)
for _ in range(300):
    now+=.05;g._siege_live_tick(r,rt,now)
    if not rt['active']:break
assert not rt['active'] and not g._siege_live_can_fire(r,rt,0,now)
assert rt['ready'][0]>=now+4.99 and g._siege_live_can_fire(r,rt,1,now)
assert g._siege_live_can_fire(r,rt,0,now+5.01)
# Real HTTP APIs: preferences persist across rooms and identities; realtime mode is shared, not turn-locked.
s=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=s.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{s.server_address[1]}'
def api(path,data=None):
    req=urllib.request.Request(url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    try:res=urllib.request.urlopen(req,timeout=5)
    except urllib.error.HTTPError as e:res=e
    with res:return json.loads(res.read())
def create(name,**kw):return api('/api/rooms',{'name':name,**kw})
def route(r,endpoint):return '/r/'+r['code']+'/api/'+endpoint
def act(r,token,kind,**kw):return api(route(r,'action'),dict(token=token,type=kind,requestId=g.secrets.token_hex(12),**kw))
def state(r):return api(route(r,'state')+'?token='+r['token'])['state']
def siege(r,token,kind,**kw):return api(route(r,'siege'),dict(token=token,type=kind,**kw))
try:
    guest='a'*48;r=create('A',guestPref=guest);t=r['token']
    assert act(r,t,'set_mode',mode='siege')['ok']
    assert act(r,t,'siege_settings',itemCount=19,mode='floating',wind='high',ammo=10,buffMode='stock',combatMode='live',reloadSeconds=3)['ok']
    assert act(r,t,'set_mode',mode='dice')['ok']
    assert act(r,t,'settings',diceStart=6,cardLives=5,drawRounds=3)['ok']
    rr=create('A new',guestPref=guest);ss=state(rr)['settings'];assert ss['siegeCombatMode']=='sync' and ss['siegeReload']==15 and ss['siegeMode']=='floating' and ss['diceStart']==6 and ss['cardLives']==5 and ss['drawRounds']==3,ss
    assert state(create('other',guestPref='b'*48))['settings']['siegeCombatMode']=='turn'
    account=api('/api/account',{'type':'register','name':'Tester','pin':'1234'})['accountToken'];ar=create('Tester',accountToken=account,guestPref='c'*48);at=ar['token']
    assert act(ar,at,'set_mode',mode='siege')['ok'];assert act(ar,at,'siege_settings',itemCount=2,mode='sky',wind='off',combatMode='live',reloadSeconds=0)['ok']
    ar2=create('Tester',accountToken=account,guestPref='d'*48);assert state(ar2)['settings']['siegeMode']=='sky' and state(ar2)['settings']['siegeReload']==15
    # Legacy live-mode settings are migrated to the new synchronization mode.
    r=rr;t=r['token'];u=api(route(r,'join'),{'name':'B','seatKey':g.secrets.token_hex(12)})['token'];assert act(r,t,'set_mode',mode='siege')['ok']
    assert act(r,t,'siege_settings',itemCount=0,mode='classic',wind='off',ammo=0,buffMode='auto',combatMode='live',reloadSeconds=0)['ok'];assert act(r,t,'start')['ok']
    first=siege(r,t,'state');assert first['combatMode']=='sync' and first['canFire']
    assert not siege(r,t,'fire',angle=40,power=65)['ok']
    # Shared runtime is excluded from persisted state, account preferences remain durable.
    g.flush_state();saved=json.loads(g.ROOMS_FILE.read_text());assert 'runtime' not in saved[r['code']]
    with g._db() as db:assert db.execute('SELECT count(*) FROM room_preferences').fetchone()[0]>=2
finally:s.shutdown();s.server_close()
print('v0.17: cross-map wall/air teleport, no fall damage, concurrent shared shots, independent reload, guest/account preferences PASS')
