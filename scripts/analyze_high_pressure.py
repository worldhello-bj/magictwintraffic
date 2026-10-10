#!/usr/bin/env python3
"""Reproducible observed congestion statistics; no invented traffic or queue lengths."""
import csv,gzip,json,math,struct,statistics
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RECORD=struct.Struct('<fIffffII')
def project(x,y,shape):
 best=(float('inf'),0);offset=0
 for a,b in zip(shape,shape[1:]):
  dx=b[0]-a[0];dy=b[1]-a[1];length=math.hypot(dx,dy);u=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(length*length))) if length else 0
  best=min(best,(math.hypot(x-a[0]-u*dx,y-a[1]-u*dy),offset+u*length));offset+=length
 return best[1]
def summarize(folder):
 m=json.loads((folder/'manifest.json').read_text());metrics=json.loads((folder/'metrics.json').read_text());series=json.loads((folder/'timeseries.json').read_text());trips=json.loads((folder/'trips.json').read_text());stock=json.loads((folder/'stock_timeseries.json').read_text());network=json.loads((folder/'network.json').read_text());edges={e['id']:e for e in network['edges']};lanes={l['id']:l for l in network['lanes']};lane_meta=[lanes[x] for x in m['lanes']];end=m['config']['demand_end_seconds'];observed=[x for x in series if 600<=x['time']<=end];window=[600,end];speed_sum=0;speed_n=0;core_speed_sum=0;core_speed_n=0;stopped_road_max={};lane_events=defaultdict(list);max_core_stopped=0;current=None;frame=[]
 def finish(t,frame):
  nonlocal speed_sum,speed_n,core_speed_sum,core_speed_n,max_core_stopped
  if not frame:return
  by_lane=defaultdict(list);roads=defaultdict(int);core_stopped=0
  for vehicle,x,y,speed,lane in frame:
   core=abs(x)<=500 and abs(y)<=500
   if 600<=t<=end:
    speed_sum+=speed;speed_n+=1
    if core:core_speed_sum+=speed;core_speed_n+=1
   if speed<.1:
    if core:core_stopped+=1
    meta=lane_meta[lane];edge=edges.get(meta['edge_id'])
    if edge:
     roads[edge['id']]+=1
     if meta['length']>=40:by_lane[lane].append(project(x,y,meta['shape']))
  max_core_stopped=max(max_core_stopped,core_stopped)
  for edge,count in roads.items():
   if count>stopped_road_max.get(edge,{}).get('stopped',0):stopped_road_max[edge]=dict(edge_id=edge,road=edges[edge]['name'],stopped=count,time=t)
  for lane,positions in by_lane.items():
   p=sorted(positions);meta=lane_meta[lane]
   # Observed stopped chain covers most of a lane and physically reaches its upstream end.
   if len(p)>=4 and p[0]<=20 and p[-1]>=.7*meta['length'] and max(b-a for a,b in zip(p,p[1:]))<=20:
    lane_events[meta['id']].append(dict(time=t,stopped=len(p),tail_m=round(p[0],2),head_m=round(p[-1],2),span_m=round(p[-1]-p[0],2),lane_length_m=meta['length']))
 for chunk in m['chunks']:
  raw=gzip.decompress((folder/chunk['file']).read_bytes())
  for t,vehicle,x,y,angle,speed,lane,flags in RECORD.iter_unpack(raw):
   if t%5:continue
   if current!=t:
    if current is not None:finish(current,frame)
    current=t;frame=[]
   frame.append((vehicle,x,y,speed,lane))
 if current is not None:finish(current,frame)
 spill=[]
 for lane,events in lane_events.items():
  longest=run=5;start=events[0]['time'];best_start=start
  for a,b in zip(events,events[1:]):
   if b['time']-a['time']==5:run+=5
   else:run=5;start=b['time']
   if run>longest:longest=run;best_start=start
  meta=lanes[lane];spill.append(dict(lane_id=lane,edge_id=meta['edge_id'],road=edges[meta['edge_id']]['name'],samples=len(events),observed_seconds=len(events)*5,longest_continuous_seconds=longest,longest_start=best_start,peak_stopped=max(x['stopped'] for x in events),example=max(events,key=lambda x:x['stopped'])))
 clear=next((x['time'] for x in series if x['time']>=end and x['all_cohort_inside']==0 and x['all_cohort_external_waiting']==0),None)
 target=[t for t in trips if t['cohort_id']=='peak'];delays=[max(0,t['travel_time_seconds']-t['reference_free_flow_seconds']) for t in target if t['status']=='completed']
 snapshots=[];stock_by_time={x['time']:x for x in stock}
 for x in series:
  if x['time']%300==0:
   y=stock_by_time[x['time']];snapshots.append(x | dict(boundary_insertion_waiting=y['boundary_insertion_waiting'],internal_insertion_waiting=y['internal_insertion_waiting'],parked_total=y['parked_total']))
 result=dict(run_id=m['run_id'],config=m['config'],network_hash=m['network_hash'],demand_hash=m['demand_hash'],metrics=metrics,audit=json.loads((folder/'audit.json').read_text()),observation_window_seconds=window,occupancy={k:dict(mean=statistics.mean(x[k] for x in observed),peak=max(x[k] for x in observed)) for k in ['all_cohort_inside','all_cohort_core_vehicles','all_cohort_periphery_vehicles','all_cohort_external_waiting','queue_vehicles']},sampled_space_mean_speed_km_h=3.6*speed_sum/speed_n if speed_n else None,sampled_core_space_mean_speed_km_h=3.6*core_speed_sum/core_speed_n if core_speed_n else None,completed_only_mean_delay_seconds=statistics.mean(delays) if delays else None,peak_strict_core_stopped=max_core_stopped,clearance_time_seconds=clear,recovery_tail_seconds=m['duration_seconds']-end,final_state=series[-1],snapshots=snapshots,top_stopped_edges=sorted(stopped_road_max.values(),key=lambda x:-x['stopped'])[:20],observed_lane_storage_pressure=sorted(spill,key=lambda x:-x['longest_continuous_seconds'])[:30],measurement_notes=['Speed is vehicle-frame arithmetic mean at 5s sampled states, 600s to demand end, not trip harmonic space-mean speed.','Stopped = speed <0.1m/s, all cohorts. Queue count is not physical contiguous length.','Lane storage pressure requires >=4 stopped cars, tail <=20m from lane start, head >=70% lane length, all consecutive front-position gaps <=20m. It is a reproducible spillback proxy, not proof of upstream junction blockage.','Recovery clearance requires zero in-network and zero due waiting after demand end. Unfinished trips remain included in finite-window TSTT.','Completed-only delay subtracts route free-flow reference and is secondary because unfinished trips are censored.'])
 return result
if __name__=='__main__':
 import sys
 for name in sys.argv[1:]:
  p=Path(name);result=summarize(p);(p/'high_pressure_analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(result['run_id'],result['clearance_time_seconds'],flush=True)
