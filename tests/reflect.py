"""Reflection through real panel controls: geometry, copies, paint and history."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.__DRAW_PANELS__')
    def setup():
        page.evaluate('''() => { __DRAW__.clearCanvas(); __DRAW__.loadOutline({paths:[
            {name:'Curve',closed:true,enableFill:true,fill:'#ff0000',stroke:'#000000',strokeWidth:3,points:[
                {x:100,y:100,cp1:{x:80,y:70},cp2:{x:130,y:120},hasHandles:true},
                {x:200,y:150},{x:120,y:220}]},
            {name:'Other',closed:true,enableFill:true,fill:'#0000ff',points:[{x:300,y:100},{x:400,y:100},{x:350,y:200}]}
        ]}); __DRAW__.selectPath(0); pushHistory(); }''')
        page.locator('#reflectCustom').uncheck();page.locator('#reflectCopy').uncheck()
    state=lambda:page.evaluate('serializeOutline().paths')
    click=lambda axis:page.locator('[data-reflect="'+axis+'"]').click()
    setup();before=state();click('x');after=state()
    assert after[0]['points'][0]['x']==200
    assert after[0]['points'][0]['cp1']=={'x':220,'y':70}
    assert after[0]['points'][0]['cp2']=={'x':170,'y':120}
    assert after[1]==before[1] and after[0]['strokeWidth']==3
    assert after[0]['fill']=='#ff0000' and after[0]['closed']
    page.keyboard.press('Control+z');assert state()==before
    page.keyboard.press('Control+y');assert state()==after
    page.evaluate('__DRAW__.selectPath(0)');click('x');assert state()==before,'double reflection restores geometry'
    click('y');assert state()[0]['points'][0]['y']==220
    assert state()[0]['points'][0]['cp1']=={'x':80,'y':250}
    # Multi-path reflection uses a shared centre, preserving relative spacing and groups.
    setup();page.evaluate('__DRAW__.selectPaths([0,1]);groupSelection()');before=state();click('x')
    assert [v['points'][0]['x'] for v in state()]==[400,200]
    assert state()[0]['groupId']==state()[1]['groupId']
    # Copy across a custom negative/decimal coordinate, remapping group membership.
    page.keyboard.press('Control+z');page.evaluate('__DRAW__.selectPath(0)')
    page.locator('#reflectCustom').check();page.locator('#reflectCoordinate').fill('-25.5');page.locator('#reflectCopy').check();click('x')
    copied=state();assert len(copied)==4 and copied[:2]==before
    assert copied[2]['points'][0]['x']==-151 and copied[3]['points'][0]['x']==-351
    assert copied[2]['groupId']==copied[3]['groupId'] and copied[2]['groupId']!=copied[0]['groupId']
    assert page.evaluate('pathSelection().length')==2
    page.keyboard.press('Control+z');assert state()==before
    page.keyboard.press('Control+y');assert state()==copied
    page.wait_for_timeout(1200);page.reload();page.wait_for_function('window.__DRAW_PANELS__');assert state()==copied
    # Mirror both gradient directions; colours, stops, dashes and joins are preserved.
    setup();page.evaluate('''() => { Object.assign(paths[0],{fillType:'linear',strokeType:'linear',strokeDash:[4,2],strokeJoin:'bevel',
        gradient:normalizeGradient({x1:0.1,y1:0.2,x2:0.8,y2:0.9,stops:[{offset:0,color:'#ff0000'},{offset:1,color:'#0000ff'}]}),
        strokeGradient:normalizeGradient({x1:0,y1:0,x2:1,y2:1,stops:[{offset:0,color:'#00ff00'},{offset:1,color:'#ffffff'}]})});pushHistory(); }''')
    before=state();click('x');mirrored=state()[0]
    assert mirrored['gradient']['x1']==0.9 and abs(mirrored['gradient']['x2']-0.2)<1e-12
    assert mirrored['strokeGradient']['x1']==1 and mirrored['strokeGradient']['x2']==0
    assert mirrored['gradient']['stops']==before[0]['gradient']['stops']
    assert mirrored['strokeDash']==[4,2] and mirrored['strokeJoin']=='bevel'
    click('y');assert abs(state()[0]['gradient']['y2']-0.1)<1e-12
    svg=page.evaluate('generateSVGString()');assert 'linearGradient' in svg and 'stroke-dasharray="4 2"' in svg
    page.keyboard.press('Control+z');page.keyboard.press('Control+z');assert state()==before
    # Inline failures are atomic and do not add undo entries.
    for mutate,message in [('deselect()','Select'),('paths[0].locked=true','unlocked'),('paths[0].visible=false','visible')]:
        setup();page.evaluate(mutate);before=state();hist=page.evaluate('history.length');click('x')
        assert state()==before and page.evaluate('history.length')==hist
        assert message in page.locator('#reflectStatus').inner_text()
    setup();page.locator('#reflectCustom').check();before=state();hist=page.evaluate('history.length')
    for value in ['', '10000001']:
        page.locator('#reflectCoordinate').fill(value);click('x');assert state()==before and page.evaluate('history.length')==hist
    # Compound contours remain distinct; reflected text recipes are intentionally cleared.
    setup();page.evaluate("paths[0].points[2].moveTo=true;paths[0].textRecipe={text:'Source',font:'DejaVu Sans',size:64};pushHistory()")
    click('x');assert state()[0]['points'][2]['moveTo'] and page.evaluate('paths[0].textRecipe') is None
    page.keyboard.press('Control+z');assert page.evaluate('paths[0].textRecipe!==null')
    page.evaluate('__DRAW__.clearCanvas()')
    page.locator('#textContent').fill('Reflect');page.locator('#textInsert').click()
    before=state();assert before[0]['textRecipe']['text']=='Reflect'
    click('x');assert state()[0]['textRecipe'] is None and len(state()[0]['points'])==len(before[0]['points'])
    assert page.locator('#textUpdate').is_disabled()
    page.keyboard.press('Control+z');assert state()==before
    # A one-anchor path stays finite even with zero-size selection bounds.
    setup();page.evaluate('paths[0].points=paths[0].points.slice(0,1);pushHistory()');click('x')
    assert state()[0]['points'][0]['x']==100 and state()[0]['points'][0]['cp1']['x']==120
    page.locator('[data-panel="reflect"]').screenshot(path='/tmp/open-vector-reflect.png')
    assert not errors,errors
    browser.close()
    print('PASS: horizontal/vertical geometry and handles, double reflection, shared centre, custom coordinate, copies/groups, undo/redo/reload, gradients/SVG, atomic rejection, compound and zero-size paths')
