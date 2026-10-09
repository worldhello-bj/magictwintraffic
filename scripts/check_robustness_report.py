#!/usr/bin/env python3
"""Exercise robustness-report rejection guards without modifying original evidence."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from report_robustness import audit_run, analyze, save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('docs/evidence/robustness_report_validation.json'))
    args = parser.parse_args()
    plan = json.loads((args.state / 'study-plan.json').read_text())
    ledger = json.loads((args.state / 'verification-execution.json').read_text())
    job = next(r for r in ledger['runs'] if r['status'] == 'succeeded')
    original = args.state / 'runs' / job['run_id']
    passed = []
    audit_run(original, job['spec'])
    passed.append('Unmodified completed run passes independent audit')

    def reject(name, action, expected):
        try:
            action()
        except ValueError as error:
            if expected not in str(error):
                raise AssertionError(f'{name}: unexpected error {error}') from error
            passed.append(name)
        else:
            raise AssertionError(f'{name}: corrupted evidence was accepted')

    wrong_spec = {**job['spec'], 'seed': job['spec']['seed'] + 1}
    reject('Changed frozen run specification is rejected',
           lambda: audit_run(original, wrong_spec), 'frozen cell')

    def corrupt(name, filename, mutate, expected, update_checksum=True):
        with tempfile.TemporaryDirectory(prefix='traffic-robustness-audit-') as temporary:
            path = Path(temporary) / 'run'
            path.mkdir()
            manifest = json.loads((original / 'manifest.json').read_text())
            for artifact in ('manifest.json', *manifest['artifact_hashes']):
                shutil.copyfile(original / artifact, path / artifact)
            value = json.loads((path / filename).read_text())
            mutate(value)
            save(path / filename, value)
            if update_checksum:
                manifest['artifact_hashes'][filename] = hashlib.sha256((path / filename).read_bytes()).hexdigest()
                save(path / 'manifest.json', manifest)
            reject(name, lambda: audit_run(path, job['spec']), expected)

    corrupt('Changed artifact bytes are rejected by checksum', 'timeseries.json',
            lambda rows: rows[-1].update(inside=rows[-1]['inside'] + 1), 'checksum mismatch', False)
    corrupt('Self-consistent checksum cannot hide invalid population', 'timeseries.json',
            lambda rows: rows[-1].update(inside=rows[-1]['inside'] + 1), 'population differs')
    corrupt('Self-consistent checksum cannot hide exposure drift', 'timeseries.json',
            lambda rows: rows[-1].update(tstt_vehicle_seconds=rows[-1]['tstt_vehicle_seconds'] + 1),
            'exposure reconstruction failed')
    corrupt('Missing saved time row is rejected', 'timeseries.json', lambda rows: rows.pop(), 'incomplete or reordered')
    corrupt('Invalid insertion ordering is rejected', 'trips.json',
            lambda rows: rows[0].update(inserted_at=-1), 'insertion ordering')
    corrupt('Modified exogenous trip identity is rejected', 'trips.json',
            lambda rows: rows[0].update(behavior_seed=rows[0]['behavior_seed'] + 1), 'exogenous demand hash')
    corrupt('Unexpected constraint event is rejected in nominal run', 'events.json',
            lambda rows: rows.append({'type': 'downstream_constraint_start', 'time': 3600}),
            'unplanned downstream constraint')
    changed = copy.deepcopy(ledger)
    changed['status'] = 'incomplete'
    reject('Incomplete matrix is rejected', lambda: analyze(plan, changed, args.state), 'fully completed')
    if ledger['status'] == 'complete':
        changed = copy.deepcopy(ledger)
        changed['runs'][1] = copy.deepcopy(changed['runs'][0])
        reject('Duplicate matrix cell is rejected', lambda: analyze(plan, changed, args.state), 'duplicate')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {'status': 'passed', 'tests_passed': len(passed), 'tests': passed,
              'scope': 'Focused report integrity guard tests; this is not a replacement for the full project test suite.',
              'source_run_id': job['run_id'], 'original_evidence_unchanged': True}
    save(args.output, result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
