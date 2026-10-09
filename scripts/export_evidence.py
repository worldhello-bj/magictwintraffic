#!/usr/bin/env python3
"""Export completed-stage provenance, group metrics and independent time audits."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
from traffic_twin.analysis import load_run


def export_stage(state,phase,destination,label):
    state,destination=Path(state),Path(destination)
    ledger=json.loads((state/f'{phase}-execution.json').read_text())
    if ledger['status']!='complete' or any(r['status']!='succeeded' for r in ledger['runs']):
        raise ValueError('Only fully completed stages can be exported as verified evidence')
    records=[];checks=[];groups=[];demand_hashes=defaultdict(set)
    for job in ledger['runs']:
        path=state/'runs'/job['run_id'];run=load_run(path);manifest=run['manifest'];metrics=run['metrics']
        for name in ('trips.json','audit.json'):
            expected=manifest.get('artifact_hashes',{}).get(name)
            if expected and hashlib.sha256((path/name).read_bytes()).hexdigest()!=expected:
                raise ValueError(f'Corrupt evidence: {job["run_id"]}/{name}')
        trips=json.loads((path/'trips.json').read_text());audit=json.loads((path/'audit.json').read_text())
        if not audit.get('conservation_passed') or any(metrics[k] for k in ('collisions','teleports','explicit_failure')):
            raise ValueError('Anomalous run requires investigation, not verified-stage export')
        horizon=manifest['duration_seconds']
        target=[t for t in trips if t['cohort_id']=='peak' and t['desired_departure']<=horizon]
        def exposure(items):
            return math.fsum((t['arrived_at'] if t['arrived_at'] is not None else horizon)-t['desired_departure'] for t in items)
        error=abs(exposure(target)-metrics['tstt_vehicle_seconds'])
        if error>1e-5:raise ValueError('Independent trip-elapsed-time audit failed')
        checks.append({'run_id':manifest['run_id'],'absolute_error_vehicle_seconds':error})
        subgroup={}
        for kind in ('car','bus'):
            subset=[t for t in target if t['vehicle_type']==kind]
            subgroup[kind]={'due':len(subset),'completed':sum(t['arrived_at'] is not None for t in subset),
                            'external_waiting':sum(t['inserted_at'] is None for t in subset),
                            'finite_window_tstt_vehicle_seconds':exposure(subset)}
        groups.append({**{k:manifest[k] for k in ('run_id','policy','period','demand_scale','seed')},'groups':subgroup})
        records.append({'spec':job['spec'],'manifest':{k:v for k,v in manifest.items() if k not in ('vehicles','lanes','chunks')},'metrics':metrics,'audit':audit})
        demand_hashes[(manifest['period'],manifest['demand_scale'],manifest['seed'])].add(manifest['demand_hash'])
    if any(len(v)!=1 for v in demand_hashes.values()):raise ValueError('Exogenous demand differs between policies or parameter variants')
    implementations={r['manifest']['implementation_hash'] for r in records}
    if len(implementations)!=1:raise ValueError('Implementation changed within stage')
    destination.mkdir(parents=True,exist_ok=True)
    artifacts={f'{label}_runs':{'scope':f'Actual {len(records)} completed {phase} runs.','runs':records},
               f'{label}_execution':ledger,
               f'{label}_subgroups':{'scope':'Peak-cohort car and bus vehicle metrics; no passenger weighting or door-to-door claim.','runs':groups},
               f'{label}_independent_check':{'checked_runs':len(records),'method':'math.fsum of arrival-or-horizon minus desired departure for every due peak trip, independently of evaluator time-series accumulation.',
                                            'maximum_absolute_error_vehicle_seconds':max(r['absolute_error_vehicle_seconds'] for r in checks),
                                            'identical_exogenous_hashes_across_policies':True,'shared_implementation_hash':next(iter(implementations)),'runs':checks}}
    for name,value in artifacts.items():
        (destination/f'{name}.json').write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    return artifacts[f'{label}_independent_check']


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path,required=True);p.add_argument('--phase',choices=('exploration','optimization','verification'),required=True)
    p.add_argument('--destination',type=Path,default=Path('docs/evidence'));p.add_argument('--label',required=True)
    args=p.parse_args()
    if not args.label.replace('_','').isalnum():p.error('Label must contain only letters, numbers and underscores')
    result=export_stage(args.state,args.phase,args.destination,args.label)
    print(json.dumps({k:v for k,v in result.items() if k!='runs'}))

if __name__=='__main__':main()
