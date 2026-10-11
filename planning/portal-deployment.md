# Main portal release — 2026-09-07

- Projects: https://tensor-portal.vercel.app/projects
- Editor: https://tensor-portal.vercel.app/draw/index.html (`/draw` redirects here).
- Vercel project: `tensor-s4/tensor-portal`.
- Portal Git commit: `bc9f632` in `sho54i/Tensor-Portal`, pushed to main.
- Editor Git commit: `26a39e2`, byte-identical to `public/draw/index.html`.
- Production deployment: https://tensor-portal-mzm0j4ipo-tensor-s4.vercel.app

The Projects page lists DRAW alongside Key·Viz. DRAW runs as a full-page static editor, keeping its vendor URL relative and avoiding an iframe input layer. Planning, tests, sample artwork and local settings are excluded.

Verification: ESLint on changed portal sources, TypeScript check, successful Vercel build, public browser navigation from Projects, exact source hash, drawing 0→1 path→Undo 0, no-op Undo regression, both Key·Viz routes returning 200, excluded assets returning 404 and no page errors.

## Retired test URL

https://eve-draw-pencil.vercel.app returns HTTP 308 to the main-site editor. The old tool deployment and temporary fallback deployment are retired; this project now exists only to preserve bookmarks through a redirect. The tested deployment is `dpl_AgTrUWeM3EkeounStisJiuTzKG3P`.

Redirect source: `/home/sho/AREA-54/software-MD/DRAW-redirect`. Deploy using `vercel deploy --prebuilt --prod --scope tensor-s4`. The effective `.vercel/output/config.json` is:

```json
{
  "version": 3,
  "routes": [{
    "src": "/.*",
    "status": 308,
    "headers": { "Location": "https://tensor-portal.vercel.app/draw/index.html" }
  }]
}
```

Local artwork belongs to its browser origin; saved outline JSON can be opened in the main-site editor. The original Git baseline remains archived on H:.

## Local update feed — 2026-09-07

Added public/draw/releases/latest.json and immutable 2026.09.07.1 JSON/ZIP to the
portal, published directly via Vercel CLI without Git. Current production release:
https://tensor-portal-fpgnmzkdz-tensor-s4.vercel.app
(dpl_FfTCwtP71Kjmc63Xw7aQCUUtCruw).
Hosted editor and portal source pages were unchanged. Retain public/draw/releases/
in future deployments. The package includes the newer locally accepted text and
panel features. Public download/install/browser/rollback smoke passed; details in
planning/local-updater.md. The CLI deployment has not been committed to Git.

## OPEN-VECTOR production release — 2026-09-08

Published approved OPEN-VECTOR branding, theme switching, text/fonts and movable
panels. Projects listing renamed OPEN-VECTOR; /draw and /draw/index.html remain
stable. Production: https://tensor-portal-dhohaqs94-tensor-s4.vercel.app
ID: dpl_FCfEm64TvJZUaFogkw4MPfv6x5zf. Status READY.

Updated local release feed to 2026.09.08.1 (sequence 2026090801), preserving the
previous package. ESLint passed for Projects. Live Chromium verified Projects
navigation, logo/credit, theme persistence, text 0→1→Undo 0, Attach/Detach and exact
hosted/source editor hash. Key-Viz and the previous release return 200; planning
and tests remain excluded. Live package install/open/rollback smoke passed.
Published directly through Vercel CLI; Git was not required or pushed.

## Buttons/aesthetics + new logo release — 2026-10-11

Editor commit 15a80b8 copied byte-identical to public/draw/index.html (sha256 b2b6868c…).
Release feed 2026.10.11.1 (sequence 2026101101) added; earlier packages kept.
Production: https://tensor-portal-n5syoxkay-tensor-s4.vercel.app (Ready). The CLI's
first `--prod` run also deployed (tensor-portal-4f83sr5ls), superseded a minute later.
Checked before deploying: origin/main had nothing newer than the checkout, and the
previous production build was the 2026-09-08 CLI release. Live checks: exact hash,
/projects 200, /draw 307 → editor, old package 200, logo, rect 1→Undo 0, zoom collapsed,
theme switch, no page errors. Published via Vercel CLI; portal Git not committed/pushed.
