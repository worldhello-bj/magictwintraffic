#!/usr/bin/env python3
"""Exact replay vehicle-position core mask; no partial-road spatial approximation."""
import gzip
import json
import struct
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RECORD=struct.Struct('<fIffffII')


def summarize(folder):
    manifest=json.loads((folder/'manifest.json').read_text());network=json.loads((folder/manifest['network']).read_text())
    lane_edges={l['id']:l['edge_id'] for l in network['lanes']};edges={e['id']:e['name'] or e['id'] for e in network['edges']}
    lane_names=[edges.get(lane_edges.get(lane,''),None) for lane in manifest['lanes']]
    maxima={};last=None;counts=Counter();max_core_stopped=0;core_count=0
    def finish_frame(t):
        nonlocal max_core_stopped
        max_core_stopped=max(max_core_stopped,core_count)
        for road,count in counts.items():
            if count>maxima.get(road,{}).get('stopped_vehicles',0):maxima[road]=dict(road=road,stopped_vehicles=count,time=t)
    for chunk in manifest['chunks']:
        raw=gzip.decompress((folder/chunk['file']).read_bytes())
        for t,vehicle,x,y,angle,speed,lane,flags in RECORD.iter_unpack(raw):
            if t!=last:
                if last is not None:finish_frame(last)
                counts.clear();core_count=0;last=t
            if abs(x)<=500 and abs(y)<=500 and speed<.1:
                core_count+=1
                if lane<len(lane_names) and lane_names[lane]:counts[lane_names[lane]]+=1
    if last is not None:finish_frame(last)
    metrics=json.loads((folder/'metrics.json').read_text());series=json.loads((folder/'timeseries.json').read_text());stock={row['time']:row for row in json.loads((folder/'stock_timeseries.json').read_text())}
    snapshots=[]
    for row in series:
        if row['time']%300:continue
        s=stock[row['time']]
        snapshots.append(dict(time=row['time'],road_vehicles=row['all_cohort_inside'],core_vehicles=row['all_cohort_core_vehicles'],moving_vehicles=row['all_cohort_inside']-row['queue_vehicles'],stopped_vehicles=row['queue_vehicles'],boundary_insertion_waiting=s['boundary_insertion_waiting'],internal_insertion_waiting=s['internal_insertion_waiting'],parked=s['parked_total'],completed=row['all_cohort_completed']))
    return dict(run_id=manifest['run_id'],all_generated=metrics['all_cohort_generated'],all_completed=metrics['all_cohort_completed'],all_completion_fraction=metrics['all_cohort_completed']/metrics['all_cohort_generated'],peak_cohort_completion_fraction=metrics['completion_rate'],snapshots=snapshots,strict_core_top_roads=sorted(maxima.values(),key=lambda r:-r['stopped_vehicles'])[:3],strict_core_peak_stopped=max_core_stopped,method='Exact sampled SUMO vehicle x/y inside [-500,500]^2; speed <0.1m/s. Road names aggregate named external lanes; junction internal lanes are included in core total but not attributed to a named road. No parked stock included.')


if __name__=='__main__':
    import sys
    results=[summarize(Path(folder)) for folder in sys.argv[1:]]
    print(json.dumps(results,ensure_ascii=False,indent=2))
