"""Topology correction preserves reachable surface turns and grade separation."""
import hashlib,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_north_surface_movement_and_tunnel_contract():
 for name in ['build_internal_network','build_access_network','build_north_surface_network']:
  module=runpy.run_path(str(ROOT/'scripts'/f'{name}.py'));module['build']()
 runpy.run_path(str(ROOT/'scripts/review_north_surface_variant.py'))
 review=json.loads((ROOT/'docs/evidence/north_surface_review.json').read_text())
 assert not review['missing_movements'] and not review['added_movements']
 assert not review['missing_bus_movements'] and not review['added_bus_movements']
 assert not review['grade_separated_semantic_changes']
 assert len(review['grade_separated_edges_checked'])==33
 assert review['gates_equal'] and review['buildings_equal']
 net=ROOT/'networks/joined_north_surface_v3/network.net.xml'
 assert review['variant_hash']==hashlib.sha256(net.read_bytes()).hexdigest()
 changes=review['surviving_external_edge_changes']
 assert len(changes)==12
 assert all(set(e['changes'])<={'shape','length','from_node','to_node'} for e in changes)
