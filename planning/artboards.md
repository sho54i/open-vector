# Multiple artboards — shipped 2026-09-07

The inspector now starts with Artboards. Add creates a board 80 units to the right of existing boards using the active board dimensions. Choose an active board in the selector; it is outlined and labeled in gold. Apply board commits name, X/Y and width/height as one undo step. Fit active (also Ctrl+0 and the zoom label) and Fit all frame the chosen bounds. Remove keeps all artwork and cannot remove the last board.

Boards are export regions in a shared coordinate space, not containers for paths. Changing bounds does not translate or scale artwork. Coordinates may be negative; dimensions range from 1 to 100,000. At extreme sizes the existing 5% minimum camera zoom still applies.

## Save and export

- Outline version 4 adds artboards and activeArtboardId. The legacy artboard field mirrors the active board. Legacy outlines without boards default to 800×600 at the origin; legacy dimensions are respected.
- Boards and the active ID are included in undo snapshots and session persistence. Empty multi-board documents can be saved, opened, reloaded and exported. Malformed board input is rejected before replacing the document. Paste merges artwork while retaining destination boards.
- Output > SVG area selects Active artboard (default) or All artwork. Active export uses exact width/height and a zero-origin viewBox, translating path coordinates by the active board origin and clipping at the SVG viewport. Empty boards export transparent SVGs. All artwork retains the existing padded artwork-bounds export.
- generateSVGString(sourcePaths, {scope:'active'}) explicitly targets the active board. Its default remains artwork bounds for clipboard and isolated Entity previews.
- Entity preview stays isolated; Insert clones and centers/scales its paths into the board active at insertion time, leaving the preview unchanged.

## Verification

Run python3 tests/artboards.py with Python Playwright and Chromium.

Passed: UI Add 1 → 2, Undo 2 → 1, Redo 1 → 2; form name/bounds edits; invalid input and Escape; active selection and fit all; downloaded SVG 320×240 with exact origin, gold interior pixels, transparent empty pixels and cyan edge clipping; all-artwork export; removal retains paths; session reload; empty board save/open/reload/export; legacy migration; invalid outline rejection; pasted outlines preserve boards; Entity insertion into a negative-origin board with undo/redo.

Precision, snapping, Pencil, Pathfinder, rulers and offline Entity regression suites passed with no browser errors. Screenshot: artboards.png.

Outcome-debug triage: new board state/UI and export-region behavior; no device/input fault. Runtime entry points: window.__DRAW__.addArtboard/selectArtboard/updateArtboard/removeArtboard/fitAllArtboards. Board list and active ID are in getState() and serializeOutline().

Next card: PNG export.
