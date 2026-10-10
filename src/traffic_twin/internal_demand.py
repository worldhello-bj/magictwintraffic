"""Auditable synthetic building-zone demand; no invented building entrances.

Map footprints establish spatial weights only. Initial stock and trip rates are
explicit scenario assumptions. Road-edge access is a nearest connected proxy,
not a surveyed driveway. Boundary arrivals are reassigned, never duplicated.
"""
import csv
import math
import random
from collections import Counter
from .gis import write_json


def _projection(point, shape):
    best = (float('inf'), 0.)
    offset = 0.
    for a, b in zip(shape, shape[1:]):
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        u = max(0., min(1., ((point[0]-a[0])*dx+(point[1]-a[1])*dy)/(length*length))) if length else 0.
        distance = math.hypot(point[0]-a[0]-u*dx, point[1]-a[1]-u*dy)
        best = min(best, (distance, offset+u*length))
        offset += length
    return best


def build_zones(net, network, options):
    size = 250
    groups = {}
    for building in network['buildings']:
        polygon = building['polygon'][:-1] or building['polygon']
        x = sum(p[0] for p in polygon)/len(polygon)
        y = sum(p[1] for p in polygon)/len(polygon)
        if -500 <= x < 500 and -500 <= y < 500:
            key = (int((x+500)//size), int((y+500)//size))
            groups.setdefault(key, []).append((building['id'], x, y))
    gates = network['gates']
    entries = [g for g in gates if g['direction']=='entry']
    exits = [g for g in gates if g['direction']=='exit']
    candidates = [e for e in network['edges'] if e['allows_passenger'] and e['length']>30 and e.get('display_elevation',0)==0 and not any(t in e['type'] for t in ('motorway','trunk')) and e['id'] not in {g['edge_id'] for g in gates}]
    if options.get('local_access_only',False):
        candidates=[e for e in candidates if any(t in e['type'] for t in ('residential','service','unclassified','living_street'))]
    zones = []
    for (col, row), buildings in sorted(groups.items()):
        center = [sum(b[1] for b in buildings)/len(buildings), sum(b[2] for b in buildings)/len(buildings)]
        ranked = sorted(((*_projection(center, e['shape']), e['id']) for e in candidates))
        for distance, position, edge_id in ranked:
            edge = net.getEdge(edge_id)
            outgoing = [g['id'] for g in exits if net.getFastestPath(edge, net.getEdge(g['edge_id']), vClass='passenger')[0]]
            incoming = [g['id'] for g in entries if net.getFastestPath(net.getEdge(g['edge_id']), edge, vClass='passenger')[0]]
            if outgoing and incoming:
                stock = max(20, min(100, len(buildings)*int(options.get('cars_per_building',3))))
                zones.append(dict(id=f'zone_{col}_{row}',name=f'玉林建筑片区 {col+1}-{row+1}',position=center,building_ids=[b[0] for b in buildings],building_count=len(buildings),access_edge=edge_id,access_position_m=round(min(edge.getLength()-5,max(5,position)),3),access_distance_m=round(distance,2),access_kind='nearest_connected_road_proxy_not_surveyed_entrance',initial_parked=stock,incoming_gates=incoming,outgoing_gates=outgoing,source='OSM building footprint aggregation; stock and access are synthetic assumptions'))
                break
    if not zones:
        raise ValueError('Internal demand requested but no building zones have connected passenger-road access')
    return zones


def add_internal_demand(net, network, config, boundary_trips):
    options = config['internal_demand']
    zones = build_zones(net, network, options)
    rng = random.Random(int(config.get('seed',42))+94117)
    end = float(config.get('demand_end_seconds',config.get('duration_seconds',600)*.7))
    warmup = float(config.get('warmup_seconds',0))
    period = config.get('period','am')
    fraction = float(options.get('departure_fraction',.7 if period=='am' else .4))
    inbound_fraction = float(options.get('boundary_to_internal_fraction',.25 if period=='am' else .55))
    gate_map = {g['id']:g for g in network['gates']}
    def route(a,b):
        path,cost=net.getFastestPath(net.getEdge(a),net.getEdge(b),vClass='passenger',withInternal=False)
        return ([e.getID() for e in path],cost) if path else ([],0)
    # Preserve each boundary arrival time, origin and ID. Only its destination changes.
    reassigned = 0
    for trip in boundary_trips:
        trip['origin_kind']='boundary';trip['destination_kind']='boundary'
        if trip['vehicle_type']!='car' or rng.random()>=inbound_fraction:continue
        choices=[z for z in zones if trip['origin_gate'] in z['incoming_gates']]
        if not choices:continue
        z=rng.choice(choices);edges,cost=route(trip['route'][0],z['access_edge'])
        trip.update(destination_gate=z['id'],destination_kind='internal',route=edges,reference_free_flow_seconds=cost,arrival_position_m=z['access_position_m'],demand_source='synthetic_boundary_arrival_reassigned_to_building_zone')
        reassigned+=1
    added=[]
    for z in zones:
        count=round(z['initial_parked']*fraction)
        initial_count=min(count,round(z['initial_parked']*float(options.get('initial_departure_fraction',.1))))
        for index in range(count):
            # A zero-time release forms an initial internal moving cohort as SUMO inserts safely.
            departure=0. if index<initial_count else round(rng.triangular(0,end,end*(.3 if period=='am' else .65)),3)
            dest=rng.choice([gate_map[g] for g in z['outgoing_gates']]);dest_id=dest['id'];dest_edge=dest['edge_id'];dest_kind='boundary';arrival=None
            if rng.random()<float(options.get('internal_to_internal_fraction',.25)):
                choices=[other for other in zones if other['id']!=z['id'] and other['access_edge']!=z['access_edge']]
                rng.shuffle(choices)
                for other in choices:
                    edges,cost=route(z['access_edge'],other['access_edge'])
                    if edges:
                        dest_id=other['id'];dest_edge=other['access_edge'];dest_kind='internal';arrival=other['access_position_m'];break
            edges,cost=route(z['access_edge'],dest_edge)
            trip=dict(persistent_trip_id=f'internal_{config.get("seed",42)}_{z["id"]}_{index:04}',desired_departure=departure,origin_gate=z['id'],destination_gate=dest_id,origin_kind='internal',destination_kind=dest_kind,vehicle_type='car',cohort_id='warmup' if departure<warmup else 'peak',demand_source='synthetic_initial_building_parked_stock',behavior_seed=rng.randrange(2**31),route=edges,reference_free_flow_seconds=cost,departure_position_m=z['access_position_m'])
            if arrival is not None:trip['arrival_position_m']=arrival
            added.append(trip)
    trips=boundary_trips+added
    trips.sort(key=lambda t:(t['desired_departure'],t['persistent_trip_id']))
    counts=Counter((t['origin_gate'],t['destination_gate'],t['origin_kind'],t['destination_kind'],int(t['desired_departure']//300)*300) for t in trips)
    od=[dict(origin=o,destination=d,origin_kind=ok,destination_kind=dk,interval_start=a,interval_end=min(a+300,end),trip_count=n,source='exact_generated_trip_inventory') for (o,d,ok,dk,a),n in sorted(counts.items())]
    return trips,dict(zones=zones,od_matrix=od,initial_parked_total=sum(z['initial_parked'] for z in zones),internal_departures=len(added),initial_release_count=sum(t['desired_departure']==0 for t in added),boundary_arrivals_reassigned=reassigned,boundary_arrival_count=len(boundary_trips),assumptions=dict(period=period,departure_fraction=fraction,boundary_to_internal_fraction=inbound_fraction,internal_to_internal_fraction=options.get('internal_to_internal_fraction',.25),initial_departure_fraction=options.get('initial_departure_fraction',.1),cars_per_building=options.get('cars_per_building',3),stock_clamp_per_zone=[20,100],zone_grid_m=250,local_access_only=options.get('local_access_only',False)),limitations=['OSM footprints are geographic evidence, not measured population or parking capacity.','Access positions are connected road proxies, not surveyed entrances or modeled private driveways.','Parked stock is off-network accounting; cars enter only valid SUMO lanes, with insertion delay retained.','Boundary arrivals are reassigned to internal destinations, never copied; no new boundary inflow is added.','Initial stock departures and boundary arrivals are distinct vehicles; arrivals park and do not generate a second journey.'])


def export_internal_demand(output, demand):
    internal=demand.get('internal_demand')
    if not internal:return
    write_json(output/'internal_zones.json',internal)
    write_json(output/'od_matrix.json',internal['od_matrix'])
    with (output/'od_matrix.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['origin','destination','origin_kind','destination_kind','interval_start','interval_end','trip_count','source'])
        writer.writeheader();writer.writerows(internal['od_matrix'])
