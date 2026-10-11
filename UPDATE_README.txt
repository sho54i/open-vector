DRAW local updater (Python 3.9+; no Git or third-party Python packages)

Windows: double-click Update_DRAW.bat. Choose Check, Install, Roll back or Recover.
Linux / macOS / WSL, from your DRAW folder:
  python3 scripts/local_updater.py check
  python3 scripts/local_updater.py apply
  python3 scripts/local_updater.py rollback
  python3 scripts/local_updater.py recover

Feed: https://tensor-portal.vercel.app/draw/releases/latest.json
Use --manifest HTTPS_URL to select a different trusted release feed.

Save your artwork and close the editor before installing or rolling back.
Reopen vector_pen_tool.html at the same location afterwards. The updater preserves
planning files, artwork files, Git history and browser storage. Do not clear your
browser storage. JSON exports are recommended for work you want to keep separately.

Packages contain application files only. The updater checks HTTPS, ZIP/file sizes
and SHA-256 checksums, then backs up affected files under .draw-updater/backups/.
A failed write restores the prior files. If the process is forcibly terminated,
run Recover before another update. Rollback restores the last installed version
(or your original local copy on the first update). Backups remain on disk.

After the first managed install, locally changed application files block updates
and rollback. Preserve those changes separately before restoring the expected
application files. Your first untracked copy is backed up before replacement.

Checksums detect corruption; the HTTPS release host is the trust source. Only
use feeds controlled by someone you trust. Packages may update this updater.
No package hooks or shell commands are executed during installation.
