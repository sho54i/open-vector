"""Document setup, anchor tools and modifier gesture outcomes."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.drawDocumentReady')
    def control(selector):
        if selector.startswith(('#document','#cmyk','#applyCMYK')):
            if not page.locator('[data-menu="file"]').evaluate("e=>e.classList.contains('open')"):
                page.locator('[data-menu="file"] .menu-item').click()
            page.locator('#documentMenuTrigger').hover()
        return page.locator(selector)
    def anchor(mode):
        page.locator('#toolPen').hover();page.mouse.down();page.wait_for_timeout(500);page.mouse.up()
        page.locator('[data-pen-mode="'+mode+'"]').click()
    def setup():
        page.evaluate("__DRAW__.clearCanvas();__DRAW__.loadOutline({paths:[{closed:true,enableFill:true,fill:'#ff0000',points:[{x:100,y:100},{x:200,y:100},{x:200,y:200},{x:100,y:200}]}]});__DRAW__.selectPath(0);camera={x:50,y:50,scale:1};showGrid=false;pushHistory();draw();")
    state=lambda:page.evaluate('serializeOutline()')
    def coords(x,y):
        return page.evaluate('([x,y])=>{const s=screenFromWorld({x,y}),r=canvas.getBoundingClientRect();return [s.x+r.x,s.y+r.y]}',[x,y])
    def click(x,y):page.mouse.click(*coords(x,y))
    def drag(a,b,keys=[]):
        for k in keys:page.keyboard.down(k)
        page.mouse.move(*coords(*a));page.mouse.down();page.mouse.move(*coords(*b),steps=6);page.mouse.up()
        for k in keys:page.keyboard.up(k)
    def blur():page.locator('#viewport').focus()
    setup();original=state()['paths']
    control('#documentName').fill('Print study');control('#documentMode').select_option('cmyk')
    control('#documentDpi').fill('300');control('#documentUnits').select_option('in')
    control('#documentWidth').fill('6');control('#documentHeight').fill('4')
    control('#documentForm button').click()
    d=state();assert d['document']=={'name':'Print study','colourMode':'cmyk','units':'in','dpi':300},d['document']
    assert d['artboard']['w']==1800 and d['artboard']['h']==1200 and d['paths']==original
    blur();page.keyboard.press('Control+z');assert state()['document']['colourMode']=='rgb'
    page.keyboard.press('Control+y');assert state()['document']==d['document']
    page.evaluate('__DRAW__.selectPath(0)');control('#cmykC').fill('100');control('#applyCMYK').click();assert state()['paths'][0]['fill']=='#00ffff'
    control('#cmykK').fill('100');control('#applyCMYK').click();assert state()['paths'][0]['fill']=='#000000'
    control('#cmykK').fill('101');before=state()['paths'];control('#applyCMYK').click();assert state()['paths']==before
    page.wait_for_timeout(400);saved=state();page.reload();page.wait_for_function('window.drawDocumentReady');assert state()['document']==saved['document'] and state()['paths']==saved['paths']
    page.evaluate('newDocument()');assert state()['document']['colourMode']=='rgb'
    page.evaluate('loadOutline('+__import__('json').dumps(saved)+')');assert state()['document']==saved['document']
    # Explicit anchor tools operate on real canvas clicks, retaining curvature when splitting.
    setup();anchor('anchor-add');click(150,100)
    assert len(state()['paths'][0]['points'])==5
    point=state()['paths'][0]['points'][1]
    anchor('anchor-convert');click(point['x'],point['y']);assert state()['paths'][0]['points'][1]['hasHandles']
    click(point['x'],point['y']);assert not state()['paths'][0]['points'][1]['hasHandles']
    anchor('anchor-remove');click(point['x'],point['y']);assert len(state()['paths'][0]['points'])==4
    page.keyboard.press('Control+z');assert len(state()['paths'][0]['points'])==5
    page.keyboard.press('Control+y');assert len(state()['paths'][0]['points'])==4
    click(100,100);assert len(state()['paths'][0]['points'])==3
    click(200,100);assert len(state()['paths'][0]['points'])==3
    page.evaluate('paths[0].locked=true');before=state()['paths'];click(200,100);assert state()['paths']==before
    setup();page.evaluate('paths=[makeEllipsePath(100,100,100,100)];setPathSelection(paths);pushHistory();draw()')
    curve=page.evaluate('cubicPoint(paths[0].points[0],paths[0].points[1],0.5)')
    anchor('anchor-add');click(curve['x'],curve['y']);points=state()['paths'][0]['points'];assert len(points)==5 and points[1]['hasHandles']
    assert abs(points[1]['x']-curve['x'])<0.1 and abs(points[1]['y']-curve['y'])<0.1
    # Alt copy is one history action; click alone must not duplicate.
    setup();drag((150,150),(230,180),['Alt']);v=state()['paths'];assert len(v)==2 and v[0]['points'][0]['x']==100 and v[1]['points'][0]['x']==180,v
    page.keyboard.press('Control+z');assert len(state()['paths'])==1
    page.keyboard.press('Control+y');assert len(state()['paths'])==2
    setup();page.keyboard.down('Alt');click(150,150);page.keyboard.up('Alt');assert len(state()['paths'])==1
    # Shift drag stays horizontally aligned even with a diagonal pointer delta.
    setup();drag((150,150),(210,170),['Shift']);v=state()['paths'][0]['points'][0];assert v['x']==160 and v['y']==100,v
    # Alt scale around centre; Shift keeps aspect ratio.
    setup();drag((200,200),(250,230),['Alt','Shift']);v=state()['paths'][0]['points'];assert v[0]['x']==50 and v[0]['y']==50 and v[2]['x']==250 and v[2]['y']==250,v
    # Pen Shift placement and handles snap to 45-degree rays.
    page.evaluate('newDocument();camera={x:50,y:50,scale:1};setMode("pen");draw()');click(100,100)
    page.keyboard.down('Shift');click(200,112);page.keyboard.up('Shift');pts=state()['paths'][0]['points'];assert abs(pts[1]['y']-100)<1e-6,pts
    # Ctrl+F uses the consolidated Paste in Front command, at the top of the stack.
    setup();page.evaluate("copySelection();const p=makeRectPath(300,300,50,50);p.name='top';paths.push(p);pushHistory();draw()")
    blur();page.keyboard.press('Control+f');v=state()['paths'];assert len(v)==3 and v[2]['points']==v[0]['points'] and v[1]['name']=='top'
    # Fields retain native Ctrl+F behavior and don't edit the drawing.
    control('#documentName').focus();page.keyboard.press('Control+f');assert len(state()['paths'])==3
    # Cancel an actual copy gesture; grouped copies must receive independent group IDs.
    setup();page.keyboard.down('Alt');page.mouse.move(*coords(150,150));page.mouse.down();page.mouse.move(*coords(230,180),steps=4)
    assert len(state()['paths'])==2
    page.evaluate("endPointer({type:'pointercancel'})");page.mouse.up();page.keyboard.up('Alt');assert len(state()['paths'])==1
    setup();page.evaluate("paths[0].groupId=90;const p=makeRectPath(250,100,80,80);p.groupId=90;paths.push(p);__DRAW__.selectPaths([0,1]);pushHistory();draw()")
    drag((150,150),(180,180),['Alt']);v=state()['paths'];assert len(v)==4 and v[2]['groupId']==v[3]['groupId']!=90
    assert v[0]['points'][0]['x']==100 and v[2]['points'][0]['x']==130
    # Compound removal preserves contour boundaries, including removing its first anchor.
    setup();page.evaluate("const a=makeRectPath(100,100,100,100),b=makeRectPath(125,125,50,50);setPathContours(a,[a.points,b.points]);paths=[a];setPathSelection(paths);pushHistory();draw()")
    anchor('anchor-remove');click(125,125)
    assert page.evaluate('pathContours(paths[0]).map(c=>c.length)')==[4,3]
    # A-mode Shift handle drag locks its angle and preserves the anchor position.
    setup();page.evaluate('__DRAW__.convertPoint(0,0);__DRAW__.selectPoint(0,0);draw()')
    h=state()['paths'][0]['points'][0]['cp2'];drag((h['x'],h['y']),(160,110),['Shift'])
    v=state()['paths'][0]['points'][0];assert v['x']==100 and v['y']==100 and abs(v['cp2']['y']-100)<1e-6,v
    # Invalid setup leaves the document intact; artwork merge preserves document settings.
    control('#documentWidth').fill('100001');before=state();control('#documentForm button').click()
    assert state()['artboard']==before['artboard'] and state()['document']==before['document']
    page.evaluate("documentSettings={name:'Keep',colourMode:'cmyk',units:'mm',dpi:300};loadOutline({document:{name:'Replace'},paths:[{points:[{x:1,y:1},{x:2,y:2}]}]},{merge:true})")
    assert state()['document']['name']=='Keep'
    assert not errors,errors
    page.set_viewport_size({'width':768,'height':1024});control('#documentForm').scroll_into_view_if_needed();page.wait_for_timeout(2600);page.screenshot(path=str(Path('/tmp/open-vector-document-setup.png')))
    # Upgrade a saved roadmap without losing custom cards or duplicating these three.
    page.goto((ROOT/'ROADMAP.html').as_uri())
    page.evaluate("localStorage.setItem('eve-roadmap-v1',JSON.stringify({version:39,cards:[{id:'custom',title:'Keep me',status:'queued'}],inbox:[]}))")
    page.reload()
    cards=page.evaluate('state.cards');seeds={c['id']:c for c in page.evaluate('SEED_CARDS')}
    for id in ['ct8ebh0i','cjriuz69','c46iw5mp']:
        matches=[c for c in cards if c['id']==id];assert len(matches)==1 and matches[0]['status']==seeds[id]['status'],matches
    assert any(c['id']=='custom' for c in cards)
    assert not errors,errors
    browser.close()
print('PASS: document setup/persistence, CMYK, anchor tools, Alt copy/scale, Shift alignment/pen, Ctrl+F, history and guards')
