#!/usr/bin/env python3
"""Make a clean checkout's default replay usable without storing 62 MiB in Git.

Standard-library entry point: reuse verified packaged files, package completed
matching simulations, or generate only missing policies with the installed engine.
No network download is performed and completed source runs are never overwritten.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ('S0', 'S7')


def run_id(policy):
    return f'dense_demo_{policy}_am_42_v1'


def validate_manifest(folder, config, policy, packaged=False):
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest.get('status') != 'completed' or manifest.get('policy') != policy:
        raise ValueError(f'Incomplete or wrong-policy replay: {folder}')
    if any(manifest.get('config', {}).get(key) != value for key, value in config.items()):
        raise ValueError(f'Completed replay configuration differs from dense_demo.json: {folder}')
    audit = json.loads((folder / 'audit.json').read_text())
    if not audit.get('conservation_passed') or audit.get('teleports') or audit.get('collisions'):
        raise ValueError(f'Replay failed conservation/collision/teleport audit: {folder}')
    for filename in ('metrics.json', 'timeseries.json', 'signals.json', 'events.json'):
        json.loads((folder / filename).read_text())
    if not manifest.get('chunks'):
        raise ValueError(f'Missing recorded trajectory: {folder}')
    for chunk in manifest['chunks']:
        path = folder / chunk['file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != chunk['sha256']:
            raise ValueError(f'Trajectory checksum mismatch: {path}')
    if packaged and not (folder / manifest['network']).is_file():
        raise ValueError(f'Missing packaged replay network: {folder}')
    return manifest


def available_packaged(root, config):
    """Fast path still verifies actual recorded bytes, rather than file existence."""
    try:
        manifests = [validate_manifest(root / 'web/public/data/runs' / run_id(p), config, p, packaged=True) for p in POLICIES]
        catalog = json.loads((root / 'web/public/data/catalog.json').read_text())
        entries = [entry for entry in catalog['runs'] if entry['run_id'] in {run_id(p) for p in POLICIES}]
        return (len({m['demand_hash'] for m in manifests}) == 1
                and [e['run_id'] for e in entries] == [run_id(p) for p in POLICIES]
                and all(e.get('playback_start_seconds') == config['warmup_seconds'] for e in entries))
    except (OSError, ValueError, KeyError, TypeError):
        return False


def ensure(root=ROOT):
    config = json.loads((root / 'scenarios/dense_demo.json').read_text())
    if available_packaged(root, config):
        print('Dense S0/S7 replay verified; reusing existing offline assets.')
        return
    # .venv is the documented local install. CI may install into its interpreter.
    local_python = root / '.venv/bin/python'
    python = str(local_python) if local_python.exists() else sys.executable
    missing = []
    for policy in POLICIES:
        source = root / 'runs' / run_id(policy)
        if (source / 'manifest.json').exists():
            # A mismatching/damaged completed source is an explicit error, never overwritten.
            validate_manifest(source, config, policy)
        else:
            missing.append(policy)
    if missing:
        print('Generating real SUMO dense replay for ' + ', '.join(missing) + '; first build may take a minute or longer.', flush=True)
        command = [python, str(root / 'scripts/run_dense_demo.py'), '--policies', ','.join(missing)]
    else:
        command = [python, str(root / 'scripts/run_dense_demo.py'), '--package-only']
    subprocess.run(command, cwd=root, check=True)
    if not available_packaged(root, config):
        raise RuntimeError('Dense replay generation finished without a complete verified default pair')


if __name__ == '__main__':
    try:
        ensure()
    except Exception as error:
        print(f'Dense demo preparation failed: {error}. For missing engine dependencies, install requirements.lock in .venv (including SUMO/libsumo). For an invalid completed run, preserve it and review the mismatch before retrying. Existing completed runs were not overwritten.', file=sys.stderr)
        sys.exit(1)
