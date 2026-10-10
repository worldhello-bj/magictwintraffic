"""Clean-checkout preparation decisions; no simulator needed for these tests."""
import importlib.util
import json
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/ensure_dense_demo.py'
spec = importlib.util.spec_from_file_location('ensure_dense_demo', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def root(tmp_path):
    (tmp_path / 'scenarios').mkdir()
    (tmp_path / 'scenarios/dense_demo.json').write_text(json.dumps({'warmup_seconds': 600}))
    return tmp_path


def completed(root, policy):
    folder = root / 'runs' / module.run_id(policy)
    folder.mkdir(parents=True)
    (folder / 'manifest.json').write_text('{}')


def test_ensure_reuses_valid_packaged_pair(tmp_path, monkeypatch):
    root(tmp_path)
    monkeypatch.setattr(module, 'available_packaged', lambda *_: True)
    monkeypatch.setattr(module.subprocess, 'run', lambda *_args, **_kwargs: pytest.fail('Must not simulate or package again'))
    module.ensure(tmp_path)


@pytest.mark.parametrize('existing,flag,value', [([], '--policies', 'S0,S7'), (['S0'], '--policies', 'S7'), (['S0','S7'], '--package-only', None)])
def test_ensure_generates_only_missing_policies(tmp_path, monkeypatch, existing, flag, value):
    root(tmp_path)
    for policy in existing:
        completed(tmp_path, policy)
    availability = iter([False, True])
    monkeypatch.setattr(module, 'available_packaged', lambda *_: next(availability))
    monkeypatch.setattr(module, 'validate_manifest', lambda *_args, **_kwargs: {})
    calls = []
    monkeypatch.setattr(module.subprocess, 'run', lambda command, **kwargs: calls.append(command))
    module.ensure(tmp_path)
    assert len(calls) == 1 and flag in calls[0]
    if value:
        assert calls[0][-1] == value


def test_ensure_never_overwrites_mismatching_completed_source(tmp_path, monkeypatch):
    root(tmp_path)
    completed(tmp_path, 'S0')
    monkeypatch.setattr(module, 'available_packaged', lambda *_: False)
    monkeypatch.setattr(module.subprocess, 'run', lambda *_args, **_kwargs: pytest.fail('Completed source must not be overwritten'))
    with pytest.raises(ValueError, match='Incomplete or wrong-policy'):
        module.ensure(tmp_path)


def test_ensure_reports_failed_postcondition(tmp_path, monkeypatch):
    root(tmp_path)
    monkeypatch.setattr(module, 'available_packaged', lambda *_: False)
    monkeypatch.setattr(module.subprocess, 'run', lambda *_args, **_kwargs: None)
    with pytest.raises(RuntimeError, match='complete verified'):
        module.ensure(tmp_path)
