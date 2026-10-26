from pathlib import Path
import json
import sys
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600"><rect x="100" y="100" width="100" height="60" fill="#ffb800" stroke="none"/><circle cx="250" cy="200" r="30" fill="#00f0ff" stroke="#ffffff" stroke-width="2"/></svg>'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'], timeout=15000)
    page = browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__ && window.__ENTITY_VECTOR__')
    page.wait_for_timeout(100)
    def state(): return page.evaluate('window.__ENTITY_VECTOR__.getState()')
    def paths(): return page.evaluate('window.__DRAW__.serializeOutline().paths')
    def settle(): page.wait_for_function('!window.__ENTITY_VECTOR__.getState().busy',timeout=200000)
    page.evaluate('window.__DRAW__.clearCanvas(); window.__DRAW__.addPoint(50,50); window.__DRAW__.addPoint(120,80); window.__DRAW__.pushHistory();')
    original=paths()
    assert page.locator('#entityInsert').is_disabled()
    if '--offline' in sys.argv:
        page.evaluate('raw=>window.__ENTITY_VECTOR__.preview(raw)', SVG)
        page.locator('#entityModel').evaluate("el=>el.value='test-model'")
        page.locator('#entityPrompt').fill('test artwork')
    else:
        # A real browser → Entity model server → preview round trip.
        page.locator('#entityConnection').evaluate('(el)=>el.open=true')
        page.locator('#entityConnect').click(); settle()
        assert 'Connected' in state()['status'],state()
        model=page.locator('#entityModel').input_value()
        page.locator('#entityPrompt').fill('Create a simple gold rocket icon: a gold triangular body, two cyan triangular fins and one cyan circular window. Use only polygon and circle elements with hex fill colors and stroke="none". No background.')
        page.locator('#entityGenerate').click()
        assert state()['busy'] and page.locator('#entityInsert').is_disabled()
        settle()
        assert state()['pathCount']>0, state()
        assert paths()==original
        page.wait_for_function('document.querySelector("#entityImage").naturalWidth > 0')
        (Path('/tmp/open-vector-entity-live-preview.svg')).write_text(state()['svg'])
        page.locator('#entityConnection').evaluate('(el)=>el.open=false')
        page.locator('.inspector').evaluate('(el)=>el.scrollTop=0')
        page.screenshot(path=str(Path('/tmp/open-vector-entity-live-panel.png')))
        print('REAL MODEL PASS:',model,'generated',state()['pathCount'],'editable paths; document unchanged.',flush=True)
    page.locator('#entityInsert').click()
    assert len(paths())==len(original)+state()['pathCount']
    page.locator('#viewport').focus();page.keyboard.press('Control+z')
    assert paths()==original
    page.keyboard.press('Control+y')
    assert len(paths())==len(original)+state()['pathCount']
    # Clipboard controls use only the preview, never the canvas clipboard.
    page.evaluate('''svg=> { window.testClipboard=svg; Object.defineProperty(navigator,'clipboard',{configurable:true,value:{readText:async()=>window.testClipboard,writeText:async text=>{window.testClipboard=text}}}); }''',SVG)
    baseline=paths()
    page.locator('#entityPaste').click()
    page.wait_for_function('window.__ENTITY_VECTOR__.getState().pathCount===2')
    assert paths()==baseline
    # Rasterize the actual preview; both shapes must remain inside its viewBox.
    assert page.evaluate("""async () => {
        const image=document.querySelector('#entityImage'); await image.decode();
        const canvas=document.createElement('canvas'); canvas.width=image.naturalWidth; canvas.height=image.naturalHeight;
        const ctx=canvas.getContext('2d'); ctx.drawImage(image,0,0);
        const data=ctx.getImageData(0,0,canvas.width,canvas.height).data;
        let gold=0,cyan=0;
        for(let i=0;i<data.length;i+=4) {
            if(data[i]>220 && data[i+1]>140 && data[i+2]<30 && data[i+3]>200) gold++;
            if(data[i]<30 && data[i+1]>200 && data[i+2]>200 && data[i+3]>200) cyan++;
        }
        return gold>5000 && cyan>2000;
    }"""), 'Preview must display the whole gold rectangle and cyan circle'
    (Path('/tmp/open-vector-entity-fixture-preview.svg')).write_text(state()['svg'])
    page.locator('#entityCopy').click()
    page.wait_for_function('window.testClipboard === window.__ENTITY_VECTOR__.getState().svg')
    saved=state()['svg']
    # Strict parsing rejects active SVG and unsupported geometry instead of mounting it.
    for invalid in ['<svg><script>alert(1)</script></svg>','<svg><path d="M 1 1 A 2 2 0 0 1 5 5"/></svg>','<svg><path d="M 1"/></svg>','<svg><rect width="20" height="20" transform="rotate(30)"/></svg>']:
        assert page.evaluate('''raw=> { try { window.__ENTITY_VECTOR__.preview(raw);return false } catch {return true} }''',invalid)
        assert state()['svg']==saved and paths()==baseline
    # Manual paste fallback and validation after edits.
    page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{readText:async()=>{throw Error('denied')}}})")
    page.locator('#entityPaste').click()
    assert page.locator('#entitySourceDetails').evaluate('(el)=>el.open')
    page.locator('#entitySource').fill(SVG)
    assert page.locator('#entityInsert').is_disabled()
    page.locator('#entityApplySource').click()
    assert not page.locator('#entityInsert').is_disabled()
    # HTTP failure, malformed output and cancellation preserve preview and document.
    endpoint='http://127.0.0.1:8081/v1/chat/completions'
    page.route(endpoint,lambda route:route.fulfill(status=503,headers={'Access-Control-Allow-Origin':'*'},body='unavailable'))
    page.locator('#entityGenerate').click();settle()
    assert '503' in state()['status'] and state()['svg']==saved and paths()==baseline
    page.unroute(endpoint)
    page.route(endpoint,lambda route:route.fulfill(content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'choices':[{'message':{'content':'not SVG'}}]})))
    page.locator('#entityGenerate').click();settle()
    assert 'valid SVG' in state()['status'] and state()['svg']==saved and paths()==baseline
    page.unroute(endpoint)
    pending=[]
    page.route(endpoint,lambda route:pending.append(route))
    page.locator('#entityGenerate').click()
    page.wait_for_timeout(150)
    page.locator('#entityCancel').click()
    assert not state()['busy'] and state()['svg']==saved and paths()==baseline
    for route in pending:
        try: route.abort()
        except: pass
    page.unroute(endpoint)
    page.wait_for_timeout(300)
    page.reload();page.wait_for_timeout(200)
    assert state()['pathCount']==2 and not page.locator('#entityInsert').is_disabled()
    assert page.locator('#entityKey').input_value()==''
    assert paths()==baseline
    assert not errors,errors
    page.locator('.inspector').evaluate('(el)=>el.scrollTop=0')
    page.screenshot(path=str(Path('/tmp/open-vector-entity-panel.png')))
    print('PASS: isolated preview, editable insert/undo/redo, Copy/Paste/manual fallback, invalid SVG and HTTP failures, cancellation, preview reload, no browser errors.',flush=True)
    browser.close()
