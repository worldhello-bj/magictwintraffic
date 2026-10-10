"""Mechanism-bearing policies; unsupported physical widening fails explicitly."""
import json,hashlib,copy,xml.etree.ElementTree as ET
from pathlib import Path
from .gis import ROOT,digest,write_json
from .demand import stable_hash
NAMES={'S0':'实验基准','S1':'局部信号疏导','S2':'既有车道空间再分配','S3':'区域协调与下游容量保护','S4':'核心支路穿行管理','S5':'路侧临停治理','S6':'公交信号优先','S7':'协调 + 路侧治理 + 公交优先'}
def policy_catalog():
 return [dict(id=k,policy_id=k,name=v,available=True,supported=True,reason='Existing OSM-tagged multilane space reassigned to buses/bicycles; hypothetical legal implementation, no widening.' if k=='S2' else None,parameters={},status='implemented_experimental') for k,v in NAMES.items()]

def compile_policy(network,policy,output,parameters=None,network_source=None):
 if policy not in NAMES:raise ValueError('Unknown policy')
 source=Path(network_source) if network_source is not None else ROOT/'networks/baseline/network.net.xml';patch=dict(parameters or {});scene=copy.deepcopy(network);path=source
 if policy in ('S2','S4'):
  if policy=='S4':
   choices=[e for e in network['edges'] if 'residential' in e['type'] and e['allows_passenger'] and e['length']>65 and e['shape'] and all(abs(p[0])<420 and abs(p[1])<420 for p in e['shape'])]
  else:
   choices=[e for e in network['edges'] if e['allows_passenger'] and e.get('osm_tags',{}).get('lanes','').isdigit() and int(e['osm_tags']['lanes'])>=2 and e.get('display_elevation',0)==0 and e['length']>80 and any(abs(p[0])<500 and abs(p[1])<500 for p in e['shape']) and len([l for l in network['lanes'] if l['edge_id']==e['id'] and 'passenger' in l['allow']])>=2]
  if not choices:raise ValueError('No evidence-qualified existing road/lane for policy '+policy)
  edge=sorted(choices,key=lambda x:(-x['length'],x['id']))[0];target=edge['id'];tree=ET.parse(source)
  target_lanes=[l['id'] for l in network['lanes'] if l['edge_id']==target and 'passenger' in l['allow']]
  if policy=='S2':target_lanes=target_lanes[:1]
  for element in tree.getroot().findall('edge'):
   if element.attrib['id']!=target:continue
   for lane in element.findall('lane'):
    if lane.get('id') not in target_lanes:continue
    allowed=lane.get('allow')
    if allowed is not None:lane.set('allow',' '.join(a for a in allowed.split() if a not in ('passenger','private')))
    else:lane.set('disallow',' '.join(sorted(set(lane.get('disallow','').split()+['passenger','private']))))
  path=Path(output)/'network.net.xml';tree.write(path,encoding='utf-8',xml_declaration=True)
  patch=dict(closed_passenger_edge=target if policy=='S4' else None,reallocated_lanes=target_lanes,osm_way_id=edge['osm_way_id'],osm_lane_tag=edge.get('osm_tags',{}).get('lanes'),road_name=edge['name'],reason='Existing lane geometry retained; one general-traffic lane reserved for non-car traffic, lost car-lane capacity explicitly modeled; no physical widening claim' if policy=='S2' else 'Experimental no-through-car rule on existing core residential geometry; buses retain access',status='assumed_policy_not_existing_rule')
  for lane in scene['lanes']:
   if lane['id'] in target_lanes:lane['closed_passenger']=True;lane['allow']=[v for v in lane['allow'] if v not in ('passenger','private')]
  for e in scene['edges']:
   if e['id']==target:e['allows_passenger']=policy!='S4';e['closed_passenger']=policy=='S4';e['reallocated_lanes']=target_lanes
 scene['network_hash']=digest(path);scene['parent_hash']=network['network_hash'] if policy in ('S2','S4') else None
 manifest=dict(policy_id=policy,name=NAMES[policy],parameters=patch,mechanisms={'S0':['fixed_time_signals','seeded_curb_stops','scheduled_bus_stops'],'S1':['bounded_main_approach_green_extension'],'S2':['existing_tagged_lane_noncar_reallocation','legal_route_recompute'],'S3':['shared_cycle_Yulin_corridor_offsets','bounded_green_extension_with_downstream_storage'],'S4':['passenger_edge_permission_closure','legal_route_recompute'],'S5':['reduced_actual_curb_stop_duration'],'S6':['actual_bus_stops','bounded_bus_green_extension'],'S7':['shared_cycle_Yulin_corridor_offsets','downstream_storage_extension','reduced_curb_stop_duration','bus_green_extension']}.get(policy,[]),status='synthetic_policy_experiment_not_field_approval')
 manifest['policy_hash']=stable_hash(manifest);write_json(Path(output)/'network.json',scene);write_json(Path(output)/'policy.json',manifest)
 return path,scene,manifest

class PolicyController:
 def __init__(self,api,network,policy,parameters=None):
  self.parameters=parameters or {};self.extension=float(self.parameters.get('green_extension_seconds',8));self.threshold=float(self.parameters.get('downstream_occupancy_threshold',65));self.api=api;self.policy=policy;self.extended={};self.events=[];self.links={};self.positions={n['id']:n['position'] for n in network['junctions']}
  edge_names={e['id']:e['name'] for e in network['edges']};lane_edges={l['id']:l['edge_id'] for l in network['lanes']}
  corridor=[]
  for tls in api.trafficlight.getIDList():
   self.links[tls]=api.trafficlight.getControlledLinks(tls)
   controlled=api.trafficlight.getControlledLanes(tls)
   if any(edge_names.get(lane_edges.get(l,''),'') in ('玉林北路','玉林中路','玉林南路') for l in controlled):corridor.append(tls)
  self.selected=min(corridor or list(self.links),key=lambda t:sum(v*v for v in self.positions.get(t,(9999,9999))),default=None)
  if policy in ('S3','S7') and corridor:
   cycle=max(120.,max(sum(p.duration for p in api.trafficlight.getAllProgramLogics(t)[0].phases if not any(c in 'Gg' for c in p.state))+8*sum(any(c in 'Gg' for c in p.state) for p in api.trafficlight.getAllProgramLogics(t)[0].phases) for t in corridor))
   for tls in corridor:
    logic=api.trafficlight.getAllProgramLogics(tls)[0];greens=[p for p in logic.phases if any(c in 'Gg' for c in p.state) and 'y' not in p.state];clear=sum(p.duration for p in logic.phases if p not in greens);original=sum(p.duration for p in greens)
    for phase in logic.phases:
     if phase in greens:phase.duration=8+(cycle-clear-8*len(greens))*phase.duration/original
    api.trafficlight.setProgramLogic(tls,logic)
    # Align first phase serving the named physical Yulin north-south corridor.
    aligned=0;prefix=0.
    for phase in logic.phases:
     serving=any(i<len(phase.state) and phase.state[i] in 'Gg' and any(edge_names.get(lane_edges.get(link[0],''),'') in ('玉林北路','玉林中路','玉林南路') for link in links) for i,links in enumerate(self.links[tls]))
     if serving:aligned=prefix;break
     prefix+=phase.duration
    x,y=self.positions.get(tls,(0,0));offset=(aligned-y/9)%cycle
    for i,phase in enumerate(logic.phases):
     if offset<phase.duration:api.trafficlight.setPhase(tls,i);api.trafficlight.setPhaseDuration(tls,phase.duration-offset);break
     offset-=phase.duration
    self.events.append(dict(time=0,type='corridor_offset',tls=tls,cycle_seconds=cycle,corridor='玉林北路/玉林中路/玉林南路',design_speed_m_s=9,position_north_m=y,status='experimental_fixed_timing_not_observed'))
  if self.selected:self.events.append(dict(time=0,type='local_target',tls=self.selected,status='nearest_core_Yulin_corridor_signal'))
 def step(self,time):
  if self.policy not in ('S1','S3','S6','S7'):return
  api=self.api
  for tls,links in self.links.items():
   if self.policy=='S1' and tls!=self.selected:continue
   phase=api.trafficlight.getPhase(tls);state=api.trafficlight.getRedYellowGreenState(tls);key=(tls,phase)
   # Reset extension only after a real phase change, never skip amber/all-red.
   old=self.extended.get(tls)
   if old and old[0]!=phase:self.extended.pop(tls,None)
   if tls in self.extended or api.trafficlight.getNextSwitch(tls)-time>1.0 or 'y' in state or not any(s in 'Gg' for s in state):continue
   pressure=0;bus=False;receiving=True
   for i,ls in enumerate(links):
    if i>=len(state) or state[i] not in 'Gg':continue
    for incoming,outgoing,via in ls:
     pressure+=api.lane.getLastStepHaltingNumber(incoming)
     if api.lane.getLastStepOccupancy(outgoing)>self.threshold:receiving=False
     if self.policy in ('S6','S7'):
      bus=bus or any(api.vehicle.getTypeID(v)=='bus' for v in api.lane.getLastStepVehicleIDs(incoming))
   extend=(self.policy=='S1' and pressure>=2) or (self.policy in ('S3','S7') and pressure>=3 and receiving) or (self.policy in ('S6','S7') and bus and receiving)
   if extend:
    api.trafficlight.setPhaseDuration(tls,self.extension);self.extended[tls]=(phase,time);self.events.append(dict(time=time,type='green_extension',tls=tls,phase=phase,duration=self.extension,queue=pressure,bus=bus,downstream_space=receiving))
