# Open recent files

Implemented 2026-10-25; awaiting user review.

File → Open recent files lists up to eight successfully opened SVG/outline JSON files, most recent first. Selecting an entry replaces the document through the existing importer; Undo restores the previous artwork. Reopening the same filename/content promotes its entry without duplication. Files with the same name but different content remain separate entries; hover shows the opened timestamp.

Entries are browser-local source copies from the moment the file was opened. They do not track disk changes, subsequent edits, exported files or canvas drops. Opening the original file again refreshes its content. Clear recent files removes the list without changing artwork or history.

Storage key: `draw-recent-files-v1`. The serialized list is limited to 1,500,000 characters; older entries are evicted to fit. Larger files still open but are not retained. If storage is full/unavailable, a message explains that the new copy is available only in this tab. Malformed storage is ignored. Filenames render as plain text.

Validation: `python3 tests/recent_files.py` passed SVG/JSON geometry and style restoration, Undo/Redo, keyboard activation, reload, promotion, list/size bounds, clear, malformed input/storage and quota fallback. `python3 tests/pen_menu.py` passed existing File/document submenu, responsive bounds, pen, keyboard and touch checks. Browser tests use Chromium; physical-device review remains pending.

The minimise-sidebar card was skipped at the user's request; no sidebar code changed.
