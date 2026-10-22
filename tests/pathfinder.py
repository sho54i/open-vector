from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'],timeout=15000)
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__')
    def doc(): return page.evaluate('window.__DRAW__.serializeOutline().paths')
    def setup(shapes):
        page.evaluate('''shapes=>{const d=window.__DRAW__; d.clearCanvas();d.loadOutline({paths:shapes});d.setZoom(1);d.selectPaths(shapes.map((_,i)=>i));d.pushHistory();}''',shapes)
    def rect(x,y,w,h,**extra):
        return dict(points=[{'x':x,'y':y},{'x':x+w,'y':y},{'x':x+w,'y':y+h},{'x':x,'y':y+h}],closed=True,enableFill=True,fill='#ffb800',**extra)
    def run(op): return page.evaluate('op=>window.__DRAW__.booleanSelection(op)',op)
    def area():
        # Independent signed polygon area for the straight-edged rectangle fixtures.
        total=0
        for path in doc():
            contours=[]
            for pt in path['points']:
                if not contours or pt.get('moveTo'): contours.append([])
                contours[-1].append(pt)
            total+=abs(sum(sum(a['x']*b['y']-b['x']*a['y'] for a,b in zip(c,c[1:]+c[:1]))/2 for c in contours))
        return total
    setup([rect(100,100,100,100),rect(150,150,100,100)])
    before=doc()
    assert page.locator('[data-cmd="unite"]').count()==1, 'Unite command is missing'
    page.locator('[data-menu="path"] .menu-item').click()
    page.locator('[data-cmd="unite"]').click()
    assert len(doc())==1 and doc()[0]['closed'] and len(doc()[0]['points'])>=3
    assert abs(area()-17500)<0.01,area()
    united=doc()
    page.locator('#viewport').focus();page.keyboard.press('Control+z');assert doc()==before
    page.keyboard.press('Control+y');assert doc()==united
    print('PASS: menu Unite: 2 paths → 1 closed path; area 17,500; Undo restores both, Redo restores result.',flush=True)
    setup([rect(100,100,100,100),rect(150,150,100,100)])
    page.locator('[data-boolean="subtract"]').click()
    assert len(doc())==1 and abs(area()-7500)<0.01
    # Subtraction order is document stacking, not selection click order.
    setup([rect(100,100,100,100),rect(150,150,100,100)])
    page.evaluate('window.__DRAW__.selectPaths([1,0])'); assert run('subtract')
    assert abs(area()-7500)<0.01 and min(p['x'] for p in doc()[0]['points'])==100
    # A fully enclosed cutter must leave a real transparent hole, in one editable object.
    setup([rect(100,100,200,200),rect(150,150,100,100)])
    assert run('subtract'); ring=doc()
    assert len(ring)==1 and sum(bool(p.get('moveTo')) for p in ring[0]['points'])==1
    assert abs(area()-30000)<0.01
    assert page.evaluate('window.__DRAW__.hitAt(125,125)') is not None
    assert page.evaluate('window.__DRAW__.hitAt(200,200)') is None
    # Rasterize exported SVG to assert transparency, not just contour counts.
    pixels=page.evaluate('''async()=>{
        const svg=window.__DRAW__.generateSVGString();const im=new Image();im.src='data:image/svg+xml,'+encodeURIComponent(svg);await im.decode();
        const c=document.createElement('canvas');c.width=im.naturalWidth;c.height=im.naturalHeight;const ctx=c.getContext('2d');ctx.drawImage(im,0,0);
        return [ctx.getImageData(41,41,1,1).data[3],ctx.getImageData(116,116,1,1).data[3]];
    }''')
    assert pixels==[255,0],pixels
    # Compound geometry survives JSON, clone/duplicate, movement, and save/reload.
    page.evaluate('window.__DRAW__.loadOutline(window.__DRAW__.serializeOutline());window.__DRAW__.selectPath(0)')
    assert doc()==ring
    page.locator('#viewport').focus();page.keyboard.press('Control+d')
    assert len(doc())==2 and sum(bool(p.get('moveTo')) for p in doc()[1]['points'])==1
    page.keyboard.press('Control+z'); assert doc()==ring
    page.evaluate('window.__DRAW__.selectPath(0)'); page.keyboard.press('ArrowRight')
    assert all(a['x']==b['x']+1 for a,b in zip(doc()[0]['points'],ring[0]['points']))
    page.keyboard.press('Control+z');assert doc()==ring
    # Inserting on a hole's closing edge must not connect it to the outer contour.
    hole_start=next(i for i,p in enumerate(ring[0]['points']) if p.get('moveTo'))
    a,b=ring[0]['points'][-1],ring[0]['points'][hole_start]
    inserted=page.evaluate('p=>window.__DRAW__.insertAnchorAt(p.x,p.y)',{'x':(a['x']+b['x'])/2,'y':(a['y']+b['y'])/2})
    assert inserted and len(doc()[0]['points'])==9 and abs(area()-30000)<0.01
    page.keyboard.press('Control+z');assert doc()==ring
    # SVG round-trip keeps the compound result and its hole.
    svg=page.evaluate('window.__DRAW__.generateSVGString()')
    page.evaluate('svg=>{window.__DRAW__.clearCanvas();window.__DRAW__.pasteText(svg,{merge:true,offset:false});}',svg)
    assert len(doc())==1 and abs(area()-30000)<0.01
    assert sum(bool(p.get('moveTo')) for p in doc()[0]['points'])==1
    setup(ring)
    # Direct-select editing and deleting the first anchor of a hole retain its contour boundary.
    hole_index=next(i for i,p in enumerate(ring[0]['points']) if p.get('moveTo'))
    page.evaluate('i=>window.__DRAW__.selectPoint(0,i)',hole_index)
    assert page.evaluate("window.__DRAW__.setAnchorCoordinate('x',155)")
    assert doc()[0]['points'][hole_index]['x']==155
    page.keyboard.press('Control+z')
    page.evaluate('i=>window.__DRAW__.selectPoint(0,i)',hole_index)
    page.keyboard.press('Delete')
    assert len(doc()[0]['points'])==7 and sum(bool(p.get('moveTo')) for p in doc()[0]['points'])==1
    page.keyboard.press('Control+z');assert doc()==ring
    page.wait_for_timeout(500);page.reload();page.wait_for_timeout(200);assert doc()==ring
    print('PASS: Subtract area 7,500; contained subtraction area 30,000; SVG hole alpha 0; compound edit/delete, duplicate, move, JSON and reload.',flush=True)
    # Disconnected output, shared edges, identical shapes, multiple cutters, empty subtraction.
    setup([rect(100,100,50,50),rect(200,100,50,50)]); assert run('unite')
    assert len(doc())==1 and abs(area()-5000)<0.01
    setup([rect(100,100,50,50),rect(150,100,50,50)]);assert run('unite');assert abs(area()-5000)<0.01
    setup([rect(100,100,50,50),rect(100,100,50,50)]);assert run('unite');assert abs(area()-2500)<0.01
    setup([rect(100,100,50,50),rect(90,90,80,80)]);before=doc();assert run('subtract');assert doc()==[]
    page.locator('#viewport').focus();page.keyboard.press('Control+z');assert doc()==before
    setup([rect(100,100,200,100),rect(150,90,20,120),rect(230,90,20,120)]);assert run('subtract');assert abs(area()-16000)<0.01
    # Reject open, locked, hidden and insufficient selections without document mutation.
    for invalid in [dict(closed=False),dict(locked=True),dict(visible=False)]:
        shapes=[rect(100,100,100,100),rect(150,150,100,100)];shapes[1].update(invalid);setup(shapes)
        before=doc();assert run('unite') is False;assert doc()==before
    setup([rect(100,100,100,100)]);before=doc();assert run('subtract') is False;assert doc()==before
    assert page.locator('[data-boolean="unite"]').is_disabled()
    # Curves remain cubic, with finite handles; no polygon flattening.
    page.evaluate('window.__DRAW__.clearCanvas();window.__DRAW__.setZoom(1)')
    for x in [100,160]:
        page.locator('#toolEllipse').click()
        corners=page.evaluate('x=>[window.__DRAW__.worldToScreen(x,100),window.__DRAW__.worldToScreen(x+120,200)]',x)
        box=page.locator('#vectorCanvas').bounding_box()
        page.mouse.move(box['x']+corners[0]['x'],box['y']+corners[0]['y']);page.mouse.down()
        page.mouse.move(box['x']+corners[1]['x'],box['y']+corners[1]['y'],steps=5);page.mouse.up()
    page.evaluate('window.__DRAW__.selectPaths([0,1]);window.__DRAW__.pushHistory()')
    assert run('unite')
    assert len(doc())==1 and any(p['hasHandles'] for p in doc()[0]['points'])
    assert page.evaluate('window.__DRAW__.serializeOutline().paths.every(p=>p.points.every(a=>[a,a.cp1,a.cp2].every(v=>Number.isFinite(v.x)&&Number.isFinite(v.y))))')
    # Appearance, unrelated layers and backmost stack position are preserved.
    base=rect(100,100,100,100,name='base',stroke='#112233',strokeWidth=5,strokeDash=[4,2])
    top=rect(150,150,100,100,name='top');top['fill']='#00f0ff'
    setup([rect(0,0,20,20,name='behind'),base,rect(400,100,20,20,name='between'),top])
    before=doc();page.evaluate('window.__DRAW__.selectPaths([3,1])');assert run('unite')
    after=doc();assert len(after)==3 and after[0]==before[0] and after[2]==before[2]
    assert after[1]['fill']=='#ffb800' and after[1]['stroke']=='#112233' and after[1]['strokeWidth']==5 and after[1]['strokeDash']==[4,2]
    # A Boolean result can participate in another operation (fill the hole again).
    setup(ring+[rect(150,150,100,100)]);assert run('unite');assert abs(area()-40000)<0.01
    # Missing engine and calculation errors leave artwork intact.
    setup([rect(100,100,100,100),rect(150,150,100,100)]);before=doc()
    assert page.evaluate("()=>{const original=paper.Path.prototype.unite;paper.Path.prototype.unite=()=>{throw Error('test failure')};try{return window.__DRAW__.booleanSelection('unite')}finally{paper.Path.prototype.unite=original}}") is False
    assert doc()==before
    # Preview artifact shows a directly editable hole and the Pathfinder controls.
    setup(ring);page.evaluate('window.__DRAW__.selectPoint(0,4);window.__DRAW__.zoomToSelection()')
    page.locator('[data-boolean="subtract"]').scroll_into_view_if_needed()
    page.wait_for_timeout(2000)
    page.screenshot(path=str(ROOT/'planning/pathfinder.png'))
    assert not errors,errors
    print('PASS: disjoint/touching/identical shapes, empty subtraction + undo, multiple cutters, invalid input guards, cubic preservation; no browser errors.',flush=True)
    page.goto((ROOT/'ROADMAP.html').as_uri())
    page.wait_for_function('window.__ROADMAP__')
    next_card=page.evaluate("window.__ROADMAP__.seed().cards.find(c=>c.status==='next')?.id || null")
    assert page.evaluate("window.__ROADMAP__.getState().cards.find(c=>c.id==='p6-bool').status")=='shipped'
    page.evaluate("""()=>{const state=window.__ROADMAP__.seed();state.version=23;state.cards.find(c=>c.id==='p6-bool').status='next';state.cards.find(c=>c.id==='p6-artboards').status='queued';state.inbox=[{id:'keep-me',title:'Keep my idea'}];localStorage.setItem('eve-roadmap-v1',JSON.stringify(state));}""")
    page.reload()
    assert page.evaluate("window.__ROADMAP__.getState().cards.find(c=>c.id==='p6-bool').status")=='shipped'
    if next_card:
        assert page.evaluate("id=>window.__ROADMAP__.getState().cards.find(c=>c.id===id).status",next_card)=='next'
    else:
        assert page.evaluate("window.__ROADMAP__.getState().cards.filter(c=>['p6-bool','p6-artboards'].includes(c.id)).every(c=>c.status==='shipped')")
    assert page.evaluate("window.__ROADMAP__.getState().inbox[0].id")=='keep-me'
    print('PASS: compound closing-edge insertion, SVG round-trip, style/layer preservation, repeated operations, atomic engine failure, and roadmap migration preserving inbox.',flush=True)
    browser.close()
