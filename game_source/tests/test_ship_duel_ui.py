"""Chromium mobile regression for the naval thin UI overlay on the shared Siege canvas."""
import importlib.util, os, tempfile, threading, urllib.request, json, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='naval_ui_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
assert 'function navalAttemptMove' in g.SIEGE_PAGE
server=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_address[1]}'
def api(path,data):
 req=urllib.request.Request(origin+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=10) as r:return json.loads(r.read())
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'])
  for width,height in ((320,640),(390,844),(844,390)):
   match=api('/api/rooms',{'name':'Captain'});token=match['token'];code=match['code'];prefix='/r/'+code
   def act(kind,**kw):
    return api(prefix+'/api/action',dict(token=token,type=kind,requestId=g.secrets.token_hex(12),**kw))
   assert act('set_mode',mode='ship')['ok']
   assert act('solo_start')['ok']
   context=browser.new_context(viewport={'width':width,'height':height},is_mobile=True,has_touch=True)
   context.add_init_script(f"localStorage.setItem('gh_token/r/{code}',{json.dumps(token)});")
   page=context.new_page();errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(origin+prefix+'/ship')
   expect(page.locator('#navalTools')).to_be_visible(timeout=12000)
   expect(page.locator('#navalMove')).to_be_enabled(timeout=12000)
   expect(page.locator('#field')).to_be_visible()
   assert page.evaluate("room.naval && room.combatMode==='turn' && !syncMode()")
   assert page.evaluate("angle===0 && power===70")
   dim=page.evaluate("""() => {
    const pos=id=>{const r=document.querySelector(id).getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,bot:r.bottom,right:r.right}};
    return {field:pos('#field'),controls:pos('#navalTools'),viewport:[innerWidth,innerHeight],scroll:document.documentElement.scrollWidth};
   }""")
   assert abs(dim['field']['w']-width)<2 and abs(dim['field']['h']-height)<2,dim
   assert dim['scroll']<=width+2,dim
   nav=dim['controls'];assert nav['x']>=0 and nav['right']<=width+2,dim
   assert nav['y']>=0 and nav['bot']<=height+2,dim

   page.locator('#navalMove').tap()
   assert page.evaluate("navalMoveMode && document.querySelector('#game').classList.contains('move-mode')")
   sx,sy=page.evaluate('launcher(room.seat)')
   dst=page.evaluate("""([dx,dy])=>{
     const [x,y]=launcher(room.seat),r=canvas.getBoundingClientRect();
     return [r.left+(x+dx-camera.x)*ZOOM*r.width/canvas.width,
             r.top+(y+dy-camera.y)*ZOOM*r.height/canvas.height];
   }""",[58,20])
   assert 0<=dst[0]<=width and 0<=dst[1]<=height,(width,height,dst)
   page.touchscreen.tap(*dst)
   page.wait_for_function('room.navalMove && room.navalMove.seat===0',timeout=8500)
   move=page.evaluate('room.navalMove')
   assert abs(move['to'][0]-(sx+58))<2,move
   assert abs(move['to'][1]-(sy+20))<2,move
   assert page.evaluate('room.shots[0]===0 && room.turn===1')
   page.wait_for_timeout(300)
   assert not errors,(width,height,errors)
   context.close()
  browser.close()
finally:
 server.shutdown();server.server_close()
print('Naval shared Siege UI, camera and click-radius movement passed')
