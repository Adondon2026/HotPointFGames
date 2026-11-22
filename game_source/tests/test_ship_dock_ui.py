"""End-to-end mobile viewport, wheel/throttle gestures and camera/menu regression."""
import importlib.util
import os
import shutil
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
os.environ['GAMEHALL_DATA_DIR'] = tempfile.mkdtemp(prefix='dock_test_')
spec = importlib.util.spec_from_file_location('g', ROOT / 'dist/game_hall_lan_v6_2.py')
game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game)
assert 'SHIP_DOCK_SCRIPT' not in game.SHIP_DOCK_PAGE
assert 'id="wheel"' in game.SHIP_DOCK_PAGE and 'id="engineRail"' in game.SHIP_DOCK_PAGE

server = game.ReliableThreadingHTTPServer(('127.0.0.1', 0), game.Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_address[1]}/trial/ship'

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('google-chrome') or shutil.which('chromium'),
            args=['--no-sandbox'],
        )
        for width, height in ((320, 640), (360, 800), (390, 844), (844, 390)):
            page = browser.new_page(viewport={'width': width, 'height': height}, is_mobile=True, has_touch=True)
            errors = []
            page.on('pageerror', lambda err: errors.append(str(err)))
            page.goto(url)
            expect(page.locator('#wheel')).to_be_visible()
            expect(page.locator('#engineRail')).to_be_visible()
            page.wait_for_timeout(140)
            sizes = page.evaluate("""() => {
                const area = id => { const r = document.querySelector(id).getBoundingClientRect();
                  return {left:r.left, right:r.right, top:r.top, bottom:r.bottom, width:r.width, height:r.height}; };
                return { canvas:area('#sea'), wheel:area('#wheel'), rail:area('#engineRail'),
                  viewportW:innerWidth,viewportH:innerHeight,scrollW:document.documentElement.scrollWidth };
            }""")
            assert abs(sizes['canvas']['width'] - sizes['viewportW']) < 2, sizes
            assert abs(sizes['canvas']['height'] - sizes['viewportH']) < 2, sizes
            assert sizes['scrollW'] <= sizes['viewportW'] + 2, sizes
            assert sizes['wheel']['right'] + 10 < sizes['rail']['left'], sizes
            for key in ('wheel', 'rail'):
                b = sizes[key]
                assert b['left'] >= 0 and b['right'] <= width + 1, (width, key, sizes)
                assert b['top'] >= 0 and b['bottom'] <= height + 1, (height, key, sizes)

            wheel = page.locator('#wheel').bounding_box()
            cx, cy = wheel['x']+wheel['width']/2, wheel['y']+wheel['height']/2
            page.mouse.move(cx + 41, cy)
            page.mouse.down()
            page.mouse.move(cx, cy + 41, steps=7)
            page.mouse.up()
            rudder = int(page.locator('#wheel').get_attribute('aria-valuenow'))
            assert rudder >= 13, (width, rudder)
            page.mouse.click(cx, cy)  # wheel hub = neutral
            assert page.locator('#wheel').get_attribute('aria-valuenow') == '0'

            rail = page.locator('#engineRail').bounding_box()
            x = rail['x'] + rail['width']*.52
            page.mouse.move(x, rail['y']+rail['height']/2)
            page.mouse.down()
            page.mouse.move(x, rail['y']+22, steps=5)
            page.mouse.up()
            assert page.locator('#engineRail').get_attribute('aria-valuenow') == '2'
            page.wait_for_timeout(650)
            assert page.locator('#speed').inner_text().endswith('kn')

            page.mouse.move(width*.48, height*.42)
            page.mouse.down()
            page.mouse.move(width*.48+18, height*.42+20, steps=4)
            page.mouse.up()
            expect(page.locator('#follow')).to_be_visible()
            page.locator('#follow').click()
            expect(page.locator('#follow')).to_be_hidden()

            page.locator('#menuButton').click()
            expect(page.locator('#menu')).to_be_visible()
            page.locator('#assist').uncheck()
            page.locator('#resume').click()
            expect(page.locator('#menu')).to_be_hidden()
            assert not errors, (width, height, errors)
            page.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()

print('ship docking immersive mobile UI passed')
