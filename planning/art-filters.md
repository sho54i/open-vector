# Art filters — 2026-10-22

Implemented; awaiting user/device review. Open **Art filters** in the inspector or Tools menu.

Select visible, unlocked artwork and choose **Pencil sketch**, **Oil paint**, or **Bubble wrap**. Strength mixes the effect with the original appearance (0% is the original); Scale controls texture size in document pixels; Seed changes the grain or bubble pattern phase. Remove art filter restores the source appearance without removing shadow or blur.

- Pencil sketch combines grayscale edge contrast with directional grain. At less than 100% strength, some original colour remains.
- Oil paint combines colour quantization, displacement, softening and directional surface lighting for a painted texture.
- Bubble wrap overlays a repeated shaded circular impression. Its seed changes the repeating pattern phase.

These are procedural stylizations, not semantic redraws or simulated brush strokes. Each path has one preset. Selection-wide parameter edits preserve different existing presets; paths without a preset remain unfiltered until a preset is chosen. Choosing a preset applies it to every selected path while retaining their individual parameters. Invalid fields, hidden/locked selections and mask paths cannot change the document.

## Composition and persistence

Art filters run before Gaussian/directional blur and shadow. Clear shadow and blur preserves the art filter; Remove art filter preserves shadow and blur. Artwork is clipped to its source alpha before blur/shadow, and any clipping mask crops the final result. Original anchors, colours, gradients and text recipes are retained.

JSON/session storage, Undo/Redo, duplicate and the internal clipboard preserve recipes. SVG exports embed their filter primitives and, for Bubble wrap, a self-contained SVG texture; PNG renders the same SVG. No external images or network requests are needed. The existing SVG importer rejects filters: save outline JSON for reopening editable documents. Third-party SVG viewers must support these filter primitives and embedded SVG images.

The existing asynchronous canvas effect cache and its 4×/4096-pixel dimension limits also apply. Texture can soften at very large zoom. Effects apply per path, not across a composited selection. Selection hits remain based on original geometry. Physical iPad/Pencil and third-party viewer verification remain pending.

## Verification

`python3 tests/art_filters.py` checks actual controls and decoded pixels for all three presets, canvas texture, strength-zero equivalence, seed/scale variation, unchanged geometry, composition with Styles, clearing each effect family independently, Undo/Redo, reload, copies, PNG download, mixed selections, clipping, invalid recipe normalization and tablet width.

Related regressions: `tests/styles.py`, `tests/stroke_width.py`, `tests/clipping_mask.py`. All passed in Chromium. The roadmap card is Testing, not Shipped.
