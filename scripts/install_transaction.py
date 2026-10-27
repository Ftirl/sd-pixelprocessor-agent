"""Verify, stage, swap, rollback. Backups persist; never deletes old installation.

CLI requires an explicit destination. No credentials or unlisted files copied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import uuid


def validate_package(root):
    root=Path(root)
    manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf-8'))
    paths=set()
    for row in manifest['files']:
        if not isinstance(row.get('path'), str) or Path(row['path']).is_absolute() or '..' in Path(row['path']).parts or row['path'] == 'MANIFEST.json':
            raise ValueError('UNSAFE_MANIFEST_PATH')
        p=root/row['path']
        p.resolve().relative_to(root.resolve())
        if p.is_symlink() or row['path'] in paths:
            raise ValueError('UNSAFE_MANIFEST_PATH')
        paths.add(row['path'])
        if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256'] or p.stat().st_size!=row['bytes']:
            raise ValueError('MANIFEST_MISMATCH:'+row['path'])
    if manifest['version']!=(root/'VERSION').read_text(encoding='utf-8').strip():
        raise ValueError('VERSION_MISMATCH')
    return manifest


def install(source, destination, *, rename=os.rename, copy=shutil.copy2):
    source=Path(source).resolve(); dest=Path(destination).absolute()
    if dest.is_symlink() or dest.resolve()==source:
        raise ValueError('SELF_INSTALL_OR_SYMLINK')
    if source in dest.resolve().parents or dest.resolve() in source.parents:
        raise ValueError('OVERLAPPING_INSTALL_TREES')
    manifest=validate_package(source)
    dest.parent.mkdir(parents=True,exist_ok=True)
    token=uuid.uuid4().hex
    stage=dest.with_name(dest.name+'.stage.'+token)
    backup=dest.with_name(dest.name+'.backup.'+token)
    lock=dest.with_name(dest.name+'.install-lock')
    # A crashed install leaves the lock and evidence; never auto-replay it.
    with lock.open('x',encoding='utf-8') as f:
        json.dump({'source':str(source),'target':str(dest),'stage':str(stage),'backup':str(backup)},f)
        f.flush(); os.fsync(f.fileno())
    moved=False
    retain_lock=False
    try:
        stage.mkdir()
        for row in manifest['files']+[{'path':'MANIFEST.json'}]:
            out=stage/row['path']; out.parent.mkdir(parents=True,exist_ok=True)
            copy(source/row['path'],out)
        validate_package(stage)
        if dest.exists():
            rename(dest,backup); moved=True
        try:
            rename(stage,dest)
            validate_package(dest)
        except Exception:
            try:
                if dest.exists():
                    rename(dest,dest.with_name(dest.name+'.failed.'+token))
                if moved:
                    rename(backup,dest)
            except Exception:
                retain_lock=True
                raise
            raise
        return {'target':str(dest),'backup':str(backup) if moved else None,
                'files':len(manifest['files']),'result':'PASS'}
    finally:
        # Leave staged/failed trees for diagnosis. Never recursively delete here.
        if not retain_lock:
            lock.unlink()


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--source',default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument('--destination',required=True)
    args=ap.parse_args()
    print(json.dumps(install(args.source,args.destination),ensure_ascii=False,indent=2))
