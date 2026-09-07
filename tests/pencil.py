from pathlib import Path
from playwright.sync_api import sync_playwright
import math

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto((Path(__file__).resolve().parents[1]/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__')
    page.evaluate('window.__DRAW__.clearCanvas(); window.__DRAW__.setZoom(1); window.__DRAW__.pushHistory()')
    def paths(): return page.evaluate('window.__DRAW__.serializeOutline().paths')
    box=page.locator('#vectorCanvas').bounding_box()
    x,y=box['x']+160,box['y']+200
    page.locator('#toolPencil').click()
    page.mouse.move(x,y); page.mouse.down()
    for i in range(1,101): page.mouse.move(x+i*2,y+40*math.sin(i/15))
    assert len(paths())==0, 'preview must not enter document'
    page.mouse.up()
    result=paths(); assert len(result)==1
    count=len(result[0]['points']); assert 2<=count<50, count
    page.keyboard.press('Control+z'); assert len(paths())==0
    page.keyboard.press('Control+y'); assert paths()==result
    page.mouse.click(x,y); assert paths()==result
    page.mouse.move(x,y); page.mouse.down(); page.mouse.move(x+100,y+60)
    page.keyboard.press('Escape'); page.mouse.up(); assert paths()==result
    page.keyboard.press('n')
    page.mouse.move(x,y); page.mouse.down(); page.mouse.move(x+100,y)
    page.evaluate("document.querySelector('#viewport').dispatchEvent(new PointerEvent('pointercancel',{pointerId:1,bubbles:true}))")
    page.mouse.up(); assert paths()==result
    page.mouse.move(x,y); page.mouse.down(); page.mouse.move(x+100,y)
    page.keyboard.press('v'); page.mouse.up(); assert paths()==result
    page.keyboard.press('n')
    page.mouse.move(x,y); page.mouse.down(); page.mouse.move(x+120,y,steps=60); page.mouse.up()
    assert len(paths())==2 and len(paths()[1]['points'])==2
    page.keyboard.press('Control+z'); assert paths()==result
    page.wait_for_timeout(500); page.reload(); page.wait_for_timeout(200)
    assert paths()==result
    assert not errors,errors
    print(f'PASS: 101 samples → {count} editable anchors; preview 0 paths → release 1 → undo 0 → redo 1; click/Escape/pointercancel/tool switch discard; straight stroke 2 anchors; reload preserved.')
    browser.close()
