"""Regression for the diagnosed short-connector / adjacent-TLS mutual blockage."""
import importlib.util
import json
from pathlib import Path
from traffic_twin.gis import ROOT
from traffic_twin.simulation import run_simulation


def test_joined_junction_releases_same_logical_trips_without_teleport(tmp_path):
    variant=ROOT/'networks/joined_nijiaqiao_v1/network.net.xml'
    if not variant.exists():
        spec=importlib.util.spec_from_file_location('build_internal_network_runtime',ROOT/'scripts/build_internal_network.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.build()
    config=dict(policy='S0',period='am',seed=42,duration_seconds=1800,warmup_seconds=300,demand_end_seconds=1500,rate_per_gate=90,trajectory=False,internal_demand={'cars_per_building':1,'initial_departure_fraction':.05,'internal_to_internal_fraction':.3,'departure_fraction':.4})
    outputs={}
    for label,network in [('baseline','baseline'),('joined','joined_nijiaqiao_v1')]:
        folder=tmp_path/label;run_simulation({**config,'network_variant':network},folder)
        outputs[label]={name:json.loads((folder/(name+'.json')).read_text()) for name in ('demand','trips','metrics','audit','timeseries')}
    fields=('persistent_trip_id','desired_departure','origin_gate','destination_gate','origin_kind','destination_kind','vehicle_type','cohort_id','behavior_seed')
    def inventory(rows):return sorted(tuple(t.get(k) for k in fields) for t in rows)
    assert inventory(outputs['baseline']['demand']['vehicle_inventory'])==inventory(outputs['joined']['demand']['vehicle_inventory'])
    for output in outputs.values():
        assert output['audit']['parked_stock_conservation_passed']
        assert output['audit']['teleports']==output['audit']['collisions']==0
    old={t['persistent_trip_id']:t for t in outputs['baseline']['trips']};new={t['persistent_trip_id']:t for t in outputs['joined']['trips']}
    for vehicle in ('t42_0000058','t42_0000043','t42_0000094','internal_42_zone_0_2_0011'):
        assert old[vehicle]['arrived_at'] is None
        assert new[vehicle]['arrived_at'] is not None
    final=outputs['joined']['timeseries'][-1]
    assert final['queue_vehicles']<10
    assert outputs['joined']['metrics']['all_cohort_completed']>.95*outputs['joined']['metrics']['all_cohort_generated']
