# Styles — 2026-10-22

Implemented; awaiting user/device review. Open **Styles** in the inspector or Tools menu.

- **Drop shadow:** enable it, then choose colour, opacity, X/Y offset and softness. Offsets are document pixels; softness is Gaussian standard deviation. Changing a shadow setting enables the shadow.
- **Blur:** Gaussian spreads in both directions; Horizontal and Vertical spread along one axis. Amount 0 disables blur. Choosing a type with blur off starts at 6 px. Blur is applied before shadow. Clear shadow and blur removes both without changing geometry.
- **Round corners:** select closed shapes, enter a radius and click Round corners. Straight corners become pairs of editable anchors with Bézier handles. Radius is limited to fit adjacent edges without overlap. Existing curved segments and degenerate/straight-through corners are preserved. Use **A** to drag the new anchors or handles. This is a geometry operation, not a live radius widget; Undo restores the original corners.
- **Roughen edges:** choose amplitude, approximate spacing and seed. Converts curves to editable straight segments, with deterministic normal displacement. Open endpoints stay fixed; closed and compound contours remain closed/compound. Repeating from the same source and seed produces the same result. Each application changes the current geometry; Undo restores it.

Effects apply separately to each selected path. Mixed-selection edits preserve each path's other effect settings. Locked, hidden and mask paths are protected. Release clipping before geometry operations. Individual clipped artwork can have shadow/blur, cropped by its mask; the mask itself cannot receive effects. Geometry operations remove text editing recipes, retaining editable outlines and appearance.

## Persistence and rendering

Shadow/blur are stored in outline JSON, session storage, history and internal clipboard/duplicates. Canvas and SVG/PNG export share one SVG filter graph. Artwork exports include generous effect margins; Active artboard exports intentionally crop to the board. Shadow and blur don't change anchor coordinates. Selection and hit tests continue to use source geometry, so select the object rather than its shadow.

Canvas caches a decoded SVG image per styled path. It refreshes asynchronously after an edit and scales with zoom/device resolution up to 4× and 4096 pixels per image dimension. This bounds raster work; very large/high-zoom styled objects can look softer on canvas. SVG retains the filter and vector source; PNG uses the existing export pipeline. Unstyled paths keep the existing immediate canvas renderer.

The existing safe SVG importer rejects filter elements; use outline JSON to reopen editable effects. Internal copy/paste retains effects, while external SVG is an export format for styled artwork. There are no art-style overlays in this card; those remain on the separate filters card.

## Validation

`python3 tests/styles.py` uses real controls and verifies:

- Blue shadow canvas pixel `[0, 0, 255, 255]` beyond the red source, matching rasterized SVG.
- Horizontal-only, vertical-only and two-axis Gaussian blur alpha outside the source.
- Actual PNG download; unchanged source anchors under appearance edits.
- Four rectangle anchors become eight rounded anchors with Bézier handles; actual A-mode handle drag moves the handle by 12 px while its anchor stays fixed.
- Deterministic roughening, changed seed, preserved open endpoints and compound contours.
- Undo/Redo, reload, duplicate, internal clipboard, invalid/locked selections, mixed settings, no-op rounding and the 10,000-anchor roughen limit.
- Gradient and variable-width appearance, clipping, tablet layout and roadmap migration.

Related Chromium regressions: stroke width, clipping mask, precision, text/panels and review cleanup. No physical iPad/Pencil acceptance is claimed.
