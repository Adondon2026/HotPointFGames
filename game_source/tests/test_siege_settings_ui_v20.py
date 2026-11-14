"""Optional real browser UI test; run after build.py and install Playwright Chromium."""
import importlib.util,os,tempfile,threading,json,urllib.request,urllib.error,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',Path(__file__).resolve().parents[1]/'dist/game_hall_lan_v6_2.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
s=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler);threading.Thread(target=s.serve_forever,daemon=True).start();url=f'http://127.0.0.1:{s.server_address[1]}'
def api(path,data=None):
 req=urllib.request.Request(url+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
 try:r=urllib.request.urlopen(req,timeout=15)
 except urllib.error.HTTPError as e:r=e
 with r:return json.loads(r.read())
r=api('/api/rooms',{'name':'A','guestPref':'b'*48});base='/r/'+r['code'];t=r['token'];api(base+'/api/action',dict(token=t,type='set_mode',mode='siege',requestId=g.secrets.token_hex(12)))
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':390,'height':844},has_touch=True,is_mobile=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def request(path,body):
  data=json.loads(body) if body else None
  return api(path,data)
 page.expose_function('testRequest',request)
 html=g.HTML_PAGE.replace(r'const roomPrefix=location.pathname.match(/^\/r\/[A-Fa-f0-9]{6}/)?.[0]||"";', 'const roomPrefix='+json.dumps(base)+';').replace('localStorage.', 'testStorage.')
 init='const storageData='+json.dumps({'gh_token'+base:t,'gh_guest_pref':'b'*48})+';const testStorage={getItem:k=>storageData[k]??null,setItem:(k,v)=>storageData[k]=v,removeItem:k=>delete storageData[k]};window.fetch=async(path,options)=>({ok:true,text:async()=>JSON.stringify(await testRequest(path,options?.body||null))});'
 html=html.replace('<script>','<script>'+init,1);page.set_content(html);page.wait_for_function('state?.mode==="siege" && state.isHost');page.locator('#liteGameSettings').click();page.wait_for_function('!document.getElementById("settingsModal").classList.contains("hidden")');assert page.locator('#siegeReload').is_hidden();assert page.locator('#siegeItemCount').get_attribute('type')=='number';page.locator('[data-value="sync"]').click();page.wait_for_function('state.settings.siegeCombatMode==="sync"');assert page.locator('#siegeReload').is_visible();page.locator('#siegeReload').fill('27');page.locator('#siegeReload').blur();page.wait_for_function('state.settings.siegeReload===27');page.locator('#siegeAmmo').fill('17');page.locator('#siegeAmmo').blur();page.wait_for_function('state.settings.siegeAmmo===17');page.locator('#siegeAllowedConfig summary').click();page.locator('#siegeBuffNone').click();page.wait_for_function('state.settings.siegeAllowedBuffs?.length===0');page.locator('#siegeBuffInvert').click();page.wait_for_function('state.settings.siegeAllowedBuffs?.length===16');page.locator('#cap-bounce').fill('20');page.locator('#cap-bounce').blur();page.wait_for_function('state.settings.siegeStackCaps?.bounce===20');page.locator('#cap-power').fill('3');page.locator('#cap-power').blur();page.wait_for_function('state.settings.siegeStackCaps?.power===3');assert page.locator('#cap-power').get_attribute('max')=='5';assert page.locator('#cap-gunteleport').is_disabled();page.locator('[data-value="sturdy"]').click();page.wait_for_function('state.settings.siegeFortStrength==="sturdy"');page.locator('#siegeAllowedConfig summary').click();page.locator('#settingsModal .sheet').evaluate('(e)=>e.scrollTop=0');
 if os.environ.get('SIEGE_UI_SCREENSHOTS'):page.screenshot(path=os.environ['SIEGE_UI_SCREENSHOTS']+'/v20_settings.png')
 page.locator('#siegeAllowedConfig summary').click();page.locator('#cap-bounce').scroll_into_view_if_needed();
 if os.environ.get('SIEGE_UI_SCREENSHOTS'):page.screenshot(path=os.environ['SIEGE_UI_SCREENSHOTS']+'/v20_caps.png')
 page.locator('#settingsModal [data-close]').click();page.locator('#liteGameSettings').click();assert page.locator('#cap-bounce').input_value()=='20';assert page.locator('#siegeAmmo').input_value()=='17';assert not errors,errors;print('v0.20 settings browser: numbers, conditional visibility, select/invert, individual cap, persistence PASS');b.close()
s.shutdown()
