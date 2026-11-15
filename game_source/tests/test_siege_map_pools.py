"""Random pools preserve exact maps, use every assigned map, and persist room settings."""
import importlib.util, pathlib, os, tempfile, random, threading, json, urllib.request
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',pathlib.Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
expected={'pool_small':{'close','floating','fragments'},'pool_medium':{'standard','peaks','obstacle','movingwall'},'pool_large':{'far','overtop','sky','floatingcenter'}}
assert set.union(*expected.values())==set(g._SIEGE_FIELDS)|set(g._SIEGE_NEW_FIELDS)
assert sum(map(len,expected.values()))==11
random.seed(2121)
for mode,members in expected.items():
 r=g._siege_new('A','a',True,0,mode);seen=set()
 for _ in range(80):
  assert r['mode']==mode and r['field'] in members and r['shots']==[0,0]
  seen.add(r['field']);g._siege_rematch(r)
 assert seen==members,(mode,seen)
 for f in members:
  r=g._siege_new('A','a',True,0,f);g._siege_rematch(r);assert r['field']==f
# Real room host API, starting the game and remembered settings.
s=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=s.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{s.server_address[1]}'
def api(path,data=None):
 req=urllib.request.Request(url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=15) as res:return json.loads(res.read())
try:
 r=api('/api/rooms',{'name':'A','guestPref':'c'*48});base='/r/'+r['code']+'/api/';t=r['token']
 def act(kind,**kw):return api(base+'action',dict(token=t,type=kind,requestId=g.secrets.token_hex(12),**kw))
 assert act('set_mode',mode='siege')['ok']
 assert act('siege_settings',itemCount=13,mode='pool_large',wind='off')['ok']
 assert act('solo_start')['ok']
 d=api(base+'siege',dict(token=t,type='state'));assert d['field'] in expected['pool_large'] and d['mode']=='pool_large'
 fresh=api('/api/rooms',{'name':'A','guestPref':'c'*48});v=api('/r/'+fresh['code']+'/api/state?token='+fresh['token'])['state']['settings'];assert v['siegeMode']=='pool_large'
 assert all('value="'+m+'"' in g.HTML_PAGE for m in expected)
finally:s.shutdown();s.server_close()
print('Map pools: complete membership, exact-map compatibility, rematches, actual room start and persistence PASS')
