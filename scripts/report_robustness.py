#!/usr/bin/env python3
"""Audit and report the frozen 24-run downstream robustness extension."""
import argparse
from bisect import bisect_right
import csv
import hashlib
import json
import math
from pathlib import Path

from export_evidence import export_stage
from traffic_twin.analysis import compare_pairs, load_run, paired_interval
from traffic_twin.demand import stable_hash
from traffic_twin.schemas import Scenario

METRICS = ('tstt_vehicle_seconds', 'completion_rate', 'external_waiting')
BOOKKEEPING = ('phase', 'variant_id', 'demand_level')
INTERNAL_CONFIG = ('run_id', 'cache_key', 'implementation_hash')


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def audit_run(path, spec):
    """Reconstruct every saved cohort count and exposure directly from trip events."""
    run = load_run(path)
    manifest, metrics = run['manifest'], run['metrics']
    expected = Scenario(**{k: v for k, v in spec.items() if k not in BOOKKEEPING}).engine_config()
    actual = {k: v for k, v in manifest['config'].items() if k not in INTERNAL_CONFIG}
    if actual != expected:
        raise ValueError(f'Run differs from the frozen cell: {path.name}')
    for name, expected_hash in manifest['artifact_hashes'].items():
        candidate = (path / name).resolve()
        if not candidate.is_relative_to(path.resolve()):
            raise ValueError('Artifact path escapes its run directory')
        if hashlib.sha256(candidate.read_bytes()).hexdigest() != expected_hash:
            raise ValueError(f'Artifact checksum mismatch: {path.name}/{name}')
    audit = json.loads((path / 'audit.json').read_text())
    if not audit['conservation_passed'] or any(audit[k] for k in (
        'conservation_max_residual', 'teleports', 'collisions', 'explicit_failures', 'unexplained_losses'
    )) or not manifest['valid_for_ranking']:
        raise ValueError(f'Anomalous run: {path.name}')
    trips = json.loads((path / 'trips.json').read_text())
    if len({t['persistent_trip_id'] for t in trips}) != len(trips):
        raise ValueError('Duplicate trip identity')
    exogenous_keys = ('persistent_trip_id', 'desired_departure', 'origin_gate',
                      'destination_gate', 'vehicle_type', 'cohort_id', 'demand_source', 'behavior_seed')
    reconstructed_demand_hash = stable_hash([{k: t[k] for k in exogenous_keys} for t in trips])
    if reconstructed_demand_hash != manifest['demand_hash']:
        raise ValueError('Trip inventory does not reproduce the exogenous demand hash')
    horizon = manifest['duration_seconds']
    for trip in trips:
        desired, inserted, arrived = trip['desired_departure'], trip['inserted_at'], trip['arrived_at']
        if inserted is not None and not desired <= inserted <= horizon:
            raise ValueError('Invalid insertion ordering')
        if arrived is not None and (inserted is None or not inserted <= arrived <= horizon):
            raise ValueError('Invalid arrival ordering')
        status = ('completed' if arrived is not None else 'inside' if inserted is not None
                  else 'external_waiting' if desired <= horizon else 'future')
        if trip['status'] != status:
            raise ValueError('Trip status disagrees with its events')
        if arrived is not None and abs(trip['travel_time_seconds'] - (arrived - desired)) > 1e-8:
            raise ValueError('Completed trip time disagrees with its events')
    target = [t for t in trips if t['cohort_id'] == 'peak' and t['desired_departure'] <= horizon]
    counts = {key: sum(t['status'] == key for t in target)
              for key in ('completed', 'inside', 'external_waiting')}
    if metrics['due'] != len(target) or sum(counts.values()) != len(target):
        raise ValueError('Independent final conservation check failed')
    if any(metrics[key] != value for key, value in counts.items()):
        raise ValueError('Independent final counts disagree with evaluator')
    if metrics['all_cohort_generated'] != len(trips) or metrics['all_cohort_completed'] != sum(
        t['arrived_at'] is not None for t in trips
    ) or metrics['all_cohort_inserted'] != sum(t['inserted_at'] is not None for t in trips):
        raise ValueError('All-cohort totals disagree with trip events')
    exposure = math.fsum((t['arrived_at'] if t['arrived_at'] is not None else horizon) -
                         t['desired_departure'] for t in target)
    final_error = abs(exposure - metrics['tstt_vehicle_seconds'])
    external_time = math.fsum((t['inserted_at'] if t['inserted_at'] is not None else horizon) -
                             t['desired_departure'] for t in target)
    external_error = abs(external_time - metrics['external_wait_vehicle_seconds'])
    if max(final_error, external_error) > 1e-5:
        raise ValueError('Independent final trip-time audit failed')

    desired = sorted(t['desired_departure'] for t in target)
    inserted = sorted(t['inserted_at'] for t in target if t['inserted_at'] is not None)
    arrived = sorted(t['arrived_at'] for t in target if t['arrived_at'] is not None)
    def prefix(values):
        result = [0.0]
        for value in values:
            result.append(result[-1] + value)
        return result
    desired_prefix, arrived_prefix = prefix(desired), prefix(arrived)
    series = json.loads((path / 'timeseries.json').read_text())
    expected_times = [float(t) for t in range(5, int(horizon) + 1, 5)]
    if [r['time'] for r in series] != expected_times:
        raise ValueError('Saved time series is incomplete or reordered')
    max_series_error = 0.0
    for row in series:
        time = row['time']
        due, entered, completed = [bisect_right(items, time) for items in (desired, inserted, arrived)]
        reconstructed = {'due': due, 'completed': completed, 'inside': entered - completed,
                         'external_waiting': due - entered}
        if any(row[k] != v for k, v in reconstructed.items()):
            raise ValueError('Saved population differs from independent event reconstruction')
        if row['core_vehicles'] + row['periphery_vehicles'] != row['inside']:
            raise ValueError('Core/periphery population does not conserve vehicles')
        exact = time * (due - completed) - desired_prefix[due] + arrived_prefix[completed]
        max_series_error = max(max_series_error, abs(exact - row['tstt_vehicle_seconds']))
    if max_series_error > 1e-5:
        raise ValueError('Independent time-series exposure reconstruction failed')

    events = json.loads((path / 'events.json').read_text())
    constraints = [e for e in events if e['type'].startswith('downstream_constraint_')]
    block = expected.get('downstream_block')
    if block:
        wanted = [('downstream_constraint_start', block['start_seconds']),
                  ('downstream_constraint_end', block['end_seconds'])]
        if [(e['type'], e['time']) for e in constraints] != wanted or any(
            e['gate_id'] != block['gate_id'] or e['speed_m_s'] != block['speed_m_s'] for e in constraints
        ):
            raise ValueError('Constraint event log differs from the frozen scenario')
    elif constraints:
        raise ValueError('Nominal run contains an unplanned downstream constraint')
    return run, {
        'run_id': manifest['run_id'], 'condition': spec['variant_id'],
        'period': spec['period'], 'seed': spec['seed'], 'policy': spec['policy'],
        'peak_trip_count': len(target), 'all_trip_count': len(trips),
        'all_cohort_counts_passed': True, 'unique_trip_ids': True,
        'exogenous_demand_hash_reconstructed': reconstructed_demand_hash,
        'conservation_max_residual': 0, 'reconstructed_time_series_rows': len(series),
        'maximum_time_series_exposure_error_vehicle_seconds': max_series_error,
        'final_exposure_error_vehicle_seconds': final_error,
        'external_wait_time_error_vehicle_seconds': external_error,
        'constraint_events': constraints,
        'terminal_counts': counts,
    }


def descriptive(values):
    return {**paired_interval(values), 'minimum': min(values), 'maximum': max(values),
            'values_in_seed_order': values,
            'interpretation': 'Exploratory n=2 summary; t interval assumes approximately normal independent seed differences, cannot assess that assumption and is not multiplicity-adjusted.'}


def delta(a, b):
    result = {k: b['metrics'][k] - a['metrics'][k] for k in METRICS}
    result['completed'] = b['metrics']['completed'] - a['metrics']['completed']
    result['terminal_backlog'] = (b['metrics']['inside'] + b['metrics']['external_waiting'] -
                                  a['metrics']['inside'] - a['metrics']['external_waiting'])
    return result


def analyze(plan, ledger, state):
    specs = plan['verification']
    expected = {(s['variant_id'], s['period'], s['seed'], s['policy']): s for s in specs}
    if len(expected) != 24 or len(specs) != 24 or ledger['status'] != 'complete' or len(ledger['runs']) != 24:
        raise ValueError('Only the fully completed frozen 24-cell matrix can be reported')
    indexed, audits = {}, []
    for job in ledger['runs']:
        spec = job['spec']
        key = (spec['variant_id'], spec['period'], spec['seed'], spec['policy'])
        if key in indexed or expected.get(key) != spec or job['status'] != 'succeeded':
            raise ValueError('Unplanned, duplicate, changed or unsuccessful run')
        run, audit = audit_run(state / 'runs' / job['run_id'], spec)
        indexed[key] = run
        audits.append(audit)
    if set(indexed) != set(expected):
        raise ValueError('The robustness matrix is incomplete')
    for field in ('implementation_hash', 'engine_version', 'network_hash'):
        if len({r['manifest'][field] for r in indexed.values()}) != 1:
            raise ValueError(f'Frozen stage differs across runs: {field}')
    if {r['manifest']['implementation_hash'] for r in indexed.values()} != {ledger['implementation_hash']}:
        raise ValueError('Ledger implementation identity disagrees with runs')
    seeds = plan['robustness_seeds']
    for period in ('am', 'pm'):
        for seed in seeds:
            if len({indexed[(c, period, seed, p)]['manifest']['demand_hash']
                    for c in ('nominal', 'exit_constraint') for p in ('S0', 'S1', 'S5')}) != 1:
                raise ValueError('Exogenous demand differs across policy or external-condition cells')
    comparisons, seed_rows = [], []
    for condition in ('nominal', 'exit_constraint'):
        for period in ('am', 'pm'):
            for policy in ('S1', 'S5'):
                pairs = [(indexed[(condition, period, seed, 'S0')], indexed[(condition, period, seed, policy)])
                         for seed in seeds]
                comparison = compare_pairs(pairs, phase='robustness')
                rows = []
                for seed, (a, b) in zip(seeds, pairs):
                    row = {'condition': condition, 'period': period, 'seed': seed, 'policy': policy,
                           'baseline_run_id': a['manifest']['run_id'], 'candidate_run_id': b['manifest']['run_id'],
                           **{f'delta_{k}': v for k, v in delta(a, b).items()}}
                    rows.append(row)
                    seed_rows.append(row)
                comparison.update(condition=condition, period=period, policy=policy, seed_level_differences=rows)
                comparisons.append(comparison)
    external_effects, interactions = [], []
    for period in ('am', 'pm'):
        for policy in ('S0', 'S1', 'S5'):
            values = [delta(indexed[('nominal', period, s, policy)], indexed[('exit_constraint', period, s, policy)])
                      for s in seeds]
            external_effects.append({'period': period, 'policy': policy, 'seeds': seeds,
                                     'direction': 'exit_constraint minus nominal',
                                     'differences': {k: descriptive([v[k] for v in values]) for k in values[0]}})
        for policy in ('S1', 'S5'):
            values = []
            for seed in seeds:
                nominal = delta(indexed[('nominal', period, seed, 'S0')], indexed[('nominal', period, seed, policy)])
                constrained = delta(indexed[('exit_constraint', period, seed, 'S0')], indexed[('exit_constraint', period, seed, policy)])
                values.append({k: constrained[k] - nominal[k] for k in nominal})
            interactions.append({'period': period, 'policy': policy, 'seeds': seeds,
                                 'direction': '(candidate minus S0 under constraint) minus (candidate minus S0 under nominal)',
                                 'differences': {k: descriptive([v[k] for v in values]) for k in values[0]}})
    return {'status': 'complete', 'stage': plan['stage_name'], 'completed_runs': 24,
            'scope': plan['scope'], 'seeds': seeds,
            'elapsed_seconds': ledger['finished_at_unix'] - ledger['started_at_unix'],
            'workers': ledger['workers'], 'comparisons': comparisons,
            'external_condition_effects': external_effects, 'policy_by_condition_interactions': interactions,
            'audit': {'checked_runs': 24, 'checksum_verified': True,
                      'identical_exogenous_hashes_across_policies_and_conditions': True,
                      'all_cohort_and_peak_conservation_passed': True,
                      'maximum_final_exposure_error_vehicle_seconds': max(a['final_exposure_error_vehicle_seconds'] for a in audits),
                      'maximum_time_series_exposure_error_vehicle_seconds': max(a['maximum_time_series_exposure_error_vehicle_seconds'] for a in audits),
                      'maximum_external_wait_time_error_vehicle_seconds': max(a['external_wait_time_error_vehicle_seconds'] for a in audits),
                      'reconstructed_time_series_rows': sum(a['reconstructed_time_series_rows'] for a in audits),
                      'runs': audits},
            'hardware': {'maximum_worker_peak_rss_kib': max(r['manifest']['hardware']['peak_rss_kib'] for r in indexed.values()),
                         'worker_wall_time_seconds': [r['manifest']['wall_time_seconds'] for r in indexed.values()]},
            'not_tested': plan['not_tested']}, seed_rows


def render_report(result, plan):
    audit = result['audit']
    pm_s1 = {row['condition']: row['paired_differences']['tstt_vehicle_seconds']['mean_difference']
             for row in result['comparisons'] if row['period'] == 'pm' and row['policy'] == 'S1'}
    lines = [
        '# Bounded downstream-receiving robustness findings', '',
        'This 24-run extension completes a bounded part of experiment E. It is a small exploratory sensitivity check, not a comprehensive robustness or field-validation result. The original 316 evaluations remain a separate study; the completed total is now 340.', '',
        f'The added evidence does not establish a robust winner. For example, S1’s mean PM exposure difference changes from {pm_s1["nominal"]:+,.0f} vehicle-s nominally to {pm_s1["exit_constraint"]:+,.0f} vehicle-s under the restriction; the two restricted-PM seed differences have opposite signs. All eight comparisons contain unfinished trips, so these are observed-window effects rather than eventual full-trip-time estimates.', '',
        '## Frozen design', '',
        '- S0, S1 and S5 × AM/PM × fresh seeds 211 and 223 × nominal/constrained exit, all at medium demand (1.0).',
        '- All runs cover 9900 s: 900 s warmup, 7200 s target demand and 1800 s drain cap. Step, driver decision and control intervals remain 0.5 s.',
        '- S1 green extension and S5 managed curb stop remain fixed at 8 s. No tuning used these outcomes.',
        '- The hypothetical external constraint sets all lanes of terminal edge 441574379 at gate W_exit_441574379 to 0.1 m/s from t=3600 to 4500 s (45–60 minutes after the peak starts), then restores their original maximum speeds. It is a speed restriction, not a fully closed exit or a calibrated downstream service rate.',
        '- The affected gate had 2227 scheduled peak destinations across the four existing medium-demand exploration inventories (AM/PM, seeds 11/29), the largest gate total. Selection used scheduled demand only, not policy performance.',
        '- Two fresh seeds were frozen before execution and are disjoint from exploration, tuning and independent verification. No seed or condition was dropped or added after observing results.',
        '- The unchanged runner uses its “verification” storage slot. This is only an execution adapter; the results below remain exploratory robustness and are not pooled into the earlier 180 verification runs.', '',
        '## Integrity and actual execution', '',
        f'- All 24 planned runs succeeded. Full artifact checksums, unique trip identities, valid trip event ordering, and final all-cohort and peak counts passed.',
        f'- All {audit["reconstructed_time_series_rows"]:,} saved 5-second peak-population rows were independently reconstructed from desired-departure, insertion and arrival events; maximum conservation residual was zero.',
        f'- Independent peak trip-elapsed-time totals agree with the evaluator within {audit["maximum_final_exposure_error_vehicle_seconds"]:.3g} vehicle-s. Maximum saved-time-series exposure discrepancy was {audit["maximum_time_series_exposure_error_vehicle_seconds"]:.3g} vehicle-s; external-wait-time discrepancy was {audit["maximum_external_wait_time_error_vehicle_seconds"]:.3g} vehicle-s.',
        '- No reported collisions, teleports, explicit failures or unexplained losses. All 12 constrained runs logged the exact scheduled start/end; nominal runs logged none.',
        '- Every period/seed has identical exogenous demand hashes across all six policy/condition cells. Implementation, network and engine versions are shared.',
        f'- Observed stage elapsed: {result["elapsed_seconds"] / 60:.2f} minutes with {result["workers"]} workers. Largest reported worker peak RSS: {result["hardware"]["maximum_worker_peak_rss_kib"] / 1024:.1f} MiB. These are environment measurements, not hardware performance guarantees.', '',
        '## Policy effects within each external condition', '',
        'Each row is candidate minus S0 for two paired seeds. Exposure includes unfinished and uninserted target trips up to the common horizon. Negative exposure is not an eventual full-trip-time benefit when cohorts remain unfinished. The intervals are unadjusted two-sided paired Student t intervals with only one degree of freedom; their distributional assumption cannot be assessed with two seeds. Use these as descriptive sensitivity evidence, not confirmatory significance tests.', '',
        '| Condition | Period | Policy | Seed 211 Δ exposure | Seed 223 Δ exposure | Mean Δ exposure | Marginal 95% CI | Mean Δ completion (pp) | Mean Δ external waiting |',
        '|---|---|---|---:|---:|---:|---|---:|---:|',
    ]
    for row in result['comparisons']:
        d = row['paired_differences']; t = d['tstt_vehicle_seconds']
        vals = [s['delta_tstt_vehicle_seconds'] for s in row['seed_level_differences']]
        lines.append(f'| {row["condition"]} | {row["period"].upper()} | {row["policy"]} | {vals[0]:+,.1f} | {vals[1]:+,.1f} | {t["mean_difference"]:+,.1f} | [{t["ci_low"]:+,.1f}, {t["ci_high"]:+,.1f}] | {100*d["completion_rate"]["mean_difference"]:+.3f} | {d["external_waiting"]["mean_difference"]:+.1f} |')
    incomplete = sum(not r['all_target_trips_complete'] for r in result['comparisons'])
    lines += ['', f'{incomplete} of the eight policy/condition comparisons include unfinished target trips. Completed-only means and P95 values are not used for ranking. Full seed-level completion, backlog and waiting differences are in `evidence/robustness_pairs.csv`.', '',
              '## Effect of the external constraint', '',
              'These differences compare the same policy, period and seed under constrained versus nominal receiving conditions. They show the scenario perturbation, not a policy benefit.', '',
              '| Period | Policy | Seed 211 Δ exposure | Seed 223 Δ exposure | Mean Δ exposure | Mean Δ completion (pp) | Mean Δ external waiting |',
              '|---|---|---:|---:|---:|---:|---:|']
    for row in result['external_condition_effects']:
        d = row['differences']; t = d['tstt_vehicle_seconds']; v = t['values_in_seed_order']
        lines.append(f'| {row["period"].upper()} | {row["policy"]} | {v[0]:+,.1f} | {v[1]:+,.1f} | {t["mean_difference"]:+,.1f} | {100*d["completion_rate"]["mean_difference"]:+.3f} | {d["external_waiting"]["mean_difference"]:+.1f} |')
    lines += ['', 'Some restriction-minus-nominal differences are negative. The full-network stochastic response is not monotonic in this small sample; this does not justify deliberate exit restriction as a beneficial intervention.', '',
              '## Policy-by-condition sensitivity', '',
              'Each interaction is (candidate − S0 under the constraint) − (candidate − S0 under nominal conditions). A positive exposure interaction means the candidate’s relative observed-window performance deteriorated under the constraint; it does not establish a general failure or an eventual travel-time effect.', '',
              '| Period | Policy | Seed 211 interaction | Seed 223 interaction | Mean exposure interaction (vehicle-s) |',
              '|---|---|---:|---:|---:|']
    for row in result['policy_by_condition_interactions']:
        t = row['differences']['tstt_vehicle_seconds']; v = t['values_in_seed_order']
        lines.append(f'| {row["period"].upper()} | {row["policy"]} | {v[0]:+,.1f} | {v[1]:+,.1f} | {t["mean_difference"]:+,.1f} |')
    lines += ['', '## Limits and reproduction', '',
              'This one-gate, one-duration perturbation does not cover internal E1 activity, reconstructed expanded-boundary demand, navigation response, independent curb-event intensity changes, matched fixed-integrator step-size tests, or field calibration. Those remain pending. Existing curb events are retained and paired; S5 changes their stop duration as its frozen policy mechanism, not as an independently varied external condition.', '',
              'A lower exposure observation, wide interval, or two same-direction seeds cannot identify an overall robust winner. Interpretation must retain completion and external backlog alongside exposure.', '',
              'From the repository root with locked dependencies installed:', '',
              '```sh',
              'PYTHONPATH=src python scripts/plan_robustness.py',
              'PYTHONPATH=src python scripts/run_study.py --plan docs/evidence/robustness_plan.json --phase verification --state var/robustness-v1 --workers 4 --keep-going',
              'PYTHONPATH=src python scripts/report_robustness.py --plan docs/evidence/robustness_plan.json --state var/robustness-v1',
              'PYTHONPATH=src python scripts/check_robustness_report.py --state var/robustness-v1',
              '```', '',
              'Use a new state directory if the frozen plan changes. The scheduler checks source/input/dependency fingerprints, bounds each worker, validates artifacts, and marks a partial or failed matrix incomplete.', '',
              'Evidence: `robustness_plan.json`, `robustness_results.json`, `robustness_pairs.csv`, `robustness_runs.json`, `robustness_execution.json`, `robustness_subgroups.json`, `robustness_independent_check.json`, and `robustness_report_validation.json` under `docs/evidence/`. The results file additionally contains the event-based audit of every saved population row, constraint event records, external-condition effects and interactions. Raw trip inventories and time series stay in the reproducible ignored run state; their hashes are preserved in exported manifests.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--destination', type=Path, default=Path('docs/evidence'))
    parser.add_argument('--report', type=Path, default=Path('docs/robustness_findings.md'))
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if plan != json.loads((args.state / 'study-plan.json').read_text()):
        parser.error('Supplied plan differs from frozen execution snapshot')
    ledger = json.loads((args.state / 'verification-execution.json').read_text())
    result, rows = analyze(plan, ledger, args.state)
    result['plan_sha256'] = hashlib.sha256(args.plan.read_bytes()).hexdigest()
    args.destination.mkdir(parents=True, exist_ok=True)
    export_stage(args.state, 'verification', args.destination, 'robustness')
    exported = json.loads((args.destination / 'robustness_runs.json').read_text())
    exported['scope'] = 'Actual 24 completed exploratory robustness runs; verification is only the unchanged runner storage slot.'
    save(args.destination / 'robustness_runs.json', exported)
    save(args.destination / 'robustness_results.json', result)
    with (args.destination / 'robustness_pairs.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(result, plan))
    print(json.dumps({'status': result['status'], 'runs': result['completed_runs'],
                      'elapsed_seconds': result['elapsed_seconds'],
                      'audit': {k: v for k, v in result['audit'].items() if k != 'runs'},
                      'report': str(args.report)}))


if __name__ == '__main__':
    main()
