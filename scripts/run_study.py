#!/usr/bin/env python3
"""Execute a saved experiment stage using isolated, checksummed SUMO workers.

Create a plan first with report_results.py --write-plan. Verification requires
explicitly frozen candidates. A partial --limit run is never stage completion.
"""
import argparse
import json
from pathlib import Path
import time
from traffic_twin.scheduler import Scheduler, TERMINAL
from traffic_twin.schemas import Scenario


def save(path, value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--phase',choices=('exploration','optimization','verification'),required=True)
    parser.add_argument('--state',type=Path,default=Path('var/study'))
    parser.add_argument('--workers',type=int,default=2,choices=range(1,9))
    parser.add_argument('--limit',type=int,help='Explicit partial batch; does not change planned sample size')
    parser.add_argument('--timeout-seconds',type=int,default=3600)
    parser.add_argument('--keep-going',action='store_true',help='Retain and report failures while continuing other planned runs')
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text())
    if set(plan['exploration_seeds']) & set(plan['verification_seeds']):
        parser.error('Exploration and verification seeds overlap')
    seed_sets=[set(plan.get(f'{phase}_seeds',[])) for phase in ('exploration','optimization','verification')]
    if any(seed_sets[i] & seed_sets[j] for i in range(3) for j in range(i+1,3)):
        parser.error('Experiment stages must use disjoint seeds')
    specs=plan[args.phase]
    if not specs:
        parser.error('No runs in this stage; freeze two candidates before verification')
    if args.limit is not None and args.limit<1:parser.error('--limit must be positive')
    selected=specs[:args.limit] if args.limit else specs
    args.state.mkdir(parents=True,exist_ok=True)
    snapshot=args.state/'study-plan.json'
    if snapshot.exists() and json.loads(snapshot.read_text()) != plan:
        parser.error('State directory belongs to a different frozen plan; choose a new state directory')
    save(snapshot,plan)
    scheduler=Scheduler(Path(__file__).resolve().parents[1],state=args.state,max_workers=args.workers,timeout_seconds=args.timeout_seconds)
    ledger={'phase':args.phase,'planned_stage_runs':len(specs),'selected_runs':len(selected),
            'status':'running','started_at_unix':time.time(),'workers':args.workers,'runs':[]}
    ledger_path=args.state/f'{args.phase}-execution.json'
    frozen_environment,implementation=scheduler.fingerprints({})
    ledger['implementation_hash']=implementation
    ledger['frozen_environment_hash']=frozen_environment
    scheduler.start()
    next_index=0
    active=[]
    failure=None
    try:
        while next_index<len(selected) or active:
            while next_index<len(selected) and len(active)<args.workers*2:
                spec=selected[next_index]
                record={'spec':spec,'status':'validating'}
                ledger['runs'].append(record)
                next_index+=1
                try:
                    config=Scenario(**{k:v for k,v in spec.items() if k not in ('phase','demand_level','variant_id')}).engine_config()
                    from traffic_twin.simulation import validate_config
                    validate_config(config)
                    current_environment,current=scheduler.fingerprints({})
                    if current != implementation or current_environment != frozen_environment:
                        raise RuntimeError('Source, network, demand inputs or dependency configuration changed during frozen batch')
                    submitted=scheduler.submit(config)
                    record.update(run_id=submitted['run_id'],status=submitted['status'],cached=submitted['cached'])
                    active.append(record)
                except Exception as exc:
                    record.update(status='failed',error=str(exc))
                    if not args.keep_going:raise
                save(ledger_path,ledger)
            for record in list(active):
                job=scheduler.get(record['run_id'])
                record.update(status=job['status'],error=job['error'])
                if job['status'] in TERMINAL:
                    active.remove(record)
                    if job['status'] == 'succeeded':
                        output=scheduler.path(job['run_id'])
                        metrics=json.loads((output/'metrics.json').read_text())
                        manifest=json.loads((output/'manifest.json').read_text())
                        if manifest.get('valid_for_ranking') is False or any(metrics.get(k,0) for k in ('explicit_failure','teleports','collisions')):
                            record.update(status='invalid',review_error='Simulation anomalies prohibit policy ranking')
                            if not args.keep_going:raise RuntimeError(f"Run {job['run_id']} contains anomalies; stop and investigate")
                    print(json.dumps({'policy':record['spec']['policy'],'seed':record['spec']['seed'],
                                      'period':record['spec']['period'],'scale':record['spec']['demand_scale'],
                                      'run_id':record['run_id'],'status':record['status']}),flush=True)
                    if job['status'] != 'succeeded' and not args.keep_going:
                        raise RuntimeError(f"Run {job['run_id']} {job['status']}: {job['error']}")
            save(ledger_path,ledger)
            if active:time.sleep(1)
    except (Exception,KeyboardInterrupt) as exc:
        failure=str(exc) or 'Interrupted'
        ledger['error']=failure
        for record in active:
            scheduler.cancel(record['run_id'])
    finally:
        scheduler.stop()
        for record in ledger['runs']:
            if record.get('run_id'):
                job=scheduler.get(record['run_id'])
                record.update(status='invalid' if record.get('review_error') else job['status'],error=job['error'])
        succeeded=sum(r['status']=='succeeded' for r in ledger['runs'])
        ledger.update(finished_at_unix=time.time(),succeeded_runs=succeeded,
                      status='complete' if succeeded==len(specs) else 'incomplete')
        save(ledger_path,ledger)
    print(json.dumps({'ledger':str(ledger_path),'status':ledger['status'],'succeeded':succeeded,'planned':len(specs)}),flush=True)
    if failure:raise SystemExit(failure)

if __name__=='__main__':main()
