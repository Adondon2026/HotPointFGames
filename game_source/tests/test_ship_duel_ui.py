"""Actual mobile Chromium regression for live naval battle controls and room navigation."""
import importlib.util,os,tempfile,threading,urllib.request,json,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='ship_ui_')
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('g',root/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
server=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_address[1]}'
def api(path,data):
 req=urllib.request.Request(origin+path,data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=8) as r:return json.loads(r.read())
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'])
  for width,height in [(320,640),(390,844),(844,390)]:
   r=api('/api/rooms',{'name':'船长'});token=r['token'];code=r['code'];path='/r/'+code
   assert api(path+'/api/action',{'token':token,'type':'set_mode','mode':'ship','requestId':g.secrets.token_hex(10)})['ok']
   assert api(path+'/api/action',{'token':token,'type':'solo_start','requestId':g.secrets.token_hex(10)})['ok']
   ctx=browser.new_context(viewport={'width':width,'height':height},is_mobile=True,has_touch=True)
   ctx.add_init_script(f"localStorage.setItem('gh_token/r/{code}',{json.dumps(token)});")
   page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto(origin+path+'/ship')
   expect(page.locator('#hpMine')).to_have_text('240',timeout=10000)
   expect(page.locator('#dial')).to_be_visible();expect(page.locator('#fire')).to_be_visible()
   ui=page.evaluate("""() => {
     const rect=id=>{const r=document.querySelector(id).getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height}};
     return {w:innerWidth,h:innerHeight,canvas:rect('#sea'),dial:rect('#dial'),fire:rect('#fire'),scrollW:document.documentElement.scrollWidth};
   }""")
   assert abs(ui['canvas']['width']-width)<2 and abs(ui['canvas']['height']-height)<2,ui
   assert ui['scrollW']<=width+2,ui
   for k in ('dial','fire'):
    b=ui[k];assert b['left']>=0 and b['right']<=width+2 and b['top']>=0 and b['bottom']<=height+2,(k,ui)
   # Tap "right max rudder" on the arc; the pointer should jump without dragging.
   dial=ui['dial'];clickx=dial['left']+151*dial['width']/175
   clicky=dial['top']+64*dial['height']/135
   page.touchscreen.tap(clickx,clicky)
   assert page.locator('#dial').get_attribute('aria-valuenow')=='35',page.locator('#dial').get_attribute('aria-valuenow')
   page.touchscreen.tap(width*.48,height*.43)  # tap water to aim
   fire=ui['fire'];x=(fire['left']+fire['right'])/2;y=(fire['top']+fire['bottom'])/2
   page.mouse.move(x,y);page.mouse.down()
   page.wait_for_timeout(680)
   page.mouse.up();page.wait_for_timeout(250)
   active=g.ROOMS[code]['runtime']['shipBattle'];assert active['ships'][0]['shotAt']>0
   page.locator('#menuButton').click();expect(page.locator('#menu')).to_be_visible()
   page.locator('#resume').click();expect(page.locator('#menu')).to_be_hidden()
   assert not errors,(width,height,errors)
   page.close();ctx.close()
  browser.close()
finally:server.shutdown();server.server_close()
print('Naval duel mobile pointer UI passed')
