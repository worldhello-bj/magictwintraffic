#!/usr/bin/env python3
"""Select bounded parameter settings using only the declared tuning inventory."""
import argparse
import json
from pathlib import Path
from traffic_twin.analysis import load_run, compare_pairs


def analyze_optimization(plan, ledger, runs_directory):
    expected={(s['variant_id'],s['period'],s['seed']):s for s in plan['optimization']}
    indexed={}
    errors=[]
    for record in ledger.get('runs',[]):
        spec=record['spec'];key=(spec['variant_id'],spec['period'],spec['seed'])
        if key not in expected or spec!=expected[key] or key in indexed:
            raise ValueError('Unplanned, modified or duplicated tuning record')
        if record['status']!='succeeded':
            errors.append({'spec':spec,'status':record['status'],'error':record.get('error')});continue
        run=load_run(Path(runs_directory)/record['run_id']);manifest=run['manifest'];config=manifest.get('config',{})
        for k in ('policy','period','seed','policy_parameters','duration_seconds','warmup_seconds','demand_end_seconds','demand_scale'):
            if config.get(k)!=spec.get(k):raise ValueError(f'Tuning manifest differs from frozen plan: {k}')
        indexed[key]=run
    result={'status':'incomplete','planned_evaluations':len(expected),'available_evaluations':len(indexed),
            'selection_rule':plan['selection_rule'],'scope':plan['scope'],'errors':errors,'variants':[],'selected_parameters':None}
    if len(indexed)!=len(expected):return result
    implementations={r['manifest'].get('implementation_hash') for r in indexed.values()}
    if None in implementations or len(implementations)!=1:raise ValueError('Tuning implementation changed across evaluations')
    selected={p:{} for p in plan['frozen_families']}
    for policy in sorted({c['policy'] for c in plan['configurations']}):
        configurations=[c for c in plan['configurations'] if c['policy']==policy]
        default=next(c for c in configurations if c['default_reference'])
        assessed=[]
        for variant in configurations:
            pairs=[(indexed[(default['variant_id'],period,seed)],indexed[(variant['variant_id'],period,seed)])
                   for period in ('am','pm') for seed in plan['optimization_seeds']]
            # All validity and pairing guards execute before any selection.
            comparisons=[]
            for period in ('am','pm'):
                comparisons.append(compare_pairs([(a,b) for a,b in pairs if a['manifest']['period']==period],phase='optimization'))
            eligible=all(b['metrics']['completed']>=a['metrics']['completed'] and
                         b['metrics']['external_waiting']<=a['metrics']['external_waiting'] and
                         b['metrics']['tstt_vehicle_seconds']<=a['metrics']['tstt_vehicle_seconds']
                         for a,b in pairs)
            score=sum(b['metrics']['tstt_vehicle_seconds']/max(a['metrics']['tstt_vehicle_seconds'],1.0) for a,b in pairs)/len(pairs)
            entry={**variant,'eligible':eligible,'mean_normalized_finite_window_tstt':score,'comparisons':comparisons}
            result['variants'].append(entry);assessed.append(entry)
        winner=min((v for v in assessed if v['eligible']),key=lambda v:(v['mean_normalized_finite_window_tstt'],not v['default_reference'],v['variant_id']))
        selected[policy]=winner['policy_parameters']
    result.update(status='complete',selected_parameters=selected,
                  interpretation='Selected for independent testing only; this bounded exploratory search does not establish an optimum or final benefit.')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--state',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();plan=json.loads(args.plan.read_text());ledger=json.loads((args.state/'optimization-execution.json').read_text())
    result=analyze_optimization(plan,ledger,args.state/'runs')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'selected_parameters':result['selected_parameters'],'output':str(args.output)}))

if __name__=='__main__':main()
