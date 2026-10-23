"""Art filter controls, rendered pixels, composition, persistence and guards."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'],timeout=15000)
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.drawArtFiltersReady')
    def setup():
        page.evaluate("""()=>{__DRAW__.clearCanvas();__DRAW__.loadOutline({paths:[{closed:true,enableFill:true,fill:'#da632a',stroke:'transparent',points:[{x:100,y:100},{x:300,y:100},{x:300,y:300},{x:100,y:300}]}]});__DRAW__.selectPath(0);camera={x:50,y:50,scale:1};showGrid=false;pushHistory();draw();}""")
    state=lambda:page.evaluate('serializeOutline().paths')
    def field(id,value):
        page.locator('#'+id).fill(str(value));page.locator('#'+id).press('Tab')
    def ready():page.wait_for_function('paths.every(p=>!normalizeEffects(p.effects) || styledArtworkCache?.get(p)?.ready)')
    def pixels():
        return page.evaluate("""async()=>{const im=new Image();im.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(generateSVGString(null,{scope:'active'}));await im.decode();const c=document.createElement('canvas');c.width=800;c.height=600;const g=c.getContext('2d');g.drawImage(im,0,0);return Array.from({length:40},(_,i)=>Array.from(g.getImageData(120+i*3,170,1,1).data));}""")
    setup();original=state();base=pixels();evidence={}
    for preset in ['sketch','oil','bubbles']:
        setup()
        page.locator('#artPreset').select_option(preset);ready();rendered=pixels()
        assert rendered!=base,(preset,rendered[:3]);assert all(v[3]==255 for v in rendered),(preset,rendered)
        assert len(set(tuple(v) for v in rendered))>3,(preset,rendered)
        evidence[preset]=rendered[:3]
        assert state()[0]['points']==original[0]['points']
        field('artStrength',0);ready();assert pixels()==base,preset
        field('artStrength',100);ready();before=pixels();field('artSeed',9);ready();assert pixels()!=before,preset
        field('artScale',30);ready();assert pixels()!=before
    # Canvas visibly renders the bubble texture (not just a filter tag in exported SVG).
    canvas=page.evaluate("""()=>{deselect();draw();return Array.from({length:40},(_,i)=>{let p=screenFromWorld({x:120+i*3,y:170});return Array.from(ctx.getImageData(p.x*dpr,p.y*dpr,1,1).data)});}""")
    assert len(set(tuple(v) for v in canvas))>3 and canvas!=base
    page.evaluate('__DRAW__.selectPath(0)');saved=state();page.locator('#clearArtFilter').click();assert state()[0]['effects'] is None
    page.keyboard.press('Control+z');assert state()==saved
    page.keyboard.press('Control+y');assert state()[0]['effects'] is None
    page.evaluate('__DRAW__.selectPath(0)');page.locator('#artPreset').select_option('oil');page.locator('#styleShadow').check();field('styleBlurAmount',2);ready()
    e=state()[0]['effects'];assert e['art'] and e['shadow'] and e['blur']
    page.locator('#clearStyles').click();e=state()[0]['effects'];assert e['art'] and not e['shadow'] and not e['blur']
    page.locator('#styleShadow').check();page.locator('#clearArtFilter').click();e=state()[0]['effects'];assert e['shadow'] and 'art' not in e
    page.locator('#artPreset').select_option('sketch');saved=state();page.wait_for_timeout(1200);page.reload();page.wait_for_function('window.drawArtFiltersReady');ready();assert state()==saved
    page.evaluate('__DRAW__.selectPath(0);duplicateSelection()');assert state()[1]['effects']==saved[0]['effects']
    page.evaluate('copySelection();pasteInPlace()');assert state()[2]['effects']==saved[0]['effects']
    with page.expect_download() as dl:assert page.evaluate('exportPNG()')
    assert Path(dl.value.path()).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    setup();page.locator('#artPreset').select_option('sketch');before=state();hist=page.evaluate('history.length');field('artScale',0)
    assert state()==before and page.evaluate('history.length')==hist
    page.evaluate('paths[0].locked=true;updateInspector()');assert page.locator('#artPreset').is_disabled();assert not page.evaluate("changeArtFilter('clearArtFilter')")
    setup();page.locator('#artPreset').select_option('oil');page.evaluate('duplicateSelection()');page.locator('#artPreset').select_option('sketch');page.evaluate('__DRAW__.selectPaths([0,1])')
    assert page.locator('#artPreset').input_value()=='mixed';field('artStrength',25);v=state();assert [p['effects']['art']['preset'] for p in v]==['oil','sketch'] and all(p['effects']['art']['strength']==0.25 for p in v)
    # Filter output cannot fill transparent holes or escape a clipping mask.
    setup();page.locator('#artPreset').select_option('bubbles')
    page.evaluate("const mask=makeRectPath(150,150,100,100);paths.push(mask);__DRAW__.selectPaths([0,1]);clippingSelection('make')");ready()
    rgba=pixels();assert all(v[3]==0 for v in rgba[:9]) and rgba[20][3]==255,rgba
    page.evaluate('__DRAW__.selectPath(1)');assert page.locator('#artPreset').is_disabled()
    # Malformed recipes normalize to bounded primitives; no external SVG input is trusted.
    sanitized=page.evaluate("normalizeEffects({art:{preset:'oil',strength:99,scale:-20,seed:Infinity}})")
    assert sanitized['art']=={'preset':'oil','strength':1,'scale':2,'seed':1}
    assert page.evaluate("normalizeEffects({art:{preset:'<script>'}})") is None
    setup();page.locator('#artPreset').select_option('bubbles');ready();page.set_viewport_size({'width':768,'height':1024})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.locator('[data-panel="art-filters"]').screenshot(path='/tmp/open-vector-art-filters.png')
    board=browser.new_page();board.goto((ROOT/'ROADMAP.html').as_uri())
    board.evaluate("localStorage.setItem('eve-roadmap-v1',JSON.stringify({version:38,cards:[{id:'cx9tgwvz',status:'queued',updated:'2026-10-22T08:41:12.016Z',notes:'Keep this note'}],inbox:[{id:'custom',title:'Unrelated work'}]}))")
    board.reload();migrated=board.evaluate('state');cards=[c for c in migrated['cards'] if c['id']=='cx9tgwvz']
    seed=board.evaluate("({version:SEED.version,status:SEED_CARDS.find(c=>c.id==='cx9tgwvz').status})")
    assert len(cards)==1 and cards[0]['status']==seed['status'] and 'Keep this note' in cards[0]['notes']
    assert migrated['version']==seed['version'] and any(c['id']=='custom' for c in migrated['inbox'])
    board.reload();assert board.evaluate("state.cards.filter(c=>c.id==='cx9tgwvz').length")==1
    board.close()
    assert not errors,errors
    browser.close();print('PASS art filters:',evidence,'canvas texture, strength/scale/seed, composition, history/reload/copy, PNG, clipping and guards')
