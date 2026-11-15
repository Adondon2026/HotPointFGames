"""Real Chromium regression for the v24 stock panel, including runtime errors."""
import importlib.util
import os
import shutil
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
os.environ['GAMEHALL_DATA_DIR'] = tempfile.mkdtemp()
spec = importlib.util.spec_from_file_location('g', ROOT/'dist/game_hall_lan_v6_2.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
s = g.ReliableThreadingHTTPServer(('127.0.0.1', 0), g.Handler)
threading.Thread(target=s.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{s.server_address[1]}'
try:
    r = g._siege_new('A','a',True,0,'classic','off',0,'stock')
    g._siege_v24_setup(r)
    r.update(mode='classic',phase='play',turn=0,until=0.)
    # Same failure shape as the reported mobile screenshot: inventory present,
    # no selected buffs. Include every positive buff, including armor and shield.
    keys = [k for k in g._SIEGE_V24_KEYS if k not in g._SIEGE_NEGATIVE]
    r['buffs'][0].update({k:min(2,g._SIEGE_V24_CAPS[k]) for k in keys})
    data = g._siege_public(r,'a',-1)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':390,'height':844},has_touch=True,is_mobile=True)
        errors = []
        page.on('pageerror',lambda err:errors.append(str(err)))
        # Standalone /siege may redirect to the lobby; serve the exact built page
        # at a test-only URL on the same HTTP origin, keeping localStorage enabled.
        page.route(url+'/siege-stock-test',lambda route:route.fulfill(status=200,content_type='text/html; charset=utf-8',body=g.SIEGE_PAGE))
        page.goto(url+'/siege-stock-test')
        page.wait_for_function('typeof apply === "function"')
        page.evaluate('d=>{apply(d);overview=null;update()}',data)
        page.locator('#stockBtn').tap()
        rows = page.locator('#stockRows .stock-row')
        expect(rows).to_have_count(len(keys))
        expect(page.locator('#stockPanel')).to_be_visible()
        # Every row has the same quantity controls, not just a heading.
        assert rows.locator('input[type=number]').count()==len(keys)
        assert rows.locator('button').count()==3*len(keys)
        expect(page.get_by_role('spinbutton',name='巨型弹使用数量')).to_have_value('0')
        page.get_by_role('button',name='增加巨型弹').tap()
        expect(page.get_by_role('spinbutton',name='巨型弹使用数量')).to_have_value('1')
        page.get_by_role('button',name='减少巨型弹').tap()
        expect(page.get_by_role('spinbutton',name='巨型弹使用数量')).to_have_value('0')
        page.get_by_role('button',name='技能',exact=True).tap()
        expect(rows).to_have_count(9)
        page.get_by_role('button',name='防御加固选满').tap()
        expect(page.get_by_role('spinbutton',name='防御加固使用数量')).to_have_value('2')
        expect(page.get_by_role('spinbutton',name='核心修复使用数量')).to_have_value('0')
        page.get_by_role('button',name='清空',exact=True).tap()
        expect(page.get_by_role('spinbutton',name='防御加固使用数量')).to_have_value('0')
        assert page.evaluate('room.buffs[0].armor')==2
        page.get_by_role('button',name='全部',exact=True).tap()
        expect(rows).to_have_count(len(keys))
        assert not errors,errors
        print('Siege v24 real browser: all 19 inventory rows rendered; uniform controls, filter, selection and cancel PASS')
        browser.close()
finally:
    s.shutdown()
