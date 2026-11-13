"""Public action ledger, retained trick cards and account score policy."""
import importlib.util, os, tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='hotpoint-table-')
spec=importlib.util.spec_from_file_location('game',root/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
with g.LOCK:
 g.STATE=g.fresh_state();g.STATE['mode']='ddz';g.add_local_bot();g.add_local_bot();g.add_local_bot()
 # add_local_bot caps at three; make host human
 p,a,b=g.STATE['players'];p.update(id='human',name='人',isBot=False,accountId='u',ready=True);g.STATE['hostPlayerId']=p['id'];g.STATE['matchId']='practice';g.STATE['matchQueue']='practice'
 g.deal_ddz();g.apply_ddz_bid(p,3);d=g.STATE['ddz']; assert [e['kind'] for e in d['events']]==['bid','landlord'];assert d['events'][1]['cards']==d['bottom']
 # play once, pass twice. Exact sequence persists even though current lastPlay clears.
 g.apply_ddz_play(p,[p['ddzHand'][0]]);old=d['lastPlay'];g.apply_ddz_pass(a);assert d['lastPlay']==old;g.apply_ddz_pass(b);assert d['lastPlay'] is None
 pub=g.ddz_public(p['id']); assert [e['kind'] for e in pub['events']][-4:]==['play','pass','pass','trick'];assert [e['seq'] for e in pub['events']]==list(range(1,len(pub['events'])+1));assert pub['events'][-4]['cards']==old['cards'];assert all('hand' not in e for e in pub['events'])
 # Practice win yields zero account points even if game raw is enormous.
 with g._db() as db:db.execute('INSERT INTO users VALUES(?,?,?,?)',('u','人','salt','hash'))
 g.finish_ddz(p['id']);g._settle_match();g._settle_match()
 with g._db() as db:
  r=g._profile(db,'u');assert r['points']==0 and r['practice']=={'games':1,'wins':1},r
  assert db.execute('SELECT count(*) FROM results').fetchone()[0]==1
  db.execute('INSERT INTO results(match_id,user_id,game,won,points,raw,ended,queue) VALUES(?,?,?,?,?,?,?,?)',('old','u','ddz',1,3,1000,1,'legacy'))
  r=g._profile(db,'u');assert r['points']==3 and r['games']==1,r
print('DDZ event sequence, pass retention, practice ledger, legacy preservation: PASS')
