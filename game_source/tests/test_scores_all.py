"""Exercise every game's real terminal path, account ledger and repeat/rematch semantics."""
import importlib.util, os, tempfile, json, threading, urllib.request
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp();root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
server=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=server.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{server.server_address[1]}'
def api(path,data):
 req=urllib.request.Request(url+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'});return json.loads(urllib.request.urlopen(req,timeout=8).read())
accounts=[api('/api/account',dict(type='register',name=n,pin='1234')) for n in ('甲','乙','丙')]
def profile(i):return api('/api/account',dict(type='profile',accountToken=accounts[i]['accountToken']))['profile']
def make(mode,solo=False):
 a=api('/api/rooms',dict(accountToken=accounts[0]['accountToken']));path='/r/'+a['code'];rec=g.ROOMS[a['code']];seats=[a]
 for ac in accounts[1:3 if mode=='ddz' else 2] if not solo else []:seats.append(api(path+'/api/join',dict(accountToken=ac['accountToken'])))
 def act(i,kind,**kw):
  r=api(path+'/api/action',dict(token=seats[i]['token'],type=kind,requestId=g.secrets.token_hex(8),**kw));assert r['ok'],(mode,kind,r);return r
 act(0,'set_mode',mode=mode)
 if mode=='siege':act(0,'siege_settings',itemCount=0,ammo=6,mode='standard',wind='off')
 act(0,'solo_start' if solo else 'start');return path,rec,seats,act
try:
 for mode in ('cards','dice','draw','ddz','chuanma','army','siege'):
  path,rec,seats,act=make(mode);before=profile(0)['points'];mid=rec['state']['matchId']
  if mode=='army':act(0,'army_setup');act(1,'army_setup');act(1,'army_resign')
  elif mode=='siege':
   r=rec['state']['siege'];r['shots']=[5,6];next(b for b in r['bodies'] if b['side']==1 and b['kind']=='core')['hp']=1
   v=api(path+'/api/siege',dict(type='fire',token=seats[0]['token'],rev=r['rev'],angle=42,power=59));assert v['phase']=='over' and v['winner']==0 and v['myResult']['points']==3,v.get('error')
  else:
   with g._room_scope(rec):
    p=g.STATE['players'];a,b=p[:2]
    if mode=='cards':b['life']=1;g.finish_cards_round(b['id'],'test',[])
    elif mode=='dice':b['diceCount']=1;g.finish_dice_round(b['id'],'test')
    elif mode=='draw':a['score']=4;b['score']=1;g.STATE['draw']['turnIndex']=g.STATE['draw']['totalTurns'];g.start_draw_turn()
    elif mode=='ddz':g.STATE['ddz'].update(landlordId=p[2]['id'],baseBid=1,multiplier=1);g.finish_ddz(a['id'])
    elif mode=='chuanma':a['cmScore']=3;b['cmScore']=-3;g.cm_finish('test')
  assert profile(0)['points']==before+3,(mode,profile(0))
  with g._room_scope(rec):g._settle_match();g._settle_match()
  assert profile(0)['points']==before+3
  if mode=='ddz':assert next(x for x in profile(1)['recent'] if x['game']=='ddz')['points']==3 # both farmers win
  if mode=='siege':
   r=rec['state']['siege'];r['until']=0;v=api(path+'/api/siege',dict(type='rematch',token=seats[0]['token']));assert v['phase']=='play' and rec['state']['matchId']!=mid
   r['shots']=[5,6];next(b for b in r['bodies'] if b['side']==1 and b['kind']=='core')['hp']=1
   v=api(path+'/api/siege',dict(type='fire',token=seats[0]['token'],rev=r['rev'],angle=42,power=59));assert v['myResult']['points']==3 and profile(0)['points']==before+6
  print(mode,'account settlement PASS')
 # Practice siege and guest points do not mint account scores.
 path,rec,seats,act=make('siege',True);before=profile(0);r=rec['state']['siege'];r['shots']=[5,6];next(b for b in r['bodies'] if b['side']==1 and b['kind']=='core')['hp']=1
 v=api(path+'/api/siege',dict(type='fire',token=seats[0]['token'],rev=r['rev'],angle=42,power=59));assert v['myResult']['queue']=='practice' and v['myResult']['points']==0 and profile(0)['points']==before['points'] and profile(0)['practice']['games']==before['practice']['games']+1
 print('Seven games, farmer team, siege rematch, practice and idempotency PASS')
finally:server.shutdown();server.server_close()
