"""Browser regression for quiet hall/room discovery and Siege's vertical aim sliders."""
import importlib.util
import json
import os
import shutil
import tempfile
import threading
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
os.environ["GAMEHALL_DATA_DIR"] = tempfile.mkdtemp(prefix="quiet_ui_")
spec = importlib.util.spec_from_file_location("g", ROOT / "dist/game_hall_lan_v6_2.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
server = g.ReliableThreadingHTTPServer(("127.0.0.1", 0), g.Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_address[1]}"


def api(path, data):
    req = urllib.request.Request(
        url + path, data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())


try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH")
            or shutil.which("google-chrome")
            or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        for width, height in ((320, 640), (390, 844), (844, 390)):
            host = api("/api/rooms", {"name": "房主"})
            code, token = host["code"], host["token"]
            ctx = browser.new_context(
                viewport={"width": width, "height": height},
                is_mobile=True, has_touch=True,
            )
            ctx.add_init_script(
                f"localStorage.setItem('gh_token/r/{code}',{json.dumps(token)});"
            )
            page = ctx.new_page()
            errors = []
            page.on("pageerror", lambda err: errors.append(str(err)))
            page.goto(url + "/")
            expect(page.locator(".room-heading")).to_be_visible()
            expect(page.locator("#create")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
            page.goto(url + f"/r/{code}/")
            expect(page.locator("#modeSiege")).to_be_visible(timeout=12000)
            assert page.locator("#liteLibrary .mode").first.get_attribute("id") == "modeSiege"
            page.locator("#modeSiege").tap()
            page.wait_for_function("state && state.mode==='siege' && state.modeSelected!==false")
            expect(page.locator("#liteLibrary")).to_be_hidden()
            expect(page.locator("#liteCurrent")).to_be_visible()
            expect(page.locator("#liteChangeGame")).to_be_visible()
            expect(page.locator("#liteGameName")).to_have_text("保卫子刊", timeout=6000)
            page.locator("#liteChangeGame").tap()
            expect(page.locator("#liteLibrary")).to_be_visible()
            assert page.locator("#liteLibrary .mode").count() == 7
            page.locator("#modeDice").tap()
            page.wait_for_function("state && state.mode==='dice'")
            expect(page.locator("#liteLibrary")).to_be_hidden()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
            assert not errors, (width, height, errors)
            ctx.close()

            r = g._siege_new("房主", "host", True, 0, "classic", "off", 0, "stock")
            g._siege_v24_setup(r)
            r.update(mode="classic", phase="play", turn=0, until=0.)
            data = g._siege_public(r, "host", -1)
            ctx = browser.new_context(
                viewport={"width": width, "height": height},
                is_mobile=True, has_touch=True,
            )
            page = ctx.new_page()
            errs = []
            page.on("pageerror", lambda err: errs.append(str(err)))
            page.route(
                url + "/quiet-siege-test",
                lambda route: route.fulfill(
                    status=200, content_type="text/html; charset=utf-8",
                    body=g.SIEGE_PAGE,
                ),
            )
            page.goto(url + "/quiet-siege-test")
            page.wait_for_function('typeof apply === "function"')
            page.evaluate("d=>{apply(d);overview=null;update()}", data)
            expect(page.locator("#angleSlider")).to_be_visible()
            expect(page.locator("#powerSlider")).to_be_visible()
            assert page.evaluate(
                "getComputedStyle(document.querySelector('#angleStepper')).flexDirection==='column'"
            )
            page.locator("#angleSlider").evaluate(
                "(el)=>{el.value='62';el.dispatchEvent(new Event('input',{bubbles:true}))}"
            )
            assert page.evaluate("angle===62 && document.querySelector('#av').textContent==='62°'")
            page.locator("#angleUp").tap()
            assert page.evaluate("angle===63")
            page.locator("#powerSlider").evaluate(
                "(el)=>{el.value='82';el.dispatchEvent(new Event('input',{bubbles:true}))}"
            )
            page.locator("#powerDown").tap()
            assert page.evaluate("power===81")
            geometry = page.evaluate("""() => {
                const box = id => {
                    const r = document.querySelector(id).getBoundingClientRect();
                    return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};
                };
                return {controls:box('#controls'),angle:box('#angleSlider'),
                        power:box('#powerSlider'),fire:box('#fire')};
            }""")
            assert geometry["controls"]["bottom"] <= height + 2, (width, height, geometry)
            assert geometry["controls"]["x"] >= -2, (width, height, geometry)
            assert geometry["fire"]["right"] <= width + 2, (width, height, geometry)
            assert geometry["angle"]["right"] < geometry["fire"]["x"], (width, height, geometry)
            assert not errs, (width, height, errs)
            ctx.close()
        browser.close()
finally:
    server.shutdown()
    server.server_close()
print("Quiet hall/room and Siege vertical sliders: three mobile viewports PASS")
