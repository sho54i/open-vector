from pathlib import Path
import base64,struct
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
SVG='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect x="10" y="10" width="30" height="20" fill="#ffb800"/><circle cx="70" cy="60" r="15" fill="#00f0ff"/></svg>'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'],timeout=15000)
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url) if r.url.startswith('http') else None)
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.__DRAW__');page.wait_for_timeout(100)
    def paths():return page.evaluate('window.__DRAW__.serializeOutline().paths')
    def state():return page.evaluate('window.__DRAW__.getState()')
    def undo():page.locator('#viewport').focus();page.keyboard.press('Control+z')
    def redo():page.locator('#viewport').focus();page.keyboard.press('Control+y')
    def drop(files,wait=True):
        page.evaluate('''files=>{const d=new DataTransfer();for(const f of files)d.items.add(new File([f.content],f.name,{type:f.type||'image/svg+xml'}));const v=document.querySelector('#viewport'),r=document.querySelector('#vectorCanvas').getBoundingClientRect(),s=window.__DRAW__.worldToScreen(250,150);v.dispatchEvent(new DragEvent('dragenter',{bubbles:true,cancelable:true,dataTransfer:d}));v.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:d,clientX:r.left+s.x,clientY:r.top+s.y}));}''',files)
        if wait:page.wait_for_function('!window.__DRAW__.getState().svgDropBusy')
    page.evaluate('''()=>{const d=window.__DRAW__;d.clearCanvas();d.updateArtboard({x:100,y:100,w:120,h:80,name:'Tile'});d.addRect(120,120,30,30);d.setFillHex('#ffb800');document.querySelector('#enableFill').checked=true;document.querySelector('#enableFill').dispatchEvent(new Event('input'));window.downloadMimes=[];const original=URL.createObjectURL;URL.createObjectURL=blob=>{window.downloadMimes.push(blob.type);return original.call(URL,blob)}}''')
    before=paths()
    for scale in [1,2,4]:
        page.locator('#pngScale').select_option(str(scale))
        with page.expect_download() as got:page.locator('#btnExportPNG').click()
        data=Path(got.value.path()).read_bytes()
        assert data[:8]==b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II',data[16:24])==(120*scale,80*scale)
        assert got.value.suggested_filename==f'Tile@{scale}x.png'
        pixel=page.evaluate('''async args=>{const im=new Image();im.src='data:image/png;base64,'+args.data;await im.decode();const c=document.createElement('canvas');c.width=im.width;c.height=im.height;const ctx=c.getContext('2d');ctx.drawImage(im,0,0);return [[...ctx.getImageData(30*args.scale,30*args.scale,1,1).data],ctx.getImageData(80*args.scale,60*args.scale,1,1).data[3]]}''',{'data':base64.b64encode(data).decode(),'scale':scale})
        assert pixel==[[255,184,0,255],0],pixel
        assert paths()==before
    assert 'image/png' in page.evaluate('window.downloadMimes')
    page.locator('#exportScope').select_option('artwork');page.locator('#pngScale').select_option('2')
    with page.expect_download() as got:
        page.locator('[data-menu="file"] .menu-item').click();page.locator('[data-cmd="exportPNG"]').click()
    assert struct.unpack('>II',Path(got.value.path()).read_bytes()[16:24])==(124,124)
    # Encoding failure restores the button and never mutates artwork.
    assert page.evaluate('''async()=>{const original=HTMLCanvasElement.prototype.toBlob;HTMLCanvasElement.prototype.toBlob=function(cb){cb(null)};try{return await window.__DRAW__.exportPNG()}finally{HTMLCanvasElement.prototype.toBlob=original}}''') is False
    assert not page.locator('#btnExportPNG').is_disabled() and paths()==before
    page.evaluate('window.__DRAW__.updateArtboard({w:100000,h:100000})');page.locator('#exportScope').select_option('active')
    assert page.evaluate('window.__DRAW__.exportPNG()') is False
    page.evaluate('window.__DRAW__.clearCanvas();window.__DRAW__.updateArtboard({w:64,h:32})');page.locator('#pngScale').select_option('1')
    with page.expect_download() as got:page.locator('#btnExportPNG').click()
    assert struct.unpack('>II',Path(got.value.path()).read_bytes()[16:24])==(64,32)
    print('PASS: real image/png downloads at 1×/2×/4×; exact dimensions, gold pixels + transparent background; artwork-area menu export; blank export; error/size guard recovery.',flush=True)
    # Actual File/DataTransfer drop, shared parser, relative geometry and one-step undo.
    page.evaluate('window.__DRAW__.clearCanvas();window.__DRAW__.addRect(20,20,30,30);window.__DRAW__.setZoom(1);window.__DRAW__.pushHistory()')
    before=paths();boards=state()['artboards']
    drop([{'name':'shapes.svg','content':SVG}]);assert len(paths())==3,(paths(),page.locator('#toastAlert').inner_text())
    assert abs(min(p['x'] for path in paths()[1:] for p in path['points'])-250)<1
    assert abs(min(p['y'] for path in paths()[1:] for p in path['points'])-150)<1
    assert paths()[1]['fill']=='#ffb800' and paths()[1]['stroke']=='transparent'
    assert any(p['hasHandles'] for p in paths()[2]['points'])
    assert state()['artboards']==boards and not page.locator('#viewport').evaluate("el=>el.classList.contains('svg-drag-over')")
    imported=paths();undo();assert paths()==before;redo();assert paths()==imported
    # Both files are committed together, or neither is committed.
    drop([{'name':'one.svg','content':SVG},{'name':'two.SVG','content':SVG}]);assert len(paths())==7
    undo();assert paths()==imported
    for bad in ['<svg><path d="M 1"/></svg>','<svg><rect></svg>','<svg><script>alert(1)</script></svg>','<svg><image href="https://example.com/image.png"/></svg>','<svg><rect width="20" height="20" fill="url(https://example.com/x)"/></svg>']:
        drop([{'name':'good.svg','content':SVG},{'name':'bad.svg','content':bad}]);assert paths()==imported
    drop([{'name':'not-svg.png','content':'bad','type':'image/png'}]);assert paths()==imported
    # Compounds/curves/transforms/gradient styles share the Paste/Open parser.
    rich='<svg xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="g"><stop offset="0" stop-color="#ff0000"/><stop offset="1" stop-color="#0000ff"/></linearGradient></defs><g transform="translate(10 20) scale(2)" fill="#ffb800"><path d="M0 0H100V100H0Z M25 25V75H75V25Z"/><rect x="120" y="0" width="20" height="30" fill="url(#g)"/><path d="M0 120 A20 20 0 0 1 40 120" fill="none" stroke="#ffffff"/></g></svg>'
    drop([{'name':'rich.svg','content':rich}]);assert len(paths())==6,page.locator('#toastAlert').inner_text()
    last=paths()[-3:];assert sum(bool(p.get('moveTo')) for p in last[0]['points'])==1
    assert max(p['x'] for p in last[0]['points'])-min(p['x'] for p in last[0]['points'])==200
    assert last[1]['fillType']=='linear' and len(last[1]['gradient']['stops'])==2
    assert any(p['hasHandles'] for p in last[2]['points'])
    # Clipboard import uses exactly the same shape conversion.
    count=len(paths());assert page.evaluate('svg=>!!window.__DRAW__.pasteText(svg)',SVG);assert len(paths())==count+2
    saved=paths();page.wait_for_timeout(500);page.reload();page.wait_for_timeout(200);assert paths()==saved
    # Drag feedback clears on leave, and drops outside the canvas cannot navigate away.
    assert page.evaluate("""()=>{const dt=new DataTransfer();dt.items.add(new File(['x'],'x.svg'));const v=document.querySelector('#viewport');v.dispatchEvent(new DragEvent('dragenter',{bubbles:true,cancelable:true,dataTransfer:dt}));const visible=v.classList.contains('svg-drag-over');v.dispatchEvent(new DragEvent('dragleave',{bubbles:true,dataTransfer:dt}));const e=new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt});document.querySelector('header').dispatchEvent(e);return visible&&!v.classList.contains('svg-drag-over')&&e.defaultPrevented}""")
    page.evaluate("window.originalFileText=File.prototype.text;File.prototype.text=async()=>{throw Error('Could not read SVG file.')};void 0")
    drop([{'name':'failed.svg','content':SVG}]);assert paths()==saved
    page.evaluate('File.prototype.text=window.originalFileText;void 0')
    page.evaluate('File.prototype.text=function(){return new Promise(resolve=>window.resolveSVGRead=resolve)};void 0')
    drop([{'name':'slow.svg','content':SVG}],wait=False)
    page.wait_for_function("typeof window.resolveSVGRead === 'function'")
    page.evaluate('window.__DRAW__.clearCanvas()')
    page.evaluate('svg=>window.resolveSVGRead(svg)',SVG)
    page.wait_for_function('!window.__DRAW__.getState().svgDropBusy')
    page.evaluate('File.prototype.text=window.originalFileText;void 0')
    assert paths()==[] and 'Document changed' in page.locator('#toastAlert').inner_text()
    page.evaluate('paths=>{window.__DRAW__.loadOutline({paths});window.__DRAW__.selectAllPaths();window.__DRAW__.zoomToSelection()}',saved)
    page.locator('#btnExportPNG').scroll_into_view_if_needed();page.wait_for_timeout(2500)
    page.screenshot(path=str(ROOT/'planning/png-svg-drop.png'))
    assert not requests,requests
    assert not errors,errors
    print('PASS: dropped rectangles/circles add editable paths at drop location; one-step undo/redo; multi-file atomicity; malformed/unsupported input unchanged; transforms, compound holes, arcs, gradients, shared paste parser and reload; no external requests or browser errors.',flush=True)
    page.goto((ROOT/'ROADMAP.html').as_uri());page.wait_for_function('window.__ROADMAP__')
    page.evaluate("""()=>{const state=window.__ROADMAP__.seed();state.version=25;state.cards.find(c=>c.id==='p6-png').status='next';state.cards.find(c=>c.id==='p6-drop').status='queued';state.inbox=[{id:'saved-idea',title:'Keep this idea'}];localStorage.setItem('eve-roadmap-v1',JSON.stringify(state));}""")
    page.reload()
    assert page.evaluate("window.__ROADMAP__.getState().cards.filter(c=>['p6-png','p6-drop'].includes(c.id)).every(c=>c.status==='shipped')")
    assert page.evaluate("window.__ROADMAP__.getState().inbox[0].id")=='saved-idea'
    assert not errors,errors
    print('PASS: failed/delayed file reads and drag cleanup; roadmap migrates both cards to shipped and preserves inbox.',flush=True)
    browser.close()
