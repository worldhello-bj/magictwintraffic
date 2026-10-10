"""Published viewer preparation never regenerates retired or already valid runs."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


module = load('ensure_high_pressure_demo')


def test_verified_pressure_demo_is_reused(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'available', lambda *a, **k: True)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: pytest.fail('Must not regenerate verified replay'))
    module.ensure(tmp_path)


def test_missing_demo_builds_network_then_seed42_only(tmp_path, monkeypatch):
    states = iter([False, False, True])
    calls = []
    monkeypatch.setattr(module, 'available', lambda *a, **k: next(states))
    monkeypatch.setattr(module.subprocess, 'run', lambda a, **k: calls.append(a))
    monkeypatch.setattr(module, 'publish_catalog', lambda *a: None)
    monkeypatch.setattr(module, 'export_catalog', lambda *a: None)
    module.ensure(tmp_path)
    assert len(calls) == 4
    assert calls[0][1].endswith('build_internal_network.py') and calls[1][1].endswith('build_access_network.py')
    assert calls[2][1].endswith('build_north_surface_network.py')
    assert calls[3][-4:] == ['--seeds', '42', '--workers', '2']


def test_stale_catalog_or_heatmap_does_not_rerun_physics(tmp_path, monkeypatch):
    states = iter([False, True, True])
    operations = []
    monkeypatch.setattr(module, 'available', lambda *a, **k: next(states))
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: pytest.fail('Valid exported physics must not rerun'))
    monkeypatch.setattr(module, 'publish_catalog', lambda *a: operations.append('catalog'))
    monkeypatch.setattr(module, 'export_catalog', lambda *a: operations.append('heatmap'))
    module.ensure(tmp_path)
    assert operations == ['catalog', 'heatmap']


def test_verification_failure_is_not_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'available', lambda *a, **k: False)
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: None)
    monkeypatch.setattr(module, 'publish_catalog', lambda *a: None)
    monkeypatch.setattr(module, 'export_catalog', lambda *a: None)
    with pytest.raises(RuntimeError, match='verification'):
        module.ensure(tmp_path)


def test_missing_assets_unavailable(tmp_path):
    assert not module.available(tmp_path)


@pytest.mark.parametrize('existing', [None, {'schema_version': '1.0', 'runs': [{'run_id': 'dense_demo_S0_am_42_v1'}]}])
def test_catalog_is_rebuilt_exactly_without_obsolete_entries(tmp_path, existing):
    data = tmp_path / 'web/public/data'
    for run_id in module.IDS:
        folder = data / 'runs' / run_id
        folder.mkdir(parents=True)
        _, _, policy, period, _, _ = run_id.split('_')
        (folder / 'manifest.json').write_text(json.dumps(dict(policy=policy, period=period, duration_seconds=4200, trajectory_step_seconds=1)))
    if existing:
        (data / 'catalog.json').write_text(json.dumps(existing))
    module.publish_catalog(tmp_path)
    assert [r['run_id'] for r in json.loads((data / 'catalog.json').read_text())['runs']] == module.IDS


def test_npm_lifecycle_only_prepares_final_v3():
    scripts = json.loads((ROOT / 'web/package.json').read_text())['scripts']
    for hook in ('predev', 'pretest', 'prebuild'):
        assert 'ensure_high_pressure_demo.py' in scripts[hook]
        assert 'ensure_dense_demo.py' not in scripts[hook]
        assert 'ensure_internal_demo.py' not in scripts[hook]
    assert 'prune_replay_exports.py' in scripts['postbuild']


def test_lane_projection_follows_bent_geometry():
    p = load('analyze_high_pressure').project
    assert p(5, 1, [[0, 0], [10, 0], [10, 10]]) == 5
    assert p(11, 6, [[0, 0], [10, 0], [10, 10]]) == 16
    assert p(-3, 0, [[0, 0], [10, 0]]) == 0


def test_partial_recomputation_preserves_complete_research_evidence(tmp_path, monkeypatch):
    generator = load('run_high_pressure_demo')
    monkeypatch.setattr(generator, 'ROOT', tmp_path)
    (tmp_path / 'scenarios').mkdir()
    (tmp_path / 'scenarios/high_pressure_v3.json').write_text('{}')
    evidence = tmp_path / 'docs/evidence'
    evidence.mkdir(parents=True)
    original = json.dumps({'completed_run_count': 12, 'research_series_complete': True})
    (evidence / 'high_pressure_demo.json').write_text(original)
    (evidence / 'high_pressure_demo.csv').write_text('preserved full study')
    generator.collect(package=False)
    assert (evidence / 'high_pressure_demo.json').read_text() == original
    assert (evidence / 'high_pressure_demo.csv').read_text() == 'preserved full study'
    assert json.loads((evidence / 'high_pressure_demo_partial.json').read_text())['completed_run_count'] == 0


def test_historical_version_cannot_replace_main_catalog():
    generator = load('run_high_pressure_demo')
    with pytest.raises(ValueError, match='Only final-v3'):
        generator.collect(package=True, version=2)
