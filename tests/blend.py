"""Blend outcomes on editable paths, history, persistence and export."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True,args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((ROOT/'vector_pen_tool.html').as_uri()); page.wait_for_function('window.__DRAW_PANELS__')
    def setup():
        page.evaluate('''() => { __DRAW__.clearCanvas(); __DRAW__.addRect(100,100,80,60); __DRAW__.addRect(300,200,120,100);
            paths.forEach(p=>Object.assign(p,{fillType:'solid',strokeType:'solid',gradient:null,strokeGradient:null}));
            Object.assign(paths[0],{fill:'#ff0000',enableFill:true,stroke:'#000000',strokeWidth:2});
            Object.assign(paths[1],{fill:'#0000ff',enableFill:true,stroke:'#ffffff',strokeWidth:10});
            __DRAW__.selectPaths([0,1]); pushHistory(); }''')
    def blend(n=1):
        page.locator('#blendSteps').fill(str(n)); page.get_by_role('button',name='Create blend',exact=True).click()
    state=lambda:page.evaluate('serializeOutline().paths')
    setup(); before=state(); blend()
    result=state(); assert len(result)==3 and result[:2]==before
    mid=result[2]
    assert (mid['points'][0]['x'],mid['points'][0]['y'])==(200,150),mid
    assert mid['fill']=='#800080' and mid['stroke']=='#808080' and mid['strokeWidth']==6,mid
    assert mid['points'][1]['x']==300 and mid['points'][2]['y']==230
    assert page.evaluate('pathSelection().length')==1
    svg=page.evaluate('generateSVGString()'); assert svg.count('<path ')==3 and '#800080' in svg
    page.keyboard.press('Control+z'); assert state()==before
    page.keyboard.press('Control+y'); assert state()==result
    page.wait_for_timeout(1200); page.reload(); page.wait_for_function('window.__DRAW_PANELS__'); assert state()==result
    # Multiple intermediates have evenly spaced anchors and one-step undo.
    setup(); before=state(); blend(3); result=state()
    assert [v['points'][0]['x'] for v in result[2:]]==[150,200,250]
    assert [v['strokeWidth'] for v in result[2:]]==[4,6,8]
    page.keyboard.press('Control+z'); assert state()==before
    # Real canvas shift-click selection feeds the same command.
    page.evaluate('deselect(); setMode("select")')
    for i in [0,1]:
        pos=page.evaluate('(i)=>{const p=screenFromWorld(paths[i].points[0]),r=viewport.getBoundingClientRect();return {x:p.x+r.left,y:p.y+r.top}}',i)
        if i: page.keyboard.down('Shift')
        page.mouse.click(pos['x'],pos['y'])
        if i: page.keyboard.up('Shift')
    assert page.evaluate('pathSelection().length')==2
    blend(); assert len(state())==3
    # Curves interpolate effective handles (a corner contributes its anchor).
    setup()
    page.evaluate('''() => { paths[0].closed=false; paths[1].closed=false;
        paths[0].points=paths[0].points.slice(0,2); paths[1].points=paths[1].points.slice(0,2);
        Object.assign(paths[1].points[0],{hasHandles:true,cp1:{x:280,y:160},cp2:{x:320,y:240}}); pushHistory(); }''')
    blend(); point=state()[2]['points'][0]
    assert point['hasHandles'] and point['cp1']=={'x':190,'y':130} and point['cp2']=={'x':210,'y':170},point
    assert not state()[2]['closed']
    # Fill and stroke gradients, including solid-to-gradient conversion.
    setup()
    page.evaluate('''() => { paths[0].fillType='linear'; paths[0].gradient={x1:0,y1:0,x2:1,y2:0,stops:[{offset:0,color:'#ff0000'},{offset:1,color:'#00ff00'}]};
        paths[1].fillType='linear'; paths[1].gradient={x1:0,y1:0,x2:0,y2:1,stops:[{offset:0,color:'#0000ff'},{offset:1,color:'#ffffff'}]};
        paths[1].strokeType='linear'; paths[1].strokeGradient={stops:[{offset:0,color:'#ff0000'},{offset:1,color:'#ffffff'}]}; pushHistory(); }''')
    blend(); mid=state()[2]
    assert mid['fillType']=='linear' and [s['color'] for s in mid['gradient']['stops']]==['#800080','#80ff80']
    assert mid['gradient']['x2']==0.5 and mid['gradient']['y2']==0.5
    assert mid['strokeType']=='linear' and [s['color'] for s in mid['strokeGradient']['stops']]==['#800000','#808080']
    assert 'linearGradient' in page.evaluate('generateSVGString()')
    # Geometric blend can deliberately retain the first appearance.
    setup(); page.locator('#blendColours').uncheck(); blend(); mid=state()[2]
    assert mid['fill']=='#ff0000' and mid['stroke']=='#000000' and mid['strokeWidth']==6
    page.locator('#blendColours').check()
    # Rejected operations leave artwork AND undo history untouched.
    for mutate,message in [
        ('__DRAW__.selectPaths([0])','exactly two'),
        ('paths[1].locked=true','unlocked'),
        ('paths[1].visible=false','visible'),
        ('paths[1].points.pop()','matching anchor'),
        ('paths[1].points[2].moveTo=true','contours'),
        ('paths[1].closed=false','closure'),
        ('paths[1].enableFill=false','Enable fill'),
        ("paths[1].stroke='transparent'",'hex colours'),
    ]:
        setup(); page.evaluate(mutate); before=state(); hist=page.evaluate('history.length')
        blend(); assert message in page.locator('#blendStatus').inner_text(), (mutate,page.locator('#blendStatus').inner_text())
        assert state()==before and page.evaluate('history.length')==hist
    setup(); before=state()
    assert page.evaluate('createBlend(0,true)') is False
    assert page.evaluate('createBlend(1.5,true)') is False
    assert page.evaluate('createBlend(101,true)') is False
    assert state()==before
    setup()
    page.evaluate("paths.forEach((p,i)=>{p.fillType='linear';p.gradient={stops:Array.from({length:2+i},(_,j)=>({offset:j/(1+i),color:'#ffffff'}))}})")
    before=state(); blend(); assert 'same number' in page.locator('#blendStatus').inner_text(); assert state()==before
    setup(); blend(100); assert len(state())==102
    page.keyboard.press('Control+z'); assert len(state())==2
    # Compound contours retain independent starts and no source text recipe leaks.
    setup(); page.evaluate('paths.forEach(p=>{p.points[2].moveTo=true;p.textRecipe={text:"source"}})')
    blend(); mid=state()[2]; assert mid['points'][2]['moveTo'] and mid['textRecipe'] is None
    setup(); blend(5)
    page.locator('[data-panel="blend"]').screenshot(path='/tmp/open-vector-blend-panel.png')
    assert not errors,errors
    browser.close()
    print('PASS: blend midpoint geometry/colours/width, curves, gradients, source preservation, real Shift-selection, multi-step undo/redo, reload, SVG, geometry-only, compound paths and atomic rejection')
