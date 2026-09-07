from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1194,'height':834},has_touch=True)
    page.set_default_timeout(10000)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((Path(__file__).resolve().parents[1]/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__')
    print('loaded',flush=True)
    page.evaluate('window.__DRAW__.clearCanvas(); window.__DRAW__.setZoom(1); window.__DRAW__.pushHistory()')
    page.locator('#toolPencil').click()
    def settings(key,value):
        page.locator('#pencil'+key).evaluate('(el,v)=>{el.value=v;el.dispatchEvent(new Event("input"))}',str(value))
    def event(kind,x,y=250,pressure=.5,typ='pen',pid=71):
        page.evaluate('''a=>{const c=document.querySelector('#vectorCanvas'),r=c.getBoundingClientRect(); c.dispatchEvent(new PointerEvent(a.kind,{bubbles:true,pointerId:a.pid,pointerType:a.typ,clientX:r.x+a.x,clientY:r.y+a.y,button:0,buttons:a.kind==='pointerup'?0:1,pressure:a.pressure}));}''',dict(kind=kind,x=x,y=y,pressure=pressure,typ=typ,pid=pid))
    def paths():return page.evaluate('window.__DRAW__.serializeOutline().paths')
    def stroke(pressure):
        event('pointerdown',150,pressure=pressure)
        for x in range(152,251,2):event('pointermove',x,250+(x%8),pressure)
        event('pointerup',250,pressure=0)
    settings('Pressure',100)
    stroke(.2); low=paths()[-1]['strokeWidth']
    # Reset base width so pressure comparison is against the same chosen width.
    page.locator('#strokeWidth').evaluate('el=>{el.value=2}')
    stroke(.8); high=paths()[-1]['strokeWidth']
    assert high>low,(low,high)
    before=paths()
    event('pointerdown',150);event('pointermove',190)
    event('pointerdown',350,typ='touch',pid=99);event('pointermove',450,typ='touch',pid=99);event('pointerup',450,typ='touch',pid=99)
    assert paths()==before
    event('pointermove',250);event('pointerup',250,pressure=0)
    assert len(paths())==len(before)+1
    event('pointerdown',150);event('pointermove',250);event('pointercancel',250)
    assert len(paths())==len(before)+1
    page.locator('#pencilUndo').click(); assert paths()==before
    page.locator('#pencilRedo').click(); assert len(paths())==len(before)+1
    settings('Touch','pan')
    cam=page.evaluate('window.__DRAW__.getState().camera.x')
    event('pointerdown',150,typ='touch');event('pointermove',230,typ='touch');event('pointerup',230,typ='touch')
    assert page.evaluate('window.__DRAW__.getState().camera.x')==cam+80
    settings('Smoothing',0);stroke(.5); detailed=len(paths()[-1]['points'])
    settings('Smoothing',100);stroke(.5); smooth=len(paths()[-1]['points'])
    assert smooth<detailed,(smooth,detailed)
    page.locator('#toggleInspector').click();assert not page.locator('.inspector').is_visible()
    page.locator('#toggleInspector').click();assert page.locator('.inspector').is_visible()
    page.wait_for_timeout(600);page.reload();page.wait_for_function('window.__DRAW__')
    assert page.evaluate('window.__DRAW__.getState().pencilPrefs.pressure')==100
    assert page.evaluate('window.__DRAW__.getState().pencilPrefs.touch')=='pan'
    page.set_viewport_size({'width':834,'height':1194})
    page.screenshot(path='/tmp/draw-pencil-portrait.png')
    assert page.locator('#vectorCanvas').bounding_box()['width']>250
    assert not errors,errors
    print(f'PASS: pressure widths {low} → {high}; smoothing anchors {detailed} → {smooth}; palm ignored; cancel/undo/redo; finger pan +80px; inspector toggle; reload settings; tablet portrait.')
    browser.close()
