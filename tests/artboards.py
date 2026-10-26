from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'],timeout=15000)
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__')
    page.wait_for_timeout(100)
    def document():return page.evaluate('window.__DRAW__.serializeOutline()')
    def boards():return document()['artboards']
    def undo():page.locator('#viewport').focus();page.keyboard.press('Control+z')
    def redo():page.locator('#viewport').focus();page.keyboard.press('Control+y')
    def fit_assert():
        assert page.evaluate('''()=>{const d=window.__DRAW__,r=document.querySelector('#vectorCanvas').getBoundingClientRect();return d.getState().artboards.every(b=>{const a=d.worldToScreen(b.x,b.y),z=d.worldToScreen(b.x+b.w,b.y+b.h);return a.x>=48&&a.y>=48&&z.x<=r.width-47&&z.y<=r.height-47})}''')
    page.evaluate('window.__DRAW__.clearCanvas()')
    assert len(boards())==1 and page.locator('#removeArtboard').is_disabled()
    page.locator('#addArtboard').click()
    assert len(boards())==2 and boards()[1]['x']==880
    second_id=boards()[1]['id']
    assert document()['activeArtboardId']==second_id
    undo();assert len(boards())==1
    redo();assert len(boards())==2 and document()['activeArtboardId']==second_id
    # Apply form commits name/position/dimensions together, preserving artwork.
    page.evaluate('window.__DRAW__.addRect(50,60,40,50)')
    original_paths=document()['paths']
    for field,value in [('Name','Poster'),('X','900'),('Y','200'),('W','320'),('H','240')]:
        page.locator('#artboard'+field).fill(value)
    page.locator('#artboardForm button[type="submit"]').click()
    assert boards()[1]==dict(id=second_id,name='Poster',x=900,y=200,w=320,h=240)
    assert document()['paths']==original_paths
    undo();assert boards()[1]['w']==800
    redo();assert boards()[1]['w']==320
    page.locator('#artboardW').fill('700');page.locator('#artboardW').press('Escape')
    assert page.locator('#artboardW').input_value()=='320' and boards()[1]['w']==320
    before=boards()
    for bad in [{'w':0},{'h':-1},{'name':' '},{'x':None},{'w':100001}]:
        assert page.evaluate('bad=>window.__DRAW__.updateArtboard(bad)',bad) is False
        assert boards()==before
    page.locator('#artboardSelect').select_option(boards()[0]['id'])
    assert document()['activeArtboardId']==boards()[0]['id']
    page.locator('#fitAllArtboards').click();fit_assert()
    page.locator('#artboardSelect').select_option(second_id)
    assert page.evaluate('''()=>{const d=window.__DRAW__,p=d.worldToScreen(1060,320),r=document.querySelector('#vectorCanvas').getBoundingClientRect();return Math.abs(p.x-(r.width+20)/2)<3&&Math.abs(p.y-(r.height+20)/2)<3}''')
    print('PASS: UI add 1 → 2 → Undo 1 → Redo 2; name/bounds apply and undo; Escape/invalid input; board selection and fit all.',flush=True)
    # Export actual UI download: exact active dimensions and clipped pixels.
    page.evaluate('''()=>{const d=window.__DRAW__;d.addRect(920,220,40,40);d.setFillHex('#ffb800');document.querySelector('#enableFill').checked=true;document.querySelector('#enableFill').dispatchEvent(new Event('input'));d.addRect(100,100,50,50);d.setFillHex('#ff0000');d.addRect(1190,300,100,50);d.setFillHex('#00f0ff');}''')
    raw_paths=document()['paths']
    page.locator('#exportScope').select_option('active')
    with page.expect_download() as got: page.locator('#btnExport').click()
    download=got.value
    assert download.suggested_filename=='Poster.svg'
    svg=Path(download.path()).read_text()
    assert 'viewBox="0 0 320 240"' in svg
    pixels=page.evaluate('''async svg=>{const im=new Image();im.src='data:image/svg+xml,'+encodeURIComponent(svg);await im.decode();const c=document.createElement('canvas');c.width=im.naturalWidth;c.height=im.naturalHeight;const ctx=c.getContext('2d');ctx.drawImage(im,0,0);return {size:[c.width,c.height],inside:[...ctx.getImageData(40,40,1,1).data],empty:[...ctx.getImageData(150,150,1,1).data],edge:[...ctx.getImageData(319,120,1,1).data]}}''',svg)
    assert pixels['size']==[320,240] and pixels['inside']==[255,184,0,255] and pixels['empty'][3]==0 and pixels['edge']==[0,240,255,255],pixels
    assert document()['paths']==raw_paths
    page.locator('#exportScope').select_option('artwork')
    with page.expect_download() as got: page.locator('#btnExport').click()
    assert 'viewBox="0 0 320 240"' not in Path(got.value.path()).read_text()
    # Removing a board retains all paths; undo recovers board and selection.
    page.locator('#removeArtboard').click();assert len(boards())==1 and document()['paths']==raw_paths
    undo();assert len(boards())==2 and document()['activeArtboardId']==second_id
    page.wait_for_timeout(500);saved=document();page.reload();page.wait_for_timeout(200)
    assert boards()==saved['artboards'] and document()['activeArtboardId']==second_id and document()['paths']==raw_paths
    print('PASS: active SVG download 320×240, correct origin, transparent empty pixels and edge clipping; all-artwork export; remove preserves paths; session reload.',flush=True)
    # Empty multi-board documents can be saved, reopened and restored.
    page.evaluate('window.__DRAW__.clearCanvas();window.__DRAW__.addArtboard()')
    empty=document()
    with page.expect_download() as got:page.locator('#btnSave').click()
    saved_file=Path(got.value.path());assert len(json.loads(saved_file.read_text())['artboards'])==2
    page.evaluate('window.__DRAW__.clearCanvas()')
    page.locator('#fileLoad').set_input_files(str(saved_file))
    page.wait_for_timeout(150)
    assert boards()==empty['artboards'] and document()['paths']==[]
    page.wait_for_timeout(500);page.reload();page.wait_for_timeout(150);assert boards()==empty['artboards']
    page.locator('#exportScope').select_option('active')
    with page.expect_download() as got:page.locator('#btnExport').click()
    assert 'viewBox="0 0 800 600"' in Path(got.value.path()).read_text()
    # Legacy outlines migrate to one board; malformed modern data is atomic.
    assert page.evaluate('window.__DRAW__.loadOutline({paths:[],artboard:{w:640,h:480}})')
    assert len(boards())==1 and boards()[0]['w']==640 and boards()[0]['x']==0
    saved=document()
    for value in [[],[{'id':'bad','x':0,'y':0,'w':-1,'h':600}]]:
        assert page.evaluate('artboards=>window.__DRAW__.loadOutline({artboards,paths:[]})',value) is False
        assert boards()==saved['artboards']
    assert page.evaluate('window.__DRAW__.loadOutline({paths:[{points:[{x:1,y:1},{x:2,y:2}]}]})')
    assert boards()[0]['w']==800
    # Pasting another document adds its paths, without replacing current boards.
    page.evaluate('window.__DRAW__.addArtboard()');before=boards()
    page.evaluate('window.__DRAW__.pasteText(JSON.stringify({artboards:[{id:"foreign",name:"Foreign",x:0,y:0,w:50,h:50}],paths:[{points:[{x:1,y:1},{x:2,y:2}]}]}))')
    assert boards()==before
    # Assistant preview stays isolated; insertion targets the board active at insertion.
    page.evaluate('window.__DRAW__.clearCanvas()')
    page.evaluate('window.__ENTITY_VECTOR__.preview(\'<svg><rect x="10" y="10" width="80" height="60" fill="#ffb800"/></svg>\')')
    preview=page.evaluate('window.__ENTITY_VECTOR__.getState().svg')
    page.evaluate('window.__DRAW__.addArtboard();window.__DRAW__.updateArtboard({x:-400,y:-200,w:320,h:240})')
    page.locator('#entityInsert').click()
    assert all(-400<=p['x']<=-80 and -200<=p['y']<=40 for p in document()['paths'][0]['points'])
    assert page.evaluate('window.__ENTITY_VECTOR__.getState().svg')==preview
    undo();assert document()['paths']==[] and len(boards())==2
    redo();assert len(document()['paths'])==1
    page.evaluate('window.__DRAW__.fitAllArtboards()');page.locator('.inspector').evaluate('el=>el.scrollTop=0')
    page.wait_for_timeout(2000);page.screenshot(path=str(Path('/tmp/open-vector-artboards.png')))
    assert not errors,errors
    print('PASS: empty board save/open/reload/export, legacy migration, malformed input rejection, paste preserves boards, Entity insert targets active negative-origin board; no browser errors.',flush=True)
    # Pointer drawing still uses world coordinates on a non-origin board.
    page.locator('#toolPen').click()
    for x,y in [(-370,-170),(-330,-140),(-290,-170)]:
        pt=page.evaluate('p=>window.__DRAW__.worldToScreen(p[0],p[1])',[x,y]);box=page.locator('#vectorCanvas').bounding_box()
        page.mouse.click(box['x']+pt['x'],box['y']+pt['y'])
    page.keyboard.press('Escape')
    points=document()['paths'][-1]['points']
    assert len(points)==3 and abs(points[0]['x']+370)<1 and abs(points[0]['y']+170)<1
    page.goto((ROOT/'ROADMAP.html').as_uri());page.wait_for_function('window.__ROADMAP__')
    page.evaluate("""()=>{const state=window.__ROADMAP__.seed();state.version=24;state.cards.find(c=>c.id==='p6-artboards').status='next';state.cards.find(c=>c.id==='p6-png').status='queued';state.inbox=[{id:'keep-artboard-idea',title:'Keep this'}];localStorage.setItem('eve-roadmap-v1',JSON.stringify(state));}""")
    page.reload()
    assert page.evaluate("window.__ROADMAP__.getState().cards.find(c=>c.id==='p6-artboards').status")=='shipped'
    assert page.evaluate("window.__ROADMAP__.getState().cards.find(c=>c.id==='p6-png').status === window.__ROADMAP__.seed().cards.find(c=>c.id==='p6-png').status")
    assert page.evaluate("window.__ROADMAP__.getState().inbox[0].id")=='keep-artboard-idea'
    assert not errors,errors
    print('PASS: pointer drawing on negative-origin board; saved roadmap migration retains inbox.',flush=True)
    browser.close()
