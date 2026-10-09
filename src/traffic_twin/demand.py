"""Immutable exogenous trip inventory; paired policies share identical trips."""
import hashlib,json,random,math
from pathlib import Path
from .gis import ROOT,write_json

def stable_hash(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def legal_paths(net,gates):
    entries=[g for g in gates if g['direction']=='entry'];exits=[g for g in gates if g['direction']=='exit']
    result={}
    for origin in entries:
        choices=[]
        for dest in exits:
            if origin['side']==dest['side']:continue
            path,cost=net.getFastestPath(net.getEdge(origin['edge_id']),net.getEdge(dest['edge_id']),vClass='passenger',withInternal=False)
            if path and len(path)>=2:
                choices.append(dict(destination_gate=dest['id'],edges=[e.getID() for e in path],free_flow_seconds=cost,distance_m=sum(e.getLength() for e in path)))
        if choices:result[origin['id']]=choices
    return result

def generate_demand(net,network,config):
    seed=int(config.get('seed',42));rng=random.Random(seed)
    warmup=float(config.get('warmup_seconds',0));end=float(config.get('demand_end_seconds',config.get('duration_seconds',600)*.7))
    scale=float(config.get('demand_scale',1));rate=float(config.get('rate_per_gate',120))*scale
    paths=legal_paths(net,network['gates'])
    entries=[g for g in network['gates'] if g['direction']=='entry']
    inaccessible=[g['id'] for g in entries if g['id'] not in paths]
    if inaccessible:raise ValueError('Boundary entries have no legal cross-boundary destination: '+','.join(inaccessible))
    trips=[];gate_map={g['id']:g for g in network['gates']};od_rates=[];expected=0.
    custom=config.get('od')
    if custom:
        for row in custom:
            origin=row['origin_gate'];dest=row['destination_gate']
            if origin not in paths or not any(c['destination_gate']==dest for c in paths[origin]):raise ValueError(f'Unreachable or unknown OD {origin} -> {dest}')
    for segment_start in range(0,math.ceil(end),300):
        segment_end=min(end,segment_start+300)
        if custom:
            rates=[]
            for row in custom:
                a=max(segment_start,float(row.get('interval_start',0)));b=min(segment_end,float(row.get('interval_end',end)))
                if a<b:rates.append((row['origin_gate'],row['destination_gate'],float(row['rate_per_hour'])*scale,a,b))
        else:
            rates=[]
            for gate_id,choices in sorted(paths.items()):
                side=gate_map[gate_id]['side'];directional=({'N':1.25,'S':.9,'E':1.1,'W':.75} if config.get('period','am')=='am' else {'N':.8,'S':1.2,'E':.85,'W':1.15})[side]
                pulse=.75+.5*math.sin(math.pi*(segment_start+segment_end)/(2*end))
                for choice in choices:rates.append((gate_id,choice['destination_gate'],rate*directional*pulse/len(choices),segment_start,segment_end))
        for gate_id,destination,flow,a,b in rates:
            od_rates.append(dict(origin_gate=gate_id,destination_gate=destination,rate_per_hour=flow,interval_start=a,interval_end=b,expected_count=flow*(b-a)/3600))
            expected+=flow*(b-a)/3600;t=a
            route=next(c for c in paths[gate_id] if c['destination_gate']==destination)
            while flow>0:
                t+=rng.expovariate(flow/3600)
                if t>=b:break
                trips.append(dict(persistent_trip_id=f't{seed}_{len(trips):07}',desired_departure=round(t,3),origin_gate=gate_id,destination_gate=destination,vehicle_type='car',cohort_id='warmup' if t<warmup else 'peak',demand_source='synthetic_boundary_scenario',behavior_seed=rng.randrange(2**31),route=route['edges'],reference_free_flow_seconds=route['free_flow_seconds']))
    # Fixed scheduled buses, conserved across all policies; actual passenger behavior is outside this model.
    if config.get('buses',True) and paths:
        for index,(gate_id,choices) in enumerate(sorted(paths.items())[:4]):
            bus_choices=[c for c in choices if all(net.getEdge(e).allows('bus') for e in c['edges'])]
            if not bus_choices:continue
            route=bus_choices[index%len(bus_choices)]
            for t in range(30+index*45,int(end),300):
                trips.append(dict(persistent_trip_id=f'bus{seed}_{index}_{t}',desired_departure=float(t),origin_gate=gate_id,destination_gate=route['destination_gate'],vehicle_type='bus',cohort_id='warmup' if t<warmup else 'peak',demand_source='synthetic_scheduled_bus',behavior_seed=seed+index,route=route['edges'],reference_free_flow_seconds=route['free_flow_seconds']))
    trips.sort(key=lambda t:(t['desired_departure'],t['persistent_trip_id']))
    return trips,dict(schema_version='1.0',demand_hash=stable_hash([{k:v for k,v in t.items() if k not in ('route','reference_free_flow_seconds')} for t in trips]),source_kind='synthetic_scenario',network_hash=network['network_hash'],seed=seed,period=config.get('period','am'),rate_per_gate_veh_h=rate,arrival_model='exact independent Poisson process within each 5-minute OD input segment; distinct AM/PM directional factors',interval_seconds=300,expected_base_count=expected,scheduled_bus_count=sum(t['vehicle_type']=='bus' for t in trips),od=od_rates,actual_count=len(trips),warmup_seconds=warmup,demand_end_seconds=end,internal_od_enabled=False,od_reachability_checked=True,vehicle_inventory=trips)
