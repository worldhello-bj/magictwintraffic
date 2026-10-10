"""Bounded topology-variant checks; no claim of field signal calibration."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
VARIANT = ROOT / 'networks/joined_nijiaqiao_v1/network.net.xml'


def norm(node):
    return node.tag, node.attrib, (node.text or '').strip(), [norm(c) for c in node]


@pytest.fixture
def ensure_variant():
    if not VARIANT.exists():
        import importlib.util
        spec = importlib.util.spec_from_file_location('build_internal_network', ROOT / 'scripts/build_internal_network.py')
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        builder.build()


def test_join_is_bounded_and_preserves_scene_metadata(ensure_variant):
    baseline = ET.parse(ROOT / 'networks/baseline/network.net.xml').getroot()
    variant = ET.parse(VARIANT).getroot()
    base = json.loads((ROOT / 'data/canonical/network.json').read_text())
    scene = json.loads((ROOT / 'data/canonical/joined_nijiaqiao_v1.json').read_text())
    assert scene['buildings'] == base['buildings']
    assert scene['gates'] == base['gates']
    be = {e['id'] for e in base['edges']}
    ve = {e['id'] for e in scene['edges']}
    assert be - ve == {'37132266#9', '-37132266#9'}
    assert not ve - be
    for tag in ('junction', 'tlLogic'):
        old = {x.get('id'): norm(x) for x in baseline.findall(tag)}
        new = {x.get('id'): norm(x) for x in variant.findall(tag)}
        assert all(old[k] == new[k] for k in old.keys() & new.keys())
    assert 'joined_nijiaqiao_v1' in {x['id'] for x in scene['traffic_lights']}
    assert scene['provenance']['network_variant']['status'] == 'topology_hypothesis_not_field_verified'


def test_atomic_builder_cache_in_isolated_workspace(tmp_path):
    import importlib.util
    import shutil
    spec = importlib.util.spec_from_file_location('isolated_internal_network', ROOT / 'scripts/build_internal_network.py')
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    for relative in ('networks/baseline/network.net.xml', 'data/canonical/network.json'):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    builder.ROOT = tmp_path
    first = builder.build()
    net = tmp_path / 'networks/joined_nijiaqiao_v1/network.net.xml'
    scene = tmp_path / 'data/canonical/joined_nijiaqiao_v1.json'
    before = net.stat().st_mtime_ns, scene.stat().st_mtime_ns
    second = builder.build()
    assert second['cache_hit'] is True
    assert (net.stat().st_mtime_ns, scene.stat().st_mtime_ns) == before
    assert first['network_hash'] == second['network_hash']
    assert first['canonical_hash'] == builder.digest(scene)
    assert first['status'] == 'ready'
    assert not list(net.parent.glob('.staging-*'))
