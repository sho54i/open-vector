# DRAW — EVE Vector Entity Studio

Open `vector_pen_tool.html` in a browser. This is a static Canvas/vector editor: drawing, history, SVG/JSON import/export, PNG export and document storage run in the browser. Paper.js is bundled in `vendor/`. The optional Entity Harness panel connects to a separately configured model server; there is no server backend in this repository.

## Version history and H: archive

Working repository: `/home/sho/AREA-54/software-MD/DRAW`

Independent Git archive and checkout: `H:\draw-git` (`/mnt/h/draw-git` in WSL). The archive is a full clone, including tests and planning, with its own Git objects. It remains usable if the working directory is lost.

- `baseline-pencil-verified-2026-09-07`: hardware-verified Pencil baseline, before review cleanup.
- `cleanup-reviewed-2026-09-07`: reviewed cleanup with automated regression verification; see `planning/code-review.md`.

After testing a future version, run from WSL:

```bash
python3 /home/sho/AREA-54/software-MD/DRAW/scripts/save_version.py "Describe the change and tests passed"
```

Use `--check` to inspect readiness without writing. The helper commits all non-ignored project changes, then fetches commits/tags into the archive and fast-forwards it. It refuses a dirty archive, a different branch/origin or divergent history; it never resets or overwrites archive edits. If the H: sync fails after committing, the source commit survives and rerunning retries the save. Review changes before running: the message records your validation; the helper does not run tests automatically.

Use descriptive tags for accepted milestones. Keep historical commits; promote the version with demonstrated correctness and measured improvements, rather than deleting alternatives or assuming the newest version is optimal.

## Tests

Requires Python, Playwright and its Chromium browser. Run `python3 tests/<name>.py` for Pencil, Apple Pencil, rulers, snapping, precision, Pathfinder, artboards and PNG/SVG drop. Run `python3 tests/entity_panel.py --offline` for fixture-based model-panel checks; omit `--offline` only with a configured model server.

`python3 tests/review_cleanup.py` checks no-op Undo/Redo, field shortcut isolation and engine microbenchmarks. Timing results are diagnostic, not hardware-independent pass thresholds. Existing tests may regenerate screenshots under `planning/`; review those changes before saving a version.

## Public testing copy

`https://eve-draw-pencil.vercel.app` is a production URL in the separate `tensor-s4/eve-draw-pencil` Vercel project. Its standalone source is the sibling `DRAW-share` directory, which excludes tests, planning, roadmap and samples. That deployed copy remains the user-tested baseline; local Git saves do not deploy changes automatically.

To publish a future accepted version, copy `vector_pen_tool.html` to `DRAW-share/index.html`, refresh any changed runtime assets, then deploy from that separate directory. Its `.vercel` linkage is local machine state and is intentionally excluded from this repository.
