# PNG export and drag-drop SVG import — shipped 2026-09-07

## PNG

Use File > Export PNG or the Output panel. Export area chooses Active artboard or All artwork, shared with SVG export; PNG scale offers 1×, 2×, 3× and 4×. Background remains transparent. Pixel dimensions are rounded after multiplying the export area dimensions by scale. The active board uses its exact bounds with clipping; all artwork uses the existing 16-unit padding. Filenames include the board name and scale.

The async exporter captures source, area, scale and filename before decoding. It renders an isolated SVG into an offscreen canvas, encodes an image/png Blob, downloads it, and releases the object URL. It does not change document history, selection, camera or geometry. Empty artboards export transparent PNGs. The UI reports failures and limits exports to 64 megapixels and 16,384 pixels per side, avoiding unbounded canvas allocations.

## SVG files

Drag one or more .svg files onto the canvas. A dashed overlay identifies the target; leaving or dropping clears it. Imported artwork is placed with its upper-left geometry bounds at the drop world coordinate. All files become one undo step, placed at the front of the document stack and selected for editing. Existing boards and paths remain intact. Dropping files outside the viewport does not navigate away.

File drop, Paste, and Open use the same parser. A pinned local Paper.js engine converts validated detached SVG into ordinary editable point arrays, retaining cubic handles, transforms, compound contours, fill/stroke styles, dashes and opaque linear gradients. Supported geometry: path (including arcs), rect, circle, ellipse, polygon, polyline and line, plus groups. Solid fill/stroke alpha is retained. SVG viewport cropping is not baked into editable geometry.

Unsupported elements/attributes (including text, images, external references, CSS classes, masks/clips/filters, radial or transparent gradients, and object/group opacity) produce a clear import error rather than inserting partial artwork. Inputs are validated before conversion; source nodes are never mounted as live artwork. Limits: 2 MB per drop, 1,024 shapes and 20,000 anchors per file. File-read failures, malformed SVG and multi-file failures leave the document unchanged. If the document changes during file reads, insertion is cancelled and the user can drop again.

## Verification

`python3 tests/png_drop.py` with Chromium and Python Playwright passed:

- Real PNG downloads: image/png MIME, PNG signature and IHDR dimensions at 1×/2×/4×. Gold pixel RGBA (255,184,0,255); empty pixel alpha 0. All-artwork menu export, blank-board export, encoding failure/button recovery and oversized export rejection.
- File/DataTransfer drops add rectangle/circle paths, correct drop placement, styles and cubic handles. One Undo restores the exact previous paths; Redo restores insertion.
- Multiple files commit together; malformed, unsupported and unreadable files leave paths unchanged. No external requests or browser errors.
- Nested transforms, compound holes, arc conversion, linear gradients, shared clipboard parsing and session reload.
- Drag feedback cleanup, prevented outside-drop navigation, and delayed reads cancelled after document changes.

Artboards, Pathfinder, Pencil, precision, snapping, rulers and offline Entity regression suites passed. Screenshot: png-svg-drop.png.

Outcome-debug triage: new export and file-routing behavior. Outcome assertions are decoded PNG dimensions/pixels and actual path-count/geometry changes, rather than event counts. Runtime hooks: window.__DRAW__.exportPNG(); getState().pngExportBusy / svgDropBusy.

All seeded roadmap cards are now shipped; custom inbox items are preserved by migration.
