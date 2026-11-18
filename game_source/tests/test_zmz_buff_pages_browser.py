"""Chromium proof: every buff page fits phone viewport, including its return button."""
import importlib.util
import os
import shutil
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
os.environ['GAMEHALL_DATA_DIR']=tempfile.mkdtemp(prefix='zmz_buff_pages_')
spec=importlib.util.spec_from_file_location('game',ROOT/'dist/game_hall_lan_v6_2.py')
g=importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

with sync_playwright() as pw:
    browser=pw.chromium.launch(
        executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('google-chrome') or shutil.which('chromium'),
        args=['--no-sandbox'])
    for width,height in [(390,844),(320,568),(844,390),(640,360),(480,320)]:
        page=browser.new_page(viewport={'width':width,'height':height},has_touch=True,is_mobile=True)
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        # About:blank has opaque-origin localStorage. Explicit fake storage
        # allows testing the exact generated HTML with no network required.
        page.evaluate("""() => {
          const store={};
          Object.defineProperty(window,'localStorage',{configurable:true,value:{
            getItem:k=>store[k]??null,setItem:(k,v)=>store[k]=String(v),
            removeItem:k=>delete store[k]}});
        }""")
        page.set_content(g.HTML_PAGE,wait_until='domcontentloaded')
        page.evaluate("""() => {
          state={mode:'siege',phase:'lobby',isHost:true,players:[],settings:{},seats:[]};
          document.getElementById('settingsModal').classList.remove('hidden');
          document.getElementById('siegeAdvanced').classList.remove('hidden');
          initSiegeSettings();
          document.getElementById('siegeAllowedConfig').open=true;
        }""")
        page.wait_for_function("document.getElementById('settingsModal').classList.contains('zmz-buff-mode')")
        page.wait_for_timeout(80)
        all_buffs=page.locator('#siegeBuffChoices .siege-buff-row')
        assert all_buffs.count()==26,(width,height,all_buffs.count())
        totals=[];count=0
        for n in range(26):
            vals=page.evaluate("""() => {
              const l=document.getElementById('siegeBuffChoices');
              const details=document.getElementById('siegeAllowedConfig');
              const back=document.getElementById('siegeBuffBack').getBoundingClientRect();
              const sheet=document.querySelector('#settingsModal .sheet').getBoundingClientRect();
              const visible=[...l.querySelectorAll('.siege-buff-row')].filter(e=>e.getBoundingClientRect().height>0);
              return {
                total:visible.length,
                pages:document.getElementById('zmzBuffPageSummary').textContent,
                innerOverflow:l.scrollHeight-l.clientHeight,
                entireOverflow:details.scrollHeight-details.clientHeight,
                footerBottom:back.bottom,sheetBottom:sheet.bottom,
                viewport:innerHeight,
                pagesShown:document.querySelectorAll('#zmzBuffPageNumbers button').length,
                nextDisabled:document.getElementById('zmzBuffNext').disabled
              }
            }""")
            assert vals['total']>0,(width,height,vals)
            assert vals['innerOverflow']<=2,(width,height,vals)
            assert vals['entireOverflow']<=2,(width,height,vals)
            assert vals['footerBottom']<=min(vals['sheetBottom']-5,vals['viewport']-2),(width,height,vals)
            assert 1<=vals['pagesShown']<=3,(width,height,vals)
            totals.append(vals['total'])
            if vals['nextDisabled']:break
            page.locator('#zmzBuffNext').click()
        assert sum(totals)==26,(width,height,totals)
        if height>=568:assert totals==[9,9,8],(width,height,totals)
        # Hidden-page checkbox values must survive switching and scrolling is never needed.
        page.locator('#siegeBuffBack').click()
        assert not page.evaluate("document.getElementById('siegeAllowedConfig').open")
        assert not page.evaluate("document.getElementById('settingsModal').classList.contains('zmz-buff-mode')")
        assert not errors,(width,height,errors)
        print(f'{width}x{height} game UI paging: {totals}, no scroll/clipped footer, close works PASS')
        page.close()
    browser.close()
