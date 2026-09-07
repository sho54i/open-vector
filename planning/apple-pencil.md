# Apple Pencil UI and support

Shipped 2026-09-07 following user hardware verification on M1 iPad with Apple Pencil generation 2. Open `vector_pen_tool.html` in Safari using the same hosting workflow as the rest of DRAW.

## Controls

The first inspector section is Pencil & touch. Preferences persist locally across reloads, independently of artwork and undo history.

- Finger input: Ignore (default palm protection), Pan canvas, or Use current tool. A second pointer cannot change an active drawing or guide gesture. Pan is single-finger; use on-screen zoom buttons for zoom.
- Freehand base width: 0.5–16 document units, independent of the selected path's appearance.
- Pressure strength: 0–100%. For pen freehand only, multiplies base width by `1 + strength * (2 * averagePressure - 1)`, clamped to 0.5–16. Zero leaves width fixed. This is a uniform editable stroke, not variable-width ink. Missing positive pressure samples use neutral pressure.
- Smoothing: 0–100%, mapping to 0–8 screen pixels of freehand simplification. Endpoints remain. Settings are captured at stroke start.
- Selection reach: 7–20 screen pixels for pen hit testing, independent of zoom and visible anchor size.
- Pressure readout identifies pen events; it does not claim a particular Pencil model is connected.
- On-canvas Undo, Redo, Finish and Inspector toggle remove keyboard dependencies for common actions. Finish cancels a freehand draft or ends an open Pen path.
- Tablet controls have larger targets and form text; the toolbar scrolls. Inspector can be hidden to recover drawing space.

## Platform limits

Pointer Events support pen coordinates and pressure in Safari: https://webkit.org/blog/9674/new-webkit-features-in-safari-13/

This web implementation has no Pencil battery source. Check the iPad Batteries widget. It does not use device battery APIs as a substitute for Pencil battery. Barrel double-tap, squeeze, hover-specific tools, roll and haptics are not implemented. Apple's documented double-tap integration uses native APIs: https://developer.apple.com/documentation/applepencil/handling-double-taps-from-apple-pencil

Generation 2 onward is the intended input scope via standard pen events; later models require separate real-device verification.

## Automated verification

`python3 AREA-54/software-MD/DRAW/tests/apple_pencil.py`

Chromium synthetic pen/touch events verify width 0.8 → 3.2 for pressure 0.2 → 0.8, smoothing 28 → 2 anchors, active-stroke palm exclusion, cancellation, undo/redo, finger pan +80px, inspector visibility and settings persistence. Portrait screenshot is captured for inspection. Synthetic input does not prove iPad hardware delivery or OS palm rejection.

Existing Pencil, rulers, precision and snapping browser regressions pass.

## User device acceptance

1. Use Safari in landscape and portrait. Select the freehand Pencil tool. Draw several separate strokes quickly; each release should add one editable path. Undo/Redo should remove/restore one stroke.
2. Leave Finger input at Ignore. Rest your palm before and during drawing. No finger marks, unwanted selection or camera movement should occur.
3. Set base width to 4 and pressure strength to 100%. Draw light and firm strokes. Firm strokes should be visibly thicker. Set strength to 0% and verify equal widths. The live pressure readout should respond to your Pencil.
4. Compare smoothing at 0% and 100% on a wavy stroke. Higher smoothing should reduce anchors. Confirm selection reach helps select and drag anchors using Direct Select.
5. Test Pen path placement, Finish, shapes, selection, handle edits, tool switching and guide dragging. Check interruptions (switch apps during a stroke) do not leave an input lock or commit an unwanted draft.
6. Choose Finger input Pan and drag the canvas with one finger. Test zoom buttons and Inspector toggle. Return to Ignore before resting a palm on the canvas.
7. Reload: preferences and completed artwork should remain. Export SVG/PNG and inspect pressure-derived width. Battery guidance should direct you to the iPad widget, with no invented percentage.

Record iPadOS/Safari version and any missed strokes or interaction problems before marking shipped.

## Outcome-debug handoff

- Symptom: new Pencil support; no reported same-path partial failure.
- Layer triage: existing application freehand behavior passed before edits; added pen settings and pointer ownership at routing layer.
- Falsification: existing mouse freehand produced 11 anchors from 101 samples, with preview excluded from document and working undo.
- Outcome assertion: PASS for synthetic pen/touch width, geometry, camera movement and cancellation; user hardware verification passed with the accepted eraser-end exception.
- Runtime entry: `window.__DRAW__`; regression command above plus `tests/pencil.py`.

## User acceptance — 2026-09-07

User reports the test passed and all tested features work. The Apple Pencil eraser end did not work; user explicitly requested leaving it as-is unless a specific future need arises. Brushes and an eraser tool were mentioned as possible future additions, with no implementation requested. Later Pencil models remain unverified.
