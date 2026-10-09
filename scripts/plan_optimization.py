#!/usr/bin/env python3
"""Declare a bounded 40-evaluation parameter search after family exploration.

This creates a plan only. Seeds 41/43 are isolated from exploration 11/29 and
verification 101..110. Search is deliberately limited to medium AM/PM demand;
selected settings must subsequently pass all six verification conditions.
"""
import argparse
import json
from pathlib import Path
from traffic_twin.analysis import build_study_plan

KNOBS={
    'S1':('green_extension_seconds',),
    'S3':('green_extension_seconds','downstream_occupancy_threshold'),
    'S5':('managed_curb_stop_seconds',),
    'S6':('green_extension_seconds','downstream_occupancy_threshold'),
    'S7':('green_extension_seconds','downstream_occupancy_threshold','managed_curb_stop_seconds'),
}
# Index zero is the default parameter setting. Other entries are a declared,
# bounded space-filling candidate set, not an unrestricted black-box optimizer.
VALUES={
    'green_extension_seconds':(8.,2.,4.,12.,15.,6.,10.,14.,3.,5.),
    'downstream_occupancy_threshold':(65.,85.,50.,75.,35.,40.,55.,70.,80.,60.),
    'managed_curb_stop_seconds':(8.,4.,12.,20.,28.,6.,10.,15.,18.,24.),
}


def build_optimization_plan(families):
    families=tuple(families)
    if len(families)!=2 or len(set(families))!=2 or any(p not in tuple(f'S{i}' for i in range(1,8)) for p in families):
        raise ValueError('Provide the two distinct families frozen after exploration')
    tunable=[p for p in families if p in KNOBS]
    if not tunable:raise ValueError('Selected families expose no supported continuous parameters; do not fabricate optimization runs')
    count=10//len(tunable)
    common=build_study_plan()['experiment_config']
    configurations=[]; runs=[]
    for policy in tunable:
        for index in range(count):
            parameters={k:VALUES[k][index] for k in KNOBS[policy]}
            variant_id=f'{policy}_v{index:02}'
            configurations.append({'policy':policy,'variant_id':variant_id,'policy_parameters':parameters,'default_reference':index==0})
            for period in ('am','pm'):
                for seed in (41,43):
                    runs.append({'phase':'optimization','variant_id':variant_id,'policy':policy,
                                 'policy_parameters':parameters,'period':period,'seed':seed,
                                 'demand_level':'medium','demand_scale':1.0,'trajectory':False,**common})
    assert len(runs)==40
    return {'schema_version':'1.0','experiment_config':common,'frozen_families':list(families),
            'exploration_seeds':[11,29],'optimization_seeds':[41,43],'verification_seeds':list(range(101,111)),
            'exploration':[],'verification':[],'optimization':runs,'configurations':configurations,
            'selection_rule':'A variant is eligible only if each of its four paired tuning runs has no lower completion, no higher external waiting, and no higher finite-window TSTT than its family default. Among eligible variants minimize mean paired normalized finite-window TSTT; default wins ties. If none eligible retain default. This is an exploratory heuristic, not proof of optimality.',
            'scope':'40 full-duration evaluations. Medium AM/PM only; independent verification must cover low/medium/high demand. No verification seed may inform tuning.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--families',nargs=2,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args(); plan=build_optimization_plan(args.families)
    if args.output.exists():raise SystemExit('Refusing to overwrite an existing frozen optimization plan')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(plan,indent=2)+'\n')
    print(args.output)

if __name__=='__main__':main()
