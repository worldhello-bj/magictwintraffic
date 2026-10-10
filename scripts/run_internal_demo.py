#!/usr/bin/env python3
"""Separate, uncalibrated AM/PM building OD demo; never replace formal study runs."""
import argparse
import json
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def run(job):
    from traffic_twin.simulation import run_simulation
    scenario,policy,period=job
    config_path='internal_peak_demo.json' if scenario=='severe' else 'internal_moderate_demo.json'
    prefix='internal_demo' if scenario=='severe' else 'internal_moderate'
    config=json.loads((ROOT/'scenarios'/config_path).read_text())
    config.update(policy=policy,period=period,run_id=f'{prefix}_{policy}_{period}_42_v1')
    output=ROOT/'runs'/config['run_id']
    if output.exists():
        if not (output/'manifest.json').exists():raise RuntimeError(f'Incomplete existing run: {output}; inspect before retrying')
        manifest=json.loads((output/'manifest.json').read_text())
        if manifest['config']!=config:raise RuntimeError('Existing run has different config; use a new version')
        scene_name='network' if config.get('network_variant','baseline')=='baseline' else config['network_variant']
        if manifest['network_hash']!=json.loads((ROOT/'data/canonical'/f'{scene_name}.json').read_text())['network_hash']:raise RuntimeError('Existing run uses a different network; use a new version')
    else:manifest=run_simulation(config,output)
    return manifest['run_id']


def package_all():
    from package_replays import package,write
    dest=ROOT/'web/public/data';entries=[]
    for scenario in ('moderate','severe'):
        prefix='internal_moderate' if scenario=='moderate' else 'internal_demo'
        evidence=[]
        for period in ('am','pm'):
            hashes=set()
            for policy in ('S0','S7'):
                source=ROOT/'runs'/f'{prefix}_{policy}_{period}_42_v1'
                if not (source/'manifest.json').exists():continue
                manifest=json.loads((source/'manifest.json').read_text());audit=json.loads((source/'audit.json').read_text())
                if audit['teleports'] or audit['collisions'] or not audit.get('parked_stock_conservation_passed'):raise ValueError(f'Unclean demo audit {source}')
                hashes.add(manifest['demand_hash'])
                if scenario=='moderate' or (period=='am' and policy=='S0'):
                    entry=package(source,dest,sample_seconds=1.)
                    label=f'{"常态高峰" if scenario=="moderate" else "接入网络诊断 · 后段锁死"} · {"早" if period=="am" else "晚"} · {policy}'
                    entry.update(label=label,playback_start_seconds=300,scenario_kind='uncalibrated_synthetic_building_od_peak',period=period,stress_level=scenario)
                    entries.append(entry)
                evidence.append(dict(run_id=manifest['run_id'],demand_hash=manifest['demand_hash'],metrics=json.loads((source/'metrics.json').read_text()),audit=audit))
            if len(hashes)>1:raise ValueError('Paired policies must preserve demand')
        if evidence:
            filename='internal_peak_demo' if scenario=='severe' else 'internal_moderate_demo'
            write(ROOT/f'docs/evidence/{filename}.json',dict(scenario=json.loads((ROOT/f'scenarios/{filename}.json').read_text()),runs=evidence))
    catalog=json.loads((dest/'catalog.json').read_text())
    catalog['runs']=entries+[e for e in catalog['runs'] if not e['run_id'].startswith(('internal_demo_','internal_moderate_'))];write(dest/'catalog.json',catalog)
    print(json.dumps(dict(packaged=[e['run_id'] for e in entries])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scenario',choices=['all','moderate','severe'],default='all');parser.add_argument('--package-only',action='store_true');args=parser.parse_args()
    scenarios=['moderate','severe'] if args.scenario=='all' else [args.scenario]
    if not args.package_only:
        if 'moderate' in scenarios:
            from build_internal_network import build
            build()
        with ProcessPoolExecutor(max_workers=2) as pool:
            jobs=[(scenario,policy,period) for scenario in scenarios for period in ('am','pm') for policy in ('S0','S7') if args.scenario!='all' or scenario=='moderate' or (period=='am' and policy=='S0')]
            for result in pool.map(run,jobs):print(result,flush=True)
    package_all()
