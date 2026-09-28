#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Self-exclusion is intentional: including MANIFEST.json would require a
# self-referential size/hash that changes when the record is written.
EXCLUDE = {'MANIFEST.json'}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def collect():
    rows = []
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel in EXCLUDE or rel.startswith('staging/') or '/__pycache__/' in '/' + rel + '/' or rel.endswith('.pyc'):
            continue
        rows.append({'path': rel, 'sha256': sha256(p), 'bytes': p.stat().st_size})
    return rows


def main():
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    data = {'name': 'sd-pixelprocessor-agent', 'version': version, 'files': collect()}
    (ROOT / 'MANIFEST.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('manifest files:', len(data['files']))


if __name__ == '__main__':
    main()
