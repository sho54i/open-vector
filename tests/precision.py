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
    def setup(paths):
        page.evaluate('''paths => { const d=window.__DRAW__; d.clearCanvas();
            d.loadOutline({paths}); d.setZoom(1); d.pushHistory(); }''', paths)
    def document():
        return page.evaluate('window.__DRAW__.serializeOutline()')
    def first():
        return document()['paths'][0]['points'][0]
    def framed(points):
        return page.evaluate('''points => {
            const d=window.__DRAW__, c=document.querySelector('#vectorCanvas').getBoundingClientRect();
            return points.every(p => { const s=d.worldToScreen(p.x,p.y); return s.x>=69 && s.y>=69 && s.x<=c.width-47 && s.y<=c.height-47; });
        }''', points)
    setup([{'points':[{'x':100,'y':100,'cp1':{'x':20,'y':10},'cp2':{'x':100,'y':-180},'hasHandles':True},{'x':220,'y':170}]}])
    page.evaluate('window.__DRAW__.selectPath(0)')
    before=document()['camera']
    page.locator('[data-menu="view"] .menu-item').click()
    page.locator('[data-cmd="zoomSelection"]').click()
    assert document()['camera']['scale']!=before['scale']
    assert framed([{'x':20,'y':10},{'x':100,'y':-180},{'x':220,'y':170}])
    assert page.locator('#propX').is_disabled()
    # Multi-path union via keyboard command, including a line of zero height.
    setup([{'points':[{'x':-200,'y':-100},{'x':-100,'y':0}]},{'points':[{'x':600,'y':300},{'x':700,'y':300}]}])
    page.evaluate('window.__DRAW__.selectAllPaths()')
    page.locator('#viewport').focus(); page.keyboard.press('Control+2')
    assert framed([{'x':-200,'y':-100},{'x':700,'y':300}])
    page.evaluate('window.__DRAW__.deselect()')
    before=document()['camera']
    assert page.evaluate('window.__DRAW__.zoomToSelection()') is False
    assert document()['camera']==before
    setup([{'points':[{'x':100,'y':100}]}])
    page.evaluate('window.__DRAW__.selectPath(0); window.__DRAW__.zoomToSelection()')
    assert framed([{'x':100,'y':100}])
    # Exact typed coordinates preserve both handle offsets and all other anchors.
    setup([{'points':[{'x':100,'y':100,'cp1':{'x':80,'y':70},'cp2':{'x':120,'y':130},'hasHandles':True},{'x':220,'y':170}]}])
    page.evaluate('window.__DRAW__.selectPoint(0,0); window.__DRAW__.setSnapping(true)')
    assert page.locator('#propX').input_value()=='100'
    assert page.evaluate("window.__DRAW__.setAnchorCoordinate('x', 400)")
    assert first()['x']==400
    page.locator('#viewport').focus(); page.keyboard.press('Control+z')
    assert first()['x']==100
    page.evaluate('window.__DRAW__.selectPoint(0,0)')
    page.locator('#propX').fill('400'); page.locator('#propX').press('Enter')
    assert page.evaluate('window.__DRAW__.getState().selected.x')==400
    assert first()['cp1']['x']==380 and first()['cp2']['x']==420
    assert document()['paths'][0]['points'][1]['x']==220
    page.keyboard.press('Control+z'); assert first()['x']==100
    page.keyboard.press('Control+y'); assert first()['x']==400
    page.evaluate('window.__DRAW__.selectPoint(0,0)')
    page.locator('#propY').fill('-12.75'); page.locator('#propY').press('Tab')
    assert first()['y']==-12.75 and first()['cp1']['y']==-42.75
    page.locator('#propX').fill('417.125'); page.locator('#propX').press('Enter')
    assert first()['x']==417.125
    page.locator('#propX').fill('99'); page.locator('#propX').press('Escape')
    assert first()['x']==417.125 and page.locator('#propX').input_value()=='417.125'
    page.locator('#propX').fill(''); page.locator('#propX').press('Enter')
    assert first()['x']==417.125
    page.evaluate('window.__DRAW__.lockPath(0,true); window.__DRAW__.selectPoint(0,0)')
    assert page.locator('#propX').is_disabled()
    assert page.evaluate("window.__DRAW__.setAnchorCoordinate('x',10)") is False
    assert first()['x']==417.125
    page.wait_for_timeout(350); page.reload(); page.wait_for_timeout(150)
    assert first()['x']==417.125 and first()['y']==-12.75
    assert not errors, errors
    print('PASS: menu/keyboard zoom, curve and multi-path framing, empty/one-point selection, exact X/Y edits, handle translation, undo/redo, negative/decimal values, Escape/invalid input, locked anchor protection, reload; no browser errors.')
    browser.close()
