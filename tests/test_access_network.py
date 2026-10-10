import copy,json,xml.etree.ElementTree as ET
from pathlib import Path
import pytest,importlib.util
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module',autouse=True)
def ensure_access_network():
 for name in ['build_internal_network','build_access_network']:
  spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.build()

def test_access_variant_is_permission_only():
 roots=[ET.parse(ROOT/'networks'/v/'network.net.xml').getroot() for v in ('joined_nijiaqiao_v1','joined_nijiaqiao_access_v2')]
 lanes=[{l.get('id'):l for e in r.findall('edge') for l in e.findall('lane')} for r in roots]
 changed={k for k in lanes[0] if lanes[0][k].attrib!=lanes[1][k].attrib}
 receipt=json.loads((ROOT/'networks/joined_nijiaqiao_access_v2/build_manifest.json').read_text())
 assert changed==set(receipt['lane_permission_changes'])
 assert len(changed)==12
 for k in changed:assert set(lanes[1][k].get('allow').split())-set(lanes[0][k].get('allow').split())=={'passenger'}
 for root in roots:
  for edge in root.findall('edge'):
   for lane in edge.findall('lane'):
    lane.attrib.pop('allow',None);lane.attrib.pop('disallow',None)
 assert ET.tostring(roots[0])==ET.tostring(roots[1])
def test_access_variant_source_evidence_and_paths():
 from traffic_twin.simulation import scenario_network_paths
 scene,net=scenario_network_paths({'network_variant':'joined_nijiaqiao_access_v2'})
 assert scene.exists() and net.exists()
 receipt=json.loads((net.parent/'build_manifest.json').read_text())
 assert set(receipt['source_ways'])=={'1491845448','1033678581'}
 for w in receipt['source_ways'].values():
  assert w['tags']['motor_vehicle']=='yes'
  assert not any('conditional' in k for k in w['tags'])
 assert receipt['geometry_width_speed_signals_connections_unchanged']

def test_access_builder_atomic_cache_and_stale_file(tmp_path):
 import importlib.util,shutil
 spec=importlib.util.spec_from_file_location('isolated_access_builder',ROOT/'scripts/build_access_network.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
 for relative in ('networks/joined_nijiaqiao_v1/network.net.xml','networks/baseline/network.net.xml','data/canonical/joined_nijiaqiao_v1.json','data/raw/yulin.osm'):
  dest=tmp_path/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,dest)
 builder.ROOT=tmp_path;first=builder.build();net=tmp_path/'networks/joined_nijiaqiao_access_v2/network.net.xml';scene=tmp_path/'data/canonical/joined_nijiaqiao_access_v2.json'
 times=(net.stat().st_mtime_ns,scene.stat().st_mtime_ns);second=builder.build();assert second['cache_hit'];assert times==(net.stat().st_mtime_ns,scene.stat().st_mtime_ns)
 scene.write_text('{}');third=builder.build();assert not third.get('cache_hit');assert third['network_hash']==first['network_hash'];assert third['canonical_hash']==first['canonical_hash'];assert not list(net.parent.glob('.staging-*'))

def test_api_accepts_access_variant():
 from traffic_twin.schemas import Scenario
 assert Scenario(network_variant='joined_nijiaqiao_access_v2').network_variant=='joined_nijiaqiao_access_v2'
