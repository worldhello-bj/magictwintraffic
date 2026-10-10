#!/usr/bin/env python3
"""Aggregate verified recorded vehicle samples; never simulate or invent traffic.

Windows use (start, end]. Empty recorded instants count in ``frames``. Road
edges with no observations are omitted, because no observed speed is available.
"""
import argparse
import gzip
import hashlib
import json
import math
import struct
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = struct.Struct('<fIffffII')
FIELDS = ['observations', 'speed_sum_m_s', 'stopped_count', 'loss_sum', 'loss_valid_observations']
ALGORITHM = 'recorded-road-heatmap-v1'


def write_json(path, value):
    data = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + '.', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(data)
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(data).hexdigest()


def load_inputs(folder, start=None, end=None, bucket_seconds=60):
    folder = Path(folder)
    manifest = json.loads((folder / 'manifest.json').read_text())
    network_bytes = (folder / manifest['network']).read_bytes()
    network = json.loads(network_bytes)
    if network['network_hash'] != manifest['network_hash']:
        raise ValueError('Heatmap network hash mismatch')
    if manifest.get('lanes') != [lane['id'] for lane in network['lanes']]:
        raise ValueError('Heatmap lane dictionary mismatch')
    start = float(manifest['config'].get('warmup_seconds', 0) if start is None else start)
    end = float(manifest['duration_seconds'] if end is None else end)
    step = float(manifest.get('trajectory_step_seconds', manifest['step_seconds']))
    if not all(math.isfinite(n) for n in (start, end, step, bucket_seconds)) or not (0 <= start < end <= manifest['duration_seconds']) or step <= 0 or bucket_seconds <= 0:
        raise ValueError('Invalid heatmap time window')
    if not manifest.get('chunks'):
        raise ValueError('Heatmap requires recorded chunks')
    source = dict(algorithm=ALGORITHM, network_sha256=hashlib.sha256(network_bytes).hexdigest(),
                  run_id=manifest['run_id'], network_hash=manifest['network_hash'], demand_hash=manifest['demand_hash'],
                  policy_hash=manifest['policy_hash'], sample_step_seconds=step, start=start, end=end,
                  bucket_seconds=bucket_seconds, chunks=[{k: c[k] for k in ('file', 'sha256', 'records', 'start', 'end')} for c in manifest['chunks']])
    digest = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return manifest, network, start, end, step, digest


def available(folder, start=None, end=None, bucket_seconds=60):
    """Check cached statistics identity; caller separately verifies trajectory bytes."""
    try:
        manifest, _, start, end, _, digest = load_inputs(folder, start, end, bucket_seconds)
        data = (Path(folder) / manifest['road_heatmap']).read_bytes()
        result = json.loads(data)
        return (hashlib.sha256(data).hexdigest() == manifest['road_heatmap_sha256']
                and result['source_digest'] == digest and result['run_id'] == manifest['run_id']
                and result['network_hash'] == manifest['network_hash']
                and result['demand_hash'] == manifest['demand_hash']
                and result['total']['start'] == start and result['total']['end'] == end)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def export(folder, start=None, end=None, bucket_seconds=60):
    folder = Path(folder)
    manifest, network, start, end, step, digest = load_inputs(folder, start, end, bucket_seconds)
    # Always verify the compressed source bytes, including when reusing a cache.
    for chunk in manifest['chunks']:
        if hashlib.sha256((folder / chunk['file']).read_bytes()).hexdigest() != chunk['sha256']:
            raise ValueError('Heatmap source chunk checksum mismatch: ' + chunk['file'])
    if available(folder, start, end, bucket_seconds):
        return json.loads((folder / manifest['road_heatmap']).read_text())
    windows = [dict(start=start + i * bucket_seconds, end=min(end, start + (i + 1) * bucket_seconds), frames=0, edges={})
               for i in range(math.ceil((end - start) / bucket_seconds))]
    total = dict(start=start, end=end, frames=0, edges={})
    road_ids = {edge['id'] for edge in network['edges']}
    lanes = network['lanes']
    recorded_ticks = set()
    excluded_internal = 0
    invalid_limits = 0
    previous_time = -math.inf
    frame_ids = set()

    def window_for(time):
        return min(len(windows) - 1, max(0, math.ceil((time - start) / bucket_seconds - 1e-9) - 1))

    for chunk in manifest['chunks']:
        first, last = float(chunk['start']), float(chunk['end'])
        if not math.isfinite(first) or not math.isfinite(last) or first > last:
            raise ValueError('Invalid recorded chunk time range')
        first_tick, last_tick = round(first / step), round(last / step)
        if abs(first_tick * step - first) > 1e-5 or abs(last_tick * step - last) > 1e-5:
            raise ValueError('Chunk is not on the recorded sample grid')
        chunk_ticks = set(range(first_tick, last_tick + 1))
        if recorded_ticks.intersection(chunk_ticks):
            raise ValueError('Overlapping recorded chunks')
        recorded_ticks.update(chunk_ticks)
        for tick in chunk_ticks:
            time = tick * step
            if start < time <= end:
                windows[window_for(time)]['frames'] += 1
                total['frames'] += 1
        compressed = (folder / chunk['file']).read_bytes()
        compression = chunk.get('compression', 'none')
        if compression not in ('gzip', 'none'):
            raise ValueError('Unsupported trajectory compression')
        raw = gzip.decompress(compressed) if compression == 'gzip' else compressed
        if len(raw) % RECORD.size or len(raw) != chunk['records'] * RECORD.size:
            raise ValueError('Heatmap source record count mismatch')
        for time, vehicle, x, y, angle, speed, lane_index, _ in RECORD.iter_unpack(raw):
            if not all(math.isfinite(n) for n in (time, x, y, angle, speed)) or speed < 0:
                raise ValueError('Invalid recorded vehicle sample')
            if time < previous_time or not first <= time <= last or abs(round(time / step) * step - time) > 1e-5:
                raise ValueError('Recorded time is outside sorted sample grid')
            if time != previous_time:
                frame_ids.clear()
                previous_time = time
            if vehicle in frame_ids:
                raise ValueError('Duplicate vehicle in recorded frame')
            frame_ids.add(vehicle)
            if lane_index >= len(lanes):
                raise ValueError('Recorded lane index outside network')
            if not start < time <= end:
                continue
            lane = lanes[lane_index]
            edge = lane['edge_id']
            if lane.get('internal') or edge not in road_ids:
                excluded_internal += 1
                continue
            limit = lane.get('speed')
            valid_limit = isinstance(limit, (int, float)) and math.isfinite(limit) and limit > 0
            loss = max(0.0, 1.0 - speed / limit) if valid_limit else 0.0
            invalid_limits += not valid_limit
            for target in (windows[window_for(time)], total):
                values = target['edges'].setdefault(edge, [0, 0.0, 0, 0.0, 0])
                values[0] += 1
                values[1] += speed
                values[2] += speed < 0.1
                values[3] += loss
                values[4] += valid_limit
    expected = set(range(math.floor(start / step) + 1, math.floor(end / step + 1e-9) + 1))
    if not expected.issubset(recorded_ticks):
        raise ValueError('Missing recorded instants in requested heatmap window')
    # Stable ordering and modest precision make exports compact and reproducible.
    for window in [*windows, total]:
        window['edges'] = {edge: [v[0], round(v[1], 6), v[2], round(v[3], 6), v[4]]
                           for edge, v in sorted(window['edges'].items())}
    result = dict(schema_version='1.0', run_id=manifest['run_id'], network_hash=manifest['network_hash'],
                  demand_hash=manifest['demand_hash'], policy_hash=manifest['policy_hash'], source_digest=digest,
                  sample_step_seconds=step, bucket_seconds=bucket_seconds,
                  definition=dict(interval='(start,end]', edge_fields=FIELDS,
                      observations='vehicle-sample observations on external road edges; not unique trips or flow',
                      frames='all recorded instants including empty frames, verified from chunk time bounds and sample step',
                      stopped='speed < 0.1 m/s; includes red lights and stopping; not physical queue length',
                      speed_loss='max(0, 1 - recorded speed / lane speed limit); mean divides by loss_valid_observations; not trip delay',
                      missing='edges without observations have no measured speed or loss; do not replace with zero',
                      scope='all on-road vehicle cohorts; internal junction lanes excluded; no inserted-waiting or parked vehicles',
                      calibration='uncalibrated synthetic SUMO scenario, not observed Chengdu traffic'),
                  excluded_internal_observations=excluded_internal, invalid_speed_limit_observations=invalid_limits,
                  windows=windows, total=total)
    manifest['road_heatmap'] = 'road_heatmap.json'
    manifest['road_heatmap_sha256'] = write_json(folder / manifest['road_heatmap'], result)
    write_json(folder / 'manifest.json', manifest)
    return result


def export_catalog(root=ROOT):
    destination = Path(root) / 'web/public/data'
    catalog = json.loads((destination / 'catalog.json').read_text())
    for entry in catalog['runs']:
        result = export((destination / entry['manifest']).parent)
        print(json.dumps(dict(run_id=result['run_id'], frames=result['total']['frames'], windows=len(result['windows']), road_edges=len(result['total']['edges']))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, help='Packaged run directory; otherwise export the published catalog')
    args = parser.parse_args()
    if args.run:
        result = export(args.run)
        print(json.dumps(dict(run_id=result['run_id'], frames=result['total']['frames'])))
    else:
        export_catalog()
