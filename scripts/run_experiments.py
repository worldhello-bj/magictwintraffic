#!/usr/bin/env python3
"""Paired SUMO experiment batches. No ranking or conclusions inferred here."""
import argparse,json,sys,itertools,shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
def run(item):
 from traffic_twin.simulation import run_simulation
 name,config=item
 result=run_simulation(config,ROOT/'runs'/name)
 return dict(run_id=name,wall_time_seconds=result['wall_time_seconds'],valid=result['valid_for_ranking'])
def publish(names):
 destination=ROOT/'web/public/data/runs';destination.mkdir(parents=True,exist_ok=True)
 catalog=[]
 for name in names:
  source=ROOT/'runs'/name
  if not (source/'manifest.json').exists():continue
  target=destination/name;target.mkdir(exist_ok=True)
  for file in ['manifest.json','metrics.json','timeseries.json','network.json','events.json','signals.json','audit.json']:
   shutil.copy2(source/file,target/file)
  if (source/'trajectory').exists():shutil.copytree(source/'trajectory',target/'trajectory',dirs_exist_ok=True)
  m=json.loads((source/'manifest.json').read_text());catalog.append(dict(run_id=name,label=f"{m['policy']} · {m['period'].upper()} · seed {m['seed']}",policy=m['policy'],manifest=f'runs/{name}/manifest.json',metrics=f'runs/{name}/metrics.json'))
 (ROOT/'web/public/data/catalog.json').write_text(json.dumps(dict(schema_version='1.0',runs=catalog),ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--policies',default='S0,S1,S2,S3,S4,S5,S6,S7');p.add_argument('--seeds',default='42');p.add_argument('--periods',default='am');p.add_argument('--scales',default='1');p.add_argument('--duration',type=float,default=9900);p.add_argument('--warmup',type=float,default=900);p.add_argument('--demand-end',type=float,default=8100);p.add_argument('--rate',type=float,default=120);p.add_argument('--workers',type=int,default=1);p.add_argument('--trajectory',action='store_true');p.add_argument('--publish',action='store_true');p.add_argument('--prefix',default='reference');a=p.parse_args()
 jobs=[]
 for policy,seed,period,scale in itertools.product(a.policies.split(','),map(int,a.seeds.split(',')),a.periods.split(','),map(float,a.scales.split(','))):
  name=f'{a.prefix}_{policy}_{period}_{seed}_d{scale:g}';config=dict(run_id=name,policy=policy,seed=seed,period=period,demand_scale=scale,duration_seconds=a.duration,warmup_seconds=a.warmup,demand_end_seconds=a.demand_end,rate_per_gate=a.rate,trajectory=a.trajectory);jobs.append((name,config))
 with ProcessPoolExecutor(max_workers=a.workers) as pool:
  futures={pool.submit(run,j):j[0] for j in jobs}
  for f in as_completed(futures):print(json.dumps(f.result()),flush=True)
 if a.publish:publish([j[0] for j in jobs])
