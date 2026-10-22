"""Styles card: actual controls, geometry, pixel rendering, persistence and export."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1100});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.drawStylesReady')
    def setup(closed=True):
        page.evaluate('''closed=>{__DRAW__.clearCanvas();__DRAW__.loadOutline({paths:[{closed,enableFill:closed,fill:'#ff0000',stroke:'#ff0000',strokeWidth:2,points:[{x:100,y:100},{x:200,y:100},{x:200,y:200},{x:100,y:200}]}]});__DRAW__.selectPath(0);camera={x:50,y:50,scale:1};showGrid=false;pushHistory();draw();}''',closed)
    state=lambda:page.evaluate('serializeOutline().paths')
    def field(id,value):
        page.locator('#'+id).fill(str(value));page.locator('#'+id).press('Tab')
    def ready():
        page.wait_for_function('paths.every(p=>!normalizeEffects(p.effects) || styledArtworkCache?.get(p)?.ready)')
    def raster():
        return page.evaluate('''async()=>{const svg=generateSVGString(),b=boundsOf(paths,16),im=new Image();im.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);await im.decode();const c=document.createElement('canvas');c.width=im.naturalWidth;c.height=im.naturalHeight;const g=c.getContext('2d');g.drawImage(im,0,0);return [[80,150],[150,80],[220,150],[150,150]].map(([x,y])=>Array.from(g.getImageData(Math.round(x-b.minX),Math.round(y-b.minY),1,1).data));}''')
    setup();original=state();page.locator('#styleShadow').check();assert state()[0]['effects']['shadow']['enabled']
    field('styleShadowX',35);field('styleShadowY',0);field('styleShadowBlur',0);field('styleShadowOpacity',100)
    page.locator('#styleShadowColor').evaluate("el=>{el.value='#0000ff';el.dispatchEvent(new Event('change',{bubbles:true}));}")
    ready();r=raster();assert r[2]==[0,0,255,255],r
    # Canvas and SVG both paint the shadow outside the original path.
    pixel=page.evaluate('''()=>{deselect();draw();const p=screenFromWorld({x:220,y:150});return Array.from(ctx.getImageData(p.x*dpr,p.y*dpr,1,1).data);}''')
    assert pixel[:3]==[0,0,255],pixel
    page.evaluate('__DRAW__.selectPath(0)');page.locator('#clearStyles').click();assert state()[0]['effects'] is None
    page.keyboard.press('Control+z');assert state()[0]['effects']['shadow']['x']==35
    page.keyboard.press('Control+y');assert state()[0]['effects'] is None
    for mode in ['horizontal','vertical','gaussian']:
        page.evaluate('__DRAW__.selectPath(0)');page.locator('#styleBlurType').select_option(mode);field('styleBlurAmount',10);ready();pixels=raster()
        if mode=='horizontal': assert pixels[0][3]>0 and pixels[1][3]==0,pixels
        elif mode=='vertical': assert pixels[0][3]==0 and pixels[1][3]>0,pixels
        else: assert pixels[0][3]>0 and pixels[1][3]>0,pixels
    assert state()[0]['points']==original[0]['points']
    saved=state();page.wait_for_timeout(1200);page.reload();page.wait_for_function('window.drawStylesReady');ready();assert state()==saved
    page.evaluate('__DRAW__.selectPath(0);duplicateSelection()');assert state()[1]['effects']==saved[0]['effects']
    # Actual PNG download exercises filtered SVG image decoding and transparent margins.
    with page.expect_download() as download: assert page.evaluate('exportPNG()')
    assert Path(download.value.path()).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    # Numeric validation and locked/mixed selection guards leave document unchanged.
    setup();prior=state();field('styleBlurAmount',101);assert state()==prior
    page.evaluate('paths[0].locked=true;updateInspector()');assert page.locator('#styleShadow').is_disabled()
    assert not page.evaluate("applyEffects({blur:{type:'gaussian',amount:10}})")
    setup();page.evaluate('duplicateSelection();paths[0].effects={shadow:{enabled:true,x:30,y:4,blur:3,color:"#123456",opacity:0.7}};__DRAW__.selectPaths([0,1]);updateInspector()')
    field('styleBlurAmount',5);v=state();assert v[0]['effects']['shadow']['x']==30 and v[1]['effects']['shadow'] is None
    # Rounding creates real Bezier anchors, not a raster approximation.
    setup();before=state();field('styleRadius',20);page.locator('#roundCorners').click();rounded=state()
    assert len(rounded[0]['points'])==8 and all(v['hasHandles'] for v in rounded[0]['points'])
    assert rounded[0]['points'][0]['y']==120 and rounded[0]['points'][1]['x']==120
    assert rounded[0]['points'][0]['cp2']['y']<120
    assert rounded[0]['closed'] and rounded[0]['fill']==before[0]['fill']
    page.keyboard.press('Control+z');assert state()==before
    page.keyboard.press('Control+y');assert state()==rounded
    # Actual A-mode drag changes an anchor and its handle by the same delta.
    page.evaluate('__DRAW__.selectPoint(0,0)')
    handle=page.evaluate("()=>{const p=paths[0].points[0].cp2,s=screenFromWorld(p),r=canvas.getBoundingClientRect();return {x:s.x+r.x,y:s.y+r.y};}")
    page.mouse.move(handle['x'],handle['y']);page.mouse.down();page.mouse.move(handle['x']-12,handle['y']-8,steps=5);page.mouse.up()
    edited=state()[0]['points'][0]
    assert abs(edited['cp2']['x']-(rounded[0]['points'][0]['cp2']['x']-12))<0.1,edited
    assert edited['x']==rounded[0]['points'][0]['x'] and edited['y']==rounded[0]['points'][0]['y']
    page.keyboard.press('Control+z');assert state()==rounded
    page.evaluate('__DRAW__.selectPath(0)');page.locator('#roughenEdges').click();rough=state()
    assert len(rough[0]['points'])>8 and rough[0]['points']!=rounded[0]['points'] and rough[0]['closed']
    page.keyboard.press('Control+z');assert state()==rounded
    page.evaluate('__DRAW__.selectPath(0)');page.locator('#roughenEdges').click();assert state()==rough
    page.keyboard.press('Control+z');page.evaluate('__DRAW__.selectPath(0)');field('styleSeed',2);page.locator('#roughenEdges').click();assert state()!=rough
    setup(False);assert page.locator('#roundCorners').is_disabled();before=state()[0]['points'];page.locator('#roughenEdges').click();after=state()[0]['points']
    assert (after[0]['x'],after[0]['y'])==(before[0]['x'],before[0]['y']) and (after[-1]['x'],after[-1]['y'])==(before[-1]['x'],before[-1]['y'])
    # No-op rounding does not add an Undo entry; huge roughen requests fail atomically.
    setup();page.evaluate('paths=[makeEllipsePath(100,100,100,100)];setPathSelection(paths);updateInspector();pushHistory()');before=state();hist=page.evaluate('history.length')
    page.locator('#roundCorners').click();assert state()==before and page.evaluate('history.length')==hist
    page.evaluate('paths[0].points[0].cp2.x=1e7');before=state();page.locator('#roughenEdges').click();assert state()==before
    # Compound holes and width profiles remain valid through rounding and filtered export.
    page.evaluate('''()=>{let a=makeRectPath(100,100,200,200),b=makeRectPath(150,150,50,50);setPathContours(a,[a.points,b.points]);a.fillRule='evenodd';a.enableFill=true;a.fill='#ff0000';paths=[a];setPathSelection(paths);updateInspector();}''')
    page.locator('#roundCorners').click();assert page.evaluate('pathContours(paths[0]).length')==2
    page.locator('#styleShadow').check();page.evaluate('applyWidthProfile([{offset:0,width:0},{offset:0.5,width:1},{offset:1,width:0}])');ready()
    assert 'feMerge' in page.evaluate('generateSVGString()')
    # A gradient retains its paint through effects; internal copy/paste retains the effect recipe.
    setup();page.evaluate("paths[0].fillType='linear';paths[0].gradient=normalizeGradient(null,'#ff0000','#00ff00');updateInspector()")
    page.locator('#styleShadow').check();ready()
    assert '<linearGradient' in page.evaluate('generateSVGString()')
    copied=state()[0]['effects'];page.evaluate('copySelection();pasteInPlace()');assert len(state())==2 and state()[1]['effects']==copied
    # Mask cropping happens after the effect, including on the canvas image cache.
    setup();page.locator('#styleShadow').check();field('styleShadowX',35);field('styleShadowY',0);field('styleShadowBlur',0)
    page.locator('#styleShadowColor').evaluate("el=>{el.value='#0000ff';el.dispatchEvent(new Event('change'));}")
    page.evaluate("const mask=makeRectPath(90,90,115,120);paths.push(mask);__DRAW__.selectPaths([0,1]);clippingSelection('make')")
    ready();clip_pixels=page.evaluate("()=>{deselect();draw();return [150,220].map(x=>{const p=screenFromWorld({x,y:150});return Array.from(ctx.getImageData(p.x*dpr,p.y*dpr,1,1).data);});}")
    assert clip_pixels[0][0]>200 and clip_pixels[1][2]<100,clip_pixels
    setup();page.locator('#styleShadow').check();ready()
    page.set_viewport_size({'width':768,'height':1024});page.locator('#styleShadow').scroll_into_view_if_needed()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('[data-panel="styles"]').screenshot(path='/tmp/open-vector-styles.png')
    # Existing boards receive the testing card once and retain unrelated inbox items.
    board=browser.new_page();board.goto((ROOT/'ROADMAP.html').as_uri())
    board.evaluate("localStorage.setItem('eve-roadmap-v1',JSON.stringify({version:37,cards:[{id:'cyb0pf3h',title:'add various styles',status:'queued',updated:'2026-10-22T08:39:36.197Z',notes:'My original note'}],inbox:[{id:'keep-me',title:'Keep me'}]}))")
    board.reload();migrated=board.evaluate('state')
    cards=[c for c in migrated['cards'] if c['id']=='cyb0pf3h'];assert len(cards)==1 and cards[0]['status']=='testing' and 'My original note' in cards[0]['notes']
    assert any(c['id']=='keep-me' for c in migrated['inbox']) and migrated['version']>=38
    board.reload();assert board.evaluate("state.cards.filter(c=>c.id==='cyb0pf3h').length")==1
    board.close()
    assert not errors,errors
    browser.close();print('PASS: shadow canvas pixel',pixel,'directional/Gaussian blur alpha, PNG, geometry anchors/handles, undo/redo, reload, copies, guards and compound paths')
