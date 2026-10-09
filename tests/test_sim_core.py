import json,struct,gzip
from pathlib import Path
import pytest
from traffic_twin.gis import ROOT,digest
from traffic_twin.demand import generate_demand,legal_paths
from traffic_twin.evaluator import conservation,Evaluator
from traffic_twin.recorder import Recorder
from traffic_twin.simulation import validate_config,run_simulation

def test_conservation_rejects_silent_loss():
 assert conservation(10,2,5,3)==0
 with pytest.raises(RuntimeError):conservation(10,1,5,3)

def test_future_demand_not_waiting():
 trip=dict(persistent_trip_id='a',desired_departure=10,cohort_id='peak',vehicle_type='car')
 e=Evaluator([trip]);e.step(5,.5,[],[],[],{},0);m,_=e.finish(5)
 assert m['due']==0 and m['external_waiting']==0 and m['tstt_vehicle_seconds']==0

def test_waiting_enters_tstt():
 trip=dict(persistent_trip_id='a',desired_departure=.25,cohort_id='peak',vehicle_type='car')
 e=Evaluator([trip]);e.step(.5,.5,[],[],[],{},0);e.step(1,.5,[],[],[],{},0);m,_=e.finish(1)
 assert m['external_waiting']==1 and m['tstt_vehicle_seconds']==.75

def test_binary_layout_hash(tmp_path):
 r=Recorder(tmp_path,['v'],['lane']);r.frame(.5,[('v',1,2,90,3,'lane',1)]);c=r.close()[0]
 assert c['record_count']==1 and c['sha256']==digest(tmp_path/'chunk_00000.bin.gz')
 assert struct.unpack('<fIffffII',gzip.decompress((tmp_path/'chunk_00000.bin.gz').read_bytes()))==(.5,0,1,2,90,3,0,1)

def test_real_osm_scope():
 n=json.loads((ROOT/'data/canonical/network.json').read_text())
 assert n['core_polygon']==[[-500,-500],[500,-500],[500,500],[-500,500]]
 assert len(n['edges'])>100 and len(n['traffic_lights'])>5
 assert n['provenance']['osm_sha256']==digest(ROOT/'data/raw/yulin.osm')
 assert any('玉林' in e['name'] for e in n['edges'])
 assert any(l.get('display_elevation',0)>0 for l in n['lanes'])
 assert all(max(map(abs,g['position']))>=1000 for g in n['gates'])

def test_demand_reproducible_and_piecewise():
 import sumolib
 n=json.loads((ROOT/'data/canonical/network.json').read_text());net=sumolib.net.readNet(str(ROOT/'networks/baseline/network.net.xml'))
 a,ma=generate_demand(net,n,dict(duration_seconds=600,seed=8));b,mb=generate_demand(net,n,dict(duration_seconds=600,seed=8))
 assert a==b and ma['demand_hash']==mb['demand_hash']
 assert all(r['interval_end']-r['interval_start']<=300 for r in ma['od'])
 assert abs(ma['expected_base_count']-sum(r['expected_count'] for r in ma['od']))<1e-8

def test_invalid_od_fails_preflight():
 with pytest.raises(ValueError,match='OD'):validate_config(dict(od=[dict(origin_gate='fake',destination_gate='fake',rate_per_hour=1)]))

@pytest.mark.parametrize('policy',['S0','S1','S2','S3','S4','S5','S6','S7'])
def test_real_engine_all_policies(tmp_path,policy):
 r=run_simulation(dict(policy=policy,seed=42,duration_seconds=120,demand_end_seconds=75,rate_per_gate=80),tmp_path/policy)
 m=json.loads((tmp_path/policy/'metrics.json').read_text());a=json.loads((tmp_path/policy/'audit.json').read_text())
 assert m['due']==m['completed']+m['inside']+m['external_waiting']
 assert a['conservation_passed'] and not a['teleports'] and not a['collisions']
 assert r['engine']=='SUMO/libsumo'
 if policy in ('S2','S4'):assert r['network_hash']!=json.loads((ROOT/'data/canonical/network.json').read_text())['network_hash']

def test_downstream_constraint_propagates_and_preserves_external_wait(tmp_path):
 import sumolib
 network=json.loads((ROOT/'data/canonical/network.json').read_text());net=sumolib.net.readNet(str(ROOT/'networks/baseline/network.net.xml'));paths=legal_paths(net,network['gates']);gates={g['id']:g for g in network['gates']}
 choices=[(origin,c) for origin,cs in paths.items() for c in cs if len(net.getEdge(gates[c['destination_gate']]['edge_id']).getLanes())==1]
 origin,route=min(choices,key=lambda z:z[1]['distance_m'])
 config=dict(policy='S0',seed=17,duration_seconds=600,demand_end_seconds=300,buses=False,trajectory=False,od=[dict(origin_gate=origin,destination_gate=route['destination_gate'],rate_per_hour=3000)])
 baseline=run_simulation(config,tmp_path/'open')
 config['downstream_block']=dict(gate_id=route['destination_gate'],start_seconds=0,end_seconds=300,speed_m_s=.1)
 blocked=run_simulation(config,tmp_path/'blocked')
 a=json.loads((tmp_path/'open/metrics.json').read_text());b=json.loads((tmp_path/'blocked/metrics.json').read_text())
 assert baseline['demand_hash']==blocked['demand_hash']
 assert b['due']==b['completed']+b['inside']+b['external_waiting']
 assert b['external_waiting']>a['external_waiting'] and b['max_queue_vehicles']>a['max_queue_vehicles']
 assert b['completed']<a['completed'] and b['teleports']==0 and b['collisions']==0

def test_quarter_second_keeps_behavior_action_step(tmp_path):
 config=dict(policy='S0',seed=42,duration_seconds=120,demand_end_seconds=75,rate_per_gate=80,trajectory=False)
 a=run_simulation(config,tmp_path/'half');config['step_seconds']=.25;b=run_simulation(config,tmp_path/'quarter')
 assert a['demand_hash']==b['demand_hash'] and a['action_step_seconds']==b['action_step_seconds']==.5
 assert b['step_seconds']==.25
 for folder in ('half','quarter'):
  audit=json.loads((tmp_path/folder/'audit.json').read_text());assert audit['conservation_passed'] and not audit['teleports'] and not audit['collisions']


def test_control_polling_stays_half_second_at_both_integrator_steps(tmp_path,monkeypatch):
 from traffic_twin.policies import PolicyController
 original=PolicyController.step
 calls=[]
 def observed(self,time):
  calls.append(time)
  return original(self,time)
 monkeypatch.setattr(PolicyController,'step',observed)
 sequences=[]
 for dt in (.5,.25):
  calls.clear()
  manifest=run_simulation(dict(policy='S3',seed=42,duration_seconds=10,demand_end_seconds=5,rate_per_gate=0,buses=False,trajectory=False,step_seconds=dt),tmp_path/str(dt))
  assert manifest['control_interval_seconds']==manifest['action_step_seconds']==.5
  sequences.append(list(calls))
 assert sequences[0]==sequences[1]==[i*.5 for i in range(20)]
