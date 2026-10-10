#!/usr/bin/env python3
"""Generate a separate, paired synthetic busy-period demo, never formal study results."""
import argparse
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def run(policy):
    from traffic_twin.simulation import run_simulation
    config = json.loads((ROOT / 'scenarios/dense_demo.json').read_text())
    config.update(policy=policy, run_id=f'dense_demo_{policy}_am_42_v1')
    output = ROOT / 'runs' / config['run_id']
    if (output / 'manifest.json').exists():
        raise RuntimeError(f'Refusing to overwrite completed demo: {output}')
    if output.exists():
        preserved = output.with_name(output.name + f'.incomplete-{time.time_ns()}')
        output.rename(preserved)
        print(f'Preserved incomplete attempt at {preserved}', flush=True)
    manifest = run_simulation(config, output)
    return {key: manifest[key] for key in ('run_id', 'demand_hash', 'valid_for_ranking', 'wall_time_seconds')}


def package_pair():
    from package_replays import package, write
    destination = ROOT / 'web/public/data'
    entries = []
    evidence = {'scenario': json.loads((ROOT / 'scenarios/dense_demo.json').read_text()), 'observation_window_seconds': [600, 1500], 'occupancy_sample_seconds': 5, 'runs': []}
    hashes = set()
    for policy in ['S0', 'S7']:
        source = ROOT / 'runs' / f'dense_demo_{policy}_am_42_v1'
        manifest = json.loads((source / 'manifest.json').read_text())
        for key, value in evidence['scenario'].items():
            if manifest['config'].get(key) != value:
                raise ValueError(f'Run does not match demo configuration: {key}')
        audit = json.loads((source / 'audit.json').read_text())
        if not audit['conservation_passed'] or audit['teleports'] or audit['collisions']:
            raise ValueError('Demo failed conservation or vehicle safety audit')
        hashes.add(manifest['demand_hash'])
        entry = package(source, destination)
        entry.update(playback_start_seconds=600, scenario_kind='uncalibrated_synthetic_busy_demo', demand_rate_per_gate_veh_h=360)
        entries.append(entry)
        series = json.loads((source / 'timeseries.json').read_text())
        observed = [row for row in series if 600 <= row['time'] <= 1500]
        metrics = json.loads((source / 'metrics.json').read_text())
        evidence['runs'].append(dict(run_id=manifest['run_id'], demand_hash=manifest['demand_hash'], metrics=metrics, audit=audit, at_playback_start=observed[0], at_end=series[-1], occupancy={key: {'mean': statistics.mean(row[key] for row in observed), 'peak': max(row[key] for row in observed)} for key in ['all_cohort_inside', 'all_cohort_core_vehicles', 'all_cohort_periphery_vehicles', 'all_cohort_external_waiting', 'queue_vehicles']}))
    if len(hashes) != 1:
        raise ValueError('Policy pair must share the exact exogenous trip inventory')
    catalog_path = destination / 'catalog.json'
    catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else {'schema_version': '1.0', 'runs': []}
    ids = {entry['run_id'] for entry in entries}
    catalog['runs'] = entries + [entry for entry in catalog['runs'] if entry['run_id'] not in ids]
    write(catalog_path, catalog)
    write(ROOT / 'docs/evidence/dense_demo.json', evidence)
    print(json.dumps({'packaged': sorted(ids), 'evidence': 'docs/evidence/dense_demo.json'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--policies', default='S0,S7', help='Generate only these missing demo policies (S0,S7)')
    parser.add_argument('--package-only', action='store_true', help='Verify and package already completed matching runs')
    args = parser.parse_args()
    policies = args.policies.split(',')
    if not policies or any(policy not in ('S0', 'S7') for policy in policies) or len(set(policies)) != len(policies):
        parser.error('--policies must be S0, S7, or S0,S7')
    if not args.package_only:
        with ProcessPoolExecutor(max_workers=2) as pool:
            for result in pool.map(run, policies):
                print(json.dumps(result), flush=True)
    package_pair()
