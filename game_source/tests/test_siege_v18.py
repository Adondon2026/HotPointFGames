import importlib.util, pathlib, time, json, tempfile, os, threading, urllib.request, urllib.error
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',pathlib.Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def simple():
    r=g._siege_new('A','a',True,0,'classic','off',0,'stock');r['bot']=False;r['players'][1]['key']='b';r.update(combatMode='sync',reloadSeconds=10);return r
def plan(r,rt,i,a=42,p=65,sel=None,lock=True):g._siege_sync_plan(r,rt,i,dict(round=rt['round'],angle=a,power=p,selection=sel or {}),lock)
r=simple();now=time.time();rt=g._siege_sync_runtime(r,now);plan(r,rt,0);assert not g._siege_sync_tick(r,rt,now+1) and r['shots']==[0,0]
rt['locked'][0]=False;plan(r,rt,0,50,72,lock=False);plan(r,rt,1,45,70);assert not g._siege_sync_tick(r,rt,now+2)
a=g._siege_sync_public(r,rt,'a');b=g._siege_sync_public(r,rt,'b');assert a['myPlan'][0]==50 and b['myPlan'][0]==45 and 'plans' not in a and a['ready']==[False,True]
assert g._siege_sync_tick(r,rt,now+10.1) and r['shots']==[1,1]
e=rt['replay'];assert e['frames'][0][0]==0 and len(e['frames'][0][2])==2 and e['frames'][0][2][0]['angle']==50
assert not g._siege_sync_tick(r,rt,rt['until']-.1);assert rt['round']==1
assert not g._siege_sync_tick(r,rt,rt['until']+.1) and rt['round']==2 and rt['locked']==[False,False]
# Both defenses armed before either launches; no extra consumption.
r=simple();r['buffs'][0]['shield']=2;r['buffs'][1]['shield']=2;rt=g._siege_sync_runtime(r,now);plan(r,rt,0,sel={'shield':2});plan(r,rt,1,sel={'shield':2});assert g._siege_sync_tick(r,rt,now);assert r['buffs'][0]['shield']==r['buffs'][1]['shield']==0 and r['armed']==[{},{}]
# HTTP readiness and private drafts; direct arbitrary fire rejected.
s=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=s.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{s.server_address[1]}'
def api(path,data=None):
    req=urllib.request.Request(url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    try:res=urllib.request.urlopen(req,timeout=10)
    except urllib.error.HTTPError as e:res=e
    with res:return json.loads(res.read())
try:
    room=api('/api/rooms',{'name':'A','guestPref':'a'*48});base='/r/'+room['code']+'/api/';t=room['token'];u=api(base+'join',{'name':'B','seatKey':g.secrets.token_hex(12)})['token']
    def act(kind,**kw):return api(base+'action',dict(token=t,type=kind,requestId=g.secrets.token_hex(12),**kw))
    def q(token,kind,**kw):return api(base+'siege',dict(token=token,type=kind,**kw))
    assert act('set_mode',mode='siege')['ok'];assert act('siege_settings',itemCount=0,mode='classic',wind='off',ammo=0,buffMode='stock',combatMode='sync',reloadSeconds=15)['ok'];assert act('start')['ok']
    a=q(t,'state');assert a['combatMode']=='sync' and a['remaining']>10 and a['round']==1
    assert not q(t,'fire',angle=42,power=65)['ok']
    a=q(t,'ready',round=1,angle=40,power=60,selection={});assert a['ready']==[True,False] and not a['busy']
    b=q(u,'state');assert b['ready']==[True,False] and b['myPlan'] is None
    a=q(t,'unready',round=1);assert a['ready']==[False,False]
    a=q(t,'ready',round=1,angle=55,power=72,selection={});b=q(u,'ready',round=1,angle=50,power=70,selection={});assert b['busy'] and b['shots']==[1,1] and len(b['replay']['frames'][0][2])==2
    a=q(t,'state');assert a['replay']['id']==b['replay']['id'] and a['replay']['frames']==b['replay']['frames']
    assert 'replay' not in q(t,'state',last=a['replay']['id'])
    assert not q(t,'return')['ok']
    time.sleep(b['replay']['duration']+.5);a=q(t,'state');assert a['round']==2 and a['ready']==[False,False] and not a['busy']
    fresh=api('/api/rooms',{'name':'A','guestPref':'a'*48});settings=api('/r/'+fresh['code']+'/api/state?token='+fresh['token'])['state']['settings'];assert settings['siegeCombatMode']=='sync' and settings['siegeReload']==15
finally:s.shutdown();s.server_close()
print('v0.18: synchronized prepare/cancel, deadline draft, private plans, same-step shots, replay, defenses, preferences PASS')
