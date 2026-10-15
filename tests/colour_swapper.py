from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.__DRAW_PANELS__');page.wait_for_timeout(800)
    # One closed rect, selected.
    page.locator('#toolRect').click();page.mouse.move(500,400);page.mouse.down();page.mouse.move(650,520,steps=5);page.mouse.up()
    page.locator('#toolSelect').click();page.mouse.click(500,400)
    path=lambda:page.evaluate("({fill:selectedPath.fill,on:selectedPath.enableFill,stroke:selectedPath.stroke})")
    sw=lambda t:page.locator(f'[data-swatch="{t}"]')
    z=lambda t:sw(t).evaluate("e=>getComputedStyle(e).zIndex")
    assert z('fill')=='1' and z('stroke')!='1','fill starts in front'
    s0=path()['stroke']
    btn=lambda a:page.locator(f'[data-swap="{a}"]').click()
    btn('black');assert path()['fill']=='#000000' and path()['on'],path()
    btn('black');assert path()['fill']=='#ffffff',path()
    btn('last');assert path()['fill']=='#000000',path()
    btn('none');assert not path()['on'],path()
    assert 'none' in sw('fill').get_attribute('class')
    btn('last');assert path()['on'] and path()['fill']=='#000000',path()
    # Swap focus to stroke by clicking the back swatch.
    sw('stroke').click(position={'x':20,'y':20});assert z('stroke')=='1'
    btn('black');assert path()['stroke']=='#000000';btn('last');assert path()['stroke']==s0,(path(),s0)
    btn('none');assert path()['stroke']=='transparent'
    # No-stroke survives an unrelated inspector edit.
    page.fill('#strokeWidthNum','5');page.press('#strokeWidthNum','Enter');assert path()['stroke']=='transparent',path()
    btn('last');assert path()['stroke']==s0
    btn('gradient');g=page.evaluate("({t:selectedPath.fillType,on:selectedPath.enableFill})")
    assert g=={'t':'linear','on':True},g;assert z('fill')=='1','gradient brings fill to front'
    assert 'linear-gradient' in sw('fill').evaluate("e=>getComputedStyle(e).backgroundImage")
    btn('gradient');assert page.evaluate("selectedPath.fillType")=='solid','second click toggles off'
    btn('gradient')
    page.locator('.toolbar').screenshot(path=str(ROOT/'planning/colour-swapper.png'))
    page.keyboard.press('Control+z');assert page.evaluate('paths[paths.length-1].fillType')=='solid','undo restores'
    assert not errors,errors
    print('PASS: swapper focus, black/white toggle, last used, none on front, gradient fill toggle, no-stroke persists, undo')
    browser.close()
