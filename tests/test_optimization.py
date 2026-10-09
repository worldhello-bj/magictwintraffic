"""Tuning plan tests require no SUMO and never use verification results."""
import json
from pathlib import Path
import runpy
import pytest

ROOT=Path(__file__).resolve().parents[1]
build=runpy.run_path(str(ROOT/'scripts/plan_optimization.py'))['build_optimization_plan']
analyze=runpy.run_path(str(ROOT/'scripts/report_optimization.py'))['analyze_optimization']


def test_forty_real_parameter_evaluations_and_isolated_seeds():
    plan=build(('S3','S5'))
    assert len(plan['optimization'])==40
    assert len(plan['configurations'])==10
    assert set(plan['optimization_seeds']).isdisjoint(plan['verification_seeds'])
    assert set(plan['optimization_seeds']).isdisjoint(plan['exploration_seeds'])
    assert len({json.dumps(c['policy_parameters'],sort_keys=True) for c in plan['configurations']})==10
    with pytest.raises(ValueError):build(('S2','S4'))
    with pytest.raises(ValueError):build(('S5','S5'))


def test_untunable_family_is_preserved_not_fake_optimized():
    plan=build(('S2','S6'))
    assert len(plan['optimization'])==40
    assert {s['policy'] for s in plan['optimization']}=={'S6'}


def test_incomplete_search_has_no_selection(tmp_path):
    result=analyze(build(('S3','S5')),{'runs':[]},tmp_path)
    assert result['status']=='incomplete' and result['selected_parameters'] is None


def test_selection_uses_all_pairs_and_retains_default_on_regression(tmp_path):
    plan=build(('S3','S5'));ledger={'runs':[]}
    for i,spec in enumerate(plan['optimization']):
        run_id=f'r{i}';output=tmp_path/run_id;output.mkdir()
        manifest={'run_id':run_id,'network_hash':'network','policy_hash':spec['variant_id'],
                  'demand_hash':f"{spec['period']}-{spec['seed']}",'cohort':{'warmup_seconds':900,'demand_end_seconds':8100},
                  'duration_seconds':9900,'seed':spec['seed'],'period':spec['period'],'policy':spec['policy'],
                  'demand_scale':1.0,'config':spec,'implementation_hash':'frozen','status':'completed'}
        tstt=90 if spec['variant_id'].endswith('01') else 100
        # A single tuning condition regression disqualifies S3_v01.
        if spec['variant_id']=='S3_v01' and spec['period']=='am' and spec['seed']==41:tstt=101
        metrics={'due':10,'completed':10,'inside':0,'external_waiting':0,'explicit_failure':0,
                 'collisions':0,'teleports':0,'tstt_vehicle_seconds':tstt}
        (output/'manifest.json').write_text(json.dumps(manifest));(output/'metrics.json').write_text(json.dumps(metrics))
        ledger['runs'].append({'spec':spec,'run_id':run_id,'status':'succeeded'})
    result=analyze(plan,ledger,tmp_path)
    assert result['status']=='complete'
    assert result['selected_parameters']['S3']==plan['configurations'][0]['policy_parameters']
    chosen=next(c for c in plan['configurations'] if c['variant_id']=='S5_v01')
    assert result['selected_parameters']['S5']==chosen['policy_parameters']
