"""Free camera has no buff entitlement; elastic rails affect real projectiles."""
import copy,importlib.util,os,tempfile,math
from pathlib import Path
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def new(mode='sky',buff='auto',count=0):return g._siege_new('A','a',True,count,mode,'off',0,buff)
assert 'vision' not in g._SIEGE_ITEMS and 'vision' not in g._SIEGE_SELECTABLE
for mode in (*g._SIEGE_FIELDS,*g._SIEGE_NEW_FIELDS):
 r=new(mode,count=25);assert all(i['kind']!='vision' for i in r['items'])
 assert ('vision' not in r['buffs'][0])
r=new('sky');assert r['reflectors'];r['buffs'][0]['vision']=2;r['items']=[dict(id=0,kind='vision',x=200,y=200,r=15)];g._siege_normalize_buffs(r);assert r['buffs'][0]['power']==2 and r['items'][0]['kind']=='power'
r=new();g._siege_fire(r,75,100);e=r['event'];assert e['bounces'],e['impact'];x,y,t,i=e['bounces'][0];assert i==-1 and abs(y-(-55+6+.1))<.11
post=[f for f in e['frames'] if f[0]>t and f[1]];assert post and post[0][1][1]>y
q=new();q['reflectors']=[];g._siege_fire(q,75,100);assert not q['event']['bounces'] and q['event']['frames']!=e['frames']
r=new();r['buffs'][0]['splitshot']=1;g._siege_fire(r,75,100);assert any(b[3]>=0 for b in r['event']['bounces']),r['event']['bounces']
# Both sides can use a bank shot to damage the opposite elevated fort.
for side in (0,1):
 found=None
 for a in range(55,86,2):
  for p in range(85,101,2):
   r=new();r['turn']=side;g._siege_fire(r,a,p)
   if r['event']['bounces'] and any(b['hp']<b['max'] for b in r['bodies'] if b['side']==1-side):found=(a,p);break
  if found:break
 assert found,side
 print('sky reflected hit',side,found)
assert new('movingwall')['reflectors'] and not new('standard')['reflectors']
print('v0.14: retired vision, migrated resources, reflected trajectory, fragment reflection and bank shots PASS')
