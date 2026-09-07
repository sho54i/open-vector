"""Behavioral regressions and non-gating engine microbenchmarks."""
from pathlib import Path
import argparse
import json
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--baseline',action='store_true')
parser.add_argument('--report',type=Path)
args=parser.parse_args()
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((Path(__file__).resolve().parents[1]/'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__')
    page.wait_for_timeout(100)
    page.evaluate('window.__DRAW__.clearCanvas(); window.__DRAW__.addRect(100,100,80,60)')
    stable=page.evaluate('snapshot()===snapshot()')
    page.evaluate('window.__DRAW__.pushHistory(); undo()')
    after_undo=page.evaluate('window.__DRAW__.getState().pathCount')
    if not args.baseline:
        assert stable,'unchanged history snapshots must be identical'
        assert after_undo==0,'no-op history push must not consume Undo'
        page.evaluate('redo()')
        assert page.evaluate('window.__DRAW__.getState().pathCount')==1
        page.evaluate('window.__DRAW__.addRect(250,100,40,40); undo(); window.__DRAW__.pushHistory(); redo()')
        assert page.evaluate('window.__DRAW__.getState().pathCount')==2
    page.evaluate('window.__DRAW__.clearCanvas(); window.__DRAW__.addRect(100,100,80,60); window.__DRAW__.selectPoint(0,0)')
    page.locator('#entityConnection').evaluate('el=>el.open=true')
    field_outcomes={}
    for field in ['#entityEndpoint','#entityKey']:
        page.evaluate('window.__DRAW__.selectPoint(0,0)')
        x0=page.evaluate('window.__DRAW__.getState().selected.x')
        page.locator(field).focus();page.keyboard.press('ArrowRight');page.keyboard.press('n')
        x1=page.evaluate('window.__DRAW__.serializeOutline().paths[0].points[0].x')
        mode=page.evaluate('window.__DRAW__.getState().mode')
        field_outcomes[field]={'x0':x0,'x1':x1,'mode':mode}
        if not args.baseline: assert x1==x0 and mode=='direct',field_outcomes
    page.evaluate('window.__DRAW__.selectPoint(0,0)')
    x0=page.evaluate('window.__DRAW__.getState().selected.x')
    page.locator('#viewport').focus();page.keyboard.press('ArrowRight')
    assert page.evaluate('window.__DRAW__.getState().selected.x')==x0+1
    bench=page.evaluate('''() => {
        const measure = (fn, count) => {
            for(let i=0;i<5;i++) fn();
            const times=[];
            for(let trial=0;trial<5;trial++) {
                const start=performance.now(); for(let i=0;i<count;i++) fn();
                times.push(performance.now()-start);
            }
            return times.sort((a,b)=>a-b)[2];
        };
        const pressures=Array.from({length:20000},(_,i)=>(i%10+1)/10);
        const stroke={baseWidth:4,strength:0.75,pressures,
            pressureSum:pressures.reduce((a,b)=>a+b,0),pressureCount:pressures.length};
        const width=pencilWidth(stroke);
        const pressureMs=measure(()=>pencilWidth(stroke),2000);
        const previous=paths;
        let snapshotMs;
        try {
            paths=Array.from({length:100},()=>{
                const path=emptyPath();
                path.points=Array.from({length:100},(_,i)=>createPoint(i,i%7)); return path;
            });
            snapshotMs=measure(snapshot,20);
        } finally { paths=previous; }
        return {pressureMs,snapshotMs,width,pressureSamples:20000,widthReads:2000,snapshotAnchors:10000,snapshotReads:20};
    }''')
    assert not errors,errors
    report={'baseline':args.baseline,'snapshotStable':stable,'pathCountAfterNoopUndo':after_undo,'fieldOutcomes':field_outcomes,'benchmark':bench,'browser':browser.version}
    print(json.dumps(report,indent=2))
    if args.report: args.report.write_text(json.dumps(report,indent=2)+'\n')
    browser.close()
