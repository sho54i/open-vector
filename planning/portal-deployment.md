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
