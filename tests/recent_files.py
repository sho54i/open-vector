"""Recent-file browser copies: actual menu, document, history and storage outcomes."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
KEY = 'draw-recent-files-v1'
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((ROOT / 'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__')
    def paths():
        # SVG imports assign fresh generated layer names; compare geometry and style.
        result = page.evaluate('__DRAW__.serializeOutline().paths')
        for path in result: path.pop('name', None)
        return result
    def entries(): return page.evaluate('(key)=>JSON.parse(localStorage.getItem(key)||"[]")', KEY)
    def upload(name, source):
        page.locator('#fileLoad').set_input_files({'name': name, 'mimeType': 'text/plain', 'buffer': source.encode()})
    def menu():
        page.locator('[data-menu="file"] > .menu-item').click()
        if not page.locator('#recentFiles').evaluate('(el)=>el.open'):
            page.locator('#recentFiles summary').click()
    svg = '<svg xmlns="http://www.w3.org/2000/svg"><rect x="10" y="20" width="100" height="80" fill="#ff0000"/></svg>'
    upload('original.svg', svg)
    page.wait_for_function('(key)=>JSON.parse(localStorage.getItem(key)||"[]").length===1', arg=KEY)
    original = paths()
    assert len(original) == 1
    outline = page.evaluate('__DRAW__.serializeOutline()')
    outline['paths'][0]['points'][0]['x'] = 245
    upload('changed.json', json.dumps(outline))
    page.wait_for_function('(key)=>JSON.parse(localStorage.getItem(key)||"[]").length===2', arg=KEY)
    changed = paths()
    assert changed != original
    menu()
    page.get_by_role('button', name='original.svg', exact=True).click()
    assert paths() == original, (paths(), original)
    assert entries()[0]['name'] == 'original.svg' and len(entries()) == 2
    page.evaluate('undo()'); assert paths() == changed
    page.evaluate('redo()'); assert paths() == original, (paths(), original)
    upload('invalid.json', '{broken')
    page.wait_for_timeout(100)
    assert paths() == original and len(entries()) == 2
    page.wait_for_timeout(450); page.reload(); page.wait_for_function('window.__DRAW__')
    menu()
    # Keyboard activation of the native details disclosure and recent entry.
    page.locator('#recentFiles summary').focus(); page.keyboard.press('Enter')
    assert not page.locator('#recentFiles').evaluate('(el)=>el.open')
    page.keyboard.press('Enter')
    page.get_by_role('button', name='changed.json', exact=True).focus(); page.keyboard.press('Enter')
    assert paths() == changed
    for i in range(9):
        upload(f'file-{i}.svg', svg)
        page.wait_for_function('([key,name])=>JSON.parse(localStorage.getItem(key)||"[]")[0]?.name===name', arg=[KEY, f'file-{i}.svg'])
    assert len(entries()) == 8 and entries()[-1]['name'] == 'file-1.svg'
    before = paths()
    upload('large.svg', svg + ' ' * 1500000)
    page.wait_for_function("document.querySelector('#toastAlert').textContent.includes('Too large')")
    assert paths() == before and len(entries()) == 8
    menu(); page.locator('#clearRecentFiles').click()
    assert paths() == before and entries() == []
    page.wait_for_timeout(450); page.reload(); page.wait_for_function('window.__DRAW__'); menu()
    assert page.get_by_text('No recent files yet.', exact=True).is_visible()
    # Corrupt storage must not prevent startup or mutate the restored document.
    page.evaluate('(key)=>localStorage.setItem(key,"{invalid")', KEY)
    page.wait_for_timeout(450); page.reload(); page.wait_for_function('window.__DRAW__')
    assert paths() == before
    # A quota failure still opens the document and offers a same-tab copy.
    page.evaluate('''() => { const real = Storage.prototype.setItem;
        Storage.prototype.setItem = function(key,value) {
            if (key === 'draw-recent-files-v1') throw new DOMException('Full','QuotaExceededError');
            return real.call(this,key,value);
        }; }''')
    upload('quota.svg', svg)
    page.wait_for_function("document.querySelector('#toastAlert').textContent.includes('this tab only')")
    menu(); assert page.get_by_role('button', name='quota.svg', exact=True).is_visible()
    page.evaluate('__DRAW__.clearCanvas()'); assert len(paths()) == 0
    page.get_by_role('button', name='quota.svg', exact=True).click(); assert paths() == original, (paths(), original)
    assert not errors, errors
    print('PASS: recent SVG/JSON restores exact paths; Undo/Redo, keyboard, reload, deduplication, eight-entry cap, clear, malformed input/storage and quota fallback.')
    browser.close()
