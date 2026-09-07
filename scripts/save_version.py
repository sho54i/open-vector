#!/usr/bin/env python3
"""Commit DRAW and fast-forward its independent H: archive without overwriting edits."""
import argparse
from pathlib import Path
import subprocess
import sys


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('message', help='Describe the version and its validation')
    parser.add_argument('--archive', type=Path, default=Path('/mnt/h/draw-git'))
    parser.add_argument('--check', action='store_true', help='Check both repositories without committing or syncing')
    args = parser.parse_args()
    if not args.message.strip():
        parser.error('Provide a non-empty commit message.')
    source = Path(__file__).resolve().parents[1]
    archive = args.archive.resolve()
    if archive == source:
        raise RuntimeError('Run this from the working DRAW project, not from the archive.')
    for repo in (source, archive):
        if Path(git(repo, 'rev-parse', '--show-toplevel')).resolve() != repo:
            raise RuntimeError(f'{repo} is not a standalone repository root.')
        if git(repo, 'branch', '--show-current') != 'main':
            raise RuntimeError(f'{repo} must be on main. Preserve other branches before saving.')
    if git(archive, 'status', '--porcelain'):
        raise RuntimeError('Archive contains local changes. Preserve them before saving; nothing overwritten.')
    origin = git(archive, 'remote', 'get-url', 'origin')
    if Path(origin).resolve() != source:
        raise RuntimeError('Archive origin does not match this working project; nothing overwritten.')
    source_head = git(source, 'rev-parse', 'HEAD')
    archive_head = git(archive, 'rev-parse', 'HEAD')
    ancestry = subprocess.run(['git', '-C', str(source), 'merge-base', '--is-ancestor', archive_head, source_head], capture_output=True)
    if ancestry.returncode:
        raise RuntimeError('Archive history has diverged or is unknown. Reconcile it before saving; nothing overwritten.')
    if args.check:
        print(f'Ready: {source}\nArchive: {archive}\nSource HEAD: {source_head}\nArchive HEAD: {archive_head}')
        return
    git(source, 'add', '--all')
    if git(source, 'diff', '--cached', '--name-only'):
        print(git(source, 'commit', '-m', args.message))
    else:
        print('No source changes to commit; syncing existing commits and tags.')
    git(archive, 'fetch', '--tags', 'origin')
    print(git(archive, 'merge', '--ff-only', 'origin/main'))
    source_head = git(source, 'rev-parse', 'HEAD')
    if git(archive, 'rev-parse', 'HEAD') != source_head or git(archive, 'status', '--porcelain'):
        raise RuntimeError('Archive verification failed; source commit remains saved. Inspect both repositories.')
    print(f'Saved and verified {source_head} at {archive}')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError) as error:
        print(f'Save stopped: {error}', file=sys.stderr)
        sys.exit(1)
