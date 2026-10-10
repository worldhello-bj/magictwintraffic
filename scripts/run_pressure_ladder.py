#!/usr/bin/env python3
"""Reproduce the pre-access-fix diagnostic ladder without replacing any completed run."""
import argparse,json,sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
def run(job):
 from traffic_twin.simulation import run_simulation
 family,rate=job;c=json.loads((ROOT/'scenarios/internal_moderate_demo.json').read_text());prefix='pressure_probe_b3_r' if family=='b3' else 'pressure_probe_r';c.update(rate_per_gate=rate,duration_seconds=4200,demand_end_seconds=1800,trajectory=False,policy='S0',period='am',run_id=f'{prefix}{rate}_am_42_v1');c['internal_demand'].update(cars_per_building=3 if family=='b3' else 5,departure_fraction=.7 if family=='b3' else .85,initial_departure_fraction=.03 if family=='b3' else .1);p=ROOT/'runs'/c['run_id']
 if p.exists():
  if not (p/'manifest.json').exists():raise ValueError(f'Incomplete run preserved: {p}')
  m=json.loads((p/'manifest.json').read_text())
  if m['config']!=c:raise ValueError('Run configuration mismatch')
  expected=json.loads((ROOT/'data/canonical/joined_nijiaqiao_v1.json').read_text())['network_hash']
  if m['network_hash']!=expected:raise ValueError('Run network hash mismatch')
 else:m=run_simulation(c,p)
 return m['run_id']
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=3);a=p.parse_args();jobs=[('b3',r) for r in (240,300,360)]+[('b5',r) for r in (220,280,420,560)]
 with ProcessPoolExecutor(max_workers=a.workers) as pool:
  for x in pool.map(run,jobs):print(x,flush=True)
 from summarize_pressure_ladder import main
 main()
