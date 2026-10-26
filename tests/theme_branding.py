from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.__DRAW_PANELS__');page.wait_for_timeout(150)
    assert page.title()=='OPEN-VECTOR — Vector Studio'
    assert page.locator('.brand-logo').evaluate('im=>im.complete&&im.naturalWidth>0')
    assert page.locator('.studio-credit').inner_text()=='miniscule solutions 2026'
    page.evaluate('__DRAW__.addRect(100,100,70,50); showGrid=false; draw()')
    before=page.evaluate('({svg:generateSVGString(),paths:serializeOutline().paths,history:history.length})')
    def pixel(): return page.evaluate('''()=>{const b=activeArtboard(),s=screenFromWorld({x:b.x+b.w*.6,y:b.y+b.h*.6});return [...ctx.getImageData(Math.round(s.x*dpr),Math.round(s.y*dpr),1,1).data]}''')
    dark=pixel()
    page.get_by_role('button',name='Switch to light theme',exact=True).click()
    assert page.locator('html').get_attribute('data-theme')=='light'
    light=pixel();assert light[:3]==[255,255,255] and light!=dark,(dark,light)
    after=page.evaluate('({svg:generateSVGString(),paths:serializeOutline().paths,history:history.length})')
    assert before==after,'Theme must not alter artwork, SVG or Undo history'
    page.screenshot(path=str(Path('/tmp/open-vector-theme-light.png')))
    page.reload();page.wait_for_function('window.__DRAW_PANELS__');page.wait_for_timeout(150)
    assert page.locator('html').get_attribute('data-theme')=='light'
    assert page.evaluate('serializeOutline().paths')==before['paths']
    page.get_by_role('button',name='Switch to dark theme',exact=True).click()
    assert page.locator('html').get_attribute('data-theme')=='dark'
    page.screenshot(path=str(Path('/tmp/open-vector-theme-dark.png')))
    page.set_viewport_size({'width':768,'height':1024})
    page.get_by_role('button',name='Switch to light theme',exact=True).click()
    assert page.locator('#themeToggle').is_visible()
    assert page.locator('.studio-credit').is_visible()
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(Path('/tmp/open-vector-theme-tablet.png')))
    assert not errors,errors
    print(f'PASS: logo/title/credit; theme pixel {dark}→{light}; unchanged artwork/SVG/history; reload; tablet; no browser errors')
    browser.close()
