"""Text and workspace outcomes through real browser controls."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((Path(__file__).resolve().parents[1]/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW_PANELS__')
    page.wait_for_timeout(150)
    def doc(): return page.evaluate('__DRAW__.serializeOutline()')
    def state(name='text'): return page.evaluate('(name)=>__DRAW_PANELS__.getState().find(p=>p.id===name)',name)
    page.locator('#textContent').fill('Hello BO8')
    page.locator('#textInsert').click()
    assert len(doc()['paths'])==1
    assert doc()['paths'][0]['textRecipe']['text']=='Hello BO8'
    assert len(doc()['paths'][0]['points'])>20
    page.evaluate('undo()'); assert len(doc()['paths'])==0
    page.evaluate('redo()'); assert len(doc()['paths'])==1
    page.evaluate('__DRAW__.selectPath(0)')
    page.locator('#textContent').fill('World')
    page.locator('#textFont').select_option('DejaVu Serif')
    page.locator('#textUpdate').click()
    assert len(doc()['paths'])==1 and doc()['paths'][0]['textRecipe']['text']=='World'
    page.evaluate('undo()'); assert doc()['paths'][0]['textRecipe']['text']=='Hello BO8'
    page.evaluate('redo()'); assert doc()['paths'][0]['textRecipe']['font']=='DejaVu Serif'
    svg=page.evaluate('__DRAW__.generateSVGString()')
    assert '<path' in svg and '<text' not in svg
    page.evaluate('__DRAW__.selectPath(0); __DRAW__.lockPath(0,true)')
    assert page.locator('#textUpdate').is_disabled()
    before=doc()['paths']
    page.locator('#textSize').fill('0'); assert page.locator('#textInsert').is_disabled()
    assert doc()['paths']==before
    page.locator('#textSize').fill('64')
    page.locator('#textFontFile').set_input_files('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
    page.wait_for_function("document.querySelector('#textFont').value==='DejaVuSans-Bold.ttf'")
    page.locator('#textInsert').click(); assert len(doc()['paths'])==2
    page.get_by_role('button',name='Collapse Text',exact=True).click()
    assert not page.locator('#textContent').is_visible() and state()['collapsed']
    page.get_by_role('button',name='Expand Text',exact=True).click()
    page.get_by_role('button',name='Move down Text',exact=True).click(); assert state()['order']==1
    page.get_by_role('button',name='Detach Text',exact=True).click(); assert state()['floating']
    attach=page.locator('[data-panel="text"] .panel-controls button').nth(3)
    assert attach.get_attribute('title')=='Attach Text'
    assert attach.get_attribute('data-icon')=='attach'
    page.get_by_role('button',name='Minimise Text',exact=True).click()
    assert state()['minimized'] and not page.locator('#textContent').is_visible()
    page.get_by_role('button',name='Restore Text',exact=True).click(); assert page.locator('#textContent').is_visible()
    page.get_by_role('button',name='Attach Text',exact=True).click(); assert not state()['floating']
    assert attach.get_attribute('title')=='Detach Text' and attach.get_attribute('data-icon')=='detach'
    page.get_by_role('button',name='Hide Text',exact=True).click(); assert state()['hidden']
    page.get_by_role('button',name='Tools',exact=True).click()
    page.get_by_role('menuitemcheckbox',name='○ Text',exact=True).click(); assert not state()['hidden']
    # Pointer drag out of sidebar and back into sidebar.
    page.locator('[data-panel="text"] .panel-header').scroll_into_view_if_needed()
    box=page.locator('[data-panel="text"] .panel-header').bounding_box()
    page.mouse.move(box['x']+20,box['y']+7); page.mouse.down();page.mouse.move(700,200,steps=12);page.mouse.up()
    assert state()['floating'],state()
    box=page.locator('[data-panel="text"] .panel-header').bounding_box()
    page.mouse.move(box['x']+20,box['y']+7); page.mouse.down();page.mouse.move(1300,100,steps=12);page.mouse.up()
    assert not state()['floating'],state()
    page.get_by_role('button',name='Collapse Text',exact=True).click()
    layout=state(); saved=doc()['paths']
    page.wait_for_timeout(400);page.reload();page.wait_for_function('window.__DRAW_PANELS__');page.wait_for_timeout(200)
    assert state()==layout
    assert doc()['paths']==saved
    assert page.locator('#textFont option[value="DejaVuSans-Bold.ttf"]').count()==1
    page.get_by_role('button',name='Expand Text',exact=True).click()
    # A glyph counter must remain transparent in the actual PNG export.
    page.evaluate('__DRAW__.clearCanvas()')
    page.locator('#textContent').fill('O')
    page.locator('#textFont').select_option('DejaVu Sans')
    page.locator('#textSize').fill('100')
    page.locator('#textInsert').click()
    bounds=page.evaluate('boundsOf(livePaths(),0)')
    with page.expect_download() as download:
        page.evaluate('__DRAW__.exportPNG()')
    import base64
    pixels=page.evaluate('''async ({data,b})=>{
        const im=new Image(); im.src='data:image/png;base64,'+data; await im.decode();
        const c=document.createElement('canvas');c.width=im.width;c.height=im.height;
        const ctx=c.getContext('2d');ctx.drawImage(im,0,0);
        const center=ctx.getImageData(Math.floor(b.minX+b.width/2),Math.floor(b.minY+b.height/2),1,1).data[3];
        const ink=[...ctx.getImageData(0,0,c.width,c.height).data].filter((v,i)=>i%4===3&&v>0).length;
        return {center,ink};
    }''',{'data':base64.b64encode(Path(download.value.path()).read_bytes()).decode(),'b':bounds})
    assert pixels['center']==0 and pixels['ink']>100,pixels
    old=doc()['paths']
    page.locator('#textFontFile').set_input_files({'name':'bad.ttf','mimeType':'font/ttf','buffer':b'invalid'})
    page.wait_for_function("document.querySelector('#textStatus').textContent.startsWith('Could not load font')")
    assert doc()['paths']==old
    page.locator('#textContent').fill('Two\nlines')
    page.locator('#textUpdate').click()
    assert doc()['paths'][0]['textRecipe']['text']=='Two\nlines'
    assert page.evaluate('boundsOf(livePaths(),0).height')>100
    page.locator('#viewport').focus();page.keyboard.press('Control+d')
    assert len(doc()['paths'])==2 and all(p['textRecipe']['text']=='Two\nlines' for p in doc()['paths'])
    page.evaluate('undo(); __DRAW__.selectPath(0)')
    page.screenshot(path=str(Path('/tmp/open-vector-text-panels.png')))
    assert not errors,errors
    print('PASS: text insert/update, font load, outlines, undo/redo, validation/lock, panel collapse/reorder/detach/minimise/hide/drag/dock and reload; no browser errors')
    roadmap=browser.new_page()
    roadmap.goto((Path(__file__).resolve().parents[1]/'ROADMAP.html').as_uri())
    roadmap.evaluate("""localStorage.setItem('eve-roadmap-v1',JSON.stringify({version:28,cards:[],inbox:[{id:'c6dq4mke',title:'My text card'},{id:'unrelated',title:'Keep me'}]}))""")
    roadmap.reload()
    migrated=roadmap.evaluate('__ROADMAP__.getState()')
    assert len([c for c in migrated['cards'] if c['id'] in ['c6dq4mke','cx0msoze'] and c['status']=='shipped'])==2
    assert [c['id'] for c in migrated['inbox']]==['unrelated']
    assert next(c for c in migrated['cards'] if c['id']=='c6dq4mke')['title']=='My text card'
    print('PASS: roadmap migration adds both review cards without duplicates and preserves unrelated inbox entries')
    browser.close()
