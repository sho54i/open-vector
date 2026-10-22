"""Library controls: real path mutations, undo, persistence and portable JSON."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
KEY = 'open-vector-library-v1'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW_PANELS__')
    page.evaluate('''() => { __DRAW__.clearCanvas(); __DRAW__.addRect(100,100,100,80);
        __DRAW__.addRect(240,100,100,80); paths[0].stroke='#123456'; paths[1].stroke='#654321';
        __DRAW__.selectPaths([0,1]); pushHistory(); }''')
    click = lambda name: page.get_by_role('button', name='Apply '+name, exact=True).click()
    values = lambda: page.evaluate('paths.filter(p=>p.points.length).map(p=>({fill:p.fill,stroke:p.stroke,width:p.strokeWidth,dash:p.strokeDash}))')
    before = values()
    click('#ff5577')
    assert [s['fill'] for s in values()] == ['#ff5577']*2
    assert [s['stroke'] for s in values()] == ['#123456','#654321']
    page.keyboard.press('Control+z'); assert values() == before
    page.keyboard.press('Control+y'); assert values()[0]['fill'] == '#ff5577'
    page.evaluate('__DRAW__.selectPaths([0,1])')
    click('Bold'); assert [s['width'] for s in values()] == [8,8]
    assert page.evaluate('pencilPrefs.width') == 8
    assert [s['stroke'] for s in values()] == ['#123456','#654321']
    page.keyboard.press('Control+z'); assert [s['width'] for s in values()] == [2,2]
    page.keyboard.press('Control+y')
    page.evaluate('__DRAW__.selectPaths([0,1])')
    click('Dashed'); assert values()[0]['dash'] == [8,4]
    svg = page.evaluate('generateSVGString()')
    assert 'stroke-dasharray="8 4"' in svg and 'stroke-linecap="butt"' in svg
    page.locator('#libraryName').fill('My dash'); page.locator('#savebrushes').click()
    page.locator('#libraryName').fill('Rose'); page.locator('#saveswatches').click()
    saved = page.evaluate('(key)=>JSON.parse(localStorage.getItem(key))',KEY)
    assert saved['swatches'][-1] == {'name':'Rose','color':'#ff5577'}
    # Switching target applies only the stroke; locked paths cannot be modified.
    page.locator('[data-swatch="stroke"]').click(position={'x':20,'y':20})
    page.evaluate('paths[0].locked=true')
    click('#7755cc')
    assert [s['stroke'] for s in values()] == ['#123456','#7755cc']
    assert values()[1]['fill'] == '#ff5577'
    page.evaluate('paths[0].locked=false; __DRAW__.selectPaths([])')
    click('Bold'); page.evaluate('__DRAW__.addRect(400,100,50,50)')
    assert values()[-1]['width'] == 8
    with page.expect_download() as download:
        page.locator('#exportLibrary').click()
    exported = json.loads(Path(download.value.path()).read_text())
    assert exported == saved
    def upload(data):
        page.locator('#libraryFile').set_input_files({'name':'library.json','mimeType':'application/json','buffer':json.dumps(data).encode()})
    upload(saved); page.wait_for_function("document.getElementById('libraryStatus').textContent.startsWith('Library imported')")
    assert page.evaluate('(key)=>JSON.parse(localStorage.getItem(key))',KEY) == saved
    upload({'format':KEY,'swatches':[{'name':'New','color':'#abcdef'}],'brushes':[{'name':'Broken'}]})
    page.wait_for_function("document.getElementById('libraryStatus').textContent.startsWith('Import failed')")
    assert page.evaluate('(key)=>JSON.parse(localStorage.getItem(key))',KEY) == saved, 'invalid import must be atomic'
    upload({'format':KEY,'swatches':[{'name':'<img onerror=alert(1)>','color':'#abc'}],'brushes':[]})
    page.wait_for_function("document.getElementById('libraryStatus').textContent.startsWith('Library imported')")
    assert page.locator('#swatchesList img').count() == 0
    page.wait_for_timeout(1200); page.reload(); page.wait_for_function('window.__DRAW_PANELS__')
    assert page.get_by_role('button',name='Apply Rose',exact=True).count() == 1
    assert page.get_by_role('button',name='Apply My dash',exact=True).count() == 1
    page.get_by_role('button',name='Remove Rose',exact=True).click()
    page.reload(); page.wait_for_function('window.__DRAW_PANELS__')
    assert page.get_by_role('button',name='Apply Rose',exact=True).count() == 0
    page.locator('[data-panel="brushes-and-swatches"]').screenshot(path='/tmp/open-vector-library.png')
    assert not errors, errors
    browser.close()
    print('PASS: swatches, brush width/dash, selection preservation, locks, undo/redo, new paths, SVG, save/remove/reload, JSON round trip and atomic invalid import')
