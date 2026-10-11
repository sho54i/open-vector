"""Install a local or live package into a disposable copy and exercise its editor."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import local_updater as u

parser=argparse.ArgumentParser()
parser.add_argument('--manifest',help='HTTPS release manifest; omit to use dist/releases')
a=parser.parse_args()
if a.manifest:
    m=u.validate_manifest(json.loads(u.download(a.manifest,256*1024)))
    blob=u.download(urljoin(a.manifest,m['package']),u.MAX_PACKAGE)
else:
    m=u.validate_manifest(json.loads((ROOT/'dist/releases/latest.json').read_text()))
    blob=(ROOT/'dist/releases'/m['package']).read_bytes()
with tempfile.TemporaryDirectory(prefix='draw-release-smoke-') as temp:
    root=Path(temp)
    (root/'vector_pen_tool.html').write_text('previous editor')
    (root/'my-artwork.json').write_text('keep me')
    assert u.install(root,m,u.unpack(m,blob))
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':900})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto((root/'vector_pen_tool.html').as_uri())
        page.wait_for_function('window.__DRAW_PANELS__');page.wait_for_timeout(100)
        assert page.evaluate('__DRAW__.getState().pathCount')==0
        page.locator('#textContent').fill('Updated from Vercel' if a.manifest else 'Package smoke')
        page.locator('#textInsert').click()
        assert page.evaluate('__DRAW__.getState().pathCount')==1
        page.evaluate('undo()');assert page.evaluate('__DRAW__.getState().pathCount')==0
        page.get_by_role('button',name='Detach Text',exact=True).click()
        assert page.get_by_role('button',name='Attach Text',exact=True).get_attribute('title')=='Attach Text'
        page.get_by_role('button',name='Attach Text',exact=True).click()
        assert not page.evaluate('__DRAW_PANELS__.getState().find(p=>p.id==="text").floating')
        assert not errors,errors
        browser.close()
    u.rollback(root)
    assert (root/'vector_pen_tool.html').read_text()=='previous editor'
    assert (root/'my-artwork.json').read_text()=='keep me'
print(f"PASS: {m['version']} package installed; editor opened, text 0→1→Undo 0, attach/detach, rollback and artwork preservation.")
