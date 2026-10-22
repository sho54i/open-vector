# Clipping mask — 2026-10-22

Implemented; awaiting user review. Open **Clipping mask** in the inspector or Tools menu.

1. Place a closed shape above the artwork to clip. Select it and one or more artwork paths with V and Shift-click.
2. Choose **Make mask**. The topmost selected path (layer order, not click order) defines the visible area. Its own fill and stroke are suppressed. Selected artwork is collected immediately below the mask, retaining its internal order.
3. V selects and moves the clipping group together. **Edit mask anchors** switches to A with the mask selected; drag its anchors and Bézier handles without changing the artwork. Individual content anchors remain editable with A or through Layers.
4. **Release mask** removes the relationship and shows the original mask paint again. Original paths, handles and appearance are retained. Make, Release and geometry edits support Undo/Redo.

Layers label paths as **Mask** or **Clipped**. Hidden masks hide their artwork; hidden paths and the mask relationship remain in saved outline JSON. Duplicate, copy/paste and reflected copies get independent clipping groups. Copy or duplicate from Edit mask includes its artwork. Moving layer order from Edit mask moves the complete clipping group.

Canvas fill, ordinary/variable-width strokes and gradients are clipped. Canvas object hits outside the mask are excluded. Compound masks use their nonzero/even-odd fill rule, including holes. Exports use SVG `clipPath` definitions; PNG uses the same SVG pipeline. SVG import accepts local, non-nested user-space clip paths; imported clips remain editable. SVG does not retain the original mask's hidden paint, text recipes or variable-stroke centreline profiles; outline JSON is the editable document format. Artwork export bounds retain the source geometry bounds, so clipped-away content can leave transparent margins.

## Limits

- Ungroup ordinary groups before making a mask. Nested masks and opacity/luminance masks are not supported.
- The topmost shape must be closed, have nonzero bounds and at least three anchors per contour. Making/releasing requires visible, unlocked affected paths.
- Release clipping before Pathfinder or Blend operations. Mask contours cannot be deleted below three anchors; release first to remove them.
- Existing multi-selection limits still apply: bounding-box scale/rotate handles are available only for a single path. Use A to edit anchors or Reflect for a whole clipping selection.
- External SVG object-bounding-box clips and nested clips are rejected, rather than imported without their clipping. Multiple paths inside an external clip definition are not supported unless represented as a compound path.

## Verification

`python3 tests/clipping_mask.py` exercises real controls and checks:

- Topmost mask choice regardless of click order; original geometry and paint retained.
- Red canvas pixels inside the mask only; no object hits on clipped-away geometry.
- Real V click selects two paths; Arrow Right moves both X coordinates by 1.
- Mask anchor `(150,150) → (160,155)` while artwork coordinates stay unchanged.
- One-step Undo/Redo, Release and its Undo; JSON/session reload.
- SVG exterior/interior/exterior alpha `0 / 255 / 0`, PNG download, editable SVG clip import.
- Independent duplicate/reflected copies, copy/duplicate from Edit mask, hidden-mask persistence, even-odd holes, gradients and variable-width strokes.
- Invalid selection, open/locked/hidden/grouped paths, nested masks, missing mask references and malformed saved groups leave the document unchanged.

Related browser regressions: reflect, stroke width, blend, brushes/swatches, Pathfinder, PNG/SVG drop and text/panels. The Pathfinder and PNG/drop roadmap assertions now check their own shipped cards rather than assuming every roadmap card is shipped.

Screenshot: `planning/clipping-mask.png`. User/device acceptance remains pending.
