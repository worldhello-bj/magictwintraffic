"""Exact recorded-sample aggregation, including empty frames and missing data."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('export_heatmaps', ROOT / 'scripts/export_heatmaps.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def fixture(tmp_path, rows=None):
    folder = tmp_path / 'run'
    folder.mkdir()
    network = dict(network_hash='network', edges=[{'id': 'a'}, {'id': 'b'}, {'id': 'unsampled'}], lanes=[
        dict(id='a_0', edge_id='a', speed=10, internal=False),
        dict(id='b_0', edge_id='b', speed=0, internal=False),
        dict(id=':internal_0', edge_id=':internal', speed=10, internal=True)])
    (folder / 'network.json').write_text(json.dumps(network))
    # Frame 2 has no vehicles. Frame 1 is warmup; exclude it from all summaries.
    if rows is None:
        rows = [(1, 0, 0, 0, 0, 5, 0, 0), (3, 0, 0, 0, 0, 0, 0, 0),
                (3, 1, 0, 0, 0, 5, 1, 0), (3, 2, 0, 0, 0, 5, 2, 0),
                (4, 0, 0, 0, 0, 15, 0, 0)]
    compressed = gzip.compress(b''.join(module.RECORD.pack(*row) for row in rows), mtime=0)
    (folder / 'chunk.gz').write_bytes(compressed)
    manifest = dict(run_id='fixture', network_hash='network', demand_hash='demand', policy_hash='policy', network='network.json',
                    lanes=[lane['id'] for lane in network['lanes']], config={'warmup_seconds': 1}, duration_seconds=4,
                    step_seconds=0.5, trajectory_step_seconds=1, chunks=[dict(file='chunk.gz', sha256=hashlib.sha256(compressed).hexdigest(),
                    records=len(rows), start=1, end=4, compression='gzip')])
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    return folder


def test_recorded_windows_include_empty_frames_and_exclude_warmup(tmp_path):
    folder = fixture(tmp_path)
    result = module.export(folder, bucket_seconds=2)
    assert result['schema_version'] == '1.0'
    assert result['definition']['interval'] == '(start,end]'
    assert result['total']['frames'] == 3
    assert [(w['start'], w['end'], w['frames']) for w in result['windows']] == [(1, 3, 2), (3, 4, 1)]
    assert result['windows'][0]['edges']['a'] == [1, 0, 1, 1, 1]
    assert result['windows'][1]['edges']['a'] == [1, 15, 0, 0, 1]
    assert result['total']['edges']['a'] == [2, 15, 1, 1, 2]
    assert result['total']['edges']['b'] == [1, 5, 0, 0, 0]
    assert 'unsampled' not in result['total']['edges']
    assert ':internal' not in result['total']['edges']
    assert result['excluded_internal_observations'] == 1
    assert result['invalid_speed_limit_observations'] == 1
    manifest = json.loads((folder / 'manifest.json').read_text())
    assert hashlib.sha256((folder / manifest['road_heatmap']).read_bytes()).hexdigest() == manifest['road_heatmap_sha256']
    assert module.available(folder, bucket_seconds=2)


def test_cached_export_is_reproducible_but_still_verifies_source_bytes(tmp_path):
    folder = fixture(tmp_path)
    module.export(folder)
    before = (folder / 'road_heatmap.json').read_bytes()
    module.export(folder)
    assert before == (folder / 'road_heatmap.json').read_bytes()
    (folder / 'chunk.gz').write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        module.export(folder)


def test_cached_identity_and_summary_checksum_are_verified(tmp_path):
    folder = fixture(tmp_path)
    module.export(folder)
    (folder / 'road_heatmap.json').write_text('{}')
    assert not module.available(folder)
    module.export(folder)
    assert module.available(folder)
    m = json.loads((folder / 'manifest.json').read_text())
    m['demand_hash'] = 'changed'
    (folder / 'manifest.json').write_text(json.dumps(m))
    assert not module.available(folder)


@pytest.mark.parametrize('rows,match', [
    ([(3, 0, 0, 0, 0, -1, 0, 0)], 'Invalid recorded'),
    ([(3, 0, 0, 0, 0, float('nan'), 0, 0)], 'Invalid recorded'),
    ([(3, 0, 0, 0, 0, 1, 8, 0)], 'lane index'),
    ([(3, 0, 0, 0, 0, 1, 0, 0), (3, 0, 0, 0, 0, 1, 0, 0)], 'Duplicate'),
    ([(4, 0, 0, 0, 0, 1, 0, 0), (3, 0, 0, 0, 0, 1, 0, 0)], 'sorted'),
])
def test_invalid_recorded_data_is_rejected(tmp_path, rows, match):
    with pytest.raises(ValueError, match=match):
        module.export(fixture(tmp_path, rows))


def test_missing_recorded_instants_are_not_filled_in(tmp_path):
    folder = fixture(tmp_path, [])
    m = json.loads((folder / 'manifest.json').read_text())
    m['chunks'][0]['end'] = 3
    (folder / 'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError, match='Missing recorded instants'):
        module.export(folder)


def test_empty_recorded_window_remains_missing_speed(tmp_path):
    result = module.export(fixture(tmp_path, []))
    assert result['total']['frames'] == 3
    assert result['total']['edges'] == {}


def test_network_identity_mismatch_is_rejected(tmp_path):
    folder = fixture(tmp_path)
    m = json.loads((folder / 'manifest.json').read_text())
    m['network_hash'] = 'other'
    (folder / 'manifest.json').write_text(json.dumps(m))
    with pytest.raises(ValueError, match='network hash'):
        module.export(folder)
