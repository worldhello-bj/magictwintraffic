#!/usr/bin/env python3
"""Matched-horizon moderate baseline and recoverable oversaturation comparison."""
import argparse,json,sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
def run(job):
 kind,version=job
 from diagnose_internal_deadlock import diagnose
 from analyze_high_pressure import summarize
 source='internal_moderate_demo.json' if kind=='moderate_matched' else ('high_pressure_access_v2.json' if version==2 else 'high_pressure_v3.json')
 c=json.loads((ROOT/'scenarios'/source).read_text());c.update(rate_per_gate=160 if kind=='moderate_matched' else 300,duration_seconds=4200,demand_end_seconds=1800,policy='S0',period='am',run_id=f'{kind}_S0_am_42_v{version}',network_variant='joined_nijiaqiao_access_v2' if version==2 else 'joined_north_surface_v3',demo_scenario=f'synthetic_building_od_{kind}_v{version}');p=ROOT/'runs'/c['run_id']
 if not p.exists():diagnose(c,p)
 else:
  if not (p/'manifest.json').exists() or json.loads((p/'manifest.json').read_text())['config']!=c:raise ValueError('Existing comparator incomplete or configuration mismatch')
 x=summarize(p);(p/'high_pressure_analysis.json').write_text(json.dumps(x,ensure_ascii=False,indent=2));return x
if __name__=='__main__':
 from package_replays import package,write
 parser=argparse.ArgumentParser();parser.add_argument('--version',type=int,choices=(2,3),default=3);args=parser.parse_args()
 with ProcessPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,[(kind,args.version) for kind in ['moderate_matched','recovery_pressure']]))
 write(ROOT/'docs/evidence/high_pressure_comparators.json',dict(runs=results,comparison='All comparator simulations use the same corrected network and 1800s demand/4200s observation windows; demand inventories differ and are not paired policy experiments.'))
 dest=ROOT/'web/public/data';entries=[]
 for x in results:
  entry=package(ROOT/'runs'/x['run_id'],dest,sample_seconds=1.);entry.update(label='同窗适度基准 · 早 · S0' if x['config']['rate_per_gate']==160 else '撤压恢复对照 · 早 · S0',playback_start_seconds=1200,scenario_kind='uncalibrated_synthetic_pressure_comparator',stress_level='matched_moderate' if x['config']['rate_per_gate']==160 else 'recoverable_pressure',period='am');entries.append(entry)
 catalog=json.loads((dest/'catalog.json').read_text())
 if args.version==3:
  for entry in catalog['runs']:
   if entry['run_id'] in ['moderate_matched_S0_am_42_v2','recovery_pressure_S0_am_42_v2']:
    if not entry['label'].startswith('前期v2诊断 · '):entry['label']='前期v2诊断 · '+entry['label']
    entry['stress_level']='archived_topology_diagnostic'
 ids={x['run_id'] for x in entries};catalog['runs']=[x for x in catalog['runs'] if x['run_id'] not in ids]+entries;write(dest/'catalog.json',catalog)
 print([(x['run_id'],x['clearance_time_seconds']) for x in results],flush=True)
