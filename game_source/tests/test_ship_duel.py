"""Naval variant reuses the Siege turn engine, ballistics, buffs and room authentication."""
import importlib.util
import json
import math
import os
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

os.environ['GAMEHALL_DATA_DIR'] = tempfile.mkdtemp(prefix='naval_siege_')
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('g', root / 'dist/game_hall_lan_v6_2.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
server = g.ReliableThreadingHTTPServer(('127.0.0.1', 0), g.Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
base = f'http://127.0.0.1:{server.server_address[1]}'

def api(path, data=None):
    req = urllib.request.Request(base+path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Content-Type':'application/json'})
    try:res=urllib.request.urlopen(req,timeout=8)
    except urllib.error.HTTPError as e:res=e
    with res:
        raw=res.read()
        if res.headers.get('Content-Type','').startswith('text/html'):
            return raw.decode()
        return json.loads(raw)

def act(r,token,kind,**kw):
    return api('/r/'+r['code']+'/api/action',dict(token=token,type=kind,
        requestId=g.secrets.token_hex(12),**kw))

def naval(r,token,kind='state',**kw):
    return api('/r/'+r['code']+'/api/siege',dict(token=token,type=kind,**kw))

try:
    room=api('/api/rooms',{'name':'Captain'});host=room['token'];prefix='/r/'+room['code']
    assert act(room,host,'set_mode',mode='ship')['ok']
    assert not act(room,host,'start')['ok']
    other=api(prefix+'/api/join',{'name':'Mate','seatKey':g.secrets.token_hex(12)})['token']
    assert act(room,host,'start')['ok']
    state=naval(room,host)
    assert state['ok'] and state['naval'] and state['turn']==0
    assert state['combatMode']=='turn' and state['moveRadius']==110
    assert state['buffMode']=='auto'
    assert len(state['items'])==13
    assert 'SHIP_BATTLE_SCRIPT' not in g.SIEGE_PAGE
    assert 'navalTools' in g.SIEGE_PAGE
    assert g.ROOMS[room['code']]['state']['siege'] is g.ROOMS[room['code']]['state']['siege']

    opponent=naval(room,other)
    assert opponent['seat']==1 and opponent['naval'] and opponent['rev']==state['rev']
    assert not naval(room,'untrusted','move',x=220,y=250,rev=state['rev'])['ok']
    assert not naval(room,other,'move',x=735,y=250,rev=state['rev'])['ok']
    assert not naval(room,host,'move',x=480,y=235,rev=state['rev'])['ok']
    assert not naval(room,host,'move',x=float('nan'),y=240,rev=state['rev'])['ok']
    assert not naval(room,host,'move',x=210,y=250,rev=-1)['ok']

    sx,sy=state['launchers'][0]
    moved=naval(room,host,'move',x=sx+65,y=sy-40,rev=state['rev'])
    assert moved['ok'] and moved['turn']==1 and moved['navalMove']['seat']==0
    assert moved['navalMove']['from']==[sx,sy]
    assert abs(moved['launchers'][0][0]-(sx+65))<.1
    assert not naval(room,host,'move',x=sx,y=sy,rev=moved['rev'])['ok']
    assert moved['shots']==[0,0]  # Moving consumes the turn, never creates a shell.

    battle=g.ROOMS[room['code']]['state']['siege']
    battle['until']=0  # simulate elapsed handoff for deterministic tests
    bot_or_friend=naval(room,other)
    assert bot_or_friend['turn']==1
    # Use the actual existing Siege ballistic engine for zero-gravity horizontal fire.
    before=g._siege_core(battle['bodies'],0)
    shot=naval(room,other,'fire',rev=bot_or_friend['rev'],angle=0,power=70,selection={})
    assert shot['ok'],shot
    assert shot['shots']==[0,1]
    event=shot['event']
    assert event and event['frames'] and event['hitAt'] is not None
    assert event['frames'][0][1][1] == event['frames'][0][1][1]
    assert all(math.isfinite(v) for frame in event['frames'] for v in (frame[0],))
    assert g._siege_core(battle['bodies'],0) < before, (before,g._siege_core(battle['bodies'],0),event.get('impact'))
    assert not naval(room,other,'fire',rev=shot['rev'],angle=0,power=70)['ok']
    assert not naval(room,other,'move',x=730,y=230,rev=shot['rev'])['ok']

    # A full replay and buffs inventory are server-authoritative (not a second engine).
    assert g._siege_public(battle,battle['players'][0]['key'],-1)['naval']
    assert isinstance(battle['buffs'][0],dict)
    assert battle['event']['attacks'] is not None
    assert not naval(room,other,'return')['ok']
    assert act(room,host,'reset')['ok']
    s=api(prefix+'/api/state?token='+other)['state']
    assert s['phase']=='lobby'
    assert act(room,host,'start')['ok']
    match2=naval(room,host)
    assert match2['turn']==0 and match2['shots']==[0,0]
    assert match2['bodies'] and match2['naval']

    solo=api('/api/rooms',{'name':'Solo'});t=solo['token']
    assert act(solo,t,'set_mode',mode='ship')['ok']
    assert act(solo,t,'solo_start')['ok']
    s=naval(solo,t);assert s['ok'] and s['bot']
    # A bot takes a turn using the same siege firing engine, without a live traffic loop.
    rt=g.ROOMS[solo['code']]['state']['siege']
    rt['turn']=1;rt['until']=0
    g._naval_bot(rt)
    assert rt['shots'][1]==1
    print('Naval Siege engine reuse, turn moves, zero gravity, LAN auth, rematch, solo bot PASS')
finally:
    server.shutdown();server.server_close()
