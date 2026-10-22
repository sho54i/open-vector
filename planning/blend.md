# Blend tool — 2026-10-21

Implemented; awaiting user review. Find **Blend** in the inspector or Tools menu.

1. Use V to select a path, then Shift-click the second path.
2. Choose 1–100 intermediate steps (endpoints are not included in this count).
3. Leave **Blend fill and stroke colours** enabled for a colour transition, or disable it to retain the first selected path's paints.
4. Choose **Create blend**. The new paths are selected and individually editable. One Undo removes the entire insertion; Redo restores it.

Anchors and effective Bézier handles interpolate by their array order. A corner contributes its anchor position as each handle. Stroke width interpolates; caps, joins and dashes follow the first endpoint. Fill and stroke colours interpolate in RGB. Solid-to-linear and linear-to-linear gradients interpolate colours, stop positions and gradient direction. Both linear gradients must have the same number of stops. Endpoint paths are unchanged. Generated paths have no group membership or text-editing recipe and are appended above existing artwork.

## Compatibility and limits

Endpoints must be exactly two visible, unlocked paths with equal anchor counts, corresponding contour starts, matching closure and fill rules. Compound paths work when those structures match. Direction and starting-anchor correspondence are not automatically corrected: reversed or differently ordered endpoints may twist the result. No resampling or spine-following is performed.

Colour blending requires both fills enabled or both disabled, and hexadecimal solid colours or linear gradients. Two transparent strokes remain transparent; a transparent-to-colour fade is not supported. Disable colour blending to retain the first path's paint when endpoint paints are incompatible.

The operation permits up to 100 intermediate paths and 20,000 generated anchors. Invalid selections/settings produce an inline message without changing artwork or Undo history. Blends are expanded paths, not live linked objects; edit them normally or Undo and recreate with different settings. They use the existing outline save/load, session restore and SVG/PNG export pipeline.

## Verification

`python3 tests/blend.py` checks:

- Rectangles at (100,100) and (300,200) produce a midpoint anchor at (200,150).
- Red/blue fill becomes #800080, black/white stroke becomes #808080, and widths 2/10 become 6.
- Three steps have evenly spaced anchors at x=150/200/250; 100 steps create exactly 100 paths.
- Endpoints remain byte-equivalent in serialized path data; one Undo/Redo and reload preserve expected results.
- Actual canvas Shift-click selection, curved handles, solid/linear and linear/linear paints, SVG output, geometry-only mode and compound contour starts.
- Wrong selection counts, locks, hidden paths, incompatible anchors/contours/closure/paints/gradient stops and invalid step counts fail without mutation.

Existing brushes_swatches, stroke_gradient and text_panels browser regressions also passed. Physical-device acceptance remains pending.
