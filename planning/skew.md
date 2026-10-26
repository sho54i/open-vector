# Skew object

Implemented 2026-10-26; awaiting user review.

Select artwork, then use **Skew** in the inspector (also available through Tools). Enter an angle from −85° to 85° and choose **Skew horizontal** or **Skew vertical**. Negative and fractional angles are supported. The shared selection anchor-bounds centre is the pivot, consistent with the existing transform bounds.

Horizontal shear applies `x += tan(angle) * (y - centreY)`; vertical shear applies `y += tan(angle) * (x - centreX)`. In canvas coordinates, positive horizontal angles move the bottom right; positive vertical angles move the right side down. Anchors and both Bézier handles receive the same transform, including compound contours. Whole objects transform even in direct-selection mode. Clipping masks and artwork transform together, including when only one clip member was selected.

Grouping, clipping identities, fill/stroke colours, gradient recipes, width profiles, effect recipes, dash patterns and contour flags are retained. Stroke weights remain fixed, gradients fit the new path bounds and effects retain their existing settings; this is a geometry shear, not an affine paint/effect transformation. Text becomes editable vector outlines so updating a text recipe cannot silently remove its skew. Undo restores the recipe.

All geometry is prepared before mutation. Empty selections, locked/hidden members, active drags/imports, non-finite/out-of-range angles, and results beyond ±10,000,000 coordinates are rejected atomically. Zero-degree and unchanged operations do not add history. One Undo restores the complete operation; Redo, session restore, outline JSON, SVG and PNG use existing paths. No drag handles, custom pivots or copy mode are introduced.

Validation: `python3 tests/skew.py` checks actual UI actions and geometry (45° horizontal: anchor X 100 → 50; handle X 80 → approximately 0), both axes, signed fractional angles, shared group pivots, clipping members, history/reload/JSON, SVG/PNG, invalid inputs and state, zero-size paths, compound contours, paint retention, text conversion, keyboard activation and a 768px-wide panel screenshot. `tests/reflect.py` and `tests/recent_files.py` regressions passed. Physical-device review remains pending.
