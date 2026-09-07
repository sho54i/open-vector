# Boolean / Pathfinder — shipped 2026-09-07

Select two or more visible, unlocked closed shapes with V / Shift-click or the Layers panel. Use Path > Unite / Subtract Front, or the inspector Pathfinder buttons. Subtract removes every selected front shape from the backmost selected shape. Both operations retain the backmost appearance and replace operands at its stack position. Empty subtraction removes the operands; one Undo restores them. Disconnected pieces and holes form one editable compound path.

## Implementation

- Paper.js core 0.12.18 is pinned under vendor/ with its MIT license and source hash. It operates on temporary items in an isolated scope. No CDN, server, or build step. Bézier handles are retained rather than flattening curves.
- `booleanSelection` computes and validates the entire result before replacing selected objects. Invalid selections and engine failures leave artwork/history unchanged.
- Outline version 3 adds optional `moveTo: true` on anchors that start additional contours, plus `fillRule` (default nonzero). Older outlines still load. All anchors remain in the ordinary points array, so transforms, bounds, selection, snapping and clipboard operate on every contour. Drawing, hit testing, segment insertion, smoothing and anchor deletion honor contour boundaries.
- SVG exports a compound path with separate M…Z contours and matching winding. SVG path paste/open preserves closed compound contours. Default nonzero is implicit for compatibility with the Entity preview parser; explicit evenodd is emitted when needed.
- Fixed outline loading of control coordinates equal to zero; they previously fell back to anchor coordinates.

## Verification

`python3 tests/pathfinder.py` in Chromium:

- UI Unite: two overlapping 100×100 rectangles become one closed path, area 17,500. Undo restores both originals; Redo restores the result.
- Subtract Front: area 7,500 regardless of selection click order. Contained subtraction: area 30,000; SVG hole alpha 0 and filled region alpha 255. Hole hit test is empty.
- Compound boundary insertion, direct anchor X editing, first-anchor deletion, duplicate, movement, SVG round-trip, JSON and session reload preserve contours.
- Disjoint, shared-edge and identical shapes, three operands, empty subtraction, locked/open/hidden/insufficient selections, curved ellipse union, subsequent union of a ring with its hole, appearance and unrelated layer order, forced engine failure.
- Precision, snapping, Pencil and offline Entity panel regression suites passed. No browser errors.

Screenshot: pathfinder.png. Runtime: window.__DRAW__.booleanSelection('unite' | 'subtract').

Outcome-debug triage: missing geometry commands, not an input failure. Baseline test failed on absent Unite. Final outcome: 2 paths → 1 closed editable result → Undo 2 → Redo 1. Next card: Multiple artboards.
