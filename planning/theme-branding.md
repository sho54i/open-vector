# OPEN-VECTOR theme and branding

Implemented locally on 2026-09-08; roadmap card cr84porb is shipped after user verification.

Header uses the supplied planning/logo/Open-Vector.png. 2026-10-11: swapped for the
updated logo (larger text, lighter back-plate); transparent padding is trimmed on embed
so it renders larger in the 68px header, and the separate OPEN-VECTOR header text is
gone because the logo carries it. The theme switch is now an icon button (sun/moon).
It is embedded in the HTML, so direct file opening and update packages include it
without a separate asset path. The browser title and header now say OPEN-VECTOR;
the small footer credit reads exactly "miniscule solutions 2026".

The top-right button switches Light theme / Dark theme. Dark remains the default;
localStorage key draw-theme remembers the choice independently of document data.
CSS controls the interface palette; a cached palette controls canvas artboards,
rulers, grid, guides and selection overlays. Existing artwork colours and export
output are not theme-dependent. Existing document and preference storage keys
remain compatible. Published to the portal on 2026-09-08 in release 2026.09.08.1; live checks passed.

Tests: tests/theme_branding.py verifies logo load/title/credit, artboard pixel
[12,15,23,255] → [255,255,255,255], unchanged paths/SVG/history, reload persistence
and 768px tablet layout. Screenshots: theme-light.png, theme-dark.png,
theme-tablet.png. User verified theme switching and approved branding on 2026-09-08.
