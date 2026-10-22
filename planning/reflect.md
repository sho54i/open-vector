# Reflect tool — 2026-10-21

Implemented; awaiting user review. Open **Reflect** in the inspector or Tools menu.

- **Flip horizontal** mirrors left/right across a vertical line at X.
- **Flip vertical** mirrors top/bottom across a horizontal line at Y.
- By default, the line passes through the centre of the whole selection's existing anchor bounding box, matching the editor's selection bounds.
- Enable **Use custom mirror line** and enter the X or Y world coordinate to use a specific line. Negative and fractional coordinates are supported.
- Enable **Create reflected copy** to keep the originals and select mirrored duplicates. Otherwise the selection is reflected in place.

Anchors and both Bézier handles mirror. Fill/stroke gradient directions mirror with the paths; stops, colours, stroke widths, dash patterns, joins, fill rules and compound contours are preserved. Multiple selected objects reflect as one arrangement. In-place reflection retains grouping; copies remap group IDs so originals and copies are independent groups. Copies append above existing artwork.

Reflected text keeps its editable vector outlines but loses the text recipe, preventing a subsequent text update from silently undoing its mirror. Undo restores the text recipe. Reflected copies leave the originals' text editing intact.

One Undo reverses the complete operation; Redo restores it. Reflected paths use the existing document save/load, reload and SVG/PNG export paths. The tool operates on whole paths even in direct-selection mode. Every selected path must be visible and unlocked; mixed locked/hidden selections are rejected without partial changes. A custom mirror coordinate must be finite and between −10,000,000 and 10,000,000. Empty and invalid operations do not add history entries. Arbitrary-angle mirror lines and interactive axis dragging are outside this version.

## Verification

`python3 tests/reflect.py` covers actual panel clicks and path outcomes:

- Anchor X 100 → 200; handle X 80 → 220 for a horizontal flip around X=150.
- Vertical reflection, double-reflection restoration and shared multi-path centre.
- Reflected copies across X=−25.5, independent copied groups, unchanged originals.
- Undo/Redo, reload, gradient directions/stops, SVG attributes and unchanged stroke appearance.
- Empty/locked/hidden selections and invalid custom coordinates leave artwork/history unchanged.
- Compound contours, zero-size bounds, and real inserted text becoming outlines with Undo restoration.

Affected regressions: precision, blend and text_panels. User/device acceptance remains pending.
