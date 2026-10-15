from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
# Rasterize an SVG string in-page and return the RGB at fractional (fx, fy) points.
SAMPLE="""async ([svg, pts]) => { const img = new Image(); img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg); await img.decode();
  const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight; const x = c.getContext('2d'); x.drawImage(img, 0, 0);
  return pts.map(([fx, fy]) => Array.from(x.getImageData(Math.round(fx * (c.width - 1)), Math.round(fy * (c.height - 1)), 1, 1).data).slice(0, 3)); }"""
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    load=lambda:(page.goto((ROOT/'vector_pen_tool.html').as_uri()),page.wait_for_function('window.__DRAW_PANELS__'),page.wait_for_timeout(800))
    load()
    # A straight horizontal pen line: zero-height bbox, the case objectBoundingBox can't paint.
    page.locator('#toolPen').click();page.mouse.click(450,400);page.mouse.click(750,400);page.keyboard.press('Escape')
    page.locator('#toolSelect').click();page.mouse.click(600,400)
    assert page.evaluate('!!selectedPath'),'line selected'
    page.locator('[data-swatch="stroke"]').click(position={'x':20,'y':20})
    page.locator('[data-swap="gradient"]').click()
    st=lambda:page.evaluate("({t:selectedPath.strokeType,g:selectedPath.strokeGradient,s:selectedPath.stroke,w:selectedPath.strokeWidth})")
    assert st()['t']=='linear' and st()['g']['stops'][0]['color']=='#00f0ff',st()
    assert page.locator('#enableStrokeGrad').is_checked() and page.locator('#strokeGradFields').is_visible()
    assert 'grad' in page.locator('[data-swatch="stroke"]').get_attribute('class')
    # Canvas: the two ends of the line show the two stops.
    page.evaluate("selectedPath.strokeWidth=12;draw()")
    ends=page.evaluate("""() => { const c = document.getElementById('vectorCanvas'), x = c.getContext('2d'), r = devicePixelRatio || 1, b = c.getBoundingClientRect();
        return [[455, 404], [745, 404]].map(([sx, sy]) => Array.from(x.getImageData((sx - b.left) * r, (sy - b.top) * r, 1, 1).data).slice(0, 3)); }""")
    assert ends[0][2]>200 and ends[0][0]<80 and ends[1][0]>200 and ends[1][2]<80,('canvas ends cyan→gold',ends)
    # Inspector stop edit applies.
    stop=lambda i:page.locator('#strokeGradFields input[data-stop]').nth(i)
    stop(-1).evaluate("e=>{e.value='#ff0000';e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))}")
    assert st()['g']['stops'][-1]['color']=='#ff0000',st()
    # + adds a stop in the widest gap, coloured from its neighbours; × removes it again.
    page.locator('#strokeGradFields .stop-add').click()
    g=st()['g']['stops'];assert len(g)==3 and g[1]['offset']==0.5 and g[1]['color']=='#807880',g
    assert page.locator('#strokeGradFields input[data-stop]').count()==3
    page.locator('#strokeGradFields .stop-add').click();assert [s['offset'] for s in st()['g']['stops']]==[0,0.25,0.5,1]
    page.locator('#strokeGradFields .grad-stop').nth(1).hover();page.locator('#strokeGradFields [data-del="1"]').click()
    assert [s['offset'] for s in st()['g']['stops']]==[0,0.5,1],st()
    stop(1).evaluate("e=>{e.value='#00ff00';e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))}")
    assert st()['g']['stops'][1]['color']=='#00ff00'
    # SVG export paints both ends (userSpaceOnUse, not objectBoundingBox).
    page.evaluate("selectedPath.strokeWidth=12;draw()")
    svg=page.evaluate("generateSVGString()")
    assert 'sgrad-' in svg and 'userSpaceOnUse' in svg and 'stroke="url(#sgrad-' in svg,svg
    a,m,z=page.evaluate(SAMPLE,[svg,[[0.12,0.5],[0.5,0.5],[0.88,0.5]]])
    assert a[2]>200 and a[0]<80 and z[0]>200 and z[1]<80 and m[1]>200 and m[0]<80 and m[2]<80,('svg cyan→green→red',a,m,z)
    # Import the exported SVG back: stroke gradient survives.
    imp=page.evaluate("parseSVGArtwork(generateSVGString()).map(p=>({t:p.strokeType,stops:p.strokeGradient&&p.strokeGradient.stops.map(s=>s.color)}))")
    assert imp[0]['t']=='linear' and imp[0]['stops']==['#00f0ff','#00ff00','#ff0000'],imp
    # Undo, reload persistence, toggle off.
    page.keyboard.press('Control+z');assert page.evaluate("paths[0].strokeGradient.stops[1].color")!='#00ff00','undo reverts stop edit'
    page.keyboard.press('Control+y')
    page.wait_for_timeout(1200);load()
    assert page.evaluate("paths[0].strokeType")=='linear','survives reload'
    page.locator('#toolSelect').click();page.mouse.click(600,400)
    page.locator('[data-swatch="stroke"]').click(position={'x':20,'y':20})
    page.locator('[data-swap="gradient"]').click();assert st()['t']=='solid','second click toggles off'
    # Gradient on a no-stroke path gives it a visible stroke.
    page.locator('[data-swap="none"]').click();assert st()['s']=='transparent'
    page.locator('[data-swap="gradient"]').click();assert st()['t']=='linear' and st()['s']!='transparent',st()
    page.locator('.toolbar').screenshot(path=str(ROOT/'planning/stroke-gradient-swapper.png'))
    page.screenshot(path=str(ROOT/'planning/stroke-gradient.png'))
    assert not errors,errors
    print('PASS: stroke gradient via swapper + inspector stops, +/× stops, canvas ends, SVG export (straight line), re-import, undo, reload, toggle off, none→gradient')
    browser.close()
