#!/usr/bin/env python3
"""Generate auditable high-pressure AM/PM same-demand policy pairs, preserving past runs."""
import argparse,csv,json,sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
def run(job):
 from traffic_twin.simulation import run_simulation
 from analyze_high_pressure import summarize
 policy,period,seed,version=job;scenario='high_pressure_access_v2.json' if version==2 else 'high_pressure_v3.json';c=json.loads((ROOT/'scenarios'/scenario).read_text());c.update(policy=policy,period=period,seed=seed,run_id=f'high_pressure_{policy}_{period}_{seed}_v{version}');p=ROOT/'runs'/c['run_id']
 if p.exists():
  if not (p/'manifest.json').exists():raise RuntimeError(f'Incomplete run preserved: {p}; choose a new run ID')
  m=json.loads((p/'manifest.json').read_text())
  if m['config']!=c:raise RuntimeError('Existing run config differs; do not overwrite')
  expected=json.loads((ROOT/'data/canonical'/f"{c['network_variant']}.json").read_text())['network_hash']
  if m['network_hash']!=expected:raise RuntimeError('Existing run network differs; do not overwrite')
 else:
  from diagnose_internal_deadlock import diagnose
  diagnose(c,p);m=json.loads((p/'manifest.json').read_text())
 a=json.loads((p/'audit.json').read_text())
 if a['collisions'] or a['teleports'] or not a['conservation_passed'] or not a['parked_stock_conservation_passed']:raise RuntimeError(f'Failed safety/conservation audit: {p}')
 result=summarize(p);(p/'high_pressure_analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result

def collect(package=True,version=3):
 if package and version != 3:raise ValueError('Only final-v3 runs may replace the public catalog; use --no-package for historical versions')
 from package_replays import package as package_run,write
 runs=[json.loads(p.read_text()) for p in sorted((ROOT/'runs').glob(f'high_pressure_*_v{version}/high_pressure_analysis.json'))];pairs=[]
 for period in ('am','pm'):
  for seed in sorted(set(x['config']['seed'] for x in runs)):
   pair={x['config']['policy']:x for x in runs if x['config']['period']==period and x['config']['seed']==seed}
   if set(pair)!={'S0','S7'}:continue
   a,b=pair['S0'],pair['S7']
   if a['demand_hash']!=b['demand_hash'] or a['network_hash']!=b['network_hash']:raise ValueError('Pair not same OD/network')
   pairs.append(dict(period=period,seed=seed,demand_hash=a['demand_hash'],s0=a['run_id'],s7=b['run_id'],s7_minus_s0_tstt_percent=100*(b['metrics']['tstt_vehicle_seconds']/a['metrics']['tstt_vehicle_seconds']-1),s7_minus_s0_completed=b['metrics']['all_cohort_completed']-a['metrics']['all_cohort_completed']))
 evidence=dict(completed_run_count=len(runs),expected_research_run_count=12,research_series_complete=len(runs)==12,scenario=json.loads((ROOT/'scenarios'/('high_pressure_access_v2.json' if version==2 else 'high_pressure_v3.json')).read_text()),calibration_status='uncalibrated_synthetic_capacity_stress_not_observed_Chengdu',runs=runs,paired_comparisons=pairs)
 evidence_stem='high_pressure_demo' if version==3 else f'high_pressure_demo_v{version}'
 existing=ROOT/'docs/evidence'/f'{evidence_stem}.json'
 if existing.exists() and json.loads(existing.read_text()).get('completed_run_count',0)>len(runs):evidence_stem+='_partial'
 write(ROOT/'docs/evidence'/f'{evidence_stem}.json',evidence)
 flat=[]
 for x in runs:
  m=x['metrics'];flat.append(dict(run_id=x['run_id'],period=x['config']['period'],policy=x['config']['policy'],seed=x['config']['seed'],generated=m['all_cohort_generated'],completed=m['all_cohort_completed'],final_inside=x['final_state']['all_cohort_inside'],final_waiting=x['final_state']['all_cohort_external_waiting'],peak_inside=x['occupancy']['all_cohort_inside']['peak'],peak_core=x['occupancy']['all_cohort_core_vehicles']['peak'],peak_stopped=m['max_queue_vehicles'],peak_core_stopped=x['peak_strict_core_stopped'],mean_speed_km_h=x['sampled_space_mean_speed_km_h'],mean_core_speed_km_h=x['sampled_core_space_mean_speed_km_h'],completed_mean_delay_seconds=x['completed_only_mean_delay_seconds'],peak_cohort_tstt_vehicle_seconds=m['tstt_vehicle_seconds'],clearance_time_seconds=x['clearance_time_seconds'],collisions=x['audit']['collisions'],teleports=x['audit']['teleports']))
 if flat:
  with (ROOT/'docs/evidence'/f'{evidence_stem}.csv').open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
 if package:
  from ensure_high_pressure_demo import IDS,publish_catalog
  from export_heatmaps import export_catalog
  final={x['run_id'] for x in runs if x['config']['seed']==42}
  if final!=set(IDS):raise ValueError('All four final-v3 seed-42 replays are required before publishing')
  dest=ROOT/'web/public/data';entries=[]
  for x in sorted(runs,key=lambda x:(x['config']['period'],x['config']['policy'])):
   if x['config']['seed']!=42:continue
   p=ROOT/'runs'/x['run_id'];entry=package_run(p,dest,sample_seconds=1.);entry.update(label=f'高压拥堵 · {"早" if x["config"]["period"]=="am" else "晚"} · {x["config"]["policy"]}',playback_start_seconds=1200,scenario_kind='uncalibrated_synthetic_high_pressure',stress_level='high_pressure',period=x['config']['period']);entries.append(entry);write(dest/'runs'/x['run_id']/'high_pressure_analysis.json',x)
  publish_catalog(ROOT)
  export_catalog(ROOT)
 print(json.dumps(dict(runs=len(runs),pairs=pairs,packaged=package)),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--version',type=int,choices=(2,3),default=3);p.add_argument('--seeds',default='42,43,44');p.add_argument('--workers',type=int,default=3);p.add_argument('--package-only',action='store_true');p.add_argument('--no-package',action='store_true');a=p.parse_args()
 if a.version!=3 and not a.no_package:p.error('Historical versions require --no-package; only final v3 is published')
 if not a.package_only:
  jobs=[(policy,period,int(seed),a.version) for seed in a.seeds.split(',') for period in ('am','pm') for policy in ('S0','S7')]
  with ProcessPoolExecutor(max_workers=a.workers) as pool:
   for x in pool.map(run,jobs):print(json.dumps(dict(run_id=x['run_id'],clearance=x['clearance_time_seconds'],peak_inside=x['occupancy']['all_cohort_inside']['peak'],peak_core=x['occupancy']['all_cohort_core_vehicles']['peak'])),flush=True)
 collect(not a.no_package,a.version)
