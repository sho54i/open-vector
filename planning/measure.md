# Measure tool

Implemented locally 2026-10-22; awaiting user/device review.

Choose the ruler icon in the left toolbar or press **K**. Click a start node and
an end node, or drag a straight measurement line. Visible anchors are highlighted
and snap within the normal screen-space selection reach. Locked artwork can be
measured; hidden paths are excluded. Free endpoints work anywhere on the canvas.

Hold **Shift** to constrain the line to 45° increments. Hold **Alt** to use the
starting point as the centre, extending the opposite endpoint symmetrically;
the readout reports the full end-to-end span. Combine Alt+Shift for a centred,
angle-constrained measurement. Modifiers work for dragging and two-click mode,
and pressing/releasing them updates the preview even with the pointer stationary.
Finishing the gesture retains that result after releasing the keys. Angle
constraints take precedence over off-axis node snapping.

The lower-left readout shows straight-line distance and signed X/Y deltas, using
File > Document setup units and resolution. Positive Y points down the canvas.
Measurements use document coordinates, so zoom and pan do not change the result.
The line is temporary: it is not artwork, exported geometry, saved state or an
Undo entry. Escape, switching tools, cancelling a gesture, losing window focus,
opening a document, New and restoring history clear it. Start again to replace a
finished measurement. Touch follows the existing Finger input setting; choose
Draw to measure by finger, or use a pen with palm protection enabled.

Validation: `python3 tests/measure.py` passed: node clicks produce 300 px; a free
drag produces 200 px; 2x zoom and pan preserve distance; 300 px at 300 DPI converts
to 25.4 mm / 1 in. Locked nodes, hidden exclusion, zero length, pen/touch routing,
cancellation, switching, resets and unchanged document/history passed. Screenshot:
`planning/measure.png`. Existing convert_anchor, rulers, precision and pencil
regressions passed. Physical tablet testing remains for user review.

Modifier tests passed: horizontal/diagonal constraints, centred endpoints, combined
modifiers, stationary key changes, two-click mode, committed-result retention,
off-axis snap exclusion and unchanged artwork/history.
