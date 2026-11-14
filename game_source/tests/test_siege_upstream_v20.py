"""Room-wide per-kind stack caps, allowlist, custom numbers and fort strength."""
import importlib.util, pathlib, time, json, tempfile, os, threading, urllib.request, urllib.error, random
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',pathlib.Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
random.seed(40412)
# Friend's whitelist regression, expanded to all maps, disabled and rare kinds.
ALL=set(g._SIEGE_ITEMS)
for allowed in ([],['big'],['splitshot','shock'],['gunteleport','heal'],['blackhole'],list(ALL)):
 for mode in g._SIEGE_MODES:
  r=g._siege_new('A','a',True,13,mode,'off',0,'stock',allowed)
  assert set(g._siege_allowed(r))==set(allowed)
  assert len(r['items'])==(13 if allowed else 0),(mode,allowed,len(r['items']))
  assert all(x['kind'] in allowed for x in r['items'])
  if allowed:
   r['items'].clear();r['respawns']=[dict(id=1,kind='shield',x=250,y=200,r=15,slot=1,readyAt=0)];g._siege_refill(r)
   assert len(r['items'])==1 and r['items'][0]['kind'] in allowed
  g._siege_rematch(r);assert all(x['kind'] in allowed for x in r['items'])
r=g._siege_new('A','a',True,0,'classic','off',0,'stock',None,{'bounce':20,'power':3,'through':10});r['buffs'][0].update(bounce=20,power=20,through=20)
assert g._siege_selection(r,{'bounce':20,'power':3,'through':10})=={'bounce':20,'power':3,'through':10}
for bad in [{'power':4},{'bounce':21},{'through':11}]:
 try:g._siege_selection(r,bad);raise AssertionError(bad)
 except ValueError:pass
# Vertical shot on empty ground has time for all twenty actual bounces.
r['bodies']=[b for b in r['bodies'] if b['kind']=='core'];g._siege_fire(r,90,15,{'bounce':20});assert len([x for x in r['event']['bounces'] if x[3]==-1])==20,r['event']['bounces'];assert r['buffs'][0]['bounce']==0
# Fort resistance applies to pieces, leaves core HP/starting health unchanged.
loss=[]
for fort in ('normal','sturdy','fortified'):
 r=g._siege_new('A','a',True,0,'classic','off',0,'stock',fort_strength=fort)
 r['bodies']=[dict(id=0,side=0,x=100,y=400,w=30,h=32,kind='core',hp=100,max=100,vx=0.,vy=0.,fixed=True),dict(id=1,side=1,x=850,y=400,w=30,h=32,kind='core',hp=100,max=100,vx=0.,vy=0.,fixed=True),dict(id=2,side=1,x=300,y=350,w=30,h=30,kind='stone',hp=75,max=75,vx=0.,vy=0.,fixed=True)]
 r['launchers']=[[235,368],[725,368]];g._siege_fire(r,15,25);loss.append(75-r['bodies'][2]['hp']);assert g._siege_core(r['bodies'],0)==100 and g._siege_core(r['bodies'],1)==100
assert loss[0]>loss[1]>loss[2]>0,loss
# HTTP authority, settings persistence, actual new round parameters.
s=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=s.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{s.server_address[1]}'
def api(path,data=None):
 req=urllib.request.Request(url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
 try:res=urllib.request.urlopen(req,timeout=15)
 except urllib.error.HTTPError as e:res=e
 with res:return json.loads(res.read())
try:
 r=api('/api/rooms',{'name':'A','guestPref':'b'*48});base='/r/'+r['code']+'/api/';t=r['token'];u=api(base+'join',{'name':'B','seatKey':g.secrets.token_hex(12)})['token']
 def act(kind,token=t,**kw):return api(base+'action',dict(token=token,type=kind,requestId=g.secrets.token_hex(12),**kw))
 assert act('set_mode',mode='siege')['ok'];cfg=dict(itemCount=13,mode='standard',wind='off',ammo=17,buffMode='stock',combatMode='sync',reloadSeconds=27,allowedBuffs=['bounce'],stackCaps={'bounce':20,'power':3},fortStrength='sturdy')
 assert not act('siege_settings',token=u,**cfg)['ok'];assert not act('siege_settings',**{**cfg,'stackCaps':{'power':20}})['ok'];assert act('siege_settings',**cfg)['ok'];assert act('start')['ok']
 d=api(base+'siege',dict(token=t,type='state'));assert d['ammo']==17 and 20<d['remaining']<=27 and d['stackCaps']['bounce']==20 and d['stackCaps']['power']==3 and d['fortStrength']=='sturdy' and all(x['kind']=='bounce' for x in d['items'])
 fresh=api('/api/rooms',{'name':'A','guestPref':'b'*48});v=api('/r/'+fresh['code']+'/api/state?token='+fresh['token'])['state']['settings'];assert v['siegeAmmo']==17 and v['siegeReload']==27 and v['siegeAllowedBuffs']==['bounce'] and v['siegeStackCaps']['bounce']==20 and v['siegeFortStrength']=='sturdy'
finally:s.shutdown();s.server_close()
print('v0.20: whitelist, per-item caps, 20 actual bounces, fort resistance, custom numeric settings, permissions and persistence PASS',loss)
