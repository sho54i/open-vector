#!/usr/bin/env python3
"""Check, install or roll back a DRAW release from Vercel. Python 3.9+; no Git."""
import argparse
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
import uuid
import zipfile

DEFAULT_MANIFEST = 'https://tensor-portal.vercel.app/draw/releases/latest.json'
MAX_PACKAGE = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
STATE = '.draw-updater'
RECEIPT = STATE + '/installed.json'


class UpdateError(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def allowed(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', name):
        return False
    parts = name.split('/')
    if any(p in ('', '.', '..') or p.endswith('.') for p in parts):
        return False
    if any(p.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))} for p in parts):
        return False
    return name in {'vector_pen_tool.html','scripts/local_updater.py','Update_DRAW.bat','UPDATE_README.txt'} or (len(parts) == 2 and parts[0] == 'vendor' and PurePosixPath(name).suffix in {'.js','.txt','.ttf','.otf','.woff'})


def target(root, name):
    if name != RECEIPT and not allowed(name):
        raise UpdateError('Disallowed update path: ' + str(name))
    p = root
    for part in name.split('/'):
        p = p / part
        if p.is_symlink() or (hasattr(p, 'is_junction') and p.is_junction()):
            raise UpdateError('Refusing linked path: ' + str(p))
    if p.exists() and not p.is_file():
        raise UpdateError('Expected a file: ' + str(p))
    return p


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.draw-write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_json(path, data):
    atomic_write(path, (json.dumps(data, indent=2) + '\n').encode())


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def origin(url):
    u = urlparse(url)
    return u.scheme, u.netloc


def validate_url(url, localhost=False):
    u = urlparse(url)
    local = localhost and u.scheme == 'http' and u.hostname in ('localhost','127.0.0.1','::1')
    if (u.scheme != 'https' and not local) or not u.hostname or u.username or u.password or u.fragment:
        raise UpdateError('Updates require an HTTPS URL (HTTP loopback only with --allow-localhost).')


class SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if origin(req.full_url) != origin(newurl):
            raise UpdateError('Refusing an update redirect to another origin.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, limit, localhost=False):
    validate_url(url, localhost)
    request = Request(url, headers={'User-Agent':'DRAW-Updater/1','Cache-Control':'no-cache'})
    with build_opener(SameOriginRedirect()).open(request, timeout=30) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise UpdateError('Download exceeds size limit.')
    return data


def validate_manifest(m):
    if not isinstance(m, dict) or m.get('schema') != 'draw-release-v1':
        raise UpdateError('Not a DRAW release manifest.')
    if type(m.get('sequence')) is not int or m['sequence'] < 1:
        raise UpdateError('Invalid release sequence.')
    if not isinstance(m.get('version'), str) or not re.fullmatch(r'[A-Za-z0-9._-]{1,80}', m['version']):
        raise UpdateError('Invalid release version.')
    if not isinstance(m.get('package'), str) or not re.fullmatch(r'draw-[A-Za-z0-9._-]+\.zip', m['package']):
        raise UpdateError('Package must be a release ZIP filename beside the manifest.')
    if type(m.get('size')) is not int or not 0 < m['size'] <= MAX_PACKAGE or not re.fullmatch('[0-9a-f]{64}', str(m.get('sha256'))):
        raise UpdateError('Invalid package size or checksum.')
    files = m.get('files')
    if not isinstance(files, dict) or not 1 <= len(files) <= 100 or 'vector_pen_tool.html' not in files:
        raise UpdateError('Invalid release file list.')
    if len({n.casefold() for n in files}) != len(files):
        raise UpdateError('Duplicate case-insensitive file names.')
    total = 0
    for name, info in files.items():
        if not allowed(name) or not isinstance(info, dict) or type(info.get('size')) is not int or not 0 < info['size'] <= MAX_EXPANDED or not re.fullmatch('[0-9a-f]{64}', str(info.get('sha256'))):
            raise UpdateError('Invalid release file: ' + str(name))
        total += info['size']
    if total > MAX_EXPANDED:
        raise UpdateError('Release exceeds expanded size limit.')
    return m


def unpack(m, data):
    if len(data) != m['size'] or digest(data) != m['sha256']:
        raise UpdateError('Package checksum/size mismatch; installation unchanged.')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries = z.infolist()
        if len(entries) != len(m['files']) or {e.filename for e in entries} != set(m['files']):
            raise UpdateError('ZIP entries do not match the manifest.')
        result = {}
        for e in entries:
            info = m['files'][e.filename]
            mode = e.external_attr >> 16
            if e.is_dir() or stat.S_ISLNK(mode) or e.flag_bits & 1 or e.file_size != info['size']:
                raise UpdateError('Invalid ZIP entry: ' + e.filename)
            blob = z.read(e)
            if digest(blob) != info['sha256']:
                raise UpdateError('File checksum mismatch: ' + e.filename)
            result[e.filename] = blob
    return result


@contextmanager
def install_lock(root):
    folder = root / STATE
    if folder.is_symlink() or (hasattr(folder, 'is_junction') and folder.is_junction()):
        raise UpdateError('Updater state directory must not be a link.')
    folder.mkdir(exist_ok=True)
    lock = folder / 'lock'
    if lock.is_symlink():
        raise UpdateError('Updater lock must not be a link.')
    with lock.open('a+b') as f:
        if f.seek(0, 2) == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            raise UpdateError('Another updater is running.') from e
        try:
            yield folder
        finally:
            if os.name == 'nt':
                f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


def check_local(root, receipt):
    for name, info in (receipt or {}).get('files', {}).items():
        p = target(root, name)
        if not p.exists() or digest(p.read_bytes()) != info['sha256']:
            raise UpdateError('Local application file changed: ' + name + '. Preserve your edit before updating.')


def restore_backup(root, journal):
    backup_id = journal.get('backup')
    if not isinstance(backup_id, str) or not re.fullmatch('[0-9a-f]{32}', backup_id):
        raise UpdateError('Invalid recovery backup identifier.')
    backup = root / STATE / 'backups' / backup_id
    # Validate every backup before changing any destination.
    restored = {}
    for name, info in journal['before'].items():
        target(root, name)
        if info is None:
            restored[name] = None
        else:
            content = (backup / name).read_bytes()
            if digest(content) != info:
                raise UpdateError('Backup checksum mismatch: ' + name)
            restored[name] = content
    for name, content in restored.items():
        p = target(root, name)
        if content is None:
            p.unlink(missing_ok=True)
        else:
            atomic_write(p, content)


def transact(root, content, fail_after=None):
    folder = root / STATE
    backup_id = uuid.uuid4().hex
    backup = folder / 'backups' / backup_id
    before = {}
    for name in content:
        p = target(root, name)
        old = p.read_bytes() if p.exists() else None
        before[name] = digest(old) if old is not None else None
        if old is not None:
            atomic_write(backup / name, old)
    journal = {'backup':backup_id,'before':before,'after':{n:digest(b) if b is not None else None for n,b in content.items()}}
    pending = folder / 'pending.json'
    write_json(pending, journal)
    try:
        for i, (name, data) in enumerate(content.items(), 1):
            p = target(root, name)
            if data is None:
                p.unlink(missing_ok=True)
            else:
                atomic_write(p, data)
            if fail_after == i:
                raise OSError('Injected write failure')
        write_json(folder / 'last-update.json', journal)
        pending.unlink()
    except BaseException:
        restore_backup(root, journal)
        pending.unlink()
        raise
    return journal


def install(root, m, files):
    with install_lock(root) as folder:
        if (folder / 'pending.json').exists():
            raise UpdateError('Interrupted update found. Run recover before installing.')
        receipt = read_json(target(root, RECEIPT))
        check_local(root, receipt)
        if receipt and m['sequence'] <= receipt['sequence']:
            if m['sequence'] == receipt['sequence'] and m['sha256'] != receipt['sha256']:
                raise UpdateError('Published release changed without a new sequence.')
            return False
        for name in files:
            target(root, name)
        content = dict(files)
        # Remove only obsolete files recorded as owned by a prior release.
        for name in (receipt or {}).get('files', {}):
            if name not in content:
                content[name] = None
        content[RECEIPT] = (json.dumps(m, indent=2)+'\n').encode()
        transact(root, content)
        return True


def rollback(root, recover=False):
    with install_lock(root) as folder:
        pending = folder / 'pending.json'
        if recover:
            if not pending.exists():
                raise UpdateError('No interrupted update to recover.')
            restore_backup(root, read_json(pending))
            last = folder / 'last-update.json'
            if last.exists() and read_json(last).get('backup') == read_json(pending).get('backup'):
                last.unlink()
            pending.unlink()
            return
        if pending.exists():
            raise UpdateError('Interrupted update found. Run recover first.')
        last = folder / 'last-update.json'
        if not last.exists():
            raise UpdateError('No update to roll back.')
        journal = read_json(last)
        for name, expected in journal['after'].items():
            p = target(root, name)
            actual = digest(p.read_bytes()) if p.exists() else None
            if actual != expected:
                raise UpdateError('Local file changed since update: ' + name + '. Preserve it before rollback.')
        # Leave an idempotent recovery journal if rollback itself is interrupted.
        write_json(pending, journal)
        restore_backup(root, journal)
        last.unlink()
        pending.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=['check','apply','rollback','recover'], default='check')
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', default=DEFAULT_MANIFEST)
    parser.add_argument('--allow-localhost', action='store_true', help='Allow HTTP loopback for smoke tests only')
    args = parser.parse_args(argv)
    root = args.directory.resolve()
    if not root.is_dir() or not (root / 'vector_pen_tool.html').is_file():
        raise UpdateError('Choose an existing DRAW folder containing vector_pen_tool.html.')
    if args.action in ('rollback','recover'):
        rollback(root, args.action == 'recover')
        print('Previous application files restored. Reopen the editor at the same path.')
        return
    manifest = validate_manifest(json.loads(download(args.manifest, 256*1024, args.allow_localhost)))
    current = read_json(target(root, RECEIPT))
    print('Installed: ' + (current['version'] if current else 'untracked local copy'))
    print('Available: ' + manifest['version'])
    if args.action == 'check':
        check_local(root, current)
        if (root / STATE / 'pending.json').exists():
            raise UpdateError('Interrupted update found. Run recover.')
        print('Update available.' if not current or manifest['sequence'] > current['sequence'] else 'No newer release.')
        return
    data = download(urljoin(args.manifest, manifest['package']), MAX_PACKAGE, args.allow_localhost)
    files = unpack(manifest, data)
    changed = install(root, manifest, files)
    print('Update installed; backup retained. Reopen the editor at the same path.' if changed else 'Already at this release or newer; no files changed.')


if __name__ == '__main__':
    try:
        main()
    except (UpdateError, OSError, ValueError, KeyError, zipfile.BadZipFile) as e:
        print('Update stopped: ' + str(e), file=sys.stderr)
        sys.exit(1)
