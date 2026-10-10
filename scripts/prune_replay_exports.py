#!/usr/bin/env python3
"""Remove unpublished replay copies from built dist only; preserve source evidence."""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prune(root=ROOT):
    data = root / 'web/dist/data'
    catalog = json.loads((data / 'catalog.json').read_text())
    expected = [f'high_pressure_{policy}_{period}_42_v3' for period in ('am', 'pm') for policy in ('S0', 'S7')]
    if [run['run_id'] for run in catalog['runs']] != expected:
        raise ValueError('Refusing to prune build with an unexpected final-v3 catalog')
    networks = set()
    for run in catalog['runs']:
        manifest_path = data / run['manifest']
        if manifest_path.resolve() != (data / 'runs' / run['run_id'] / 'manifest.json').resolve():
            raise ValueError('Catalog manifest is outside its published run directory')
        manifest = json.loads(manifest_path.read_text())
        network_path = (manifest_path.parent / manifest['network']).resolve()
        if not network_path.is_relative_to(data.resolve()) or not network_path.is_file():
            raise ValueError('Missing or external published replay network')
        networks.add(network_path)
    removed = []
    # Validate all references first. Never touch web/public, runs/, or docs/evidence.
    for folder in sorted((data / 'runs').iterdir()):
        if folder.name not in expected and folder.is_dir():
            if folder.is_symlink():
                raise ValueError('Refusing a symlink in built replay data')
            shutil.rmtree(folder)
            removed.append(folder.name)
    if (data / 'networks').exists():
        for asset in (data / 'networks').glob('*.json'):
            if asset.resolve() not in networks:
                asset.unlink()
    print(json.dumps(dict(published_runs=len(expected), removed_unpublished_build_copies=removed)))
    return removed


if __name__ == '__main__':
    prune()
