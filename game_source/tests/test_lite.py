"""Local accounts, match idempotency and full HTTP flow."""
import importlib.util, json, os, sys, tempfile, threading, urllib.request
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ['HOME']=tempfile.mkdtemp(prefix='hotpoint-test-')
os.environ['GAMEHALL_DATA_DIR']=os.environ['HOME']
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
g.STATE=g.fresh_state();g.TOKENS={};g.ACCOUNT_DB=Path(os.environ['HOME'])/'test.sqlite3'
server=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler)
threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_address[1])
def api(path,data=None):
    req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
    return json.loads(urllib.request.urlopen(req,timeout=4).read())
def acct(kind,name='',pin='',t=''):
    return api('/api/account',{'type':kind,'name':name,'pin':pin,'accountToken':t})
def join(a):
    return api('/api/join',{'accountToken':a['accountToken'],'name':'fake','seatKey':'client-test'})
def act(t,kind,**kw):
    return api('/api/action',dict(token=t,type=kind,requestId=g.secrets.token_hex(8),**kw))
try:
    a=acct('register','甲','1234');b=acct('register','乙','4321');assert a['ok'] and b['ok']
    assert not acct('login','甲','1235')['ok'];assert acct('login','甲','1234')['ok']
    aa=join(a);bb=join(b);assert aa['ok'] and bb['ok'];assert join(a)['playerId']==aa['playerId']
    assert not api('/api/join',{'name':'甲','token':aa['token']})['ok']
    t=aa['token'];u=bb['token'];assert act(t,'set_mode',mode='dice')['ok'];assert act(t,'toggle_ready')['ok'];assert act(u,'toggle_ready')['ok'];assert act(t,'start')['ok']
    with g.LOCK:
        g.STATE['players'][0]['diceCount']=2;g.STATE['players'][0]['dice']=[4,4]
        g.STATE['players'][1]['diceCount']=1;g.STATE['players'][1]['dice']=[4]
    assert act(t,'dice_bid',quantity=1,face=4)['ok']
    assert act(u,'dice_challenge')['ok']
    assert g.STATE['phase']=='finished'
    with g.LOCK: g.bump();g.bump()
    p=acct('profile',t=a['accountToken'])['profile'];q=acct('profile',t=b['accountToken'])['profile']
    assert (p['games'],p['wins'],p['points'])==(1,1,3),p;assert (q['games'],q['wins'],q['points'])==(1,0,0),q
    assert act(t,'reset')['ok'];assert acct('profile',t=a['accountToken'])['profile']['games']==1
    assert act(t,'start')['ok'];assert act(t,'reset')['ok'];assert acct('profile',t=a['accountToken'])['profile']['games']==1
    assert api('/api/invite')['urls'] is not None
    print('Account HTTP, duplicate settlement, aborted game, seat protection: PASS')
finally:
    server.shutdown();server.server_close()
