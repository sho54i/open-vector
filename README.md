# DRAW — EVE Vector Entity Studio

Open `vector_pen_tool.html` in a browser. This is a static Canvas/vector editor: drawing, history, SVG/JSON import/export, PNG export and document storage run in the browser. Paper.js is bundled in `vendor/`. The optional Vector Assistant connects to a local or hosted Chat Completions-compatible model service. Browser agents can use the versioned `window.__VECTOR_ASSISTANT__` tool API without a model connection. Help in the top menu includes editor shortcuts, connection guidance and downloadable agent documentation. See [Vector Assistant guide](planning/vector-assistant.md). There is no server backend or standalone MCP transport in this repository.

## Version history and H: archive

Working repository: `/home/sho/AiM/Entity-OS/crts/open-vector`

Independent Git archive and checkout: `H:\draw-git` (`/mnt/h/draw-git` in WSL). The archive is a full clone, including tests and planning, with its own Git objects. It remains usable if the working directory is lost.

- `baseline-pencil-verified-2026-09-07`: hardware-verified Pencil baseline, before review cleanup.
- `cleanup-reviewed-2026-09-07`: reviewed cleanup with automated regression verification; see `planning/code-review.md`.

After testing a future version, run from WSL:

```bash
python3 /home/sho/AiM/Entity-OS/crts/open-vector/scripts/save_version.py "Describe the change and tests passed"
```

Use `--check` to inspect readiness without writing. The helper commits all non-ignored project changes, then fetches commits/tags into the archive and fast-forwards it. It refuses a dirty archive, a different branch/origin or divergent history; it never resets or overwrites archive edits. If the H: sync fails after committing, the source commit survives and rerunning retries the save. Review changes before running: the message records your validation; the helper does not run tests automatically.

Use descriptive tags for accepted milestones. Keep historical commits; promote the version with demonstrated correctness and measured improvements, rather than deleting alternatives or assuming the newest version is optimal.

## Tests

Requires Python, Playwright and its Chromium browser. Run `python3 tests/<name>.py` for Pencil, Apple Pencil, rulers, snapping, precision, Pathfinder, artboards and PNG/SVG drop. Run `python3 tests/entity_panel.py --offline` for fixture-based model-panel checks; omit `--offline` only with a configured model server.

`python3 tests/review_cleanup.py` checks no-op Undo/Redo, field shortcut isolation and engine microbenchmarks. Timing results are diagnostic, not hardware-independent pass thresholds. `python3 tests/draw_perf.py --check-pixels --gate` times redraw, drag and hover on a 300-path / 18k-anchor document, asserts a pointer burst renders once per frame, and checks the canvas against `tests/draw_perf.sha256` (regenerate with `--save-pixels` after an intended visual change). Tests write disposable screenshots and model previews to `/tmp/open-vector-*`, outside the repository.

## Main-site deployment

DRAW is published alongside Key·Viz at https://tensor-portal.vercel.app/projects. Open the editor at https://tensor-portal.vercel.app/draw/index.html.

The portal repository is `sho54i/Tensor-Portal`; its integration checkout is `/home/sho/AiM/tensor-portal-draw`. Accepted editor source is copied to `public/draw/index.html` with its vendor folder. Planning, tests and samples stay out of the deployment. The former `eve-draw-pencil.vercel.app` test URL now redirects to the main editor; the old test tool deployment has been retired.

For a future accepted version, refresh `public/draw/index.html` and changed vendor assets in the portal repository, verify both Projects links and drawing/undo, then commit and push the portal's main branch. The `share/` folder is an archived test copy, not the current publication target. The `redirect/` directory maintains the retired URL's prebuilt redirect only.

See `planning/portal-deployment.md` for release details. Git saves to H: do not automatically deploy updates.

## Local updates without Git

Run `Update_DRAW.bat` on Windows, or `python3 scripts/local_updater.py check` then `python3 scripts/local_updater.py apply` from the DRAW folder. Python 3.9+ is required. Releases come from the Vercel portal; backups, rollback and interrupted-update recovery are included. See [UPDATE_README.txt](UPDATE_README.txt) for usage and [planning/local-updater.md](planning/local-updater.md) for release publishing and validation.
