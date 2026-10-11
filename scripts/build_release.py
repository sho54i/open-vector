#!/usr/bin/env python3
"""Build an immutable DRAW ZIP and latest.json for static Vercel hosting; no Git."""
import argparse
import io
import json
from pathlib import Path
import re
import zipfile
from local_updater import allowed, digest, validate_manifest, atomic_write


def build(root, output, version, sequence):
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,80}', version):
        raise ValueError('Invalid version')
    names = ['vector_pen_tool.html','scripts/local_updater.py','Update_DRAW.bat','UPDATE_README.txt']
    names += sorted(p.relative_to(root).as_posix() for p in (root/'vendor').iterdir() if p.is_file() and allowed(p.relative_to(root).as_posix()))
    content = {}
    for name in names:
        p = root/name
        if p.is_symlink():
            raise ValueError('Release files must not be links: '+name)
        content[name] = p.read_bytes()
    html=content['vector_pen_tool.html'].decode()
    for src in re.findall(r'<script\s+src="([^"]+)"',html):
        if src not in content:
            raise ValueError('Missing runtime script: '+src)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in content.items():
            info=zipfile.ZipInfo(name, (2026,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            z.writestr(info,data)
    blob=stream.getvalue()
    m=validate_manifest({'schema':'draw-release-v1','version':version,'sequence':sequence,
        'package':f'draw-{version}.zip','size':len(blob),'sha256':digest(blob),
        'files':{name:{'size':len(data),'sha256':digest(data)} for name,data in content.items()}})
    output.mkdir(parents=True,exist_ok=True)
    package=output/m['package']
    if package.exists() and package.read_bytes()!=blob:
        raise ValueError('Version already exists with different bytes. Use a new version.')
    latest=output/'latest.json'
    if latest.exists():
        previous=json.loads(latest.read_text())
        if previous['sequence']>sequence or (previous['sequence']==sequence and previous['sha256']!=m['sha256']):
            raise ValueError('Use a new, increasing sequence for changed releases.')
    atomic_write(package,blob)
    atomic_write(output/f'draw-{version}.json',(json.dumps(m,indent=2)+'\n').encode())
    atomic_write(latest,(json.dumps(m,indent=2)+'\n').encode())
    return m


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version',required=True)
    p.add_argument('--sequence',required=True,type=int)
    p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'dist/releases')
    a=p.parse_args()
    m=build(Path(__file__).resolve().parents[1],a.output,a.version,a.sequence)
    print(f"Built {m['version']}: {len(m['files'])} files, {m['size']} bytes\n{a.output / 'latest.json'}")
