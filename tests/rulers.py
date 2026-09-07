from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'], timeout=15000)
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto((Path(__file__).resolve().parents[1] / 'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__ && window.__DRAW__.getState()')
    page.evaluate('window.__DRAW__.clearCanvas()')
    box = page.locator('#vectorCanvas').bounding_box()
    def drag(x, y, xx, yy):
        page.mouse.move(box['x'] + x, box['y'] + y)
        page.mouse.down()
        page.mouse.move(box['x'] + xx, box['y'] + yy, steps=5)
        page.mouse.up()
    def guides():
        return page.evaluate('window.__DRAW__.serializeOutline().guides')
    drag(200, 10, 200, 250)
    assert len(guides()) == 1 and guides()[0]['axis'] == 'y'
    drag(10, 200, 350, 200)
    assert len(guides()) == 2 and guides()[1]['axis'] == 'x'
    page.keyboard.press('Delete')
    assert len(guides()) == 1
    page.keyboard.press('Control+z')
    assert len(guides()) == 2
    page.keyboard.press('Control+y')
    assert len(guides()) == 1
    drag(400, 250, 400, 320)
    expected = guides()
    assert expected[0]['position'] != 250
    for zoom in [0.05, 0.25, 1, 4, 64]:
        page.evaluate('(z) => window.__DRAW__.setZoom(z)', zoom)
        assert guides() == expected
        # Center the guide so its rendered pixels can be asserted at every zoom.
        page.evaluate('''() => { const d = window.__DRAW__; const g = d.getGuides()[0];
            const s = d.worldToScreen(0, g.position); d.panBy(0, 320-s.y); d.draw(); }''')
        assert page.evaluate('''() => { const c = document.querySelector('canvas'); const ctx=c.getContext('2d');
            const data=ctx.getImageData(400,319,100,3).data;
            for(let i=0;i<data.length;i+=4) if((data[i]<20 && data[i+1]>180 && data[i+2]>180) || (data[i]>220 && data[i+1]>140 && data[i+2]<30)) return true;
            return false; }''')
    page.wait_for_timeout(400)
    page.reload()
    page.wait_for_timeout(200)
    assert guides() == expected
    import json
    payload = page.evaluate('window.__DRAW__.serializeOutline()')
    page.evaluate('window.__DRAW__.clearCanvas()')
    page.locator('#fileLoad').set_input_files({'name': 'guides.json', 'mimeType': 'application/json', 'buffer': json.dumps(payload).encode()})
    page.wait_for_timeout(100)
    assert guides() == expected
    assert not errors, errors
    print('PASS: ruler drags 0→2 guides; delete 2→1; undo 1→2; redo 2→1; move; visible at 5%–6400%; guide-only session reload; no browser errors.')
    browser.close()
