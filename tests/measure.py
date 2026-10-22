"""Measure gestures are exact, zoom independent, cancellable and read-only."""
from pathlib import Path
from math import isclose
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__ && window.drawDocumentReady')
    page.evaluate("""__DRAW__.clearCanvas();__DRAW__.loadOutline({paths:[{points:[{x:120,y:120},{x:300,y:360}],locked:true},{points:[{x:450,y:100},{x:570,y:260}],visible:false}]});camera={x:40,y:40,scale:1};hideNodes=true;pushHistory();draw()""")
    def coords(x,y):
        return page.evaluate('([x,y])=>{const s=screenFromWorld({x,y}),r=canvas.getBoundingClientRect();return [r.x+s.x,r.y+s.y]}',[x,y])
    def info():return page.evaluate('__DRAW__.getState().measurement')
    def document():return page.evaluate('(()=>{const data=serializeOutline();delete data.savedAt;return JSON.stringify(data)})()')
    def drag(a,b):
        page.mouse.move(*coords(*a));page.mouse.down();page.mouse.move(*coords(*b),steps=8);page.mouse.up()
    before=document();history=page.evaluate('JSON.stringify(history)')
    page.locator('#toolMeasure').click()
    assert page.locator('#measureReadout').is_visible()
    # Near-node clicks resolve to exact anchors, even on locked artwork.
    page.mouse.click(*coords(123,122));page.mouse.move(*coords(303,362))
    assert info()['complete'] is False and info()['distance']==300,info()
    page.mouse.click(*coords(303,362))
    m=info();assert m['complete'] and m['distance']==300 and m['dx']==180 and m['dy']==240,m
    assert m['a']['snapped'] and m['b']['snapped']
    assert '300.00 px' in page.locator('#measureValue').inner_text()
    assert document()==before and page.evaluate('JSON.stringify(history)')==history
    # Modifiers recompute from the original start, even with a stationary pointer.
    page.mouse.move(*coords(450,400));page.mouse.down();page.mouse.move(*coords(550,420))
    radius=(100**2+20**2)**0.5
    page.keyboard.down('Shift');m=info()
    assert isclose(m['dy'],0,abs_tol=1e-8) and isclose(m['distance'],radius) and m['constrained'],m
    page.keyboard.down('Alt');m=info()
    assert isclose(m['distance'],2*radius) and m['centred'],m
    assert isclose((m['a']['x']+m['b']['x'])/2,450) and m['a']['y']==400,m
    page.keyboard.up('Shift');m=info()
    assert m['a']['x']==350 and m['a']['y']==380 and m['b']['x']==550 and m['b']['y']==420,m
    page.keyboard.up('Alt');m=info()
    assert m['a']['x']==450 and m['a']['y']==400 and isclose(m['distance'],radius),m
    # Combined modifiers persist in the committed result after the keys are released.
    page.keyboard.down('Shift');page.keyboard.down('Alt');page.mouse.up()
    committed=info();assert committed['complete'] and isclose(committed['distance'],2*radius)
    page.keyboard.up('Alt');page.keyboard.up('Shift');assert info()==committed
    # Two-click mode also supports a centred measurement.
    page.mouse.click(*coords(450,400));page.mouse.move(*coords(550,420))
    page.keyboard.down('Alt');page.mouse.click(*coords(550,420));page.keyboard.up('Alt')
    m=info();assert m['complete'] and m['a']['x']==350 and m['a']['y']==380,m
    # A constrained line must not claim it snapped to an off-axis node.
    page.mouse.move(*coords(120,120));page.mouse.down();page.keyboard.down('Shift')
    page.mouse.move(*coords(300,360));page.mouse.up();page.keyboard.up('Shift')
    m=info();assert isclose(m['dx'],m['dy']) and isclose(m['distance'],300) and not m['b']['snapped'],m
    page.keyboard.press('Escape')
    assert document()==before and page.evaluate('JSON.stringify(history)')==history
    # Hidden nodes do not snap; dragging uses world coordinates.
    drag((453,102),(573,262));m=info()
    assert isclose(m['distance'],200) and not m['a']['snapped'] and not m['b']['snapped'],m
    page.evaluate('camera.scale=2;draw()')
    drag((120,120),(300,360));assert info()['distance']==300
    # Result remains constant while panning; measurement isn't exported.
    page.keyboard.down('Space');drag((180,180),(200,200));page.keyboard.up('Space')
    assert info()['distance']==300 and info()['complete']
    page.evaluate("documentSettings.units='mm';documentSettings.dpi=300;draw()")
    assert isclose(info()['distance'],25.4)
    assert '25.40 mm' in page.locator('#measureValue').inner_text()
    page.evaluate("documentSettings.units='in';draw()")
    assert info()['distance']==1
    page.keyboard.press('Escape');assert info() is None
    # Cancellation and switching tools discard incomplete measurements.
    page.mouse.move(*coords(120,120));page.mouse.down();page.mouse.move(*coords(160,140))
    page.locator('#viewport').dispatch_event('pointercancel',{'pointerId':1,'pointerType':'mouse'})
    page.mouse.up();assert info() is None
    page.mouse.click(*coords(120,120));page.keyboard.press('v')
    assert info() is None and page.locator('#measureReadout').is_hidden()
    page.keyboard.press('k');assert page.evaluate('__DRAW__.getState().mode')=='measure'
    # Zero-length measurement is finite. Two taps finish without adding a path.
    page.mouse.click(*coords(120,120));page.mouse.click(*coords(120,120))
    assert info()['distance']==0 and info()['complete']
    # Pen and touch draw mode use the same routed gestures.
    page.evaluate("camera={x:40,y:40,scale:1};documentSettings.units='px';pencilPrefs.touch='draw';draw()")
    for kind in ('pen','touch'):
        page.keyboard.press('Escape')
        for name,point,buttons in [('pointerdown',(120,120),1),('pointermove',(300,360),1),('pointerup',(300,360),0)]:
            x,y=coords(*point)
            page.locator('#vectorCanvas').dispatch_event(name,{'pointerId':9,'pointerType':kind,'clientX':x,'clientY':y,'button':0,'buttons':buttons,'isPrimary':True})
        assert info()['complete'] and info()['distance']==300,(kind,info())
    # Reload / new document never retain a stale ruler.
    page.evaluate('newDocument()');assert info() is None
    page.evaluate("__DRAW__.loadOutline({paths:[{points:[{x:120,y:120},{x:300,y:360}]}]});camera={x:40,y:40,scale:1};setMode('measure');draw()")
    drag((120,120),(300,360))
    page.screenshot(path=str(ROOT/'planning/measure.png'))
    page.evaluate('restoreSnapshot(history[0])');assert info() is None
    assert not errors,errors
    browser.close()
print('PASS: Shift 45°, Alt centred, combined, live key changes, commit retention, unchanged history; node clicks 300 px; free drag 200 px; zoom/pan invariant; 25.4 mm / 1 in at 300 DPI; zero, cancel, tool switch, pen/touch; unchanged document/history; reset clears')
