"""Draw-cost probe: per-frame render time on a heavy document and renders per pointer burst.
Timings are diagnostic; the gating asserts are render coalescing and unchanged pixels."""
from pathlib import Path
import hashlib, json, sys
from playwright.sync_api import sync_playwright

SETUP = '''(profile) => {
    window.__DRAW__.clearCanvas();
    paths = Array.from({length: 300}, (_, k) => {
        const p = emptyPath();
        p.points = Array.from({length: 60}, (_, i) => createPoint(60 + (k % 20) * 60 + i, 60 + Math.floor(k / 20) * 50 + (i % 9) * 4));
        if (profile) { p.strokeWidth = 4; p.widthProfile = [{offset: 0, width: 0.2}, {offset: 0.5, width: 1.5}, {offset: 1, width: 0.2}]; }
        return p;
    });
    setMode('direct');
    selectedPath = paths[0]; selectedPaths = [];
    selectedPoints = paths.flatMap(p => p.points); selectedPoint = selectedPoints[0];
    draw();
}'''
TIME = '''() => { const t = []; for (let i = 0; i < 15; i++) { const s = performance.now(); draw(); t.push(performance.now() - s); }
    return +t.sort((a, b) => a - b)[7].toFixed(2); }'''
# 120 pointermoves in one task (a 240 Hz pen or coalesced burst), then count canvas clears = renders.
BURST = '''async () => {
    let clears = 0; const orig = ctx.clearRect; ctx.clearRect = function (...a) { clears++; return orig.apply(this, a); };
    setMode('hand'); const v = document.getElementById('viewport'), r = canvas.getBoundingClientRect();
    const ev = (type, i) => new PointerEvent(type, {bubbles: true, pointerId: 1, pointerType: 'mouse', buttons: 1, clientX: r.left + 300 + i, clientY: r.top + 300});
    canvas.dispatchEvent(ev('pointerdown', 0));
    const s = performance.now();
    for (let i = 1; i <= 120; i++) v.dispatchEvent(ev('pointermove', i));
    const ms = performance.now() - s, during = clears;
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const afterFrame = clears;
    v.dispatchEvent(ev('pointerup', 120));
    ctx.clearRect = orig;
    return {ms: +ms.toFixed(1), rendersDuringBurst: during, rendersAfterFrame: afterFrame, cameraX: camera.x};
}'''

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto((Path(__file__).resolve().parents[1] / 'vector_pen_tool.html').as_uri())
    page.wait_for_function('window.__DRAW__'); page.wait_for_timeout(100)
    out = {}
    page.evaluate(SETUP, False); out['drawMs_300x60_allPointsSelected'] = page.evaluate(TIME)
    pixels = hashlib.sha256(bytes(page.evaluate('() => Array.from(ctx.getImageData(0, 0, canvas.width, canvas.height).data)'))).hexdigest()
    page.evaluate(SETUP, True); out['drawMs_300x60_widthProfile'] = page.evaluate(TIME)
    page.evaluate(SETUP, False)
    out.update(page.evaluate('''() => { const m = f => { const t = []; for (let i = 0; i < 9; i++) { const s = performance.now(); f(); t.push(performance.now() - s); }
        return +t.sort((a, b) => a - b)[4].toFixed(2); };
        return {dragMoveMs_18kAnchors: m(() => moveSelectionBy(0, 0)), hoverMissMs: m(() => detectElementAt({x: 5000, y: 5000}))}; }'''))
    out['burst'] = page.evaluate(BURST)
    out['errors'] = errors
    print(json.dumps(out, indent=2))
    Path(__file__).with_name('draw_perf.sha256').write_text(pixels) if '--save-pixels' in sys.argv else None
    if '--check-pixels' in sys.argv:
        assert pixels == Path(__file__).with_name('draw_perf.sha256').read_text(), 'render output changed'
    if '--gate' in sys.argv:
        # pointerdown renders synchronously; the 120 moves add exactly one frame.
        assert out['burst']['rendersDuringBurst'] == 1 and out['burst']['rendersAfterFrame'] == 2, out['burst']
        assert out['burst']['cameraX'] != 0
    assert not errors, errors
    browser.close()
