import importlib.util,os,tempfile,threading,json,urllib.request
from pathlib import Path
import shutil

# Optional end-to-end browser regression: python -m pip install playwright; playwright install chromium.
# Build game first. Run with CHROMIUM_PATH set to a system Chromium if desired.
ROOT=Path(__file__).resolve().parents[1]
SCREENSHOTS=os.environ.get("SIEGE_UI_SCREENSHOTS")
def screenshot(page,name):
 if SCREENSHOTS:
  Path(SCREENSHOTS).mkdir(parents=True,exist_ok=True);page.screenshot(path=str(Path(SCREENSHOTS)/name))

from playwright.sync_api import sync_playwright
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',ROOT/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
s=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=s.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{s.server_address[1]}'
def api(path,data):
 req=urllib.request.Request(url+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read())
def new(mode):
 r=api('/api/rooms',{'name':'A','guestPref':'a'*48});base='/r/'+r['code'];t=r['token'];u=api(base+'/api/join',{'name':'B','seatKey':g.secrets.token_hex(12)})['token']
 def act(kind,**kw):return api(base+'/api/action',dict(token=t,type=kind,requestId=g.secrets.token_hex(12),**kw))
 assert act('set_mode',mode='siege')['ok'];assert act('siege_settings',itemCount=13,mode='classic',wind='off',ammo=0,buffMode='stock',combatMode=mode,reloadSeconds=0,stackCaps={'bounce':20})['ok'];assert act('start')['ok'];return base,t,u
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium'),args=['--no-sandbox']);errors=[]
 def page(base,token,width=390,height=844,storage=None):
  pg=b.new_page(viewport={'width':width,'height':height},has_touch=True,is_mobile=True);pg.on('pageerror',lambda e:errors.append(str(e)))
  def request(path,body):return api(path,json.loads(body))
  pg.expose_function('testRequest',request)
  html=g.SIEGE_PAGE.replace('const roomPrefix=location.pathname.match(/^\/r\/[A-Fa-f0-9]{6}/)?.[0]||"";const roomToken=localStorage.getItem("gh_token"+roomPrefix)||"";', 'const roomPrefix='+json.dumps(base)+';const roomToken='+json.dumps(token)+';').replace('localStorage.', 'testStorage.').replace('<script>','<script>const storageData='+json.dumps(storage or {})+';const testStorage={getItem:k=>storageData[k]??null,setItem:(k,v)=>storageData[k]=v,removeItem:k=>delete storageData[k]};window.fetch=async(path,options)=>({json:async()=>await testRequest(path,options.body)});',1)
  pg.set_content(html);pg.wait_for_function('room && !requesting',timeout=10000);return pg

 base,t,u=new('turn');g.ROOMS[base.split('/')[-1]]['state']['siege']['buffs'][0].update(shield=2,bounce=25);a=page(base,t);a.wait_for_function('canAim()');screenshot(a,'v19_aim.png');assert a.locator('#minimap').is_hidden() and a.locator('#roomInfo').is_hidden() and a.locator('#angleStepper').is_hidden();assert a.locator('#camLeft').count()==0
 x,y=a.evaluate('()=>{let [x,y]=launcher(room.seat);return [(x-camera.x)*innerWidth/VIEW_W,(y-camera.y)*innerHeight/VIEW_H]}')
 a.evaluate('([x,y])=>{const el=canvas;const e=(type,X,Y)=>el.dispatchEvent(new TouchEvent(type,{changedTouches:[new Touch({identifier:7,target:el,clientX:X,clientY:Y})],bubbles:true,cancelable:true}));e("touchstart",x,y);e("touchmove",x-105,y+45);e("touchend",x-105,y+45)}',[x,y]);a.wait_for_timeout(500);assert a.evaluate('room.shots[0]===0 && !playing && power>65');ap=a.evaluate('[angle,power]');print('aim retained',ap)
 a.locator('#stockBtn').tap();assert a.locator('#stockPanel').is_visible();a.get_by_role('button',name='增加护盾').tap();assert a.evaluate('selection.shield===1');n=a.get_by_role('spinbutton',name='弹跳弹使用数量');n.fill('20');a.wait_for_timeout(800);assert n.input_value()=='20' and a.evaluate('selection.bounce===20');n.fill('25');n.press('Enter');assert n.input_value()=='20' and a.evaluate('selection.bounce===20');n.fill('0');n.press('Enter');assert a.evaluate('!selection.bounce');n.fill('20');n.press('Enter');assert a.evaluate('selection.bounce===20');a.locator('#stockClose').tap();assert a.evaluate('[angle,power]')==ap and a.evaluate('selection.shield===1')
 a.locator('#angleValue').tap();assert a.locator('#angleStepper').is_visible();a.locator('#angleUp').click();assert a.evaluate('angle')==ap[0]+1
 a.locator('#mapToggle').tap();assert a.locator('#minimap').is_visible() and a.locator('#angleStepper').is_visible();screenshot(a,'v19_map.png');a.locator('#mapCanvas').tap(position={'x':195,'y':60});assert a.locator('#minimap').is_visible() and a.evaluate('camera.x>400')
 a.locator('#menuToggle').tap();assert a.locator('#roomInfo').is_visible();a.locator('#homeCam').tap();assert a.locator('#minimap').is_visible() and a.evaluate('camera.x<300');a.locator('#menuToggle').tap();assert a.locator('#roomInfo').is_visible();a.locator('#hudOpacity').fill('55');a.locator('#mapOpacity').fill('60');assert a.evaluate('displayPrefs.hud===55 && displayPrefs.map===60');stored=a.evaluate('({...storageData})');a.locator('#menuToggle').tap();assert a.locator('#roomInfo').is_hidden();a.locator('#mapToggle').tap();assert a.locator('#minimap').is_hidden();a.locator('#mapToggle').tap();assert a.locator('#minimap').is_visible();a.locator('#angleValue').tap();assert a.locator('#minimap').is_visible();a.locator('#angleValue').tap();
 a.locator('#fire').tap();a.wait_for_function('!!playing');assert a.evaluate('playing.event.selected.shield===1 && playing.event.selected.bounce===20');assert a.locator('#controls').is_hidden() and a.locator('#mapToggle').is_visible() and a.locator('#minimap').is_visible();screenshot(a,'v19_flight.png');print('turn UI pass');a.close()
 base,t,u=new('sync');a=page(base,t,844,390,stored);c=page(base,u,390,844);assert a.evaluate('displayPrefs.hud===55 && displayPrefs.map===60');assert a.locator('#hud').bounding_box()['height']<42;assert a.locator('#controls').bounding_box()['height']<43;assert c.locator('#controls').bounding_box()['height']>=58;a.locator('#mapToggle').tap();screenshot(a,'v191_landscape_aim.png');screenshot(c,'v191_portrait.png');a.locator('#fire').tap();a.wait_for_function('room.ready[room.seat]');assert a.locator('#angleValue').is_hidden() and a.locator('#fire').inner_text()=='取消准备';a.locator('#fire').tap();a.wait_for_function('!room.ready[room.seat]');assert a.locator('#angleValue').is_visible();a.locator('#fire').tap();c.locator('#fire').tap();a.wait_for_function('!!syncReplay');assert a.locator('#controls').is_hidden() and c.locator('#controls').is_hidden() and a.locator('#minimap').is_visible();screenshot(a,'v19_sync.png');print('sync UI pass');assert not errors,errors;b.close()
s.shutdown()
