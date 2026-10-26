"""Provider-independent assistant, browser tools and Help outcomes (no live model)."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
SVG='<svg xmlns="http://www.w3.org/2000/svg"><rect x="10" y="20" width="80" height="40" fill="#ffb800"/></svg>'
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000});errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri());page.wait_for_function('window.__VECTOR_ASSISTANT__')
    # Preserve layout preferences through the old panel-name migration.
    page.evaluate("localStorage.setItem('draw-panel-layout-v1',JSON.stringify({'entity-harness':{collapsed:true,order:0}}))")
    page.reload();page.wait_for_function('window.__VECTOR_ASSISTANT__')
    assert page.locator('[data-panel="vector-assistant"]').count()==1
    assert page.evaluate("JSON.parse(localStorage.getItem('draw-panel-layout-v1'))['vector-assistant'].collapsed")
    page.evaluate("localStorage.removeItem('draw-panel-layout-v1')")
    page.reload();page.wait_for_function('window.__VECTOR_ASSISTANT__')
    def call(name,args=None,code=None):
        result=page.evaluate('([name,args])=>__VECTOR_ASSISTANT__.callTool(name,args)',[name,args or {}])
        if code:
            assert not result['ok'] and result['error']['code']==code,result
            return result
        assert result['ok'],result
        return result['result']
    def artwork():return page.evaluate('serializeOutline().paths')
    tools=page.evaluate('__VECTOR_ASSISTANT__.listTools()')
    assert len(tools)==6 and all(t['inputSchema']['additionalProperties'] is False for t in tools)
    call('missing',code='UNKNOWN_TOOL');call('get_document',{'extra':True},'INVALID_ARGUMENT')
    call('preview_svg',{'svg':42},'INVALID_ARGUMENT')
    page.evaluate("__DRAW__.clearCanvas();__DRAW__.loadOutline({paths:[{closed:false,locked:true,points:[{x:10,y:10},{x:50,y:50}]}]});pushHistory()")
    before=artwork();doc=call('get_document')
    assert doc['pathIds'] and doc['outline']['paths'][0]['locked']
    page.wait_for_timeout(30);assert call('get_document')['documentRevision']==doc['documentRevision']
    page.evaluate('camera.x+=5;draw()');assert call('get_document')['documentRevision']==doc['documentRevision']
    preview=call('preview_svg',{'svg':SVG});assert preview['pathCount']==1 and preview['ready'] and artwork()==before
    good=preview['svg']
    call('preview_svg',{'svg':'<svg><script>alert(1)</script></svg>'},'INVALID_SVG')
    assert call('get_preview')['svg']==good and artwork()==before
    # Refreshing the same source still invalidates the review token.
    new=call('preview_svg',{'svg':SVG})
    args={'previewId':preview['previewId'],'documentRevision':doc['documentRevision'],'requestId':'first'}
    call('insert_preview',args,'STALE_PREVIEW');args['previewId']=new['previewId']
    page.evaluate("documentSettings.name='Changed document';pushHistory()")
    call('insert_preview',args,'STALE_DOCUMENT');args['documentRevision']=call('get_document')['documentRevision']
    page.evaluate('pointerDown=true');call('insert_preview',args,'BUSY');page.evaluate('pointerDown=false')
    page.evaluate("entity.source.value+=' '");call('insert_preview',args,'NOT_READY');page.evaluate('entity.source.value=entity.svg')
    inserted=call('insert_preview',args)
    assert inserted['pathCount']==1 and len(artwork())==2 and artwork()[0]==before[0]
    assert call('insert_preview',args)==inserted and len(artwork())==2
    call('insert_preview',{**args,'previewId':'other'},'REQUEST_CONFLICT')
    points=artwork()[1]['points'];assert max(p['x'] for p in points)-min(p['x'] for p in points)==80
    assert '<svg' in call('export_svg')['svg']
    page.locator('#viewport').focus();page.keyboard.press('Control+z');assert artwork()==before
    page.keyboard.press('Control+y');assert len(artwork())==2
    # Compatible provider request: explicitly entered model bypasses /models.
    page.locator('#entityConnection').evaluate('e=>e.open=true')
    page.locator('#entityEndpoint').fill('https://model.example/v1');page.locator('#entityModel').fill('custom-model')
    page.locator('#entityKey').fill('fixture-secret');page.locator('#entityPrompt').fill('a gold rectangle')
    requests=[]
    def generate(route):
        body=route.request.post_data_json;requests.append(body)
        assert body['model']=='custom-model' and 'chat_template_kwargs' not in body
        assert route.request.headers['authorization']=='Bearer fixture-secret'
        route.fulfill(content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'choices':[{'message':{'content':SVG}}]}))
    page.route('https://model.example/v1/chat/completions',generate)
    page.locator('#entityGenerate').click();page.wait_for_function('!__ENTITY_VECTOR__.getState().busy')
    assert len(requests)==1 and 'ready' in call('get_preview')['status'] and len(artwork())==2
    assert len(requests[0]['messages'])==2 and requests[0]['messages'][1]['content']=='a gold rectangle'
    assert 'fixture-secret' not in json.dumps([call('get_document'),call('get_preview'),call('get_help')])
    assert 'fixture-secret' not in page.evaluate('JSON.stringify(localStorage)')
    page.route('https://model.example/v1/models',lambda r:r.fulfill(content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps({'data':[{'id':'custom-model'},{'id':'second-model'}]})))
    page.locator('#entityConnect').click();page.wait_for_function('!__ENTITY_VECTOR__.getState().busy')
    assert page.locator('#assistantModels option').count()==2
    assert 'Connected' in call('get_preview')['status']
    # Busy preview replacement never races generation.
    page.unroute('https://model.example/v1/chat/completions');pending=[]
    page.route('https://model.example/v1/chat/completions',lambda r:pending.append(r))
    page.locator('#entityGenerate').click();page.wait_for_timeout(80)
    call('preview_svg',{'svg':SVG},'BUSY');page.locator('#entityCancel').click()
    for r in pending:
        try:r.abort()
        except Exception:pass
    # Help is keyboard accessible and isolates drawing shortcuts.
    page.locator('[data-menu="help"] .menu-item').focus();page.keyboard.press('Enter')
    page.locator('[data-menu="help"] [data-help="agents"]').click()
    assert page.locator('#vectorHelp').is_visible() and page.locator('[data-help-topic="agents"]').is_visible()
    old_mode=page.evaluate('currentMode');old_art=artwork()
    page.keyboard.press('p');page.keyboard.press('Control+z');assert page.evaluate('currentMode')==old_mode and artwork()==old_art
    with page.expect_download() as dl:page.locator('#downloadAgentSchema').click()
    schema=json.loads(Path(dl.value.path()).read_text());assert schema['tools']==tools
    with page.expect_download() as dl:page.locator('#downloadAgentDocs').click()
    assert Path(dl.value.path()).read_text()==(ROOT/'planning/vector-assistant.md').read_text()
    page.set_viewport_size({'width':768,'height':1024})
    box=page.locator('#vectorHelp').bounding_box();assert box['x']>=0 and box['x']+box['width']<=768 and box['height']<=1024
    page.screenshot(path=str(Path('/tmp/open-vector-vector-assistant-help.png')))
    page.keyboard.press('Escape');assert not page.locator('#vectorHelp').is_visible()
    assert page.locator('[data-menu="help"] .menu-item').evaluate('e=>e===document.activeElement')
    saved=artwork();page.wait_for_timeout(300);page.reload();page.wait_for_function('window.__VECTOR_ASSISTANT__')
    assert artwork()==saved and page.locator('#entityKey').input_value()==''
    assert call('get_preview')['pathCount']==1
    assert call('get_document')['documentRevision']!=args['documentRevision']
    # Roadmap migration adds this card once and preserves custom user notes.
    roadmap=browser.new_page();roadmap.on('pageerror',lambda e:errors.append(str(e)))
    roadmap.goto((ROOT/'ROADMAP.html').as_uri())
    assert roadmap.evaluate('state.version===SEED.version')
    roadmap.evaluate("state.version=SEED.version-1;state.cards=state.cards.filter(c=>c.id!=='c8g9lqt2');state.cards.push({id:'custom-test',title:'Keep me',phase:'P1',status:'queued',notes:'User notes',updated:'2026-10-22T00:00:00Z'});persist()")
    roadmap.reload()
    assert roadmap.evaluate("state.cards.filter(c=>c.id==='c8g9lqt2').length")==1
    assert roadmap.evaluate("state.cards.find(c=>c.id==='c8g9lqt2').status")=='testing'
    assert roadmap.evaluate("state.cards.find(c=>c.id==='cjriuz69').status")=='shipped'
    assert roadmap.evaluate("state.cards.find(c=>c.id==='custom-test').notes")=='User notes'
    roadmap.reload();assert roadmap.evaluate("state.cards.filter(c=>c.id==='c8g9lqt2').length")==1
    assert not errors,errors
    browser.close()
print('PASS: provider fixtures, six agent tools, preview → editable insertion, stale/retry guards, Undo/Redo, secret omission, reload/layout migration, Help keyboard/shortcuts/downloads/tablet')
