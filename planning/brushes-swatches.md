# Brushes and swatches — 2026-10-21

Implemented; awaiting user review. Open Brushes and swatches in the inspector or Tools menu. The panel supports the existing collapse, reorder, detach and hide controls.

Swatches apply a solid colour to the front fill/stroke target in the left toolbar. Applying a fill enables it; applying a stroke restores a solid stroke. Save colour captures the current solid colour. Gradient and disabled paints are rejected with guidance.

Brushes capture stroke width (0.5–16 px), cap, join and dash pattern. Fine, Bold, Dashed and Dotted are included. They preserve each selected path's colour, gradients and fill. They are uniform-width stroke styles, not textured/art brushes or variable-width profiles. The separate stroke-width roadmap card remains queued.

Applying either changes only the relevant properties on visible, unlocked selected paths, with one Undo step. With no selection, it sets the appearance for new paths. Brush selection also updates the Pencil base-width preference; that workspace preference remains independent of document Undo. Existing pressure/smoothing settings continue to apply.

Name and save custom presets, remove individual entries, or export a library for backup/sharing. Libraries persist under localStorage key `open-vector-library-v1`, independently of document files and history. Storage failures report session-only availability. Import merges entries and skips exact duplicates; validation is atomic. Limit: 128 entries per list and 256 KB per imported file. Names are plain text, up to 80 characters.

## Portable format

The colour-picker app can exchange this JSON format. No changes or direct connection to that application were made.

```json
{
  "format": "open-vector-library-v1",
  "swatches": [{ "name": "Ocean", "color": "#00f0ff" }],
  "brushes": [{ "name": "Dashed", "strokeWidth": 2, "strokeCap": "butt", "strokeJoin": "miter", "strokeDash": [8, 4] }]
}
```

Both arrays are required; a palette-only file uses an empty brushes array. Colours normalize from three/six-digit hex to lowercase six-digit hex. Cap: round/butt/square; join: round/miter/bevel. Dash arrays allow up to 32 finite values from 0 to 10000.

## Verification

- `python3 tests/brushes_swatches.py`: actual fill/stroke/width/dash outcomes; multi-selection preservation; locked paths; Undo/Redo; new path styling; SVG attributes; save/remove/reload; downloaded JSON round trip; duplicate import; atomic malformed import; plain-text names.
- Existing colour_swapper, stroke_gradient, pencil, apple_pencil and text_panels tests passed.
- Panel screenshot inspected in Chromium. Physical Pencil interaction and user acceptance remain pending.
