# Local updater / patch handler

Release 2026.09.07.1 (sequence 2026090701). No Git required for building,
publishing or applying packages. Python 3.9+ standard library on the local machine.

- Windows launcher: Update_DRAW.bat (check / install / rollback / recover).
- CLI: python3 scripts/local_updater.py check|apply|rollback|recover
- Feed: https://tensor-portal.vercel.app/draw/releases/latest.json
- Optional alternate source: --manifest <trusted HTTPS URL>
- Package builder: python3 scripts/build_release.py --version <new-version> --sequence <increasing-integer>

Packages contain the editor HTML, bundled runtime dependencies/fonts/licenses,
updater, Windows launcher and UPDATE_README.txt. Excludes planning, artwork, tests,
Git data, settings, backups and credentials. The current working HTML is packaged;
there is no dependency on a Git commit or accessible Git server.

Before mutation the updater validates manifest schema, sequence, HTTPS/same-origin
redirects, package SHA-256/size, exact ZIP member list and per-file SHA-256/size.
Paths are restricted to application destinations. Traversal, Windows reserved
names, case collisions, symlinks and oversized/invalid packages are rejected.
Packages are read as bytes, not extracted with extractall; no post-install hooks.
The HTTPS host is the trust source, not a detached signing key. Checksums verify
integrity, not a publisher independently of that host.

Affected files are backed up under .draw-updater/backups before a durable recovery
journal is created. Individual replacements are atomic. Ordinary write failures
restore the entire prior set; a terminated process leaves a journal for recover.
The OS file lock releases after process exit. Rollback restores the previous
receipt and files, including the original untracked local copy on first install.
Only obsolete paths previously recorded as package-owned are deleted. Modified
managed files block install/rollback, preserving local edits for explicit handling.

Save work and close the editor before applying. Reopen at the same path to retain
browser storage. The updater does not manipulate browser artwork, preferences,
fonts cached by the browser or roadmap state. Backups are retained, not pruned.

Validation: 12 tests in tests/local_updater.py passed, including actual loopback
HTTP CLI check/apply/no-op/rollback, checksums, ZIP/path guards, destination symlink,
local modifications, obsolete file rollback, injected mid-write failure, a killed
subprocess followed by recover, concurrent lock rejection and repeatable builds.
tests/release_smoke.py installs the built package into a disposable directory,
opens it in Chromium, verifies text path count 0→1→Undo 0 and Attach/Detach, then
rolls back and checks original editor/artwork bytes. Windows batch execution and
an update on the user's actual installation remain for user acceptance testing.

Publishing: copy dist/releases/* into the portal checkout's public/draw/releases/,
then use vercel deploy --prod --yes --scope tensor-s4. Versioned ZIPs/manifests
must remain immutable and older ZIPs must remain available. latest.json is the
moving pointer. Next.js public files use revalidation (max-age=0); the updater also
requests no-cache. This release adds static downloads without changing the hosted
editor or other portal pages. Future portal publishes must retain the release files.

## Published release verification

Published via Vercel CLI on 2026-09-07. Production deployment:
https://tensor-portal-fpgnmzkdz-tensor-s4.vercel.app
ID: dpl_FfTCwtP71Kjmc63Xw7aQCUUtCruw. Build status READY; production alias
https://tensor-portal.vercel.app.

The public latest.json and ZIP passed tests/release_smoke.py --manifest
https://tensor-portal.vercel.app/draw/releases/latest.json: checksum verification,
installation in a temporary local copy, Chromium editor launch, text 0→1→Undo 0,
Attach/Detach state, rollback to original bytes and artwork preservation.
Release includes 10 application files; compressed package is 1,163,255 bytes.
Portal source changes consist only of public/draw/releases/. Keep that directory
in later deployments. No Git commit, push or archive sync was performed.
