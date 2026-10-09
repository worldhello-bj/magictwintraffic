#!/usr/bin/env python3
"""Restore lossless bundled data assets. Standard library only; no downloads."""
from pathlib import Path
import gzip, hashlib, json
ROOT = Path(__file__).resolve().parents[1]
def restore():
    manifest = json.loads((ROOT / 'assets/packed/manifest.json').read_text())
    count = 0
    for item in manifest['assets']:
        target = ROOT / item['path']
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256']:
            continue
        compressed = b''.join((ROOT / p).read_bytes() for p in item['parts'])
        raw = gzip.decompress(compressed)
        if len(raw) != item['size'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('Damaged bundled asset: ' + item['path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name + '.restore.tmp')
        temp.write_bytes(raw)
        temp.replace(target)
        count += 1
    print(f'Restored {count} bundled assets; all hashes match.')
if __name__ == '__main__':
    restore()
