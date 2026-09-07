from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'], timeout=15000)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto((Path(__file__).resolve().parents[1] / 'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__ && window.__DRAW__.getState()')
    page.wait_for_timeout(100)
    def setup(extra=None, guides=None, zoom=1):
        page.evaluate('''({extra,guides,zoom}) => {
            const d=window.__DRAW__; d.clearCanvas();
            d.loadOutline({ paths:[{points:[{x:113,y:117},{x:180,y:193}]}, ...(extra || [])], guides:guides||[] });
            d.setZoom(zoom); const screen=d.worldToScreen(100,100); d.panBy(180-screen.x,180-screen.y); d.selectPoint(0,0); d.pushHistory();
        }''', dict(extra=extra, guides=guides, zoom=zoom))
    def screen(x,y):
        s=page.evaluate('([x,y])=>window.__DRAW__.worldToScreen(x,y)',[x,y])
        box=page.locator('#vectorCanvas').bounding_box()
        return box['x']+s['x'],box['y']+s['y']
    def drag(x,y,xx,yy):
        page.mouse.move(*screen(x,y)); page.mouse.down()
        page.mouse.move(*screen(xx,yy),steps=8); page.mouse.up()
    def point():
        return page.evaluate('window.__DRAW__.serializeOutline().paths[0].points[0]')
    setup()
    page.locator('#snapEnabled').check()
    assert page.evaluate('window.__DRAW__.snapPosition({x:244,y:137}).x') == 240
    drag(113,117,244,137)
    assert point()['x']==240 and point()['y']==137, point()
    page.keyboard.press('Control+z')
    assert point()['x']==113
    page.keyboard.press('Control+y')
    assert point()['x']==240
    page.locator('#snapEnabled').uncheck()
    drag(240,137,244,149)
    assert abs(point()['x']-244)<1e-6, point()
    setup(guides=[{'axis':'x','position':253}])
    page.locator('#snapEnabled').check()
    drag(113,117,257,149)
    assert point()['x']==253, point()
    setup(extra=[{'points':[{'x':267,'y':173},{'x':330,'y':220}]}])
    drag(113,117,270,175)
    assert point()['x']==267 and point()['y']==173, point()
    # Hidden paths do not attract anchors.
    setup(extra=[{'visible':False,'points':[{'x':267,'y':173},{'x':330,'y':220}]}])
    drag(113,117,270,175)
    assert point()['x']==270 and point()['y']==175, point()
    # Keep test anchors in view at different zooms and verify screen-pixel tolerance.
    for z in [.5,2]:
        setup(zoom=z)
        drag(113,117,240+5/z,137)
        assert point()['x']==240, (z, point())
        setup(zoom=z)
        drag(113,117,240+7/z,137)
        assert abs(point()['x']-(240+7/z))<1e-6, (z,point())
    # Pen insertion also uses snapped geometry.
    setup()
    page.evaluate("window.__DRAW__.clearCanvas(); window.__DRAW__.setMode('pen')")
    page.mouse.click(*screen(244,137))
    assert point()['x']==240, point()
    # A selected path translates rigidly without snapping to its own anchors.
    setup()
    page.evaluate("window.__DRAW__.setMode('select')")
    page.mouse.click(*screen(145,153))
    # Force select using the public API, then drag the middle of its stroke.
    page.evaluate('window.__DRAW__.selectPath(0)')
    before=page.evaluate('window.__DRAW__.serializeOutline().paths[0].points')
    drag(145,153,276,173)
    after=page.evaluate('window.__DRAW__.serializeOutline().paths[0].points')
    assert after[0]['x']==240, after
    assert abs((after[1]['x']-after[0]['x'])-(before[1]['x']-before[0]['x']))<1e-6
    setup()
    page.evaluate("window.__DRAW__.clearCanvas(); window.__DRAW__.setMode('rect')")
    drag(124,137,284,217)
    rectangle=page.evaluate('window.__DRAW__.serializeOutline().paths[0].points')
    assert rectangle[0]['x']==120 and rectangle[1]['x']==280, rectangle
    page.reload(); page.wait_for_timeout(150)
    assert page.locator('#snapEnabled').is_checked()
    assert not errors, errors
    print('PASS: grid on/off, guides, anchor targets, hidden targets excluded, 6-screen-pixel tolerance, undo/redo, pen placement, rigid path drag, preference reload; no browser errors.')
    browser.close()
