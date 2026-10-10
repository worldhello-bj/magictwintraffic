"""Bounded topology correction, movement retention and grade-separation regression checks."""
import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'networks/joined_nijiaqiao_access_v2/network.net.xml';TARGET=ROOT/'networks/joined_north_surface_v3/network.net.xml'
pytestmark=pytest.mark.skipif(not TARGET.exists(),reason='Build isolated north-surface variant first')
def test_only_selected_external_edges_removed_and_source_preserved():
 a=ET.parse(SOURCE).getroot();b=ET.parse(TARGET).getroot();cfg=json.loads((ROOT/'scenarios/north_surface_join.json').read_text());edges=lambda x:{e.get('id') for e in x.findall('edge') if e.get('function')!='internal'}
 assert edges(a)-edges(b)==set(cfg['expected_removed_external_edges']);assert not edges(b)-edges(a)
 receipt=json.loads((TARGET.parent/'build_manifest.json').read_text());assert receipt['baseline_network_hash']==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
def test_old_reachable_uturn_is_retained_with_signal_control():
 x=ET.parse(TARGET).getroot();found=[c for c in x.findall('connection') if c.get('from')=='136053867#2' and c.get('to')=='459143633#0'];assert len(found)==1
 c=found[0];assert c.get('fromLane')=='2' and c.get('toLane')=='2';assert c.get('dir')=='t';assert c.get('tl')=='joined_north_surface_v3'
def test_tunnel_edge_geometry_and_permissions_unchanged():
 a=ET.parse(SOURCE).getroot();b=ET.parse(TARGET).getroot();cfg=json.loads((ROOT/'scenarios/north_surface_join.json').read_text());ae={e.get('id'):e for e in a.findall('edge')};be={e.get('id'):e for e in b.findall('edge')}
 for edge in cfg['excluded_grade_separated_edges']:
  assert ae[edge].attrib==be[edge].attrib
  assert [l.attrib for l in ae[edge].findall('lane')]==[l.attrib for l in be[edge].findall('lane')]
 for node in cfg['excluded_grade_separated_nodes']:
  assert a.find(f"junction[@id='{node}']").attrib==b.find(f"junction[@id='{node}']").attrib
