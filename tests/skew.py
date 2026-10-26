"""Skew actual controls: coordinates, compound curves, clip members and history."""
from pathlib import Path
from math import isclose, tan, radians
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri()); page.wait_for_function('window.__DRAW_PANELS__')
    def state(): return page.evaluate('__DRAW__.serializeOutline().paths')
    def setup():
        page.evaluate('''() => { __DRAW__.clearCanvas(); __DRAW__.loadOutline({paths:[
            {name:'Curve',closed:true,fill:'#ff0000',enableFill:true,stroke:'#000000',strokeWidth:3,points:[
                {x:100,y:100,cp1:{x:80,y:70},cp2:{x:130,y:120},hasHandles:true},
                {x:200,y:100},{x:200,y:200},{x:100,y:200}]},
            {name:'Other',closed:true,points:[{x:300,y:100},{x:400,y:100},{x:350,y:200}]}
        ]}); __DRAW__.selectPath(0); pushHistory(); }''')
    def click(axis='x', degrees='45'):
        page.locator('#skewAngle').fill(degrees)
        page.locator('[data-skew="'+axis+'"]').click()
    def check(before, after, axis, centre, degrees):
        other = 'y' if axis == 'x' else 'x'
        assert len(before['points']) == len(after['points'])
        for a,b in zip(before['points'],after['points']):
            for pa,pb in [(a,b),(a['cp1'],b['cp1']),(a['cp2'],b['cp2'])]:
                assert isclose(pb[axis],pa[axis]+tan(radians(degrees))*(pa[other]-centre),abs_tol=1e-8)
                assert pb[other] == pa[other]
    setup(); before=state(); click(); after=state()
    check(before[0], after[0], 'x', 150, 45)
    assert after[1] == before[1] and after[0]['strokeWidth'] == 3
    assert isclose(after[0]['points'][0]['x'],50) and isclose(after[0]['points'][0]['cp1']['x'],0,abs_tol=1e-8)
    page.keyboard.press('Control+z'); assert state() == before
    page.keyboard.press('Control+y'); assert state() == after
    page.wait_for_timeout(500); page.reload(); page.wait_for_function('window.__DRAW_PANELS__'); assert state() == after
    page.evaluate('__DRAW__.selectPath(0)'); click('x','-45')
    for a,b in zip(state()[0]['points'],before[0]['points']):
        assert isclose(a['x'],b['x'],abs_tol=1e-8)
    setup(); before=state(); click('y','-22.5'); check(before[0],state()[0],'y',150,-22.5)
    # A shared pivot preserves selected arrangements and group membership.
    setup(); page.evaluate('__DRAW__.selectPaths([0,1]); groupSelection()'); before=state(); click('y')
    for a,b in zip(before,state()): check(a,b,'y',250,45)
    assert state()[0]['groupId'] == state()[1]['groupId'] == before[0]['groupId']
    # Clipped artwork is transformed together even if just its mask is selected.
    setup(); page.evaluate("paths.forEach(p=>p.clipId='test-clip');paths[1].clipMask=true;__DRAW__.selectPath(1);pushHistory()")
    before=state(); click()
    for a,b in zip(before,state()): check(a,b,'x',150,45)
    assert state()[1]['clipMask'] and state()[0]['clipId'] == 'test-clip'
    page.keyboard.press('Control+z'); assert state()==before
    # Atomic rejection: empty, locked/hidden member, invalid angles, zero and overflow.
    for change in ['deselect()', 'paths[0].locked=true', 'paths[0].visible=false',
                   "paths.forEach(p=>p.clipId='guard');paths[1].locked=true"]:
        setup(); page.evaluate(change); before=state(); history=page.evaluate('history.length'); click()
        assert state()==before and page.evaluate('history.length')==history, (change, page.locator('#skewStatus').inner_text(),state(),before)
        page.evaluate('pointerDown=false')
    setup(); before=state(); history=page.evaluate('history.length')
    assert page.evaluate("() => { pointerDown=true; const result=skewSelection('x',45); pointerDown=false; return result; }") is False
    assert state()==before and page.evaluate('history.length')==history
    for angle in ['', '86', '-86', '0']:
        click(degrees=angle); assert state()==before and page.evaluate('history.length')==history
    page.evaluate('paths[0].points[0].x=9999999'); before=state(); click(degrees='-85'); assert state()==before
    setup(); page.evaluate('paths[0].points=paths[0].points.slice(1,2);pushHistory()')
    before=state(); history=page.evaluate('history.length'); click(); assert state()==before and page.evaluate('history.length')==history
    # Contours and appearance recipes survive; text recipe is invalidated and undoable.
    setup(); page.evaluate('''() => { Object.assign(paths[0], {fillType:'linear',strokeType:'linear',
        gradient:normalizeGradient({}),strokeGradient:normalizeGradient({}),strokeDash:[4,2],
        effects:{blur:{type:'gaussian',radius:2}}}); paths[0].points[2].moveTo=true;pushHistory(); }''')
    before=state(); click(); after=state()
    for key in ['gradient','strokeGradient','strokeDash','effects','fill','fillRule']:
        assert after[0][key]==before[0][key]
    assert after[0]['points'][2]['moveTo']
    svg=page.evaluate('__DRAW__.generateSVGString()'); assert 'linearGradient' in svg and '<path' in svg
    # JSON round trip retains all transformed data.
    page.evaluate('__DRAW__.loadOutline(__DRAW__.serializeOutline())'); assert state()==after
    with page.expect_download() as download: page.evaluate('__DRAW__.exportPNG()')
    assert Path(download.value.path()).stat().st_size > 100
    page.evaluate('__DRAW__.clearCanvas()'); page.locator('#textContent').fill('Skew'); page.locator('#textInsert').click()
    before=state(); assert before[0]['textRecipe']
    click(); assert state()[0]['textRecipe'] is None and page.locator('#textUpdate').is_disabled()
    page.keyboard.press('Control+z'); assert state()==before
    # The generated Tools entry reveals Skew, with keyboard-operable buttons.
    page.evaluate("__DRAW__.selectPath(0); __DRAW_PANELS__.show('skew','skewAngle')")
    page.locator('#skewAngle').fill('15'); page.keyboard.press('Tab'); page.keyboard.press('Enter')
    assert state()[0]['textRecipe'] is None
    page.set_viewport_size({'width':768,'height':1024})
    page.locator('[data-panel="skew"]').screenshot(path='/tmp/open-vector-skew.png')
    assert not errors,errors
    print('PASS: anchor X 100→50 and handle X 80→0; horizontal/vertical/fractional skew, groups/clips, history/reload/JSON, SVG/PNG, guards, compounds, appearance, text and keyboard.')
    browser.close()
