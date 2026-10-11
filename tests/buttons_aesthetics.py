from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    load=lambda:(page.goto((ROOT/'vector_pen_tool.html').as_uri()),page.wait_for_function('window.__DRAW_PANELS__'),page.wait_for_timeout(1400))
    load()
    # Menus: left-aligned beside the logo, pinned to the header top, context slot below.
    logo=page.locator('.brand-logo').bounding_box();file=page.locator('.menu-item').first.bounding_box()
    assert file['x']-(logo['x']+logo['width'])<40 and file['y']<20,(logo,file)
    assert page.locator('#contextBar').bounding_box()['y']>file['y']+file['height']-1
    # Icon-only buttons with hover context.
    for sel in ['#themeToggle','#pencilUndo','#pencilRedo','#pencilFinish','#toggleInspector','#zoomToggle','#hudToggle']:
        b=page.locator(sel);assert b.locator('svg').count()==1 and b.inner_text().strip()=='',sel
        assert b.get_attribute('title') and b.bounding_box()['width']<=40,sel
    # Zoom collapses to the magnifier, expands on hover, pins on click, flashes on zoom change.
    zoom=page.locator('#zoomLabel');assert not zoom.is_visible()
    page.locator('#zoomToggle').hover();assert zoom.is_visible()
    page.mouse.move(600,500);page.wait_for_timeout(50);assert not zoom.is_visible()
    page.locator('#zoomToggle').click();page.mouse.move(600,500);page.locator('#viewport').focus()
    assert zoom.is_visible() and page.locator('#zoomToggle').get_attribute('aria-expanded')=='true'
    page.locator('#zoomToggle').click();page.mouse.move(600,500);page.locator('#viewport').focus();assert not zoom.is_visible()
    page.evaluate("runCmd('zoomIn')");assert zoom.is_visible();page.wait_for_timeout(1400);assert not zoom.is_visible()
    # Coordinates hide/show and remember.
    hud=page.locator('.hud-readout');assert hud.is_visible()
    page.locator('#hudToggle').click();assert not hud.is_visible()
    load();assert not hud.is_visible()
    page.locator('#hudToggle').click();assert hud.is_visible()
    # Panel controls share the title row and reveal on hover.
    ctl=page.locator('[data-panel="text"] .panel-controls');head=page.locator('[data-panel="text"] .panel-header')
    page.mouse.move(600,500);page.wait_for_timeout(200);assert ctl.evaluate('e=>getComputedStyle(e).opacity')=='0'
    head.hover(position={'x':10,'y':6});page.wait_for_timeout(200);assert ctl.evaluate('e=>getComputedStyle(e).opacity')=='1'
    assert head.bounding_box()['height']<=30,'controls stay on the title row'
    # Inspector title follows state.
    page.locator('#toggleInspector').click();assert page.locator('#toggleInspector').get_attribute('title')=='Show inspector'
    page.locator('#toggleInspector').click()
    page.set_viewport_size({'width':768,'height':1024});page.wait_for_timeout(100)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert page.locator('.menu-item').last.bounding_box()['y']<20,'menus stay on the top row at tablet width'
    page.screenshot(path=str(ROOT/'planning/buttons-tablet.png'))
    assert not errors,errors
    print('PASS: menus top-left + context slot; icon buttons with titles; zoom collapse/hover/pin/flash; coordinates hide + reload; tablet fit; no browser errors')
    browser.close()
