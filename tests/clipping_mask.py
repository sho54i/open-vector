"""Clipping masks: real controls, canvas/SVG/PNG pixels, editing and persistence."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'], timeout=15000)
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri()); page.wait_for_function('window.__DRAW_PANELS__')
    def setup():
        page.evaluate('''() => {
            __DRAW__.clearCanvas();
            const rect=(x,y,w,h,fill)=>({closed:true,enableFill:true,fill,stroke:'transparent',points:[{x,y},{x:x+w,y},{x:x+w,y:y+h},{x,y:y+h}]});
            __DRAW__.loadOutline({paths:[rect(100,100,200,200,'#ff0000'),rect(150,150,100,100,'#0000ff')]});
            camera={x:50,y:50,scale:1};showGrid=false;__DRAW__.selectPaths([1,0]);pushHistory();draw();
        }''')
    state = lambda: page.evaluate('serializeOutline().paths')
    make = lambda: page.locator('#makeClip').click()
    def screen(x,y):
        return page.evaluate('p=>{const s=screenFromWorld(p),r=canvas.getBoundingClientRect();return {x:s.x+r.left,y:s.y+r.top};}', {'x':x,'y':y})
    def pixels():
        return page.evaluate('''() => {deselect();draw();return [125,175,275].map(x=>{const s=screenFromWorld({x,y:200});return [...ctx.getImageData(s.x*dpr,s.y*dpr,1,1).data];});}''')
    def red(pixel): return pixel[0]>200 and pixel[1]<50 and pixel[2]<50
    setup(); before=state(); make(); clipped=state()
    assert clipped[1]['clipMask'] and not clipped[0]['clipMask'], 'Topmost, not last-clicked, is mask'
    assert clipped[0]['clipId']==clipped[1]['clipId'] and clipped[0]['clipId']
    assert clipped[0]['points']==before[0]['points'] and clipped[1]['fill']==before[1]['fill']
    colours=pixels(); assert not red(colours[0]) and red(colours[1]) and not red(colours[2]),colours
    assert page.evaluate('hitPathAt({x:125,y:200})===null && hitStrokeAt({x:100,y:200})===null')
    # Real V click selects the entire clipping group; arrow moves content and mask together.
    assert page.evaluate('setPathSelection([hitPathAt({x:175,y:200})]);pathSelection().length')==2
    page.evaluate('deselect()');page.keyboard.press('v');page.mouse.click(**screen(175,200))
    assert page.evaluate('pathSelection().length')==2
    page.keyboard.press('ArrowRight'); moved=state()
    assert moved[0]['points'][0]['x']==101 and moved[1]['points'][0]['x']==151
    page.keyboard.press('Control+z');assert state()==clipped
    page.keyboard.press('Control+z');assert state()==before
    page.keyboard.press('Control+y');assert state()==clipped
    # Direct mask edit moves just its anchor and leaves the content geometry intact.
    page.evaluate('__DRAW__.selectPath(0)');page.locator('#editClip').click()
    assert page.evaluate("currentMode==='direct' && selectedPath.clipMask")
    page.mouse.move(**screen(150,150));page.mouse.down();page.mouse.move(**screen(160,155),steps=4);page.mouse.up()
    edited=state();assert edited[1]['points'][0]['x']==160 and edited[1]['points'][0]['y']==155,edited[1]['points'][0]
    assert edited[0]['points']==clipped[0]['points']
    page.keyboard.press('Control+z');assert state()==clipped
    # Release restores original paint and geometry, and is one reversible operation.
    page.evaluate('__DRAW__.selectPath(0)');page.locator('#releaseClip').click();assert state()==before
    page.keyboard.press('Control+z');assert state()==clipped
    # SVG/PNG actually crop; export's transparent exterior is sampled after decoding.
    svg=page.evaluate('generateSVGString(null,{scope:"active"})');assert '<clipPath' in svg and 'clip-path="url(#clip-' in svg
    rgba=page.evaluate('''async svg=>{const im=new Image();im.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);await im.decode();const c=document.createElement('canvas');c.width=im.naturalWidth;c.height=im.naturalHeight;const g=c.getContext('2d');g.drawImage(im,0,0);return [125,175,275].map(x=>[...g.getImageData(x,200,1,1).data]);}''',svg)
    assert rgba[0][3]==0 and red(rgba[1]) and rgba[2][3]==0,rgba
    with page.expect_download() as download: assert page.evaluate('exportPNG()')
    png=Path(download.value.path()).read_bytes();assert png.startswith(b'\x89PNG\r\n\x1a\n')
    # Importing our SVG retains clipping rather than exposing the hidden content.
    imported=page.evaluate('''() => {const p=parseSVGArtwork(generateSVGString());return {count:p.length,masks:p.filter(p=>p.clipMask).length,ids:p.map(p=>p.clipId)};}''')
    assert imported['count']==2 and imported['masks']==1 and len(set(imported['ids']))==1,imported
    # Outline reload and session reload preserve relationships; duplicate gets its own group.
    saved=state();page.evaluate('loadOutline(serializeOutline());scheduleSessionSave()');assert state()==saved
    page.wait_for_timeout(1200);page.reload();page.wait_for_function('window.__DRAW_PANELS__');assert state()==saved
    page.evaluate('__DRAW__.selectPath(0);duplicateSelection()'); copies=state()
    assert len(copies)==4 and copies[2]['clipId']==copies[3]['clipId']!=copies[0]['clipId']
    page.locator('#releaseClip').click();assert state()[0]['clipId'] and state()[2]['clipId'] is None
    # Reflected copies remain independent masks, including after history restores.
    page.evaluate('__DRAW__.selectPath(0);reflectSelection("x",null,true)');copies=state()
    assert copies[-1]['clipId']==copies[-2]['clipId']!=copies[0]['clipId']
    # Hidden masks stay in JSON and hide their content through reload.
    setup();make();page.evaluate('paths[1].visible=false;draw()'); hidden=state()
    assert len(hidden)==2 and not hidden[1]['visible'];assert not any(red(v) for v in pixels())
    page.evaluate('loadOutline(serializeOutline())');assert state()==hidden and not any(red(v) for v in pixels())
    # A compound even-odd mask keeps a hole in both the canvas and SVG.
    setup();page.evaluate('''() => {const m=paths[1];setPathContours(m,[m.points,[createPoint(180,180),createPoint(220,180),createPoint(220,220),createPoint(180,220)]]);m.fillRule='evenodd';pushHistory();}''');make()
    assert page.evaluate('!clipAllowsPoint(paths[0],{x:200,y:200}) && clipAllowsPoint(paths[0],{x:160,y:200})')
    assert 'clip-rule="evenodd"' in page.evaluate('generateSVGString()')
    # Gradients and variable-width outlines remain clipped in canvas and SVG.
    setup();page.evaluate("paths[0].fillType='linear';paths[0].gradient=normalizeGradient(null,'#ff0000','#00ff00');paths[0].stroke='#ff0000';paths[0].widthProfile=[{offset:0,width:4},{offset:1,width:4}];pushHistory()");make()
    assert '<linearGradient' in page.evaluate('generateSVGString()') and 'clip-path=' in page.evaluate('generateSVGString()')
    assert not red(pixels()[0])
    # Invalid operations leave both geometry and history unchanged.
    for mutate in ['__DRAW__.selectPath(0)', 'paths[1].closed=false', 'paths[0].locked=true', 'paths[1].visible=false', 'paths[0].groupId=7']:
        setup();page.evaluate(mutate);prior=state();hist=page.evaluate('history.length');make()
        assert state()==prior and page.evaluate('history.length')==hist,mutate
    setup();make();prior=state();hist=page.evaluate('history.length');make()
    assert state()==prior and page.evaluate('history.length')==hist
    assert not page.evaluate('booleanReady()') and not page.evaluate('createBlend(3,true)')
    page.evaluate('paths[0].locked=true');prior=state();hist=page.evaluate('history.length')
    page.locator('#releaseClip').click();assert state()==prior and page.evaluate('history.length')==hist
    assert not page.evaluate('deleteSelected()') and state()==prior
    # Duplication/copy from Edit mask must include its artwork rather than orphan a mask.
    setup();make();page.locator('#editClip').click()
    assert page.evaluate('pathsToCopy().length')==2
    page.evaluate('duplicateSelection()');assert len(state())==4
    assert state()[2]['clipId']==state()[3]['clipId']!=state()[0]['clipId']
    # Invalid saved groups and dangling SVG references fail atomically.
    prior=state()
    assert not page.evaluate('loadOutline({paths:[serializeOutline().paths[0]]})') and state()==prior
    assert page.evaluate("parsePayload('<svg xmlns=\"http://www.w3.org/2000/svg\"><rect width=\"10\" height=\"10\" clip-path=\"url(#missing)\"/></svg>').paths.length") == 0
    # Record the finished panel and masked canvas for visual review.
    setup();make();page.locator('#makeClip').scroll_into_view_if_needed();page.screenshot(path=str(ROOT/'planning/clipping-mask.png'))
    assert not errors,errors
    print('PASS clipping: canvas red inside only; V movement +1 on both paths; mask anchor (150,150)→(160,155); Undo/Redo/release; SVG alpha 0/255/0; PNG; SVG import; reload; independent copies; holes; guards.')
    browser.close()
