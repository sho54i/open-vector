"""Variable-width strokes: rendered pixels, editable state, history and exports."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.drawWidthReady')
    def setup():
        page.evaluate('''() => { __DRAW__.clearCanvas(); __DRAW__.loadOutline({paths:[{stroke:'#ff0000',strokeWidth:16,strokeCap:'butt',points:[{x:100,y:200},{x:500,y:200}]}]});
            __DRAW__.selectPath(0);camera={x:50,y:50,scale:1};showGrid=false;pushHistory();draw(); }''')
    state=lambda:page.evaluate('serializeOutline().paths')
    choose=lambda name:page.locator('#widthPreset').select_option(name)
    setup();before=state();choose('spindle');after=state()
    assert after[0]['points']==before[0]['points'] and after[0]['widthProfile'][1]['width']==1
    # Canvas thickness at 10% vs 50%, excluding on-canvas selection chrome.
    page.evaluate('hideNodes=true;deselect();draw()')
    pixels=page.evaluate('''() => {const c=document.getElementById('vectorCanvas'),g=c.getContext('2d');
        return [140,300].map(x=>{let count=0;for(let y=180;y<=220;y++){const s=screenFromWorld({x,y}),v=g.getImageData(s.x*dpr,s.y*dpr,1,1).data;if(v[0]>180&&v[1]<80&&v[2]<80)count++;}return count;});}''')
    assert pixels[1]>=14 and pixels[0]<pixels[1]/2,pixels
    # Visible wide edge hit testing, even far from original centreline.
    page.evaluate('__DRAW__.selectPath(0)');page.get_by_label('Width percent stop 2',exact=True).fill('400');page.get_by_label('Width percent stop 2',exact=True).press('Tab')
    assert page.evaluate('hitPathAt({x:300,y:225})===paths[0]')
    assert state()[0]['widthProfile'][1]['width']==4
    page.keyboard.press('Control+z');assert state()[0]['widthProfile'][1]['width']==1
    page.keyboard.press('Control+y');assert state()[0]['widthProfile'][1]['width']==4
    page.evaluate('__DRAW__.selectPath(0)');page.locator('#addWidthStop').click();assert len(state()[0]['widthProfile'])==4
    page.get_by_label('Remove width stop 2',exact=True).click();assert len(state()[0]['widthProfile'])==3
    # Invalid/duplicate positions cannot mutate document or history.
    prior=state();hist=page.evaluate('history.length')
    page.get_by_label('Position percent stop 2',exact=True).fill('0');page.get_by_label('Position percent stop 2',exact=True).press('Tab')
    assert state()==prior and page.evaluate('history.length')==hist
    # SVG raster uses the same contour; PNG export succeeds via that SVG pipeline.
    svg=page.evaluate('generateSVGString()');assert 'stroke="none"' in svg and 'fill="#ff0000"' in svg
    raster=page.evaluate('''async svg=>{const im=new Image();im.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);await im.decode();
        const c=document.createElement('canvas');c.width=im.naturalWidth;c.height=im.naturalHeight;const g=c.getContext('2d');g.drawImage(im,0,0);
        return [0.15,0.5].map(t=>{let n=0;for(let y=0;y<c.height;y++){const p=g.getImageData(Math.round(c.width*t),y,1,1).data;if(p[0]>180&&p[1]<80&&p[2]<80&&p[3]>128)n++;}return n;});}''',svg)
    assert raster[1]>raster[0] and raster[1]>=60,raster
    with page.expect_download() as download:
        assert page.evaluate('exportPNG()')
    assert Path(download.value.path()).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert page.evaluate("parseSVGArtwork(generateSVGString()).length")>=1
    # Saved outline, reload, duplicate and reflect retain profiles.
    saved=state();page.wait_for_timeout(1200);page.reload();page.wait_for_function('window.drawWidthReady');assert state()==saved
    page.evaluate('__DRAW__.selectPath(0);duplicateSelection()');assert state()[1]['widthProfile']==saved[0]['widthProfile']
    page.locator('[data-reflect="x"]').click();assert state()[1]['widthProfile']==saved[0]['widthProfile']
    # Gradient stroke becomes a gradient-filled outline, preserving its paint.
    setup();page.evaluate("paths[0].strokeType='linear';paths[0].strokeGradient=normalizeGradient({stops:[{offset:0,color:'#ff0000'},{offset:1,color:'#0000ff'}]});updateInspector()")
    choose('taperEnd');svg=page.evaluate('generateSVGString()');assert 'fill="url(#sgrad-' in svg and 'userSpaceOnUse' in svg
    # Closed and compound curved contours produce finite outlines and retain holes.
    page.evaluate('''() => {const a=makeEllipsePath(100,100,120,120),b=makeEllipsePath(130,130,40,40);setPathContours(a,[a.points,b.points]);
        paths=[a];setPathSelection([a]);updateInspector();}''');choose('wave')
    d=page.evaluate('variableStrokeD(paths[0])');assert d and 'NaN' not in d and 'Infinity' not in d,(d[:120],page.locator('#widthStatus').inner_text(),state())
    choose('uniform');assert state()[0]['widthProfile'] is None
    # Locked path and unselected state are disabled, direct invalid profile rejects atomically.
    setup();page.evaluate('paths[0].locked=true;updateInspector()');assert page.locator('#widthPreset').is_disabled()
    assert not page.evaluate('applyWidthProfile([{offset:0,width:1},{offset:1,width:2}])')
    setup();prior=state();assert not page.evaluate('applyWidthProfile([{offset:0,width:1},{offset:1,width:9}])');assert state()==prior
    choose('wave');page.locator('#strokeDash').fill('4 2');page.locator('#strokeDash').press('Enter');assert state()[0]['widthProfile'] is None
    setup();page.evaluate('duplicateSelection();paths[1].strokeWidth=8;__DRAW__.selectPaths([0,1])');choose('taperStart')
    assert all(v['widthProfile']==[{'offset':0,'width':0},{'offset':1,'width':1}] for v in state())
    assert [v['strokeWidth'] for v in state()]==[16,8]
    page.evaluate('paths[1].locked=true;updateInspector()');prior=state();assert not page.evaluate('applyWidthProfile(null)');assert state()==prior
    setup();choose('spindle');page.locator('[data-panel="stroke-width"]').screenshot(path='/tmp/open-vector-width.png')
    assert not errors,errors
    browser.close();print('PASS: canvas thickness',pixels,'SVG thickness',raster,'profile edits, validation, hit testing, undo/redo/reload, copies/reflection, gradients, compound curves and dash compatibility')
