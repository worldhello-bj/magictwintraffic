#!/usr/bin/env python3
"""Build a bounded north-surface junction counterfactual, preserving v2 and tunnels."""
import copy
import json
import os
import tempfile
import hashlib
import fcntl
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from traffic_twin.gis import digest, write_json

VARIANT = 'joined_north_surface_v3'
SOURCE_VARIANT = 'joined_nijiaqiao_access_v2'
CONFIG = ROOT / 'scenarios/north_surface_join.json'


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        json.loads(Path(temporary).read_text())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def build():
    target_dir = ROOT / 'networks' / VARIANT
    target_dir.mkdir(parents=True, exist_ok=True)
    # Concurrent ensure calls serialize; cache is checked only inside this lock.
    with (target_dir / '.build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with tempfile.TemporaryDirectory(prefix='.staging-', dir=target_dir) as staging:
            return _build_locked(Path(staging))


def _build_locked(staging):
    import sumolib
    baseline = ROOT / 'networks' / SOURCE_VARIANT / 'network.net.xml'
    settings = json.loads(CONFIG.read_text())
    JOINED = tuple(settings['joined_nodes'])
    REMOVED_EDGES = set(settings['expected_removed_external_edges'])
    canonical = ROOT / 'data/canonical' / f'{SOURCE_VARIANT}.json'
    source_hash = digest(baseline)
    canonical_hash = digest(canonical)
    target_dir = ROOT / 'networks' / VARIANT
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / 'network.net.xml'
    scene_target = ROOT / 'data/canonical' / f'{VARIANT}.json'
    receipt = target_dir / 'build_manifest.json'
    build_key = hashlib.sha256((source_hash + canonical_hash + digest(__file__) + digest(CONFIG)).encode()).hexdigest()
    if target.exists() and scene_target.exists() and receipt.exists():
        try:
            previous = json.loads(receipt.read_text())
            scene = json.loads(scene_target.read_text())
            if (previous.get('build_key') == build_key
                    and previous.get('network_hash') == digest(target)
                    and previous.get('canonical_hash') == digest(scene_target)
                    and scene.get('network_hash') == previous['network_hash']):
                ET.parse(target)
                return dict(previous, cache_hit=True)
        except (ValueError, OSError, ET.ParseError):
            pass
    nodes = staging / 'join.nod.xml'
    nodes.write_text('<nodes><join nodes="' + ' '.join(JOINED) + '" id="' + VARIANT + '" type="traffic_light"/></nodes>\n')
    staged_net = staging / 'network.net.xml'
    binary = Path(sys.executable).parent / 'netconvert'
    if not binary.exists():
        binary = Path(sumolib.checkBinary('netconvert'))
    args = [str(binary), '--sumo-net-file', str(baseline), '--node-files', str(nodes), '--output-file', str(staged_net), '--tls.yellow.time', '3', '--tls.allred.time', '1', '--tls.green.time', '30', '--output.street-names', 'true']
    if settings.get('extra_connections'):
        connections = staging / 'connections.con.xml'
        element = ET.Element('connections')
        for item in settings['extra_connections']:
            ET.SubElement(element, 'connection', {k:str(v) for k,v in item.items()})
        ET.ElementTree(element).write(connections, encoding='utf-8', xml_declaration=True)
        args += ['--connection-files', str(connections)]
    result = subprocess.run(args, capture_output=True, text=True)
    (staging / 'conversion.log').write_text(result.stdout + '\n' + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr)
    ET.parse(staged_net).write(staged_net, encoding='utf-8', xml_declaration=True)
    source = json.loads(canonical.read_text())
    source_nodes={n['id'] for n in source['junctions']}
    assert set(JOINED) <= source_nodes
    expected_by_endpoints={e['id'] for e in source['edges'] if e['from_node'] in JOINED and e['to_node'] in JOINED}
    assert expected_by_endpoints==REMOVED_EDGES, (sorted(expected_by_endpoints), sorted(REMOVED_EDGES))
    assert not set(JOINED).intersection(settings.get('excluded_grade_separated_nodes',[]))
    assert all(not e.get('osm_tags',{}).get('tunnel') or e.get('osm_tags',{}).get('tunnel')=='no' for e in source['edges'] if e['id'] in REMOVED_EDGES)
    manifest = copy.deepcopy(source)
    net = sumolib.net.readNet(str(staged_net), withInternal=True, withPrograms=True)
    origin = net.convertLonLat2XY(source['origin']['lon'], source['origin']['lat'])
    def local(p): return [round(p[0] - origin[0], 3), round(p[1] - origin[1], 3)]
    old_edges = {e['id']: e for e in source['edges']}
    old_lanes = {l['id']: l for l in source['lanes']}
    edges, lanes = [], []
    for edge in net.getEdges(withInternal=True):
        internal = edge.getFunction() == 'internal'
        for lane in edge.getLanes():
            entry = copy.deepcopy(old_lanes.get(lane.getID(), {}))
            entry.update(id=lane.getID(), edge_id=edge.getID(), shape=[local(p) for p in lane.getShape()], width=lane.getWidth(), speed=lane.getSpeed(), length=lane.getLength(), allow=list(lane.getPermissions()), internal=internal)
            lanes.append(entry)
        if internal:
            continue
        if edge.getID() not in old_edges:
            raise ValueError(f'Unexpected added external edge: {edge.getID()}')
        entry = copy.deepcopy(old_edges[edge.getID()])
        entry.update(from_node=edge.getFromNode().getID(), to_node=edge.getToNode().getID(), length=edge.getLength(), speed=edge.getSpeed(), lanes=[l.getID() for l in edge.getLanes()], shape=[local(p) for p in edge.getShape()], allows_passenger=edge.allows('passenger'), type=edge.getType())
        edges.append(entry)
    assert set(old_edges) - {e['id'] for e in edges} == REMOVED_EDGES
    assert {g['edge_id'] for g in source['gates']} <= {e['id'] for e in edges}
    manifest.update(network_variant=VARIANT, network_hash=digest(staged_net), name='成都玉林 · 北侧地面路口合并对照', edges=edges, lanes=lanes,
        junctions=[dict(id=n.getID(), position=local(n.getCoord()), shape=[local(p) for p in n.getShape()], type=n.getType()) for n in net.getNodes() if not n.getID().startswith(':')],
        traffic_lights=[dict(id=t.getID(), junction_ids=[t.getID()]) for t in net.getTrafficLights()])
    manifest['origin'].update(sumo_x=origin[0], sumo_y=origin[1])
    manifest['provenance']['network_variant'] = dict(id=VARIANT, baseline_network_hash=source_hash, joined_nodes=list(JOINED), removed_external_edges=sorted(REMOVED_EDGES), method='Explicit netconvert node join; loaded connectivity retained; rebuilt junction conflict geometry and inferred fixed-time TLS; baseline preserved.', status='topology_hypothesis_not_field_verified', sources=['https://sumo.dlr.de/docs/Networks/PlainXML.html#reasons_for_joining_node_clusters'], source_variant=SOURCE_VARIANT, grade_separation_review=settings)
    manifest['provenance']['signals'] = 'SUMO inferred experimental fixed-time control, including isolated north surface join; not observed Chengdu timing'
    staged_scene = staging / 'scene.json'
    write_json(staged_scene, manifest)
    ET.parse(staged_net)
    assert json.loads(staged_scene.read_text())['network_hash'] == digest(staged_net)
    assert source_hash == digest(baseline) and canonical_hash == digest(canonical)
    summary = dict(network_variant=VARIANT, network_hash=manifest['network_hash'], baseline_network_hash=source_hash, removed_external_edges=sorted(REMOVED_EDGES), joined_nodes=list(JOINED), joined_node=VARIANT, baseline_unchanged=True, buildings_preserved=manifest['buildings'] == source['buildings'], gates_preserved=manifest['gates'] == source['gates'], external_edges=len(edges), lanes=len(lanes), junctions=len(manifest['junctions']), traffic_lights=len(manifest['traffic_lights']))
    summary['source_variant']=SOURCE_VARIANT
    summary['grade_separation_review']=settings
    summary.update(build_key=build_key, canonical_hash=digest(staged_scene), status='ready')
    # Publish complete files only. Receipt is last and carries both content hashes.
    # Readers requiring cross-file consistency should verify this receipt.
    with staged_net.open('rb') as stream:
        os.fsync(stream.fileno())
    os.replace(staged_net, target)
    atomic_json(scene_target, manifest)
    os.replace(nodes, target_dir / 'join.nod.xml')
    os.replace(staging / 'conversion.log', target_dir / 'conversion.log')
    atomic_json(receipt, summary)
    return summary


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
