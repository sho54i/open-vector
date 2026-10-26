# Document setup, anchor management and modifiers — 2026-10-22

Implemented locally; all three cards are Testing pending user/device review.

## Document setup

Open **File → Document setup**. Hover the entry to reveal its submenu, or click/tap it. Set the document name, RGB/CMYK mode, setup units (px/mm/in), pixels per inch (36–1200), and active-board dimensions. Apply commits one Undo action without moving artwork. Physical dimensions convert to internal pixels using the selected resolution. This resolution is a setup conversion, not PNG export scaling or embedded print-resolution metadata. Existing Artboards controls remain in pixels.

Document settings persist in outline JSON, browser sessions and Undo/Redo. New documents and older JSON default to RGB, pixels and 96 pixels/inch. Importing artwork into an existing document preserves its settings.

CMYK mode exposes C/M/Y/K percentage entry for selected artwork's solid fill or stroke. Values convert using `RGB = 255 × (1 − channel) × (1 − K)`. Applying a colour replaces that target's gradient with a solid colour; the other target remains unchanged. Locked, hidden and clipping-mask paths are protected. RGB is the underlying paint representation: original CMYK recipes, ICC profiles, soft proofing and print separations are not retained/supported. The UI explicitly labels canvas and SVG/PNG output as RGB approximations.

## Anchor points

Long-press the **Pen** toolbar button (450 ms) to choose Pen, Add anchor, Remove anchor or Convert anchor. Each variant has a distinct SVG icon and matching canvas cursor. Arrow Down on the focused Pen button also opens the menu; arrows and Enter choose a variant, and Escape dismisses it. P restores the ordinary Pen. Add clicks a segment and splits its cubic with De Casteljau interpolation; Remove clicks an anchor; Convert toggles a clicked anchor between smooth and corner. Existing A-mode anchor editing and pen gestures remain available. Each tool stays active for successive edits. Closed contours retain at least three anchors and open contours at least two. Locked/hidden paths cannot be edited. Compound contour boundaries are preserved. Editing removes a text recipe while retaining its vector outlines. Each edit supports Undo/Redo and session saving.

## Keyboard modifiers

- Shift + pen placement or handle drag constrains to 45° rays.
- Shift + path/anchor movement constrains to horizontal or vertical alignment from the gesture origin. Shift-click still toggles selection, with deselection deferred until release so selected artwork can be dragged.
- Existing Shift square/circle creation, proportional corner scaling and 15° rotation remain available.
- Alt + bounding-box scale uses the selection's centre; combine with Shift for proportional corner scaling.
- Alt + selection drag creates independent copies after a three-screen-pixel threshold. Original geometry remains unchanged. Group and clipping IDs are remapped. Copy+move is one Undo action; a click does not copy. Pointer cancellation restores the pre-copy document. Unlock/show the complete selection before copying.
- Ctrl/Cmd+F runs **Paste in Front**, keeping copied coordinates and placing the copy at the top of the artwork stack. Ctrl/Cmd+Shift+V is retained as an alias. The separate Paste in Place menu entry has been removed.

## Verification

`python3 tests/next_three.py` exercises actual controls and canvas gestures: document dimensions/CMYK/JSON/reload/history, anchor counts and curved insertion, locked/minimum-count guards, Alt copy and centred proportional scale, Shift alignment and pen placement, Paste in Front stacking, and text-field shortcut isolation. `/tmp/open-vector-document-setup.png` shows the tablet viewport.

Outcome-debug baseline: underlying insertion, conversion and clipboard operations already worked (2 → 3 anchors; smooth handles false → true; 1 → 2 paths). Changes extend application interactions, not device input decoding. New assertions include copy X=100 → 180 with original fixed; Shift move (100,100) → (160,100); centred scaling bounds (100,100)–(200,200) → (50,50)–(250,250).

Final Chromium results: `next_three.py`, `precision.py`, `snapping.py`, `artboards.py`, `text_panels.py`, `clipping_mask.py`, `review_cleanup.py`, `pencil.py` and `apple_pencil.py` passed. Additional outcomes: cancelled Alt drag restores one path; grouped copies retain a shared new group ID; removing a hole's first anchor preserves contour lengths `[4, 3]`; Shift handle drag keeps the anchor at `(100,100)` and handle Y at `100`; roadmap v39 → v40 retains custom cards and adds each review card exactly once. Physical keyboard/tablet acceptance remains pending.

UI revision: Document setup and Anchor points are removed from the inspector and Tools panel list. `tests/pen_menu.py` verifies mouse/touch long press, four distinct SVGs, keyboard access, cancellation, hover-form edits, responsive submenu bounds and the single paste command. `tests/next_three.py` now exercises the new access paths. Screenshots: `pen-tools.png` and `document-menu.png`.

Convert-anchor follow-up (2026-10-22): direct conversion and click toggling passed the baseline, but an anchor drag left its automatically generated handles unchanged. The Convert gesture now stays active until release: drag an anchor to draw mirrored handles, drag an existing handle to adjust it independently, and hold Shift for 45° constraints. Click still toggles smooth/corner. Cancellation restores original geometry and each completed edit has one Undo step. The toolbar, flyout and cursor use a single angled delta, with the cursor hotspot at its tip. `tests/convert_anchor.py` covers geometry outcomes, history, cancellation, locked/hidden guards and icon/hotspot; `tests/next_three.py` and `tests/pen_menu.py` cover existing interactions. Physical device review remains pending.
