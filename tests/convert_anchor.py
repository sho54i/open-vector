"""Convert gestures: geometry, independent handles, history and cancellation."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.penFormsReady')
    page.evaluate("__DRAW__.clearCanvas();__DRAW__.loadOutline({paths:[{closed:true,points:[{x:100,y:100},{x:300,y:100},{x:300,y:300},{x:100,y:300}]}]});__DRAW__.selectPath(0);camera={x:50,y:50,scale:1};pushHistory();draw()")
    page.locator('#toolPen').hover();page.mouse.down();page.wait_for_timeout(500);page.mouse.up()
    page.locator('[data-pen-mode="anchor-convert"]').click()
    def coords(x,y):
        return page.evaluate('([x,y])=>{const s=screenFromWorld({x,y}),r=canvas.getBoundingClientRect();return [r.x+s.x,r.y+s.y]}',[x,y])
    def drag(a,b,cancel=False,shift=False):
        page.mouse.move(*coords(*a));page.mouse.down()
        if shift: page.keyboard.down('Shift')
        page.mouse.move(*coords(*b),steps=6)
        if cancel: page.locator('#viewport').dispatch_event('pointercancel', {'pointerId':1, 'pointerType':'mouse'})
        page.mouse.up()
        if shift: page.keyboard.up('Shift')
    info = lambda: page.evaluate('pointInfo(paths[0].points[0])')
    original = info()
    drag((100,100),(160,100))
    smooth = info()
    assert smooth['cp2']=={'x':160,'y':100} and smooth['cp1']=={'x':40,'y':100} and smooth['mirrored'],smooth
    assert smooth['x']==100 and smooth['y']==100
    page.keyboard.press('Control+z');assert info()==original
    page.keyboard.press('Control+y');assert info()==smooth, (info(), smooth)
    page.evaluate('setPathSelection([paths[0]]);selectedPoint=paths[0].points[0];selectedPoints=[selectedPoint];draw()')
    drag((160,100),(175,130))
    broken = info()
    assert broken['cp2']=={'x':175,'y':130} and broken['cp1']==smooth['cp1'] and broken['broken'],broken
    page.keyboard.press('Control+z');assert info()==smooth, (info(), smooth)
    drag((100,100),(140,140),cancel=True);assert info()==smooth, (info(), smooth)
    drag((100,100),(170,110),shift=True);assert info()['cp2']['y']==100 and info()['mirrored']
    page.mouse.click(*coords(100,100));assert not info()['hasHandles']
    page.mouse.click(*coords(100,100));assert info()['hasHandles']
    page.evaluate('paths[0].locked=true');before=info()
    drag((100,100),(180,100));assert info()==before
    page.evaluate('paths[0].locked=false;paths[0].visible=false')
    drag((100,100),(180,100));assert info()==before
    assert page.locator('#toolPen svg path').count()==1 and page.locator('#toolPen svg circle').count()==0
    assert ') 4 4,' in page.locator('#viewport').evaluate('e=>e.style.cursor')
    assert not errors,errors
    browser.close()
print('PASS: anchor stays (100,100); handles → (40,100)/(160,100); independent handle → (175,130); click toggle, Shift, undo/redo, cancellation, guards, delta icon/hotspot')
