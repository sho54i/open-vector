# Text and movable tool panels

Implemented locally on 2026-09-07; ready for user review. No deployment performed.

Text panel supports multiline text, size 1–1000 px, three bundled DejaVu fonts, and local TTF/OTF/WOFF loading. Blender is not bundled; load its font file. WOFF2 is not supported. Font shaping uses the vendored OpenType.js 1.3.4 parser (https://github.com/opentypejs/opentype.js/tree/1.3.4); fonts and parser work offline, including opening the HTML directly. Licenses are in vendor/.

Insert creates one editable compound path at the active board's top-left inset. Text settings remain on that path through Undo/Redo, duplication, internal clipboard, outline JSON, and browser reload. Select the path to edit its wording/font/size and choose Update selected. This explicitly rebuilds outlines at their current top-left; rotation, scaling, and individual anchor edits are replaced. Appearance remains intact. SVG and PNG export outlines without requiring installed fonts; SVG re-import retains geometry, not the text recipe. Unsupported glyphs and invalid fonts show a status and leave artwork unchanged. Uploaded fonts are cached in browser storage when space permits; outlines remain portable if the font is missing, but editing requires reloading that font. Fonts are not embedded in document JSON.

Every inspector section has a title drag handle plus Collapse/Expand, Up/Down, Detach/Dock, Minimise, and Hide buttons. Drag outside the sidebar to float; drag back over the sidebar to dock at the drop location. Minimise places a restore button above the status bar. Tools in the top bar shows/hides sections and resets the layout. Workspace order, floating positions, collapsed state and visibility persist separately from artwork history. Pointer cancellation restores the pre-drag position. Floating positions are clamped to the viewport on resize.

Validation:

- tests/text_panels.py: actual Insert/Update and font-file controls; path count, recipe and geometry assertions; undo/redo; font selection; invalid size and locked path; collapse/reorder/detach/minimise/hide/restore; pointer drag out and back; layout/artwork/custom-font reload; real PNG download with nonzero ink and transparent O counter; malformed font leaves paths unchanged; multiline bounds and duplication. No browser errors.
- tests/review_cleanup.py: stable undo history and field shortcut isolation.
- tests/precision.py, tests/pathfinder.py, tests/png_drop.py, tests/apple_pencil.py: passed existing browser regressions, including tablet portrait and pressure/state outcomes.

User review remaining: preferred Blender font file, panel ergonomics and Pencil dragging on the actual iPad. The new cards are marked testing for this review.

Deployment: keep vector_pen_tool.html and all vendor assets together. Existing portal instructions copy the HTML to public/draw/index.html and the vendor folder beside it.
