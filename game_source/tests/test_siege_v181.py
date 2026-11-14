"""Unlimited preparation and non-stackable teleport pickups."""
import importlib.util, os, pathlib, tempfile, time, random, threading, urllib.request, urllib.error, json
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',pathlib.Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

def new(bot=False):
    r=g._siege_new('A','a',True,0,'standard','off',0,'stock');r['bot']=bot;r['players'][1]['key']='b';r.update(combatMode='sync',reloadSeconds=0);return r

def plan(r,rt,i):g._siege_sync_plan(r,rt,i,dict(round=rt['round'],angle=42,power=65,selection={}),True)
now=time.time();r=new();rt=g._siege_sync_runtime(r,now)
assert rt['deadline'] is None and g._siege_sync_public(r,rt,'a')['remaining'] is None
plan(r,rt,0);assert not g._siege_sync_tick(r,rt,now+86400) and r['shots']==[0,0]
rt['locked'][0]=False;plan(r,rt,0);plan(r,rt,1);assert g._siege_sync_tick(r,rt,now+86400) and r['shots']==[1,1]
g._siege_sync_tick(r,rt,rt['until']+.1);assert rt['round']==2 and rt['deadline'] is None
r=new(True);rt=g._siege_sync_runtime(r,now);assert not g._siege_sync_tick(r,rt,now+600) and rt['locked']==[False,True];plan(r,rt,0);assert g._siege_sync_tick(r,rt,now+600)
# Even a forced five-charge draw produces single teleport/heal pickups, including respawns.
original=g._siege_amount;g._siege_amount=lambda:5
seen=set()
for seed in range(30):
    random.seed(seed);r=g._siege_new('A','a',True,25,'standard','off',0,'stock')
    for it in r['items']:
        if it['kind'] in g._SIEGE_SINGLE_ITEMS:assert it['amount']==1;seen.add(it['kind'])
assert set(g._SIEGE_SINGLE_ITEMS)<=seen
choice=g.random.choice
for k in g._SIEGE_SINGLE_ITEMS:
    r=new();r['respawns']=[dict(id=0,kind='big',x=300,y=200,r=15,slot=0,readyAt=0,amount=5)];g.random.choice=lambda seq,k=k:k;g._siege_refill(r);assert r['items'][0]['amount']==1
    if k=='heal':continue
    for mode in ('auto','stock'):
        r=new();r['buffMode']=mode;x,y=g._siege_muzzle(0,r,75);r['items']=[dict(id=i,kind=k,amount=5,x=x,y=y,r=20) for i in range(2)];g._siege_fire(r,75,35);assert r['buffs'][0][k]==1 and [p['gained'] for p in r['event']['pickups']]==[1,0]
        r['buffs'][0][k]=5;g._siege_normalize_buffs(r);assert r['buffs'][0][k]==1
        if mode=='stock':
            try:g._siege_selection(r,{k:2},0)
            except ValueError:pass
            else:raise AssertionError('stacked teleport accepted')
g.random.choice=choice;g._siege_amount=original
# HTTP settings, unlimited readiness, cancellation, persistence across new rooms.
s=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=s.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{s.server_address[1]}'
def api(path,data=None):
    req=urllib.request.Request(url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    try:res=urllib.request.urlopen(req,timeout=15)
    except urllib.error.HTTPError as e:res=e
    with res:return json.loads(res.read())
try:
    room=api('/api/rooms',{'name':'A','guestPref':'a'*48});base='/r/'+room['code']+'/api/';t=room['token'];u=api(base+'join',{'name':'B','seatKey':g.secrets.token_hex(12)})['token']
    def act(kind,**kw):return api(base+'action',dict(token=t,type=kind,requestId=g.secrets.token_hex(12),**kw))
    def q(token,kind,**kw):return api(base+'siege',dict(token=token,type=kind,**kw))
    assert act('set_mode',mode='siege')['ok'];assert act('siege_settings',itemCount=0,mode='classic',wind='off',ammo=0,buffMode='stock',combatMode='sync',reloadSeconds=0)['ok'];assert act('start')['ok']
    assert q(t,'state')['remaining'] is None
    assert q(t,'ready',round=1,angle=42,power=65,selection={})['ready']==[True,False]
    assert q(t,'unready',round=1)['ready']==[False,False]
    assert q(t,'ready',round=1,angle=42,power=65,selection={})['ready']==[True,False]
    assert q(u,'ready',round=1,angle=42,power=65,selection={})['shots']==[1,1]
    fresh=api('/api/rooms',{'name':'A','guestPref':'a'*48});settings=api('/r/'+fresh['code']+'/api/state?token='+fresh['token'])['state']['settings'];assert settings['siegeReload']==0 and settings['siegeCombatMode']=='sync'
finally:s.shutdown();s.server_close()
print('v0.18.1: unlimited sync, bot waits, single teleport spawn/refill/pickup, settings persistence PASS')
