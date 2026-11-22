"""Mobile workbench regression: same canvas, contextual panels and scene history."""
import importlib.util, os, shutil, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp()
spec=importlib.util.spec_from_file_location('g',ROOT/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
s=g.ReliableThreadingHTTPServer(('127.0.0.1',0),g.Handler)
threading.Thread(target=s.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{s.server_address[1]}'
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(url+'/trial/siege')
        expect(page.locator('#scenarioToggle')).to_be_visible(timeout=15000)
        page.locator('#scenarioToggle').tap()
        expect(page.locator('#scenarioEditor')).to_be_visible()
        expect(page.locator('#scPanel')).to_be_hidden()
        expect(page.locator('#controls')).to_be_hidden()
        assert page.locator('#game canvas').count()==2
        page.locator('#scBtn-add').tap()
        page.get_by_role('button',name='僵尸',exact=True).tap()
        page.locator('.scresource').first.tap()
        page.locator('#scPanelClose').tap()
        n=page.evaluate('sceneDraft.zombies.length')
        page.touchscreen.tap(195,450)
        assert page.evaluate('sceneDraft.zombies.length')==n+1
        page.locator('#scUndo').tap()
        assert page.evaluate('sceneDraft.zombies.length')==n
        page.locator('#scRedo').tap()
        assert page.evaluate('sceneDraft.zombies.length')==n+1
        page.locator('#scBtn-settings').tap()
        expect(page.locator('#scPanelTitle')).to_have_text('关卡设置')
        for width,height in [(320,800),(390,844),(844,390)]:
            page.set_viewport_size({'width':width,'height':height})
            assert page.evaluate("""()=>{const p=document.querySelector('#scPanel').getBoundingClientRect(),f=document.querySelector('#field').getBoundingClientRect();return p.width<=f.width&&p.height<f.height*.8&&f.height>=innerHeight-2}""")
        page.locator('#scPanelClose').tap()
        page.locator('#scPlay').tap()
        expect(page.locator('#scenarioEditor')).to_be_hidden(timeout=15000)
        page.wait_for_function('room.scenarioActive===true')
        expect(page.locator('#scenarioToggle')).to_have_text('布置')
        assert not errors,errors
        browser.close()
finally:
    s.shutdown();s.server_close()
print('scenario mobile workbench passed')
