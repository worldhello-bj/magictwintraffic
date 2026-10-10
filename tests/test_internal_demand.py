import csv
import json
from collections import Counter
import pytest
from traffic_twin.gis import ROOT
from traffic_twin.demand import generate_demand
from traffic_twin.schemas import Scenario
from traffic_twin.simulation import run_simulation, validate_config


@pytest.fixture(scope='module')
def network():
    import sumolib
    return sumolib.net.readNet(str(ROOT/'networks/baseline/network.net.xml')),json.loads((ROOT/'data/canonical/network.json').read_text())


def test_internal_inventory_reproducible_and_boundary_not_duplicated(network):
    net,scene=network
    config=dict(seed=17,period='am',duration_seconds=300,demand_end_seconds=250,rate_per_gate=120)
    boundary,_=generate_demand(net,scene,config)
    config['internal_demand']={'cars_per_building':2,'initial_departure_fraction':.2}
    trips,meta=generate_demand(net,scene,config);again,other=generate_demand(net,scene,config)
    assert trips==again and meta['demand_hash']==other['demand_hash']
    original={t['persistent_trip_id']:(t['origin_gate'],t['desired_departure']) for t in boundary}
    retained={t['persistent_trip_id']:(t['origin_gate'],t['desired_departure']) for t in trips if t['origin_kind']=='boundary'}
    assert original==retained
    assert len({t['persistent_trip_id'] for t in trips})==len(trips)
    internal=meta['internal_demand'];counts=Counter(t['origin_gate'] for t in trips if t['origin_kind']=='internal')
    assert internal['boundary_arrivals_reassigned']>0
    assert sum(row['trip_count'] for row in internal['od_matrix'])==len(trips)
    for z in internal['zones']:
        assert counts[z['id']]<=z['initial_parked']
        assert net.getEdge(z['access_edge']).allows('passenger')
        assert 0<z['access_position_m']<net.getEdge(z['access_edge']).getLength()
    assert any(t['desired_departure']==0 and t['origin_kind']=='internal' for t in trips)
    assert all(t['route'][0]!=t['route'][-1] for t in trips if t['origin_kind']=='internal')
    assert all(net.getFastestPath(net.getEdge(t['route'][0]),net.getEdge(t['route'][-1]),vClass='passenger')[0] for t in trips)


def test_am_pm_assumptions_are_explicit(network):
    net,scene=network
    config=dict(seed=42,duration_seconds=300,internal_demand={'cars_per_building':1})
    _,am=generate_demand(net,scene,config)
    _,pm=generate_demand(net,scene,{**config,'period':'pm'})
    assert am['internal_demand']['internal_departures']>pm['internal_demand']['internal_departures']
    assert am['internal_demand']['assumptions']['boundary_to_internal_fraction']<pm['internal_demand']['assumptions']['boundary_to_internal_fraction']


def test_real_internal_stock_signals_and_od_export(tmp_path):
    manifest=run_simulation(dict(policy='S0',seed=42,duration_seconds=90,demand_end_seconds=60,rate_per_gate=80,trajectory=False,internal_demand={'cars_per_building':1,'departure_fraction':.2,'initial_departure_fraction':.1}),tmp_path)
    audit=json.loads((tmp_path/'audit.json').read_text())
    assert audit['parked_stock_conservation_passed'] and not audit['teleports'] and not audit['collisions']
    stocks=json.loads((tmp_path/'stock_timeseries.json').read_text())
    for s in stocks:
        assert s['initial_parked_total']+s['boundary_inserted']==s['parked_total']+s['inside']+s['boundary_completed']
        assert min(s['parked_by_zone'].values())>=0
        assert s['conservation_residual']==0
    demand=json.loads((tmp_path/'demand.json').read_text())
    rows=list(csv.DictReader((tmp_path/'od_matrix.csv').open()))
    assert sum(int(row['trip_count']) for row in rows)==len(demand['vehicle_inventory'])
    signals=json.loads((tmp_path/'signals.json').read_text())
    assert signals and signals[0]['time']==0
    topology=json.loads((tmp_path/'signal_topology.json').read_text())
    states={s['tls']:s['state'] for s in signals}
    assert all(link['index']<len(states[node['tls']]) for node in topology for link in node['links'])
    hotspots=json.loads((tmp_path/'queue_hotspots.json').read_text())
    assert all(sum(e['stopped_vehicles'] for e in row['edges'])==row['total_stopped'] for row in hotspots)
    assert manifest['internal_zones']=='internal_zones.json'


def test_internal_api_schema_and_bounds():
    config=Scenario(internal_demand={'cars_per_building':2}).engine_config()
    assert config['internal_demand']['cars_per_building']==2
    validate_config(config)
    for options in ({'departure_fraction':2},{'fake':1},{'cars_per_building':21}):
        with pytest.raises(ValueError):validate_config({'internal_demand':options})
