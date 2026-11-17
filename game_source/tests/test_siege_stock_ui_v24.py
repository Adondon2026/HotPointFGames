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
        # A modifier's trigger buttons occupy a dedicated left rail, not a
        # second row where they can collide with the description below.
        assert page.evaluate("siegeZombieMirror('walker',250,480)") is True
        assert page.evaluate("siegeZombieMirror('walker',710,480)") is False
        assert page.evaluate("siegeZombieMirror('siegecar',250,480)") is False
        assert page.evaluate("siegeZombieMirror('siegecar',710,480)") is True
        page.locator('#stockRows .stock-row[data-buff-kind="splitshot"] button').nth(1).tap()
        expect(page.locator('#stockModeRail .stock-mode-card')).to_have_count(2)
        expect(page.get_by_role('button',name='分裂时机：击发分裂')).to_have_attribute('aria-pressed','true')
        page.get_by_role('button',name='分裂时机：落点分裂').tap()
        expect(page.get_by_role('button',name='分裂时机：落点分裂')).to_have_attribute('aria-pressed','true')
        assert page.evaluate("shotConfig.triggers.splitshot")=='contact'
        for width in (320,390,480):
            page.set_viewport_size({'width':width,'height':844})
            regions=page.evaluate("""()=>{
                const rail=document.querySelector('#stockModeRail').getBoundingClientRect();
                const rows=document.querySelector('#stockRows').getBoundingClientRect();
                const panel=document.querySelector('#stockPanel').getBoundingClientRect();
                return {gap:rows.left-rail.right,railLeft:rail.left,panelLeft:panel.left,
                    rowWidth:rows.width, railWidth:rail.width,
                    badButtons:[...document.querySelectorAll('#stockModeRail button')].filter(x=>{
                      const b=x.getBoundingClientRect();return b.left<rail.left-1||b.right>rail.right+1||b.width<25
                    }).length,
                    oldInline:document.querySelectorAll('#stockRows .stock-row > .buff-inline').length}
            }""")
            assert regions['gap']>=3 and regions['railLeft']>=regions['panelLeft'] and regions['rowWidth']>160 and regions['badButtons']==0 and regions['oldInline']==0,(width,regions)
        page.set_viewport_size({'width':390,'height':844})
        page.locator('#stockRows .stock-row[data-buff-kind="splitshot"] button').nth(0).tap()
        expect(page.locator('#stockModeRail .stock-mode-card')).to_have_count(0)
        # Every row has the same quantity controls, not just a heading.
        assert rows.locator('input[type=number]').count()==len(keys)
        assert rows.locator('button').count()==3*len(keys)
        expect(page.get_by_role('spinbutton',name='巨型弹使用数量')).to_have_value('0')
        page.get_by_role('button',name='增加巨型弹').tap()
        expect(page.get_by_role('spinbutton',name='巨型弹使用数量')).to_have_value('1')
        page.get_by_role('button',name='减少巨型弹').tap()
        expect(page.get_by_role('spinbutton',name='巨型弹使用数量')).to_have_value('0')
        page.get_by_role('button',name='技能',exact=True).tap()
        expect(rows).to_have_count(10)
        page.get_by_role('button',name='防御加固选满').tap()
        expect(page.get_by_role('spinbutton',name='防御加固使用数量')).to_have_value('2')
        expect(page.get_by_role('spinbutton',name='核心修复使用数量')).to_have_value('0')
        page.get_by_role('button',name='清空',exact=True).tap()
        expect(page.get_by_role('spinbutton',name='防御加固使用数量')).to_have_value('0')
        assert page.evaluate('room.buffs[0].armor')==2
        page.get_by_role('button',name='全部',exact=True).tap()
        expect(rows).to_have_count(len(keys))
        # Wide and tall distributions must remain visible in the same frame.
        result=page.evaluate("""()=>{const pts=[[8,360,6],[952,-220,12],[480,20,8],...Array.from({length:29},(_,i)=>[25+i*31,100-i*5,8])];cameraGroup(pts,.016);
            const visible=pts.every(([x,y,r])=>Math.max(0,x-r)>=camera.x-1e-6&&Math.min(960,x+r)<=camera.x+VIEW_W+1e-6&&y-r>=camera.y-1e-6&&y+r<=camera.y+VIEW_H+1e-6);
            const wide=VIEW_W;for(let i=0;i<180;i++)cameraGroup([[440,100,8]],1/60);
            const near=VIEW_W;cameraHandoff({from:{...camera,w:VIEW_W},to:home(0)},1);
            return {visible,wide,near,home:VIEW_W,base:BASE_W}}""")
        assert result['visible'] and result['wide']<=960 and result['wide']>=950 and result['near']<result['wide'] and result['home']==result['base'],result
        assert page.evaluate("""()=>cameraShotPoints([{p:[10,20],radius:6,fragments:[[1,300,100]]},{p:[900,10],fragments:[[2,810,90]]}]).length""")==4
        assert page.evaluate("""()=>cameraWorldPoints([[1,800,300,90],[2,100,300,18]],[[1,780,300,100],[2,100,300,18]],[{id:1,kind:'core',w:44,h:44},{id:2,kind:'tnt',w:24,h:24,tntFuseStart:1}],.1,1.5).length""")==2
        # Replay the real generated 32-shell trajectory with the same camera helpers
        # used by frame(), including individual body motion, at a phone viewport.
        r2=g._siege_new('A','a',True,0,'classic','off',0,'stock')
        g._siege_v24_setup(r2)
        r2.update(mode='classic',phase='play',turn=0,until=0.)
        r2['bodies']=[b for b in r2['bodies'] if b['kind']=='core']
        r2['launchers']=[[235,368],[725,368]]
        r2['items']=[]
        sel={'splitshot':3,'repeat':3,'bounce':2,'tntdrop':2}
        r2['buffs'][0].update(sel)
        g._siege_fire(r2,75,55,sel,config=g._siege_public_config({}))
        event=r2['event']
        result=page.evaluate("""ev=>{
            const plan=cameraPlan(ev,[]),frames=ev.frames;let count=0,max=0,maxZoomRate=0,maxPan=0;
            for(let i=0;i<frames.length;i++){
                const f=frames[i],next=frames[Math.min(i+1,frames.length-1)],pts=cameraShotPoints([{p:f[1],fragments:f[3],radius:f[4]}]);
                if(!pts.length)continue;count++;max=Math.max(max,pts.length);
                const a=cameraPlanAt(plan,f[0]),b=cameraPlanAt(plan,next[0]),dt=Math.max(.001,next[0]-f[0]);
                maxZoomRate=Math.max(maxZoomRate,Math.abs(b.w-a.w)/dt);maxPan=Math.max(maxPan,Math.abs(b.x-a.x)/dt);
                for(const q of [0,.25,.5,.75,1]){
                    const t=f[0]+(next[0]-f[0])*q,c=cameraPlanAt(plan,t),h=c.w/ASPECT;
                    if(c.x<-.001||c.x+c.w>960.001||c.y+h>480.001)return {ok:false,reason:'boundary',c};
                    const points=pts.map(([x,y,r],j)=>{const id=j-(f[1]?1:0);const z=id<0?next[1]:next[3].find(z=>z[0]===f[3][id][0])?.slice(1);return [z?x+(z[0]-x)*q:x,z?y+(z[1]-y)*q:y,r]});
                    if(!points.every(([x,y,r])=>Math.max(0,x-r)>=c.x-.05&&Math.min(960,x+r)<=c.x+c.w+.05&&y-r>=c.y-.05&&Math.min(480,y+r)<=c.y+h+.05))return {ok:false,reason:'visibility',i,q,c,points};
                }
            }
            return {ok:true,count,max,maxZoomRate,maxPan}
        }""",event)
        assert result['ok'] and result['count']>5 and result['max']>=8,result
        assert result['maxZoomRate']<.001,result # fixed focal length
        assert page.evaluate("""()=>{const d={shellEnd:.1,handoffAt:1,playbackDuration:1.48,duration:6};return replayClock(d,.1)===.1&&replayClock(d,1)===1&&replayClock(d,1.48)===1.48}""")
        assert page.evaluate("""()=>compoundHint('ricochet').includes('弹跳 +1')&&compoundHint('seek').includes('制导 +1')&&compoundHint('siegebreak').includes('爆炸 +1')""")
        # A single shell traversing the map must actually pan; stationary debris
        # and late explosions must not change its camera plan or handoff.
        pan=page.evaluate("""()=>{const frames=Array.from({length:61},(_,i)=>[i/20,i<60?[60+i*14,220]:null,[],[],6,[]]);const ev={frames,hitAt:3,duration:3};const a=cameraPlan(ev,[]),b=cameraPlan({...ev,duration:9,frames:frames.concat([[9,null,[[1,930,300,100]],[],6,[]]]),behaviorEvents:[['bounceBlast',8,930,300,100]]},[{id:1,kind:'core'}]);return {pan:a.at(-1).x-a[0].x,zoom:new Set(a.map(c=>c.w)).size,same:JSON.stringify(a)===JSON.stringify(b)}}""")
        assert pan['pan']>300 and pan['zoom']==1 and pan['same'],pan
        page.evaluate("""()=>{room.buffs[0].compound=3;room.compoundRecipes=[['siegebreak','ricochet','ricochet'],[]];stockKey='';update()}""")
        page.get_by_role('button',name='全部',exact=True).tap()
        expect(page.locator('.compound-row .buff-effect').first).to_have_text('攻坚 · 穿透 +1 · 破甲 +1 · 爆炸 +1')
        assert page.locator('.compound-row .buff-effect').first.evaluate("e=>e.scrollHeight<=e.clientHeight+1")
        page.get_by_role('button',name='复合·爆跳选满').tap()
        page.get_by_role('button',name='增加复合·攻坚').tap()
        assert page.evaluate('selection')=={'compound:ricochet':2,'compound:siegebreak':1}
        page.get_by_role('button',name='清空',exact=True).tap()
        page.evaluate("""()=>{room.trial=true;room.compoundRecipes=[Object.keys(compoundLabels).flatMap(k=>[k,k,k]),[]];stockKey='';update()}""")
        expect(page.locator('.compound-row')).to_have_count(5)
        page.get_by_role('button',name='复合·爆跳选满').tap()
        expect(page.get_by_role('button',name='增加复合·追甲')).to_be_disabled()
        page.get_by_role('button',name='清空',exact=True).tap()
        page.evaluate("""()=>{room.trial=false;room.compoundRecipes=[['siegebreak','ricochet','ricochet'],[]];stockKey='';update()}""")
        print('Siege single shell pan and debris-independent plan:',pan)
        # Exercise the actual requestAnimationFrame renderer, not just the planner.
        # During preroll no projectile is visible; once playback starts every
        # rendered projectile stays inside the camera and the map stays bounded.
        real=page.evaluate("""async ev=>{
            closePanels();stockOpen=false;cameraSnap(home(0));overview=null;
            playing={event:ev,start:performance.now()+CAMERA_PREROLL*1000,handoff:null,cameraFrom:{...camera,w:VIEW_W}};
            const start=performance.now();let count=0,pre=0,fail=null,prior=null,maxJump=0;
            while(playing&&performance.now()-start<16000){
                await new Promise(requestAnimationFrame);
                if(!playing||!animFrame)continue;
                const elapsed=(performance.now()-playing.start)/1000;
                const w=VIEW_W,h=VIEW_H;
                if(camera.x<-.001||camera.x+w>960.001||camera.y+h>480.001){fail='map boundary';break}
                if(elapsed<0){pre++;if(animFrame[1]||animFrame[3]?.length){fail='premature projectile';break}continue}
                if(playing.handoff)continue;
                const pts=cameraShotPoints([{p:animFrame[1],fragments:animFrame[3],radius:animFrame[4]}]);
                if(pts.length){count++;if(!pts.every(([x,y,r])=>Math.max(0,x-r)>=camera.x-.6&&Math.min(960,x+r)<=camera.x+w+.6&&y-r>=camera.y-.6&&Math.min(480,y+r)<=camera.y+h+.6)){fail='projectile outside actual view';break}}
                if(prior)maxJump=Math.max(maxJump,Math.abs(w-prior));prior=w;
            }
            playing=null;animFrame=null;cameraSnap(home(0));return {count,pre,fail,maxJump}
        }""",event)
        assert not real['fail'] and real['count']>10 and real['pre']>0 and real['maxJump']<.001,real
        print('Siege camera rendered playback:',real)
        # Two actual public views of the cooperative game. Seat 1 must face
        # right, share the same core, and get the turn after seat 0 fires.
        coop=g._siege_new('A','a',True,8,'classic','off',0,'stock')
        g._siege_v24_setup(coop,'zombie');g._siege_field(coop);coop['code']='COOP01'
        g._siege_fire(coop,90,25,{},config=g._siege_public_config({}))
        d=g._siege_public(coop,'bot',coop['rev']);d['busy']=False
        page.evaluate('d=>{apply(d);overview=null;update()}',d)
        expect(page.locator('#coopCore')).to_be_visible()
        expect(page.locator('#coopCoreText')).to_have_text('共享子刊 100/100')
        expect(page.locator('#turn')).to_contain_text('轮到你')
        assert page.evaluate('muzzle(1,45,6)[0]>launcher(1)[0]')
        assert page.evaluate('room.bodies.filter(b=>b.kind==="zombie").length')==3
        g._siege_fire(coop,90,25,{},config=g._siege_public_config({}))
        d=g._siege_public(coop,'a',-1)
        page.evaluate('d=>{apply(d);overview=null;update()}',d)
        page.wait_for_function('playing===null',timeout=15000)
        assert not errors,errors
        print('Siege zombie coop real browser: shared core, seat 1 right-facing, enemy phase replay PASS')
        print('Siege camera actual replay coverage:',result)
        print('Siege camera: 32 targets, zoom contraction, both sides, moving core and lit TNT PASS')
        print('Siege v24 real browser: all 22 inventory rows rendered; uniform controls, filter, selection and cancel PASS')
        browser.close()
finally:
    s.shutdown()
