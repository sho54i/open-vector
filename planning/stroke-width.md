# Stroke width profiles — 2026-10-21

Implemented; awaiting user review. **Stroke width** is an inspector widget, also available through Tools.

Select one or more paths and choose Uniform, Spindle, Taper start, Taper end or Wave. Profile position is measured by sampled distance along each contour, starting at its first anchor. Width is a percentage of the path's existing stroke weight: 100% retains that weight and 400% is four times as wide. Each selected path retains its own base weight and paint.

Edit numeric position/width stops, add a stop in the widest interval, or remove intermediate stops. Endpoint positions remain 0% and 100%; widths can range from 0–400%. Up to 32 unique stops are supported. These are panel controls, not draggable canvas handles. Uniform restores the normal stroke renderer.

The editable centreline and handles remain intact. Profiles apply to open, closed and compound paths, repeating per contour. Both solid and linear-gradient strokes are supported. Reflection and duplication preserve profile data. Blend currently inherits the first endpoint's profile while interpolating the base weight; it does not morph two different profiles.

## Rendering and interchange

- Canvas and SVG use the same sampled outline geometry. Curves use up to 128 samples per Bézier segment, with explicit width-stop samples. The approximation is not an exact analytic offset.
- Variable strokes use continuous paint and round joins; applying a profile clears dashes and selects round joins. Choosing a dash restores uniform width. Butt, round and square endpoint caps are supported.
- Each sample strip and round join contributes to a filled outline. Dense/self-overlapping shapes may merge their stroke regions. Unequal widths at the start/end of a closed contour can create a seam.
- JSON saves the centreline plus `widthProfile: [{offset:0,width:0}, …, {offset:1,width:0}]`; legacy documents without the field remain uniform. Invalid imported profiles fall back to uniform.
- SVG exports filled stroke outlines, including gradient paint. Re-imported SVG is editable outline geometry, not a recoverable centreline/profile. PNG uses that same SVG pipeline. Export bounds include the maximum profile radius.
- Outline and Canvas Path2D caches invalidate when geometry or profile changes. Hit-testing uses the visible variable-width outline. Fit Selection includes maximum profile width.

## Verification

`python3 tests/stroke_width.py` verifies actual canvas pixel thickness (2 px near the tip versus 16 px at the centre), custom 400% width and exported SVG pixel thickness (64 px at centre), PNG download, SVG outline re-import, edit/add/remove/invalid stops, wide-edge hit-testing, Undo/Redo, reload, duplication/reflection, linear gradients, compound curves, uniform/dash compatibility, locked paths and multi-selection.

Existing stroke_gradient, reflect, blend, brushes_swatches, precision, pencil and text_panels regressions passed. User/device acceptance remains pending.
