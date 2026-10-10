#!/usr/bin/env python3
"""Publish only verified final-v3 seed-42 pairs; never regenerate retired demos."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from export_heatmaps import available as heatmap_available, export_catalog, write_json

IDS = [f'high_pressure_{policy}_{period}_42_v3' for period in ('am', 'pm') for policy in ('S0', 'S7')]


def catalog_entries(root=ROOT):
    entries = []
    for run_id in IDS:
        m = json.loads((root / 'web/public/data/runs' / run_id / 'manifest.json').read_text())
        entries.append(dict(run_id=run_id, label=f'高压拥堵 · {"早" if m["period"] == "am" else "晚"} · {m["policy"]}',
                            policy=m['policy'], manifest=f'runs/{run_id}/manifest.json', metrics=f'runs/{run_id}/metrics.json',
                            duration_seconds=m['duration_seconds'], trajectory_step_seconds=m['trajectory_step_seconds'],
                            playback_start_seconds=1200, scenario_kind='uncalibrated_synthetic_high_pressure',
                            stress_level='high_pressure', period=m['period']))
    return entries


def publish_catalog(root=ROOT):
    """Replace the public selection only; raw runs and evidence are never removed."""
    write_json(root / 'web/public/data/catalog.json', dict(schema_version='1.0', runs=catalog_entries(root)))


def available(root=ROOT, require_catalog=True, require_heatmap=True):
    try:
        config = json.loads((root / 'scenarios/high_pressure_v3.json').read_text())
        canonical = json.loads((root / 'data/canonical' / f"{config['network_variant']}.json").read_text())
        if require_catalog:
            catalog = json.loads((root / 'web/public/data/catalog.json').read_text())
            if catalog != dict(schema_version='1.0', runs=catalog_entries(root)):
                return False
        netfile = root / 'networks' / config['network_variant'] / 'network.net.xml'
        if hashlib.sha256(netfile.read_bytes()).hexdigest() != canonical['network_hash']:
            return False
        manifests = {}
        for run_id in IDS:
            folder = root / 'web/public/data/runs' / run_id
            m = json.loads((folder / 'manifest.json').read_text())
            a = json.loads((folder / 'audit.json').read_text())
            if m['run_id'] != run_id or m['status'] != 'completed' or m['seed'] != 42:
                return False
            if run_id != f"high_pressure_{m['policy']}_{m['period']}_{m['seed']}_v3":
                return False
            if any(m['config'].get(k) != v for k, v in config.items()):
                return False
            network = json.loads((folder / m['network']).read_text())
            if m['network_hash'] != canonical['network_hash'] or network['network_hash'] != m['network_hash']:
                return False
            if m['lanes'] != [lane['id'] for lane in network['lanes']]:
                return False
            if not a['conservation_passed'] or not a['parked_stock_conservation_passed'] or a['collisions'] or a['teleports']:
                return False
            for key in ('signals', 'signal_topology', 'queue_hotspots', 'stock_timeseries', 'internal_zones', 'od_matrix', 'metrics', 'timeseries'):
                json.loads((folder / m[key]).read_text())
            if not (folder / m['od_csv']).is_file() or not m['chunks']:
                return False
            for chunk in m['chunks']:
                if hashlib.sha256((folder / chunk['file']).read_bytes()).hexdigest() != chunk['sha256']:
                    return False
            if require_heatmap and not heatmap_available(folder):
                return False
            manifests[run_id] = m
        for period in ('am', 'pm'):
            if len({manifests[f'high_pressure_{p}_{period}_42_v3']['demand_hash'] for p in ('S0', 'S7')}) != 1:
                return False
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def ensure(root=ROOT):
    if available(root):
        print('Final-v3 seed-42 AM/PM paired replays and recorded road heatmaps verified.')
        return
    if not available(root, require_catalog=False, require_heatmap=False):
        python = root / '.venv/bin/python'
        python = str(python) if python.exists() else sys.executable
        for script in ('build_internal_network.py', 'build_access_network.py', 'build_north_surface_network.py'):
            subprocess.run([python, str(root / 'scripts' / script)], cwd=root, check=True)
        print('Preparing genuine final-v3 high-pressure replay pairs; first generation may take several minutes.', flush=True)
        subprocess.run([python, str(root / 'scripts/run_high_pressure_demo.py'), '--seeds', '42', '--workers', '2'], cwd=root, check=True)
    # A missing/stale catalog or derived heatmap must not rerun physics.
    publish_catalog(root)
    export_catalog(root)
    if not available(root):
        raise RuntimeError('High-pressure replay asset verification failed')


if __name__ == '__main__':
    ensure()
