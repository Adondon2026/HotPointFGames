"""Room-authenticated real-time naval duel, projectile pickups and match boundaries."""
import importlib.util,os,tempfile,threading,urllib.request,urllib.error,json,math
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='ship_duel_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
assert 'SHIP_BATTLE_SCRIPT' not in g.SHIP_BATTLE_PAGE
assert 'id="dial"' in g.SHIP_BATTLE_PAGE
server=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_address[1]}'
def api(path,data=None):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
 try:res=urllib.request.urlopen(req,timeout=6)
 except urllib.error.HTTPError as ex:res=ex
 with res:
  raw=res.read()
  if res.headers.get('Content-Type','').startswith('text/html'):return raw.decode()
  return json.loads(raw)
def room_action(r,t,kind,**kw):
 return api('/r/'+r['code']+'/api/action',dict(token=t,type=kind,requestId=g.secrets.token_hex(12),**kw))
def battle(r,t,kind='state',**kw):
 return api('/r/'+r['code']+'/api/ship',dict(token=t,type=kind,**kw))
try:
 a=api('/api/rooms',{'name':'船长'});t=a['token'];prefix='/r/'+a['code']
 assert not room_action(a,t,'start')['ok']
 assert room_action(a,t,'set_mode',mode='ship')['ok']
 assert not room_action(a,t,'start')['ok']
 friend=api(prefix+'/api/join',{'name':'舵手','seatKey':g.secrets.token_hex(12)})['token']
 assert room_action(a,t,'start')['ok']
 assert api(prefix+'/ship').startswith('<!doctype html>')
 mine=battle(a,t);enemy=battle(a,friend)
 assert mine['ok'] and enemy['ok']
 assert mine['seat']==0 and enemy['seat']==1
 assert mine['bases']==enemy['bases']==[240.,240.]
 assert len(mine['buffs'])==5
 assert not battle(a,'invalid','state')['ok']
 assert not battle(a,friend,'return')['ok']
 assert battle(a,t,'control',rudder=1e100,aimx=-1e8,aimy=2e8,fire=True)['ok']
 rt=g.ROOMS[a['code']]['runtime']['shipBattle']
 assert abs(rt['ships'][0]['rudder'])<=.61 and 0<=rt['ships'][0]['aimx']<=g._SHIP_W
 # A shot that crosses a buff must mutate mid-flight, without entering an inventory screen.
 rt['ships'][0].update(x=550.,y=393.,a=0.,aimx=1364.,aimy=393.,fire=True,shotAt=0.)
 rt['shots']=[]
 g._ship_shot(rt,0,0.)
 for _ in range(22):g._ship_step(rt,.025)
 assert not rt['buffs'][1]['until']<rt['t'],rt['buffs']
 assert any(p['kind']=='split' for p in rt['shots']),rt['shots']
 assert len(rt['shots'])>=2
 # Ship physics and base damage are server owned, not accepted from client payloads.
 original_hp=rt['bases'][1]
 g._ship_hit(rt,0,g._SHIP_W-76,375,30.)
 assert rt['bases'][1]==original_hp-30
 battle(a,t,'control',x=1400,y=100,hp=999999,baseHp=999999)
 assert rt['bases'][1]==original_hp-30
 # End state and rematch restricted to the host.
 g._ship_hit(rt,0,g._SHIP_W-76,375,1000.)
 assert battle(a,t)['winner']==0
 assert not battle(a,friend,'rematch')['ok']
 assert battle(a,t,'rematch')['winner'] is None
 assert not battle(a,friend,'return')['ok']
 assert battle(a,t,'return')['returned']
 assert api(prefix+'/api/state?token='+friend)['state']['phase']=='lobby'
 # Solo room starts with a rules bot, not two local controls.
 b=api('/api/rooms',{'name':'独行'});u=b['token']
 assert room_action(b,u,'set_mode',mode='ship')['ok']
 assert room_action(b,u,'solo_start')['ok']
 solo=battle(b,u);assert solo['ok'] and len(solo['ships'])==2
 assert any(p.get('isBot') for p in g.ROOMS[b['code']]['state']['players'])
 assert battle(b,u,'return')['returned']
 print('Real-time naval duel rules, authentication, solo bot and lifecycle passed')
finally:
 server.shutdown();server.server_close()
