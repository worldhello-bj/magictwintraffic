import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('prune_replay_exports', ROOT / 'scripts/prune_replay_exports.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_pruning_removes_only_unpublished_dist_copies(tmp_path):
    data = tmp_path / 'web/dist/data'
    (data / 'networks').mkdir(parents=True)
    for name in ('current', 'old'):
        (data / 'networks' / f'{name}.json').write_text('{}')
    entries = []
    for period in ('am', 'pm'):
        for policy in ('S0', 'S7'):
            run_id = f'high_pressure_{policy}_{period}_42_v3'
            folder = data / 'runs' / run_id
            folder.mkdir(parents=True)
            (folder / 'manifest.json').write_text(json.dumps({'network': '../../networks/current.json'}))
            entries.append(dict(run_id=run_id, manifest=f'runs/{run_id}/manifest.json'))
    (data / 'catalog.json').write_text(json.dumps({'runs': entries}))
    for root in (tmp_path / 'runs', tmp_path / 'web/public/data/runs', data / 'runs'):
        old = root / 'old'
        old.mkdir(parents=True)
        (old / 'evidence.json').write_text('{}')
    assert module.prune(tmp_path) == ['old']
    assert (tmp_path / 'runs/old/evidence.json').exists()
    assert (tmp_path / 'web/public/data/runs/old/evidence.json').exists()
    assert (data / 'networks/current.json').exists()
    assert not (data / 'networks/old.json').exists()
    assert not (data / 'runs/old').exists()


def test_pruning_rejects_unexpected_catalog_before_removing_anything(tmp_path):
    data = tmp_path / 'web/dist/data'
    data.mkdir(parents=True)
    (data / 'catalog.json').write_text(json.dumps({'runs': []}))
    with pytest.raises(ValueError, match='unexpected'):
        module.prune(tmp_path)
