"""Four independent clients, same/different games, cross-room auth and room lifecycle."""
import importlib.util,json,os,tempfile,threading,urllib.request,urllib.error
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp();root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
s=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=s.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{s.server_address[1]}'
def api(path,data=None):
    req=urllib.request.Request(url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    try:r=urllib.request.urlopen(req,timeout=5)
    except urllib.error.HTTPError as e:r=e
    with r:return json.loads(r.read())
def create(name):return api('/api/rooms',{'name':name})
def route(r,endpoint):return '/r/'+r['code']+'/api/'+endpoint
def join(r,n,claim=''):return api(route(r,'join'),{'name':n,'seatKey':g.secrets.token_hex(12),'claim':claim})
def act(r,t,kind,**kw):return api(route(r,'action'),dict(token=t,type=kind,requestId=g.secrets.token_hex(12),**kw))
def state(r,t):return api(route(r,'state')+'?token='+t)['state']
def siege(r,t,kind,**kw):return api(route(r,'siege'),dict(token=t,type=kind,**kw))
try:
 a,b=create('A'),create('C');x,z=a['token'],b['token'];y,w=join(a,'B')['token'],join(b,'D')['token']
 assert state(a,x)['isHost'] and not state(a,x)['modeSelected'];assert not act(a,x,'start')['ok'];assert not act(a,y,'set_mode',mode='dice')['ok']
 assert act(a,x,'set_mode',mode='dice')['ok'];assert act(b,z,'set_mode',mode='dice')['ok']
 assert len(api('/api/rooms')['rooms'])==2
 assert not act(b,x,'set_mode',mode='army')['ok']
 for r,t,u in [(a,x,y),(b,z,w)]:
  assert not act(r,u,'start')['ok'];assert act(r,t,'start')['ok']
 assert {p['name'] for p in state(a,x)['players']}=={'A','B'};assert {p['name'] for p in state(b,z)['players']}=={'C','D'}
 old=state(b,z);assert act(a,x,'dice_bid',quantity=2,face=3)['ok'];assert state(b,z)['version']==old['version']
 assert act(a,x,'reset')['ok'];assert act(a,x,'set_mode',mode='siege')['ok']
 assert state(a,x)['settings']['siegeItemCount']==13
 assert not act(a,y,'siege_settings',itemCount=25)['ok']
 for bad in (-1,26,True,3.5,'13'):assert not act(a,x,'siege_settings',itemCount=bad)['ok']
 assert state(a,x)['settings']['siegeAmmo']==0 and state(a,x)['settings']['siegeMode']=='random'
 assert not act(a,x,'siege_settings',itemCount=21,ammo=7)['ok']
 assert not act(a,x,'siege_settings',itemCount=21,wind='invalid')['ok']
 assert act(a,x,'siege_settings',itemCount=21,ammo=10,mode='classic',wind='off')['ok'];assert state(a,y)['settings']['siegeItemCount']==21;assert state(b,z)['settings']['siegeItemCount']==13
 assert act(a,x,'start')['ok'];assert len(siege(a,x,'state')['items'])==21
 assert not act(a,x,'siege_settings',itemCount=0)['ok']
 assert siege(a,x,'state')['ammo']==10 and siege(a,x,'state')['mode']=='classic' and siege(a,x,'state')['wind']==0
 assert state(b,z)['settings']['siegeAmmo']==0 and state(b,z)['settings']['siegeMode']=='random'
 assert state(a,x)['phase']=='siege_play';assert state(b,z)['mode']=='dice'
 assert not siege(a,z,'state')['ok'];assert siege(a,x,'state')['seat']==0;assert siege(a,y,'state')['seat']==1
 fire=siege(a,x,'fire',rev=0,last=0,angle=42,power=65);assert fire['ok'] and fire['shots']==[1,0] and fire['event']['hitId'] is not None
 assert siege(a,y,'state',last=0)['event']==fire['event'];assert not siege(a,y,'return')['ok']
 g.ROOMS[a['code']]['state']['siege']['until']=0
 r=g.ROOMS[a['code']]['state']['siege'];r['phase']='over';r['until']=0
 assert len(siege(a,x,'rematch')['items'])==21
 assert siege(a,x,'return')['ok'];assert state(a,y)['phase']=='lobby';assert act(a,x,'set_mode',mode='army')['ok']
 assert state(a,y)['mode']=='army';assert state(b,z)['mode']=='dice';assert not act(a,y,'dissolve')['ok']
 g.flush_state();saved=json.loads(g.ROOMS_FILE.read_text());assert set(saved)=={a['code'],b['code']};assert saved[b['code']]['state']['phase']!='lobby'
 assert act(a,x,'dissolve')['ok'];assert api(route(a,'state')+'?token='+y)['roomEnded'];assert state(b,z)['mode']=='dice'
 assert act(b,z,'reset')['ok'];assert act(b,z,'leave')['ok'];assert state(b,w)['isHost'];assert act(b,w,'leave')['ok'];assert not api('/api/rooms')['rooms']
 print('Multiroom: four users, same-game isolation, mixed games, siege shared room, permissions, persistence, dissolution PASS')
finally:s.shutdown();s.server_close()
