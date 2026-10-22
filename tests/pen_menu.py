"""Pen long press, distinct icons, File submenu and unified paste outcomes."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.penFormsReady')
    assert page.locator('.inspector #documentForm').count()==0
    assert page.locator('[data-panel="anchor-points"]').count()==0
    page.locator('#toolPen').click();assert page.evaluate('currentMode')=='pen' and page.locator('#penMenu').is_hidden()
    icons=[]
    for mode in ['anchor-add','anchor-remove','anchor-convert','pen']:
        page.locator('#toolPen').hover();page.mouse.down();page.wait_for_timeout(500);assert page.locator('#penMenu').is_visible();page.mouse.up()
        page.locator('[data-pen-mode="'+mode+'"]').click()
        assert page.evaluate('currentMode')==mode
        assert page.locator('#toolPen').get_attribute('data-mode')==mode
        assert page.locator('#toolPen').evaluate("e=>e.classList.contains('active')")
        icons.append(page.locator('#toolPen svg').inner_html())
        assert 'data:image/svg+xml' in page.locator('#viewport').evaluate('e=>e.style.cursor')
    assert len(set(icons))==4
    # Keyboard alternative and dismissal; returning with P restores the pen icon.
    page.locator('#toolPen').focus();page.keyboard.press('ArrowDown');page.keyboard.press('ArrowDown');page.keyboard.press('Enter')
    assert page.evaluate('currentMode')=='anchor-add'
    page.keyboard.press('p');assert page.evaluate('currentMode')=='pen' and page.locator('#toolPen svg').inner_html()==icons[3]
    page.locator('#toolPen').focus();page.keyboard.press('ArrowDown');page.keyboard.press('Escape');assert page.locator('#penMenu').is_hidden()
    # Cancelled hold must never open later.
    page.locator('#toolPen').dispatch_event('pointerdown',{'button':0,'clientX':20,'clientY':200})
    page.locator('#toolPen').dispatch_event('pointercancel');page.wait_for_timeout(500);assert page.locator('#penMenu').is_hidden()
    # File hover opens the independent form; editing and Apply don't close its parent menu.
    page.locator('[data-menu="file"] .menu-item').click();page.locator('#documentMenuTrigger').hover()
    assert page.locator('#documentSubmenu').is_visible()
    page.locator('#documentName').fill('Hover setup');page.locator('#documentWidth').fill('640');page.locator('#documentForm button').click()
    assert page.evaluate('documentSettings.name')=='Hover setup' and page.evaluate('activeArtboard().w')==640
    assert page.locator('#documentSubmenu').is_visible()
    page.locator('#viewport').click(position={'x':250,'y':400});assert page.locator('#documentSubmenu').is_hidden()
    assert page.locator('[data-cmd="pasteInPlace"]').count()==0
    assert page.locator('[data-cmd="pasteInFront"]').count()==1
    # Touch long press opens the same choices without invoking a drawing action.
    page.locator('#toolPen').dispatch_event('pointerdown',{'button':0,'pointerType':'touch','clientX':20,'clientY':200})
    page.wait_for_timeout(500);page.locator('#toolPen').dispatch_event('pointerup',{'pointerType':'touch'});assert page.locator('#penMenu').is_visible()
    page.screenshot(path=str(ROOT/'planning/pen-tools.png'))
    page.keyboard.press('Escape');page.set_viewport_size({'width':768,'height':1024})
    page.locator('[data-menu="file"] .menu-item').click();page.locator('#documentMenuTrigger').click()
    box=page.locator('#documentSubmenu').bounding_box();assert box['x']>=0 and box['x']+box['width']<=768 and box['y']+box['height']<=1024
    page.screenshot(path=str(ROOT/'planning/document-menu.png'))
    assert not errors,errors;b.close()
print('PASS: four pen icons/cursors, long press, keyboard, touch, cancellation, File hover form, responsive bounds, single paste command')
