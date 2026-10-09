#!/usr/bin/env python3
"""Freeze a bounded downstream-receiving robustness matrix before execution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import sumolib
from traffic_twin.demand import generate_demand
from traffic_twin.schemas import Scenario
from traffic_twin.simulation import validate_config


def build_plan(source, root):
    source = Path(source)
    previous = json.loads(source.read_text())
    parameters = previous['frozen_candidate_parameters']
    if previous['frozen_candidates'] != ['S1', 'S5'] or parameters != {
        'S1': {'green_extension_seconds': 8.0},
        'S5': {'managed_curb_stop_seconds': 8.0},
    }:
        raise ValueError('This extension requires the previously frozen S1/S5 settings')
    seeds = [211, 223]
    prior_seeds = sorted(set(previous['exploration_seeds']) |
                         set(previous['verification_seeds']) | {41, 43})
    if set(seeds) & set(prior_seeds):
        raise ValueError('Robustness seeds must be independent of earlier stages')
    common = {**previous['experiment_config'], 'demand_scale': 1.0, 'trajectory': False}
    if (common['duration_seconds'], common['warmup_seconds'],
        common['demand_end_seconds'], common['step_seconds']) != (9900, 900, 8100, 0.5):
        raise ValueError('Preserve the complete frozen observation horizon and step')
    scene = json.loads((root / 'data/canonical/network.json').read_text())
    net = sumolib.net.readNet(str(root / 'networks/baseline/network.net.xml'))
    counts = Counter()
    selection = []
    for period in ('am', 'pm'):
        for seed in previous['exploration_seeds']:
            trips, demand = generate_demand(net, scene, {**common, 'period': period, 'seed': seed})
            destinations = Counter(t['destination_gate'] for t in trips if t['cohort_id'] == 'peak')
            counts.update(destinations)
            selection.append({'period': period, 'seed': seed, 'demand_hash': demand['demand_hash'],
                              'scheduled_peak_destination_counts': dict(sorted(destinations.items()))})
    gate_id = min(counts, key=lambda gate: (-counts[gate], gate))
    block = {'gate_id': gate_id, 'start_seconds': 3600.0,
             'end_seconds': 4500.0, 'speed_m_s': 0.1}
    conditions = [
        {'id': 'nominal', 'downstream_block': None,
         'description': 'Existing unrestricted terminal-lane receiving speeds.'},
        {'id': 'exit_constraint', 'downstream_block': block,
         'description': 'Hypothetical 15-minute terminal-edge speed restriction, 0.1 m/s from t=3600 to 4500 s; this is not an impermeable closure or measured service rate.'},
    ]
    specs = []
    for condition in conditions:
        for period in ('am', 'pm'):
            for seed in seeds:
                for policy in ('S0', 'S1', 'S5'):
                    spec = {**common, 'phase': 'verification', 'variant_id': condition['id'],
                            'demand_level': 'medium', 'period': period, 'seed': seed, 'policy': policy}
                    if policy in parameters:
                        spec['policy_parameters'] = parameters[policy]
                    if condition['downstream_block']:
                        spec['downstream_block'] = condition['downstream_block']
                    config = Scenario(**{k: v for k, v in spec.items()
                                         if k not in ('phase', 'variant_id', 'demand_level')}).engine_config()
                    validate_config(config)
                    specs.append(spec)
    return {
        'schema_version': '1.0', 'stage_name': 'bounded_downstream_robustness',
        'scope': '24 exploratory robustness runs, separate from the 180-run independent verification. Medium demand only; no field-effectiveness claim.',
        'storage_phase': 'verification',
        'storage_phase_note': 'The unchanged run_study.py runner accepts three phase names. Its verification slot is used only as an execution adapter; these results are reported as exploratory robustness, never pooled into original verification.',
        'source_plan': str(source), 'source_plan_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'experiment_config': common, 'frozen_candidates': previous['frozen_candidates'],
        'frozen_candidate_parameters': parameters, 'prior_stage_seeds': prior_seeds,
        'robustness_seeds': seeds, 'exploration_seeds': previous['exploration_seeds'],
        'optimization_seeds': [41, 43], 'verification_seeds': seeds,
        'conditions': conditions,
        'gate_selection': {
            'rule': 'Most scheduled peak trips in the four pre-existing medium-demand exploration inventories (AM/PM, seeds 11/29); tie-break lexical gate ID. No simulation performance or new robustness outcomes used.',
            'selected_gate': next(g for g in scene['gates'] if g['id'] == gate_id),
            'scheduled_peak_trips': counts[gate_id],
            'destination_totals': dict(sorted(counts.items())), 'source_inventories': selection},
        'stopping_rule': 'Run exactly this 24-cell matrix once. Retain anomalies and failures; do not retune, enlarge the sample or change conditions based on outcomes.',
        'analysis_rule': 'Compare each candidate to S0 within the same condition, period and seed. Report all seed-level differences, descriptive mean/range and marginal paired t intervals (n=2, df=1). Also report restriction-minus-nominal differences and policy-by-restriction interactions. No confirmatory significance or overall-winner claim; censored exposure is not eventual trip time.',
        'not_tested': ['Internal E1 activity', 'Expanded boundary with reconstructed demand',
                       'Independent curb-event intensity changes', 'Navigation-response sensitivity',
                       'Matched fixed-integrator step-size sensitivity', 'Field calibration'],
        'exploration': [], 'optimization': [], 'verification': specs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('docs/evidence/verification_plan.json'))
    parser.add_argument('--output', type=Path, default=Path('docs/evidence/robustness_plan.json'))
    args = parser.parse_args()
    result = build_plan(args.source, Path(__file__).resolve().parents[1])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output.exists() and args.output.read_text() != payload:
        parser.error('Refusing to overwrite a different frozen robustness plan')
    args.output.write_text(payload)
    print(json.dumps({'output': str(args.output), 'runs': len(result['verification']),
                      'selected_gate': result['gate_selection']['selected_gate']['id']}))


if __name__ == '__main__':
    main()
