#!/usr/bin/env python3
"""Preserve failed and successful pressure probes, including censoring and all residual queues."""
import json,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 rows=[];runs=[]
 for p in sorted((ROOT/'runs').glob('pressure_probe*/manifest.json')):
  m=json.loads(p.read_text());d=p.parent;s=json.loads((d/'timeseries.json').read_text());metrics=json.loads((d/'metrics.json').read_text());end=m['config']['demand_end_seconds'];clear=next((x['time'] for x in s if x['time']>=end and not x['all_cohort_inside'] and not x['all_cohort_external_waiting']),None)
  row=dict(run_id=m['run_id'],rate_per_gate=m['config']['rate_per_gate'],cars_per_building=m['config']['internal_demand']['cars_per_building'],departure_fraction=m['config']['internal_demand']['departure_fraction'],initial_departure_fraction=m['config']['internal_demand']['initial_departure_fraction'],max_network=max(x['all_cohort_inside'] for x in s),max_core=max(x['all_cohort_core_vehicles'] for x in s),max_stopped=metrics['max_queue_vehicles'],completed=metrics['all_cohort_completed'],generated=metrics['all_cohort_generated'],final_inside=s[-1]['all_cohort_inside'],final_waiting=s[-1]['all_cohort_external_waiting'],clearance_time_seconds=clear,completion_in_final_600_seconds=s[-1]['all_cohort_completed']-next(x['all_cohort_completed'] for x in s if x['time']==m['duration_seconds']-600),teleports=metrics['teleports'],collisions=metrics['collisions'])
  rows.append(row);runs.append(dict(**row,config=m['config'],network_hash=m['network_hash'],demand_hash=m['demand_hash'],metrics=metrics,audit=json.loads((d/'audit.json').read_text()),snapshots=[x for x in s if x['time']%300==0]))
 dest=ROOT/'docs/evidence';dest.mkdir(exist_ok=True)
 (dest/'high_pressure_ladder.json').write_text(json.dumps(dict(runs=runs,interpretation='Scenario ladder, not calibrated capacity estimation; stock/initial-release settings differ between families. All residuals retained. Persistent standstill needs leader/foe diagnosis before attribution.'),ensure_ascii=False,indent=2))
 with (dest/'high_pressure_ladder.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
if __name__=='__main__':main()
