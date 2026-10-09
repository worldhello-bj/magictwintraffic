from copy import deepcopy
import math
import pytest
from traffic_twin.analysis import build_study_plan, compare_pairs, paired_interval, analyze_study


def run(seed, policy="S0", completed=10, external=0, tstt=100, due=10):
    return {"manifest":{"run_id":f"{policy}-{seed}", "policy":policy,"period":"am","seed":seed,
                        "demand_scale":1.0,"demand_hash":f"arrival-{seed}","network_hash":policy,
                        "policy_hash":policy,"cohort":{"warmup_seconds":900,"demand_end_seconds":8100},
                        "rate_per_gate":120,"step_seconds":0.5,"duration_seconds":9900,"status":"succeeded"},
            "metrics":{"due":due,"completed":completed,"inside":due-completed-external,
                       "external_waiting":external,"explicit_failure":0,"tstt_vehicle_seconds":tstt,
                       "collisions":0,"teleports":0}}


def test_plan_coverage_and_seed_independence():
    pending=build_study_plan()
    assert len(pending["exploration"])==96 and not pending["verification"]
    plan=build_study_plan(candidates=("S3","S7"))
    assert len(plan["verification"])==180
    assert {r['policy'] for r in plan['exploration']}=={f"S{i}" for i in range(8)}
    assert {r['period'] for r in plan['exploration']}=={'am','pm'}
    with pytest.raises(ValueError): build_study_plan((1,2),(2,3))
    with pytest.raises(ValueError): build_study_plan(candidates=('S3','S3'))


def test_t_interval_hand_calculation():
    ci=paired_interval([1,2,3])
    assert ci['mean_difference']==2
    assert ci['ci_low']==pytest.approx(2-4.302652730/math.sqrt(3))
    assert paired_interval([1])['ci_low'] is None
    with pytest.raises(ValueError): paired_interval([float('nan')])


def test_completed_only_mean_never_wins_censored():
    a,b=run(1,completed=9,tstt=100),run(1,'S3',completed=1,external=8,tstt=10)
    b['metrics']['mean_travel_time_seconds']=1
    result=compare_pairs([(a,b)])
    assert result['conclusion']=='censored_no_travel_time_ranking'
    assert not result['travel_time_ranking_allowed']


def test_observed_dominance_is_not_full_trip_time_claim():
    result=compare_pairs([(run(1,completed=5,external=3),run(1,'S3',completed=8,external=1))])
    assert result['conclusion']=='observed_completion_backlog_dominance'
    assert not result['travel_time_ranking_allowed']


def test_final_difference_and_exploratory_guard():
    pairs=[(run(i),run(i,'S3',tstt=80)) for i in (1,2,3)]
    assert compare_pairs(pairs)['conclusion']=='lower_system_time_in_this_condition'
    assert compare_pairs(pairs,phase='exploration')['conclusion']=='exploratory_only'


@pytest.mark.parametrize('field,value',[('demand_hash','other'),('cohort',{'warmup_seconds':1}),('duration_seconds',121),('seed',999),('period','pm')])
def test_pair_guard(field,value):
    a,b=run(1),run(1,'S3')
    b['manifest'][field]=value
    with pytest.raises(ValueError): compare_pairs([(a,b)])


def test_anomaly_conservation_and_replicate_guards():
    a,b=run(1),run(1,'S3')
    b['metrics']['teleports']=1
    with pytest.raises(ValueError): compare_pairs([(a,b)])
    b=run(1,'S3'); b['metrics']['due']=11
    with pytest.raises(ValueError): compare_pairs([(a,b)])
    with pytest.raises(ValueError): compare_pairs([(a,a),(a,a)])
    with pytest.raises(ValueError): compare_pairs([(run(1),run(1,'S3')),(run(2),run(2,'S4'))])


def test_incomplete_verification_never_yields_winner():
    plan=build_study_plan(candidates=('S3','S7'))
    runs=[run(i,p,tstt=80 if p=='S3' else 100) for i in (101,102) for p in ('S0','S3')]
    report=analyze_study(runs,plan)
    assert report['status']=='incomplete'
    assert report['comparisons'][0]['conclusion']=='exploratory_only'
    assert not report['comparisons'][0]['travel_time_ranking_allowed']
    assert len(report['missing_runs'])==272


def test_unplanned_and_duplicate_rejected():
    plan=build_study_plan()
    with pytest.raises(ValueError): analyze_study([run(101)],plan)
    with pytest.raises(ValueError): analyze_study([run(11),run(11)],plan)


def test_partial_cohort_and_changed_policy_versions_rejected():
    a,b=run(1),run(1,'S3')
    b['metrics']['generated']=11
    with pytest.raises(ValueError): compare_pairs([(a,b)])
    pairs=[(run(i),run(i,'S3')) for i in (1,2)]
    pairs[1][1]['manifest']['policy_hash']='different_parameters'
    with pytest.raises(ValueError): compare_pairs(pairs)


def test_anomalous_study_report_keeps_invalid_evidence():
    a,b=run(11),run(11,'S3')
    b['metrics']['collisions']=1
    report=analyze_study([a,b],build_study_plan())
    assert report['status']=='invalid'
    assert report['comparisons'][0]['conclusion']=='invalid_comparison'
    assert report['comparisons'][0]['run_pairs'][0]['candidate']=='S3-11'


def test_evidence_plot_keeps_singleton_ci_absent():
    import runpy
    from pathlib import Path
    import xml.etree.ElementTree as ET
    renderer=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/report_results.py'))['evidence_svg']
    report=analyze_study([run(11),run(11,'S3')],build_study_plan())
    svg=renderer(report)
    ET.fromstring(svg)
    assert 'n=1; no CI' in svg
    assert 'No overall leaderboard' in svg


def test_smoke_horizon_cannot_masquerade_as_formal_study():
    r=run(11)
    r['manifest']['duration_seconds']=600
    with pytest.raises(ValueError,match='frozen study configuration'): analyze_study([r],build_study_plan())


def test_frozen_verification_parameters_and_implementation_guard():
    plan=build_study_plan(candidates=('S1','S5'),candidate_parameters={'S1':{'green_extension_seconds':4.0}})
    candidate=run(101,'S1')
    with pytest.raises(ValueError,match='frozen policy parameters'):analyze_study([candidate],plan)
    candidate['manifest']['config']={'policy_parameters':{'green_extension_seconds':4.0}}
    assert analyze_study([candidate],plan)['available_runs']==1
    a,b=run(1),run(1,'S1')
    a['manifest']['implementation_hash']='old';b['manifest']['implementation_hash']='new'
    with pytest.raises(ValueError,match='implementation_hash'):compare_pairs([(a,b)])


def test_load_run_rejects_tampered_metrics(tmp_path):
    import json
    from traffic_twin.analysis import load_run
    r=run(1);r['manifest']['artifact_hashes']={'metrics.json':'bad'}
    (tmp_path/'manifest.json').write_text(json.dumps(r['manifest']))
    (tmp_path/'metrics.json').write_text(json.dumps(r['metrics']))
    with pytest.raises(ValueError,match='checksum'):load_run(tmp_path)


def test_evidence_export_rejects_incomplete_stage(tmp_path):
    import json
    import runpy
    from pathlib import Path
    export=runpy.run_path(str(Path(__file__).resolve().parents[1]/'scripts/export_evidence.py'))['export_stage']
    (tmp_path/'verification-execution.json').write_text(json.dumps({'status':'incomplete','runs':[]}))
    with pytest.raises(ValueError,match='fully completed'):export(tmp_path,'verification',tmp_path/'out','verification')
